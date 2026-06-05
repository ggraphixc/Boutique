# ASIKO Boutique - Brevo Transactional Email & Contact Sync Service

import logging
from typing import Optional

import httpx
from starlette.config import Config

logger = logging.getLogger("asiko.brevo")

_config = Config(".env")
BREVO_API_KEY = _config("BREVO_API_KEY", cast=str, default="")
SENDER_EMAIL = _config("SENDER_EMAIL", cast=str, default="orders@asikoboutique.com")

BREVO_API_URL = "https://api.brevo.com/v3"


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
