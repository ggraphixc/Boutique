# app/fashion_ai.py
# AI Fashion Assistant — Recommendation Engine, Style Advisor, Wardrobe Manager
# Supports OpenRouter (free models), OpenAI, Anthropic, and rule-based fallback.
# AI provider config is read from store_settings in the database.

import os
import json
import logging
import re
from typing import Optional
from datetime import datetime

logger = logging.getLogger("asiko.fashion_ai")

# ---------------------------------------------------------------------------
# LLM Configuration — reads from DB at call time, env vars as fallback
# ---------------------------------------------------------------------------
_env_openai_key = os.environ.get("OPENAI_API_KEY", "")
_env_anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")

# OpenRouter free models
OPENROUTER_MODELS = {
    "google/gemini-2.0-flash-001": "Gemini 2.0 Flash (free)",
    "meta-llama/llama-3.3-70b-instruct:free": "Llama 3.3 70B (free)",
    "mistralai/mistral-small-3.1-24b-instruct:free": "Mistral Small 3.1 (free)",
    "qwen/qwen3-235b-a22b:free": "Qwen3 235B (free)",
}


def _get_provider_config(db_pool=None, settings: dict = None) -> dict:
    """Resolve AI provider configuration from DB settings, env fallback."""
    if settings:
        provider = settings.get("ai_provider", "openrouter")
        api_key = settings.get("ai_api_key", "")
        model = settings.get("ai_model", "google/gemini-2.0-flash-001")
        system_prompt_override = settings.get("ai_system_prompt", "")
        max_tokens = settings.get("ai_max_tokens", 1024)
        temperature = float(settings.get("ai_temperature", 0.7))
    else:
        provider = "openai" if _env_openai_key else ("anthropic" if _env_anthropic_key else "none")
        api_key = _env_openai_key or _env_anthropic_key
        model = "gpt-4o-mini" if provider == "openai" else "claude-3-5-haiku-20241022"
        system_prompt_override = ""
        max_tokens = 1024
        temperature = 0.7

    # Auto-detect from env if DB has no key
    if provider not in ("openai", "anthropic") and _env_openai_key:
        provider = "openai"
        api_key = _env_openai_key
        model = "gpt-4o-mini"
    elif provider not in ("openai", "anthropic") and _env_anthropic_key:
        provider = "anthropic"
        api_key = _env_anthropic_key
        model = "claude-3-5-haiku-20241022"

    if not api_key:
        provider = "none"

    return {
        "provider": provider,
        "api_key": api_key,
        "model": model,
        "system_prompt_override": system_prompt_override,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }


async def _call_llm(system_prompt: str, user_message: str, max_tokens: int = 800,
                     settings: dict = None) -> Optional[str]:
    """Call LLM if available, return None if no provider configured."""
    cfg = _get_provider_config(settings=settings)
    provider = cfg["provider"]
    api_key = cfg["api_key"]
    model = cfg["model"]
    temperature = cfg["temperature"]

    if provider == "none":
        return None

    try:
        import httpx

        if provider == "openrouter":
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
                data = resp.json()
                if "choices" in data and data["choices"]:
                    return data["choices"][0]["message"]["content"]
                logger.warning("OpenRouter response: %s", json.dumps(data)[:200])
                return None

        elif provider == "openai":
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
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
                data = resp.json()
                return data["choices"][0]["message"]["content"]

        elif provider == "anthropic":
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                    },
                    json={
                        "model": model,
                        "max_tokens": max_tokens,
                        "system": system_prompt,
                        "messages": [{"role": "user", "content": user_message}],
                    },
                )
                data = resp.json()
                return data["content"][0]["text"]

    except Exception as e:
        logger.warning("LLM call failed (%s/%s): %s", provider, model, e)
        return None

    return None


# ---------------------------------------------------------------------------
# Product Recommendation Engine
# ---------------------------------------------------------------------------

# Category compatibility matrix — which categories pair well together
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

