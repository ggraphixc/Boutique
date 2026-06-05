# ASIKO Boutique - Webhook Routes & Brevo Email Integration
# Plus Meshy 3D Pipeline Webhook Receiver for real-time event processing

import json
import logging
import hashlib
import hmac
import asyncio
from typing import Optional

import httpx
from starlette.config import Config
from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse
from starlette.routing import Route

from app.database import (
    fetch_order_by_id,
    fetch_order_items,
    update_order_status,
)

config = Config(".env")
BREVO_API_KEY = config("BREVO_API_KEY", cast=str, default="")
SENDER_EMAIL = config("SENDER_EMAIL", cast=str, default="ggraphixc@gmail.com")
PAYSTACK_SECRET_KEY = config("PAYSTACK_SECRET_KEY", cast=str, default="")

logger = logging.getLogger("asiko.webhooks")


def _parse_metadata(raw) -> dict:
    """Safely parse order metadata from DB (may be JSON string or dict)."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


# ---------------------------------------------------------------------------
# Brevo Email Sender
# ---------------------------------------------------------------------------

async def send_brevo_email(
    to_email: str,
    to_name: str,
    subject: str,
    html_content: str,
) -> bool:
    """Send a transactional email via Brevo SMTP API."""
    if not BREVO_API_KEY or BREVO_API_KEY.startswith("your_"):
        logger.warning("Brevo API key not configured - skipping email to %s", to_email)
        return False

    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": BREVO_API_KEY,
    }
    payload = {
        "sender": {"email": SENDER_EMAIL, "name": "ASIKO Boutique"},
        "to": [{"email": to_email, "name": to_name}],
        "subject": subject,
        "htmlContent": html_content,
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers, timeout=15.0)
            if response.status_code in (200, 201):
                logger.info("Email sent to %s: %s", to_email, subject)
                return True
            logger.error("Brevo error %s: %s", response.status_code, response.text[:200])
            return False
        except Exception as e:
            logger.error("Email send failed to %s: %s", to_email, e)
            return False


# ---------------------------------------------------------------------------
# Email Templates
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


def _build_order_items_table(items: list[dict]) -> str:
    """Render order items as an HTML table."""
    rows = ""
    for item in items:
        price = float(item["price"])
        rows += f"""
        <tr>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;">{item['product_name']}</td>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;text-align:center;">{item['quantity']}</td>
          <td style="padding:10px 8px;border-bottom:1px solid #eee;text-align:right;">&#8358;{price:,.0f}</td>
        </tr>"""
    return f"""
    <table style="width:100%;border-collapse:collapse;margin:16px 0;">
      <thead>
        <tr style="background-color:#0D2A22;color:#fff;">
          <th style="padding:10px 8px;text-align:left;">Product</th>
          <th style="padding:10px 8px;text-align:center;">Qty</th>
          <th style="padding:10px 8px;text-align:right;">Price</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>"""


async def notify_customer_order_confirmation(
    customer_email: str,
    customer_name: str,
    order_id: str,
    items: list[dict],
    total: float,
    shipping_state: str,
    shipping_cost: float,
) -> bool:
    """Send order confirmation email to the customer."""
    items_table = _build_order_items_table(items)

    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
      {_BRAND_HEADER}
      <div style="padding:24px;background-color:#FBF9F6;">
        <h2 style="color:#0D2A22;margin-top:0;">Order Confirmed</h2>
        <p>Dear <strong>{customer_name}</strong>,</p>
        <p>Thank you for your purchase. Your order has been received and is being processed.</p>
        <div style="background:#fff;border:1px solid #D4AF37;border-radius:8px;padding:16px;margin:16px 0;">
          <p style="margin:4px 0;"><strong>Order ID:</strong> {order_id}</p>
          <p style="margin:4px 0;"><strong>Shipping to:</strong> {shipping_state}</p>
          <p style="margin:4px 0;"><strong>Shipping cost:</strong> &#8358;{shipping_cost:,.0f}</p>
          <p style="margin:4px 0;font-size:18px;"><strong>Total:</strong> &#8358;{total:,.0f}</p>
        </div>
        {items_table}
        <p style="color:#666;">We&rsquo;ll notify you once your order has been shipped.</p>
      </div>
      {_BRAND_FOOTER}
    </body></html>"""

    return await send_brevo_email(
        to_email=customer_email,
        to_name=customer_name,
        subject=f"Order Confirmed \u2014 {order_id}",
        html_content=html,
    )


