# C. AI SYSTEMS

## Overview

ASIKO Boutique features 4 AI-powered systems: a multi-provider LLM fashion assistant, a color analysis engine, an admin-managed training data system, and a 12-endpoint API for the AI Stylist chatroom.

---

## 1. Fashion AI Engine

**File:** `app/fashion_ai.py` (920 lines)

### What It Does
The core AI fashion assistant powering the `/stylist` chatroom. Provides product recommendations, style chat, wardrobe management, and event styling. Supports multiple LLM providers with a rule-based fallback.

### Multi-Provider LLM Backend

#### Provider Configuration
```python
def _get_provider_config(db_pool, settings) -> dict:
    # Priority: DB settings > env vars > fallback
    return {
        "provider": "openrouter",      # openrouter | openai | anthropic | none
        "api_key": "...",
        "model": "google/gemini-2.0-flash-001",
        "system_prompt_override": "",
        "max_tokens": 1024,
        "temperature": 0.7,
    }
```

#### Supported Providers

| Provider | Models | Cost | Free Tier |
|----------|--------|------|-----------|
| **OpenRouter** (default) | Gemini 2.0 Flash, Llama 3.3 70B, Mistral Small, Qwen3 235B | Free | Yes |
| OpenAI | GPT-4o-mini | Pay-per-token | No |
| Anthropic | Claude 3.5 Haiku | Pay-per-token | No |
| None | Rule-based responses | Free | N/A |

**OpenRouter Free Models:**
```python
OPENROUTER_MODELS = {
    "google/gemini-2.0-flash-001": "Gemini 2.0 Flash (free)",
    "meta-llama/llama-3.3-70b-instruct:free": "Llama 3.3 70B (free)",
    "mistralai/mistral-small-3.1-24b-instruct:free": "Mistral Small 3.1 (free)",
    "qwen/qwen3-235b-a22b:free": "Qwen3 235B (free)",
}
```

#### LLM Call Function
```python
async def _call_llm(system_prompt, user_message, max_tokens=800, settings=None):
    # 1. Get provider config
    # 2. Build messages array [system, user]
    # 3. POST to provider API
    # 4. Return response text or None
```

**OpenRouter request:**
```python
async with httpx.AsyncClient(timeout=60) as client:
    resp = await client.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://asikoboutique.com",
            "X-Title": "ASIKO Fashion Stylist",
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        },
    )
```

### Brand-Aware System Prompt

```python
async def _build_brand_aware_prompt(db_pool, settings) -> str:
    parts = [SYSTEM_PROMPT]
    
    # 1. Brand info from settings
    parts.append(f"\n## About {brand_name}\n{brand_desc}")
    
    # 2. Training data from ai_training_data table
    # Categories: brand, faq, product, style, voice, custom
    
    # 3. Current product catalog (top 30 in-stock items)
    # Includes: name, price, category, color, description
    
    # 4. Admin override instructions (highest priority)
    
    return "\n".join(parts)
```

**The AI Stylist knows:**
- ASIKO brand story and values
- Every product in the catalog with prices
- Nigerian fashion expertise (Ankara, Aso-Oke, Adire)
- Color harmony and seasonal recommendations
- Occasion-specific styling rules

### Intent Detection

```python
INTENT_PATTERNS = {
    "recommend": r"(recommend|suggest|show me|find me|what should i|help me pick|looking for)",
    "wedding": r"(wedding|nikkah|engagement|traditional marriage|white wedding)",
    "church": r"(church|sunday service|worship|mass)",
    "office": r"(office|work|business|professional|corporate|meeting|interview|presentation)",
    "party": r"(party|club|night out|celebration|birthday|concert|fashion)",
    "casual": r"(casual|everyday|chill|hangout|market|errand|comfort)",
    "traditional": r"(traditional|aso.oke|ankara|adire|native|agbada|gele|iro|buba)",
    "date": r"(date|dinner|romantic|anniversary|valentine)",
    "color": r"(color|colour|skin tone|complexion|match|complement|what goes with)",
    "match": r"(match|pair|combine|go with|coordinate)",
    "trend": r"(trend|trending|fashion|style|what.s popular|what.s hot|latest)",
    "wardrobe": r"(wardrobe|closet|own|have|already own|matching my)",
    "budget": r"(budget|cheap|affordable|under|price|cost|how much|expensive)",
    "season": r"(harmattan|rainy|dry|cold|hot|weather|season|warm|cool)",
}
```

### Product Recommendation Engine

**Scoring (0-100):**
```python
def score_product_for_user(product, preferences, purchase_history, context):
    score = 50.0  # base
    
    # Budget fit (+/-15)
    if budget_min <= price <= budget_max: score += 15
    
    # Category relevance for occasion (+/-20)
    if product_cat in event_recommended: score += 20
    
    # Color harmony (+/-15)
    if product_color matches favorite: score += 15
    
    # Season match (+/-10)
    if color in season_colors: score += 10
    
    # Stock availability
    if stock <= 0: score -= 30
    elif stock <= 3: score -= 5
    
    # Purchase history diversity
    if same_category_recent: score -= 10
    
    return max(0, min(100, score))
```

