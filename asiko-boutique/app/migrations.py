# ASIKO Boutique - Database Migrations
# Batched into a single connection for serverless (Vercel) cold-start efficiency.
# Idempotent: safe to run multiple times (CREATE IF NOT EXISTS / ADD COLUMN IF NOT EXISTS).

import logging
from typing import Optional

import asyncpg

logger = logging.getLogger("asiko.migrations")


async def run_migrations(pool: asyncpg.Pool) -> None:
    """Run all pending migrations in a single connection/transaction."""
    async with pool.acquire() as conn:
        await _migration_23(conn)
        await _migration_24(conn)
        await _migration_25(conn)
        await _migration_26(conn)
        await _migration_27(conn)
        await _migration_28(conn)
        await _migration_30(conn)
        await _migration_31(conn)
        await _migration_32(conn)
        await _migration_33(conn)
        await _migration_34(conn)
        await _migration_35(conn)
    logger.info("All migrations completed.")


async def _migration_23(conn: asyncpg.Connection) -> None:
    await conn.execute("""
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
    """)


async def _migration_24(conn: asyncpg.Connection) -> None:
    for col in ["brevo_api_key", "sender_email", "sender_name", "admin_email"]:
        await conn.execute(
            f"ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS {col} VARCHAR(500) DEFAULT ''"
        )
    for col in ["email_welcome_enabled", "email_order_enabled", "email_shipping_enabled",
                 "email_newsletter_enabled", "email_password_reset_enabled"]:
        await conn.execute(
            f"ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS {col} BOOLEAN DEFAULT TRUE"
        )


