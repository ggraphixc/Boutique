# ASIKO Boutique — Email System: Complete Implementation Guide

## TABLE OF CONTENTS

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Brevo API Integration](#3-brevo-api-integration)
4. [Email Service Module](#4-email-service-module)
5. [Email Templates & HTML Design](#5-email-templates--html-design)
6. [Email Types & Triggers](#6-email-types--triggers)
7. [Flow Diagrams](#7-flow-diagrams)
8. [Configuration & Settings](#8-configuration--settings)
9. [Admin Controls](#9-admin-controls)
10. [Error Handling & Graceful Degradation](#10-error-handling--graceful-degradation)
11. [Database Schema](#11-database-schema)
12. [Testing & Verification](#12-testing--verification)
13. [Code Reference](#13-code-reference)

---

## 1. Overview

ASIKO Boutique uses **Brevo** (formerly Sendinblue) as its email service provider for all transactional emails. Brevo provides a SMTP API that sends HTML emails via REST calls — no SMTP server configuration needed on the application side.

### Email Types Supported
| Email | Trigger | Async? |
|-------|---------|--------|
| Welcome Greeting | Customer registers | Yes |
| Password Reset | `/forgot-password` submit | Yes |
| Newsletter Confirmation | `/newsletter/subscribe` submit | Yes |
| Order Confirmation | Checkout submit | Yes |
| Order Status Update | Admin changes order status | Yes |
| Admin Notification | New order placed | Yes |
| Test Email | Debug endpoint | Yes |

### Key Design Decisions
- **All emails are HTML** — rich branded templates, not plain text
- **All emails are async** — `asyncio.create_task()` so page load doesn't block
- **Graceful degradation** — if Brevo API key is placeholder, emails skip silently (no crashes)
- **Two sender implementations exist** — centralized `brevo.py` and inline `webhooks.py` (both functional, same API)
- **Admin controls** — every email type can be toggled on/off from admin settings

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    EMAIL SYSTEM ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────┐ │
│  │  TRIGGER      │     │  SERVICE     │     │  BREVO API       │ │
│  │  LAYER        │────▶│  LAYER       │────▶│  (REST)          │ │
│  │              │     │              │     │                  │ │
│  │ customer.py  │     │ brevo.py     │     │ smtp/email       │ │
│  │ checkout.py  │     │ webhooks.py  │     │ contacts         │ │
│  │ webhooks.py  │     │              │     │                  │ │
│  └──────────────┘     └──────────────┘     └──────────────────┘ │
│         │                    │                     │             │
│         │                    │                     │             │
│         ▼                    ▼                     ▼             │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────┐ │
│  │  TEMPLATES   │     │  SETTINGS    │     │  DATABASE        │ │
│  │              │     │              │     │                  │ │
│  │ HTML inline  │     │ store_settings│     │ customers        │ │
│  │ Brand header │     │ .env config  │     │ orders           │ │
│  │ Brand footer │     │ Admin toggles│     │ password_reset   │ │
│  └──────────────┘     └──────────────┘     └──────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow
1. **Trigger** — User action (register, checkout, etc.) or admin action (status change)
2. **Service** — `brevo.py` or `webhooks.py` builds HTML email
3. **API Call** — POST to `https://api.brevo.com/v3/smtp/email`
4. **Response** — 201 = sent, 4xx/5xx = failed (logged, not raised)
5. **Database** — Token stored (password reset), order updated

---

## 3. Brevo API Integration

### API Details
- **Base URL:** `https://api.brevo.com/v3`
- **Auth:** API key in `api-key` header
- **Endpoint:** `POST /smtp/email`
- **Rate limit:** 300 emails/day (free tier), 40,000/month (starter)

### Authentication
```python
headers = {
    "accept": "application/json",
    "content-type": "application/json",
    "api-key": BREVO_API_KEY,  # From .env
}
```

### Request Payload
```python
{
    "sender": {
        "name": "ASIKO Boutique",
        "email": "ggraphixc@gmail.com"  # From .env
    },
    "to": [
        {"email": "customer@example.com", "name": "Customer Name"}
    ],
    "subject": "Order Confirmed — asiko_abc123",
    "htmlContent": "<html>...</html>"
}
```

### Response
- **201 Created:** Email sent successfully
  ```json
  {"messageId": "<202606141507.32017228458@smtp-relay.mailin.fr>"}
  ```
- **400 Bad Request:** Invalid payload
- **401 Unauthorized:** Invalid API key

### Contact Sync (Newsletter)
- **Endpoint:** `POST /contacts`
- **Purpose:** Add subscriber to Brevo marketing list
- **Payload:**
  ```python
  {
      "email": "subscriber@example.com",
      "listIds": [2],  # Newsletter list
      "updateEnabled": True
  }
  ```

---

## 4. Email Service Module

### Primary: `app/services/brevo.py`

This is the **centralized email service** used by customer routes (register, password reset, newsletter).

#### Core Function
```python
async def send_transactional_email(
    to_email: str,
    subject: str,
    html_content: str,
    sender_name: str = "ASIKO Boutique",
) -> bool:
    """
    Send a transactional HTML email via Brevo SMTP API.
    
    Returns True on success, False on failure.
    Logs warning when API key is placeholder.
    """
```

**How it works:**
1. Checks if `BREVO_API_KEY` is configured (not empty, not starting with `your_`)
2. Builds HTTP headers with API key
3. Constructs payload with sender, recipient, subject, HTML content
4. Sends POST request to Brevo API with 15-second timeout
5. Returns `True` if status is 200 or 201
6. Logs error and returns `False` on failure

#### Email Template Functions

| Function | Purpose | Subject Line |
|----------|---------|--------------|
| `send_welcome_email(to_email, customer_name)` | New account greeting | "Welcome to ASIKO Boutique!" |
| `send_forgot_password_email(to_email, customer_name, reset_url)` | Password reset link | "Reset Your Password — ASIKO Boutique" |
| `send_newsletter_confirmation(to_email)` | Subscription confirm | "Welcome to the ASIKO Newsletter" |

#### Contact Sync Function
```python
async def sync_to_brevo_waitlist_audience(
    email: str,
    list_id: int = 2,
) -> bool:
    """Add or update a contact in a Brevo marketing audience list."""
```

### Secondary: `app/routes/webhooks.py`

This file contains a **separate inline email sender** and additional email templates for order-related emails.

#### Inline Sender
```python
async def send_brevo_email(
    to_email: str,
    to_name: str,
    subject: str,
    html_content: str,
) -> bool:
    """Send a transactional email via Brevo SMTP API."""
```

Same logic as `brevo.py` but with an additional `to_name` parameter.

#### Order Email Functions

| Function | Purpose | Called By |
|----------|---------|-----------|
| `notify_customer_order_confirmation(...)` | Full order confirmation with items table | `on_order_created()` |
| `notify_status_change(...)` | Status update notification | `on_order_status_changed()` |
| `on_order_created(order_id)` | Orchestrator: sends customer + admin emails | Checkout flow |
| `on_order_status_changed(order_id, new_status)` | Orchestrator: notifies customer | Admin status update |

#### Test Email Endpoint
```python
async def send_test_email(request: Request) -> JSONResponse:
    """Debug endpoint: send a test email via Brevo to verify config."""
    # POST /webhooks/test-email
    # Body: {"email": "test@example.com"}
```

---

## 5. Email Templates & HTML Design

### Brand Wrapper System

Every email is wrapped in a consistent brand frame:

#### Brand Header
```html
<div style="background-color:#0D2A22;color:#fff;padding:24px;text-align:center;">
  <h1 style="margin:0;font-size:24px;letter-spacing:2px;">ASIKO BOUTIQUE</h1>
  <p style="margin:4px 0 0;font-size:13px;opacity:.8;">Contemporary Nigerian Fashion</p>
</div>
```
- **Color:** Deep emerald (#0D2A22)
- **Font:** Arial, 24px, letter-spacing 2px
- **Tagline:** "Contemporary Nigerian Fashion"

#### Brand Footer
```html
<div style="background-color:#D4AF37;padding:12px;text-align:center;color:#0D2A22;">
  <p style="margin:0;font-size:12px;">&copy; 2026 ASIKO Boutique &mdash; All rights reserved</p>
</div>
```
- **Color:** Gold (#D4AF37)
- **Text:** Deep emerald on gold
- **Copyright:** Current year

### Email-Specific Templates

#### 1. Welcome Email
```
┌─────────────────────────────────────┐
│  ASIKO BOUTIQUE (emerald header)    │
├─────────────────────────────────────┤
│                                     │
│  Welcome to ASIKO!                  │
│                                     │
│  Dear {customer_name},              │
│                                     │
│  Thank you for joining ASIKO        │
│  Boutique. We're excited to have    │
│  you.                               │
│                                     │
│  Explore our curated collection     │
│  of authentic Nigerian fashion...   │
│                                     │
│  ┌─────────────────────────┐        │
│  │    [Start Shopping]     │        │
│  │    (Gold CTA button)    │        │
│  └─────────────────────────┘        │
│                                     │
│  If you ever need help, reply to    │
│  this email or visit our Help       │
│  Center.                            │
│                                     │
├─────────────────────────────────────┤
│  © 2026 ASIKO Boutique (gold footer)│
└─────────────────────────────────────┘
```

#### 2. Password Reset Email
```
┌─────────────────────────────────────┐
│  ASIKO BOUTIQUE (emerald header)    │
├─────────────────────────────────────┤
│                                     │
│  Reset Your Password                │
│                                     │
│  Dear {customer_name},              │
│                                     │
│  We received a request to reset     │
│  your password. Click the button    │
│  below to set a new one.            │
│                                     │
│  ┌─────────────────────────┐        │
│  │    [Reset Password]     │        │
│  │    (Deep emerald CTA)   │        │
│  └─────────────────────────┘        │
│                                     │
│  This link expires in 1 hour.       │
│  If you didn't request this,        │
│  ignore this email.                 │
│                                     │
├─────────────────────────────────────┤
│  © 2026 ASIKO Boutique (gold footer)│
└─────────────────────────────────────┘
```

**Reset URL format:** `https://asikoboutique.com/reset-password?token={64-char-hex}`

#### 3. Newsletter Confirmation
```
┌─────────────────────────────────────┐
│  ASIKO BOUTIQUE (emerald header)    │
├─────────────────────────────────────┤
│                                     │
│  You're Subscribed!                 │
│                                     │
│  Thank you for subscribing to the   │
│  ASIKO Boutique newsletter.         │
│                                     │
│  You'll receive updates on new      │
│  arrivals, exclusive offers, and    │
│  styling inspiration.               │
│                                     │
│  ┌─────────────────────────┐        │
│  │  [Browse New Arrivals]  │        │
│  │    (Gold CTA button)    │        │
│  └─────────────────────────┘        │
│                                     │
├─────────────────────────────────────┤
│  © 2026 ASIKO Boutique (gold footer)│
└─────────────────────────────────────┘
```

#### 4. Order Confirmation (webhooks.py — Full Version)
```
┌─────────────────────────────────────┐
│  ASIKO BOUTIQUE (emerald header)    │
├─────────────────────────────────────┤
│                                     │
│  Order Confirmed                    │
│                                     │
│  Dear {customer_name},              │
│                                     │
│  Thank you for your purchase.       │
│  Your order has been received and   │
│  is being processed.                │
│                                     │
│  ┌─────────────────────────┐        │
│  │ Order ID: {order_id}    │        │
│  │ Shipping to: {state}    │        │
│  │ Shipping cost: ₦{cost}  │        │
│  │ Total: ₦{total}         │        │
│  └─────────────────────────┘        │
│                                     │
│  ┌─────────────────────────────┐    │
│  │ Product      │ Qty │ Price  │    │
│  ├──────────────┼─────┼────────┤    │
│  │ {item_name}  │  1  │ ₦8,000 │    │
│  │ {item_name}  │  2  │ ₦4,500 │    │
│  └─────────────────────────────┘    │
│                                     │
│  We'll notify you once your order   │
│  has been shipped.                  │
│                                     │
├─────────────────────────────────────┤
│  © 2026 ASIKO Boutique (gold footer)│
└─────────────────────────────────────┘
```

#### 5. Order Status Update
```
┌─────────────────────────────────────┐
│  ASIKO BOUTIQUE (emerald header)    │
├─────────────────────────────────────┤
│                                     │
│  Order Update                       │
│                                     │
│  Dear {customer_name},              │
│                                     │
│  ┌─────────────────────────┐        │
│  │ ▌ {status_message}      │        │
│  │   Order ID: {order_id}  │        │
│  └─────────────────────────┘        │
│                                     │
│  (Gold left border accent)          │
│                                     │
├─────────────────────────────────────┤
│  © 2026 ASIKO Boutique (gold footer)│
└─────────────────────────────────────┘
```

**Status messages:**
| Status | Message |
|--------|---------|
| `paid` | Payment confirmed |
| `processing` | Your order is being prepared |
| `shipped` | Your order has been shipped |
| `delivered` | Your order has been delivered |
| `cancelled` | Your order has been cancelled |

#### 6. Admin Notification (New Order)
```
┌─────────────────────────────────────┐
│  ASIKO BOUTIQUE (emerald header)    │
├─────────────────────────────────────┤
│                                     │
│  New Order Received                 │
│                                     │
│  A new order has been placed on     │
│  ASIKO Boutique.                    │
│                                     │
│  ┌─────────────────────────┐        │
│  │ Order ID: {order_id}    │        │
│  │ Customer: {email}       │        │
│  │ Total: ₦{total}         │        │
│  └─────────────────────────┘        │
│                                     │
│  ┌─────────────────────────────┐    │
│  │ (Items table)               │    │
│  └─────────────────────────────┘    │
│                                     │
├─────────────────────────────────────┤
│  © 2026 ASIKO Boutique (gold footer)│
└─────────────────────────────────────┘
```

#### 7. Test Email
```
┌─────────────────────────────────────┐
│  ASIKO BOUTIQUE (emerald header)    │
├─────────────────────────────────────┤
│                                     │
│  Email Integration Working          │
│                                     │
│  This is a test email from ASIKO    │
│  Boutique. Your Brevo integration   │
│  is configured correctly.           │
│                                     │
├─────────────────────────────────────┤
│  © 2026 ASIKO Boutique (gold footer)│
└─────────────────────────────────────┘
```

---

## 6. Email Types & Triggers

### 6.1 Welcome Email

**Trigger:** Customer successfully registers at `/register`

**Code path:**
```
POST /register
  → customer.py: register_submit()
    → INSERT INTO customers
    → asyncio.create_task(send_welcome_email(email, name))
      → brevo.py: send_welcome_email()
        → send_transactional_email()
          → POST https://api.brevo.com/v3/smtp/email
```

**Key code (`customer.py:72-77`):**
```python
# Send welcome greeting email (non-blocking)
try:
    from app.services.brevo import send_welcome_email
    import asyncio
    asyncio.create_task(send_welcome_email(email, full_name or email.split("@")[0]))
except Exception:
    pass
```

**Template location:** `app/services/brevo.py:107-127`

### 6.2 Password Reset Email

**Trigger:** Customer submits email at `/forgot-password`

**Code path:**
```
POST /forgot-password
  → customer.py: forgot_password_submit()
    → SELECT FROM customers WHERE email = $1
    → Generate 64-char hex token (secrets.token_hex(32))
    → INSERT INTO password_reset_tokens (1hr expiry)
    → asyncio.create_task(send_forgot_password_email(email, name, reset_url))
      → brevo.py: send_forgot_password_email()
        → send_transactional_email()
          → POST https://api.brevo.com/v3/smtp/email
    → Redirect to /forgot-password?success=...
```

**Key code (`customer.py:325-330`):**
```python
reset_url = f"{request.base_url}reset-password?token={token}"
try:
    from app.services.brevo import send_forgot_password_email
    import asyncio
    asyncio.create_task(send_forgot_password_email(email, customer["full_name"] or "Customer", reset_url))
except Exception:
    pass
```

**Token flow:**
1. Token generated: `secrets.token_hex(32)` → 64-character hex string
2. Stored in `password_reset_tokens` table with `expires_at = now() + 1 hour`
3. Reset URL: `https://asikoboutique.com/reset-password?token={token}`
4. Customer clicks link → `/reset-password?token=...` page
5. Customer enters new password → `POST /reset-password`
6. Token validated, password updated, token marked as `used = TRUE`

**Template location:** `app/services/brevo.py:84-104`

### 6.3 Newsletter Confirmation

**Trigger:** Customer submits email at footer newsletter form

**Code path:**
```
POST /newsletter/subscribe
  → customer.py: newsletter_subscribe()
    → asyncio.create_task(sync_to_brevo_waitlist_audience(email, list_id=2))
    → asyncio.create_task(send_newsletter_confirmation(email))
      → brevo.py: send_newsletter_confirmation()
        → send_transactional_email()
          → POST https://api.brevo.com/v3/smtp/email
    → Redirect to /?success=...
```

**Key code (`customer.py:395-401`):**
```python
try:
    from app.services.brevo import sync_to_brevo_waitlist_audience, send_newsletter_confirmation
    import asyncio
    asyncio.create_task(sync_to_brevo_waitlist_audience(email, list_id=2))
    asyncio.create_task(send_newsletter_confirmation(email))
except Exception:
    pass
```

**Two actions happen:**
1. `sync_to_brevo_waitlist_audience()` — Adds/updates contact in Brevo marketing list (ID: 2)
2. `send_newsletter_confirmation()` — Sends confirmation email to subscriber

**Template location:** `app/services/brevo.py:130-147`

### 6.4 Order Confirmation Email

**Trigger:** Successful checkout at `/checkout/submit`

**Code path:**
```
POST /checkout/submit
  → checkout.py: checkout_submit()
    → Atomic transaction (SELECT FOR UPDATE)
    → Create order + order_items
    → Decrement stock
    → Initialize OPay payment
    → asyncio.create_task(send_transactional_email(...))
    → Redirect to OPay payment page
```

**Key code (`checkout.py:192-205`):**
```python
# Brevo email dispatch with graceful fallback
try:
    email_body = (
        f"<h3>Order #{order_id} Confirmed</h3>"
        f"<p>Thank you {first_name}. Your fashion order total is "
        f"₦{grand_total:,.2f}. Outbound logistics route: {state_row['name']}.</p>"
    )
    await send_transactional_email(
        to_email=email,
        subject=f"ASIKO Boutique Confirmation - Order #{order_id}",
        html_content=email_body,
    )
except Exception:
    pass  # Suppress failures from missing/placeholder API keys
```

**Note:** This uses a simpler HTML body compared to `webhooks.py`'s full branded template.

### 6.5 Order Confirmation (Full Version via Webhooks)

**Trigger:** `on_order_created(order_id)` called after order creation

**Code path:**
```
on_order_created(order_id)
  → webhooks.py: notify_customer_order_confirmation()
    → Fetches order + items from DB
    → Builds items table HTML
    → send_brevo_email() to customer
  → send_brevo_email() to admin (hello@asikoboutique.com)
```

**Key code (`webhooks.py:208-256`):**
```python
async def on_order_created(order_id: str) -> None:
    order = await fetch_order_by_id(order_id)
    items = await fetch_order_items(order_id)
    
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
    await send_brevo_email(
        to_email=ASIKO_ADMIN_EMAIL,  # hello@asikoboutique.com
        to_name="ASIKO Admin",
        subject=f"New Order — {order_id}",
        html_content=admin_html,
    )
```

### 6.6 Order Status Update Email

**Trigger:** Admin changes order status via `/admin/orders/{order_id}/status`

**Code path:**
```
POST /admin/orders/{order_id}/status
  → admin_sections.py: update_order_status()
    → UPDATE orders SET status = $2
    → asyncio.create_task(on_order_status_changed(order_id, new_status))
      → webhooks.py: on_order_status_changed()
        → Fetches order from DB
        → notify_status_change()
          → send_brevo_email() to customer
```

**Status messages mapping (`webhooks.py:170-177`):**
```python
status_labels = {
    "paid": "Payment confirmed",
    "processing": "Your order is being prepared",
    "shipped": "Your order has been shipped",
    "delivered": "Your order has been delivered",
    "cancelled": "Your order has been cancelled",
}
```

### 6.7 Test Email

**Trigger:** POST to `/webhooks/test-email`

**Code path:**
```
POST /webhooks/test-email
  → webhooks.py: send_test_email()
    → send_brevo_email()
      → POST https://api.brevo.com/v3/smtp/email
    → JSONResponse({"sent": True/False, "to": email})
```

**Request body:**
```json
{"email": "test@example.com"}
```

**Response:**
```json
{"sent": true, "to": "test@example.com"}
```

---

## 7. Flow Diagrams

### 7.1 Welcome Email Flow
```
Customer                    Server                    Brevo API
   │                          │                          │
   │  POST /register          │                          │
   │  (email, password, name) │                          │
   │─────────────────────────▶│                          │
   │                          │                          │
   │                    ┌─────┴─────┐                    │
   │                    │ Validate  │                    │
   │                    │ form data │                    │
   │                    └─────┬─────┘                    │
   │                          │                          │
   │                    ┌─────┴─────┐                    │
   │                    │ Check if  │                    │
   │                    │ email     │                    │
   │                    │ exists    │                    │
   │                    └─────┬─────┘                    │
   │                          │                          │
   │                    ┌─────┴─────┐                    │
   │                    │ INSERT    │                    │
   │                    │ customer  │                    │
   │                    └─────┬─────┘                    │
   │                          │                          │
   │                    ┌─────┴─────┐                    │
   │                    │ Set       │                    │
   │                    │ session   │                    │
   │                    └─────┬─────┘                    │
   │                          │                          │
   │                    ┌─────┴─────┐                    │
   │                    │ asyncio   │                    │
   │                    │ .create   │                    │
   │                    │ _task()   │                    │
   │                    └─────┬─────┘                    │
   │                          │                          │
   │  Redirect /account       │                          │
   │◀─────────────────────────│                          │
   │                          │                          │
   │                          │  POST /v3/smtp/email     │
   │                          │─────────────────────────▶│
   │                          │                          │
   │                          │  201 Created             │
   │                          │◀─────────────────────────│
   │                          │                          │
   │  (page loads)            │                          │
   │                          │                          │
   │                          │  (email delivered)       │
   │                          │                          │
   │  Welcome email arrives   │                          │
   │◀─────────────────────────────────────────────────────│
```

### 7.2 Password Reset Flow
```
Customer                    Server                    Brevo API
   │                          │                          │
   │  GET /forgot-password    │                          │
   │─────────────────────────▶│                          │
   │                          │                          │
   │  Render form             │                          │
   │◀─────────────────────────│                          │
   │                          │                          │
   │  POST /forgot-password   │                          │
   │  (email)                 │                          │
   │─────────────────────────▶│                          │
   │                          │                          │
   │                    ┌─────┴─────┐                    │
   │                    │ Check if  │                    │
   │                    │ customer  │                    │
   │                    │ exists    │                    │
   │                    └─────┬─────┘                    │
   │                          │                          │
   │                    ┌─────┴─────┐                    │
   │                    │ Generate  │                    │
   │                    │ token     │                    │
   │                    │ (64-char) │                    │
   │                    └─────┬─────┘                    │
   │                          │                          │
   │                    ┌─────┴─────┐                    │
   │                    │ Store     │                    │
   │                    │ token     │                    │
   │                    │ (1hr TTL) │                    │
   │                    └─────┬─────┘                    │
   │                          │                          │
   │                    ┌─────┴─────┐                    │
   │                    │ Build     │                    │
   │                    │ reset URL │                    │
   │                    └─────┬─────┘                    │
   │                          │                          │
   │                    ┌─────┴─────┐                    │
   │                    │ Send email│                    │
   │                    │ (async)   │                    │
   │                    └─────┬─────┘                    │
   │                          │                          │
   │  Redirect ?success=...   │                          │
   │◀─────────────────────────│                          │
   │                          │                          │
   │                          │  POST /v3/smtp/email     │
   │                          │─────────────────────────▶│
   │                          │                          │
   │  Email with reset link   │                          │
   │◀─────────────────────────────────────────────────────│
   │                          │                          │
   │  Click link              │                          │
   │  GET /reset-password?token=...                      │
   │─────────────────────────▶│                          │
   │                          │                          │
   │  Render form             │                          │
   │◀─────────────────────────│                          │
   │                          │                          │
   │  POST /reset-password    │                          │
   │  (token, password)       │                          │
   │─────────────────────────▶│                          │
   │                          │                          │
   │                    ┌─────┴─────┐                    │
   │                    │ Validate  │                    │
   │                    │ token     │                    │
   │                    │ (not used,│                    │
   │                    │  not exp) │                    │
   │                    └─────┬─────┘                    │
   │                          │                          │
   │                    ┌─────┴─────┐                    │
   │                    │ Update    │                    │
   │                    │ password  │                    │
   │                    │ Mark used │                    │
   │                    └─────┬─────┘                    │
   │                          │                          │
   │  Redirect /login?success │                          │
   │◀─────────────────────────│                          │
```

### 7.3 Order Confirmation Flow
```
Customer                    Server                    Brevo API
   │                          │                          │
   │  POST /checkout/submit   │                          │
   │─────────────────────────▶│                          │
   │                          │                          │
   │                    ┌─────┴─────┐                    │
   │                    │ Atomic    │                    │
   │                    │ transaction│                   │
   │                    │ (SELECT   │                    │
   │                    │ FOR UPDATE│                    │
   │                    └─────┬─────┘                    │
   │                          │                          │
   │                    ┌─────┴─────┐                    │
   │                    │ Create    │                    │
   │                    │ order +   │                    │
   │                    │ items     │                    │
   │                    └─────┬─────┘                    │
   │                          │                          │
   │                    ┌─────┴─────┐                    │
   │                    │ Decrement │                    │
   │                    │ stock     │                    │
   │                    └─────┬─────┘                    │
   │                          │                          │
   │                    ┌─────┴─────┐                    │
   │                    │ Initialize│                    │
   │                    │ OPay      │                    │
   │                    └─────┬─────┘                    │
   │                          │                          │
   │                    ┌─────┴─────┐                    │
   │                    │ Send email│                    │
   │                    │ (async)   │                    │
   │                    └─────┬─────┘                    │
   │                          │                          │
   │  Redirect to OPay        │                          │
   │◀─────────────────────────│                          │
   │                          │                          │
   │                          │  POST /v3/smtp/email     │
   │                          │─────────────────────────▶│
   │                          │                          │
   │  Order confirmation      │                          │
   │  email arrives           │                          │
   │◀─────────────────────────────────────────────────────│
```

### 7.4 Admin Status Change Flow
```
Admin                       Server                    Brevo API   Customer
   │                          │                          │           │
   │  POST /admin/orders/     │                          │           │
   │  {order_id}/status       │                          │           │
   │  (status: "shipped")     │                          │           │
   │─────────────────────────▶│                          │           │
   │                          │                          │           │
   │                    ┌─────┴─────┐                    │           │
   │                    │ UPDATE    │                    │           │
   │                    │ orders    │                    │           │
   │                    │ SET status│                    │           │
   │                    └─────┬─────┘                    │           │
   │                          │                          │           │
   │                    ┌─────┴─────┐                    │           │
   │                    │ asyncio   │                    │           │
   │                    │ .create   │                    │           │
   │                    │ _task()   │                    │           │
   │                    └─────┬─────┘                    │           │
   │                          │                          │           │
   │  HTMX response           │                          │           │
   │◀─────────────────────────│                          │           │
   │                          │                          │           │
   │                          │  on_order_status_changed │           │
   │                          │──────────┐               │           │
   │                          │          │               │           │
   │                          │  ┌───────┴───────┐      │           │
   │                          │  │ Fetch order   │      │           │
   │                          │  │ from DB       │      │           │
   │                          │  └───────┬───────┘      │           │
   │                          │          │               │           │
   │                          │  ┌───────┴───────┐      │           │
   │                          │  │ Build status  │      │           │
   │                          │  │ email HTML    │      │           │
   │                          │  └───────┬───────┘      │           │
   │                          │          │               │           │
   │                          │  POST /v3/smtp/email    │           │
   │                          │─────────────────────────▶│           │
   │                          │                          │           │
   │                          │  201 Created             │           │
   │                          │◀─────────────────────────│           │
   │                          │                          │           │
   │                          │                          │  Status   │
   │                          │                          │  update   │
   │                          │                          │  email    │
   │                          │                          │──────────▶│
```

---

## 8. Configuration & Settings

### 8.1 Environment Variables (`.env`)

```bash
# Brevo API Key (required for email)
BREVO_API_KEY="xkeysib-your_api_key_here"

# Sender email (must be verified in Brevo)
SENDER_EMAIL="ggraphixc@gmail.com"
```

### 8.2 Database Settings (`store_settings` table)

| Column | Type | Default | Purpose |
|--------|------|---------|---------|
| `brevo_api_key` | VARCHAR(500) | "" | Brevo API key (overrides .env) |
| `sender_email` | VARCHAR(500) | "orders@asikoboutique.com" | From address |
| `sender_name` | VARCHAR(500) | "ASIKO Boutique" | Sender display name |
| `admin_email` | VARCHAR(500) | "hello@asikoboutique.com" | Admin notification address |
| `email_welcome_enabled` | BOOLEAN | TRUE | Send welcome email on register |
| `email_order_enabled` | BOOLEAN | TRUE | Send order confirmation |
| `email_shipping_enabled` | BOOLEAN | TRUE | Send shipping updates |
| `email_newsletter_enabled` | BOOLEAN | TRUE | Send newsletter confirmation |
| `email_password_reset_enabled` | BOOLEAN | TRUE | Send password reset email |

### 8.3 Settings Service Integration

```python
# app/settings_service.py
DEFAULTS = {
    "brevo_api_key": "",
    "sender_email": "orders@asikoboutique.com",
    "sender_name": "ASIKO Boutique",
    "admin_email": "hello@asikoboutique.com",
    "email_welcome_enabled": True,
    "email_order_enabled": True,
    "email_shipping_enabled": True,
    "email_newsletter_enabled": True,
    "email_password_reset_enabled": True,
}

# BOOLEAN_KEYS includes email toggles
BOOLEAN_KEYS = {
    ...
    "email_welcome_enabled", "email_order_enabled", "email_shipping_enabled",
    "email_newsletter_enabled", "email_password_reset_enabled",
}
```

### 8.4 How Settings Are Used

1. **At startup:** `brevo.py` reads `BREVO_API_KEY` and `SENDER_EMAIL` from `.env`
2. **On email send:** `send_transactional_email()` checks if API key is valid
3. **Admin can override:** Settings saved to `store_settings` table via admin panel
4. **Cache invalidation:** `save_settings()` calls `invalidate_settings_cache()`

---

## 9. Admin Controls

### 9.1 Settings Sections

**Email · Brevo Section** (`/admin/sections/settings` → Email · Brevo):
- Brevo API Key
- Sender Email
- Sender Name
- Admin Email

**Email Notifications Section** (`/admin/sections/settings` → Email Notifications):
- Enable welcome email on registration
- Enable order confirmation email
- Enable shipping status emails
- Enable newsletter confirmation email
- Enable password reset email

### 9.2 Per-Section Save

Each settings section has its own save button. When saved:
1. Form data sent as `POST /admin/sections/settings`
2. `section_settings_post()` in `admin_sections.py` processes
3. `save_settings(db_pool, payload)` called
4. `_pg_literal()` embeds values in SQL
5. Cache invalidated via `invalidate_settings_cache()`
6. `asikoToast("success", "Saved", "Settings updated")` shown

### 9.3 Test Email Button

Admin can send test email via:
```
POST /webhooks/test-email
Body: {"email": "test@example.com"}
Response: {"sent": true, "to": "test@example.com"}
```

---

## 10. Error Handling & Graceful Degradation

### 10.1 API Key Check

Every email function checks the API key before sending:

```python
if not BREVO_API_KEY or BREVO_API_KEY.startswith("your_"):
    logger.warning("Brevo API key not configured - skipping email to %s", to_email)
    return False
```

**Behavior:**
- Empty API key → skip (log warning)
- Placeholder API key (`your_*`) → skip (log warning)
- Valid API key → attempt to send

### 10.2 Async Task Error Handling

All email sends are wrapped in `try/except`:

```python
try:
    from app.services.brevo import send_welcome_email
    import asyncio
    asyncio.create_task(send_welcome_email(email, name))
except Exception:
    pass
```

**Why `pass`?** Email failure should never block the user experience. A customer registering should see their dashboard even if the welcome email fails.

### 10.3 HTTP Error Handling

The Brevo API call handles all errors:

```python
async with httpx.AsyncClient() as client:
    try:
        response = await client.post(url, json=payload, headers=headers, timeout=15.0)
        if response.status_code in (200, 201):
            return True
        logger.error("Brevo error %s: %s", response.status_code, response.text[:200])
        return False
    except httpx.HTTPError as exc:
        logger.error("Failed to communicate with Brevo: %s", exc)
        return False
```

**Timeout:** 15 seconds — emails won't hang indefinitely.

### 10.4 Password Reset Safety

- Always shows success message (prevents email enumeration)
- Token expires in 1 hour
- Token is single-use (marked `used = TRUE` after reset)
- Invalid/expired tokens redirect to login with error

### 10.5 Logging

All email activity is logged:

```python
logger.info("Email sent to %s: %s", to_email, subject)      # Success
logger.warning("Brevo API key not configured...")             # Skip
logger.error("Brevo error %s: %s", status_code, response)    # API error
logger.error("Failed to communicate with Brevo: %s", exc)    # Network error
```

---

## 11. Database Schema

### 11.1 `password_reset_tokens` Table

```sql
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    token VARCHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_prt_token ON password_reset_tokens(token);
CREATE INDEX IF NOT EXISTS idx_prt_customer ON password_reset_tokens(customer_id);
```

### 11.2 `store_settings` Columns (Email-Related)

```sql
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS brevo_api_key VARCHAR(500) DEFAULT '';
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS sender_email VARCHAR(500) DEFAULT '';
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS sender_name VARCHAR(500) DEFAULT '';
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS admin_email VARCHAR(500) DEFAULT '';
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS email_welcome_enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS email_order_enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS email_shipping_enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS email_newsletter_enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS email_password_reset_enabled BOOLEAN DEFAULT TRUE;
```

---

## 12. Testing & Verification

### 12.1 Live API Test (Verified)

```bash
# Test Brevo API key and send email
python -c "
import httpx
API_KEY = 'xkeysib-...'
headers = {'accept': 'application/json', 'api-key': API_KEY, 'content-type': 'application/json'}
payload = {
    'sender': {'name': 'ASIKO Boutique', 'email': 'ggraphixc@gmail.com'},
    'to': [{'email': 'ggraphixc@gmail.com'}],
    'subject': 'ASIKO API Test',
    'htmlContent': '<html><body><h1>Test</h1></body></html>'
}
resp = httpx.post('https://api.brevo.com/v3/smtp/email', json=payload, headers=headers)
print(f'Status: {resp.status_code}')
print(f'Response: {resp.text}')
"
```

**Result:** Status 201, messageId returned. Email sent successfully.

### 12.2 Endpoint Test

```bash
# Send test email via webhook
curl -X POST http://localhost:8000/webhooks/test-email \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'
```

### 12.3 Manual Verification

1. **Register new account** → Check inbox for welcome email
2. **Click "Forgot Password"** → Check inbox for reset email
3. **Subscribe to newsletter** → Check inbox for confirmation
4. **Place order** → Check inbox for order confirmation
5. **Admin changes status** → Check inbox for status update

---

## 13. Code Reference

### Files

| File | Lines | Purpose |
|------|-------|---------|
| `app/services/brevo.py` | 190 | Centralized email service |
| `app/routes/webhooks.py` | 338 | Order emails + inline sender |
| `app/routes/customer.py` | 419 | Welcome, password reset, newsletter |
| `app/routes/checkout.py` | 239 | Order confirmation on checkout |
| `app/settings_service.py` | 224 | Email settings defaults + cache |
| `app/templates/customer/forgot_password.html` | 31 | Forgot password form |
| `app/templates/customer/reset_password.html` | 43 | Reset password form |
| `app/templates/customer/register.html` | 241 | Registration form |

### Key Functions

| Function | File:Line | Purpose |
|----------|-----------|---------|
| `send_transactional_email()` | brevo.py:36 | Core Brevo API call |
| `send_welcome_email()` | brevo.py:107 | Welcome greeting |
| `send_forgot_password_email()` | brevo.py:84 | Password reset link |
| `send_newsletter_confirmation()` | brevo.py:130 | Newsletter confirm |
| `sync_to_brevo_waitlist_audience()` | brevo.py:150 | Contact sync |
| `send_brevo_email()` | webhooks.py:45 | Inline sender |
| `notify_customer_order_confirmation()` | webhooks.py:124 | Full order email |
| `notify_status_change()` | webhooks.py:163 | Status update |
| `on_order_created()` | webhooks.py:208 | Order orchestrator |
| `on_order_status_changed()` | webhooks.py:259 | Status orchestrator |
| `register_submit()` | customer.py:40 | Triggers welcome email |
| `forgot_password_submit()` | customer.py:303 | Triggers reset email |
| `newsletter_subscribe()` | customer.py:389 | Triggers newsletter email |
| `checkout_submit()` | checkout.py:68 | Triggers order email |

---

*Document generated for ASIKO Boutique — Nigerian Fashion Marketplace*
*Last updated: June 2026*