# Color harmony rules
COMPLEMENTARY_COLORS = {
    "red": ["green", "navy", "cream", "black"],
    "blue": ["orange", "coral", "cream", "white"],
    "green": ["red", "burgundy", "cream", "gold"],
    "yellow": ["purple", "navy", "grey", "black"],
    "pink": ["grey", "navy", "cream", "black"],
    "purple": ["yellow", "gold", "cream", "grey"],
    "orange": ["blue", "navy", "cream", "grey"],
    "coral": ["navy", "teal", "cream", "grey"],
    "burgundy": ["gold", "cream", "grey", "navy"],
    "navy": ["coral", "gold", "cream", "white"],
    "black": ["gold", "coral", "red", "white", "cream"],
    "white": ["black", "navy", "red", "blue"],
    "cream": ["navy", "burgundy", "forest green", "black"],
    "grey": ["pink", "coral", "yellow", "blue"],
    "gold": ["navy", "burgundy", "black", "cream"],
    "mustard": ["purple", 'navy', "burgundy", "grey"],
    "terracotta": ["navy", "teal", "cream", "olive"],
    "olive": ["coral", "gold", "cream", "burgundy"],
}

# Season-appropriate colors
SEASON_COLORS = {
    "harmattan": ["earth tones", "burgundy", "mustard", "olive", "cream", "brown", "terracotta", "gold"],
    "rainy": ["jewel tones", "navy", "forest green", "burgundy", "grey", "deep purple"],
    "dry": ["brights", "pastels", "white", "coral", "turquoise", "yellow", "pink"],
    "all": ["earth tones", "jewel tones", "pastels", "neutrals", "brights"],
}

# Occasion → recommended event slugs
OCCASION_KEYWORDS = {
    "wedding": "wedding-guest",
    "church": "church",
    "sunday": "church",
    "office": "office",
    "work": "office",
    "meeting": "business-meeting",
    "interview": "business-meeting",
    "party": "party",
    "night": "party",
    "club": "party",
    "date": "date-night",
    "dinner": "date-night",
    "casual": "casual",
    "everyday": "casual",
    "traditional": "traditional",
    "ceremony": "traditional",
    "native": "traditional",
}


def score_product_for_user(product: dict, preferences: dict, purchase_history: list, context: dict = None) -> float:
    """Score a product (0-100) for a specific user based on preferences and context."""
    score = 50.0  # base score
    context = context or {}

    # --- Preference matching ---
    style_profiles = preferences.get("style_profiles", [])
    occasions = preferences.get("occasions", [])
    fav_colors = preferences.get("favorite_colors", [])
    budget_min = preferences.get("budget_min", 0)
    budget_max = preferences.get("budget_max", 100000)
    preferred_fit = preferences.get("preferred_fit", "regular")
    skin_tone = preferences.get("skin_tone")
    season = context.get("season", "all")

    price = float(product.get("price", 0))

    # Budget fit (+/- 15)
    if budget_min <= price <= budget_max:
        score += 15
    elif price < budget_min:
        score += 5
    else:
        score -= 10

    # Category relevance for occasion (+/- 20)
    occasion_slug = context.get("occasion_slug")
    if occasion_slug:
        event_recommended = context.get("event_recommended_categories", [])
        product_cat = product.get("category_name", "").lower()
        if product_cat in event_recommended:
            score += 20
        else:
            score -= 5

    # Color harmony (+/- 15)
    product_color = (product.get("color", "") or "").lower()
    if fav_colors and product_color:
        for fc in fav_colors:
            if fc.lower() in product_color or product_color in fc.lower():
                score += 15
                break
    if product_color and product_color in COMPLEMENTARY_COLORS:
        harmony_colors = COMPLEMENTARY_COLORS[product_color]
        if any(fc.lower() in harmony_colors for fc in fav_colors):
            score += 10

    # Season match (+/- 10)
    if season != "all":
        season_colors = SEASON_COLORS.get(season, [])
        if product_color and any(sc in product_color for sc in season_colors):
            score += 10

    # Stock availability
    stock = product.get("stock_quantity", 0)
    if stock <= 0:
        score -= 30
    elif stock <= 3:
        score -= 5

    # Purchase history — avoid repurchasing same category recently
    if purchase_history:
        recent_cats = [p.get("category_name", "") for p in purchase_history[:5]]
        product_cat = product.get("category_name", "").lower()
        if product_cat in [c.lower() for c in recent_cats]:
            score -= 10

    # Description quality (longer = more detail = likely better product)
    desc = product.get("description", "") or ""
    if len(desc) > 100:
        score += 3

    return max(0, min(100, score))


