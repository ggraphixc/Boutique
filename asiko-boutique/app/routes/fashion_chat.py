# app/routes/fashion_chat.py
# AI Fashion Assistant — Chat, Recommendations, Event Styling, Color Analysis

import json
import logging
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.fashion_ai import (
    style_assistant_chat,
    get_recommendations,
    get_event_styling,
    list_events,
    analyze_wardrobe,
    suggest_outfit_from_wardrobe,
)
from app.color_analysis import (
    analyze_skin_from_photo,
    get_color_recommendations,
    analyze_outfit_colors,
    suggest_complementary_outfit,
    extract_dominant_colors,
)
from app.settings_service import get_settings

logger = logging.getLogger("asiko.fashion_chat")


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

async def chat_endpoint(request: Request) -> JSONResponse:
    """POST /api/fashion/chat — Send a message to the style assistant."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    message = (body.get("message") or "").strip()
    if not message:
        return JSONResponse({"error": "Message is required"}, status_code=400)

    session_id = request.session.get("sid")
    customer_id = request.session.get("customer_id")

    settings = await get_settings(request.app.state.db_pool)

    result = await style_assistant_chat(
        request.app.state.db_pool,
        message=message,
        session_id=session_id,
        customer_id=customer_id,
        settings=settings,
    )

    # Serialize products for JSON
    products = []
    for p in result.get("products", []):
        products.append({
            "id": str(p["id"]),
            "name": p["name"],
            "price": float(p["price"]),
            "price_fmt": f"₦{float(p['price']):,.0f}",
            "image": p.get("base_image", ""),
            "category": p.get("category_name", ""),
        })

    return JSONResponse({
        "response": result["response"],
        "products": products,
        "intent": result.get("intent", {}),
    })


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

async def recommendations_endpoint(request: Request) -> JSONResponse:
    """GET /api/fashion/recommendations — Get personalized product recommendations."""
    session_id = request.session.get("sid")
    customer_id = request.session.get("customer_id")
    occasion = request.query_params.get("occasion")
    limit = int(request.query_params.get("limit", "8"))

    products = await get_recommendations(
        request.app.state.db_pool,
        session_id=session_id,
        customer_id=customer_id,
        occasion=occasion,
        limit=limit,
    )

    items = []
    for p in products:
        items.append({
            "id": str(p["id"]),
            "name": p["name"],
            "price": float(p["price"]),
            "price_fmt": f"₦{float(p['price']):,.0f}",
            "image": p.get("base_image", ""),
            "category": p.get("category_name", ""),
            "score": p.get("score", 0),
        })

    return JSONResponse({"products": items, "count": len(items)})


# ---------------------------------------------------------------------------
# Event Styling
# ---------------------------------------------------------------------------

async def events_list_endpoint(request: Request) -> JSONResponse:
    """GET /api/fashion/events — List all style events."""
    events = await list_events(request.app.state.db_pool)
    items = []
    for e in events:
        items.append({
            "id": str(e["id"]),
            "name": e["name"],
            "slug": e["slug"],
            "description": e.get("description", ""),
            "dress_code": e.get("dress_code", ""),
            "icon": e.get("icon", e.get("slug", "")),
            "recommended_categories": e.get("recommended_categories", []),
            "recommended_fabrics": e.get("recommended_fabrics", []),
            "recommended_colors": e.get("recommended_colors", []),
        })
    return JSONResponse({"events": items})


async def event_styling_endpoint(request: Request) -> JSONResponse:
    """GET /api/fashion/events/{slug} — Get styling for a specific event."""
    slug = request.path_params["slug"]
    result = await get_event_styling(request.app.state.db_pool, slug)

    if "error" in result:
        return JSONResponse(result, status_code=404)

    products = []
    for p in result.get("products", []):
        products.append({
            "id": str(p["id"]),
            "name": p["name"],
            "price": float(p["price"]),
            "price_fmt": f"₦{float(p['price']):,.0f}",
            "image": p.get("base_image", ""),
            "category": p.get("category_name", ""),
        })

    return JSONResponse({
        "event": {
            "name": result["name"],
            "slug": result["slug"],
            "description": result.get("description", ""),
            "dress_code": result.get("dress_code", ""),
            "recommended_categories": result.get("recommended_categories", []),
            "recommended_fabrics": result.get("recommended_fabrics", []),
            "recommended_colors": result.get("recommended_colors", []),
            "avoid_colors": result.get("avoid_colors", []),
            "icon": result.get("icon", result.get("slug", "")),
        },
        "products": products,
    })


# ---------------------------------------------------------------------------
# Color Analysis
# ---------------------------------------------------------------------------

async def color_analyze_photo_endpoint(request: Request) -> JSONResponse:
    """POST /api/fashion/color/analyze-photo — Analyze skin tone from uploaded photo."""
    form = await request.form()
    photo = form.get("photo")

    if not photo:
        return JSONResponse({"error": "Photo is required"}, status_code=400)

    import tempfile, os
    suffix = os.path.splitext(photo.filename or "photo.jpg")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await photo.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = await analyze_skin_from_photo(tmp_path)
        return JSONResponse(result)
    finally:
        os.unlink(tmp_path)


async def color_recommendations_endpoint(request: Request) -> JSONResponse:
    """GET /api/fashion/color/recommendations?tone=X&undertone=Y — Get color recommendations."""
    skin_tone = request.query_params.get("tone", "medium")
    undertone = request.query_params.get("undertone", "neutral")
    result = get_color_recommendations(skin_tone, undertone)
    return JSONResponse(result)


async def color_outfit_endpoint(request: Request) -> JSONResponse:
    """POST /api/fashion/color/outfit — Analyze outfit color combination."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    colors = body.get("colors", [])
    if not colors:
        return JSONResponse({"error": "Colors list is required"}, status_code=400)

    result = analyze_outfit_colors(colors)
    return JSONResponse(result)


