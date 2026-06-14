-- Migration 20: Expand store_settings for AI Stylist + page configuration
-- Adds AI provider settings, stylist config, and page-level configs

-- AI Provider settings
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS ai_provider VARCHAR(20) NOT NULL DEFAULT 'openrouter';
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS ai_api_key TEXT NOT NULL DEFAULT '';
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS ai_model VARCHAR(120) NOT NULL DEFAULT 'google/gemini-2.0-flash-001';
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS ai_system_prompt TEXT NOT NULL DEFAULT '';
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS ai_max_tokens INT NOT NULL DEFAULT 1024;
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS ai_temperature NUMERIC(3,2) NOT NULL DEFAULT 0.70;

-- AI Stylist page config
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS ai_stylist_enabled BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS ai_stylist_welcome TEXT NOT NULL DEFAULT 'Hello! I''m your personal ASIKO fashion stylist. I can help you find the perfect outfit, suggest color combinations, and keep you on trend. What can I help you with today?';
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS ai_stylist_suggestions TEXT NOT NULL DEFAULT 'What should I wear to a wedding?,Recommend something casual,What colors match my skin tone?,What is trending in Nigerian fashion?';

-- Homepage config
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS hero_title TEXT NOT NULL DEFAULT 'Authentic';
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS hero_title_accent TEXT NOT NULL DEFAULT 'Nigerian Fashion';
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS hero_subtitle TEXT NOT NULL DEFAULT 'Shop curated styles with transparent pricing. Every piece crafted with verified provenance and fair-trade standards.';
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS hero_badge_text TEXT NOT NULL DEFAULT 'New Collection Available';
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS hero_cta_text TEXT NOT NULL DEFAULT 'Shop Collection';
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS hero_cta_link TEXT NOT NULL DEFAULT '#storefront';

-- Shop config
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS shop_products_per_page INT NOT NULL DEFAULT 12;
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS shop_default_sort VARCHAR(30) NOT NULL DEFAULT 'newest';
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS shop_show_3d_badge BOOLEAN NOT NULL DEFAULT true;

-- Lookbook config
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS lookbook_title TEXT NOT NULL DEFAULT 'The Lookbook';
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS lookbook_subtitle TEXT NOT NULL DEFAULT 'Curated ensembles and styling inspiration from ASIKO''s collection.';

-- About page config
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS about_title TEXT NOT NULL DEFAULT 'ASIKO Boutique';
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS about_tagline TEXT NOT NULL DEFAULT 'Authentic Nigerian Fashion';
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS about_story TEXT NOT NULL DEFAULT 'ASIKO was founded with a mission to bring transparent, verified Nigerian fashion to the world. Every piece in our collection is crafted with care, using traditional techniques and modern design.';
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS about_location TEXT NOT NULL DEFAULT 'Lagos, Nigeria';
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS about_email TEXT NOT NULL DEFAULT 'hello@asikoboutique.com';
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS about_founded_year INT NOT NULL DEFAULT 2024;

-- Customer dashboard config
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS customer_welcome_title TEXT NOT NULL DEFAULT 'Welcome back';
ALTER TABLE store_settings ADD COLUMN IF NOT EXISTS customer_welcome_subtitle TEXT NOT NULL DEFAULT 'Manage your orders and discover new styles.';
