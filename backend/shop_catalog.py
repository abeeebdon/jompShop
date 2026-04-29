"""Authoritative list of 50 export-ready African shop listings.

Used by both seed.py (fresh DB) and scripts/load_50_listings.py (backfill).
Each entry produces a `shop_listing` document. Images use a hybrid strategy:
- Product-specific Unsplash photos for items where we have visually-verified matches
- Branded placeholder cards (placehold.co with Jomp palette) for everything else,
  which are guaranteed to display the product name accurately and on-brand.
"""
from __future__ import annotations
from urllib.parse import quote_plus

# Jomp brand palette for placeholders (used when no verified Unsplash match).
# Each category gets a tinted, branded card so the marketplace stays visually cohesive.
_PALETTE = {
    "fashion":      ("F39C12", "FFFFFF"),  # Jomp orange / white
    "agriculture":  ("1A7A6E", "FFFFFF"),  # forest teal / white
    "staple-foods": ("C9922A", "0A1628"),  # gold / navy
    "beauty":       ("F39C12", "1F1B2E"),  # orange / deep purple
    "home-decor":   ("4A2E8A", "F39C12"),  # purple / orange
    "accessories":  ("1A1A2E", "F39C12"),  # dark / orange
    "beverages":    ("1A7A6E", "F5F5F5"),  # teal / cream
}

# Verified Unsplash IDs that visually depict their assigned products.
# (Verified via screenshot inspection + analyze_file_tool checks — Feb 2026.)
_UNSPLASH = {
    "adire":      "1528459105426-b9548367069b",
    "ankara":     "1503342217505-b0a15ec3261c",
    "rice":       "1586201375761-83865001e31c",
    "rice_pack":  "1536304929831-ee1ca9d44906",
    "palm_oil":   "1604329760661-e71dc83f8f26",
    "shea_jar":   "1608571423902-eed4a5ad8108",
    "shea_cos":   "1565193566173-7a0ee3dbe261",
    "leather":    "1553062407-98eeb64c6a62",
    "soap":       "1556228720-195a672e8a03",
}

_IMG_BASE = "https://images.unsplash.com/photo-"
_IMG_QS = "?auto=format&fit=crop&w=900&q=80"


def img_unsplash(key: str) -> str:
    return f"{_IMG_BASE}{_UNSPLASH[key]}{_IMG_QS}"


def img_placeholder(name: str, category: str) -> str:
    bg, fg = _PALETTE.get(category, ("4A2E8A", "F39C12"))
    # placehold.co renders a clean text card with the product name centered.
    return f"https://placehold.co/900x675/{bg}/{fg}/png?text={quote_plus(name)}&font=poppins"


# ------------------------------------------------------------
# 50 listings — (title, description, category, price, stock, mode, ships_from, image_strategy)
# image_strategy is either ("u", unsplash_key) or ("p",) for placeholder card.
# ------------------------------------------------------------

