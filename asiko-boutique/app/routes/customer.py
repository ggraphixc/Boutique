# ASIKO Boutique — Customer Auth + Dashboard Routes
# Register, login, logout, forgot/reset password, order history, profile.

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.routing import Route

from app.core import templates
from app.settings_service import get_settings


def _hash_password(password: str) -> str:
    """SHA-256 hash with salt. Simple enough for a boutique — not Fort Knox."""
    salt = os.environ.get("AUTH_SALT", "asiko-boutique-salt-2024")
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def _check_password(password: str, password_hash: str) -> bool:
    return hmac.compare_digest(_hash_password(password), password_hash)


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

async def register_page(request: Request) -> HTMLResponse:
    error = request.query_params.get("error", "")
    pool = request.app.state.db_pool
    settings = await get_settings(pool)
    return templates.TemplateResponse(request, "customer/register.html", {
        "request": request,
        "error": error,
        "settings": settings,
    })


async def register_submit(request: Request) -> RedirectResponse:
    form = await request.form()
    email = (form.get("email") or "").strip().lower()
    password = form.get("password") or ""
    full_name = (form.get("full_name") or "").strip()

    if not email or not password:
        return RedirectResponse("/register?error=Email+and+password+are+required", status_code=302)

    if len(password) < 6:
        return RedirectResponse("/register?error=Password+must+be+at+least+6+characters", status_code=302)

    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        existing = await conn.fetchval(
            "SELECT id FROM customers WHERE email = $1", email
        )
        if existing:
            return RedirectResponse("/register?error=An+account+with+this+email+already+exists", status_code=302)

        customer_id = await conn.fetchval(
            "INSERT INTO customers (email, password_hash, full_name) VALUES ($1, $2, $3) RETURNING id",
            email,
            _hash_password(password),
            full_name or email.split("@")[0],
        )

    request.session["customer_id"] = str(customer_id)
    request.session["customer_email"] = email
    request.session["customer_name"] = full_name or email.split("@")[0]

    # Send welcome greeting email (non-blocking)
    try:
        from app.services.brevo import send_welcome_email
        import asyncio
        asyncio.create_task(send_welcome_email(email, full_name or email.split("@")[0]))
    except Exception:
        pass

    return RedirectResponse("/account?success=Account+created+successfully", status_code=302)


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

async def login_page(request: Request) -> HTMLResponse:
    error = request.query_params.get("error", "")
    pool = request.app.state.db_pool
    settings = await get_settings(pool)
    return templates.TemplateResponse(request, "customer/login.html", {
        "request": request,
        "error": error,
        "settings": settings,
    })


async def login_submit(request: Request) -> RedirectResponse:
    form = await request.form()
    email = (form.get("email") or "").strip().lower()
    password = form.get("password") or ""

    if not email or not password:
        return RedirectResponse("/login?error=Email+and+password+are+required", status_code=302)

    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        customer = await conn.fetchrow(
            "SELECT id, password_hash, full_name FROM customers WHERE email = $1",
            email,
        )

    if not customer or not _check_password(password, customer["password_hash"]):
        return RedirectResponse("/login?error=Invalid+email+or+password", status_code=302)

    request.session["customer_id"] = str(customer["id"])
    request.session["customer_email"] = email
    request.session["customer_name"] = customer["full_name"]
    return RedirectResponse("/account?success=Welcome+back!", status_code=302)


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

async def logout(request: Request) -> RedirectResponse:
    request.session.pop("customer_id", None)
    request.session.pop("customer_email", None)
    request.session.pop("customer_name", None)
    return RedirectResponse("/?success=You+have+been+signed+out", status_code=302)