async def get_recommendations(
    db_pool,
    session_id: str = None,
    customer_id: str = None,
    occasion: str = None,
    limit: int = 8,
    exclude_ids: list = None,
) -> list:
    """Get personalized product recommendations."""
    exclude_ids = exclude_ids or []

    # Fetch user preferences
    preferences = {}
    if customer_id:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM user_preferences WHERE customer_id = $1 ORDER BY updated_at DESC LIMIT 1",
                customer_id,
            )
            if row:
                preferences = dict(row)
    elif session_id:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM user_preferences WHERE session_id = $1 ORDER BY updated_at DESC LIMIT 1",
                session_id,
            )
            if row:
                preferences = dict(row)

    # Fetch purchase history
    purchase_history = []
    if customer_id:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT p.name, p.category_id, c.name as category_name, p.price
                   FROM order_items oi
                   JOIN orders o ON oi.order_id = o.id
                   JOIN products p ON oi.product_id = p.id
                   LEFT JOIN categories c ON p.category_id = c.id
                   WHERE o.customer_id = $1
                   ORDER BY o.created_at DESC LIMIT 10""",
                customer_id,
            )
            purchase_history = [dict(r) for r in rows]

    # Fetch event context
    event_context = {}
    if occasion:
        slug = OCCASION_KEYWORDS.get(occasion.lower(), occasion.lower())
        async with db_pool.acquire() as conn:
            event_row = await conn.fetchrow(
                "SELECT * FROM style_events WHERE slug = $1 AND is_active = TRUE", slug
            )
            if event_row:
                event_context = dict(event_row)

    # Fetch all products
    async with db_pool.acquire() as conn:
        product_rows = await conn.fetch(
            """SELECT p.*, c.name as category_name
               FROM products p
               LEFT JOIN categories c ON p.category_id = c.id
               WHERE p.stock_quantity > 0
               ORDER BY p.created_at DESC"""
        )
        products = [dict(r) for r in product_rows]

    # Score and rank
    scored = []
    for p in products:
        if p["id"] in exclude_ids:
            continue
        s = score_product_for_user(p, preferences, purchase_history, {
            "season": preferences.get("season_preference", "all"),
            "occasion_slug": event_context.get("slug"),
            "event_recommended_categories": event_context.get("recommended_categories", []),
        })
        scored.append((s, p))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"score": round(s, 1), **p} for s, p in scored[:limit]]


# ---------------------------------------------------------------------------
# Style Assistant Chat
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are ASIKO's AI Fashion Stylist — a warm, knowledgeable personal stylist for Nigerian fashion.
You help customers find the perfect outfit, suggest combinations, and answer style questions.

Rules:
- Be warm, friendly, and fashion-savvy. Use Nigerian fashion context.
- Reference specific products when available (name, price in Naira).
- Give practical, actionable advice.
- Consider Nigerian weather (harmattan, rainy, dry seasons).
- Mention Nigerian fashion elements (Ankara, Aso-Oke, Adire) when relevant.
- Keep responses concise (2-4 sentences max unless asked for detail).
- Use ₦ for prices, never $.
- If asked about something outside fashion, gently redirect to style topics."""


