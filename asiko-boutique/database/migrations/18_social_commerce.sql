-- Migration 18: Social Commerce
-- Fashion feed, outfit sharing, influencer profiles, follows

-- Fashion feed posts (outfit sharing)
CREATE TABLE IF NOT EXISTS fashion_feed_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id),
    post_type VARCHAR(20) DEFAULT 'outfit'
        CHECK (post_type IN ('outfit','review','lookbook','trend','tutorial')),
    title VARCHAR(200),
    content TEXT,
    images TEXT[],
    product_ids UUID[],
    look_data JSONB,
    likes_count INT DEFAULT 0,
    comments_count INT DEFAULT 0,
    shares_count INT DEFAULT 0,
    is_featured BOOLEAN DEFAULT FALSE,
    is_public BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ffp_customer ON fashion_feed_posts(customer_id);
CREATE INDEX IF NOT EXISTS idx_ffp_type ON fashion_feed_posts(post_type);
CREATE INDEX IF NOT EXISTS idx_ffp_created ON fashion_feed_posts(created_at DESC);

-- Feed likes
CREATE TABLE IF NOT EXISTS feed_likes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES fashion_feed_posts(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(post_id, customer_id)
);

-- Feed comments
CREATE TABLE IF NOT EXISTS feed_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES fashion_feed_posts(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id),
    content TEXT NOT NULL,
    parent_id UUID REFERENCES feed_comments(id),
    likes_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fc_post ON feed_comments(post_id);

-- Enhance product_reviews with social fields
ALTER TABLE product_reviews ADD COLUMN IF NOT EXISTS images TEXT[];
ALTER TABLE product_reviews ADD COLUMN IF NOT EXISTS fit_rating INT
    CHECK (fit_rating BETWEEN 1 AND 5);
ALTER TABLE product_reviews ADD COLUMN IF NOT EXISTS body_type VARCHAR(30);
ALTER TABLE product_reviews ADD COLUMN IF NOT EXISTS height_cm INT;
ALTER TABLE product_reviews ADD COLUMN IF NOT EXISTS weight_kg INT;
ALTER TABLE product_reviews ADD COLUMN IF NOT EXISTS helpful_count INT DEFAULT 0;
ALTER TABLE product_reviews ADD COLUMN IF NOT EXISTS verified_purchase BOOLEAN DEFAULT FALSE;

-- Influencer profiles
CREATE TABLE IF NOT EXISTS influencer_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID UNIQUE REFERENCES customers(id),
    display_name VARCHAR(100) NOT NULL,
    bio TEXT,
    avatar_url TEXT,
    platform_links JSONB,
    follower_count INT DEFAULT 0,
    engagement_rate NUMERIC(5,2) DEFAULT 0,
    total_posts INT DEFAULT 0,
    total_referrals INT DEFAULT 0,
    total_earnings NUMERIC(12,2) DEFAULT 0,
    tier VARCHAR(20) DEFAULT 'micro'
        CHECK (tier IN ('nano','micro','mid','macro','mega')),
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Follow relationships
CREATE TABLE IF NOT EXISTS follows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    follower_id UUID NOT NULL REFERENCES customers(id),
    following_type VARCHAR(20) NOT NULL CHECK (following_type IN ('customer','store','influencer')),
    following_id UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(follower_id, following_type, following_id)
);

-- Outfit boards (saved outfit combinations)
CREATE TABLE IF NOT EXISTS outfit_boards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    occasion VARCHAR(50),
    products JSONB NOT NULL,
    cover_image TEXT,
    is_public BOOLEAN DEFAULT TRUE,
    likes_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