**Category Compatibility Matrix:**
```python
CATEGORY_PAIRS = {
    "dress": ["shoe", "bag", "accessory"],
    "shirt": ["trouser", "skirt", "shoe", "bag", "jacket"],
    "trouser": ["shirt", "hoodie", "jacket", "shoe", "bag"],
    "skirt": ["shirt", "blouse", "jacket", "shoe", "bag"],
    "jacket": ["shirt", "trouser", "skirt", "dress"],
    "hoodie": ["trouser", "skirt", "shoe"],
    "shoe": ["dress", "shirt", "trouser", "skirt", "bag"],
    "bag": ["dress", "shirt", "trouser", "skirt"],
}
```

**Color Harmony Rules (18 colors):**
```python
COMPLEMENTARY_COLORS = {
    "red": ["green", "navy", "cream", "black"],
    "blue": ["orange", "coral", "cream", "white"],
    "navy": ["coral", "gold", "cream", "white"],
    "black": ["gold", "coral", "red", "white", "cream"],
    # ... 18 total color mappings
}
```

**Seasonal Palettes:**
```python
SEASON_COLORS = {
    "harmattan": ["earth tones", "burgundy", "mustard", "olive", "cream", "terracotta", "gold"],
    "rainy": ["jewel tones", "navy", "forest green", "burgundy", "grey", "deep purple"],
    "dry": ["brights", "pastels", "white", "coral", "turquoise", "yellow", "pink"],
}
```

### Style Assistant Chat

```python
async def style_assistant_chat(db_pool, message, session_id, customer_id, settings):
    # 1. Detect intent from message
    # 2. Fetch relevant products (occasion-matched or random)
    # 3. Build brand-aware system prompt
    # 4. Try LLM response (OpenRouter/OpenAI/Anthropic)
    # 5. If LLM fails, use rule-based fallback
    # 6. Save chat history to DB
    # 7. Return response + products + intent
```

### Rule-Based Fallback

When no LLM is configured, the system generates responses based on detected intent:

| Intent | Response |
|--------|----------|
| Wedding | "For a wedding guest look, I recommend a statement dress in jewel tones..." |
| Church | "For church, elegant and modest is the way to go..." |
| Office | "For the office, structured pieces in neutrals are always sharp..." |
| Party | "For a party, go bold! Satin slip dresses, sequin tops..." |
| Traditional | "Nigerian traditional wear is always a showstopper! Ankara and Aso-Oke..." |
| Casual | "For casual outings, comfort meets style..." |
| Date | "For date night, think elegant but not overdone..." |
| Color | "For warm skin tones, earth tones, gold, coral..." |
| Trend | "Right now in Nigerian fashion, Ankara fusion and Aso-Oke modernization..." |
| Budget | "We have beautiful pieces ranging from ₦X to ₦Y..." |

### Why It Matters
This is ASIKO's differentiator. A fashion boutique with an AI stylist that knows every product and Nigerian fashion context.

---

## 2. Color Analysis Engine

**File:** `app/color_analysis.py`

### What It Does
Comprehensive color theory engine for skin tone detection, seasonal color analysis, and outfit color matching. Used by the AI Stylist to give personalized color advice.

### Skin Tone Detection

**6 Tone Categories:**
| Tone | RGB Range | Undertone |
|------|-----------|-----------|
| Fair | R:220-255, G:190-230, B:170-210 | Cool |
| Light | R:200-240, G:170-210, B:150-190 | Warm |
| Medium | R:170-220, G:140-190, B:120-170 | Warm |
| Olive | R:150-200, G:140-180, B:100-150 | Neutral |
| Dark | R:100-160, G:70-130, B:50-110 | Warm |
| Deep | R:60-120, G:40-90, B:30-80 | Cool |

**Undertone Detection:**
```python
def detect_undertone(r, g, b):
    # Warm: red/yellow dominance
    # Cool: blue/pink dominance
    # Neutral: balanced
```

### Seasonal Color Analysis

| Season | Best Colors | Avoid Colors | Metals |
|--------|-------------|--------------|--------|
| Spring | Coral, peach, warm green, gold | Cool pastels, black | Gold |
| Summer | Pastels, lavender, dusty rose | Neon, orange | Silver |
| Autumn | Earth tones, rust, olive, burgundy | Bright pink, ice blue | Gold |
| Winter | Jewel tones, black, white, red | Earth tones, pastels | Silver |

### Color Harmony

**Complementary:** Colors opposite on the color wheel (e.g., blue + orange)
**Analogous:** Colors next to each other (e.g., blue + green + teal)
**Triadic:** Three equally spaced (e.g., red + yellow + blue)

### Image Analysis (PIL)

```python
def extract_dominant_colors(image_path, num_colors=5):
    """Quantize image and count pixel colors."""
    # Opens image with PIL
    # Resizes for performance
    # Quantizes to N colors
    # Returns top N dominant colors

def analyze_skin_from_photo(image_path):
    """Sample center face region for skin tone detection."""
    # Crops center 40% of image (face region)
    # Averages pixel colors
    # Maps to skin tone category
```

### Outfit Analysis