async def notify_status_change(
    customer_email: str,
    customer_name: str,
    order_id: str,
    new_status: str,
) -> bool:
    """Notify customer when order status changes."""
    status_labels = {
        "paid": "Payment confirmed",
        "processing": "Your order is being prepared",
        "shipped": "Your order has been shipped",
        "delivered": "Your order has been delivered",
        "cancelled": "Your order has been cancelled",
    }
    message = status_labels.get(new_status, f"Order status: {new_status}")

    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
      {_BRAND_HEADER}
      <div style="padding:24px;background-color:#FBF9F6;">
        <h2 style="color:#0D2A22;margin-top:0;">Order Update</h2>
        <p>Dear <strong>{customer_name}</strong>,</p>
        <div style="background:#fff;border-left:4px solid #D4AF37;padding:16px;margin:16px 0;">
          <p style="margin:0;font-size:16px;">{message}</p>
          <p style="margin:8px 0 0;color:#666;">Order ID: {order_id}</p>
        </div>
      </div>
      {_BRAND_FOOTER}
    </body></html>"""

    return await send_brevo_email(
        to_email=customer_email,
        to_name=customer_name,
        subject=f"Order Update \u2014 {order_id}",
        html_content=html,
    )


# ---------------------------------------------------------------------------
# Notification Orchestrators
# ---------------------------------------------------------------------------

ASIKO_ADMIN_EMAIL = "hello@asikoboutique.com"


async def on_order_created(order_id: str) -> None:
    """Called after checkout: sends customer confirmation + admin notification."""
    order = await fetch_order_by_id(order_id)
    if not order:
        return

    items = await fetch_order_items(order_id)
    total = float(order["total_amount"])
    shipping_cost = float(order["shipping_cost"]) if order.get("shipping_cost") else 0
    customer_email = order["customer_email"]
    metadata = _parse_metadata(order.get("metadata"))
    customer_name = metadata.get("customer_name", "Customer")
    shipping_state = order.get("shipping_state", "")

    # 1) Customer confirmation
    await notify_customer_order_confirmation(
        customer_email=customer_email,
        customer_name=customer_name,
        order_id=order_id,
        items=items,
        total=total,
        shipping_state=shipping_state,
        shipping_cost=shipping_cost,
    )

    # 2) Admin notification
    items_table = _build_order_items_table(items)
    admin_html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
      {_BRAND_HEADER}
      <div style="padding:24px;background-color:#FBF9F6;">
        <h2 style="color:#0D2A22;margin-top:0;">New Order Received</h2>
        <p>A new order has been placed on ASIKO Boutique.</p>
        <div style="background:#fff;border:1px solid #D4AF37;border-radius:8px;padding:16px;margin:16px 0;">
          <p style="margin:4px 0;"><strong>Order ID:</strong> {order_id}</p>
          <p style="margin:4px 0;"><strong>Customer:</strong> {customer_email}</p>
          <p style="margin:4px 0;"><strong>Total:</strong> &#8358;{total:,.0f}</p>
        </div>
        {items_table}
      </div>
      {_BRAND_FOOTER}
    </body></html>"""

    await send_brevo_email(
        to_email=ASIKO_ADMIN_EMAIL,
        to_name="ASIKO Admin",
        subject=f"New Order \u2014 {order_id}",
        html_content=admin_html,
    )


async def on_order_status_changed(order_id: str, new_status: str) -> None:
    """Called when order status is updated: notifies the customer."""
    order = await fetch_order_by_id(order_id)
    if not order:
        return

    customer_email = order["customer_email"]
    metadata = _parse_metadata(order.get("metadata"))
    customer_name = metadata.get("customer_name", "Customer")

    await notify_status_change(
        customer_email=customer_email,
        customer_name=customer_name,
        order_id=order_id,
        new_status=new_status,
    )


