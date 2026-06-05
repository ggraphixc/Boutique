# ASIKO Boutique - HTMX Cart Session Operations (Variant-Based)
# Session schema: {"lines": [...], "total": float, "item_count": int}

from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.routing import Route

from app.core import templates, get_cart_from_session, save_cart_to_session


def _recalculate_cart(cart: dict) -> dict:
    """Recalculate rolling aggregate metrics across all active session lines."""
    total = 0.0
    item_count = 0
    for line in cart.get("lines", []):
        total += float(line["price"]) * int(line["quantity"])
        item_count += int(line["quantity"])
    cart["total"] = total
    cart["item_count"] = item_count
    return cart


async def cart_add(request: Request) -> HTMLResponse:
    """
    Validates on-hand stock via product_variants and injects into session.
    Returns the isolated cart counter badge partial via HTMX.
    """
    if request.method != "POST":
        return HTMLResponse("Method Not Allowed", status_code=405)

    form_data = await request.form()
    variant_id = form_data.get("variant_id")
    quantity = int(form_data.get("quantity", 1))

    if not variant_id:
        return HTMLResponse("Missing Variant Pointer Identifier", status_code=400)

    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        variant = await conn.fetchrow(
            """
            SELECT v.id, v.size, v.color, v.stock_qty,
                   p.id AS product_id, p.name, p.price, p.base_image
            FROM product_variants v
            JOIN products p ON v.product_id = p.id
            WHERE v.id = $1
            """,
            variant_id,
        )

        if not variant:
            return HTMLResponse(
                "<span class='text-xs text-red-500 font-mono'>Item Variant Obliterated</span>",
                status_code=404,
            )

        cart = get_cart_from_session(request)

        existing_line = next(
            (line for line in cart["lines"] if line["variant_id"] == str(variant["id"])),
            None,
        )
        staged_qty = existing_line["quantity"] if existing_line else 0
        target_total_qty = staged_qty + quantity

        if variant["stock_qty"] < target_total_qty:
            return HTMLResponse(
                f"<div id='cart-error' hx-swap-oob='true' class='text-xs font-mono text-[#EF4444]'>"
                f"Atelier allocation cap reached ({variant['stock_qty']} available).</div>",
                status_code=400,
            )

        if existing_line:
            existing_line["quantity"] = target_total_qty
        else:
            cart["lines"].append({
                "variant_id": str(variant["id"]),
                "product_id": str(variant["product_id"]),
                "name": variant["name"],
                "price": float(variant["price"]),
                "quantity": quantity,
                "size": variant["size"],
                "color": variant["color"],
                "image_url": variant["base_image"],
            })

    cart = _recalculate_cart(cart)
    save_cart_to_session(request, cart)

    context = {"request": request, "cart": cart}
    return templates.TemplateResponse(request, "cart/cart_badge.html", context)


async def cart_update(request: Request) -> HTMLResponse:
    """
    Handles increment/decrement/remove actions and renders the cart drawer.
    Validates stock on increment via product_variants.
    """
    form_data = await request.form()
    variant_id = form_data.get("variant_id")
    action = form_data.get("action")

    cart = get_cart_from_session(request)
    existing_line = next(
        (line for line in cart["lines"] if line["variant_id"] == variant_id), None
    )

    if existing_line:
        if action == "increment":
            pool = request.app.state.db_pool
            async with pool.acquire() as conn:
                stock_qty = await conn.fetchval(
                    "SELECT stock_qty FROM product_variants WHERE id = $1;",
                    variant_id,
                )
                if stock_qty is not None and existing_line["quantity"] < stock_qty:
                    existing_line["quantity"] += 1
        elif action == "decrement":
            existing_line["quantity"] -= 1
            if existing_line["quantity"] <= 0:
                cart["lines"].remove(existing_line)
        elif action == "remove":
            cart["lines"].remove(existing_line)

    cart = _recalculate_cart(cart)
    save_cart_to_session(request, cart)

    context = {"request": request, "cart": cart}
    return templates.TemplateResponse(request, "cart/cart_content.html", context)


async def cart_drawer(request: Request) -> HTMLResponse:
    """GET handler rendering current cart state within the drawer sidebar."""
    cart = get_cart_from_session(request)
    context = {"request": request, "cart": cart}
    return templates.TemplateResponse(request, "cart/cart_content.html", context)


routes = [
    Route("/cart/add", endpoint=cart_add, methods=["POST"]),
    Route("/cart/update", endpoint=cart_update, methods=["POST"]),
    Route("/cart/drawer", endpoint=cart_drawer, methods=["GET"]),
]
