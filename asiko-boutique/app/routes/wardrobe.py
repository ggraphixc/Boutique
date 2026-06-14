# app/routes/wardrobe.py
# Wardrobe AI — CRUD for user wardrobe items, outfit suggestions

import os
import tempfile
import logging
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.fashion_ai import analyze_wardrobe, suggest_outfit_from_wardrobe

logger = logging.getLogger("asiko.wardrobe")


async def wardrobe_list_endpoint(request: Request) -> JSONResponse:
    """GET /api/wardrobe — List user's wardrobe items."""
    session_id = request.session.get("sid")
    customer_id = request.session.get("customer_id")

    if not session_id and not customer_id:
        return JSONResponse({"items": [], "total": 0})

    where = "customer_id = $1" if customer_id else "session_id = $1"
    param = customer_id or session_id

    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT * FROM wardrobe_items WHERE {where} AND is_active = TRUE ORDER BY created_at DESC",
            param,
        )

    _CATEGORY_EMOJI = {
        "dress": "\U0001f457", "shirt": "\U0001f45a", "trouser": "\U0001f456",
        "skirt": "\U0001f459", "jacket": "\U0001f9e5", "hoodie": "\U0001f3a5",
        "shoe": "\U0001f45f", "bag": "\U0001f45c",
    }
    items = []
    for r in rows:
        cat = r["category"]
        items.append({
            "id": str(r["id"]),
            "name": r["name"],
            "category": cat,
            "category_emoji": _CATEGORY_EMOJI.get(cat, "\U0001f457"),
            "subcategory": r.get("subcategory", ""),
            "color_primary": r.get("color_primary", ""),
            "color_hex": r.get("color_hex", ""),
            "color_secondary": r.get("color_secondary", ""),
            "pattern": r.get("pattern", "solid"),
            "fabric": r.get("fabric", ""),
            "season": r.get("season", "all"),
            "occasions": r.get("occasions", []),
            "image_url": r.get("image_url", ""),
            "condition": r.get("condition", "good"),
            "brand": r.get("brand", ""),
            "notes": r.get("notes", ""),
            "created_at": r["created_at"].isoformat(),
        })

    return JSONResponse({"items": items, "total": len(items)})


