# F. EMAIL SYSTEM

## Overview

ASIKO Boutique uses **Brevo** (formerly Sendinblue) for all transactional emails. 2 email sender implementations exist (centralized and inline), supporting 7 email types with branded HTML templates.

---

## 1. Brevo Email Service (Centralized)

**File:** `app/services/brevo.py` (190 lines)

### What It Does
Centralized email service used by customer routes (register, password reset, newsletter). Provides branded HTML templates and contact sync.

### Core Sender
```python
async def send_transactional_email(to_email, subject, html_content, sender_name="ASIKO Boutique"):
    """Send HTML email via Brevo SMTP API."""
    if not BREVO_API_KEY or BREVO_API_KEY.startswith("your_"):
        return False  # Skip silently
    
    payload = {
        "sender": {"name": sender_name, "email": SENDER_EMAIL},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_content,
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.brevo.com/v3/smtp/email",
            json=payload, headers=headers, timeout=15.0
        )
        return response.status_code in (200, 201)
```

### Email Templates

#### Welcome Email
```python
async def send_welcome_email(to_email, customer_name):
    html = f"""
    {_BRAND_HEADER}
    <div style="padding:24px;background-color:#FBF9F6;">
        <h2>Welcome to ASIKO!</h2>
        <p>Dear <strong>{customer_name}</strong>,</p>
        <p>Thank you for joining ASIKO Boutique...</p>
        <a href="/" style="...">Start Shopping</a>
    </div>
    {_BRAND_FOOTER}
    """
    return await send_transactional_email(to_email, "Welcome to ASIKO Boutique!", html)
```

#### Password Reset Email
```python
async def send_forgot_password_email(to_email, customer_name, reset_url):
    html = f"""
    {_BRAND_HEADER}
    <div style="padding:24px;background-color:#FBF9F6;">
        <h2>Reset Your Password</h2>
        <p>Dear <strong>{customer_name}</strong>,</p>
        <p>Click the button below to set a new password.</p>
        <a href="{reset_url}" style="...">Reset Password</a>
        <p style="color:#666;font-size:13px;">This link expires in 1 hour.</p>
    </div>
    {_BRAND_FOOTER}
    """
    return await send_transactional_email(to_email, "Reset Your Password — ASIKO Boutique", html)
```

#### Newsletter Confirmation
```python
async def send_newsletter_confirmation(to_email):
    html = f"""
    {_BRAND_HEADER}
    <div style="padding:24px;background-color:#FBF9F6;">
        <h2>You're Subscribed!</h2>
        <p>Thank you for subscribing to the ASIKO Boutique newsletter.</p>
        <a href="/" style="...">Browse New Arrivals</a>
    </div>
    {_BRAND_FOOTER}
    """
    return await send_transactional_email(to_email, "Welcome to the ASIKO Newsletter", html)
```

### Contact Sync
```python
async def sync_to_brevo_waitlist_audience(email, list_id=2):
    """Add/update contact in Brevo marketing list."""
    payload = {"email": email, "listIds": [list_id], "updateEnabled": True}
    # POST https://api.brevo.com/v3/contacts
```

---

## 2. Order Email System (Inline)

**File:** `app/routes/webhooks.py` (338 lines)

### What It Does
Order-related emails with branded HTML templates. Includes order confirmation, status updates, and admin notifications.

### Inline Sender
```python
async def send_brevo_email(to_email, to_name, subject, html_content):
    """Send email via Brevo SMTP API."""
    # Same logic as brevo.py but with to_name parameter
```

### Order Confirmation (Full Version)
```python
async def notify_customer_order_confirmation(
    customer_email, customer_name, order_id,
    items, total, shipping_state, shipping_cost
):
    """Send full order confirmation with items table."""
    items_table = _build_order_items_table(items)
    
    html = f"""
    {_BRAND_HEADER}
    <div style="padding:24px;background-color:#FBF9F6;">
        <h2>Order Confirmed</h2>
        <p>Dear <strong>{customer_name}</strong>,</p>
        <div style="...">
            <p>Order ID: {order_id}</p>
            <p>Shipping to: {shipping_state}</p>
            <p>Shipping cost: ₦{shipping_cost:,.0f}</p>
            <p>Total: ₦{total:,.0f}</p>
        </div>
        {items_table}
        <p>We'll notify you once your order has been shipped.</p>
    </div>
    {_BRAND_FOOTER}
    """
```

### Items Table Builder
```python
def _build_order_items_table(items):
    """Render order items as HTML table."""
    rows = ""
    for item in items:
        rows += f"""
        <tr>
            <td>{item['product_name']}</td>
            <td>{item['quantity']}</td>
            <td>₦{float(item['price']):,.0f}</td>
        </tr>"""
    return f"""
    <table style="width:100%;border-collapse:collapse;">
        <thead>
            <tr style="background-color:#0D2A22;color:#fff;">
                <th>Product</th><th>Qty</th><th>Price</th>
            </tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>"""
```

### Status Update Email
```python
async def notify_status_change(customer_email, customer_name, order_id, new_status):
    status_labels = {
        "paid": "Payment confirmed",
        "processing": "Your order is being prepared",
        "shipped": "Your order has been shipped",
        "delivered": "Your order has been delivered",
        "cancelled": "Your order has been cancelled",
    }
    # Gold left-border accent design
```

### Admin Notification
```python
# Sent to hello@asikoboutique.com on every new order
ASIKO_ADMIN_EMAIL = "hello@asikoboutique.com"
```

### Orchestrators
```python
async def on_order_created(order_id):
    """Send customer confirmation + admin notification."""
    await notify_customer_order_confirmation(...)
    await send_brevo_email(ASIKO_ADMIN_EMAIL, "ASIKO Admin", ...)

async def on_order_status_changed(order_id, new_status):
    """Notify customer of status change."""
    await notify_status_change(...)
```

### Test Email Endpoint
```python
async def send_test_email(request):
    """POST /webhooks/test-email"""
    # Debug endpoint for Brevo config verification
    return JSONResponse({"sent": ok, "to": to_email})
```

---

## 3. Brand Design System

### Brand Header
```html
<div style="background-color:#0D2A22;color:#fff;padding:24px;text-align:center;">
  <h1 style="margin:0;font-size:24px;letter-spacing:2px;">ASIKO BOUTIQUE</h1>
  <p style="margin:4px 0 0;font-size:13px;opacity:.8;">Contemporary Nigerian Fashion</p>
</div>
```

### Brand Footer
```html
<div style="background-color:#D4AF37;padding:12px;text-align:center;color:#0D2A22;">
  <p style="margin:0;font-size:12px;">&copy; 2026 ASIKO Boutique — All rights reserved</p>
</div>
```

### Colors Used in Emails
| Element | Color | Hex |
|---------|-------|-----|
| Header background | Deep emerald | #0D2A22 |
| Footer background | Gold | #D4AF37 |
| Page background | Cream | #FBF9F6 |
| Text | Dark | #1A1A1A |
| Muted text | Gray | #666666 |

---

## Summary

| System | File | Lines | Key Feature |
|--------|------|-------|-------------|
| Brevo Service | `app/services/brevo.py` | 190 | Welcome, reset, newsletter, contact sync |
| Order Emails | `app/routes/webhooks.py` | 338 | Confirmation, status, admin notification |
| Brand Templates | (inline in both files) | — | Header/footer, items table |

**Total: ~528 lines of code**
