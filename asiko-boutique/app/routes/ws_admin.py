# ASIKO Boutique - Admin WebSocket Endpoints
# HTMX hx-ext="ws" connects to these endpoints for real-time updates.
# Each endpoint accepts the WS, subscribes to relevant channels,
# and pushes pre-rendered HTML fragments when NOTIFY events arrive.

import json
import logging
from typing import List

from starlette.requests import Request
from starlette.websockets import WebSocket, WebSocketDisconnect
from starlette.routing import Route, WebSocketRoute

from app.realtime import (
    manager,
    CH_NEW_REVIEW,
    CH_NEW_ORDER,
)

logger = logging.getLogger("asiko.ws.admin")


def _render_dashboard_kpi_fragment(request: Request, payload: dict) -> str:
    """
    Render a small HTML fragment for the dashboard KPI update.
    Called from the WS message handler; the fragment is sent back
    to the client which swaps it into the DOM via htmx.
    """
    from jinja2 import Template

    kpi_type = payload.get("kpi", "")
    value = payload.get("value", 0)
    delta = payload.get("delta", "")

    # Map KPI type to display properties
    templates_map = {
        "total_sales": {"label": "Total Sales", "prefix": "$", "color": "blue"},
        "orders": {"label": "Orders", "prefix": "", "color": "emerald"},
        "reviews": {"label": "Reviews", "prefix": "", "color": "purple"},
        "active_users": {"label": "Active Users", "prefix": "", "color": "amber"},
    }

    props = templates_map.get(kpi_type, {"label": kpi_type, "prefix": "", "color": "gray"})

    tmpl = Template("""
<div id="kpi-{{ kpi_type }}" class="bg-white dark:bg-[#111114] rounded-xl border border-gray-200 dark:border-gray-800 shadow-card p-5 hover:shadow-card-hover transition-shadow">
    <div class="flex items-center justify-between">
        <div class="text-sm font-medium text-gray-500 dark:text-gray-400">{{ label }}</div>
        {% if delta %}<span class="text-xs font-medium text-emerald-600">{{ delta }}</span>{% endif %}
    </div>
    <div class="text-2xl font-bold text-gray-900 dark:text-gray-100 mt-1">{{ prefix }}{{ value }}</div>
</div>
    """)
    return tmpl.render(kpi_type=kpi_type, label=props["label"], prefix=props["prefix"],
                       value=value, delta=delta)


def _render_activity_item(payload: dict) -> str:
    """Render a single activity feed item as an HTML fragment."""
    from jinja2 import Template

    tmpl = Template("""
<div class="flex items-start gap-3 py-3 border-b border-gray-100 dark:border-gray-800 last:border-0" id="activity-new">
    <div class="w-8 h-8 rounded-full bg-{{ color }}-50 text-{{ color }}-600 flex items-center justify-center flex-shrink-0">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="{{ icon }}"/>
        </svg>
    </div>
    <div class="flex-1 min-w-0">
        <div class="text-sm text-gray-900 dark:text-gray-100">{{ title }}</div>
        <div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{{ detail }}</div>
    </div>
    <div class="text-xs text-gray-400 dark:text-gray-500 flex-shrink-0">just now</div>
</div>
    """)
    return tmpl.render(
        color=payload.get("color", "blue"),
        icon=payload.get("icon", "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"),
        title=payload.get("title", "New activity"),
        detail=payload.get("detail", ""),
    )


def _render_review_summary_fragment(payload: dict) -> str:
    """Render the review stats summary fragment (average, count, needs response)."""
    from jinja2 import Template

    tmpl = Template("""
<div id="review-summary" class="grid grid-cols-1 md:grid-cols-4 gap-5">
    <div class="bg-white dark:bg-[#111114] rounded-xl border border-gray-200 dark:border-gray-800 p-5">
        <div class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider font-semibold">Average rating</div>
        <div class="mt-2 flex items-baseline gap-1.5">
            <span class="text-3xl font-semibold text-gray-900 dark:text-gray-100">{{ avg }}</span>
            <span class="text-sm text-gray-500 dark:text-gray-400">/ 5</span>
        </div>
    </div>
    <div class="bg-white dark:bg-[#111114] rounded-xl border border-gray-200 dark:border-gray-800 p-5">
        <div class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider font-semibold">Total reviews</div>
        <div class="text-3xl font-semibold text-gray-900 dark:text-gray-100 mt-2">{{ total }}</div>
    </div>
    <div class="bg-white dark:bg-[#111114] rounded-xl border border-gray-200 dark:border-gray-800 p-5">
        <div class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider font-semibold">5-star reviews</div>
        <div class="text-3xl font-semibold text-amber-500 mt-2">{{ five_star }}</div>
    </div>
    <div class="bg-white dark:bg-[#111114] rounded-xl border border-gray-200 dark:border-gray-800 p-5">
        <div class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider font-semibold">Needs response</div>
        <div class="text-3xl font-semibold text-orange-500 mt-2">{{ needs_response }}</div>
    </div>
</div>
    """)
    return tmpl.render(
        avg=payload.get("rating_avg", "—"),
        total=payload.get("total_reviews", 0),
        five_star=payload.get("five_star_count", 0),
        needs_response=payload.get("needs_response", 0),
    )


# ---------------------------------------------------------------------------
# WS Endpoints
# ---------------------------------------------------------------------------

async def ws_admin_dashboard(ws: WebSocket) -> None:
    """
    WebSocket endpoint for the admin dashboard.
    Subscribes to: new_order, new_review, pipeline_update.
    Pushes pre-rendered HTML fragments for HTMX to swap.
    """
    channels = [CH_NEW_ORDER, CH_NEW_REVIEW]

    await manager.connect(ws, channels)
    try:
        while True:
            # Keep connection alive; receive pings or client messages
            data = await ws.receive_text()
            # Client can send {"action": "ping"} for keepalive
            try:
                msg = json.loads(data)
                if msg.get("action") == "ping":
                    await ws.send_text(json.dumps({"type": "pong"}))
            except (json.JSONDecodeError, TypeError):
                pass
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.debug("Admin dashboard WS closed: %s", exc)
    finally:
        await manager.disconnect(ws, channels)


async def ws_admin_reviews(ws: WebSocket) -> None:
    """
    WebSocket endpoint for admin review notifications.
    Subscribes to: new_review.
    Pushes the updated review summary stats fragment.
    """
    channels = [CH_NEW_REVIEW]

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
        logger.debug("Admin reviews WS closed: %s", exc)
    finally:
        await manager.disconnect(ws, channels)


# ---------------------------------------------------------------------------
# Route list
# ---------------------------------------------------------------------------

ws_admin_routes = [
    WebSocketRoute("/ws/admin/dashboard", endpoint=ws_admin_dashboard),
    WebSocketRoute("/ws/admin/reviews", endpoint=ws_admin_reviews),
]
