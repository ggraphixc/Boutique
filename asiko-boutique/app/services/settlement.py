# ASIKO Boutique - Settlement Engine & Background Workers
# Paystack HMAC verification | 36-state shipping matrix | Reservation expiry | Brevo dispatch

import os
import hmac
import hashlib
import asyncio
import logging

import httpx
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

logger = logging.getLogger("asiko.settlement")


# ---------------------------------------------------------------------------
# 36-State Nigerian Delivery Matrix
# ---------------------------------------------------------------------------

SHIPPING_MATRIX = {
    # Base logistics — ₦1,500
    "LAGOS": 1500,
    "ABUJA": 1500,
    "FCT": 1500,
    # South-South / South-East — ₦2,500–₦3,500
    "EDO": 3000,
    "DELTA": 3000,
    "RIVERS": 3500,
    "AKWA IBOM": 3500,
    "CROSS RIVER": 3500,
    "ABIA": 3000,
    "IMO": 3000,
    "ANAMBRA": 3500,
    "ENUGU": 3000,
    "EBONYI": 3000,
    # South-West — ₦2,000–₦2,500
    "OGUN": 2000,
    "OGUN": 2000,
    "ONDO": 2500,
    "OSUN": 2500,
    "EKITI": 2500,
    "OYO": 2500,
    "OSUN": 2500,
    # North-Central — ₦3,000
    "KOGI": 3000,
    "KWARA": 3000,
    "NIGER": 3000,
    "PLATEAU": 3000,
    "NASARAWA": 3000,
    "BENUE": 3000,
    # North-West — ₦3,500–₦4,000
    "KANO": 4000,
    "KADUNA": 4000,
    "KATSINA": 3500,
    "SOKOTO": 3500,
    "ZAMFARA": 3500,
    "KEBBI": 3500,
    "JIGAWA": 3500,
    # North-East — ₦4,000
    "BORNO": 4000,
    "YOBE": 4000,
    "ADAMAWA": 4000,
    "GOMBE": 3500,
    "TARABA": 3500,
    "BAUCHI": 3500,
}

DEFAULT_REGIONAL_COST = 4000


def calculate_shipping(state_code: str) -> int:
    """Resolve shipping cost for a Nigerian state code (case-insensitive)."""
    return SHIPPING_MATRIX.get(state_code.upper().strip(), DEFAULT_REGIONAL_COST)


# ---------------------------------------------------------------------------
# Background Worker: Expired Reservation Purge
# Uses asyncio.create_task (NOT Starlette BackgroundTasks) to avoid TestClient hangs
# ---------------------------------------------------------------------------