async def color_complement_endpoint(request: Request) -> JSONResponse:
    """POST /api/fashion/color/complement — Get complementary color suggestions."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    color = body.get("color", "#000000")
    result = suggest_complementary_outfit(color)
    return JSONResponse(result)


async def color_extract_endpoint(request: Request) -> JSONResponse:
    """POST /api/fashion/color/extract — Extract dominant colors from image."""
    form = await request.form()
    photo = form.get("photo")

    if not photo:
        return JSONResponse({"error": "Photo is required"}, status_code=400)

    import tempfile, os
    suffix = os.path.splitext(photo.filename or "photo.jpg")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await photo.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        colors = extract_dominant_colors(tmp_path)
        return JSONResponse({"colors": colors})
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Preferences
# ---------------------------------------------------------------------------

async def save_preferences_endpoint(request: Request) -> JSONResponse:
    """POST /api/fashion/preferences — Save user fashion preferences."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    session_id = request.session.get("sid")
    customer_id = request.session.get("customer_id")

    if not session_id and not customer_id:
        return JSONResponse({"error": "Session required"}, status_code=400)

    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        if customer_id:
            existing = await conn.fetchrow(
                "SELECT id FROM user_preferences WHERE customer_id = $1", customer_id
            )
            if existing:
                await conn.execute(
                    """UPDATE user_preferences SET
                       style_profiles = COALESCE($1, style_profiles),
                       favorite_colors = COALESCE($2, favorite_colors),
                       preferred_fit = COALESCE($3, preferred_fit),
                       occasions = COALESCE($4, occasions),
                       season_preference = COALESCE($5, season_preference),
                       skin_tone = COALESCE($6, skin_tone),
                       skin_undertone = COALESCE($7, skin_undertone),
                       budget_min = COALESCE($8, budget_min),
                       budget_max = COALESCE($9, budget_max),
                       updated_at = NOW()
                       WHERE customer_id = $10""",
                    body.get("style_profiles"),
                    body.get("favorite_colors"),
                    body.get("preferred_fit"),
                    body.get("occasions"),
                    body.get("season_preference"),
                    body.get("skin_tone"),
                    body.get("skin_undertone"),
                    body.get("budget_min"),
                    body.get("budget_max"),
                    customer_id,
                )
            else:
                await conn.execute(
                    """INSERT INTO user_preferences
                       (customer_id, session_id, style_profiles, favorite_colors, preferred_fit,
                        occasions, season_preference, skin_tone, skin_undertone, budget_min, budget_max)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)""",
                    customer_id, session_id,
                    body.get("style_profiles"),
                    body.get("favorite_colors"),
                    body.get("preferred_fit"),
                    body.get("occasions"),
                    body.get("season_preference"),
                    body.get("skin_tone"),
                    body.get("skin_undertone"),
                    body.get("budget_min"),
                    body.get("budget_max"),
                )
        elif session_id:
            existing = await conn.fetchrow(
                "SELECT id FROM user_preferences WHERE session_id = $1", session_id
            )
            if existing:
                await conn.execute(
                    """UPDATE user_preferences SET
                       style_profiles = COALESCE($1, style_profiles),
                       favorite_colors = COALESCE($2, favorite_colors),
                       preferred_fit = COALESCE($3, preferred_fit),
                       occasions = COALESCE($4, occasions),
                       season_preference = COALESCE($5, season_preference),
                       skin_tone = COALESCE($6, skin_tone),
                       skin_undertone = COALESCE($7, skin_undertone),
                       budget_min = COALESCE($8, budget_min),
                       budget_max = COALESCE($9, budget_max),
                       updated_at = NOW()
                       WHERE session_id = $10""",
                    body.get("style_profiles"),
                    body.get("favorite_colors"),
                    body.get("preferred_fit"),
                    body.get("occasions"),
                    body.get("season_preference"),
                    body.get("skin_tone"),
                    body.get("skin_undertone"),
                    body.get("budget_min"),
                    body.get("budget_max"),
                    session_id,
                )
            else:
                await conn.execute(
                    """INSERT INTO user_preferences
                       (session_id, style_profiles, favorite_colors, preferred_fit,
                        occasions, season_preference, skin_tone, skin_undertone, budget_min, budget_max)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)""",
                    session_id,
                    body.get("style_profiles"),
                    body.get("favorite_colors"),
                    body.get("preferred_fit"),
                    body.get("occasions"),
                    body.get("season_preference"),
                    body.get("skin_tone"),
                    body.get("skin_undertone"),
                    body.get("budget_min"),
                    body.get("budget_max"),
                )

    return JSONResponse({"status": "success"})


