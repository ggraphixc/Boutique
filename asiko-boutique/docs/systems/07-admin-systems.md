# G. ADMIN SYSTEMS

## Overview

The admin panel is the command center for the boutique owner. 5 systems handle product management, section-based dashboard, executive dashboard, inventory operations, and audit logging.

---

## 1. Admin CRUD Router

**File:** `app/routes/admin.py`

### What It Does
Product management endpoints for the HTMX-driven admin interface. Handles create, read, update, delete operations.

### Routes
| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| GET | `/admin/products` | `admin_products` | Product table with variant stock |
| POST | `/admin/products/create` | `admin_create_product` | Create product |
| POST | `/admin/products/{id}/edit` | `admin_edit_product` | Update product |
| GET | `/admin/products/{id}/detail` | `admin_product_detail` | Single product view |
| DELETE | `/admin/products/{id}` | `admin_delete_product` | Delete with FK protection |

### Create Product
```python
async def admin_create_product(request):
    form = await request.form()
    name = form.get("name", "").strip()
    price = float(form.get("price", 0))
    stock = int(form.get("stock_quantity", 0))
    description = form.get("description", "")
    base_image = form.get("base_image", "")
    category_id = form.get("category_id")
    
    # Slug auto-generation with dedup
    slug = slugify(name)
    existing = await conn.fetchval("SELECT id FROM products WHERE slug = $1", slug)
    if existing:
        slug = f"{slug}-{uuid4().hex[:6]}"
    
    product_id = await conn.fetchval("""
        INSERT INTO products (store_id, name, slug, description, price, stock_quantity, base_image, category_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING id
    """, ASIKO_STORE_ID, name, slug, description, price, stock, base_image, category_id)
```

### Delete with FK Protection
```python
async def admin_delete_product(request):
    product_id = request.path_params["id"]
    # Check for order references
    has_orders = await conn.fetchval(
        "SELECT EXISTS(SELECT 1 FROM order_items WHERE product_id = $1)",
        product_id
    )
    if has_orders:
        return JSONResponse({"error": "Cannot delete: product has orders"}, status_code=409)
    
    await conn.execute("DELETE FROM products WHERE id = $1", product_id)
```

### Why It Matters
The owner needs to add/edit/remove products. This is the product management layer.

---

## 2. Admin Sections (12+ Sections)

**File:** `app/routes/admin_sections.py`

### What It Does
The complete admin redesign with 12+ HTMX sections. Each section is served as a fragment to `#workspace-content`.

### Sections Overview

| # | Section | Route | Description |
|---|---------|-------|-------------|
| 1 | Dashboard | `/admin/section/dashboard` | KPI cards, activity feed, top sellers |
| 2 | Products | `/admin/section/products` | Product card grid |
| 3 | Product Detail | `/admin/section/products/{id}` | Full product + variants |
| 4 | Sales | `/admin/section/sales` | Orders with status filter |
| 5 | Analytics | `/admin/section/analytics` | Charts, funnel, traffic sources |
| 6 | Members | `/admin/section/members` | Customer profiles, lifetime value |
| 7 | Operations | `/admin/section/operations` | Inventory, orders, waitlist |
| 8 | Settings | `/admin/section/settings` | 14 sub-sections with per-section save |
| 9 | About | `/admin/section/about` | Owner profile management |
| 10 | Reviews | `/admin/section/reviews` | Review management with stats |
| 11 | Pages | `/admin/section/pages` | Dynamic pages management |
| 12 | Blog | `/admin/section/blog` | Blog post management |

### Settings Sub-Sections (14)
1. Store Profile
2. AI Provider
3. AI Stylist
4. Homepage Hero
5. Shop
6. Lookbook
7. About
8. Customer Dashboard
9. Currency & Locale
10. Shipping
11. Security
12. Notifications
13. Email (Brevo)
14. Email Notifications
15. Brand Identity (logo, name, tagline)
16. SEO / GEO / AEO
17. Chatbot
18. Social & Loyalty

### Per-Section Save
```python
async def section_settings_post(request):
    form = await request.form()
    section = form.get("section", "")

    # Extract only fields for this section
    payload = {k: v for k, v in form.items() if k != "section"}

    # Save to correct table via per-table save function
    save_fn = _SAVE路由.get(section)
    if save_fn:
        await save_fn(pool, payload)

    # Return toast via HX-Trigger header
    return HTMLResponse("", headers={"HX-Trigger": "settingsToast"})
```

### Real-Time Fragments
```
_rt_kpi_cards.html      → Live KPI updates via WebSocket
_rt_activity_feed.html   → Live activity feed items
_rt_review_stats.html    → Live review statistics
_rt_notifications.html   → Bell icon dropdown (7 activity types, responsive)
```