async def _migration_25(conn: asyncpg.Connection) -> None:
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(255) DEFAULT '',
            role VARCHAR(50) DEFAULT 'admin',
            is_active BOOLEAN DEFAULT TRUE,
            last_login TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW()
        );
        CREATE INDEX IF NOT EXISTS idx_admin_users_email ON admin_users(email);
    """)
    import hashlib, os as _os
    _salt = _os.environ.get("AUTH_SALT", "asiko-boutique-salt-2024")
    _hash = hashlib.sha256(f"{_salt}zerupthcode".encode()).hexdigest()
    await conn.execute("""
        INSERT INTO admin_users (email, password_hash, full_name, role)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (email) DO NOTHING
    """, "zerupth@gmail.com", _hash, "ASIKO Admin", "owner")


async def _migration_26(conn: asyncpg.Connection) -> None:
    for col, typ, default in [
        ("store_name",        "VARCHAR(255)", "'ASIKO Boutique'"),
        ("contact_email",     "VARCHAR(255)", "''"),
        ("store_description", "TEXT",         "''"),
        ("phone",             "VARCHAR(50)",  "''"),
        ("store_address",     "TEXT",         "''"),
        ("notif_new_order",   "BOOLEAN",      "TRUE"),
        ("notif_pipeline",    "BOOLEAN",      "TRUE"),
        ("notif_review",      "BOOLEAN",      "TRUE"),
        ("notif_low_stock",   "BOOLEAN",      "TRUE"),
        ("session_timeout",   "INT",          "60"),
    ]:
        try:
            await conn.execute(
                f"ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS {col} {typ} DEFAULT {default}"
            )
        except Exception:
            pass


async def _migration_27(conn: asyncpg.Connection) -> None:
    try:
        count = await conn.fetchval("SELECT COUNT(*) FROM ai_training_data")
        if count == 0:
            await conn.execute("""
                INSERT INTO ai_training_data (category, question, answer, is_active, sort_order) VALUES
                ('brand', 'What is ASIKO?', 'ASIKO Boutique is a Nigerian fashion brand offering authentic, curated styles with transparent pricing. Every piece is crafted with verified provenance and fair-trade standards.', TRUE, 1),
                ('brand', 'What does ASIKO mean?', 'ASIKO means "time" or "era" in Yoruba. It represents timeless fashion that transcends trends.', TRUE, 2),
                ('brand', 'Where is ASIKO located?', 'ASIKO Boutique is based in Lagos, Nigeria. We ship nationwide across all 36 states and the FCT.', TRUE, 3),
                ('brand', 'What makes ASIKO different?', 'We combine verified provenance, transparent pricing (no "DM for price"), and fair-trade standards. Every product shows its real price upfront.', TRUE, 4),
                ('faq', 'Do you have physical stores?', 'Currently ASIKO operates online only at asikoboutique.com. We''re working on pop-up events in Lagos.', TRUE, 10),
                ('faq', 'What sizes do you carry?', 'We carry sizes XS through XXL. Each product has a detailed size guide. Our AI Stylist can recommend the best size for your body type.', TRUE, 11),
                ('faq', 'How do I track my order?', 'Once your order ships, you''ll receive an email with a tracking number. Check My Orders in your account anytime.', TRUE, 12),
                ('faq', 'Can I return or exchange?', 'Yes! Returns and exchanges within 7 days of delivery. Items must be unworn with tags. Contact support@asikoboutique.com.', TRUE, 13),
                ('style', 'What styles does ASIKO specialize in?', 'Contemporary Nigerian fashion: Ankara prints, Aso-Oke, Adire (tie-dye), solid-color modern pieces, and fusion styles blending heritage with global trends.', TRUE, 20),
                ('style', 'How do I style for Nigerian weather?', 'Lightweight cotton/linen for dry season, breathable fabrics for rainy season, layerable pieces for harmattan. Our AI Stylist suggests outfits by location and season.', TRUE, 21),
                ('style', 'What are popular outfit combinations?', 'Ankara top + solid skirt/trousers, Adire dress + leather accessories, Aso-Oke wrapper + modern blouse, solid agbada for men, mix-and-match separates.', TRUE, 22),
                ('voice', 'How should the AI communicate?', 'Warm, friendly, knowledgeable — like a trusted fashion friend. Use Nigerian English naturally. Reference specific products. Use ₦ for prices.', TRUE, 30),
                ('voice', 'What tone should the AI use?', 'Conversational, helpful, confident. Not robotic. Think of a knowledgeable boutique owner who genuinely cares about helping customers look their best.', TRUE, 31)
            """)
    except Exception as exc:
        logger.warning("Migration 27 failed (non-fatal): %s", exc)


async def _migration_28(conn: asyncpg.Connection) -> None:
    try:
        for col in ['page_contact_visible', 'page_faq_visible', 'page_shipping_visible',
                    'page_size_guide_visible', 'page_stylist_visible', 'page_lookbook_visible',
                    'email_from_name', 'email_reply_to', 'email_tracking_enabled',
                    'email_unsubscribe_link', 'email_footer_text']:
            try:
                await conn.execute(f"ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS {col} VARCHAR(500)")
            except Exception:
                pass
        for col in ['page_contact_visible', 'page_faq_visible', 'page_shipping_visible',
                    'page_size_guide_visible', 'page_stylist_visible', 'page_lookbook_visible',
                    'email_tracking_enabled', 'email_unsubscribe_link']:
            try:
                await conn.execute(f"UPDATE store_settings SET {col} = 'true' WHERE {col} IS NULL")
            except Exception:
                pass
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS email_templates (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(255) NOT NULL,
                subject VARCHAR(500) NOT NULL,
                body TEXT NOT NULL,
                category VARCHAR(50) DEFAULT 'custom',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS email_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                recipient_email VARCHAR(255) NOT NULL,
                subject VARCHAR(500) NOT NULL,
                template_id UUID REFERENCES email_templates(id) ON DELETE SET NULL,
                status VARCHAR(50) DEFAULT 'sent',
                sent_at TIMESTAMPTZ DEFAULT NOW(),
                opened_at TIMESTAMPTZ,
                clicked_at TIMESTAMPTZ
            )
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_email_templates_category ON email_templates(category)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_email_logs_recipient ON email_logs(recipient_email)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_email_logs_status ON email_logs(status)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_email_logs_sent_at ON email_logs(sent_at DESC)")
        count = await conn.fetchval("SELECT COUNT(*) FROM email_templates")
        if count == 0:
            await conn.execute("""
                INSERT INTO email_templates (name, subject, body, category) VALUES
                ('Welcome to ASIKO', 'Welcome to ASIKO Boutique!', '<h2>Welcome to ASIKO!</h2><p>Hi {{name}},</p><p>Thank you for joining ASIKO Boutique. We are excited to have you!</p><p>Explore our curated collection of authentic Nigerian fashion with transparent pricing.</p><p>Happy shopping!</p><p>The ASIKO Team</p>', 'welcome'),
                ('Order Confirmation', 'Your ASIKO Order is Confirmed', '<h2>Order Confirmed!</h2><p>Hi {{name}},</p><p>Your order <strong>#{{order_id}}</strong> has been confirmed.</p><p><strong>Total:</strong> {{total}}</p><p>We will send you a shipping update soon.</p><p>The ASIKO Team</p>', 'order'),
                ('Shipping Update', 'Your ASIKO Order Has Been Shipped', '<h2>Your Order is On Its Way!</h2><p>Hi {{name}},</p><p>Your order <strong>#{{order_id}}</strong> has been shipped.</p><p><strong>Carrier:</strong> {{carrier}}</p><p><strong>Tracking:</strong> {{tracking_number}}</p><p>The ASIKO Team</p>', 'order')
            """)
    except Exception as exc:
        logger.warning("Migration 28 failed (non-fatal): %s", exc)


async def _migration_30(conn: asyncpg.Connection) -> None:
    await conn.execute(
        "ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS brand_logo TEXT DEFAULT ''"
    )


async def _migration_31(conn: asyncpg.Connection) -> None:
    for col_def in [
        "ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS brand_name VARCHAR(100) DEFAULT ''",
        "ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS brand_tagline VARCHAR(200) DEFAULT ''",
        "ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS brand_footer_text VARCHAR(300) DEFAULT ''",
        "ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS brand_currency_symbol VARCHAR(10) DEFAULT ''",
        "ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS brand_currency_code VARCHAR(10) DEFAULT ''",
    ]:
        await conn.execute(col_def)


async def _migration_32(conn: asyncpg.Connection) -> None:
    for col_def in [
        "ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS seo_title VARCHAR(200) DEFAULT ''",
        "ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS seo_description TEXT DEFAULT ''",
        "ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS seo_keywords TEXT DEFAULT ''",
        "ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS seo_og_image VARCHAR(500) DEFAULT ''",
        "ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS seo_twitter_handle VARCHAR(100) DEFAULT ''",
        "ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS seo_google_analytics VARCHAR(100) DEFAULT ''",
        "ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS seo_google_tag_manager VARCHAR(100) DEFAULT ''",
        "ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS seo_structured_data BOOLEAN DEFAULT TRUE",
        "ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS seo_sitemap_enabled BOOLEAN DEFAULT TRUE",
        "ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS seo_robots_enabled BOOLEAN DEFAULT TRUE",
        "ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS geo_enabled BOOLEAN DEFAULT TRUE",
        "ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS geo_local_business JSONB DEFAULT '{}'::jsonb",
        "ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS aeo_faq_schema BOOLEAN DEFAULT TRUE",
        "ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS aeo_product_schema BOOLEAN DEFAULT TRUE",
        "ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS smo_twitter_card VARCHAR(50) DEFAULT 'summary_large_image'",
        "ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS smo_facebook_app_id VARCHAR(50) DEFAULT ''",
        "ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS sem_conversion_id VARCHAR(100) DEFAULT ''",
        "ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS sem_conversion_label VARCHAR(100) DEFAULT ''",
        "ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS sem_remarketing_tag TEXT DEFAULT ''",
    ]:
        await conn.execute(col_def)


async def _migration_33(conn: asyncpg.Connection) -> None:
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS seo_settings (
            id INTEGER PRIMARY KEY DEFAULT 1,
            seo_title VARCHAR(200) DEFAULT '',
            seo_description TEXT DEFAULT '',
            seo_keywords TEXT DEFAULT '',
            seo_og_image VARCHAR(500) DEFAULT '',
            seo_twitter_handle VARCHAR(100) DEFAULT '',
            seo_google_analytics VARCHAR(100) DEFAULT '',
            seo_google_tag_manager VARCHAR(100) DEFAULT '',
            seo_structured_data BOOLEAN DEFAULT TRUE,
            seo_sitemap_enabled BOOLEAN DEFAULT TRUE,
            seo_robots_enabled BOOLEAN DEFAULT TRUE,
            geo_enabled BOOLEAN DEFAULT TRUE,
            geo_local_business JSONB DEFAULT '{}'::jsonb,
            aeo_faq_schema BOOLEAN DEFAULT TRUE,
            aeo_product_schema BOOLEAN DEFAULT TRUE,
            smo_twitter_card VARCHAR(50) DEFAULT 'summary_large_image',
            smo_facebook_app_id VARCHAR(50) DEFAULT '',
            sem_conversion_id VARCHAR(100) DEFAULT '',
            sem_conversion_label VARCHAR(100) DEFAULT '',
            sem_remarketing_tag TEXT DEFAULT '',
            updated_at TIMESTAMP DEFAULT now()
        )
    """)
    existing = await conn.fetchval("SELECT COUNT(*) FROM seo_settings")
    if existing == 0:
        await conn.execute("""
            INSERT INTO seo_settings (
                id, seo_title, seo_description, seo_keywords, seo_og_image,
                seo_twitter_handle, seo_google_analytics, seo_google_tag_manager,
                seo_structured_data, seo_sitemap_enabled, seo_robots_enabled,
                geo_enabled, geo_local_business, aeo_faq_schema, aeo_product_schema,
                smo_twitter_card, smo_facebook_app_id, sem_conversion_id,
                sem_conversion_label, sem_remarketing_tag
            )
            SELECT 1,
                COALESCE(seo_title, ''), COALESCE(seo_description, ''), COALESCE(seo_keywords, ''),
                COALESCE(seo_og_image, ''), COALESCE(seo_twitter_handle, ''),
                COALESCE(seo_google_analytics, ''), COALESCE(seo_google_tag_manager, ''),
                COALESCE(seo_structured_data, TRUE), COALESCE(seo_sitemap_enabled, TRUE),
                COALESCE(seo_robots_enabled, TRUE), COALESCE(geo_enabled, TRUE),
                COALESCE(geo_local_business, '{}'::jsonb), COALESCE(aeo_faq_schema, TRUE),
                COALESCE(aeo_product_schema, TRUE), COALESCE(smo_twitter_card, 'summary_large_image'),
                COALESCE(smo_facebook_app_id, ''), COALESCE(sem_conversion_id, ''),
                COALESCE(sem_conversion_label, ''), COALESCE(sem_remarketing_tag, '')
            FROM store_settings WHERE id = 1
            ON CONFLICT (id) DO NOTHING
        """)


