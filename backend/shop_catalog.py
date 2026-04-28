"""Authoritative list of 50 export-ready African shop listings.

Used by both seed.py (fresh DB) and scripts/load_50_listings.py (backfill).
Each entry produces a `shop_listing` document. Images are stable Unsplash IDs
that have been verified to return HTTP 200.
"""
from __future__ import annotations

# Verified Unsplash photo IDs (200 OK as of Feb 2026).
_IMG_BANK = {
    "textile_a": "1528459105426-b9548367069b",
    "textile_b": "1503342217505-b0a15ec3261c",
    "textile_c": "1768212566108-4ce4f329e4d2",
    "textile_d": "1488646953014-85cb44e25828",
    "textile_e": "1583394838336-acd977736f90",
    "textile_f": "1545167622-3a6ac756afa4",
    "textile_g": "1535378917042-10a22c95931a",
    "rice":      "1586201375761-83865001e31c",
    "rice_2":    "1536304929831-ee1ca9d44906",
    "grain":     "1574484284002-952d92456975",
    "agro_a":    "1601050690597-df0568f70950",
    "agro_b":    "1622676566956-b42b50c84c31",
    "agro_c":    "1604329760661-e71dc83f8f26",
    "oil_jar":   "1608571423902-eed4a5ad8108",
    "oil_2":     "1565193566173-7a0ee3dbe261",
    "leather":   "1553062407-98eeb64c6a62",
    "soap":      "1556228720-195a672e8a03",
    "beauty_a":  "1591348122449-02525d70379b",
    "beauty_b":  "1583394838336-acd977736f90",
    "beauty_c":  "1606107557195-0e29a4b5b4aa",
    "beauty_d":  "1571781926291-c477ebfd024b",
    "decor_a":   "1542838132-92c53300491e",
    "decor_b":   "1584308666744-24d5c474f2ae",
    "decor_c":   "1582719508461-905c673771fd",
    "decor_d":   "1611078489935-0cb964de46d6",
    "decor_e":   "1610563166150-b34df4f3bcd6",
    "decor_f":   "1607082348824-0a96f2a4b9da",
    "decor_g":   "1599566150163-29194dcaad36",
    "decor_h":   "1525909002-1b05e0c869d8",
    "jewel_a":   "1578321272176-b7bbc0679853",
    "jewel_b":   "1571877227200-a0d98ea607e9",
    "jewel_c":   "1596496050755-c923e73e42e1",
    "tea":       "1551018612-9715965c6742",
    "spice":     "1547036967-23d11aacaee0",
    "tea_2":     "1554995207-c18c203602cb",
    "general":   "1497486751825-1233686d5d80",
}

_IMG_BASE = "https://images.unsplash.com/photo-"
_IMG_QS = "?auto=format&fit=crop&w=900&q=80"


def img(key: str) -> str:
    return f"{_IMG_BASE}{_IMG_BANK[key]}{_IMG_QS}"


# ------------------------------------------------------------
# 50 listings — (title, description, category, price, stock, mode, ships_from, image_key)
# mode: 'riby_dtc' (direct from Africa, Riby Inc DPoR) or 'buyer_local' (US warehouse, 48hr)
# Origin = Nigeria unless noted.
# ------------------------------------------------------------