async def get_preferences_endpoint(request: Request) -> JSONResponse:
    """GET /api/fashion/preferences — Get user fashion preferences."""
    session_id = request.session.get("sid")
    customer_id = request.session.get("customer_id")

    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        if customer_id:
            row = await conn.fetchrow(
                "SELECT * FROM user_preferences WHERE customer_id = $1 ORDER BY updated_at DESC LIMIT 1",
                customer_id,
            )
        elif session_id:
            row = await conn.fetchrow(
                "SELECT * FROM user_preferences WHERE session_id = $1 ORDER BY updated_at DESC LIMIT 1",
                session_id,
            )
        else:
            row = None

    if row:
        return JSONResponse(dict(row))
    return JSONResponse({})


# ---------------------------------------------------------------------------
# Chat History
# ---------------------------------------------------------------------------

async def chat_history_endpoint(request: Request) -> JSONResponse:
    """GET /api/fashion/chat/history — Get recent chat messages."""
    session_id = request.session.get("sid")
    customer_id = request.session.get("customer_id")
    limit = int(request.query_params.get("limit", "20"))

    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        if customer_id:
            rows = await conn.fetch(
                "SELECT role, message, created_at FROM fashion_chat_history WHERE customer_id = $1 ORDER BY created_at DESC LIMIT $2",
                customer_id, limit,
            )
        elif session_id:
            rows = await conn.fetch(
                "SELECT role, message, created_at FROM fashion_chat_history WHERE session_id = $1 ORDER BY created_at DESC LIMIT $2",
                session_id, limit,
            )
        else:
            rows = []

    messages = [{"role": r["role"], "message": r["message"], "created_at": r["created_at"].isoformat()} for r in reversed(rows)]
    return JSONResponse({"messages": messages})


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

routes = [
    Route("/api/fashion/chat", endpoint=chat_endpoint, methods=["POST"]),
    Route("/api/fashion/recommendations", endpoint=recommendations_endpoint, methods=["GET"]),
    Route("/api/fashion/events", endpoint=events_list_endpoint, methods=["GET"]),
    Route("/api/fashion/events/{slug}", endpoint=event_styling_endpoint, methods=["GET"]),
    Route("/api/fashion/color/analyze-photo", endpoint=color_analyze_photo_endpoint, methods=["POST"]),
    Route("/api/fashion/color/recommendations", endpoint=color_recommendations_endpoint, methods=["GET"]),
    Route("/api/fashion/color/outfit", endpoint=color_outfit_endpoint, methods=["POST"]),
    Route("/api/fashion/color/complement", endpoint=color_complement_endpoint, methods=["POST"]),
    Route("/api/fashion/color/extract", endpoint=color_extract_endpoint, methods=["POST"]),
    Route("/api/fashion/preferences", endpoint=save_preferences_endpoint, methods=["POST"]),
    Route("/api/fashion/preferences", endpoint=get_preferences_endpoint, methods=["GET"]),
    Route("/api/fashion/chat/history", endpoint=chat_history_endpoint, methods=["GET"]),
]
