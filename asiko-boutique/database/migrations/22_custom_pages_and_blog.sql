-- Migration 22: Custom Pages & Blog System
-- Owner can create pages, toggle go-live, choose navbar vs footer placement.
-- Content pages (blog) support posts that owner can publish anytime.

CREATE TABLE IF NOT EXISTS custom_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL UNIQUE,
    page_type VARCHAR(50) NOT NULL DEFAULT 'content',  -- content, blog, policy, static
    body_html TEXT DEFAULT '',                           -- main page HTML content
    excerpt TEXT DEFAULT '',                             -- short description for cards
    meta_description TEXT DEFAULT '',                    -- SEO
    featured_image TEXT DEFAULT '',                      -- hero/banner image URL
    show_in_nav BOOLEAN DEFAULT FALSE,                  -- appear in storefront navbar
    show_in_footer BOOLEAN DEFAULT FALSE,               -- appear in storefront footer
    is_live BOOLEAN DEFAULT FALSE,                      -- go-live toggle
    sort_order INTEGER DEFAULT 0,                       -- ordering in nav/footer
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_custom_pages_slug ON custom_pages(slug);
CREATE INDEX IF NOT EXISTS idx_custom_pages_live ON custom_pages(is_live);
CREATE INDEX IF NOT EXISTS idx_custom_pages_type ON custom_pages(page_type);

CREATE TABLE IF NOT EXISTS blog_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    page_id UUID NOT NULL REFERENCES custom_pages(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    content_html TEXT DEFAULT '',
    excerpt TEXT DEFAULT '',
    featured_image TEXT DEFAULT '',
    author_name VARCHAR(100) DEFAULT '',
    is_published BOOLEAN DEFAULT FALSE,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(page_id, slug)
);

CREATE INDEX IF NOT EXISTS idx_blog_posts_page ON blog_posts(page_id);
CREATE INDEX IF NOT EXISTS idx_blog_posts_published ON blog_posts(is_published, published_at DESC);
