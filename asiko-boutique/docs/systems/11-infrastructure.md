# K. INFRASTRUCTURE SYSTEMS

## Overview

The foundation layer — 23 database migrations that create all tables and data, plus a 13-module test suite with 155+ tests that verify everything works.

---

## 1. Database Migrations (23 Files)

**Directory:** `database/migrations/`

### What It Does
Incremental database schema changes. Each migration adds tables, columns, indexes, or seed data. Applied in order (05-23).

### Migration Inventory

| # | File | What It Adds |
|---|------|-------------|
| 05 | `05_single_brand.sql` | `target_skeleton_fit` column on products (male/female/unisex) |
| 06 | `06_admin_audit.sql` | `administrative_audit_logs` table (immutable audit trail) |
| 07 | `07_gltf_columns.sql` | `model_3d_url`, `model_usdz_url`, `apparel_layer_depth` on products; `mesh_node_identifier`, `custom_shader_color`, `morph_target_index` on variants |
| 08 | `08_admin_redesign.sql` | `categories`, `product_reviews`, `store_settings` tables |
| 09 | `09_admin_redesign.sql` | Alternative admin redesign (categories, reviews, settings) |
| 10 | `10_seed_catalog.sql` | 10 products with 39 variants (₦8K – ₦120K range) |
| 11 | `11_customers_auth.sql` | `customers` table, `orders.customer_id` FK |
| 12 | `12_product_images_pipeline.sql` | `base_image`, `source_2d_image_url` for 10 products, pipeline columns |
| 13 | `13_avatar_measurements.sql` | `avatar_measurements` table (body measurements for virtual try-on) |
| 14 | `14_phase2_body_types.sql` | Body type enums, `saved_looks`, `outfit_items` tables, photo upload columns |
| 15 | `15_ai_fashion_assistant.sql` | `user_preferences`, `wardrobe_items`, `color_profiles`, `style_events`, `trend_data`, `fashion_chat_history` tables + 8 seeded events + 15 seeded trends |
| 16 | `16_analytics_tracking.sql` | `page_views`, `funnel_events`, `traffic_sources`, `platform_daily_stats`, `tryon_sessions` tables |
| 17 | `17_logistics.sql` | `delivery_providers`, `shipments`, `shipping_rates`, `tracking_events` tables + 4 seeded providers |
| 18 | `18_social_commerce.sql` | `fashion_feed_posts`, `feed_likes`, `feed_comments`, `influencer_profiles`, `follows`, `outfit_boards` tables |
| 19 | `19_loyalty_system.sql` | `loyalty_points`, `loyalty_accounts`, `vip_tiers`, `referrals`, `rewards_catalog`, `point_redemptions` tables + 5 seeded tiers + 5 seeded rewards |
| 20 | `20_settings_expansion.sql` | AI provider, stylist, hero, shop, lookbook, about, customer dashboard settings on `store_settings` |
| 21 | `21_ai_training_data.sql` | `ai_training_data` table (admin-configurable brand knowledge) |
| 22 | `22_custom_pages_and_blog.sql` | `custom_pages`, `blog_posts` tables (CMS) |
| 23 | `23_seed_default_pages.sql` | Seeds 4 default pages: About Us, Size Guide, Shipping & Returns, Contact Us |

### Inline Migrations (in app/main.py)
| # | What It Adds |
|---|-------------|
| 23 | `password_reset_tokens` table (runs at startup) |
| 24 | Email settings columns on `store_settings` (runs at startup) |

### Seed Data Summary
| Migration | Seed Data |
|-----------|-----------|
| 10 | 10 products, 39 variants |
| 15 | 8 style events, 15 trend entries |
| 17 | 4 delivery providers |
| 19 | 5 VIP tiers, 5 rewards |
| 23 | 4 default pages |

### How Migrations Are Applied
```bash
# Run in order
psql $DATABASE_URL -f database/migrations/05_single_brand.sql
psql $DATABASE_URL -f database/migrations/06_admin_audit.sql
# ... repeat for each migration
```

