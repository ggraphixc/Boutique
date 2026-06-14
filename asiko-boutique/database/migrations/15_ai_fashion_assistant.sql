-- Migration 15: AI Fashion Assistant tables
-- user_preferences, wardrobe_items, color_profiles, style_events, trend_data

-- User fashion preferences (linked to customer or session)
CREATE TABLE IF NOT EXISTS user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    session_id TEXT UNIQUE,
    style_profiles TEXT[] DEFAULT '{}',       -- ['casual', 'traditional', 'formal', 'streetwear', 'bohemian']
    favorite_colors TEXT[] DEFAULT '{}',      -- ['earth tones', 'jewel tones', 'pastels', 'monochrome']
    preferred_fit TEXT DEFAULT 'regular',     -- slim/regular/loose/oversized
    size_top TEXT,                            -- XS/S/M/L/XL/XXL
    size_bottom TEXT,                         -- 28/30/32/34/36/38/40
    shoe_size NUMERIC(4,1),
    budget_min NUMERIC(10,2) DEFAULT 0,
    budget_max NUMERIC(10,2) DEFAULT 100000,
    occasions TEXT[] DEFAULT '{}',            -- ['wedding', 'church', 'office', 'party', 'casual']
    season_preference TEXT DEFAULT 'all',     -- all/harmattan/rainy/dry
    skin_tone TEXT,                           -- fair/light/medium/olive/dark/deep
    skin_undertone TEXT,                      -- warm/cool/neutral
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Wardrobe items (clothes the user already owns)
CREATE TABLE IF NOT EXISTS wardrobe_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    session_id TEXT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,                   -- dress/shirt/trouser/skirt/jacket/hoodie/shoe/bag/accessory
    subcategory TEXT,                         -- blouse/polo/chinos/jeans/blazer/cardigan/sneakers/heels/clutch
    color_primary TEXT,                       -- main color name
    color_hex VARCHAR(7),                     -- #RRGGBB
    color_secondary TEXT,                     -- accent color
    pattern TEXT DEFAULT 'solid',             -- solid/striped/plaid/floral/geometric/abstract
    fabric TEXT,                              -- cotton/silk/denim/leather/wool/lace/chiffon/satin
    season TEXT DEFAULT 'all',                -- all/harmattan/rainy/dry
    occasions TEXT[] DEFAULT '{}',            -- ['casual', 'formal', 'party']
    image_url TEXT,                           -- uploaded photo path
    condition TEXT DEFAULT 'good',            -- new/good/fair/worn
    brand TEXT,
    notes TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Color profile (computed from skin tone analysis)
CREATE TABLE IF NOT EXISTS color_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    session_id TEXT,
    skin_tone TEXT NOT NULL,                  -- fair/light/medium/olive/dark/deep
    skin_undertone TEXT NOT NULL,             -- warm/cool/neutral
    best_colors TEXT[] DEFAULT '{}',          -- colors that complement this skin tone
    avoid_colors TEXT[] DEFAULT '{}',         -- colors to avoid
    best_neutrals TEXT[] DEFAULT '{}',        -- best neutral colors
    best_metals TEXT[] DEFAULT '{}',          -- gold/silver/rose gold
    seasonal_palette TEXT,                    -- spring/summer/autumn/winter (color season analysis)
    photo_url TEXT,                           -- uploaded photo for analysis
    confidence_score NUMERIC(3,2) DEFAULT 0.8,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Style events (occasions and their fashion rules)
CREATE TABLE IF NOT EXISTS style_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    slug TEXT UNIQUE NOT NULL,
    description TEXT,
    dress_code TEXT,                          -- casual/smart-casual/business/formal/traditional/cocktail
    recommended_categories TEXT[] DEFAULT '{}', -- which product categories fit this event
    recommended_fabrics TEXT[] DEFAULT '{}',
    recommended_colors TEXT[] DEFAULT '{}',
    avoid_colors TEXT[] DEFAULT '{}',
    avoid_fabrics TEXT[] DEFAULT '{}',
    icon_emoji TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Nigerian fashion trends
