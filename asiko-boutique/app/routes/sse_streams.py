# ASIKO Boutique - Server-Sent Events (SSE) Streams for Real-Time Pipeline Updates

import json
import asyncio
import logging
from starlette.requests import Request
from starlette.responses import StreamingResponse
from starlette.routing import Route

logger = logging.getLogger("asiko.sse")


async def pipeline_status_sse_stream(request: Request):
    """
    Maintains a persistent HTTP connection boundary to push server state modifications 
    directly down to the client view layers in real-time without browser reload polling loops.
    """
    product_id = request.path_params.get("product_id")
    db_pool = request.app.state.db_pool

    async def event_generator():
        last_known_status = None
        
        while True:
            # Check for client disconnect loops before querying
            if await request.is_disconnected():
                break

            async with db_pool.acquire() as conn:
                record = await conn.fetchrow(
                    "SELECT pipeline_status, model_3d_url FROM products WHERE id = $1::UUID;", product_id
                )
                
                if record:
                    current_status = record["pipeline_status"]
                    model_url = record["model_3d_url"] or ""
                    
                    # Only dispatch push updates down the pipeline wire on clear data variance transitions
                    if current_status != last_known_status:
                        last_known_status = current_status
                        payload = {
                            "status": current_status,
                            "product_id": product_id,
                            "model_url": model_url
                        }
                        # Format tracking blocks matching formal text/event-stream parsing matrices
                        yield f"data: {json.dumps(payload)}\n\n"
                        
                        if current_status in ["completed", "failed"]:
                            break
                            
            await asyncio.sleep(2.0)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


sse_routes = [
    Route("/api/v1/streams/pipeline/{product_id:uuid}", endpoint=pipeline_status_sse_stream),
]