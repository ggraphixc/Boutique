# app/services/opay_service.py
# OPay payment integration for Nigerian bank transfer + card payments.
# Replaces Paystack. OPay API: https://api.opay.com

import os
import hashlib
import hmac
import json
import logging
from typing import Optional

import httpx

logger = logging.getLogger("asiko.opay")

OPAY_BASE_URL = os.getenv("OPAY_BASE_URL", "https://api.opay.com")
OPAY_MERCHANT_ID = os.getenv("OPAY_MERCHANT_ID", "")
OPAY_SECRET_KEY = os.getenv("OPAY_SECRET_KEY", "")
OPAY_PUBLIC_KEY = os.getenv("OPAY_PUBLIC_KEY", "")
OPAY_CALLBACK_URL = os.getenv(
    "OPAY_CALLBACK_URL", "https://asikoboutique.com/webhooks/opay"
)
OPAY_RETURN_URL = os.getenv(
    "OPAY_RETURN_URL", "https://asikoboutique.com/checkout/confirmation"
)


def _headers(content_type: str = "application/json") -> dict:
    """Build OPay request headers."""
    return {
        "Content-Type": content_type,
        "Authorization": f"Bearer {OPAY_SECRET_KEY}",
        "Merchant-Id": OPAY_MERCHANT_ID,
    }


async def initialize_opay_payment(
    order_id: str,
    amount_kobo: int,
    email: str,
    customer_name: str = "",
    description: str = "",
    payment_method: str = "bank_transfer",
) -> dict:
    """
    Initialize an OPay payment session.

    Args:
        order_id: Internal order ID (used as reference)
        amount_kobo: Amount in kobo (₦1 = 100 kobo)
        email: Customer email
        customer_name: Customer full name
        description: Payment description
        payment_method: 'card' or 'bank_transfer'

    Returns:
        dict with 'reference' and 'payment_url' on success,
        or 'error' key on failure.
    """
    if not OPAY_SECRET_KEY or OPAY_SECRET_KEY.startswith("your_"):
        logger.warning("[OPAY] Secret key not configured — using mock mode")
        return {
            "reference": f"asiko_{order_id}",
            "payment_url": f"/checkout/confirmation?reference=asiko_{order_id}",
            "mock": True,
        }

    reference = f"asiko_{order_id}"

    payload = {
        "amount": str(amount_kobo),
        "currency": "NGN",
        "reference": reference,
        "description": description or f"Order #{order_id}",
        "callbackUrl": OPAY_CALLBACK_URL,
        "returnUrl": OPAY_RETURN_URL,
        "paymentMethod": payment_method,
    }

    if email:
        payload["customerEmail"] = email
    if customer_name:
        payload["customerName"] = customer_name

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{OPAY_BASE_URL}/api/v1/gateway/webanchor/initialize",
                headers=_headers(),
                json=payload,
            )
            data = response.json()

            if response.status_code == 200 and data.get("code") == "0000":
                result = data.get("data", {})
                payment_url = result.get("paymentUrl", "")
                logger.info(
                    "[OPAY] Payment initialized: ref=%s url=%s", reference, payment_url
                )
                return {
                    "reference": reference,
                    "payment_url": payment_url,
                    "status": "initialized",
                }
            else:
                msg = data.get("message", "Unknown OPay error")
                logger.error(
                    "[OPAY] Initialization failed: %s %s",
                    response.status_code,
                    msg,
                )
                return {"error": msg}

    except httpx.TimeoutException:
        logger.error("[OPAY] Request timeout during initialization")
        return {"error": "Payment service timeout. Please try again."}
    except Exception as e:
        logger.error("[OPAY] Initialization exception: %s", e)
        return {"error": f"Payment service error: {str(e)}"}


async def verify_opay_payment(reference: str) -> dict:
    """
    Verify an OPay payment by reference.

    Returns:
        dict with 'status', 'amount', 'reference', 'transaction_id' on success.
    """
    if not OPAY_SECRET_KEY or OPAY_SECRET_KEY.startswith("your_"):
        logger.info("[OPAY] Mock mode — returning success for %s", reference)
        return {
            "status": "success",
            "reference": reference,
            "amount": 0,
            "transaction_id": f"mock_{reference}",
            "mock": True,
        }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{OPAY_BASE_URL}/api/v1/gateway/query/reference",
                headers=_headers(),
                params={"reference": reference},
            )
            data = response.json()

            if response.status_code == 200 and data.get("code") == "0000":
                result = data.get("data", {})
                status_raw = result.get("status", "").upper()

                # OPay statuses: SUCCESS, FAIL, PENDING, CLOSED
                if status_raw == "SUCCESS":
                    status = "success"
                elif status_raw in ("FAIL", "CLOSED"):
                    status = "failed"
                else:
                    status = "pending"

                return {
                    "status": status,
                    "reference": reference,
                    "amount": result.get("amount", 0),
                    "transaction_id": result.get("transactionId", ""),
                    "payment_method": result.get("paymentMethod", ""),
                    "paid_at": result.get("paidAt", ""),
                }
            else:
                msg = data.get("message", "Verification failed")
                logger.error("[OPAY] Verification failed: %s", msg)
                return {"status": "error", "error": msg}

    except Exception as e:
        logger.error("[OPAY] Verification exception: %s", e)
        return {"status": "error", "error": str(e)}


def verify_opay_webhook_signature(payload_body: bytes, signature: str) -> bool:
    """
    Verify OPay webhook HMAC-SHA512 signature.

    OPay signs the raw body with the secret key and sends the
    hex digest in the x-opay-signature header.
    """
    if not OPAY_SECRET_KEY or OPAY_SECRET_KEY.startswith("your_"):
        logger.warning("[OPAY] No secret key — accepting webhook in dev mode")
        return True

    expected = hmac.new(
        OPAY_SECRET_KEY.encode("utf-8"),
        payload_body,
        hashlib.sha512,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


async def get_opay_bank_account(order_id: str, amount_kobo: int) -> dict:
    """
    Get virtual bank account details for bank transfer payment.
    OPay can generate unique virtual accounts per transaction.

    Returns:
        dict with bank_name, account_number, account_name, amount, reference
    """
    reference = f"asiko_{order_id}"

    if not OPAY_SECRET_KEY or OPAY_SECRET_KEY.startswith("your_"):
        return {
            "bank_name": "OPay Digital Bank",
            "account_number": "8012345678",
            "account_name": "ASIKO Boutique",
            "amount": amount_kobo,
            "reference": reference,
            "mock": True,
        }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{OPAY_BASE_URL}/api/v1/bank-transfer/create",
                headers=_headers(),
                json={
                    "amount": str(amount_kobo),
                    "reference": reference,
                    "currency": "NGN",
                },
            )
            data = response.json()

            if response.status_code == 200 and data.get("code") == "0000":
                result = data.get("data", {})
                return {
                    "bank_name": result.get("bankName", "OPay"),
                    "account_number": result.get("accountNumber", ""),
                    "account_name": result.get("accountName", ""),
                    "amount": amount_kobo,
                    "reference": reference,
                }
            else:
                logger.error("[OPAY] Bank account creation failed: %s", data.get("message"))
                return {"error": data.get("message", "Failed to create bank account")}

    except Exception as e:
        logger.error("[OPAY] Bank account exception: %s", e)
        return {"error": str(e)}
