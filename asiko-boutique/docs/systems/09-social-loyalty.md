# I. SOCIAL & LOYALTY SYSTEMS

## Overview

These 3 systems handle the social commerce layer, loyalty/VIP program, and analytics tracking. All implemented via database migrations with admin management.

---

## 1. Social Commerce

**Database:** Migration 18 (`18_social_commerce.sql`)

### What It Does
Social features for customer engagement — fashion feed posts, likes, comments, influencer profiles, follows, and outfit boards.

### Database Tables

#### fashion_feed_posts
```sql
CREATE TABLE fashion_feed_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id),
    product_id UUID REFERENCES products(id),
    title VARCHAR(200),
    body TEXT,
    image_url TEXT,
    post_type VARCHAR(30) DEFAULT 'style_post',
    likes_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    is_featured BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### feed_likes
```sql
CREATE TABLE feed_likes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES fashion_feed_posts(id) ON DELETE CASCADE,
    customer_id UUID REFERENCES customers(id),
    session_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(post_id, customer_id)
);
```

#### feed_comments
```sql
CREATE TABLE feed_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES fashion_feed_posts(id) ON DELETE CASCADE,
    customer_id UUID REFERENCES customers(id),
    body TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### influencer_profiles
```sql
CREATE TABLE influencer_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id),
    display_name VARCHAR(100),
    bio TEXT,
    avatar_url TEXT,
    followers_count INTEGER DEFAULT 0,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### follows
```sql
CREATE TABLE follows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    follower_id UUID NOT NULL REFERENCES customers(id),
    following_id UUID NOT NULL REFERENCES customers(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(follower_id, following_id)
);
```

#### outfit_boards
```sql
CREATE TABLE outfit_boards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id),
    title VARCHAR(200),
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Why It Matters
Social commerce turns customers into brand ambassadors. User-generated content drives organic reach.

---

## 2. Loyalty & VIP System

**Database:** Migration 19 (`19_loyalty_system.sql`)

### What It Does
Points-based loyalty program with VIP tiers, referrals, and a rewards catalog. Customers earn points on purchases and redeem them for rewards.

### Database Tables

#### loyalty_accounts
```sql
CREATE TABLE loyalty_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID UNIQUE NOT NULL REFERENCES customers(id),
    points_balance INTEGER DEFAULT 0,
    total_points_earned INTEGER DEFAULT 0,
    tier VARCHAR(30) DEFAULT 'bronze',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### loyalty_points
```sql
CREATE TABLE loyalty_points (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES loyalty_accounts(id),
    points INTEGER NOT NULL,
    reason VARCHAR(50) NOT NULL,
    reference_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### vip_tiers (5 seeded)
```sql
CREATE TABLE vip_tiers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,
    min_points INTEGER NOT NULL,
    discount_percent NUMERIC(5,2) DEFAULT 0,
    benefits JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Seeded Tiers:**
| Tier | Min Points | Discount | Benefits |
|------|-----------|----------|----------|
| Bronze | 0 | 0% | Basic member |
| Silver | 1,000 | 5% | Free shipping |
| Gold | 5,000 | 10% | Free shipping, early access |
| Platinum | 15,000 | 15% | Free shipping, early access, personal stylist |
| Diamond | 50,000 | 20% | All benefits + VIP events |

#### referrals
```sql
CREATE TABLE referrals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    referrer_id UUID NOT NULL REFERENCES customers(id),
    referred_email VARCHAR(200) NOT NULL,
    referred_customer_id UUID REFERENCES customers(id),
    status VARCHAR(30) DEFAULT 'pending',
    reward_points INTEGER DEFAULT 500,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### rewards_catalog (5 seeded)
```sql
CREATE TABLE rewards_catalog (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    points_cost INTEGER NOT NULL,
    reward_type VARCHAR(50) NOT NULL,
    reward_value NUMERIC(10,2),
    is_active BOOLEAN DEFAULT TRUE,
    stock INTEGER DEFAULT -1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Seeded Rewards:**
| Reward | Points Cost | Type | Value |
|--------|------------|------|-------|
| 10% Off Next Order | 500 | discount | 10% |
| Free Shipping | 300 | shipping | ₦0 |
| ₦2,000 Store Credit | 2,000 | credit | ₦2,000 |
| Exclusive Styling Session | 3,000 | experience | — |
| Limited Edition Item | 5,000 | product | — |

#### point_redemptions
```sql
CREATE TABLE point_redemptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES loyalty_accounts(id),
    reward_id UUID NOT NULL REFERENCES rewards_catalog(id),
    points_spent INTEGER NOT NULL,
    status VARCHAR(30) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Points Earning Rules
| Action | Points |
|--------|--------|
| Purchase (per ₦1,000) | 10 points |
| Write a review | 50 points |
| Refer a friend (on signup) | 500 points |
| Birthday bonus | 200 points |

### Why It Matters
Loyalty programs increase repeat purchases. VIP tiers create aspiration. Referrals drive organic growth.

---

## 3. Analytics Tracking

**Database:** Migration 16 (`16_analytics_tracking.sql`)

### What It Does
Tracks page views, conversion funnels, traffic sources, platform performance, and try-on sessions. Powers the admin analytics dashboard.

### Database Tables

#### page_views
```sql
CREATE TABLE page_views (
    id BIGSERIAL PRIMARY KEY,
    page_url TEXT NOT NULL,
    session_id VARCHAR(100),
    customer_id UUID,
    referrer TEXT,
    user_agent TEXT,
    ip_address INET,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### funnel_events
```sql
CREATE TABLE funnel_events (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    session_id VARCHAR(100),
    customer_id UUID,
    product_id UUID,
    order_id UUID,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Event Types:**
| Event | Description |
|-------|-------------|
| `page_view` | Customer views a page |
| `product_view` | Customer views a product |
| `add_to_cart` | Customer adds to cart |
| `begin_checkout` | Customer starts checkout |
| `purchase` | Customer completes purchase |

#### traffic_sources
```sql
CREATE TABLE traffic_sources (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(100),
    medium VARCHAR(50),
    campaign VARCHAR(100),
    session_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### platform_daily_stats
```sql
CREATE TABLE platform_daily_stats (
    id BIGSERIAL PRIMARY KEY,
    stat_date DATE NOT NULL DEFAULT CURRENT_DATE,
    page_views INTEGER DEFAULT 0,
    unique_visitors INTEGER DEFAULT 0,
    sessions INTEGER DEFAULT 0,
    orders INTEGER DEFAULT 0,
    revenue NUMERIC(12,2) DEFAULT 0,
    conversion_rate NUMERIC(5,2) DEFAULT 0,
    UNIQUE(stat_date)
);
```

#### tryon_sessions
```sql
CREATE TABLE tryon_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID,
    session_id VARCHAR(100),
    product_id UUID,
    duration_seconds INTEGER,
    completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Why It Matters
You can't improve what you don't measure. Analytics show what's working and what isn't.

---

## Summary

| System | File | Key Feature |
|--------|------|-------------|
| Social Commerce | Migration 18 | Feed, likes, comments, influencers, follows, outfit boards |
| Loyalty & VIP | Migration 19 | Points, 5 VIP tiers, referrals, 5 rewards |
| Analytics | Migration 16 | Page views, funnels, traffic sources, daily stats |

**Total: 3 database schemas with 17 tables**
