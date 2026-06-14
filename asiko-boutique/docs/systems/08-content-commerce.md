# H. CONTENT & COMMERCE SYSTEMS

## Overview

These 6 systems handle the content layer and premium commerce features — storefront pages, catalog interactions, luxury extensions, CMS for custom pages and blog, the dynamic pages middleware, and Digital Product Passports.

---

## 1. Storefront Pages

**File:** `app/routes/storefront.py`

### What It Does
All public-facing storefront pages with editorial design. The homepage, product detail, lookbook, about page, and custom dynamic pages.

### Routes
| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| GET | `/` | `homepage` | Homepage with product catalog |
| GET | `/about` | `about_page` | About page |
| GET | `/lookbook` | `lookbook_page` | Editorial lookbook |
| GET | `/product/{product_id}` | `product_detail` | Product detail page |
| POST | `/product/{product_id}/review` | `submit_review` | Submit product review |
| GET | `/product/{product_id}/reviews` | `product_reviews` | HTMX reviews fragment |
| GET | `/page/{slug}` | `custom_page` | Dynamic custom page |
| GET | `/blog` | `blog_listing` | Blog listing |
| GET | `/blog/{slug}` | `blog_post` | Individual blog post |
| GET | `/stylist` | `stylist_page` | AI Fashion Assistant |
| GET | `/dpp` | `dpp_page` | DPP verification |
| GET | `/htmx/products` | `htmx_products` | HTMX product grid |

### Homepage
```python
async def homepage(request):
    pool = request.app.state.db_pool
    settings = await get_settings(pool)
    
    async with pool.acquire() as conn:
        products = await conn.fetch("""
            SELECT p.*, c.name as category_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.stock_quantity > 0
            ORDER BY p.created_at DESC
            LIMIT 12
        """)
    
    return templates.TemplateResponse(request, "storefront/index.html", {
        "request": request,
        "products": [dict(p) for p in products],
        "settings": settings,
        "cart": get_cart_from_session(request),
    })
```

### Product Detail Page
```python
async def product_detail(request):
    product_id = request.path_params["product_id"]
    
    # Fetch product with variants
    product = await conn.fetchrow("""
        SELECT p.*, c.name as category_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE p.id = $1
    """, product_id)
    
    # Fetch variants
    variants = await conn.fetch("""
        SELECT * FROM product_variants
        WHERE product_id = $1 AND is_active = TRUE
        ORDER BY sort_order
    """, product_id)
    
    # Fetch reviews
    reviews = await conn.fetch("""
        SELECT * FROM product_reviews
        WHERE product_id = $1 AND deleted_at IS NULL
        ORDER BY created_at DESC LIMIT 10
    """, product_id)
```

### Review Submission
```python
async def submit_review(request):
    product_id = request.path_params["product_id"]
    form = await request.form()
    
    await conn.execute("""
        INSERT INTO product_reviews (product_id, customer_name, customer_email, rating, title, body)
        VALUES ($1, $2, $3, $4, $5, $6)
    """, product_id, name, email, rating, title, body)
    
    # Notify via WebSocket
    await notify(pool, "new_review", {"product_id": product_id, "rating": rating})
```

### Why It Matters
This is the public face of the brand. Every customer interaction starts here.

---

## 2. Catalog Interaction Engine

**File:** `app/catalog/routes.py`

### What It Does
Session-based premium features for the product detail page. Allocation gatekeepers, body measurement binding, WhatsApp concierge, and capsule bundle.

### Routes
| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| GET | `/catalog/allocation/{slug}` | `allocation_check` | Tiered allocation gatekeeper |
| POST | `/catalog/atelier/bind` | `bind_measurements` | Session body measurement binding |
| GET | `/catalog/concierge/redirect` | `concierge_redirect` | WhatsApp concierge bridge |
| POST | `/catalog/cart/capsule` | `capsule_bundle` | Capsule matrix bundle add |

### Allocation Gatekeeper
```python
async def allocation_check(request):
    """
    Mock 3-unit limited run.
    Checks if customer has already claimed an allocation.
    """
    slug = request.path_params["slug"]
    # Session-based tracking (no DB)
    allocations = request.session.get("allocations", {})
    if slug in allocations:
        return JSONResponse({"allocated": True, "remaining": 0})
    return JSONResponse({"allocated": False, "remaining": 3})
```

### Body Measurement Binding
```python
async def bind_measurements(request):
    """
    Store body measurements in session.
    Used for virtual try-on fit prediction.
    """
    form = await request.form()
    measurements = {
        "chest": float(form.get("chest", 0)),
        "waist": float(form.get("waist", 0)),
        "hips": float(form.get("hips", 0)),
        "height": float(form.get("height", 0)),
    }
    request.session["measurements"] = measurements
    return JSONResponse({"bound": True})
```