LISTINGS_50 = [
    # ---------------- Fashion & Textiles (10) ----------------
    ("Premium Adire Indigo Fabric — 6 yards", "Handwoven indigo-dyed Adire textile from Abeokuta artisans. 100% cotton, 6-yard panels. Export-ready, SON certified.", "fashion", 64.99, 80, "riby_dtc", "Lagos → Riby US fulfillment", "textile_a"),
    ("Ankara Wax Print Roll — 12 yards", "Vibrant wax-print Ankara fabric, 12-yard commercial roll. Designed in Lagos, printed in Nigeria.", "fashion", 79.00, 120, "riby_dtc", "Lagos → Riby US fulfillment", "textile_b"),
    ("Aso-Oke Handwoven Silk Textile — Royal", "Festival-grade Aso-Oke woven by Ilorin master weavers. Metallic silver and gold threadwork.", "fashion", 145.00, 25, "riby_dtc", "Ilorin → Riby US fulfillment", "textile_c"),
    ("Kente Royal Cloth — Strip (4 yards)", "Hand-loomed Ashanti Kente strip from Bonwire, Ghana. Vibrant traditional patterns.", "fashion", 89.00, 40, "riby_dtc", "Ghana → Riby US fulfillment", "textile_d"),
    ("Akwete Hand-loomed Cloth — Igbo", "Traditional Akwete cloth from Abia State, hand-loomed by women cooperatives. 6 yards.", "fashion", 110.00, 30, "riby_dtc", "Abia → Riby US fulfillment", "textile_e"),
    ("Bogolan Mudcloth Bedspread — Mali", "Authentic mudcloth bedspread from Mali, hand-painted with natural dyes.", "fashion", 165.00, 18, "riby_dtc", "Mali → Riby US fulfillment", "textile_f"),
    ("Tuareg Indigo Throw Blanket", "Hand-dyed indigo throw blanket from Saharan Tuareg artisans. 200x150cm.", "fashion", 95.00, 35, "riby_dtc", "Niger → Riby US fulfillment", "textile_g"),
    ("Handwoven Adire Scarf — Lagos Edition", "Hand-dyed Adire indigo scarf (180×50cm) from Abeokuta artisans. Individually numbered.", "fashion", 49.00, 75, "buyer_local", "Brooklyn, NY", "textile_a"),
    ("Ankara Print Maxi Dress — Women's", "Tailored Ankara maxi dress, sizes XS–XL. Made by Lagos women's cooperative.", "fashion", 78.00, 60, "buyer_local", "Brooklyn, NY", "textile_b"),
    ("Kente Stole — Graduation Edition", "Traditional Kente graduation stole — 60 inches, ready to wear.", "fashion", 39.99, 110, "buyer_local", "Brooklyn, NY", "textile_d"),

    # ---------------- Agriculture & Foods (12) ----------------
    ("Premium Ofada Rice — 50kg Bag", "Single-origin brown Ofada rice from Ogun State farmers. NAFDAC registered, parboiled.", "staple-foods", 78.00, 200, "riby_dtc", "Ogun → Riby US fulfillment", "rice"),
    ("Ofada Rice 5kg Retail Bag", "Authentic single-origin Ofada rice, repackaged into retail-ready 5kg bags at Brooklyn.", "staple-foods", 24.99, 220, "buyer_local", "Brooklyn, NY", "rice_2"),
    ("Cold-Pressed Palm Oil — 20L Jerry Can", "Sustainably-sourced unrefined red palm oil from Edo cooperatives.", "agriculture", 92.00, 90, "riby_dtc", "Edo → Riby US fulfillment", "agro_c"),
    ("Cold-Pressed Palm Oil 1L Bottle", "Retail 1L bottle of pure unrefined palm oil. NAFDAC registered.", "agriculture", 14.50, 180, "buyer_local", "Brooklyn, NY", "agro_c"),
    ("Garri Ijebu — Premium 5kg", "Crisp Ijebu garri, oven-dried and stone-ground. Resealable export bag.", "staple-foods", 18.99, 150, "buyer_local", "Brooklyn, NY", "grain"),
    ("Hibiscus (Zobo) Dried Flowers — 1kg", "Sun-dried Sudanese hibiscus flowers — for tea, juice, syrups.", "staple-foods", 22.00, 140, "riby_dtc", "Kano → Riby US fulfillment", "agro_a"),
    ("Cocoa Beans — Fermented (50kg)", "Premium fermented cocoa beans from Ondo State for chocolate makers.", "agriculture", 280.00, 30, "riby_dtc", "Ondo → Riby US fulfillment", "agro_b"),
    ("Sesame Seeds — Hulled (25kg)", "Pure white hulled sesame seeds from Benue State. Export-grade.", "agriculture", 89.00, 60, "riby_dtc", "Benue → Riby US fulfillment", "agro_a"),
    ("Cashew Nuts — Raw Whole (10kg)", "Premium raw cashew nuts from Kogi cooperatives. Vacuum-sealed.", "agriculture", 145.00, 50, "riby_dtc", "Kogi → Riby US fulfillment", "agro_b"),
    ("Stockfish (Whole) — 1kg", "Norwegian-cured stockfish, traditional Igbo cooking staple.", "staple-foods", 45.00, 100, "buyer_local", "Brooklyn, NY", "general"),
    ("Plantain Flour — Unripe (5kg)", "Stone-ground unripe plantain flour. Diabetic-friendly.", "staple-foods", 28.00, 130, "buyer_local", "Brooklyn, NY", "grain"),
    ("Yam Flour (Elubo) — 5kg", "Pounded yam flour for amala. NAFDAC certified.", "staple-foods", 26.00, 140, "buyer_local", "Brooklyn, NY", "grain"),

    # ---------------- Beauty & Cosmetics (8) ----------------
    ("Unrefined Shea Butter 500g Jar", "Grade A unrefined shea butter hand-whipped by Northern Nigeria women's cooperatives.", "beauty", 32.00, 90, "riby_dtc", "Lagos → Riby US fulfillment", "oil_jar"),
    ("African Black Soap (Dudu Osun) — Set of 5", "Authentic Dudu Osun black soap, handmade in Ilesa. Set of 5 bars.", "beauty", 24.99, 220, "buyer_local", "Brooklyn, NY", "soap"),
    ("Marula Oil 100ml — Cold Pressed", "Pure cold-pressed marula oil from Southern Africa. For face & hair.", "beauty", 45.00, 80, "riby_dtc", "South Africa → Riby US fulfillment", "beauty_a"),
    ("Baobab Oil 50ml", "Cold-pressed baobab seed oil — rich in omega 3-6-9.", "beauty", 38.00, 70, "riby_dtc", "Senegal → Riby US fulfillment", "beauty_b"),
    ("Coconut Oil — Virgin 500ml", "Cold-pressed virgin coconut oil from Cross River State.", "beauty", 22.00, 130, "buyer_local", "Brooklyn, NY", "oil_2"),
    ("Argan Oil 100ml — Moroccan", "Pure Moroccan argan oil from Berber women's cooperatives.", "beauty", 52.00, 60, "riby_dtc", "Morocco → Riby US fulfillment", "beauty_c"),
    ("African Black Soap Liquid 500ml", "Liquid African black soap with shea & honey. Pump bottle.", "beauty", 19.99, 140, "buyer_local", "Brooklyn, NY", "beauty_d"),
    ("Shea Butter Body Cream 250g", "Whipped shea butter body cream — lavender vanilla scent.", "beauty", 28.00, 110, "buyer_local", "Brooklyn, NY", "oil_jar"),

    # ---------------- Home & Decor (8) ----------------
    ("Hand-carved Yoruba Mask — Authentic", "Hand-carved iroko wood Yoruba mask. Each piece unique.", "home-decor", 145.00, 22, "riby_dtc", "Oyo → Riby US fulfillment", "decor_a"),
    ("Bolga Basket — Round (Large)", "Hand-woven Bolga basket from Ghana. Natural straw, leather handles.", "home-decor", 68.00, 80, "riby_dtc", "Ghana → Riby US fulfillment", "decor_b"),
    ("Djembe Drum — Senegal Origin", "Hand-carved djembe with goat-skin head. 14-inch professional grade.", "home-decor", 220.00, 18, "riby_dtc", "Senegal → Riby US fulfillment", "decor_c"),
    ("Calabash Bowl Set (3 pieces)", "Hand-decorated calabash bowls — small, medium, large.", "home-decor", 55.00, 60, "riby_dtc", "Lagos → Riby US fulfillment", "decor_d"),
    ("Mudcloth Cushion Cover — Pair", "Pair of hand-painted mudcloth cushion covers. 18×18 inches.", "home-decor", 75.00, 50, "buyer_local", "Brooklyn, NY", "decor_e"),
    ("Soapstone Sculpture — Kisii", "Hand-carved Kisii soapstone sculpture from Kenya. 8-10 inches.", "home-decor", 89.00, 35, "riby_dtc", "Kenya → Riby US fulfillment", "decor_f"),
    ("Beaded Wall Art Hanging", "Maasai-style beaded wall hanging. 24-inch diameter.", "home-decor", 110.00, 28, "riby_dtc", "Kenya → Riby US fulfillment", "decor_g"),
    ("Akan Stool — Ghana", "Traditional Akan-style hand-carved wooden stool.", "home-decor", 185.00, 15, "riby_dtc", "Ghana → Riby US fulfillment", "decor_h"),

    # ---------------- Jewelry & Accessories (6) ----------------
    ("Maasai Beaded Necklace", "Authentic Maasai beaded statement necklace, multicolor.", "accessories", 42.00, 100, "riby_dtc", "Kenya → Riby US fulfillment", "jewel_a"),
    ("Ankara Print Tote Bag", "Lined Ankara print tote with leather handles.", "accessories", 38.00, 120, "buyer_local", "Brooklyn, NY", "textile_b"),
    ("Leather Tote — Handcrafted Lagos", "Full-grain Nigerian leather tote, hand-stitched in Lagos.", "accessories", 159.00, 45, "riby_dtc", "Lagos → Riby US fulfillment", "leather"),
    ("Tuareg Silver Cross Pendant", "Hand-wrought silver Tuareg cross pendant on leather cord.", "accessories", 58.00, 70, "riby_dtc", "Mali → Riby US fulfillment", "jewel_b"),
    ("Recycled Glass Bead Bracelet — Krobo", "Stack of 3 Krobo recycled glass bead bracelets.", "accessories", 24.99, 130, "buyer_local", "Brooklyn, NY", "jewel_c"),
    ("Handwoven Raffia Hat", "Wide-brim raffia sun hat, hand-woven in Madagascar.", "accessories", 49.00, 85, "riby_dtc", "Madagascar → Riby US fulfillment", "decor_b"),

    # ---------------- Beverages (4) ----------------
    ("Hibiscus Tea Bags (50 ct)", "Premium hibiscus tea — 50 individually-wrapped sachets.", "beverages", 18.99, 200, "buyer_local", "Brooklyn, NY", "tea"),
    ("Baobab Powder 250g", "Wild-harvested baobab powder — vitamin C powerhouse.", "beverages", 26.00, 140, "riby_dtc", "Senegal → Riby US fulfillment", "tea_2"),
    ("Ginger Turmeric Spice Blend (200g)", "Stone-ground ginger + turmeric + black pepper blend.", "beverages", 14.99, 160, "buyer_local", "Brooklyn, NY", "spice"),
    ("Rooibos Tea — Loose Leaf (250g)", "Premium South African rooibos. Caffeine-free.", "beverages", 22.00, 120, "riby_dtc", "South Africa → Riby US fulfillment", "tea"),

    # ---------------- Spices & Pantry (2) ----------------
    ("Suya Spice Mix (200g)", "Authentic Northern Nigerian suya pepper blend — peanut, ginger, paprika.", "staple-foods", 12.99, 200, "buyer_local", "Brooklyn, NY", "spice"),
    ("Ata Rodo Pepper Powder (150g)", "Stone-ground habanero (Ata Rodo) pepper powder — fiery hot.", "staple-foods", 14.99, 180, "buyer_local", "Brooklyn, NY", "spice"),
]


