# app/workers/pipeline_daemon.py
# ---------------------------------------------------------------------------
# ASIKO Image-to-3D Pipeline Daemon
#
# Uses Tencent Hunyuan3D-2 on Hugging Face Spaces.
# Single API call: photo in → textured GLB out.
# No multi-step session state required.
# ---------------------------------------------------------------------------
import asyncio
import json
import os
import shutil
import logging
from typing import Optional

logger = logging.getLogger("asiko.pipeline")
OPTIMIZED_DIR = "static/uploads/optimized"
os.makedirs(OPTIMIZED_DIR, exist_ok=True)

# Hunyuan3D-2: single-step shape + texture generation.
# Configurable via env var for DNS/firewall workarounds.
GRADIO_SPACE = os.environ.get("ASIKO_GRADIO_SPACE", "tencent/Hunyuan3D-2")

# --- Prompt templates for garment categories ---
CATEGORY_PROMPTS = {
    "apparel":       "A realistic piece of clothing on a plain background, studio lighting",
    "outerwear":     "A realistic jacket or coat on a plain background, studio lighting",
    "tailoring":     "A realistic tailored suit on a plain background, studio lighting",
    "knitwear":      "A realistic knitwear garment on a plain background, studio lighting",
    "dresses":       "A realistic dress on a plain background, studio lighting",
    "accessories":   "A realistic fashion accessory on a plain background, studio lighting",
    "footwear":      "A realistic shoe or boot on a plain background, studio lighting",
}


