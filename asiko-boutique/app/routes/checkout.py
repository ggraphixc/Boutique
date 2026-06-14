# ASIKO Boutique - Checkout & Shipping Routes (Atomic Transactions)
# DB-backed 36-state matrix, SELECT FOR UPDATE stock validation, Brevo dispatch.
# OPay payment initialization for Nigerian bank transfer + card payments.

import json
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, JSONResponse
from starlette.routing import Route

from app.core import templates, get_cart_from_session, save_cart_to_session
from app.services.brevo import send_transactional_email
from app.services.settlement import initialize_payment


async def checkout_page(request: Request) -> HTMLResponse:
    """Render checkout with 36-state shipping dropdown from nigerian_states."""
    cart = get_cart_from_session(request)
    if not cart.get("lines"):
        return RedirectResponse("/", status_code=302)

    pool = request.app.state.db_pool
    settings = await get_settings(pool)
    async with pool.acquire() as conn:
        states_raw = await conn.fetch(
            "SELECT code, name, shipping_cost FROM nigerian_states ORDER BY name ASC"
        )

    context = {
        "request": request,
        "cart": cart,
        "states": [dict(s) for s in states_raw],
        "settings": settings,
    }
    return templates.TemplateResponse(request, "checkout/index.html", context)


async def shipping_summary(request: Request) -> HTMLResponse:
    """HTMX endpoint: dynamically compute shipping cost based on state selection."""
    state_code = request.query_params.get("state")
    cart = get_cart_from_session(request)

    shipping_cost = 0.0
    state_name = "Unselected"

    if state_code:
        pool = request.app.state.db_pool
        async with pool.acquire() as conn:
            state_row = await conn.fetchrow(
                "SELECT name, shipping_cost FROM nigerian_states WHERE code = $1;",
                state_code,
            )
            if state_row:
                shipping_cost = float(state_row["shipping_cost"])
                state_name = state_row["name"]

    grand_total = float(cart.get("total", 0.0)) + shipping_cost

    context = {
        "request": request,
        "shipping_cost": shipping_cost,
        "state_name": state_name,
        "grand_total": grand_total,
        "cart": cart,
    }
    return templates.TemplateResponse(request, "checkout/shipping_summary.html", context)


