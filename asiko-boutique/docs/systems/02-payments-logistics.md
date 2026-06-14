# B. PAYMENTS & LOGISTICS SYSTEMS

## Overview

These 3 systems handle the financial and delivery operations of ASIKO Boutique — OPay payment processing, the settlement engine that orchestrates order completion, and the logistics system managing Nigerian delivery providers.

---

## 1. OPay Payment Service

**File:** `app/services/opay_service.py` (246 lines)

### What It Does
Integrates with OPay (Nigerian payment platform) for card payments and bank transfers. Provides payment initialization, verification, webhook signature validation, and virtual bank account generation.

### Why OPay?
The user explicitly chose OPay over Paystack because "Nigerians know that OPay well." OPay is widely used in Nigeria for mobile payments, bank transfers, and POS transactions.

### API Configuration
```python
OPAY_BASE_URL = os.getenv("OPAY_BASE_URL", "https://api.opay.com")
OPAY_MERCHANT_ID = os.getenv("OPAY_MERCHANT_ID", "")
OPAY_SECRET_KEY = os.getenv("OPAY_SECRET_KEY", "")
OPAY_PUBLIC_KEY = os.getenv("OPAY_PUBLIC_KEY", "")
OPAY_CALLBACK_URL = os.getenv("OPAY_CALLBACK_URL", "https://asikoboutique.com/webhooks/opay")
OPAY_RETURN_URL = os.getenv("OPAY_RETURN_URL", "https://asikoboutique.com/checkout/confirmation")
```

### Key Functions

#### Initialize Payment
```python
async def initialize_opay_payment(
    order_id: str,
    amount_kobo: int,       # ₦1 = 100 kobo
    email: str,
    customer_name: str = "",
    description: str = "",
    payment_method: str = "bank_transfer",  # or "card"
) -> dict:
```

**Flow:**
1. Check if API key is configured (not placeholder)
2. Build payload with amount, currency (NGN), reference, callback/return URLs
3. POST to `https://api.opay.com/api/v1/gateway/webanchor/initialize`
4. Return `{"reference": "asiko_{order_id}", "payment_url": "...", "status": "initialized"}`

**Mock Mode:** When API key starts with `your_`, returns mock URL without calling OPay API.

#### Verify Payment
```python
async def verify_opay_payment(reference: str) -> dict:
```

**Flow:**
1. GET `https://api.opay.com/api/v1/gateway/query/reference?reference={ref}`
2. Parse response status: SUCCESS, FAIL, PENDING, CLOSED
3. Return normalized status, amount, transaction_id

**Status Mapping:**
| OPay Status | Normalized |
|-------------|------------|
| SUCCESS | `success` |
| FAIL | `failed` |
| CLOSED | `failed` |
| PENDING | `pending` |

#### Verify Webhook Signature
```python
def verify_opay_webhook_signature(payload_body: bytes, signature: str) -> bool:
```

**How it works:**
1. Take raw request body bytes
2. Compute HMAC-SHA512 using OPAY_SECRET_KEY
3. Compare computed hash with provided signature
4. Use `hmac.compare_digest()` for timing-safe comparison

```python
expected = hmac.new(
    OPAY_SECRET_KEY.encode("utf-8"),
    payload_body,
    hashlib.sha512,
).hexdigest()
return hmac.compare_digest(expected, signature)
```

#### Get Virtual Bank Account
```python
async def get_opay_bank_account(order_id: str, amount_kobo: int) -> dict:
```

**Purpose:** Generate unique bank account details for bank transfer payments.

**Returns:**
```python
{
    "bank_name": "OPay Digital Bank",
    "account_number": "8012345678",
    "account_name": "ASIKO Boutique",
    "amount": 2500000,  # kobo
    "reference": "asiko_order_uuid"
}
```

### Headers
```python
def _headers(content_type="application/json"):
    return {
        "Content-Type": content_type,
        "Authorization": f"Bearer {OPAY_SECRET_KEY}",
        "Merchant-Id": OPAY_MERCHANT_ID,
    }
```

### Error Handling
| Error | Handling |
|-------|----------|
| Timeout (15s) | Returns `{"error": "Payment service timeout"}` |
| HTTP error | Returns `{"error": "..."}` |
| Invalid response | Logs error, returns error dict |
| No API key | Returns mock data |

### Why It Matters
Without this, no money comes in. This is the revenue pipeline.

---

## 2. Settlement Engine

**File:** `app/services/settlement.py`

### What It Does
Orchestrates order completion after OPay payment. Handles webhook processing, shipping cost calculation, reservation cleanup, and email dispatch.

### Key Components