CREATE TABLE IF NOT EXISTS trend_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    category TEXT NOT NULL,                   -- fabric/style/color/silhouette/print
    description TEXT,
    region TEXT DEFAULT 'nigeria',            -- nigeria/west_africa/global
    popularity_score NUMERIC(3,2) DEFAULT 0.5, -- 0.0 to 1.0
    season TEXT DEFAULT 'all',
    keywords TEXT[] DEFAULT '{}',
    image_url TEXT,
    source TEXT,                              -- where this trend was observed
    is_active BOOLEAN DEFAULT TRUE,
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Chat history (for style assistant conversations)
CREATE TABLE IF NOT EXISTS fashion_chat_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    session_id TEXT,
    role TEXT NOT NULL,                       -- user/assistant
    message TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',              -- product_ids, event_type, etc.
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed default style events
INSERT INTO style_events (name, slug, description, dress_code, recommended_categories, recommended_fabrics, recommended_colors, avoid_colors, icon_emoji) VALUES
('Wedding Guest', 'wedding-guest', 'Attending a wedding celebration', 'formal',
 ARRAY['dress', 'shirt', 'trouser', 'skirt', 'jacket', 'shoe', 'bag'],
 ARRAY['silk', 'lace', 'chiffon', 'satin'],
 ARRAY['jewel tones', 'pastels', 'gold', 'emerald', 'royal blue', 'burgundy'],
 ARRAY['white', 'black', 'cream'],
 '💒'),
('Church Service', 'church', 'Sunday church service', 'smart-casual',
 ARRAY['dress', 'shirt', 'trouser', 'skirt', 'jacket', 'shoe'],
 ARRAY['cotton', 'lace', 'silk', 'chiffon'],
 ARRAY['white', 'earth tones', 'pastels', 'jewel tones'],
 ARRAY['revealing cuts', 'excessively bright neon'],
 '⛪'),
('Office / Work', 'office', 'Professional workplace attire', 'business',
 ARRAY['shirt', 'trouser', 'skirt', 'jacket', 'shoe', 'bag'],
 ARRAY['cotton', 'wool', 'satin'],
 ARRAY['neutrals', 'navy', 'grey', 'white', 'earth tones'],
 ARRAY['neon', 'excessively casual', 'ripped'],
 '💼'),
('Party / Night Out', 'party', 'Evening party or nightlife', 'cocktail',
 ARRAY['dress', 'shirt', 'trouser', 'skirt', 'shoe', 'bag'],
 ARRAY['silk', 'satin', 'leather', 'lace', 'velvet'],
 ARRAY['black', 'red', 'gold', 'metallic', 'jewel tones'],
 ARRAY['overly conservative', 'wrinkled'],
 '🎉'),
('Casual Outing', 'casual', 'Everyday casual wear', 'casual',
 ARRAY['shirt', 'trouser', 'skirt', 'hoodie', 'shoe'],
 ARRAY['cotton', 'denim', 'linen'],
 ARRAY['earth tones', 'pastels', 'monochrome', 'brights'],
 ARRAY['overly formal fabrics'],
 '🌿'),
('Traditional Event', 'traditional', 'Traditional Nigerian ceremony or celebration', 'traditional',
 ARRAY['dress', 'shirt', 'trouser', 'skirt', 'jacket', 'shoe', 'bag'],
 ARRAY['ankara', 'aso-oke', 'adire', 'lace', 'silk'],
 ARRAY['gold', 'royal blue', 'green', 'wine', 'coral', 'mustard'],
 ARRAY['plain western-only looks'],
 '🎭'),
('Date Night', 'date-night', 'Romantic evening or dinner date', 'smart-casual',
 ARRAY['dress', 'shirt', 'trouser', 'skirt', 'shoe', 'bag'],
 ARRAY['silk', 'satin', 'chiffon', 'leather'],
 ARRAY['red', 'black', 'burgundy', 'pastels', 'jewel tones'],
 ARRAY['overly casual', 'wrinkled'],
 '💕'),
('Business Meeting', 'business-meeting', 'Formal business meeting or presentation', 'formal',
 ARRAY['shirt', 'trouser', 'skirt', 'jacket', 'shoe', 'bag'],
 ARRAY['wool', 'cotton', 'satin'],
 ARRAY['navy', 'grey', 'black', 'white', 'earth tones'],
 ARRAY['casual', 'bright patterns'],
 '📊')
