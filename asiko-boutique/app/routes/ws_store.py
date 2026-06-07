# ASIKO Boutique - Public Store WebSocket Endpoints
# HTMX hx-ext="ws" connects to these for real-time PDP updates.
# Review stats + stock availability pushed to product pages live.

import json
import logging

from starlette.requests import Request
from starlette.websockets import WebSocket, WebSocketDisconnect
from starlette.routing import Route

from app.realtime import (
    manager,
    CH_NEW_REVIEW,
    CH_STOCK_UPDATE,
)

logger = logging.getLogger("asiko.ws.store")


def _render_pdp_review_fragment(payload: dict) -> str:
    """Render the review summary for a product detail page."""
    from jinja2 import Template

    tmpl = Template("""
<div id="pdp-review-{{ pid }}" class="flex items-center gap-2 text-sm">
    <div class="flex items-center gap-0.5 text-amber-400">
        {% for i in range(5) %}
            {% if avg and i < avg|int %}
                <svg class="w-4 h-4 fill-current" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118L10 13.347l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L3.567 7.82c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>
            {% else %}
                <svg class="w-4 h-4 fill-current text-gray-200" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118L10 13.347l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L3.567 7.82c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>
            {% endif %}
        {% endfor %}
    </div>
    <span class="text-gray-500">{{ avg }}</span>
    <span class="text-gray-400">({{ count }} reviews)</span>
</div>
    """)
    return tmpl.render(
        pid=payload.get("product_id", ""),
        avg=payload.get("rating_avg", 0),
        count=payload.get("total_reviews", 0),
    )


def _render_stock_badge_fragment(payload: dict) -> str:
    """Render the stock availability badge for a product detail page."""
    from jinja2 import Template

    stock = payload.get("stock", 0)
    in_stock = stock > 0

    tmpl = Template("""
<div id="pdp-stock-{{ pid }}" class="flex items-center gap-2">
    {% if in_stock %}
        <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            In Stock ({{ stock }} available)
        </span>
    {% else %}
        <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-red-50 text-red-700">
            <span class="w-1.5 h-1.5 rounded-full bg-red-500"></span>
            Out of Stock
        </span>
    {% endif %}
</div>
    """)
    return tmpl.render(pid=payload.get("product_id", ""), stock=stock, in_stock=in_stock)


# ---------------------------------------------------------------------------
# WS Endpoints
# ---------------------------------------------------------------------------

async def ws_store_product(request: Request) -> None:
    """
    WebSocket endpoint for a single product's real-time updates.
    URL: /ws/store/product/{product_id}
    Subscribes to: new_review, stock_update (filtered by product_id).
    Pushes HTML fragments for PDP review stats + stock badge.
    """
    product_id = request.path_params.get("product_id", "")
    ws: WebSocket = request.scope["ws"]
    channels = [CH_NEW_REVIEW, CH_STOCK_UPDATE]

    await manager.connect(ws, channels)
    try:
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("action") == "ping":
                    await ws.send_text(json.dumps({"type": "pong"}))
            except (json.JSONDecodeError, TypeError):
                pass
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.debug("Store product WS closed: %s", exc)
    finally:
        await manager.disconnect(ws, channels)


# ---------------------------------------------------------------------------
# Route list
# ---------------------------------------------------------------------------

ws_store_routes = [
    Route("/ws/store/product/{product_id}", endpoint=ws_store_product),
]