async def _migration_34(conn: asyncpg.Connection) -> None:
    for ddl in [
        """CREATE TABLE IF NOT EXISTS store_profile (
            id INTEGER PRIMARY KEY DEFAULT 1,
            store_name VARCHAR(100) DEFAULT 'ASIKO Boutique',
            contact_email VARCHAR(200) DEFAULT '',
            store_description TEXT DEFAULT '',
            phone VARCHAR(50) DEFAULT '',
            store_address VARCHAR(300) DEFAULT '',
            updated_at TIMESTAMP DEFAULT now()
        )""",
        """CREATE TABLE IF NOT EXISTS brand_settings (
            id INTEGER PRIMARY KEY DEFAULT 1,
            brand_name VARCHAR(100) DEFAULT 'ASIKO Boutique',
            brand_tagline VARCHAR(200) DEFAULT 'Authentic Nigerian Fashion',
            brand_footer_text VARCHAR(300) DEFAULT '',
            brand_currency_symbol VARCHAR(10) DEFAULT '&#8358;',
            brand_currency_code VARCHAR(10) DEFAULT 'NGN',
            brand_logo TEXT DEFAULT '',
            updated_at TIMESTAMP DEFAULT now()
        )""",
        """CREATE TABLE IF NOT EXISTS ai_settings (
            id INTEGER PRIMARY KEY DEFAULT 1,
            ai_provider VARCHAR(20) DEFAULT 'openrouter',
            ai_api_key VARCHAR(500) DEFAULT '',
            ai_model VARCHAR(120) DEFAULT 'google/gemini-2.0-flash-001',
            ai_system_prompt TEXT DEFAULT '',
            ai_max_tokens INTEGER DEFAULT 1024,
            ai_temperature REAL DEFAULT 0.7,
            ai_stylist_enabled BOOLEAN DEFAULT TRUE,
            ai_stylist_welcome TEXT DEFAULT '',
            ai_stylist_suggestions TEXT DEFAULT '',
            mesh_provider VARCHAR(50) DEFAULT 'hunyuan3d2',
            auto_mesh BOOLEAN DEFAULT TRUE,
            updated_at TIMESTAMP DEFAULT now()
        )""",
        """CREATE TABLE IF NOT EXISTS chatbot_settings (
            id INTEGER PRIMARY KEY DEFAULT 1,
            chatbot_enabled BOOLEAN DEFAULT TRUE,
            chatbot_welcome TEXT DEFAULT '',
            chatbot_color_primary VARCHAR(20) DEFAULT '#0D2A22',
            chatbot_color_accent VARCHAR(20) DEFAULT '#D4AF37',
            updated_at TIMESTAMP DEFAULT now()
        )""",
        """CREATE TABLE IF NOT EXISTS page_settings (
            id INTEGER PRIMARY KEY DEFAULT 1,
            hero_title VARCHAR(100) DEFAULT 'Authentic',
            hero_title_accent VARCHAR(100) DEFAULT 'Nigerian Fashion',
            hero_subtitle TEXT DEFAULT '',
            hero_badge_text VARCHAR(100) DEFAULT '',
            hero_cta_text VARCHAR(50) DEFAULT 'Shop Collection',
            hero_cta_link VARCHAR(200) DEFAULT '#storefront',
            lookbook_title VARCHAR(100) DEFAULT 'The Lookbook',
            lookbook_subtitle TEXT DEFAULT '',
            about_title VARCHAR(100) DEFAULT 'ASIKO Boutique',
            about_tagline VARCHAR(200) DEFAULT '',
            about_story TEXT DEFAULT '',
            about_location VARCHAR(100) DEFAULT 'Lagos, Nigeria',
            about_email VARCHAR(200) DEFAULT '',
            about_founded_year INTEGER DEFAULT 2024,
            customer_welcome_title VARCHAR(100) DEFAULT 'Welcome back',
            customer_welcome_subtitle TEXT DEFAULT '',
            currency VARCHAR(10) DEFAULT 'NGN',
            timezone VARCHAR(50) DEFAULT 'Africa/Lagos',
            locale VARCHAR(10) DEFAULT 'en',
            blog_enabled BOOLEAN DEFAULT TRUE,
            blog_posts_per_page INTEGER DEFAULT 6,
            session_timeout INTEGER DEFAULT 30,
            page_contact_visible BOOLEAN DEFAULT TRUE,
            page_faq_visible BOOLEAN DEFAULT TRUE,
            page_shipping_visible BOOLEAN DEFAULT TRUE,
            page_size_guide_visible BOOLEAN DEFAULT TRUE,
            page_stylist_visible BOOLEAN DEFAULT TRUE,
            page_lookbook_visible BOOLEAN DEFAULT TRUE,
            updated_at TIMESTAMP DEFAULT now()
        )""",
        """CREATE TABLE IF NOT EXISTS shop_settings (
            id INTEGER PRIMARY KEY DEFAULT 1,
            shop_products_per_page INTEGER DEFAULT 12,
            shop_default_sort VARCHAR(20) DEFAULT 'newest',
            shop_show_3d_badge BOOLEAN DEFAULT TRUE,
            shipping_domestic REAL DEFAULT 0,
            shipping_international REAL DEFAULT 0,
            free_shipping_threshold REAL DEFAULT 0,
            updated_at TIMESTAMP DEFAULT now()
        )""",
        """CREATE TABLE IF NOT EXISTS notification_settings (
            id INTEGER PRIMARY KEY DEFAULT 1,
            notif_new_order BOOLEAN DEFAULT TRUE,
            notif_pipeline BOOLEAN DEFAULT TRUE,
            notif_review BOOLEAN DEFAULT TRUE,
            notif_low_stock BOOLEAN DEFAULT TRUE,
            email_from_name VARCHAR(100) DEFAULT 'ASIKO Boutique',
            email_reply_to VARCHAR(200) DEFAULT '',
            email_tracking_enabled BOOLEAN DEFAULT TRUE,
            email_unsubscribe_link BOOLEAN DEFAULT TRUE,
            email_footer_text TEXT DEFAULT '',
            brevo_api_key VARCHAR(500) DEFAULT '',
            sender_name VARCHAR(100) DEFAULT 'ASIKO Boutique',
            admin_email VARCHAR(200) DEFAULT '',
            email_welcome_enabled BOOLEAN DEFAULT TRUE,
            email_order_enabled BOOLEAN DEFAULT TRUE,
            email_shipping_enabled BOOLEAN DEFAULT TRUE,
            email_newsletter_enabled BOOLEAN DEFAULT TRUE,
            email_password_reset_enabled BOOLEAN DEFAULT TRUE,
            updated_at TIMESTAMP DEFAULT now()
        )""",
    ]:
        await conn.execute(ddl)

    migrate_queries = [
        """INSERT INTO store_profile (id, store_name, contact_email, store_description, phone, store_address)
           SELECT 1, COALESCE(store_name,'ASIKO Boutique'), COALESCE(contact_email,''),
                  COALESCE(store_description,''), COALESCE(phone,''), COALESCE(store_address,'')
           FROM store_settings WHERE id = 1
           ON CONFLICT (id) DO NOTHING""",
        """INSERT INTO brand_settings (id, brand_name, brand_tagline, brand_footer_text, brand_currency_symbol, brand_currency_code, brand_logo)
           SELECT 1, COALESCE(brand_name,'ASIKO Boutique'), COALESCE(brand_tagline,'Authentic Nigerian Fashion'),
                  COALESCE(brand_footer_text,''), COALESCE(brand_currency_symbol,'&#8358;'),
                  COALESCE(brand_currency_code,'NGN'), COALESCE(brand_logo,'')
           FROM store_settings WHERE id = 1
           ON CONFLICT (id) DO NOTHING""",
        """INSERT INTO ai_settings (id, ai_provider, ai_api_key, ai_model, ai_system_prompt, ai_max_tokens, ai_temperature,
                                    ai_stylist_enabled, ai_stylist_welcome, ai_stylist_suggestions, mesh_provider, auto_mesh)
           SELECT 1, COALESCE(ai_provider,'openrouter'), COALESCE(ai_api_key,''),
                  COALESCE(ai_model,'google/gemini-2.0-flash-001'), COALESCE(ai_system_prompt,''),
                  COALESCE(ai_max_tokens,1024), COALESCE(ai_temperature,0.7),
                  COALESCE(ai_stylist_enabled,TRUE), COALESCE(ai_stylist_welcome,''),
                  COALESCE(ai_stylist_suggestions,''), COALESCE(mesh_provider,'hunyuan3d2'), COALESCE(auto_mesh,TRUE)
           FROM store_settings WHERE id = 1
           ON CONFLICT (id) DO NOTHING""",
        """INSERT INTO chatbot_settings (id, chatbot_enabled, chatbot_welcome, chatbot_color_primary, chatbot_color_accent)
           SELECT 1, COALESCE(chatbot_enabled,TRUE), COALESCE(chatbot_welcome,''),
                  COALESCE(chatbot_color_primary,'#0D2A22'), COALESCE(chatbot_color_accent,'#D4AF37')
           FROM store_settings WHERE id = 1
           ON CONFLICT (id) DO NOTHING""",
        """INSERT INTO page_settings (id, hero_title, hero_title_accent, hero_subtitle, hero_badge_text, hero_cta_text, hero_cta_link,
                                      lookbook_title, lookbook_subtitle, about_title, about_tagline, about_story,
                                      about_location, about_email, about_founded_year,
                                      customer_welcome_title, customer_welcome_subtitle,
                                      currency, timezone, locale, blog_enabled, blog_posts_per_page,
                                      session_timeout, page_contact_visible, page_faq_visible, page_shipping_visible,
                                      page_size_guide_visible, page_stylist_visible, page_lookbook_visible)
           SELECT 1, COALESCE(hero_title,'Authentic'), COALESCE(hero_title_accent,'Nigerian Fashion'),
                  COALESCE(hero_subtitle,''), COALESCE(hero_badge_text,''), COALESCE(hero_cta_text,'Shop Collection'),
                  COALESCE(hero_cta_link,'#storefront'),
                  COALESCE(lookbook_title,'The Lookbook'), COALESCE(lookbook_subtitle,''),
                  COALESCE(about_title,'ASIKO Boutique'), COALESCE(about_tagline,''), COALESCE(about_story,''),
                  COALESCE(about_location,'Lagos, Nigeria'), COALESCE(about_email,''), COALESCE(about_founded_year,2024),
                  COALESCE(customer_welcome_title,'Welcome back'), COALESCE(customer_welcome_subtitle,''),
                  COALESCE(currency,'NGN'), COALESCE(timezone,'Africa/Lagos'), COALESCE(locale,'en'),
                  (COALESCE(blog_enabled, 'true'))::boolean, COALESCE(blog_posts_per_page,6), COALESCE(session_timeout,30),
                  (COALESCE(page_contact_visible, 'true'))::boolean, (COALESCE(page_faq_visible, 'true'))::boolean, (COALESCE(page_shipping_visible, 'true'))::boolean,
                  (COALESCE(page_size_guide_visible, 'true'))::boolean, (COALESCE(page_stylist_visible, 'true'))::boolean, (COALESCE(page_lookbook_visible, 'true'))::boolean
           FROM store_settings WHERE id = 1
           ON CONFLICT (id) DO NOTHING""",
        """INSERT INTO shop_settings (id, shop_products_per_page, shop_default_sort, shop_show_3d_badge,
                                      shipping_domestic, shipping_international, free_shipping_threshold)
           SELECT 1, COALESCE(shop_products_per_page,12), COALESCE(shop_default_sort,'newest'),
                  (COALESCE(shop_show_3d_badge, 'true'))::boolean,
                  COALESCE(shipping_domestic,0), COALESCE(shipping_international,0), COALESCE(free_shipping_threshold,0)
           FROM store_settings WHERE id = 1
           ON CONFLICT (id) DO NOTHING""",
        """INSERT INTO notification_settings (id, notif_new_order, notif_pipeline, notif_review, notif_low_stock,
                                             email_from_name, email_reply_to, email_tracking_enabled,
                                             email_unsubscribe_link, email_footer_text)
           SELECT 1, (COALESCE(notif_new_order, 'true'))::boolean, (COALESCE(notif_pipeline, 'true'))::boolean,
                  (COALESCE(notif_review, 'true'))::boolean, (COALESCE(notif_low_stock, 'true'))::boolean,
                  COALESCE(sender_name,'ASIKO Boutique'), COALESCE(admin_email,'hello@asikoboutique.com'),
                  (COALESCE(email_tracking_enabled, 'true'))::boolean, (COALESCE(email_unsubscribe_link, 'true'))::boolean,
                  COALESCE(email_footer_text,'')
           FROM store_settings WHERE id = 1
           ON CONFLICT (id) DO NOTHING""",
    ]
    for q in migrate_queries:
        await conn.execute(q)