### WhatsApp Concierge
```python
async def concierge_redirect(request):
    """
    Generate WhatsApp link with pre-filled message.
    Uses Django Signer for token verification.
    """
    product_id = request.query_params.get("product_id")
    message = f"Hi! I'm interested in this product: https://asikoboutique.com/product/{product_id}"
    wa_url = f"https://wa.me/2348000000000?text={urllib.parse.quote(message)}"
    return RedirectResponse(wa_url)
```

### Capsule Bundle
```python
async def capsule_bundle(request):
    """
    Add a curated capsule look as a bundle.
    Session-based (no DB persistence).
    """
    form = await request.form()
    bundle_items = json.loads(form.get("items", "[]"))
    # Add all items to cart
    for item in bundle_items:
        # ... add to cart logic
    return JSONResponse({"added": len(bundle_items)})
```

### Why It Matters
These are the premium, interactive features that make the shopping experience feel luxury.

---

## 3. Luxury Extensions

**File:** `app/routes/luxury_extensions.py`

### What It Does
DB-backed premium features with persistence (vs catalog's session-only approach). Digital Atelier measurements, signed concierge tokens, capsule matrix, and pre-order tier gates.

### Routes
| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/atelier/measurements` | `save_measurements` | Digital Atelier vault |
| GET | `/catalog/concierge/bridge` | `concierge_bridge` | WhatsApp with signed token |
| POST | `/catalog/capsule/add-bundle` | `add_capsule_bundle` | Capsule matrix bulk add |
| GET | `/products/{slug}/preorder` | `preorder_page` | Pre-order tier-gated page |
| POST | `/catalog/preorder/secure` | `secure_preorder` | Atomic pre-order lock |

### Digital Atelier Measurement Vault
```python
async def save_measurements(request):
    """
    Store body measurements in DB (not just session).
    Supports cm/inch conversion.
    """
    form = await request.form()
    unit = form.get("unit", "cm")  # cm or inch
    
    chest = float(form.get("chest", 0))
    waist = float(form.get("waist", 0))
    hips = float(form.get("hips", 0))
    
    # Convert inches to cm if needed
    if unit == "inch":
        chest *= 2.54
        waist *= 2.54
        hips *= 2.54
    
    await conn.execute("""
        INSERT INTO measurement_vault (customer_id, chest_cm, waist_cm, hips_cm)
        VALUES ($1, $2, $3, $4)
    """, customer_id, chest, waist, hips)
```

### WhatsApp Concierge with Signed Token
```python
async def concierge_bridge(request):
    """
    WhatsApp link with Django Signer verification token.
    Prevents tampering with concierge referrals.
    """
    product_id = request.query_params["product_id"]
    
    # Generate signed token
    from apps.boutique_core.models import generate_signed_concierge_payload
    token = generate_signed_concierge_payload(product_id)
    
    wa_url = f"https://wa.me/2348000000000?text=...&token={token}"
    return RedirectResponse(wa_url)
```

### Atomic Pre-Order Lock
```python
async def secure_preorder(request):
    """
    Atomic pre-order with SELECT FOR UPDATE.
    Prevents oversell on limited allocation windows.
    """
    async with conn.transaction():
        # Lock allocation window
        window = await conn.fetchrow("""
            SELECT * FROM allocation_windows
            WHERE product_id = $1 AND is_active = TRUE
            FOR UPDATE
        """, product_id)
        
        if window["remaining"] <= 0:
            return JSONResponse({"error": "Allocation exhausted"}, status_code=409)
        
        # Decrement remaining
        await conn.execute("""
            UPDATE allocation_windows SET remaining = remaining - 1 WHERE id = $1
        """, window["id"])
        
        # Create reservation
        await conn.execute("""
            INSERT INTO product_reservations (variant_id, quantity, order_id, status)
            VALUES ($1, 1, $2, 'active')
        """, variant_id, order_id)
```

### Why It Matters
These are the high-end features that justify premium pricing. Measurement vaults, signed tokens, and tier-gated pre-orders.

---

## 4. Custom Pages & Blog CMS

**Database:** Migration 22 (`22_custom_pages_and_blog.sql`)

### What It Does
Content management system for the boutique owner. Create pages (about, policy, payment guide) and blog posts, toggle them live, choose navbar/footer placement.

### Database Tables

#### custom_pages
```sql
CREATE TABLE custom_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(200) NOT NULL,
    slug VARCHAR(200) UNIQUE NOT NULL,
    page_type VARCHAR(50) DEFAULT 'custom',
    body_html TEXT,
    excerpt TEXT,
    meta_description TEXT,
    featured_image TEXT,
    show_in_nav BOOLEAN DEFAULT FALSE,
    show_in_footer BOOLEAN DEFAULT FALSE,
    is_live BOOLEAN DEFAULT FALSE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### blog_posts
```sql
CREATE TABLE blog_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    page_id UUID REFERENCES custom_pages(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    slug VARCHAR(200) UNIQUE NOT NULL,
    content_html TEXT,
    excerpt TEXT,
    featured_image TEXT,
    author_name VARCHAR(100) DEFAULT 'ASIKO Team',
    is_published BOOLEAN DEFAULT FALSE,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Admin Management

**Pages Management** (`/admin/sections/pages`):
- Create new page (title, slug, body HTML, excerpt)
- Toggle live status (`is_live`)
- Choose placement: navbar, footer, or neither
- Set sort order
- Edit/delete existing pages

**Blog Management** (`/admin/sections/blog`):
- Create new post (title, slug, content HTML, excerpt)
- Toggle published status
- Set author name
- Featured image URL

### Storefront Rendering

**Dynamic Page:** `GET /page/{slug}`
```python
async def custom_page(request):
    slug = request.path_params["slug"]
    page = await conn.fetchrow(
        "SELECT * FROM custom_pages WHERE slug = $1 AND is_live = TRUE", slug
    )
    if not page:
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse(request, "storefront/page.html", {"page": page})
```

**Blog Listing:** `GET /blog`
```python
async def blog_listing(request):
    posts = await conn.fetch("""
        SELECT bp.*, cp.featured_image
        FROM blog_posts bp
        LEFT JOIN custom_pages cp ON bp.page_id = cp.id
        WHERE bp.is_published = TRUE
        ORDER BY bp.published_at DESC
    """)
    return templates.TemplateResponse(request, "storefront/blog_listing.html", {"posts": posts})
```

### Why It Matters
The owner can create content without touching code. Blog posts, policies, guides — all managed from the admin panel.

---

## 5. Dynamic Pages Middleware

**File:** `app/main.py` (CustomPagesMiddleware)

### What It Does
Caches live custom pages in-memory and injects them into every request for navbar and footer rendering.

### How It Works
```python
class CustomPagesMiddleware:
    _nav_pages: list = []
    _footer_pages: list = []
    _cache_ts: float = 0.0
    CACHE_TTL: int = 30
    
    async def __call__(self, scope, receive, send):
        now = time.monotonic()
        if (now - self._cache_ts) >= self.CACHE_TTL:
            # Single DB query every 30 seconds
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT title, slug, show_in_nav, show_in_footer "
                    "FROM custom_pages WHERE is_live = TRUE "
                    "ORDER BY sort_order, title"
                )
            self._nav_pages = [r for r in rows if r["show_in_nav"]]
            self._footer_pages = [r for r in rows if r["show_in_footer"]]
            self._cache_ts = now
        
        request.state.nav_pages = self._nav_pages
        request.state.footer_pages = self._footer_pages