class AsikoPipelineDaemon:
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.is_running = True
        self.ai_client = None

    # ------------------------------------------------------------------
    # Gradio connection
    # ------------------------------------------------------------------
    def _ensure_client(self) -> bool:
        """Lazy-connect to the Hunyuan3D-2 Space.  Retries on each call if
        previous attempt failed (no permanent flag)."""
        if self.ai_client is not None:
            return True
        try:
            from gradio_client import Client
            self.ai_client = Client(GRADIO_SPACE)
            logger.info("Connected to Gradio Space: %s", GRADIO_SPACE)
            return True
        except Exception as e:
            logger.warning("Gradio connection failed (will retry next product): %s", e)
            self.ai_client = None
            return False

    def _reset_client(self):
        """Force a fresh connection on next attempt."""
        self.ai_client = None

    # ------------------------------------------------------------------
    # Realtime notifications
    # ------------------------------------------------------------------
    async def _notify_pipeline_update(self, product_id: str, status: str, model_url: str = "") -> None:
        """Send a Postgres NOTIFY on pipeline_update channel for WebSocket broadcast."""
        try:
            from app.realtime import notify, CH_PIPELINE_UPDATE
            await notify(self.db_pool, CH_PIPELINE_UPDATE, {
                "type": "pipeline_update",
                "product_id": str(product_id),
                "status": status,
                "model_url": model_url,
            })
        except Exception as exc:
            logger.debug("NOTIFY pipeline_update failed: %s", exc)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    async def start_loop(self, check_interval_seconds=5):
        """Monitor the DB for newly queued products and process them."""
        while self.is_running:
            try:
                async with self.db_pool.acquire() as conn:
                    queued_items = await conn.fetch(
                        "SELECT id, source_2d_image_url, asset_category "
                        "FROM products WHERE pipeline_status = 'queued' ORDER BY id ASC;"
                    )
                    for item in queued_items:
                        product_id = item["id"]
                        img_url = item["source_2d_image_url"]
                        if not img_url:
                            logger.warning("Product %s queued but has no source image — skipping", product_id)
                            continue
                        local_img_path = img_url.lstrip("/")
                        category = item["asset_category"] or "apparel"
                        asyncio.create_task(
                            self.process_oss_generation(product_id, local_img_path, category)
                        )
            except Exception as e:
                logger.error("Error in processing loop: %s", e)
            await asyncio.sleep(check_interval_seconds)

    # ------------------------------------------------------------------
    # Core generation — single-step Hunyuan3D-2
    # ------------------------------------------------------------------
    async def process_oss_generation(self, product_id, local_img_path, category):
        """Call Hunyuan3D-2 `/shape_generation` to produce a textured GLB."""
        logger.info("Starting 3D generation for product %s ...", product_id)

        # Mark as generating
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE products SET pipeline_status = 'generating_mesh' WHERE id = $1;",
                product_id,
            )
        await self._notify_pipeline_update(product_id, "generating_mesh")

        if not os.path.exists(local_img_path):
            await self.mark_as_failed(product_id, f"Source image not found: {local_img_path}")
            return

        try:
            if not self._ensure_client():
                raise ConnectionError(
                    f"Cannot reach Gradio Space '{GRADIO_SPACE}'. "
                    "Set ASIKO_GRADIO_SPACE env var to override, or check network/DNS."
                )

            from gradio_client import handle_file
            loop = asyncio.get_running_loop()

            # Build a descriptive caption from the category
            caption = CATEGORY_PROMPTS.get(category, CATEGORY_PROMPTS["apparel"])

            logger.info("Calling Hunyuan3D-2 /shape_generation for product %s ...", product_id)
            result = await loop.run_in_executor(
                None,
                lambda: self.ai_client.predict(
                    caption=caption,
                    image=handle_file(local_img_path),
                    steps=50,
                    guidance_scale=5.5,
                    seed=1234,
                    octree_resolution="256",
                    check_box_rembg=True,
                    api_name="/shape_generation",
                ),
            )

            logger.debug("Hunyuan3D-2 raw result for product %s: %s", product_id, result)

            # /shape_generation returns: (untextured_glb, html_preview, stats, seed)
            # Extract the GLB file path from the result.
            glb_path = self._extract_glb_path(result)
            if not glb_path or not os.path.exists(glb_path):
                raise ValueError(f"No valid GLB file returned by Hunyuan3D-2. Raw result: {result}")

            logger.info("GLB generated: %s", glb_path)

            # Copy to final destination
            secure_filename = f"mesh_prod_{product_id}.glb"
            final_destination = os.path.join(OPTIMIZED_DIR, secure_filename)
            shutil.copy(glb_path, final_destination)
            # Normalize Windows backslashes for DB URL
            public_url_path = "/" + final_destination.replace("\\", "/")

            await self.commit_success(product_id, public_url_path)

        except Exception as e:
            logger.error("Hunyuan3D-2 pipeline failed for product %s: %s", product_id, e)

            # If the client seems broken, reset so next product retries fresh
            self._reset_client()

            # Mark as failed with the actual error — DO NOT silently fallback
            await self.mark_as_failed(
                product_id,
                f"Hunyuan3D-2 generation failed: {e}",
            )

    # ------------------------------------------------------------------
    # Result extraction helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_glb_path(result) -> Optional[str]:
        """Walk the Hunyuan3D-2 API result and return the first .glb path found."""
        if result is None:
            return None

        # Single string — could be a path directly
        if isinstance(result, str):
            return result if result.endswith(".glb") else None

        # Dict with a "path" or "value" key (Gradio update format)
        if isinstance(result, dict):
            p = result.get("path") or result.get("value") or result.get("url") or result.get("name")
            if p and isinstance(p, str) and p.endswith(".glb"):
                return p
            # Fall through to treat dict values as iterable
            result = list(result.values())

        # Tuple / list — walk elements
        if isinstance(result, (list, tuple)):
            for item in result:
                if isinstance(item, str) and item.endswith(".glb"):
                    return item
                if isinstance(item, dict):
                    p = item.get("path") or item.get("value") or item.get("url")
                    if p and isinstance(p, str) and p.endswith(".glb"):
                        return p
                # Recurse one level for nested tuples
                if isinstance(item, (list, tuple)):
                    inner = AsikoPipelineDaemon._extract_glb_path(item)
                    if inner:
                        return inner
            # If no .glb found, try the first file-like path anyway
            for item in result:
                if isinstance(item, str) and os.path.exists(item):
                    return item
                if isinstance(item, dict):
                    p = item.get("path") or item.get("value")
                    if p and isinstance(p, str) and os.path.exists(p):
                        return p

        return None

    # ------------------------------------------------------------------
    # DB commit helpers
    # ------------------------------------------------------------------
    async def commit_success(self, product_id, public_url_path):
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE products SET pipeline_status = 'completed', "
                "model_3d_url = $1, pipeline_error_log = NULL WHERE id = $2;",
                public_url_path, product_id,
            )
        logger.info("Product %s marked completed.", product_id)
        await self._notify_pipeline_update(product_id, "completed", public_url_path)

    async def mark_as_failed(self, product_id, error_message):
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE products SET pipeline_status = 'failed', "
                "pipeline_error_log = $1 WHERE id = $2;",
                error_message, product_id,
            )
        logger.warning("Product %s marked failed: %s", product_id, error_message)
        await self._notify_pipeline_update(product_id, "failed")