async def _build_brand_aware_prompt(db_pool, settings: dict = None) -> str:
    """Build a dynamic system prompt that includes brand knowledge, products, and training data."""
    parts = [SYSTEM_PROMPT]

    # 1. Brand info from settings
    if settings:
        brand_name = settings.get("store_name", "ASIKO Boutique")
        brand_desc = settings.get("store_description", "")
        if brand_desc:
            parts.append(f"\n## About {brand_name}\n{brand_desc}")

    # 2. Fetch training data from DB
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT category, question, answer FROM ai_training_data WHERE is_active = TRUE ORDER BY category, sort_order"
            )
            if rows:
                by_cat = {}
                for r in rows:
                    cat = r["category"]
                    if cat not in by_cat:
                        by_cat[cat] = []
                    by_cat[cat].append(f"Q: {r['question']}\nA: {r['answer']}")

                if "brand" in by_cat:
                    parts.append("\n## Brand Knowledge\n" + "\n---\n".join(by_cat["brand"]))
                if "faq" in by_cat:
                    parts.append("\n## FAQ — Common Customer Questions\n" + "\n---\n".join(by_cat["faq"]))
                if "product" in by_cat:
                    parts.append("\n## Product Knowledge\n" + "\n---\n".join(by_cat["product"]))
                if "style" in by_cat:
                    parts.append("\n## Style Rules & Nigerian Fashion Expertise\n" + "\n---\n".join(by_cat["style"]))
                if "voice" in by_cat:
                    parts.append("\n## Brand Voice Guidelines\n" + "\n---\n".join(by_cat["voice"]))
                if "custom" in by_cat:
                    parts.append("\n## Additional Context\n" + "\n---\n".join(by_cat["custom"]))
    except Exception as e:
        logger.warning("Failed to load training data for prompt: %s", e)

    # 3. Fetch current products from DB (abbreviated catalog)
    try:
        async with db_pool.acquire() as conn:
            product_rows = await conn.fetch(
                """SELECT p.name, p.price, p.description, p.color, p.fabric,
                          c.name as category_name
                   FROM products p
                   LEFT JOIN categories c ON p.category_id = c.id
                   WHERE p.stock_quantity > 0
                   ORDER BY p.created_at DESC
                   LIMIT 30"""
            )
            if product_rows:
                catalog_lines = []
                for p in product_rows:
                    desc = (p["description"] or "")[:80]
                    line = f"- {p['name']} — ₦{float(p['price']):,.0f} [{p.get('category_name', '')}]"
                    if p.get("color"):
                        line += f" color={p['color']}"
                    if desc:
                        line += f" — {desc}"
                    catalog_lines.append(line)
                parts.append("\n## Current Product Catalog (in stock)\n" + "\n".join(catalog_lines))
    except Exception as e:
        logger.warning("Failed to load products for prompt: %s", e)

    # 4. Use admin override if provided (highest priority)
    if settings:
        cfg = _get_provider_config(settings=settings)
        if cfg.get("system_prompt_override"):
            # Append admin override as extra context, not replace
            parts.append(f"\n## Admin Instructions\n{cfg['system_prompt_override']}")

    return "\n".join(parts)

# Keyword patterns for intent detection
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
    "match": r"(match|搭配|pair|combine|go with|coordinate|搭配|搭配)",
    "trend": r"(trend|trending|fashion|style|what.s popular|what.s hot|latest)",
    "wardrobe": r"(wardrobe|closet|own|have|already own|matching my)",
    "budget": r"(budget|cheap|affordable|under|price|cost|how much|expensive)",
    "season": r"(harmattan|rainy|dry|cold|hot|weather|season|warm|cool)",
}


def detect_intent(message: str) -> dict:
    """Detect user intent from message."""
    lower = message.lower() if message else ""
    intents = []
    occasion = None

    for intent, pattern in INTENT_PATTERNS.items():
        if re.search(pattern, lower):
            intents.append(intent)

    # Map occasion intents to event slugs
    for intent in intents:
        if intent in OCCASION_KEYWORDS:
            occasion = OCCASION_KEYWORDS[intent]
            break

    return {
        "intents": intents,
        "occasion": occasion,
        "is_color_question": "color" in intents or "match" in intents,
        "is_trend_question": "trend" in intents,
        "is_wardrobe_question": "wardrobe" in intents,
        "is_budget_question": "budget" in intents,
    }