async def customer_dashboard(request: Request) -> HTMLResponse:
    """Customer dashboard: order history, profile, account."""
    # Check if customer is identified (via email in session)
    customer_email = request.session.get("customer_email")
    if not customer_email:
        # Try to get from last order
        pool = request.app.state.db_pool
        async with pool.acquire() as conn:
            last_order_id = request.session.get("last_order_id")
            if last_order_id:
                order = await conn.fetchrow(
                    "SELECT customer_email FROM orders WHERE id = $1",
                    last_order_id,
                )
                if order:
                    customer_email = order["customer_email"]
                    request.session["customer_email"] = customer_email

    if not customer_email:
        return RedirectResponse("/", status_code=302)

    pool = request.app.state.db_pool
    orders = []
    async with pool.acquire() as conn:
        orders = await conn.fetch(
            """
            SELECT o.id, o.total_amount, o.status, o.created_at,
                   o.shipping_cost, o.metadata,
                   COUNT(oi.id) AS item_count
            FROM orders o
            LEFT JOIN order_items oi ON oi.order_id = o.id
            WHERE o.customer_email = $1
            GROUP BY o.id
            ORDER BY o.created_at DESC
            LIMIT 20
            """,
            customer_email,
        )

    # Format orders for display
    formatted_orders = []
    for o in orders:
        import json
        meta = {}
        if o.get("metadata"):
            try:
                meta = json.loads(o["metadata"]) if isinstance(o["metadata"], str) else o["metadata"]
            except Exception:
                meta = {}

        created = o["created_at"].strftime("%d %b %Y") if o["created_at"] else ""
        status_map = {
            "pending": ("Pending", "text-amber-600 bg-amber-50"),
            "paid": ("Paid", "text-emerald-600 bg-emerald-50"),
            "processing": ("Processing", "text-blue-600 bg-blue-50"),
            "shipped": ("Shipped", "text-purple-600 bg-purple-50"),
            "delivered": ("Delivered", "text-emerald-700 bg-emerald-50"),
            "cancelled": ("Cancelled", "text-red-600 bg-red-50"),
        }
        status_label, status_cls = status_map.get(o["status"], ("Unknown", "text-gray-600 bg-gray-50"))

        formatted_orders.append({
            "id": str(o["id"]),
            "total": float(o["total_amount"] or 0),
            "status": status_label,
            "status_cls": status_cls,
            "item_count": o["item_count"],
            "created": created,
            "customer_name": meta.get("customer_name", ""),
            "state": meta.get("state", ""),
        })

    context = {
        "request": request,
        "customer_email": customer_email,
        "orders": formatted_orders,
        "order_count": len(formatted_orders),
        "settings": await get_settings(pool),
    }
    return templates.TemplateResponse(request, "customer/dashboard.html", context)


async def customer_order_detail(request: Request) -> HTMLResponse:
    """Customer order detail page."""
    order_id = request.path_params["order_id"]
    customer_email = request.session.get("customer_email")

    if not customer_email:
        return RedirectResponse("/", status_code=302)

    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        order = await conn.fetchrow(
            """
            SELECT o.id, o.total_amount, o.status, o.created_at,
                   o.shipping_cost, o.metadata, o.customer_email
            FROM orders o
            WHERE o.id = $1 AND o.customer_email = $2
            """,
            order_id,
            customer_email,
        )

        if not order:
            return RedirectResponse("/account", status_code=302)

        items = await conn.fetch(
            """
            SELECT oi.quantity, oi.price, p.name, p.base_image
            FROM order_items oi
            JOIN products p ON p.id = oi.product_id
            WHERE oi.order_id = $1
            """,
            order_id,
        )

    import json
    meta = {}
    if order.get("metadata"):
        try:
            meta = json.loads(order["metadata"]) if isinstance(order["metadata"], str) else order["metadata"]
        except Exception:
            meta = {}

    status_map = {
        "pending": ("Pending", "text-amber-600 bg-amber-50"),
        "paid": ("Paid", "text-emerald-600 bg-emerald-50"),
        "processing": ("Processing", "text-blue-600 bg-blue-50"),
        "shipped": ("Shipped", "text-purple-600 bg-purple-50"),
        "delivered": ("Delivered", "text-emerald-700 bg-emerald-50"),
        "cancelled": ("Cancelled", "text-red-600 bg-red-50"),
    }
    status_label, status_cls = status_map.get(order["status"], ("Unknown", "text-gray-600 bg-gray-50"))

    context = {
        "request": request,
        "order": {
            "id": str(order["id"]),
            "total": float(order["total_amount"] or 0),
            "shipping": float(order["shipping_cost"] or 0),
            "status": status_label,
            "status_cls": status_cls,
            "created": order["created_at"].strftime("%d %b %Y") if order["created_at"] else "",
            "customer_name": meta.get("customer_name", ""),
            "address": meta.get("address", ""),
            "state": meta.get("state", ""),
        },
        "items": [
            {
                "name": i["name"],
                "quantity": i["quantity"],
                "price": float(i["price"] or 0),
                "image": i.get("base_image"),
            }
            for i in items
        ],
    }
    settings = await get_settings(pool)
    context["settings"] = settings
    return templates.TemplateResponse(request, "customer/order_detail.html", context)


# ---------------------------------------------------------------------------
# Forgot Password
# ---------------------------------------------------------------------------

async def forgot_password_page(request: Request) -> HTMLResponse:
    error = request.query_params.get("error", "")
    success = request.query_params.get("success", "")
    pool = request.app.state.db_pool
    settings = await get_settings(pool)
    return templates.TemplateResponse(request, "customer/forgot_password.html", {
        "request": request, "error": error, "success": success, "settings": settings,
    })


