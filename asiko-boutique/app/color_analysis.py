# app/color_analysis.py
# Color Analysis Engine — skin tone detection, color harmony, outfit matching
# Uses PIL for image analysis and rule-based color theory.

from typing import Optional
import logging

logger = logging.getLogger("asiko.color_analysis")

# ---------------------------------------------------------------------------
# Color Theory Constants
# ---------------------------------------------------------------------------

# Skin tone categories with RGB reference ranges
SKIN_TONE_RANGES = {
    "fair": {"r": (220, 255), "g": (200, 235), "b": (180, 215)},
    "light": {"r": (200, 235), "g": (170, 210), "b": (140, 180)},
    "medium": {"r": (170, 210), "g": (130, 170), "b": (90, 140)},
    "olive": {"r": (140, 180), "g": (110, 150), "b": (70, 120)},
    "dark": {"r": (100, 150), "g": (70, 110), "b": (40, 80)},
    "deep": {"r": (60, 110), "g": (40, 80), "b": (20, 55)},
}

# Undertone detection from color channels
UNDERTONE_RULES = {
    "warm": "red_channel_dominant",    # R > G > B with R significantly higher
    "cool": "blue_channel_dominant",   # B close to or exceeding R, green lower
    "neutral": "balanced",             # Channels relatively close
}

# Seasonal color palette mapping
SEASONAL_PALETTES = {
    "spring": {
        "skin_tones": ["fair", "light"],
        "undertone": "warm",
        "best_colors": ["coral", "peach", "warm red", "golden yellow", "turquoise", "warm green", "cream", "ivory", "camel"],
        "avoid_colors": ["black", "dark navy", "icy pink", "silver", "cool grey"],
        "best_neutrals": ["camel", "warm grey", "cream", "brown"],
        "best_metals": ["gold", "rose gold", "copper"],
    },
    "summer": {
        "skin_tones": ["fair", "light", "medium"],
        "undertone": "cool",
        "best_colors": ["lavender", "rose", "powder blue", "mauve", "cool pink", "plum", "seafoam", "mint"],
        "avoid_colors": ["orange", "bright yellow", "rust", "warm brown"],
        "best_neutrals": ["cool grey", "navy", "taupe", "white"],
        "best_metals": ["silver", "platinum", "white gold"],
    },
    "autumn": {
        "skin_tones": ["medium", "olive", "dark"],
        "undertone": "warm",
        "best_colors": ["rust", "olive", "mustard", "terracotta", "warm red", "burnt orange", "chocolate", "gold"],
        "avoid_colors": ["pink", "icy blue", "fuchsia", "cool grey"],
        "best_neutrals": ["brown", "olive", "cream", "warm grey"],
        "best_metals": ["gold", "bronze", "copper"],
    },
    "winter": {
        "skin_tones": ["olive", "dark", "deep"],
        "undertone": "cool",
        "best_colors": ["red", "emerald", "royal blue", "fuchsia", "black", "white", "burgundy", "magenta"],
        "avoid_colors": ["peach", "salmon", "warm brown", "olive", "camel"],
        "best_neutrals": ["black", "white", "cool grey", "navy"],
        "best_metals": ["silver", "platinum", "chrome"],
    },
}

