# ASIKO Boutique - Brevo Transactional Email & Contact Sync Service

import logging
import secrets
from typing import Optional

import httpx
from starlette.config import Config

logger = logging.getLogger("asiko.brevo")

_config = Config(".env")
BREVO_API_KEY = _config("BREVO_API_KEY", cast=str, default="")
SENDER_EMAIL = _config("SENDER_EMAIL", cast=str, default="orders@asikoboutique.com")

BREVO_API_URL = "https://api.brevo.com/v3"

# ---------------------------------------------------------------------------
# Brand HTML wrappers
# ---------------------------------------------------------------------------

_BRAND_HEADER = """
<div style="background-color:#0D2A22;color:#fff;padding:24px;text-align:center;">
  <h1 style="margin:0;font-size:24px;letter-spacing:2px;">ASIKO BOUTIQUE</h1>
  <p style="margin:4px 0 0;font-size:13px;opacity:.8;">Contemporary Nigerian Fashion</p>
</div>
"""

_BRAND_FOOTER = """
<div style="background-color:#D4AF37;padding:12px;text-align:center;color:#0D2A22;">
  <p style="margin:0;font-size:12px;">&copy; 2026 ASIKO Boutique &mdash; All rights reserved</p>
</div>
"""


async def send_transactional_email(
    to_email: str,
    subject: str,
    html_content: str,
    sender_name: str = "ASIKO Boutique",
) -> bool:
    """Dispatch a transactional HTML email via Brevo SMTP API."""
    if not BREVO_API_KEY or BREVO_API_KEY.startswith("your_"):
        logger.warning("Brevo API key not configured - skipping email to %s", to_email)
        return False

    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json",
    }

    payload = {
        "sender": {"name": sender_name, "email": SENDER_EMAIL},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_content,
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BREVO_API_URL}/smtp/email",
                json=payload,
                headers=headers,
                timeout=15.0,
            )
            if response.status_code in (200, 201):
                logger.info("Email sent to %s: %s", to_email, subject)
                return True
            logger.error(
                "Brevo API error %s: %s", response.status_code, response.text[:200]
            )
            return False
        except httpx.HTTPError as exc:
            logger.error("Failed to communicate with Brevo: %s", exc)
            return False


# ---------------------------------------------------------------------------
# Email Templates
# ---------------------------------------------------------------------------

async def send_forgot_password_email(
    to_email: str,
    customer_name: str,
    reset_url: str,
) -> bool:
    """Send password reset email with branded template."""
    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
      {_BRAND_HEADER}
      <div style="padding:24px;background-color:#FBF9F6;">
        <h2 style="color:#0D2A22;margin-top:0;">Reset Your Password</h2>
        <p>Dear <strong>{customer_name}</strong>,</p>
        <p>We received a request to reset your password. Click the button below to set a new one.</p>
        <div style="text-align:center;margin:24px 0;">
          <a href="{reset_url}" style="display:inline-block;background-color:#0D2A22;color:#fff;padding:12px 32px;border-radius:8px;text-decoration:none;font-weight:600;">Reset Password</a>
        </div>
        <p style="color:#666;font-size:13px;">This link expires in 1 hour. If you didn&rsquo;t request this, ignore this email.</p>
      </div>
      {_BRAND_FOOTER}
    </body></html>"""
    return await send_transactional_email(to_email, "Reset Your Password — ASIKO Boutique", html)


async def send_welcome_email(
    to_email: str,
    customer_name: str,
) -> bool:
    """Send welcome greeting email to new customers."""
    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
      {_BRAND_HEADER}
      <div style="padding:24px;background-color:#FBF9F6;">
        <h2 style="color:#0D2A22;margin-top:0;">Welcome to ASIKO!</h2>
        <p>Dear <strong>{customer_name}</strong>,</p>
        <p>Thank you for joining ASIKO Boutique. We&rsquo;re excited to have you.</p>
        <p>Explore our curated collection of authentic Nigerian fashion — every piece crafted with care and verified provenance.</p>
        <div style="text-align:center;margin:24px 0;">
          <a href="/" style="display:inline-block;background-color:#D4AF37;color:#0D2A22;padding:12px 32px;border-radius:8px;text-decoration:none;font-weight:600;">Start Shopping</a>
        </div>
        <p style="color:#666;font-size:13px;">If you ever need help, reply to this email or visit our Help Center.</p>
      </div>
      {_BRAND_FOOTER}
    </body></html>"""
    return await send_transactional_email(to_email, "Welcome to ASIKO Boutique!", html)


async def send_newsletter_confirmation(
    to_email: str,
) -> bool:
    """Send newsletter subscription confirmation."""
    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
      {_BRAND_HEADER}
      <div style="padding:24px;background-color:#FBF9F6;">
        <h2 style="color:#0D2A22;margin-top:0;">You&rsquo;re Subscribed!</h2>
        <p>Thank you for subscribing to the ASIKO Boutique newsletter.</p>
        <p>You&rsquo;ll receive updates on new arrivals, exclusive offers, and styling inspiration.</p>
        <div style="text-align:center;margin:24px 0;">
          <a href="/" style="display:inline-block;background-color:#D4AF37;color:#0D2A22;padding:12px 32px;border-radius:8px;text-decoration:none;font-weight:600;">Browse New Arrivals</a>
        </div>
      </div>
      {_BRAND_FOOTER}
    </body></html>"""
    return await send_transactional_email(to_email, "Welcome to the ASIKO Newsletter", html)


async def sync_to_brevo_waitlist_audience(
    email: str,
    list_id: int = 2,
) -> bool:
    """Add or update a contact in a Brevo marketing audience list."""
    if not BREVO_API_KEY or BREVO_API_KEY.startswith("your_"):
        logger.warning("Brevo API key not configured - skipping contact sync")
        return False

    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json",
    }

    payload = {
        "email": email,
        "listIds": [list_id],
        "updateEnabled": True,
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BREVO_API_URL}/contacts",
                json=payload,
                headers=headers,
                timeout=15.0,
            )
            if response.status_code in (200, 201, 204):
                logger.info("Contact synced to Brevo list %s: %s", list_id, email)
                return True
            logger.warning(
                "Brevo contact sync returned %s: %s",
                response.status_code,
                response.text[:200],
            )
            return False
        except httpx.HTTPError as exc:
            logger.error("Brevo contact sync failed: %s", exc)
            return False