ON CONFLICT (name) DO NOTHING;

-- Seed Nigerian fashion trends (2024-2025)
INSERT INTO trend_data (name, category, description, region, popularity_score, season, keywords) VALUES
('Ankara Modern Fusion', 'style', 'Contemporary cuts using traditional Ankara fabric', 'nigeria', 0.9, 'all', ARRAY['ankara', 'modern', 'fusion', 'contemporary']),
('Oversized Blazers', 'silhouette', 'Relaxed-fit blazers for both men and women', 'global', 0.85, 'all', ARRAY['blazer', 'oversized', 'structured', 'power dressing']),
('Earth Tone Palettes', 'color', 'Warm browns, terracotta, olive, and cream combinations', 'global', 0.88, 'all', ARRAY['earth tones', 'brown', 'terracotta', 'olive', 'cream']),
('Aso-Oke Revival', 'fabric', 'Modern interpretations of traditional Aso-Oke weaving', 'nigeria', 0.82, 'all', ARRAY['aso-oke', 'traditional', 'weaving', 'handwoven']),
('Satin Slip Dresses', 'style', 'Minimalist satin slip dresses for events', 'global', 0.8, 'rainy', ARRAY['satin', 'slip dress', 'minimalist', 'elegant']),
('Agbada Modernization', 'style', 'Contemporary Agbada designs with modern tailoring', 'nigeria', 0.87, 'all', ARRAY['agbada', 'traditional', 'modern', 'tailoring']),
('Chunky Sneakers', 'style', 'Platform and chunky sneaker designs', 'global', 0.75, 'dry', ARRAY['sneakers', 'chunky', 'platform', 'streetwear']),
('Lace Overlay', 'fabric', 'Intricate lace overlays on dresses and tops', 'nigeria', 0.83, 'all', ARRAY['lace', 'overlay', 'intricate', 'elegant']),
('Monochrome Styling', 'color', 'Head-to-toe single color outfits', 'global', 0.78, 'all', ARRAY['monochrome', 'single color', 'minimalist', 'clean']),
('Adire Renaissance', 'fabric', 'Traditional Adire tie-dye patterns in modern silhouettes', 'nigeria', 0.81, 'dry', ARRAY['adire', 'tie-dye', 'traditional', 'indigo']),
('Wide-Leg Trousers', 'silhouette', 'Flowing wide-leg trousers replacing skinny fits', 'global', 0.82, 'all', ARRAY['wide-leg', 'trousers', 'flowing', 'relaxed']),
('Coral and Gold', 'color', 'Coral accessories with gold jewelry combinations', 'nigeria', 0.79, 'all', ARRAY['coral', 'gold', 'accessories', 'jewelry']),
('Layered Necklaces', 'accessory', 'Multiple delicate chains and pendant combinations', 'global', 0.77, 'all', ARRAY['necklaces', 'layered', 'delicate', 'gold']),
('Structured Shoulders', 'silhouette', 'Strong shoulder lines in blazers and dresses', 'global', 0.76, 'all', ARRAY['shoulders', 'structured', 'power', 'blazer']),
('Bold Print Mixing', 'style', 'Combining multiple print patterns in one outfit', 'nigeria', 0.74, 'all', ARRAY['prints', 'mixing', 'bold', 'pattern'])
ON CONFLICT DO NOTHING;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_wardrobe_session ON wardrobe_items(session_id);
CREATE INDEX IF NOT EXISTS idx_wardrobe_customer ON wardrobe_items(customer_id);
CREATE INDEX IF NOT EXISTS idx_preferences_session ON user_preferences(session_id);
CREATE INDEX IF NOT EXISTS idx_preferences_customer ON user_preferences(customer_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_session ON fashion_chat_history(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_customer ON fashion_chat_history(customer_id);
CREATE INDEX IF NOT EXISTS idx_trend_category ON trend_data(category);
CREATE INDEX IF NOT EXISTS idx_trend_active ON trend_data(is_active);
CREATE INDEX IF NOT EXISTS idx_events_active ON style_events(is_active);
