# ASIKO Boutique — Customer Auth + Dashboard Routes
# Register, login, logout, order history, profile.

import hashlib
import hmac
import os

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.routing import Route

from app.core import templates


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
    return templates.TemplateResponse(request, "customer/register.html", {
        "request": request,
        "error": error,
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
    return RedirectResponse("/account", status_code=302)


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

async def login_page(request: Request) -> HTMLResponse:
    error = request.query_params.get("error", "")
    return templates.TemplateResponse(request, "customer/login.html", {
        "request": request,
        "error": error,
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
    return RedirectResponse("/account", status_code=302)


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

async def logout(request: Request) -> RedirectResponse:
    request.session.pop("customer_id", None)
    request.session.pop("customer_email", None)
    request.session.pop("customer_name", None)
    return RedirectResponse("/", status_code=302)


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
    return templates.TemplateResponse(request, "customer/order_detail.html", context)


routes = [
    Route("/register", endpoint=register_page, methods=["GET"]),
    Route("/register", endpoint=register_submit, methods=["POST"]),
    Route("/login", endpoint=login_page, methods=["GET"]),
    Route("/login", endpoint=login_submit, methods=["POST"]),
    Route("/logout", endpoint=logout, methods=["GET"]),
    Route("/account", endpoint=customer_dashboard, methods=["GET"]),
    Route("/account/order/{order_id}", endpoint=customer_order_detail, methods=["GET"]),
]