async def forgot_password_submit(request: Request) -> RedirectResponse:
    form = await request.form()
    email = (form.get("email") or "").strip().lower()
    if not email:
        return RedirectResponse("/forgot-password?error=Please+enter+your+email", status_code=302)

    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        customer = await conn.fetchrow(
            "SELECT id, full_name FROM customers WHERE email = $1", email
        )

    # Always show success to prevent email enumeration
    if customer:
        token = secrets.token_hex(32)
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).replace(tzinfo=None)
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO password_reset_tokens (customer_id, token, expires_at) VALUES ($1, $2, $3)",
                str(customer["id"]), token, expires_at,
            )
        reset_url = f"{request.base_url}reset-password?token={token}"
        try:
            from app.services.brevo import send_forgot_password_email
            import asyncio
            asyncio.create_task(send_forgot_password_email(email, customer["full_name"] or "Customer", reset_url))
        except Exception:
            pass

    return RedirectResponse("/forgot-password?success=If+an+account+exists+with+that+email,+a+reset+link+has+been+sent", status_code=302)


# ---------------------------------------------------------------------------
# Reset Password
# ---------------------------------------------------------------------------

async def reset_password_page(request: Request) -> HTMLResponse:
    token = request.query_params.get("token", "")
    error = request.query_params.get("error", "")
    if not token:
        return RedirectResponse("/login", status_code=302)
    pool = request.app.state.db_pool
    settings = await get_settings(pool)
    return templates.TemplateResponse(request, "customer/reset_password.html", {
        "request": request, "token": token, "error": error, "settings": settings,
    })


async def reset_password_submit(request: Request) -> RedirectResponse:
    form = await request.form()
    token = form.get("token") or ""
    password = form.get("password") or ""
    confirm = form.get("confirm_password") or ""

    if not token:
        return RedirectResponse("/login", status_code=302)
    if len(password) < 6:
        return RedirectResponse(f"/reset-password?token={token}&error=Password+must+be+at+least+6+characters", status_code=302)
    if password != confirm:
        return RedirectResponse(f"/reset-password?token={token}&error=Passwords+do+not+match", status_code=302)

    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, customer_id, expires_at, used FROM password_reset_tokens WHERE token = $1", token
        )
        if not row or row["used"]:
            return RedirectResponse("/login?error=Invalid+or+expired+reset+link", status_code=302)
        if row["expires_at"].replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            return RedirectResponse("/login?error=Reset+link+has+expired", status_code=302)

        # Update password
        await conn.execute(
            "UPDATE customers SET password_hash = $1 WHERE id = $2",
            _hash_password(password), row["customer_id"],
        )
        # Mark token used
        await conn.execute(
            "UPDATE password_reset_tokens SET used = TRUE WHERE id = $1", row["id"]
        )

    return RedirectResponse("/login?success=Password+reset+successfully.+Please+sign+in", status_code=302)


# ---------------------------------------------------------------------------
# Newsletter Subscribe
# ---------------------------------------------------------------------------

async def newsletter_subscribe(request: Request) -> RedirectResponse:
    form = await request.form()
    email = (form.get("email") or "").strip().lower()
    if not email:
        return RedirectResponse("/?error=Please+enter+your+email", status_code=302)

    try:
        from app.services.brevo import sync_to_brevo_waitlist_audience, send_newsletter_confirmation
        import asyncio
        asyncio.create_task(sync_to_brevo_waitlist_audience(email, list_id=2))
        asyncio.create_task(send_newsletter_confirmation(email))
    except Exception:
        pass

    return RedirectResponse("/?success=You+are+subscribed+to+the+ASIKO+newsletter", status_code=302)


routes = [
    Route("/register", endpoint=register_page, methods=["GET"]),
    Route("/register", endpoint=register_submit, methods=["POST"]),
    Route("/login", endpoint=login_page, methods=["GET"]),
    Route("/login", endpoint=login_submit, methods=["POST"]),
    Route("/logout", endpoint=logout, methods=["GET"]),
    Route("/forgot-password", endpoint=forgot_password_page, methods=["GET"]),
    Route("/forgot-password", endpoint=forgot_password_submit, methods=["POST"]),
    Route("/reset-password", endpoint=reset_password_page, methods=["GET"]),
    Route("/reset-password", endpoint=reset_password_submit, methods=["POST"]),
    Route("/newsletter/subscribe", endpoint=newsletter_subscribe, methods=["POST"]),
    Route("/account", endpoint=customer_dashboard, methods=["GET"]),
    Route("/account/order/{order_id}", endpoint=customer_order_detail, methods=["GET"]),
]