LISTINGS_50 = [
    # ---------------- Fashion & Textiles (10) ----------------
    ("Premium Adire Indigo Fabric — 6 yards", "Handwoven indigo-dyed Adire textile from Abeokuta artisans. 100% cotton, 6-yard panels. Export-ready, SON certified.", "fashion", 64.99, 80, "riby_dtc", "Lagos → Riby US fulfillment", ("u", "adire")),
    ("Ankara Wax Print Roll — 12 yards", "Vibrant wax-print Ankara fabric, 12-yard commercial roll. Designed in Lagos, printed in Nigeria.", "fashion", 79.00, 120, "riby_dtc", "Lagos → Riby US fulfillment", ("p",)),
    ("Aso-Oke Handwoven Silk Textile — Royal", "Festival-grade Aso-Oke woven by Ilorin master weavers. Metallic silver and gold threadwork.", "fashion", 145.00, 25, "riby_dtc", "Ilorin → Riby US fulfillment", ("p",)),
    ("Kente Royal Cloth — Strip (4 yards)", "Hand-loomed Ashanti Kente strip from Bonwire, Ghana. Vibrant traditional patterns.", "fashion", 89.00, 40, "riby_dtc", "Ghana → Riby US fulfillment", ("p",)),
    ("Akwete Hand-loomed Cloth — Igbo", "Traditional Akwete cloth from Abia State, hand-loomed by women cooperatives. 6 yards.", "fashion", 110.00, 30, "riby_dtc", "Abia → Riby US fulfillment", ("p",)),
    ("Bogolan Mudcloth Bedspread — Mali", "Authentic mudcloth bedspread from Mali, hand-painted with natural dyes.", "fashion", 165.00, 18, "riby_dtc", "Mali → Riby US fulfillment", ("p",)),
    ("Tuareg Indigo Throw Blanket", "Hand-dyed indigo throw blanket from Saharan Tuareg artisans. 200x150cm.", "fashion", 95.00, 35, "riby_dtc", "Niger → Riby US fulfillment", ("p",)),
    ("Handwoven Adire Scarf — Lagos Edition", "Hand-dyed Adire indigo scarf (180×50cm) from Abeokuta artisans. Individually numbered.", "fashion", 49.00, 75, "buyer_local", "Brooklyn, NY", ("u", "adire")),
    ("Ankara Print Maxi Dress — Women's", "Tailored Ankara maxi dress, sizes XS–XL. Made by Lagos women's cooperative.", "fashion", 78.00, 60, "buyer_local", "Brooklyn, NY", ("p",)),
    ("Kente Stole — Graduation Edition", "Traditional Kente graduation stole — 60 inches, ready to wear.", "fashion", 39.99, 110, "buyer_local", "Brooklyn, NY", ("p",)),

    # ---------------- Agriculture & Foods (12) ----------------
    ("Premium Ofada Rice — 50kg Bag", "Single-origin brown Ofada rice from Ogun State farmers. NAFDAC registered, parboiled.", "staple-foods", 78.00, 200, "riby_dtc", "Ogun → Riby US fulfillment", ("u", "rice")),
    ("Ofada Rice 5kg Retail Bag", "Authentic single-origin Ofada rice, repackaged into retail-ready 5kg bags at Brooklyn.", "staple-foods", 24.99, 220, "buyer_local", "Brooklyn, NY", ("u", "rice_pack")),
    ("Cold-Pressed Palm Oil — 20L Jerry Can", "Sustainably-sourced unrefined red palm oil from Edo cooperatives.", "agriculture", 92.00, 90, "riby_dtc", "Edo → Riby US fulfillment", ("u", "palm_oil")),
    ("Cold-Pressed Palm Oil 1L Bottle", "Retail 1L bottle of pure unrefined palm oil. NAFDAC registered.", "agriculture", 14.50, 180, "buyer_local", "Brooklyn, NY", ("u", "palm_oil")),
    ("Garri Ijebu — Premium 5kg", "Crisp Ijebu garri, oven-dried and stone-ground. Resealable export bag.", "staple-foods", 18.99, 150, "buyer_local", "Brooklyn, NY", ("p",)),
    ("Hibiscus (Zobo) Dried Flowers — 1kg", "Sun-dried Sudanese hibiscus flowers — for tea, juice, syrups.", "staple-foods", 22.00, 140, "riby_dtc", "Kano → Riby US fulfillment", ("p",)),
    ("Cocoa Beans — Fermented (50kg)", "Premium fermented cocoa beans from Ondo State for chocolate makers.", "agriculture", 280.00, 30, "riby_dtc", "Ondo → Riby US fulfillment", ("p",)),
    ("Sesame Seeds — Hulled (25kg)", "Pure white hulled sesame seeds from Benue State. Export-grade.", "agriculture", 89.00, 60, "riby_dtc", "Benue → Riby US fulfillment", ("p",)),
    ("Cashew Nuts — Raw Whole (10kg)", "Premium raw cashew nuts from Kogi cooperatives. Vacuum-sealed.", "agriculture", 145.00, 50, "riby_dtc", "Kogi → Riby US fulfillment", ("p",)),
    ("Stockfish (Whole) — 1kg", "Norwegian-cured stockfish, traditional Igbo cooking staple.", "staple-foods", 45.00, 100, "buyer_local", "Brooklyn, NY", ("p",)),
    ("Plantain Flour — Unripe (5kg)", "Stone-ground unripe plantain flour. Diabetic-friendly.", "staple-foods", 28.00, 130, "buyer_local", "Brooklyn, NY", ("p",)),
    ("Yam Flour (Elubo) — 5kg", "Pounded yam flour for amala. NAFDAC certified.", "staple-foods", 26.00, 140, "buyer_local", "Brooklyn, NY", ("p",)),

    # ---------------- Beauty & Cosmetics (8) ----------------
    ("Unrefined Shea Butter 500g Jar", "Grade A unrefined shea butter hand-whipped by Northern Nigeria women's cooperatives.", "beauty", 32.00, 90, "riby_dtc", "Lagos → Riby US fulfillment", ("u", "shea_jar")),
    ("African Black Soap (Dudu Osun) — Set of 5", "Authentic Dudu Osun black soap, handmade in Ilesa. Set of 5 bars.", "beauty", 24.99, 220, "buyer_local", "Brooklyn, NY", ("u", "soap")),
    ("Marula Oil 100ml — Cold Pressed", "Pure cold-pressed marula oil from Southern Africa. For face & hair.", "beauty", 45.00, 80, "riby_dtc", "South Africa → Riby US fulfillment", ("p",)),
    ("Baobab Oil 50ml", "Cold-pressed baobab seed oil — rich in omega 3-6-9.", "beauty", 38.00, 70, "riby_dtc", "Senegal → Riby US fulfillment", ("p",)),
    ("Coconut Oil — Virgin 500ml", "Cold-pressed virgin coconut oil from Cross River State.", "beauty", 22.00, 130, "buyer_local", "Brooklyn, NY", ("u", "shea_cos")),
    ("Argan Oil 100ml — Moroccan", "Pure Moroccan argan oil from Berber women's cooperatives.", "beauty", 52.00, 60, "riby_dtc", "Morocco → Riby US fulfillment", ("p",)),
    ("African Black Soap Liquid 500ml", "Liquid African black soap with shea & honey. Pump bottle.", "beauty", 19.99, 140, "buyer_local", "Brooklyn, NY", ("u", "soap")),
    ("Shea Butter Body Cream 250g", "Whipped shea butter body cream — lavender vanilla scent.", "beauty", 28.00, 110, "buyer_local", "Brooklyn, NY", ("u", "shea_jar")),

    # ---------------- Home & Decor (8) ----------------
    ("Hand-carved Yoruba Mask — Authentic", "Hand-carved iroko wood Yoruba mask. Each piece unique.", "home-decor", 145.00, 22, "riby_dtc", "Oyo → Riby US fulfillment", ("p",)),
    ("Bolga Basket — Round (Large)", "Hand-woven Bolga basket from Ghana. Natural straw, leather handles.", "home-decor", 68.00, 80, "riby_dtc", "Ghana → Riby US fulfillment", ("p",)),
    ("Djembe Drum — Senegal Origin", "Hand-carved djembe with goat-skin head. 14-inch professional grade.", "home-decor", 220.00, 18, "riby_dtc", "Senegal → Riby US fulfillment", ("p",)),
    ("Calabash Bowl Set (3 pieces)", "Hand-decorated calabash bowls — small, medium, large.", "home-decor", 55.00, 60, "riby_dtc", "Lagos → Riby US fulfillment", ("p",)),
    ("Mudcloth Cushion Cover — Pair", "Pair of hand-painted mudcloth cushion covers. 18×18 inches.", "home-decor", 75.00, 50, "buyer_local", "Brooklyn, NY", ("p",)),
    ("Soapstone Sculpture — Kisii", "Hand-carved Kisii soapstone sculpture from Kenya. 8-10 inches.", "home-decor", 89.00, 35, "riby_dtc", "Kenya → Riby US fulfillment", ("p",)),
    ("Beaded Wall Art Hanging", "Maasai-style beaded wall hanging. 24-inch diameter.", "home-decor", 110.00, 28, "riby_dtc", "Kenya → Riby US fulfillment", ("p",)),
    ("Akan Stool — Ghana", "Traditional Akan-style hand-carved wooden stool.", "home-decor", 185.00, 15, "riby_dtc", "Ghana → Riby US fulfillment", ("p",)),

    # ---------------- Jewelry & Accessories (6) ----------------
    ("Maasai Beaded Necklace", "Authentic Maasai beaded statement necklace, multicolor.", "accessories", 42.00, 100, "riby_dtc", "Kenya → Riby US fulfillment", ("p",)),
    ("Ankara Print Tote Bag", "Lined Ankara print tote with leather handles.", "accessories", 38.00, 120, "buyer_local", "Brooklyn, NY", ("p",)),
    ("Leather Tote — Handcrafted Lagos", "Full-grain Nigerian leather tote, hand-stitched in Lagos.", "accessories", 159.00, 45, "riby_dtc", "Lagos → Riby US fulfillment", ("u", "leather")),
    ("Tuareg Silver Cross Pendant", "Hand-wrought silver Tuareg cross pendant on leather cord.", "accessories", 58.00, 70, "riby_dtc", "Mali → Riby US fulfillment", ("p",)),
    ("Recycled Glass Bead Bracelet — Krobo", "Stack of 3 Krobo recycled glass bead bracelets.", "accessories", 24.99, 130, "buyer_local", "Brooklyn, NY", ("p",)),
    ("Handwoven Raffia Hat", "Wide-brim raffia sun hat, hand-woven in Madagascar.", "accessories", 49.00, 85, "riby_dtc", "Madagascar → Riby US fulfillment", ("p",)),

    # ---------------- Beverages (4) ----------------
    ("Hibiscus Tea Bags (50 ct)", "Premium hibiscus tea — 50 individually-wrapped sachets.", "beverages", 18.99, 200, "buyer_local", "Brooklyn, NY", ("p",)),
    ("Baobab Powder 250g", "Wild-harvested baobab powder — vitamin C powerhouse.", "beverages", 26.00, 140, "riby_dtc", "Senegal → Riby US fulfillment", ("p",)),
    ("Ginger Turmeric Spice Blend (200g)", "Stone-ground ginger + turmeric + black pepper blend.", "beverages", 14.99, 160, "buyer_local", "Brooklyn, NY", ("p",)),
    ("Rooibos Tea — Loose Leaf (250g)", "Premium South African rooibos. Caffeine-free.", "beverages", 22.00, 120, "riby_dtc", "South Africa → Riby US fulfillment", ("p",)),

    # ---------------- Spices & Pantry (2) ----------------
    ("Suya Spice Mix (200g)", "Authentic Northern Nigerian suya pepper blend — peanut, ginger, paprika.", "staple-foods", 12.99, 200, "buyer_local", "Brooklyn, NY", ("p",)),
    ("Ata Rodo Pepper Powder (150g)", "Stone-ground habanero (Ata Rodo) pepper powder — fiery hot.", "staple-foods", 14.99, 180, "buyer_local", "Brooklyn, NY", ("p",)),
]


