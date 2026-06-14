# E. CUSTOMER SYSTEMS

## Overview

The 3 customer-facing systems handle authentication, account management, and newsletter subscription. Built with simplicity in mind — SHA-256 hashing, session-based auth, and Brevo email integration.

---

## 1. Customer Authentication

**File:** `app/routes/customer.py` (419 lines)

### What It Does
Full customer authentication system with registration, login, logout, password reset, and session management.

### Password Hashing
```python
def _hash_password(password: str) -> str:
    """SHA-256 hash with salt."""
    salt = os.environ.get("AUTH_SALT", "asiko-boutique-salt-2024")
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

def _check_password(password: str, password_hash: str) -> bool:
    return hmac.compare_digest(_hash_password(password), password_hash)
```

**Why SHA-256 not bcrypt?** User chose simplicity. SHA-256 + salt is sufficient for a single-boutique store. Bcrypt adds complexity (hashing rounds, library dependency) that isn't needed here.

### Registration Flow

```
GET /register → Render registration form
POST /register → Process registration
```

**Form Fields:**
- Full Name (text, required)
- Email (email, required)
- Password (min 6 chars, required)
- Confirm Password (must match)
- Agree to Terms (checkbox, required)

**Validation:**
1. Email and password required
2. Password minimum 6 characters
3. Passwords must match
4. Email must be unique (check DB)
5. Terms checkbox must be checked

**On Success:**
```python
# 1. Insert customer
customer_id = await conn.fetchval(
    "INSERT INTO customers (email, password_hash, full_name) VALUES ($1, $2, $3) RETURNING id",
    email, _hash_password(password), full_name
)

# 2. Set session
request.session["customer_id"] = str(customer_id)
request.session["customer_email"] = email
request.session["customer_name"] = full_name

# 3. Send welcome email (async, non-blocking)
asyncio.create_task(send_welcome_email(email, full_name))

# 4. Redirect to dashboard
return RedirectResponse("/account?success=Account+created+successfully")
```

### Login Flow

```
GET /login → Render login form
POST /login → Process login
```

**Form Fields:**
- Email (email, required)
- Password (required)
- Remember Me (checkbox)

**Validation:**
```python
customer = await conn.fetchrow(
    "SELECT id, password_hash, full_name FROM customers WHERE email = $1",
    email
)

if not customer or not _check_password(password, customer["password_hash"]):
    return RedirectResponse("/login?error=Invalid+email+or+password")
```

**On Success:**
```python
request.session["customer_id"] = str(customer["id"])
request.session["customer_email"] = email
request.session["customer_name"] = customer["full_name"]
return RedirectResponse("/account?success=Welcome+back!")
```

### Logout
```python
async def logout(request):
    request.session.pop("customer_id", None)
    request.session.pop("customer_email", None)
    request.session.pop("customer_name", None)
    return RedirectResponse("/?success=You+have+been+signed+out")
```

### Session Data
```python
{
    "customer_id": "uuid",
    "customer_email": "user@example.com",
    "customer_name": "John Doe",
    "cart": {"lines": [...], "total": 0.0, "item_count": 0}
}
```

**Session Cookie:**
- Name: `asiko_session`
- Max Age: 7 days (604,800 seconds)
- Signed with SECRET_KEY

### Why It Matters
Without auth, there are no customer accounts, no order history, no password reset. This is the identity layer.

---

## 2. Customer Dashboard

**File:** `app/routes/customer.py`

### What It Does
Customer account dashboard showing order history, order details, and quick actions.

### Dashboard Route
```python
async def customer_dashboard(request):
    """GET /account"""
    # 1. Check if customer is logged in
    # 2. Fetch orders from DB
    # 3. Format orders for display
    # 4. Render dashboard template
```

**Order Fetch:**
```python
orders = await conn.fetch("""
    SELECT o.id, o.total_amount, o.status, o.created_at,
           o.shipping_cost, o.metadata,
           COUNT(oi.id) AS item_count
    FROM orders o
    LEFT JOIN order_items oi ON oi.order_id = o.id
    WHERE o.customer_email = $1
    GROUP BY o.id
    ORDER BY o.created_at DESC
    LIMIT 20
""", customer_email)
```

**Order Formatting:**
```python
status_map = {
    "pending": ("Pending", "text-amber-600 bg-amber-50"),
    "paid": ("Paid", "text-emerald-600 bg-emerald-50"),
    "processing": ("Processing", "text-blue-600 bg-blue-50"),
    "shipped": ("Shipped", "text-purple-600 bg-purple-50"),
    "delivered": ("Delivered", "text-emerald-700 bg-emerald-50"),
    "cancelled": ("Cancelled", "text-red-600 bg-red-50"),
}
```

### Order Detail Route
```python
async def customer_order_detail(request):
    """GET /account/order/{order_id}"""
    # 1. Verify order belongs to logged-in customer
    # 2. Fetch order + items
    # 3. Render order detail template
```

### Dashboard Template Features
- Welcome header with customer name
- Order count badge
- Order history table with status badges
- Quick actions: Continue Shopping, Wishlist, Track Order, Profile, Logout
- Order detail page with item breakdown

### Why It Matters
Customers need to see their order history. This is the post-purchase experience.

---

## 3. Newsletter Subscription

**File:** `app/routes/customer.py`

### What It Does
Captures email subscribers and syncs them to Brevo marketing list. Sends confirmation email.

### Route
```python
async def newsletter_subscribe(request):
    """POST /newsletter/subscribe"""
    form = await request.form()
    email = (form.get("email") or "").strip().lower()
    
    if not email:
        return RedirectResponse("/?error=Please+enter+your+email", status_code=302)
    
    # 1. Sync to Brevo contact list (list_id=2)
    asyncio.create_task(sync_to_brevo_waitlist_audience(email, list_id=2))
    
    # 2. Send confirmation email
    asyncio.create_task(send_newsletter_confirmation(email))
    
    return RedirectResponse("/?success=You+are+subscribed+to+the+ASIKO+newsletter")
```

### Brevo Contact Sync
```python
async def sync_to_brevo_waitlist_audience(email, list_id=2):
    """Add or update contact in Brevo marketing list."""
    payload = {
        "email": email,
        "listIds": [list_id],
        "updateEnabled": True,  # Update if exists
    }
    # POST https://api.brevo.com/v3/contacts
```

### Confirmation Email
```
Subject: Welcome to the ASIKO Newsletter

[Brand Header]
You're Subscribed!

Thank you for subscribing to the ASIKO Boutique newsletter.
You'll receive updates on new arrivals, exclusive offers, and styling inspiration.

[Browse New Arrivals CTA]

[Brand Footer]
```

### Why It Matters
Newsletter subscribers are warm leads. They've opted in to hear from you. This is the list you market to.

---

## Summary

| System | File | Lines | Key Feature |
|--------|------|-------|-------------|
| Customer Auth | `app/routes/customer.py` | 419 | Register, login, password reset |
| Customer Dashboard | `app/routes/customer.py` | (same) | Order history, order detail |
| Newsletter | `app/routes/customer.py` | (same) | Brevo sync + confirmation email |

**Total: ~419 lines of code (all in one file)**