def build_rule_response(message: str, products: list, event: dict = None) -> str:
    """Generate a rule-based response when no LLM is available."""
    lower = message.lower()
    intent = detect_intent(message)

    # Budget question
    if intent["is_budget_question"]:
        prices = [float(p.get("price", 0)) for p in products if p.get("price")]
        if prices:
            avg = sum(prices) / len(prices)
            low = min(prices)
            high = max(prices)
            return (
                f"We have beautiful pieces ranging from ₦{low:,.0f} to ₦{high:,.0f}. "
                f"On average, our customers spend around ₦{avg:,.0f}. "
                f"Would you like me to filter by a specific budget?"
            )
        return "I can help you find something within your budget. What price range are you comfortable with?"

    # Wedding
    if "wedding" in intent["intents"]:
        return (
            "For a wedding guest look, I recommend a statement dress or a tailored agbada in jewel tones — "
            "emerald, burgundy, or royal blue work beautifully. Pair with gold accessories. "
            "Shall I show you some options?"
        )

    # Church
    if "church" in intent["intents"]:
        return (
            "For church, elegant and modest is the way to go. A lace dress in pastels or earth tones, "
            "or a well-tailored shirt with trousers. Our AnkarA pieces are also perfect for Sunday service."
        )

    # Office
    if "office" in intent["intents"]:
        return (
            "For the office, structured pieces in neutrals are always sharp — navy, grey, or cream. "
            "A blazer with tailored trousers or a midi skirt. Our satin blouses are customer favorites."
        )

    # Party
    if "party" in intent["intents"]:
        return (
            "For a party, go bold! Satin slip dresses, sequin tops, or a sleek all-black look with statement jewelry. "
            "Our customers love the coral and gold combo for celebrations."
        )

    # Traditional
    if "traditional" in intent["intents"]:
        return (
            "Nigerian traditional wear is always a showstopper! Ankara and Aso-Oke are trending right now. "
            "A modern agbada or a ankara co-ord set with gele — very fashionable. Want me to show you our traditional collection?"
        )

    # Casual
    if "casual" in intent["intents"]:
        return (
            "For casual outings, comfort meets style. Our cotton pieces, denim, and relaxed-fit trousers "
            "are perfect for everyday wear. Pair with sneakers or slides for a effortless look."
        )

    # Date
    if "date" in intent["intents"]:
        return (
            "For date night, think elegant but not overdone. A satin midi dress in burgundy or coral, "
            "or a fitted top with wide-leg trousers. Add delicate jewelry — less is more."
        )

    # Color
    if intent["is_color_question"]:
        return (
            "Great question! For warm skin tones, earth tones, gold, coral, and warm reds look amazing. "
            "For cool skin tones, jewel tones, navy, silver, and berry shades complement beautifully. "
            "What's your skin tone? I can give more specific advice."
        )

    # Trend
    if intent["is_trend_question"]:
        return (
            "Right now in Nigerian fashion, Ankara fusion and Aso-Oke modernization are huge! "
            "Earth tones, oversized blazers, and wide-leg trousers are also trending globally. "
            "Would you like to see our trending pieces?"
        )

    # Wardrobe
    if intent["is_wardrobe_question"]:
        return (
            "I can help you build outfits from your wardrobe! Upload photos of clothes you own, "
            "and I'll suggest combinations and identify missing pieces. Want to start building your wardrobe?"
        )

    # Season
    if "harmattan" in lower:
        return (
            "For harmattan, think warm layers! Earth tones, burgundy, and mustard work perfectly. "
            "Wool, velvet, and knit pieces keep you warm while looking stylish. "
            "A blazer or cardigan is essential."
        )
    if "rainy" in lower:
        return (
            "Rainy season calls for darker jewel tones — navy, forest green, burgundy. "
            "Light fabrics like chiffon and cotton are comfortable. "
            "Water-resistant shoes are a must!"
        )

    # Product recommendations
    if products:
        rec_text = "\n".join(
            f"- {p['name']} — ₦{float(p['price']):,.0f}" for p in products[:5]
        )
        return f"Here are some pieces I think you'd love:\n{rec_text}\n\nWould you like more details on any of these?"

    return (
        "I'm your personal ASIKO stylist! I can help you find the perfect outfit for any occasion. "
        "Tell me what you're looking for — a wedding outfit, office wear, casual pieces, or something else? "
        "I'm here to help!"
    )


