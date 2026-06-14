# ASIKO Boutique - Settlement Engine & Background Workers
# OPay HMAC verification | 36-state shipping matrix | Reservation expiry | Brevo dispatch

import os
import hmac
import hashlib
import asyncio
import logging

import httpx
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from app.services.opay_service import (
    verify_opay_webhook_signature,
    initialize_opay_payment,
)

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
    "ONDO": 2500,
    "OSUN": 2500,
    "EKITI": 2500,
    "OYO": 2500,
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
# OPay Webhook Handler (HMAC-SHA512)
# ---------------------------------------------------------------------------

async def opay_webhook_handler(request: Request) -> Response:
    """
    Processes incoming secure webhooks from OPay.
    HMAC-SHA512 verification → order status update → email dispatch.
    """
    raw_body = await request.body()
    signature = request.headers.get("x-opay-signature", "")

    if not signature:
        return JSONResponse(
            {"status": "error", "message": "Missing signature header"},
            status_code=401,
        )

    if not verify_opay_webhook_signature(raw_body, signature):
        logger.warning("[OPAY] HMAC verification failed")
        return JSONResponse(
            {"status": "error", "message": "Invalid signature"},
            status_code=401,
        )

    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(
            {"status": "error", "message": "Invalid JSON payload"},
            status_code=400,
        )

    status = payload.get("status", "").upper()
    reference = payload.get("reference", "")

    if not reference:
        return JSONResponse(
            {"status": "error", "message": "Missing reference"},
            status_code=400,
        )

    # Extract order_id from reference (format: asiko_{order_id})
    order_id = reference.replace("asiko_", "", 1)

    pool = request.app.state.db_pool

    if status == "SUCCESS":
        async with pool.acquire() as conn:
            # Update order status to 'paid'
            await conn.execute(
                "UPDATE orders SET status = 'paid' WHERE id::text = $1 AND status = 'pending'",
                order_id,
            )
            # Update product reservations
            await conn.execute(
                """
                UPDATE product_reservations
                SET status = 'paid'
                WHERE order_id::text = $1 AND status = 'staged'
                """,
                order_id,
            )

        logger.info("[OPAY] Payment confirmed: order=%s ref=%s", order_id, reference)

        # Send confirmation email
        order_row = None
        async with pool.acquire() as conn:
            order_row = await conn.fetchrow(
                "SELECT customer_email, total_amount FROM orders WHERE id::text = $1",
                order_id,
            )

        if order_row and order_row["customer_email"]:
            asyncio.create_task(
                dispatch_luxury_alert_email(
                    order_row["customer_email"],
                    "ASIKO Boutique — Payment Confirmed",
                    f"Your order #{order_id[:8]} has been confirmed. "
                    f"Amount: ₦{order_row['total_amount']:,.0f}. "
                    f"We'll notify you when it ships.",
                )
            )

    elif status in ("FAIL", "CLOSED"):
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE orders SET status = 'cancelled' WHERE id::text = $1 AND status = 'pending'",
                order_id,
            )
        logger.info("[OPAY] Payment failed: order=%s ref=%s", order_id, reference)

    return JSONResponse({"status": "success", "message": "Webhook processed"})


# ---------------------------------------------------------------------------
# OPay Transaction Initialization (wrapper for checkout.py)
# ---------------------------------------------------------------------------

async def initialize_payment(
    email: str,
    amount_kobo: int,
    order_id: str,
    customer_name: str = "",
    metadata: dict = None,
) -> dict:
    """
    Initialize OPay payment. Called by checkout.py.
    Returns {"authorization_url": "...", "reference": "..."} on success.
    Returns {"error": "..."} on failure.
    """
    result = await initialize_opay_payment(
        order_id=order_id,
        amount_kobo=amount_kobo,
        email=email,
        customer_name=customer_name,
    )

    if "error" in result:
        return {"error": result["error"]}

    return {
        "authorization_url": result.get("payment_url", ""),
        "reference": result.get("reference", ""),
    }


# ---------------------------------------------------------------------------
# Route table
# ---------------------------------------------------------------------------

routes = [
    Route("/webhooks/opay", endpoint=opay_webhook_handler, methods=["POST"]),
]
