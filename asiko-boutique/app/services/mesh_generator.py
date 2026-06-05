# app/services/mesh_generator.py
import os
import httpx
import logging

logger = logging.getLogger("asiko.mesh_generator")

MESHY_API_URL = "https://api.meshy.ai/v2/3d-from-image"
API_KEY = os.getenv("MESHY_API_KEY", "")

async def initiate_3d_generation_task(image_url: str) -> str:
    """
    Submits a 2D source photo URL to the production 3D AI engine.
    Returns the unique external job tracking ID string.
    """
    if not API_KEY:
        raise ValueError("CRITICAL_CONFIGURATION_ERROR: MESHY_API_KEY environment variable is unassigned.")

    headers = {"Authorization": f"Bearer {API_KEY}"}
    payload = {
        "image_url": image_url,
        "enable_pbr": True,
        "art_style": "realistic",
        "tilt_blend": True
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(MESHY_API_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            # Meshy v2 returns task identifier in the 'result' key
            return data.get("result") or data.get("id")
        except httpx.HTTPStatusError as e:
            logger.error(f"Meshy API Rejected Ingestion Vector: {e.response.text}")
            raise RuntimeError(f"EXTERNAL_API_REFUSAL: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Network transport fault during 3D generation init: {str(e)}")
            raise RuntimeError(f"NETWORK_TRANSPORT_FAILURE: {str(e)}")

async def check_external_task_status(job_id: str) -> dict:
    """
    Polls the active state of an asset generation task from the production endpoint.
    Returns a dict containing 'status', 'model_url' (if complete), and 'error'.
    """
    headers = {"Authorization": f"Bearer {API_KEY}"}
    poll_url = f"{MESHY_API_URL}/{job_id}"

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(poll_url, headers=headers)
            response.raise_for_status()
            data = response.json()

            status_map = data.get("status", "SUCCEEDED") # Fallback to upper matching parameters

            return {
                "status": status_map.lower(), # Normalizes to 'succeeded', 'failed', 'in_progress'
                "model_url": data.get("model_urls", {}).get("glb", ""),
                "error_message": data.get("task_error", {}).get("message", "Unknown synthesis fault.")
            }
        except Exception as e:
            logger.error(f"Failed to poll tracking data boundary for task {job_id}: {str(e)}")
            return {"status": "error", "model_url": "", "error_message": str(e)}