async def style_assistant_chat(
    db_pool,
    message: str,
    session_id: str = None,
    customer_id: str = None,
    settings: dict = None,
) -> dict:
    """
    Process a style assistant message. Returns {response, products, intent, event}.
    Uses LLM if available, falls back to rule-based responses.
    """
    intent = detect_intent(message)

    # Fetch relevant products
    products = []
    async with db_pool.acquire() as conn:
        if intent["occasion"]:
            # Fetch products matching the event category
            event_row = await conn.fetchrow(
                "SELECT * FROM style_events WHERE slug = $1", intent["occasion"]
            )
            if event_row:
                rec_cats = event_row["recommended_categories"]
                product_rows = await conn.fetch(
                    """SELECT p.*, c.name as category_name
                       FROM products p
                       LEFT JOIN categories c ON p.category_id = c.id
                       WHERE c.name = ANY($1) AND p.stock_quantity > 0
                       ORDER BY RANDOM() LIMIT 6""",
                    rec_cats,
                )
                products = [dict(r) for r in product_rows]
        else:
            # General product fetch
            product_rows = await conn.fetch(
                """SELECT p.*, c.name as category_name
                   FROM products p
                   LEFT JOIN categories c ON p.category_id = c.id
                   WHERE p.stock_quantity > 0
                   ORDER BY RANDOM() LIMIT 6"""
            )
            products = [dict(r) for r in product_rows]

    # Build system prompt — use brand-aware dynamic prompt
    try:
        system_prompt = await _build_brand_aware_prompt(db_pool, settings)
    except Exception:
        system_prompt = SYSTEM_PROMPT
    if settings:
        cfg = _get_provider_config(settings=settings)
        max_tokens = cfg.get("max_tokens", 300)
        ai_settings = settings
    else:
        max_tokens = 300
        ai_settings = None

    # Try LLM response
    product_context = "\n".join(
        f"- {p['name']} (₦{float(p['price']):,.0f}, {p.get('category_name', 'N/A')})"
        for p in products[:6]
    )
    llm_prompt = f"Available products:\n{product_context}\n\nCustomer message: {message}"

    llm_response = await _call_llm(system_prompt, llm_prompt, max_tokens=max_tokens, settings=ai_settings)

    if llm_response:
        response_text = llm_response
    else:
        response_text = build_rule_response(message, products)

    # Save chat history
    if session_id or customer_id:
        try:
            async with db_pool.acquire() as conn:
                if customer_id:
                    await conn.execute(
                        "INSERT INTO fashion_chat_history (customer_id, role, message) VALUES ($1, 'user', $2)",
                        customer_id, message,
                    )
                    await conn.execute(
                        "INSERT INTO fashion_chat_history (customer_id, role, message) VALUES ($1, 'assistant', $2)",
                        customer_id, response_text,
                    )
                elif session_id:
                    await conn.execute(
                        "INSERT INTO fashion_chat_history (session_id, role, message) VALUES ($1, 'user', $2)",
                        session_id, message,
                    )
                    await conn.execute(
                        "INSERT INTO fashion_chat_history (session_id, role, message) VALUES ($1, 'assistant', $2)",
                        session_id, response_text,
                    )
        except Exception as e:
            logger.warning(f"Failed to save chat history: {e}")

    return {
        "response": response_text,
        "products": products[:6],
        "intent": intent,
    }


# ---------------------------------------------------------------------------
# Wardrobe Manager
# ---------------------------------------------------------------------------

async def analyze_wardrobe(db_pool, session_id: str = None, customer_id: str = None) -> dict:
    """Analyze user's wardrobe and suggest improvements."""
    where_clause = "customer_id = $1" if customer_id else "session_id = $1"
    param = customer_id or session_id

    async with db_pool.acquire() as conn:
        items = await conn.fetch(
            f"SELECT * FROM wardrobe_items WHERE {where_clause} AND is_active = TRUE ORDER BY created_at DESC",
            param,
        )

    wardrobe = [dict(i) for i in items]

    if not wardrobe:
        return {
            "total_items": 0,
            "message": "Your wardrobe is empty! Start by adding pieces you own.",
            "categories": {},
            "missing_pieces": [],
            "combinations": [],
        }

    # Analyze categories
    categories = {}
    colors = {}
    occasions = set()
    for item in wardrobe:
        cat = item.get("category", "other")
        categories[cat] = categories.get(cat, 0) + 1
        color = item.get("color_primary", "")
        if color:
            colors[color] = colors.get(color, 0) + 1
        for occ in item.get("occasions", []):
            occasions.add(occ)

    # Identify missing pieces
    missing = []
    has = set(categories.keys())
    essentials = {
        "shirt": "A good shirt is versatile — pairs with trousers, skirts, and under jackets",
        "trouser": "Every wardrobe needs reliable trousers — formal and casual options",
        "dress": "A dress is a complete outfit — perfect for events and easy to style",
        "shoe": "The right shoes complete any look — a neutral pair is essential",
        "jacket": "A jacket adds structure — perfect for layering and formal occasions",
        "bag": "A good bag ties an outfit together — go for a neutral color",
    }
    for cat, reason in essentials.items():
        if cat not in has:
            missing.append({"category": cat, "reason": reason})

    # Suggest combinations (rule-based)
    combinations = []
    shirts = [i for i in wardrobe if i["category"] in ("shirt", "hoodie")]
    bottoms = [i for i in wardrobe if i["category"] in ("trouser", "skirt")]
    for s in shirts[:3]:
        for b in bottoms[:3]:
            s_color = (s.get("color_primary") or "").lower()
            b_color = (b.get("color_primary") or "").lower()
            if s_color in COMPLEMENTARY_COLORS and b_color in COMPLEMENTARY_COLORS.get(s_color, []):
                combinations.append({
                    "top": s["name"],
                    "bottom": b["name"],
                    "reason": f"{s_color} and {b_color} are complementary colors",
                })

    return {
        "total_items": len(wardrobe),
        "categories": categories,
        "colors": colors,
        "occasions": list(occasions),
        "missing_pieces": missing[:5],
        "combinations": combinations[:5],
    }