async def wardrobe_add_endpoint(request: Request) -> JSONResponse:
    """POST /api/wardrobe — Add a wardrobe item."""
    session_id = request.session.get("sid")
    customer_id = request.session.get("customer_id")

    if not session_id and not customer_id:
        return JSONResponse({"error": "Session required"}, status_code=400)

    # Handle both JSON and form data
    content_type = request.headers.get("content-type", "")
    if "multipart" in content_type:
        form = await request.form()
        data = {
            "name": form.get("name", ""),
            "category": form.get("category", ""),
            "subcategory": form.get("subcategory", ""),
            "color_primary": form.get("color_primary", ""),
            "color_hex": form.get("color_hex", ""),
            "color_secondary": form.get("color_secondary", ""),
            "pattern": form.get("pattern", "solid"),
            "fabric": form.get("fabric", ""),
            "season": form.get("season", "all"),
            "occasions": form.get("occasions", "").split(",") if form.get("occasions") else [],
            "condition": form.get("condition", "good"),
            "brand": form.get("brand", ""),
            "notes": form.get("notes", ""),
        }
        photo = form.get("photo")
    else:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)
        data = body
        photo = None

    name = (data.get("name") or "").strip()
    category = (data.get("category") or "").strip()
    if not name or not category:
        return JSONResponse({"error": "Name and category are required"}, status_code=400)

    # Handle photo upload
    image_url = data.get("image_url", "")
    if photo:
        suffix = os.path.splitext(photo.filename or "wardrobe.jpg")[1]
        upload_dir = os.path.join("static", "uploads", "wardrobe")
        os.makedirs(upload_dir, exist_ok=True)
        filepath = os.path.join(upload_dir, f"{session_id or customer_id}_{name[:20].replace(' ', '_')}{suffix}")
        content = await photo.read()
        with open(filepath, "wb") as f:
            f.write(content)
        image_url = "/" + filepath.replace("\\", "/")

    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO wardrobe_items
               (customer_id, session_id, name, category, subcategory, color_primary, color_hex,
                color_secondary, pattern, fabric, season, occasions, image_url, condition, brand, notes)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
               RETURNING id""",
            customer_id, session_id, name, category,
            data.get("subcategory", ""),
            data.get("color_primary", ""),
            data.get("color_hex", ""),
            data.get("color_secondary", ""),
            data.get("pattern", "solid"),
            data.get("fabric", ""),
            data.get("season", "all"),
            data.get("occasions", []),
            image_url,
            data.get("condition", "good"),
            data.get("brand", ""),
            data.get("notes", ""),
        )

    return JSONResponse({"status": "success", "id": str(row["id"])})


async def wardrobe_update_endpoint(request: Request) -> JSONResponse:
    """PUT /api/wardrobe/{item_id} — Update a wardrobe item."""
    item_id = request.path_params["item_id"]
    session_id = request.session.get("sid")
    customer_id = request.session.get("customer_id")

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        # Verify ownership
        where = "customer_id = $1" if customer_id else "session_id = $1"
        param = customer_id or session_id
        existing = await conn.fetchrow(
            f"SELECT id FROM wardrobe_items WHERE id = $2 AND {where}",
            param, item_id,
        )
        if not existing:
            return JSONResponse({"error": "Item not found"}, status_code=404)

        # Build update
        updates = []
        params = []
        idx = 1
        for field in ["name", "category", "subcategory", "color_primary", "color_hex",
                       "color_secondary", "pattern", "fabric", "season", "occasions",
                       "condition", "brand", "notes"]:
            if field in body:
                updates.append(f"{field} = ${idx + 1}")
                params.append(body[field])
                idx += 1

        if not updates:
            return JSONResponse({"error": "No fields to update"}, status_code=400)

        updates.append("updated_at = NOW()")
        params.append(item_id)

        await conn.execute(
            f"UPDATE wardrobe_items SET {', '.join(updates)} WHERE id = ${idx + 1}",
            *params,
        )

    return JSONResponse({"status": "success"})


async def wardrobe_delete_endpoint(request: Request) -> JSONResponse:
    """DELETE /api/wardrobe/{item_id} — Soft-delete a wardrobe item."""
    item_id = request.path_params["item_id"]
    session_id = request.session.get("sid")
    customer_id = request.session.get("customer_id")

    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        where = "customer_id = $1" if customer_id else "session_id = $1"
        param = customer_id or session_id
        result = await conn.execute(
            f"UPDATE wardrobe_items SET is_active = FALSE WHERE id = $2 AND {where}",
            param, item_id,
        )

    return JSONResponse({"status": "success"})


async def wardrobe_analyze_endpoint(request: Request) -> JSONResponse:
    """GET /api/wardrobe/analyze — Analyze wardrobe and suggest improvements."""
    session_id = request.session.get("sid")
    customer_id = request.session.get("customer_id")

    if not session_id and not customer_id:
        return JSONResponse({"error": "Session required"}, status_code=400)

    result = await analyze_wardrobe(
        request.app.state.db_pool,
        session_id=session_id,
        customer_id=customer_id,
    )
    return JSONResponse(result)


async def wardrobe_suggest_outfit_endpoint(request: Request) -> JSONResponse:
    """POST /api/wardrobe/suggest-outfit — Suggest outfit from wardrobe for occasion."""
    session_id = request.session.get("sid")
    customer_id = request.session.get("customer_id")

    if not session_id and not customer_id:
        return JSONResponse({"error": "Session required"}, status_code=400)

    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    occasion = body.get("occasion", "casual")
    result = await suggest_outfit_from_wardrobe(
        request.app.state.db_pool,
        occasion=occasion,
        session_id=session_id,
        customer_id=customer_id,
    )

    return JSONResponse(result)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

routes = [
    Route("/api/wardrobe", endpoint=wardrobe_list_endpoint, methods=["GET"]),
    Route("/api/wardrobe", endpoint=wardrobe_add_endpoint, methods=["POST"]),
    Route("/api/wardrobe/{item_id}", endpoint=wardrobe_update_endpoint, methods=["PUT"]),
    Route("/api/wardrobe/{item_id}", endpoint=wardrobe_delete_endpoint, methods=["DELETE"]),
    Route("/api/wardrobe/analyze", endpoint=wardrobe_analyze_endpoint, methods=["GET"]),
    Route("/api/wardrobe/suggest-outfit", endpoint=wardrobe_suggest_outfit_endpoint, methods=["POST"]),
]