async def purge_expired_reservations(db_pool, timeout_minutes: int = 15) -> None:
    """
    Async baseline cleanup task runner.
    Clears stale 'staged' reservations that failed to finalize within the checkout window.
    Safe to fire via asyncio.create_task from any route handler.
    """
    try:
        async with db_pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE product_reservations
                SET status = 'expired'
                WHERE status = 'staged'
                  AND created_at < NOW() - make_interval(mins => $1);
                """,
                timeout_minutes,
            )
            count = result.split()[-1] if result else "0"
            logger.info("[WORKER] Evicted stale reservations: %s rows expired", count)
    except Exception as e:
        logger.error("[WORKER] Background eviction failed: %s", e)


def spawn_expiry_worker(db_pool, timeout_minutes: int = 15) -> None:
    """
    Fire-and-forget launcher for the reservation purge worker.
    Call from route handlers to schedule non-blocking cleanup.
    """
    asyncio.create_task(purge_expired_reservations(db_pool, timeout_minutes))


# ---------------------------------------------------------------------------
# Brevo Email Dispatch (Graceful Fallback)
# ---------------------------------------------------------------------------

async def dispatch_luxury_alert_email(
    email_address: str,
    subject: str,
    message_body: str,
) -> bool:
    """
    Dispatches notifications via Brevo API.
    Gracefully skips if API key is placeholder — no exceptions, just a log entry.
    """
    api_key = os.getenv("BREVO_API_KEY", "")
    if not api_key or api_key.startswith("your_") or api_key == "PLACEHOLDER_KEY":
        logger.info("[BREVO MOCK] Key placeholder — skipping send to %s", email_address)
        return False

    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json",
    }
    payload = {
        "sender": {"name": "ASIKO Atelier", "email": "concierge@asikoboutique.com"},
        "to": [{"email": email_address}],
        "subject": subject,
        "htmlContent": f"<html><body>{message_body}</body></html>",
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers, timeout=15.0)
            if response.status_code in (200, 201):
                logger.info("[BREVO] Dispatch success → %s", email_address)
                return True
            logger.warning("[BREVO] Dispatch %s: %s", response.status_code, response.text[:200])
            return False
        except Exception as e:
            logger.error("[BREVO] Dispatch failed → %s: %s", email_address, e)
            return False


# ---------------------------------------------------------------------------
# Paystack Webhook Handler (HMAC-SHA512)
# ---------------------------------------------------------------------------

async def paystack_webhook_handler(request: Request) -> Response:
    """
    Processes incoming secure webhooks from Paystack.
    HMAC-SHA512 verification → reservation state transitions → async email dispatch.
    """
    paystack_secret = os.getenv("PAYSTACK_SECRET_KEY", "")
    signature = request.headers.get("x-paystack-signature")

    if not signature:
        return JSONResponse(
            {"status": "error", "message": "Missing Security Header"},
            status_code=401,
        )

    raw_body = await request.body()

    # Compute cryptographic trace to protect against packet tampering
    computed_hmac = hmac.new(
        paystack_secret.encode("utf-8"),
        raw_body,
        hashlib.sha512,
    ).hexdigest()

    if not hmac.compare_digest(computed_hmac, signature):
        logger.warning("[PAYMENTS] HMAC verification failed")
        return JSONResponse(
            {"status": "error", "message": "Signature Verification Failed"},
            status_code=401,
        )

    # Ingest verification payload parameters safely
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(
            {"status": "error", "message": "Invalid JSON payload"},
            status_code=400,
        )

    event = payload.get("event")

    if event == "charge.success":
        data = payload.get("data", {})
        metadata = data.get("metadata", {})
        session_key = metadata.get("session_key", "ANONYMOUS_SESSION")
        delivery_state = metadata.get("state", "LAGOS").upper().strip()
        customer_email = data.get("customer", {}).get("email", "")

        # Calculate transaction shipping rate based on regional matrix
        shipping_cost = calculate_shipping(delivery_state)
        logger.info("[PAYMENTS] Shipping to %s: N%d", delivery_state, shipping_cost)

        # Update persistent reservation ledger via active db_pool
        pool = request.app.state.db_pool
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    UPDATE product_reservations
                    SET status = 'paid'
                    WHERE session_identifier = $1 AND status = 'staged';
                    """,
                    session_key,
                )

        # Fire email dispatch as non-blocking async task
        if customer_email:
            email_content = (
                f"Your luxury order has been confirmed. "
                f"Shipping to {delivery_state} is now processing."
            )
            asyncio.create_task(
                dispatch_luxury_alert_email(
                    customer_email,
                    "ASIKO Boutique — Order Confirmed",
                    email_content,
                )
            )

        logger.info("[PAYMENTS] Processed charge.success for session %s", session_key)

    return JSONResponse({"status": "success", "message": "Webhook Verified & Processed"})


# ---------------------------------------------------------------------------
# Paystack Transaction Initialization
# ---------------------------------------------------------------------------

async def initialize_paystack_transaction(
    email: str,
    amount_kobo: int,
    order_id: str,
    metadata: dict = None,
) -> dict:
    """
    Initialize a Paystack transaction and return the authorization URL.
    Returns {"authorization_url": "...", "reference": "..."} on success.
    Returns {"error": "..."} on failure.
    """
    paystack_secret = os.getenv("PAYSTACK_SECRET_KEY", "")
    if not paystack_secret or paystack_secret.startswith("your_"):
        return {"error": "Paystack secret key not configured"}

    payload = {
        "email": email,
        "amount": amount_kobo,  # Paystack expects amount in kobo (₦1 = 100 kobo)
        "reference": f"asiko_{order_id}",
        "callback_url": os.getenv("PAYSTACK_CALLBACK_URL", "https://asikoboutique.com/checkout/confirmation"),
        "metadata": metadata or {},
    }

    headers = {
        "Authorization": f"Bearer {paystack_secret}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.paystack.co/transaction/initialize",
                json=payload,
                headers=headers,
                timeout=15.0,
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("status"):
                    return {
                        "authorization_url": data["data"]["authorization_url"],
                        "reference": data["data"]["reference"],
                    }
                return {"error": data.get("message", "Unknown Paystack error")}
            else:
                logger.error("[PAYSTACK] Initialization failed: %s %s", response.status_code, response.text[:200])
                return {"error": f"Paystack API error: {response.status_code}"}

    except Exception as e:
        logger.error("[PAYSTACK] Initialization exception: %s", e)
        return {"error": f"Payment initialization failed: {str(e)}"}


# ---------------------------------------------------------------------------
# Route table
# ---------------------------------------------------------------------------

routes = [
    Route("/payments/webhook", endpoint=paystack_webhook_handler, methods=["POST"]),
]