async def suggest_outfit_from_wardrobe(
    db_pool,
    occasion: str,
    session_id: str = None,
    customer_id: str = None,
) -> dict:
    """Suggest an outfit combination from the user's wardrobe for a specific occasion."""
    where_clause = "customer_id = $1" if customer_id else "session_id = $1"
    param = customer_id or session_id

    async with db_pool.acquire() as conn:
        items = await conn.fetch(
            f"SELECT * FROM wardrobe_items WHERE {where_clause} AND is_active = TRUE",
            param,
        )

    wardrobe = [dict(i) for i in items]

    # Get event rules
    slug = OCCASION_KEYWORDS.get(occasion.lower(), occasion.lower())
    async with db_pool.acquire() as conn:
        event = await conn.fetchrow(
            "SELECT * FROM style_events WHERE slug = $1", slug
        )

    event_dict = dict(event) if event else {}
    recommended_cats = event_dict.get("recommended_categories", [])
    rec_fabrics = event_dict.get("recommended_fabrics", [])
    rec_colors = event_dict.get("recommended_colors", [])

    # Score each wardrobe item
    scored = []
    for item in wardrobe:
        score = 50
        cat = item.get("category", "")
        if cat in recommended_cats:
            score += 25
        if item.get("fabric", "") in rec_fabrics:
            score += 15
        color = (item.get("color_primary") or "").lower()
        if any(rc.lower() in color or color in rc.lower() for rc in rec_colors):
            score += 15
        if occasion.lower() in [o.lower() for o in item.get("occasions", [])]:
            score += 10
        scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Build outfit from top scorers across categories
    outfit = []
    used_cats = set()
    for score, item in scored:
        cat = item["category"]
        if cat not in used_cats and len(outfit) < 5:
            outfit.append({"score": score, **item})
            used_cats.add(cat)

    return {
        "occasion": event_dict.get("name", occasion),
        "outfit": outfit,
        "total_items_available": len(wardrobe),
    }


# ---------------------------------------------------------------------------
# Event Styling
# ---------------------------------------------------------------------------

async def get_event_styling(db_pool, event_slug: str) -> dict:
    """Get styling advice for a specific event."""
    async with db_pool.acquire() as conn:
        event = await conn.fetchrow(
            "SELECT * FROM style_events WHERE slug = $1 AND is_active = TRUE", event_slug
        )

    if not event:
        return {"error": "Event not found"}

    event_dict = dict(event)

    # Fetch matching products
    async with db_pool.acquire() as conn:
        products = await conn.fetch(
            """SELECT p.*, c.name as category_name
               FROM products p
               LEFT JOIN categories c ON p.category_id = c.id
               WHERE c.name = ANY($1) AND p.stock_quantity > 0
               ORDER BY RANDOM() LIMIT 8""",
            event_dict["recommended_categories"],
        )

    event_dict["products"] = [dict(p) for p in products]
    return event_dict


async def list_events(db_pool) -> list:
    """List all available style events."""
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM style_events WHERE is_active = TRUE ORDER BY name"
        )
    return [dict(r) for r in rows]