async def checkout_submit(request: Request) -> HTMLResponse:
    """
    Transactional gateway: SELECT FOR UPDATE stock validation, atomic order creation,
    stock decrement, OPay initialization, Brevo email dispatch with graceful fallback.
    """
    form_data = await request.form()
    first_name = form_data.get("first_name", "").strip()
    last_name = form_data.get("last_name", "").strip()
    email = form_data.get("email", "").strip()
    phone = form_data.get("phone", "").strip()
    address = form_data.get("address", "").strip()
    state_code = form_data.get("state", "").strip()

    if not all([first_name, last_name, email, phone, address, state_code]):
        return HTMLResponse(
            "<div class='p-4 text-xs font-mono text-[#EF4444] bg-[#FBF9F6]'>"
            "Required checkout entries are incomplete.</div>",
            status_code=400,
        )

    cart = get_cart_from_session(request)
    if not cart.get("lines"):
        return HTMLResponse(
            "<div class='p-4 text-xs font-mono text-[#EF4444] bg-[#FBF9F6]'>"
            "Your shopping bag contains no selectable assets.</div>",
            status_code=400,
        )

    pool = request.app.state.db_pool

    try:
        async with pool.acquire() as conn:
            # Resolve shipping cost from nigerian_states
            state_row = await conn.fetchrow(
                "SELECT name, shipping_cost FROM nigerian_states WHERE code = $1;",
                state_code,
            )
            if not state_row:
                return HTMLResponse(
                    "<div class='p-4 text-xs font-mono text-[#EF4444] bg-[#FBF9F6]'>"
                    "Invalid regional logistics target selected.</div>",
                    status_code=400,
                )

            shipping_cost = float(state_row["shipping_cost"])
            subtotal = float(cart.get("total", 0.0))
            grand_total = subtotal + shipping_cost

            metadata_payload = {
                "customer_name": f"{first_name} {last_name}",
                "phone": phone,
                "address": address,
                "state": state_row["name"],
            }

            # Atomic transaction with SELECT FOR UPDATE row locking
            async with conn.transaction():
                # Pre-flight inventory checks with row-level locks
                for line in cart["lines"]:
                    variant_id = line["variant_id"]
                    req_qty = int(line["quantity"])

                    current_stock = await conn.fetchval(
                        "SELECT stock_qty FROM product_variants WHERE id = $1 FOR UPDATE;",
                        variant_id,
                    )

                    if current_stock is None or current_stock < req_qty:
                        return HTMLResponse(
                            f"<div class='p-4 text-xs font-mono text-[#EF4444] bg-[#FBF9F6]'>"
                            f"Allocation clash: '{line['name']}' has insufficient stock.</div>",
                            status_code=400,
                        )

                # Create order record
                order_id = await conn.fetchval(
                    """
                    INSERT INTO orders (total_amount, shipping_cost, status, customer_email, metadata)
                    VALUES ($1, $2, 'pending', $3, $4)
                    RETURNING id
                    """,
                    grand_total, shipping_cost, email, json.dumps(metadata_payload),
                )

                # Create order items and decrement stock
                for line in cart["lines"]:
                    await conn.execute(
                        """
                        INSERT INTO order_items (order_id, product_id, quantity, price)
                        VALUES ($1, $2, $3, $4)
                        """,
                        order_id, line["product_id"], line["quantity"], line["price"],
                    )

                    await conn.execute(
                        "UPDATE product_variants SET stock_qty = stock_qty - $1 WHERE id = $2;",
                        line["quantity"], line["variant_id"],
                    )

        # Initialize OPay payment
        amount_kobo = int(grand_total * 100)  # Convert to kobo
        opay_result = await initialize_payment(
            email=email,
            amount_kobo=amount_kobo,
            order_id=str(order_id),
            customer_name=f"{first_name} {last_name}",
            metadata=metadata_payload,
        )

        if "error" in opay_result:
            request.session["last_order_id"] = str(order_id)
            request.session["payment_error"] = opay_result["error"]
            return RedirectResponse(url="/checkout/confirmation?success=Order+placed+successfully!", status_code=302)

        # Store OPay reference in session for verification
        request.session["last_order_id"] = str(order_id)
        request.session["opay_reference"] = opay_result["reference"]

        # Flush cart after successful transaction
        cart["lines"] = []
        cart["total"] = 0.0
        cart["item_count"] = 0
        save_cart_to_session(request, cart)

        # Brevo email dispatch with graceful fallback
        try:
            email_body = (
                f"<h3>Order #{order_id} Confirmed</h3>"
                f"<p>Thank you {first_name}. Your fashion order total is "
                f"₦{grand_total:,.2f}. Outbound logistics route: {state_row['name']}.</p>"
            )
            await send_transactional_email(
                to_email=email,
                subject=f"ASIKO Boutique Confirmation - Order #{order_id}",
                html_content=email_body,
            )
        except Exception:
            pass  # Suppress failures from missing/placeholder API keys

        # Redirect to OPay payment page
        return RedirectResponse(url=opay_result["authorization_url"], status_code=302)

    except Exception as exc:
        return HTMLResponse(
            f"<div class='p-4 text-xs font-mono text-[#EF4444] bg-[#FBF9F6]'>"
            f"System error processing checkout sequence: {str(exc)}</div>",
            status_code=500,
        )


async def checkout_confirmation(request: Request) -> HTMLResponse:
    """Render order confirmation from session-stored order_id."""
    order_id = request.session.get("last_order_id")
    if not order_id:
        return RedirectResponse("/?error=Checkout+failed", status_code=302)

    pool = request.app.state.db_pool
    settings = await get_settings(pool)
    context = {
        "request": request,
        "order_id": order_id,
        "settings": settings,
    }
    return templates.TemplateResponse(request, "checkout/confirmation.html", context)


routes = [
    Route("/checkout", endpoint=checkout_page, methods=["GET"]),
    Route("/checkout/shipping-summary", endpoint=shipping_summary, methods=["GET"]),
    Route("/checkout/submit", endpoint=checkout_submit, methods=["POST"]),
    Route("/checkout/confirmation", endpoint=checkout_confirmation, methods=["GET"]),
]
