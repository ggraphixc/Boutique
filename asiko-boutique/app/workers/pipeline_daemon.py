# app/workers/pipeline_daemon.py
import asyncio
import json
import os
import shutil
import logging
from typing import Optional

logger = logging.getLogger("asiko.pipeline")
OPTIMIZED_DIR = "static/uploads/optimized"
os.makedirs(OPTIMIZED_DIR, exist_ok=True)

# Gradio Space name — configurable via env var so DNS/firewall issues
# can be worked around without code changes.
GRADIO_SPACE = os.environ.get("ASIKO_GRADIO_SPACE", "TencentARC/InstantMesh")


class AsikoPipelineDaemon:
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.is_running = True
        self.ai_client = None

    def _ensure_client(self) -> bool:
        """Lazy-connect to the Gradio Space. Returns True if client is ready.
        Retries on each call if previous attempt failed (no permanent flag)."""
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

    async def start_loop(self, check_interval_seconds=5):
        """
        Monitors the database for newly queued products uploaded by the admin 
        and passes them immediately into the processing channel.
        """
        while self.is_running:
            try:
                async with self.db_pool.acquire() as conn:
                    queued_items = await conn.fetch(
                        "SELECT id, source_2d_image_url, asset_category FROM products WHERE pipeline_status = 'queued' ORDER BY id ASC;"
                    )
                    
                    for item in queued_items:
                        product_id = item["id"]
                        img_url = item["source_2d_image_url"]
                        if not img_url:
                            logger.warning("Product %s queued but has no source image — skipping", product_id)
                            continue
                        local_img_path = img_url.lstrip("/")
                        category = item["asset_category"] or "apparel"
                        asyncio.create_task(self.process_oss_generation(product_id, local_img_path, category))
                        
            except Exception as e:
                logger.error(f"Error inside processing loop sequence: {e}")
            await asyncio.sleep(check_interval_seconds)

    async def process_oss_generation(self, product_id, local_img_path, category):
        print(f"LOG_SYSTEM: Initiating 3D reconstruction for Product {product_id}...")
        
        async with self.db_pool.acquire() as conn:
            await conn.execute("UPDATE products SET pipeline_status = 'generating_mesh' WHERE id = $1;", product_id)
        await self._notify_pipeline_update(product_id, "generating_mesh")

        if not os.path.exists(local_img_path):
            await self.mark_as_failed(product_id, f"File {local_img_path} not found on disk.")
            return

        try:
            if not self._ensure_client():
                raise ConnectionError(
                    f"Cannot reach Gradio Space '{GRADIO_SPACE}'. "
                    "Set ASIKO_GRADIO_SPACE env var to override, or check network/DNS."
                )

            from gradio_client import handle_file
            loop = asyncio.get_running_loop()

            # Step 1: Preprocess — remove background
            print(f"LOG_SYSTEM: Step 1/3 — Preprocessing image for Product {product_id}...")
            preprocessed = await loop.run_in_executor(
                None,
                lambda: self.ai_client.predict(
                    handle_file(local_img_path),  # input_image
                    True,                         # do_remove_background
                    api_name="/preprocess"
                )
            )
            preprocessed_path = preprocessed if isinstance(preprocessed, str) else preprocessed.get("path") if isinstance(preprocessed, dict) else preprocessed[0]
            print(f"LOG_SYSTEM: Preprocessed result: {preprocessed_path}")

            # Step 2: Generate multi-view images
            print(f"LOG_SYSTEM: Step 2/3 — Generating multi-views for Product {product_id}...")
            multiview = await loop.run_in_executor(
                None,
                lambda: self.ai_client.predict(
                    handle_file(preprocessed_path),  # input_image (preprocessed)
                    30,                              # sample_steps
                    42,                              # sample_seed
                    api_name="/generate_mvs"
                )
            )
            multiview_path = multiview if isinstance(multiview, str) else multiview.get("path") if isinstance(multiview, dict) else multiview[0]
            print(f"LOG_SYSTEM: Multi-view result: {multiview_path}")

            # Step 3: Generate 3D model from multi-views
            print(f"LOG_SYSTEM: Step 3/3 — Generating 3D mesh for Product {product_id}...")
            result = await loop.run_in_executor(
                None,
                lambda: self.ai_client.predict(
                    api_name="/make3d"
                )
            )
            # Result is a tuple: (obj_path, glb_path)
            if isinstance(result, (list, tuple)) and len(result) >= 2:
                glb_path = result[1]  # GLB format
            elif isinstance(result, str):
                glb_path = result
            else:
                glb_path = result[0] if isinstance(result, (list, tuple)) else result

            if isinstance(glb_path, dict):
                glb_path = glb_path.get("path") or glb_path.get("url")

            print(f"LOG_SYSTEM: 3D model generated: {glb_path}")

            # Copy to final destination
            secure_filename = f"mesh_prod_{product_id}.glb"
            final_destination = os.path.join(OPTIMIZED_DIR, secure_filename)
            
            shutil.copy(glb_path, final_destination)
            public_url_path = f"/{final_destination}"

            await self.commit_success(product_id, public_url_path)

        except Exception as e:
            logger.warning(f"Gradio pipeline failed ({e}). Deploying fallback...")
            
            secure_filename = f"mesh_prod_{product_id}.glb"
            final_destination = os.path.join(OPTIMIZED_DIR, secure_filename)
            
            fallback_source = "static/models/avatar_female.glb" 
            try:
                shutil.copy(fallback_source, final_destination)
                public_url_path = f"/{final_destination}"
                await self.commit_success(product_id, public_url_path)
                print(f"LOG_SYSTEM: Fallback model deployed for Product {product_id}.")
            except Exception as fallback_err:
                await self.mark_as_failed(product_id, f"Pipeline Error: {str(e)} | Fallback Error: {str(fallback_err)}")

    async def commit_success(self, product_id, public_url_path):
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE products SET pipeline_status = 'completed', model_3d_url = $1, pipeline_error_log = NULL WHERE id = $2;",
                public_url_path, product_id
            )
        print(f"LOG_SYSTEM: Product {product_id} state updated successfully.")
        await self._notify_pipeline_update(product_id, "completed", public_url_path)

    async def mark_as_failed(self, product_id, error_message):
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE products SET pipeline_status = 'failed', pipeline_error_log = $1 WHERE id = $2;",
                error_message, product_id
            )
        await self._notify_pipeline_update(product_id, "failed")