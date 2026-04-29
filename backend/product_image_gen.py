"""SVG product card generator for shop listings without a verified photo.

Generates a self-contained `data:image/svg+xml` URL with:
  - Jomp-themed gradient background
  - A category-specific emoji (acts as an "icon" for fish, masks, drums, etc.)
  - The product name in clean typography
  - Origin / category subtitle

Result: every product gets a polished, on-brand visual card — never blank,
never mismatched, and instantly recognisable to the shopper.
"""
from __future__ import annotations
from urllib.parse import quote
import html

# Per-category gradient (top -> bottom) + emoji icon.
_THEME = {
    # tuple: (color_top, color_bottom, accent, emoji)
    "fashion":      ("#7B2CBF", "#F39C12", "#FFFFFF", "🧵"),
    "agriculture":  ("#1A7A6E", "#C9922A", "#FFFFFF", "🌾"),
    "staple-foods": ("#C9922A", "#0A1628", "#F5F5F5", "🍚"),
    "beauty":       ("#F39C12", "#4A2E8A", "#FFFFFF", "✨"),
    "home-decor":   ("#4A2E8A", "#C9922A", "#FFFFFF", "🏺"),
    "accessories":  ("#1A1A2E", "#F39C12", "#F39C12", "💎"),
    "beverages":    ("#7B2CBF", "#1A7A6E", "#FFD180", "🍵"),
}

# Per-product overrides — use a more specific emoji when the category emoji
# doesn't communicate the actual product (e.g., dried fish, drums, masks).
_PRODUCT_EMOJI = {
    "Stockfish": "🐟",
    "Yoruba Mask": "🎭",
    "Bolga Basket": "🧺",
    "Djembe Drum": "🥁",
    "Calabash Bowl": "🥥",
    "Akan Stool": "🪑",
    "Soapstone Sculpture": "🗿",
    "Beaded Wall Art": "🎨",
    "Mudcloth": "🟤",
    "Maasai Beaded": "📿",
    "Tuareg Silver": "🔱",
    "Recycled Glass Bead": "📿",
    "Raffia Hat": "🎩",
    "Hibiscus": "🌺",
    "Baobab": "🌳",
    "Ginger Turmeric": "🌶️",
    "Rooibos": "🍵",
    "Suya Spice": "🌶️",
    "Ata Rodo": "🌶️",
    "Cocoa": "🍫",
    "Sesame": "🌾",
    "Cashew": "🌰",
    "Plantain Flour": "🍌",
    "Yam Flour": "🥔",
    "Garri": "🌾",
    "Marula": "🥥",
    "Argan": "🫒",
    "Aso-Oke": "🧵",
    "Kente": "🧵",
    "Akwete": "🧵",
    "Bogolan": "🧵",
    "Tuareg Indigo": "🧣",
    "Ankara": "🧶",
}


def _pick_emoji(name: str, category: str) -> str:
    for keyword, emoji in _PRODUCT_EMOJI.items():
        if keyword.lower() in name.lower():
            return emoji
    return _THEME.get(category, _THEME["fashion"])[3]


def product_svg_url(name: str, category: str, ships_from: str = "") -> str:
    top, bot, accent, _ = _THEME.get(category, _THEME["fashion"])
    emoji = _pick_emoji(name, category)
    short_name = (name[:55] + "…") if len(name) > 56 else name
    short_ships = ships_from.split("→")[0].strip() if ships_from else category.replace("-", " ").title()

    safe_name = html.escape(short_name, quote=True)
    safe_ships = html.escape(short_ships[:38], quote=True)

    # Wrap long names onto two lines (~28 chars each).
    if len(safe_name) > 30:
        # Find a space near the middle.
        mid = len(safe_name) // 2
        left = safe_name.rfind(" ", 0, mid + 8)
        if left > 8:
            line1 = safe_name[:left]
            line2 = safe_name[left + 1:]
        else:
            line1, line2 = safe_name, ""
    else:
        line1, line2 = safe_name, ""

    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 900 675'>
  <defs>
    <linearGradient id='g' x1='0%' y1='0%' x2='100%' y2='100%'>
      <stop offset='0%' stop-color='{top}'/>
      <stop offset='100%' stop-color='{bot}'/>
    </linearGradient>
    <radialGradient id='spot' cx='30%' cy='25%' r='50%'>
      <stop offset='0%' stop-color='#FFFFFF' stop-opacity='0.18'/>
      <stop offset='100%' stop-color='#FFFFFF' stop-opacity='0'/>
    </radialGradient>
  </defs>
  <rect width='900' height='675' fill='url(#g)'/>
  <rect width='900' height='675' fill='url(#spot)'/>
  <text x='450' y='240' font-family='-apple-system,Helvetica,Arial,sans-serif' font-size='160' text-anchor='middle' dominant-baseline='middle'>{emoji}</text>
  <text x='450' y='400' font-family='-apple-system,Helvetica,Arial,sans-serif' font-weight='700' font-size='42' text-anchor='middle' fill='{accent}'>{line1}</text>
  <text x='450' y='452' font-family='-apple-system,Helvetica,Arial,sans-serif' font-weight='700' font-size='42' text-anchor='middle' fill='{accent}'>{line2}</text>
  <text x='450' y='540' font-family='-apple-system,Helvetica,Arial,sans-serif' font-size='22' text-anchor='middle' fill='{accent}' opacity='0.75' letter-spacing='3'>{safe_ships.upper()}</text>
  <text x='450' y='620' font-family='-apple-system,Helvetica,Arial,sans-serif' font-size='15' text-anchor='middle' fill='{accent}' opacity='0.55' letter-spacing='6'>JOMP SHOP</text>
</svg>"""
    # Whitespace + UTF-8 emojis are safe in `data:image/svg+xml;utf8,<...>` once URI-encoded.
    return "data:image/svg+xml;utf8," + quote(svg, safe="")