### Schema Guard (Auto-Fix at Startup)
```python
# In app/main.py lifespan:
async with app.state.db_pool.acquire() as conn:
    # Auto-create asset_category_type enum if missing
    await conn.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'asset_category_type') THEN
                CREATE TYPE asset_category_type AS ENUM ('apparel', 'footwear');
            END IF;
        END $$;
    """)
    # Auto-add asset_category column if missing
    await conn.execute("""
        ALTER TABLE products ADD COLUMN IF NOT EXISTS 
        asset_category asset_category_type DEFAULT 'apparel';
    """)
```

### Why It Matters
Migrations are the source of truth for the database schema. Without them, the database doesn't exist.

---

## 2. Test Suite

**Directory:** `app/tests/` (13 test files, 155+ tests)

### What It Does
Automated tests verifying every system works correctly. Uses pytest with mocked database connections.

### Test Files

| File | Tests | What It Covers |
|------|-------|---------------|
| `test_admin_sections.py` | 72 | All 12 admin sections with mocked DB: empty states, populated states, HTMX fragment rendering, settings save/load |
| `test_admin_create_product.py` | 30 | POST /admin/products/create: form validation, slug generation, image upload, category resolution, store requirement |
| `test_storefront_pages.py` | 43 | Homepage, lookbook, product detail, DPP verification with mocked DB |
| `test_realtime.py` | 35 | ConnectionManager init/connect/disconnect/broadcast, notify(), fragment renderers |
| `test_admin_crud.py` | ~15 | Admin panel security, product lifecycle, stock validation, reservations |
| `test_flow.py` | ~15 | Integration: lifespan pool, storefront load, HTMX grid, cart, checkout, admin |
| `test_catalog.py` | ~10 | Allocation gatekeeper, Atelier binding, WhatsApp concierge, capsule bundle |
| `test_dpp.py` | ~10 | DPP token generation, verification, tamper resistance, uniqueness |
| `test_schema_guard.py` | ~5 | Lifespan schema guard: enum creation, column addition |
| `test_sse_streams.py` | ~10 | SSE endpoint, content type, pipeline status queries |
| `test_webhooks.py` | ~5 | Meshy webhook: method check, POST acknowledgment |
| `test_dual_ingestion.py` | ~5 | Admin dashboard: dual ingestion mode, file input |
| `test_pipeline_worker.py` | 7 | Pipeline daemon: GLB extraction, Gradio result parsing |

### Running Tests
```bash
# All tests
python -m pytest app/tests/ -v

# Specific file
python -m pytest app/tests/test_admin_sections.py -v

# With short traceback
python -m pytest app/tests/ -v --tb=short

# Count tests
python -m pytest app/tests/ --co -q
```

### Test Patterns
```python
# Mock database pool
@pytest.fixture
def mock_pool():
    pool = AsyncMock()
    conn = AsyncMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    return pool

# Test admin section
async def test_section_dashboard_empty(mock_pool):
    conn = mock_pool.acquire.return_value.__aenter__.return_value
    conn.fetch.return_value = []  # Empty results
    
    response = await section_dashboard(mock_pool)
    assert response.status_code == 200
    assert "Dashboard" in response.body.decode()
```

### Test Coverage
| System | Coverage |
|--------|----------|
| Admin sections | 72 tests (12 sections × 6 scenarios) |
| Product CRUD | 30 tests (create, edit, delete, validation) |
| Storefront | 43 tests (all public pages) |
| Realtime | 35 tests (WebSocket, SSE, fragments) |
| Other | ~50 tests (catalog, DPP, flow, schema) |

### Why It Matters
Tests catch bugs before they reach production. 155+ tests ensure every system works as expected.

---

## Summary

| System | Files | Key Feature |
|--------|-------|-------------|
| Database Migrations | 23 SQL files | Schema creation, seed data |
| Inline Migrations | 2 in main.py | Startup auto-migration |
| Test Suite | 13 test files | 155+ automated tests |

**Total: 23 migration files + 13 test modules**