# Color hex to name mapping (common colors)
COLOR_NAME_MAP = {
    "#000000": "black", "#ffffff": "white", "#ff0000": "red", "#00ff00": "green",
    "#0000ff": "blue", "#ffff00": "yellow", "#ff00ff": "magenta", "#00ffff": "cyan",
    "#800000": "maroon", "#008000": "green", "#000080": "navy", "#808080": "grey",
    "#c0c0c0": "silver", "#800080": "purple", "#ffa500": "orange", "#ffc0cb": "pink",
    "#a52a2a": "brown", "#deb887": "tan", "#f5deb3": "wheat", "#ffd700": "gold",
    "#ff6347": "tomato", "#ff4500": "orange red", "#dc143c": "crimson",
    "#b22222": "firebrick", "#cd853f": "peru", "#d2691e": "chocolate",
    "#8b4513": "saddle brown", "#228b22": "forest green", "#2e8b57": "sea green",
    "#3cb371": "medium sea green", "#20b2aa": "light sea green", "#4682b4": "steel blue",
    "#1e90ff": "dodger blue", "#00bfff": "deep sky blue", "#87ceeb": "sky blue",
    "#0000cd": "medium blue", "#191970": "midnight blue", "#4b0082": "indigo",
    "#9370db": "medium purple", "#ba55d3": "medium orchid", "#da70d6": "orchid",
    "#c71585": "medium violet red", "#db7093": "pale violet red",
    "#f08080": "light coral", "#e6e6fa": "lavender", "#fff0f5": "lavender blush",
    "#ffe4e1": "misty rose", "#ffdead": "navajo white", "#f5f5dc": "beige",
    "#fdf5e6": "old lace", "#fffff0": "ivory", "#f0fff0": "honeydew",
    "#f5fffa": "mint cream", "#f0ffff": "azure", "#f0f8ff": "alice blue",
    "#fff8dc": "cornsilk", "#f5f5f5": "white smoke", "#fff5ee": "seashell",
    "#f8f8ff": "ghost white", "#fffaf0": "floral white",
    "#ffc0cb": "pink", "#ffb6c1": "light pink", "#ff1493": "deep pink",
    "#ff69b4": "hot pink", "#db7093": "pale violet red",
    "#800000": "maroon", "#b03060": "maroon", "#c00000": "dark red",
    "#e30b5c": "ruby", "#9b111e": "ruby red",
}

# Harmonious color pairings
COLOR_HARMONY = {
    "complementary": {  # Opposite on color wheel
        "red": ["green", "teal"], "blue": ["orange", "gold"], "yellow": ["purple", "indigo"],
        "green": ["red", "magenta"], "purple": ["yellow", "gold"], "orange": ["blue", "navy"],
        "pink": ["green", "olive"], "coral": ["teal", "navy"], "burgundy": ["gold", "olive"],
        "navy": ["coral", "gold"], "teal": ["coral", "peach"], "gold": ["purple", "navy"],
    },
    "analogous": {  # Adjacent on color wheel
        "red": ["orange", "pink", "burgundy"], "blue": ["teal", "purple", "navy"],
        "yellow": ["orange", "green", "gold"], "green": ["teal", "olive", "yellow"],
        "purple": ["blue", "pink", "magenta"], "orange": ["red", "yellow", "coral"],
        "pink": ["red", "purple", "lavender"], "coral": ["orange", "pink", "salmon"],
    },
    "triadic": {  # 120 degrees apart
        "red": ["blue", "yellow"], "blue": ["red", "yellow"], "yellow": ["red", "blue"],
        "green": ["purple", "orange"], "purple": ["green", "orange"], "orange": ["green", "purple"],
    },
}


def hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB to hex color."""
    return f"#{r:02x}{g:02x}{b:02x}"


def rgb_to_hsl(r: int, g: int, b: int) -> tuple:
    """Convert RGB to HSL."""
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    max_c = max(r, g, b)
    min_c = min(r, g, b)
    l = (max_c + min_c) / 2

    if max_c == min_c:
        h = s = 0.0
    else:
        d = max_c - min_c
        s = d / (2 - max_c - min_c) if l > 0.5 else d / (max_c + min_c)
        if max_c == r:
            h = (g - b) / d + (6 if g < b else 0)
        elif max_c == g:
            h = (b - r) / d + 2
        else:
            h = (r - g) / d + 4
        h /= 6

    return (h * 360, s * 100, l * 100)


def detect_skin_tone_from_rgb(r: int, g: int, b: int) -> str:
    """Detect skin tone category from average RGB values."""
    for tone, ranges in SKIN_TONE_RANGES.items():
        if (ranges["r"][0] <= r <= ranges["r"][1] and
            ranges["g"][0] <= g <= ranges["g"][1] and
            ranges["b"][0] <= b <= ranges["b"][1]):
            return tone
    # Fallback: use brightness
    brightness = (r * 299 + g * 587 + b * 114) / 1000
    if brightness > 200:
        return "fair"
    elif brightness > 160:
        return "light"
    elif brightness > 120:
        return "medium"
    elif brightness > 80:
        return "olive"
    elif brightness > 50:
        return "dark"
    return "deep"


def detect_undertone_from_rgb(r: int, g: int, b: int) -> str:
    """Detect skin undertone from RGB."""
    r_ratio = r / max(r + g + b, 1)
    b_ratio = b / max(r + g + b, 1)
    g_ratio = g / max(r + g + b, 1)

    if r_ratio > 0.42 and r > b:
        return "warm"
    elif b_ratio > 0.35 or b > r:
        return "cool"
    else:
        return "neutral"


def detect_season(skin_tone: str, undertone: str) -> str:
    """Determine color season from skin tone and undertone."""
    for season, config in SEASONAL_PALETTES.items():
        if skin_tone in config["skin_tones"] and undertone == config["undertone"]:
            return season
    # Fallback based on undertone only
    if undertone == "warm":
        return "autumn"
    elif undertone == "cool":
        return "summer"
    return "winter"


def get_color_recommendations(skin_tone: str, undertone: str) -> dict:
    """Get full color recommendations for a skin tone."""
    season = detect_season(skin_tone, undertone)
    palette = SEASONAL_PALETTES[season]
    return {
        "season": season,
        "skin_tone": skin_tone,
        "undertone": undertone,
        "best_colors": palette["best_colors"],
        "avoid_colors": palette["avoid_colors"],
        "best_neutrals": palette["best_neutrals"],
        "best_metals": palette["best_metals"],
    }


def analyze_outfit_colors(colors: list) -> dict:
    """
    Analyze a combination of colors in an outfit.
    colors: list of hex color strings.
    Returns harmony score and suggestions.
    """
    if not colors:
        return {"score": 0, "message": "No colors to analyze"}

    rgb_colors = [hex_to_rgb(c) for c in colors]
    hsl_colors = [rgb_to_hsl(r, g, b) for r, g, b in rgb_colors]

    score = 50  # base
    notes = []

    if len(colors) == 1:
        score = 60
        notes.append("Single color outfit — add an accent for visual interest")
    elif len(colors) == 2:
        # Check complementary
        c1_name = _closest_color_name(*rgb_colors[0])
        c2_name = _closest_color_name(*rgb_colors[1])
        if c2_name in COLOR_HARMONY["complementary"].get(c1_name, []):
            score += 30
            notes.append(f"{c1_name} and {c2_name} are complementary — great contrast!")
        elif c2_name in COLOR_HARMONY["analogous"].get(c1_name, []):
            score += 20
            notes.append(f"{c1_name} and {c2_name} are analogous — harmonious blend")
        else:
            score += 10
            notes.append("These colors work but aren't a classic pairing")
    else:
        # Multiple colors — check if they share a temperature
        temps = []
        for h, s, l in hsl_colors:
            if h < 60 or h > 300:
                temps.append("warm")
            elif 150 < h < 270:
                temps.append("cool")
            else:
                temps.append("neutral")
        if len(set(temps)) <= 2:
            score += 15
            notes.append("Colors share similar temperature — cohesive look")
        else:
            score -= 5
            notes.append("Mixed warm and cool tones — can look disjointed")

    # Check for neutral anchoring
    neutrals = ["black", "white", "grey", "navy", "cream", "brown"]
    has_neutral = any(_closest_color_name(*rgb) in neutrals for rgb in rgb_colors)
    if has_neutral and len(colors) > 2:
        score += 10
        notes.append("Neutral anchor provides balance")

    return {
        "score": max(0, min(100, score)),
        "colors": colors,
        "notes": notes,
        "harmony_types": _detect_harmony_type(rgb_colors),
    }


def _closest_color_name(r: int, g: int, b: int) -> str:
    """Find the closest named color for an RGB value."""
    min_dist = float("inf")
    closest = "unknown"
    for hex_color, name in COLOR_NAME_MAP.items():
        hr, hg, hb = hex_to_rgb(hex_color)
        dist = ((r - hr) ** 2 + (g - hg) ** 2 + (b - hb) ** 2) ** 0.5
        if dist < min_dist:
            min_dist = dist
            closest = name
    return closest


def _detect_harmony_type(rgb_colors: list) -> list:
    """Detect what type of color harmony is present."""
    if len(rgb_colors) < 2:
        return []
    names = [_closest_color_name(*rgb) for rgb in rgb_colors]
    harmonies = []
    for h_type, pairs in COLOR_HARMONY.items():
        for i, n1 in enumerate(names):
            for n2 in names[i + 1:]:
                if n2 in pairs.get(n1, []):
                    harmonies.append(h_type)
    return list(set(harmonies))


def extract_dominant_colors(image_path: str, num_colors: int = 3) -> list:
    """
    Extract dominant colors from an image using PIL.
    Returns list of hex color strings.
    """
    try:
        from PIL import Image
        import collections

        img = Image.open(image_path)
        img = img.convert("RGB")
        img = img.resize((150, 150))

        pixels = list(img.getdata())
        # Quantize to reduce color space
        quantized = []
        for r, g, b in pixels:
            qr = (r // 32) * 32
            qg = (g // 32) * 32
            qb = (b // 32) * 32
            quantized.append((min(qr, 255), min(qg, 255), min(qb, 255)))

        counter = collections.Counter(quantized)
        dominant = counter.most_common(num_colors)

        return [rgb_to_hex(r, g, b) for (r, g, b), _ in dominant]
    except Exception as e:
        logger.warning(f"Failed to extract colors from image: {e}")
        return []


async def analyze_skin_from_photo(image_path: str) -> dict:
    """
    Analyze skin tone from a photo.
    Extracts face/skin region colors and determines tone and undertone.
    """
    try:
        from PIL import Image

        img = Image.open(image_path)
        img = img.convert("RGB")
        img = img.resize((200, 200))

        # Sample center region (likely face/skin)
        w, h = img.size
        center_region = img.crop((w // 4, h // 4, 3 * w // 4, 3 * h // 4))
        pixels = list(center_region.getdata())

        # Filter out very dark and very light pixels (background, hair)
        skin_pixels = [
            (r, g, b) for r, g, b in pixels
            if 50 < r < 250 and 30 < g < 230 and 20 < b < 200
            and abs(r - g) > 5  # Not pure grey
        ]

        if not skin_pixels:
            skin_pixels = pixels  # Fallback to all pixels

        # Average color
        avg_r = sum(p[0] for p in skin_pixels) // len(skin_pixels)
        avg_g = sum(p[1] for p in skin_pixels) // len(skin_pixels)
        avg_b = sum(p[2] for p in skin_pixels) // len(skin_pixels)

        skin_tone = detect_skin_tone_from_rgb(avg_r, avg_g, avg_b)
        undertone = detect_undertone_from_rgb(avg_r, avg_g, avg_b)
        recommendations = get_color_recommendations(skin_tone, undertone)

        return {
            "detected_rgb": [avg_r, avg_g, avg_b],
            "detected_hex": rgb_to_hex(avg_r, avg_g, avg_b),
            "skin_tone": skin_tone,
            "undertone": undertone,
            **recommendations,
        }
    except Exception as e:
        logger.warning(f"Skin tone analysis failed: {e}")
        return {
            "skin_tone": "medium",
            "undertone": "neutral",
            "error": str(e),
            **get_color_recommendations("medium", "neutral"),
        }


def suggest_complementary_outfit(base_color_hex: str) -> dict:
    """Suggest complementary colors for an outfit based on a base color."""
    r, g, b = hex_to_rgb(base_color_hex)
    base_name = _closest_color_name(r, g, b)

    complementary = COLOR_HARMONY["complementary"].get(base_name, [])
    analogous = COLOR_HARMONY["analogous"].get(base_name, [])
    triadic = COLOR_HARMONY["triadic"].get(base_name, [])

    return {
        "base_color": base_color_hex,
        "base_name": base_name,
        "complementary": complementary,
        "analogous": analogous,
        "triadic": triadic,
        "suggestion": (
            f"Pair {base_name} with "
            + (complementary[0] if complementary else "neutrals")
            + " for a bold look, or "
            + (analogous[0] if analogous else "similar tones")
            + " for a subtle blend."
        ),
    }