### Admin Header
- Hamburger menu (mobile only)
- Notification bell (dynamic unread badge, responsive dropdown)
- Dark mode toggle
- Profile avatar + name

### Why It Matters
This is where the owner spends most of their time. Every business operation is managed from these sections.

---

## 3. Admin Dashboard

**File:** `app/routes/admin_dashboard.py`

### What It Does
Executive dashboard with inline stock updates and waitlist notification trigger.

### Routes
| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| GET | `/admin/dashboard` | `admin_dashboard` | Delegates to section_dashboard |
| POST | `/admin/dashboard/update-stock` | `update_stock` | Inline stock update |
| POST | `/admin/dashboard/notify-waitlist` | `notify_waitlist` | Batch restock emails |

### Inline Stock Update
```python
async def update_stock(request):
    form = await request.form()
    variant_id = form.get("variant_id")
    new_stock = int(form.get("stock_qty", 0))
    
    await conn.execute(
        "UPDATE product_variants SET stock_qty = $1 WHERE id = $2",
        new_stock, variant_id
    )
    
    # Notify via WebSocket
    await notify(pool, "stock_update", {"variant_id": variant_id, "new_stock": new_stock})
```

### Waitlist Batch Notification
```python
async def notify_waitlist(request):
    form = await request.form()
    variant_id = form.get("variant_id")
    
    # Fetch all waitlisted emails
    waitlisted = await conn.fetch(
        "SELECT email FROM product_waitlists WHERE variant_id = $1",
        variant_id
    )
    
    # Send restock email to each
    for entry in waitlisted:
        await send_brevo_email(
            to_email=entry["email"],
            subject="Back in Stock!",
            html_content=restock_html
        )
```

### Why It Matters
Quick access to critical operations — stock updates and waitlist notifications.

---

## 4. Admin Inventory

**File:** `app/routes/admin_inventory.py`

### What It Does
Omnichannel stock reservation engine with row-level locking. Manages stock holds, settles stale reservations, and maintains a reservation ledger.

### Routes
| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| POST | `/admin/reserve` | `reserve_stock` | Admin stock hold |
| POST | `/admin/settle` | `settle_reservations` | Flush stale holds |
| GET | `/admin/reservations` | `list_reservations` | Live reservation ledger |

### Stock Reservation
```python
async def reserve_stock(request):
    form = await request.form()
    variant_id = form.get("variant_id")
    quantity = int(form.get("quantity", 1))
    order_id = form.get("order_id")
    
    # Row-level lock
    stock = await conn.fetchval(
        "SELECT stock_qty FROM product_variants WHERE id = $1 FOR UPDATE",
        variant_id
    )
    
    if stock < quantity:
        return JSONResponse({"error": "Insufficient stock"}, status_code=409)
    
    # Create reservation
    await conn.execute("""
        INSERT INTO product_reservations (variant_id, quantity, order_id, status)
        VALUES ($1, $2, $3, 'active')
    """, variant_id, quantity, order_id)
```

### Reservation Cleanup
```python
async def settle_reservations(request):
    """Flush reservations older than 60 minutes."""
    result = await conn.execute("""
        DELETE FROM product_reservations
        WHERE created_at < NOW() - INTERVAL '60 minutes'
        AND status = 'active'
    """)
    return JSONResponse({"settled": True})
```

### Why It Matters
Prevents oversell during high-traffic periods. Stock is locked at the row level during checkout.

---

## 5. Admin Audit Trail

**Database:** Migration 06 (`06_admin_audit.sql`)

### What It Does
Immutable record of all admin actions. Every product edit, status change, and setting update is logged.

### Database Table
```sql
CREATE TABLE administrative_audit_logs (
    id BIGSERIAL PRIMARY KEY,
    admin_session VARCHAR(100),
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID,
    old_value JSONB,
    new_value JSONB,
    ip_address INET,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### What Gets Logged
| Action | Entity | Details |
|--------|--------|---------|
| product.create | product | New product data |
| product.update | product | Before/after values |
| product.delete | product | Deleted product data |
| order.status_change | order | Old status → new status |
| settings.update | store_settings | Changed settings |
| variant.update | product_variant | Stock changes |

### Why It Matters
If something goes wrong, you need to know who changed what and when. This is the audit trail.

---

## Summary

| System | File | Lines | Key Feature |
|--------|------|-------|-------------|
| Admin CRUD | `app/routes/admin.py` | ~200 | Product create/edit/delete |
| Admin Sections | `app/routes/admin_sections.py` | ~800 | 12+ sections, per-section save |
| Admin Dashboard | `app/routes/admin_dashboard.py` | ~100 | Stock updates, waitlist notify |
| Admin Inventory | `app/routes/admin_inventory.py` | ~100 | Stock reservation, cleanup |
| Audit Trail | Migration 06 | — | Immutable action log |

**Total: ~1,200 lines of code + database schema**