```

### Template Usage
```html
<!-- In base.html navbar -->
{% for page in request.state.nav_pages %}
<a href="/page/{{ page.slug }}">{{ page.title }}</a>
{% endfor %}

<!-- In footer -->
{% for page in request.state.footer_pages %}
<a href="/page/{{ page.slug }}">{{ page.title }}</a>
{% endfor %}
```

### Why It Matters
Without this, every page load would query the database for nav/footer links. The 30s cache eliminates this.

---

## 6. Digital Product Passport (DPP)

**File:** `app/services/dpp_crypto.py`

### What It Does
Cryptographically signed provenance tokens for product authentication. Uses Django's signing infrastructure to create tamper-proof verification.

### Token Generation
```python
def generate_passport_token(product_id, serial_number, artisan_id):
    """Sign provenance data into a verifiable token."""
    payload = json.dumps({
        "product_id": product_id,
        "serial_number": serial_number,
        "artisan_id": artisan_id,
        "timestamp": datetime.utcnow().isoformat(),
    })
    signer = Signer(salt="asiko.concierge.vector")
    return signer.sign(payload)
```

### Token Verification
```python
def verify_passport_token(token):
    """Validate token authenticity."""
    try:
        signer = Signer(salt="asiko.concierge.vector")
        payload = signer.unsign(token)
        return json.loads(payload)
    except SignatureExpired:
        return {"error": "Token expired"}
    except BadSignature:
        return {"error": "Invalid token"}
```

### Verification Page
```python
# GET /dpp?token=...
# Renders verification result with product provenance details
```

### Why It Matters
DPP proves authenticity. In a market with counterfeits, cryptographic verification is a trust signal.

---

## Summary

| System | File | Lines | Key Feature |
|--------|------|-------|-------------|
| Storefront Pages | `app/routes/storefront.py` | ~300 | Homepage, PDP, lookbook, reviews |
| Catalog Engine | `app/catalog/routes.py` | ~150 | Allocation, measurements, concierge, capsule |
| Luxury Extensions | `app/routes/luxury_extensions.py` | ~200 | Measurement vault, signed tokens, pre-orders |
| Custom Pages & Blog | Migration 22 + admin | — | CMS for pages and blog posts |
| Dynamic Pages MW | `app/main.py` | ~30 | In-memory cache, nav/footer injection |
| DPP Crypto | `app/services/dpp_crypto.py` | ~60 | Signed provenance tokens |

**Total: ~740 lines of code + database schema**
