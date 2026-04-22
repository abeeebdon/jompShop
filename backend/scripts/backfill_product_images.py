"""One-shot backfill: assign unique, topical images to existing products & shop_listings.

Run: cd /app/backend && python -m scripts.backfill_product_images
Idempotent: it resets photos to the chosen asset per title match.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db import db  # noqa: E402

_U = "https://images.unsplash.com/photo-"
_Q = "?auto=format&fit=crop&w=900&q=80"

PRODUCT_IMAGES = {
    # product.name substring  ->  unsplash id
    "Adire Indigo": "1528459105426-b9548367069b",
    "Ankara Wax": "1503342217505-b0a15ec3261c",
    "Ofada Rice": "1586201375761-83865001e31c",
    "Palm Oil": "1604329760661-e71dc83f8f26",
    "Shea Butter": "1608571423902-eed4a5ad8108",
    "Leather Tote": "1553062407-98eeb64c6a62",
}

LISTING_IMAGES = {
    "Ofada Rice 5kg": "1536304929831-ee1ca9d44906",
    "Shea Butter 500g": "1565193566173-7a0ee3dbe261",
    "Adire Scarf": "1528459105426-b9548367069b",
    "Ankara": "1503342217505-b0a15ec3261c",
    "Palm Oil": "1604329760661-e71dc83f8f26",
    "Leather": "1553062407-98eeb64c6a62",
}

FALLBACK_BY_CATEGORY = {
    "fashion": "1528459105426-b9548367069b",
    "agriculture": "1608571423902-eed4a5ad8108",
    "staple-foods": "1586201375761-83865001e31c",
    "general-goods": "1554672723-d42a16e533db",
}

GENERIC_FALLBACK = "1554672723-d42a16e533db"


def _url(photo_id: str) -> str:
    return f"{_U}{photo_id}{_Q}"


def pick(title: str, mapping: dict, category: str | None = None) -> str:
    for key, pid in mapping.items():
        if key.lower() in (title or "").lower():
            return _url(pid)
    if category and category in FALLBACK_BY_CATEGORY:
        return _url(FALLBACK_BY_CATEGORY[category])
    return _url(GENERIC_FALLBACK)


async def main():
    # products
    prod_count = 0
    async for p in db.products.find({}, {"_id": 0, "id": 1, "name": 1, "category": 1, "photos": 1}):
        new_photo = pick(p.get("name", ""), PRODUCT_IMAGES, p.get("category"))
        if p.get("photos") != [new_photo]:
            await db.products.update_one({"id": p["id"]}, {"$set": {"photos": [new_photo]}})
            prod_count += 1
            print(f"[product] {p['name']} -> {new_photo}")

    # shop listings
    listing_count = 0
    async for l in db.shop_listings.find({}, {"_id": 0, "id": 1, "title": 1, "category": 1, "photos": 1}):
        new_photo = pick(l.get("title", ""), LISTING_IMAGES, l.get("category"))
        if l.get("photos") != [new_photo]:
            await db.shop_listings.update_one({"id": l["id"]}, {"$set": {"photos": [new_photo]}})
            listing_count += 1
            print(f"[listing] {l['title']} -> {new_photo}")

    print(f"\nBackfill complete: {prod_count} products + {listing_count} listings updated.")


if __name__ == "__main__":
    asyncio.run(main())