# ---------------------------------------------------------------------------
# Webhook Handlers
# ---------------------------------------------------------------------------

async def order_status_webhook(request: Request) -> JSONResponse:
    """Internal webhook: update order status and notify customer."""
    body = await request.json()
    order_id = body.get("order_id")
    new_status = body.get("status")

    if not order_id or not new_status:
        return JSONResponse({"error": "Missing order_id or status"}, status_code=400)

    valid_statuses = ["pending", "paid", "processing", "shipped", "delivered", "cancelled"]
    if new_status not in valid_statuses:
        return JSONResponse({"error": f"Invalid status: {new_status}"}, status_code=400)

    order = await fetch_order_by_id(order_id)
    if not order:
        return JSONResponse({"error": "Order not found"}, status_code=404)

    await update_order_status(order_id, new_status)

    # Send status notification to customer
    await on_order_status_changed(order_id, new_status)

    return JSONResponse({
        "status": "updated",
        "order_id": order_id,
        "new_status": new_status,
    })


async def paystack_webhook(request: Request) -> JSONResponse:
    """Paystack webhook: verify payment and trigger notifications."""
    raw_body = await request.body()
    signature = request.headers.get("x-paystack-signature")

    if not signature:
        return JSONResponse({"error": "Missing signature"}, status_code=401)

    # Verify signature
    if PAYSTACK_SECRET_KEY and not PAYSTACK_SECRET_KEY.startswith("your_"):
        expected = hmac.new(
            PAYSTACK_SECRET_KEY.encode("utf-8"),
            raw_body,
            hashlib.sha512,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            logger.warning("Invalid Paystack signature")
            return JSONResponse({"error": "Invalid signature"}, status_code=401)

    try:
        event = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    event_type = event.get("event")
    data = event.get("data", {})

    if event_type == "charge.success":
        reference = data.get("reference", "")
        if not reference:
            return JSONResponse({"error": "No reference"}, status_code=400)

        order = await fetch_order_by_id(reference)
        if not order:
            logger.info("Paystack reference %s did not match any order", reference)
            return JSONResponse({"received": True})

        # Mark as paid
        await update_order_status(str(order["id"]), "paid")

        # Send customer confirmation + store owner notifications
        await on_order_created(str(order["id"]))

        logger.info("Payment verified for order %s", reference)

    return JSONResponse({"received": True})


async def send_test_email(request: Request) -> JSONResponse:
    """Debug endpoint: send a test email via Brevo to verify config."""
    body = await request.json()
    to_email = body.get("email", "")
    if not to_email:
        return JSONResponse({"error": "Missing email"}, status_code=400)

    ok = await send_brevo_email(
        to_email=to_email,
        to_name="Test",
        subject="ASIKO Boutique - Test Email",
        html_content=f"""
        <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
          {_BRAND_HEADER}
          <div style="padding:24px;background-color:#FBF9F6;">
            <h2 style="color:#0D2A22;margin-top:0;">Email Integration Working</h2>
            <p>This is a test email from ASIKO Boutique. Your Brevo integration is configured correctly.</p>
          </div>
          {_BRAND_FOOTER}
        </body></html>""",
    )

    return JSONResponse({"sent": ok, "to": to_email})


# ---------------------------------------------------------------------------
# Meshy 3D Pipeline Webhook Receiver
# Receives real-time task completion events from Meshy API
# ---------------------------------------------------------------------------

async def meshy_webhook_receiver(request: Request) -> Response:
    """
    Deprecated: Meshy webhook kept for backward compatibility.
    New OSS Gradio pipeline handles processing directly in pipeline_daemon.
    Returns simple acknowledgment for any POST request.
    """
    if request.method != "POST":
        return Response(status_code=405, content="Method Not Allowed")
    
    # Deprecated endpoint - return acknowledgment
    return Response(status_code=200, content="DEPRECATED_ENDPOINT_ACKNOWLEDGED")


webhook_routes = [
    Route("/webhooks/order-status", order_status_webhook, methods=["POST"]),
    Route("/webhooks/test-email", send_test_email, methods=["POST"]),
    Route("/api/v1/webhooks/meshy", meshy_webhook_receiver, methods=["POST"]),
]