```python
def analyze_outfit_colors(colors: list[str]) -> dict:
    """Score outfit color combination."""
    # Returns:
    # {
    #   "score": 0-100,
    #   "harmony": "complementary" | "analogous" | "triadic" | "clashing",
    #   "suggestions": ["..."]
    # }
```

### Why It Matters
Color is the #1 factor in fashion decisions. This engine gives data-driven color advice instead of generic suggestions.

---

## 3. AI Training Data System

**Database:** Migration 21 (`21_ai_training_data.sql`)

### What It Does
Admin-managed knowledge base that feeds the AI Stylist's system prompt. Allows the boutique owner to teach the AI about their brand, products, and expertise — no coding required.

### Database Table
```sql
CREATE TABLE ai_training_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR(50) NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 6 Knowledge Categories

| Category | Purpose | Example |
|----------|---------|---------|
| `brand` | Brand story, values, mission | "What is ASIKO?" → "ASIKO is a luxury Nigerian fashion brand..." |
| `faq` | Common customer questions | "Do you ship internationally?" → "Yes, we ship to..." |
| `product` | Product-specific knowledge | "What fabric is the Lagos Silk Blazer?" → "100% mulberry silk..." |
| `style` | Nigerian fashion expertise | "How do I tie a gele?" → "Start with..." |
| `voice` | Brand voice guidelines | "How should the AI respond?" → "Warm, friendly, fashion-savvy..." |
| `custom` | Additional context | Any other knowledge the owner wants to add |

### How It's Used

```python
# In _build_brand_aware_prompt():
rows = await conn.fetch(
    "SELECT category, question, answer FROM ai_training_data "
    "WHERE is_active = TRUE ORDER BY category, sort_order"
)

# Organized into system prompt sections:
# ## Brand Knowledge
# Q: What is ASIKO?
# A: ASIKO is...
#
# ## FAQ — Common Customer Questions
# Q: Do you ship internationally?
# A: Yes...
#
# ## Product Knowledge
# Q: What fabric is the Lagos Silk Blazer?
# A: 100% mulberry silk...
```

### Admin CRUD

Managed from `/admin/sections/ai-stylist`:
- Add new Q&A pairs
- Edit existing answers
- Toggle active/inactive
- Reorder by sort order
- Delete entries

### Why It Matters
Without this, the AI gives generic fashion advice. With it, the AI knows ASIKO's specific products, brand voice, and Nigerian fashion expertise.

---

## 4. AI Stylist API

**File:** `app/routes/fashion_chat.py`

### What It Does
Complete JSON API powering the AI Stylist chatroom. 12 endpoints covering chat, recommendations, events, color analysis, and user preferences.

### Endpoints

#### Chat
```http
POST /api/fashion/chat
Body: {"message": "What should I wear to a wedding?"}
Response: {
    "response": "For a wedding guest look...",
    "products": [...],
    "intent": {"intents": ["wedding"], "occasion": "wedding-guest"}
}
```

#### Recommendations
```http
GET /api/fashion/recommendations?occasion=wedding&limit=8
Response: {
    "recommendations": [
        {"score": 85.0, "name": "Emerald Lace Dress", "price": 120000, ...},
        ...
    ]
}
```

#### Style Events
```http
GET /api/fashion/events
Response: {
    "events": [
        {"slug": "wedding-guest", "name": "Wedding Guest", "recommended_categories": ["dress", "shoe", "bag"]},
        ...
    ]
}

GET /api/fashion/events/{slug}
Response: {
    "event": {...},
    "products": [...]
}
```

#### Color Analysis
```http
POST /api/fashion/color/analyze-photo    # Upload photo for skin tone
GET  /api/fashion/color/recommendations?tone=warm&undertone=golden
POST /api/fashion/color/outfit            # Analyze outfit colors
POST /api/fashion/color/complement        # Get complementary colors
POST /api/fashion/color/extract           # Extract dominant color from image
```

#### User Preferences
```http
POST /api/fashion/preferences
Body: {"favorite_colors": ["navy", "gold"], "occasions": ["wedding", "church"]}

GET /api/fashion/preferences
Response: {"favorite_colors": ["navy", "gold"], "occasions": ["wedding", "church"]}
```

#### Chat History
```http
GET /api/fashion/chat/history?limit=20
Response: {
    "history": [
        {"role": "user", "message": "What should I wear?"},
        {"role": "assistant", "message": "For a wedding guest look..."},
        ...
    ]
}
```

### Why It Matters
This is the backend that powers the entire AI Stylist experience. Every chat message, recommendation, and color analysis flows through these endpoints.

---

## Summary

| System | File | Lines | Key Feature |
|--------|------|-------|-------------|
| Fashion AI Engine | `app/fashion_ai.py` | 920 | Multi-LLM, 14 intents, product scoring |
| Color Analysis | `app/color_analysis.py` | ~400 | Skin tone, seasonal palettes, image analysis |
| AI Training Data | Migration 21 | — | 6-category admin-managed knowledge base |
| AI Stylist API | `app/routes/fashion_chat.py` | ~300 | 12 API endpoints |

**Total: ~1,620 lines of code + database schema**