def to_listing_doc(idx: int, owner_business_id: str, item: tuple, now_iso: str) -> dict:
    import uuid as _uuid
    title, desc, cat, price, stock, mode, ships_from, img_key = item
    return {
        "id": str(_uuid.uuid4()),
        "owner_business_id": owner_business_id,
        "title": title,
        "description": desc,
        "category": cat,
        "retail_price_usd": float(price),
        "stock_qty": int(stock),
        "fulfillment_mode": mode,
        "country_of_origin": "Nigeria" if "Lagos" in ships_from or "Ogun" in ships_from or "Edo" in ships_from or "Kano" in ships_from or "Ondo" in ships_from or "Benue" in ships_from or "Kogi" in ships_from or "Cross River" in ships_from or "Oyo" in ships_from or "Abia" in ships_from or "Ilorin" in ships_from else (
            "Ghana" if "Ghana" in ships_from else
            "Kenya" if "Kenya" in ships_from else
            "Senegal" if "Senegal" in ships_from else
            "South Africa" if "South Africa" in ships_from else
            "Morocco" if "Morocco" in ships_from else
            "Mali" if "Mali" in ships_from else
            "Niger" if "Niger" in ships_from else
            "Madagascar" if "Madagascar" in ships_from else
            "Nigeria"
        ),
        "ships_from": ships_from,
        "delivery_partner_of_record": "Riby Inc" if mode == "riby_dtc" else "",
        "photos": [img(img_key)],
        "status": "active",
        "created_at": now_iso,
    }