async def _migration_35(conn: asyncpg.Connection) -> None:
    for col in [
        "ALTER TABLE notification_settings ADD COLUMN IF NOT EXISTS brevo_api_key VARCHAR(500) DEFAULT ''",
        "ALTER TABLE notification_settings ADD COLUMN IF NOT EXISTS sender_name VARCHAR(100) DEFAULT 'ASIKO Boutique'",
        "ALTER TABLE notification_settings ADD COLUMN IF NOT EXISTS admin_email VARCHAR(200) DEFAULT ''",
        "ALTER TABLE notification_settings ADD COLUMN IF NOT EXISTS email_welcome_enabled BOOLEAN DEFAULT TRUE",
        "ALTER TABLE notification_settings ADD COLUMN IF NOT EXISTS email_order_enabled BOOLEAN DEFAULT TRUE",
        "ALTER TABLE notification_settings ADD COLUMN IF NOT EXISTS email_shipping_enabled BOOLEAN DEFAULT TRUE",
        "ALTER TABLE notification_settings ADD COLUMN IF NOT EXISTS email_newsletter_enabled BOOLEAN DEFAULT TRUE",
        "ALTER TABLE notification_settings ADD COLUMN IF NOT EXISTS email_password_reset_enabled BOOLEAN DEFAULT TRUE",
    ]:
        await conn.execute(col)