def to_listing_doc(idx: int, owner_business_id: str, item: tuple, now_iso: str) -> dict:
    import uuid as _uuid
    title, desc, cat, price, stock, mode, ships_from, img_strat = item
    if img_strat[0] == "u":
        photo = img_unsplash(img_strat[1])
    else:
        photo = img_placeholder(title, cat)
    # Country inference (simple)
    nigeria_keys = ("Lagos", "Ogun", "Edo", "Kano", "Ondo", "Benue", "Kogi",
                    "Cross River", "Oyo", "Abia", "Ilorin")
    country = (
        "Ghana" if "Ghana" in ships_from else
        "Kenya" if "Kenya" in ships_from else
        "Senegal" if "Senegal" in ships_from else
        "South Africa" if "South Africa" in ships_from else
        "Morocco" if "Morocco" in ships_from else
        "Mali" if "Mali" in ships_from else
        "Niger" if "Niger" in ships_from else
        "Madagascar" if "Madagascar" in ships_from else
        "Nigeria" if any(k in ships_from for k in nigeria_keys) else
        "Nigeria"
    )
    return {
        "id": str(_uuid.uuid4()),
        "owner_business_id": owner_business_id,
        "title": title,
        "description": desc,
        "category": cat,
        "retail_price_usd": float(price),
        "stock_qty": int(stock),
        "fulfillment_mode": mode,
        "country_of_origin": country,
        "ships_from": ships_from,
        "delivery_partner_of_record": "Riby Inc" if mode == "riby_dtc" else "",
        "photos": [photo],
        "status": "active",
        "created_at": now_iso,
    }