#### 36-State Nigerian Shipping Matrix
```python
NIGERIAN_STATES = {
    "AB": {"name": "Abia", "shipping_cost": 2500},
    "AD": {"name": "Adamawa", "shipping_cost": 3500},
    "AK": {"name": "Akwa Ibom", "shipping_cost": 2500},
    "AN": {"name": "Anambra", "shipping_cost": 2500},
    "BA": {"name": "Bauchi", "shipping_cost": 3000},
    "BY": {"name": "Bayelsa", "shipping_cost": 2500},
    "BE": {"name": "Benue", "shipping_cost": 3000},
    "BO": {"name": "Borno", "shipping_cost": 4000},
    # ... all 36 states + FCT
    "LA": {"name": "Lagos", "shipping_cost": 1500},
    "FC": {"name": "FCT Abuja", "shipping_cost": 2000},
}
```

**Shipping Cost Range:**
- ₦1,500 (Lagos — closest to hub)
- ₦2,000 (South-West, FCT)
- ₦2,500 (South-East, South-South)
- ₦3,000 (North-Central, North-West)
- ₦4,000 (North-East — farthest)

#### Shipping Calculator
```python
def calculate_shipping(state_code: str) -> float:
    """Resolve shipping cost from state code."""
    return NIGERIAN_STATES.get(state_code, {}).get("shipping_cost", 2500)
```

#### Reservation Cleanup Worker
```python
async def purge_expired_reservations(pool):
    """Flush stale reservations older than 60 minutes."""
    async with pool.acquire() as conn:
        await conn.execute("""
            DELETE FROM product_reservations
            WHERE created_at < NOW() - INTERVAL '60 minutes'
            AND status = 'active'
        """)
```

**Why 60 minutes?** If a customer adds items to cart but doesn't checkout within an hour, the stock hold is released for other customers.

#### OPay Webhook Handler
```python
async def opay_webhook_handler(request):
    """
    POST /webhooks/opay
    1. Verify HMAC-SHA512 signature
    2. Extract reference and status
    3. Update order status to 'paid'
    4. Release reservations
    5. Send confirmation email
    """
```

**Flow:**
```
1. Read raw body bytes
2. Verify signature: verify_opay_webhook_signature(body, x-opay-signature)
3. Parse JSON payload
4. Extract reference: "asiko_{order_id}"
5. Update order: UPDATE orders SET status = 'paid' WHERE id = $1
6. Release reservations: DELETE FROM product_reservations WHERE order_id = $1
7. Send confirmation email via Brevo
8. Return 200 OK
```

#### Initialize Payment Wrapper
```python
async def initialize_payment(email, amount_kobo, order_id, customer_name, metadata):
    """Wrapper for checkout integration."""
    return await initialize_opay_payment(
        order_id=order_id,
        amount_kobo=amount_kobo,
        email=email,
        customer_name=customer_name,
    )
```

#### Luxury Alert Email
```python
async def dispatch_luxury_alert_email(order_id, customer_email):
    """Send luxury order confirmation with Brevo."""
    try:
        await send_brevo_email(...)
    except Exception:
        pass  # Graceful fallback
```

### Why It Matters
This connects payment to fulfillment. Without it, orders are created but never completed.

---

## 3. Delivery & Logistics System

**Database:** Migration 17 (`17_logistics.sql`)

### What It Does
Manages Nigerian delivery providers, shipments, shipping rates, and tracking events. Pre-seeded with 4 major Nigerian delivery companies.

### Database Tables

#### delivery_providers
```sql
CREATE TABLE delivery_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    api_url TEXT,
    api_key VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Seeded Providers:**
| Provider | Code | Coverage |
|----------|------|----------|
| KwikDelivery | KWIK | Lagos, same-day |
| GIG Logistics | GIG | Nationwide |
| DHL Nigeria | DHL | International |
| FedEx Nigeria | FEDEX | International |

#### shipments
```sql
CREATE TABLE shipments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id),
    provider_id UUID REFERENCES delivery_providers(id),
    tracking_number VARCHAR(100),
    status VARCHAR(30) DEFAULT 'pending',
    estimated_delivery DATE,
    actual_delivery DATE,
    shipping_cost NUMERIC(10,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### shipping_rates
```sql
CREATE TABLE shipping_rates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id UUID REFERENCES delivery_providers(id),
    state_code VARCHAR(2) NOT NULL,
    weight_min NUMERIC(5,2),
    weight_max NUMERIC(5,2),
    rate NUMERIC(10,2) NOT NULL,
    estimated_days INTEGER
);
```

#### tracking_events
```sql
CREATE TABLE tracking_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shipment_id UUID NOT NULL REFERENCES shipments(id),
    status VARCHAR(30) NOT NULL,
    location VARCHAR(200),
    description TEXT,
    event_time TIMESTAMPTZ DEFAULT NOW()
);
```

### Why It Matters
Nigerian logistics are complex. Having multiple providers with tracking ensures orders actually reach customers.

---

## Summary

| System | File | Lines | Key Feature |
|--------|------|-------|-------------|
| OPay Payment | `app/services/opay_service.py` | 246 | Card + bank transfer, HMAC-SHA512 |
| Settlement Engine | `app/services/settlement.py` | ~200 | 36-state shipping, webhook handler |
| Delivery Logistics | Migration 17 | — | 4 providers, shipments, tracking |

**Total: ~450 lines of code + database schema**
