# ASIKO Boutique - Admin Email Section
# Templates, campaign sending, analytics, and delivery tracking.
#
# Routes:
#   /admin/section/email  (GET + POST)
#
# POST actions are dispatched via a hidden 'section' field:
#   email_create  - create a new template
#   email_update  - update an existing template
#   email_delete  - delete a template
#   email_send    - send an email campaign

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.routing import Route

from app.core import templates

logger = logging.getLogger("asiko.admin.email")


# ---------------------------------------------------------------------------
# Section response wrapper — same pattern as admin_sections.py
# ---------------------------------------------------------------------------
def _section_response(request: Request, template: str, context: dict) -> HTMLResponse:
    ctx = {"request": request, **context}
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(request, template, ctx)
    ctx["section_template"] = template
    return templates.TemplateResponse(request, "admin/base.html", ctx)


def _humanize_dt(dt) -> str:
    if dt is None:
        return "—"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except ValueError:
            return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    delta = now - dt
    if delta.days > 30:
        return dt.strftime("%b %-d, %Y")
    if delta.days >= 1:
        return f"{delta.days}d ago"
    hours = int(delta.total_seconds() // 3600)
    if hours >= 1:
        return f"{hours}h ago"
    minutes = max(int(delta.total_seconds() // 60), 0)
    if minutes >= 1:
        return f"{minutes}m ago"
    return "just now"


# ---------------------------------------------------------------------------
# GET — load templates, stats, and logs
# ---------------------------------------------------------------------------
async def section_email_get(request: Request) -> HTMLResponse:
    pool = request.app.state.db_pool
    email_templates: List[Dict[str, Any]] = []
    email_logs: List[Dict[str, Any]] = []
    email_stats: Dict[str, int] = {"sent": 0, "delivered": 0, "opened": 0, "clicked": 0}

    try:
        async with pool.acquire() as conn:
            try:
                rows = await conn.fetch("SELECT * FROM email_templates ORDER BY created_at DESC")
                email_templates = [dict(r) for r in rows]
                for t in email_templates:
                    t["created_at"] = _humanize_dt(t.get("created_at"))
            except Exception as exc:
                logger.warning("[admin] email_templates fetch failed (table may not exist yet): %s", exc)

            try:
                rows = await conn.fetch("SELECT * FROM email_logs ORDER BY created_at DESC LIMIT 50")
                email_logs = [dict(r) for r in rows]
                for log in email_logs:
                    log["created_at"] = _humanize_dt(log.get("created_at"))
            except Exception as exc:
                logger.warning("[admin] email_logs fetch failed (table may not exist yet): %s", exc)

            try:
                stats = await conn.fetchrow(
                    "SELECT "
                    "COUNT(*) AS sent, "
                    "COUNT(*) FILTER (WHERE status = 'delivered') AS delivered, "
                    "COUNT(*) FILTER (WHERE status = 'opened') AS opened, "
                    "COUNT(*) FILTER (WHERE status = 'clicked') AS clicked "
                    "FROM email_logs"
                )
                if stats:
                    email_stats = {
                        "sent": int(stats["sent"] or 0),
                        "delivered": int(stats["delivered"] or 0),
                        "opened": int(stats["opened"] or 0),
                        "clicked": int(stats["clicked"] or 0),
                    }
            except Exception as exc:
                logger.warning("[admin] email_stats fetch failed: %s", exc)
    except Exception as exc:
        logger.error("[admin] email section GET failed: %s", exc)

    return _section_response(request, "admin/sections/email.html", {
        "email_templates": email_templates,
        "email_logs": email_logs,
        "email_stats": email_stats,
    })


# ---------------------------------------------------------------------------
# POST — handle template CRUD and email sending
# ---------------------------------------------------------------------------
async def section_email_post(request: Request) -> HTMLResponse:
    pool = request.app.state.db_pool
    form = await request.form()
    section = form.get("section", "")

    # --- Create Template ---
    if section == "email_create":
        name = (form.get("name") or "").strip()
        subject = (form.get("subject") or "").strip()
        body = (form.get("body") or "").strip()
        category = (form.get("category") or "custom").strip()
        if name and subject and body:
            try:
                async with pool.acquire() as conn:
                    await conn.execute(
                        "INSERT INTO email_templates (name, subject, body, category) VALUES ($1, $2, $3, $4)",
                        name, subject, body, category,
                    )
                return HTMLResponse(
                    "<div class='text-xs text-emerald-600'>Template created.</div>",
                    headers={"HX-Redirect": "/admin/section/email"},
                )
            except Exception as exc:
                logger.error("[admin] email template create failed: %s", exc)
                return HTMLResponse(
                    "<div class='text-xs text-red-500'>Failed to create template.</div>",
                    status_code=500,
                )
        return HTMLResponse(
            "<div class='text-xs text-red-500'>Please fill all fields.</div>",
            status_code=400,
        )

    # --- Update Template ---
    if section == "email_update":
        template_id = form.get("template_id")
        name = (form.get("name") or "").strip()
        subject = (form.get("subject") or "").strip()
        body = (form.get("body") or "").strip()
        category = (form.get("category") or "custom").strip()
        if template_id and name and subject and body:
            try:
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE email_templates SET name=$1, subject=$2, body=$3, category=$4, updated_at=NOW() WHERE id=$5",
                        name, subject, body, category, template_id,
                    )
                return HTMLResponse(
                    "<div class='text-xs text-emerald-600'>Template updated.</div>",
                    headers={"HX-Redirect": "/admin/section/email"},
                )
            except Exception as exc:
                logger.error("[admin] email template update failed: %s", exc)
                return HTMLResponse(
                    "<div class='text-xs text-red-500'>Failed to update template.</div>",
                    status_code=500,
                )

    # --- Delete Template ---
    if section == "email_delete":
        template_id = form.get("template_id")
        if template_id:
            try:
                async with pool.acquire() as conn:
                    await conn.execute("DELETE FROM email_templates WHERE id = $1", template_id)
                return HTMLResponse(
                    "<div class='text-xs text-emerald-600'>Template deleted.</div>",
                    headers={"HX-Redirect": "/admin/section/email"},
                )
            except Exception as exc:
                logger.error("[admin] email template delete failed: %s", exc)
                return HTMLResponse(
                    "<div class='text-xs text-red-500'>Failed to delete template.</div>",
                    status_code=500,
                )

    # --- Send Email Campaign ---
    if section == "email_send":
        template_id = form.get("template_id")
        recipient_email = (form.get("recipient_email") or "").strip()
        segment = (form.get("segment") or "").strip()

        if not template_id:
            return HTMLResponse(
                "<div class='text-xs text-red-500'>Please select a template.</div>",
                status_code=400,
            )

        try:
            async with pool.acquire() as conn:
                tpl = await conn.fetchrow("SELECT * FROM email_templates WHERE id = $1", template_id)
                if not tpl:
                    return HTMLResponse(
                        "<div class='text-xs text-red-500'>Template not found.</div>",
                        status_code=404,
                    )

                # Resolve recipients
                recipients: List[str] = []
                if recipient_email:
                    recipients = [recipient_email]
                elif segment:
                    if segment == "all":
                        rows = await conn.fetch("SELECT email FROM customers")
                    elif segment == "active":
                        rows = await conn.fetch(
                            "SELECT email FROM customers WHERE id IN (SELECT DISTINCT customer_id FROM orders)"
                        )
                    elif segment == "new":
                        rows = await conn.fetch(
                            "SELECT email FROM customers WHERE created_at > NOW() - INTERVAL '30 days'"
                        )
                    elif segment == "at_risk":
                        rows = await conn.fetch(
                            "SELECT email FROM customers WHERE id NOT IN ("
                            "  SELECT DISTINCT customer_id FROM orders WHERE created_at > NOW() - INTERVAL '60 days'"
                            ")"
                        )
                    else:
                        rows = await conn.fetch("SELECT email FROM customers")
                    recipients = [r["email"] for r in rows if r["email"]]
                else:
                    return HTMLResponse(
                        "<div class='text-xs text-red-500'>No recipients selected.</div>",
                        status_code=400,
                    )

                if not recipients:
                    return HTMLResponse(
                        "<div class='text-xs text-red-500'>No recipients found for this selection.</div>",
                        status_code=400,
                    )

                # Log the sends
                tpl_subject = tpl["subject"]
                tpl_body = tpl["body"]
                for email in recipients:
                    await conn.execute(
                        "INSERT INTO email_logs (recipient_email, subject, template_id, status) VALUES ($1, $2, $3, 'sent')",
                        email, tpl_subject, template_id,
                    )

                # Fire-and-forget bulk send via Brevo
                async def _send_bulk():
                    from app.services.brevo import send_transactional_email
                    for email in recipients:
                        try:
                            await send_transactional_email(email, tpl_subject, tpl_body)
                        except Exception as exc:
                            logger.warning("[admin] Brevo send to %s failed: %s", email, exc)

                asyncio.create_task(_send_bulk())

                return HTMLResponse(
                    f"<div class='text-xs text-emerald-600'>Sending to {len(recipients)} recipient(s).</div>",
                    headers={"HX-Redirect": "/admin/section/email"},
                )
        except Exception as exc:
            logger.error("[admin] email send failed: %s", exc)
            return HTMLResponse(
                "<div class='text-xs text-red-500'>Failed to send email.</div>",
                status_code=500,
            )

    # Fallback — re-render the section
    return await section_email_get(request)


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------
routes = [
    Route("/admin/section/email", endpoint=section_email_get, methods=["GET"]),
    Route("/admin/section/email", endpoint=section_email_post, methods=["POST"]),
]
