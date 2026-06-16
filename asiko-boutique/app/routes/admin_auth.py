# ASIKO Boutique — Admin Authentication Routes
# Login, logout, session management for admin panel.

import hashlib
import hmac
import os

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.routing import Route

from app.core import templates


def _hash_password(password: str) -> str:
    """SHA-256 hash with salt — same algorithm as customer auth."""
    salt = os.environ.get("AUTH_SALT", "asiko-boutique-salt-2024")
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def _check_password(password: str, password_hash: str) -> bool:
    return hmac.compare_digest(_hash_password(password), password_hash)


def _is_admin(session: dict) -> bool:
    """Check if current session has an authenticated admin."""
    return bool(session.get("admin_id"))


# ---------------------------------------------------------------------------
# Admin Login Page
# ---------------------------------------------------------------------------

async def admin_login_page(request: Request) -> HTMLResponse:
    """GET /admin/login — Render admin login form."""
    error = request.query_params.get("error", "")
    settings = {}
    try:
        from app.settings_service import get_settings
        settings = await get_settings(request.app.state.db_pool)
    except Exception:
        pass
    return templates.TemplateResponse(request, "admin/login.html", {
        "request": request,
        "error": error,
        "settings": settings,
    })


# ---------------------------------------------------------------------------
# Admin Login Submit
# ---------------------------------------------------------------------------

async def admin_login_submit(request: Request) -> RedirectResponse:
    """POST /admin/login — Validate credentials and create session."""
    form = await request.form()
    email = (form.get("email") or "").strip().lower()
    password = form.get("password") or ""

    if not email or not password:
        return RedirectResponse("/admin/login?error=Email+and+password+are+required", status_code=302)

    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        admin = await conn.fetchrow(
            "SELECT id, email, password_hash, full_name, role, is_active "
            "FROM admin_users WHERE email = $1",
            email,
        )

    if not admin:
        return RedirectResponse("/admin/login?error=Invalid+email+or+password", status_code=302)

    if not admin["is_active"]:
        return RedirectResponse("/admin/login?error=Account+is+disabled+contact+super+admin", status_code=302)

    if not _check_password(password, admin["password_hash"]):
        return RedirectResponse("/admin/login?error=Invalid+email+or+password", status_code=302)

    # Update last_login
    pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE admin_users SET last_login = NOW() WHERE id = $1",
            admin["id"],
        )

    # Set session
    request.session["admin_id"] = str(admin["id"])
    request.session["admin_email"] = admin["email"]
    request.session["admin_name"] = admin["full_name"]
    request.session["admin_role"] = admin["role"]

    return RedirectResponse("/admin/section/dashboard", status_code=302)


# ---------------------------------------------------------------------------
# Admin Logout
# ---------------------------------------------------------------------------

async def admin_logout(request: Request) -> RedirectResponse:
    """GET /admin/logout — Clear admin session and redirect to login."""
    request.session.clear()
    return RedirectResponse("/admin/login?success=Logged+out+successfully", status_code=302)


# ---------------------------------------------------------------------------
# Register admin auth routes
# ---------------------------------------------------------------------------

routes = [
    Route("/admin/login", admin_login_page, methods=["GET"]),
    Route("/admin/login", admin_login_submit, methods=["POST"]),
    Route("/admin/logout", admin_logout, methods=["GET"]),
]
