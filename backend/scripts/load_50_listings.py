"""Backfill: replace shop_listings with the canonical 50-product catalog.

Idempotent: deletes all existing shop_listings owned by the seeded businesses
(or all if --all), then inserts 50 fresh listings split across exporter (riby_dtc)
and buyer (buyer_local).

Run: cd /app/backend && python -m scripts.load_50_listings [--all]
"""
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db import db  # noqa: E402
from shop_catalog import LISTINGS_50, to_listing_doc  # noqa: E402


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def main(wipe_all: bool = False):
    # find exporter + buyer business IDs from seeded users
    exporter = await db.users.find_one({"email": "exporter@helix.com"}, {"_id": 0, "business_id": 1})
    buyer = await db.users.find_one({"email": "buyer@helix.com"}, {"_id": 0, "business_id": 1})
    if not exporter or not exporter.get("business_id"):
        print("Exporter business not found — run seed first.")
        return
    if not buyer or not buyer.get("business_id"):
        print("Buyer business not found — run seed first.")
        return
    exp_biz = exporter["business_id"]
    byr_biz = buyer["business_id"]

    # delete previous listings (default: only owned by these two)
    if wipe_all:
        r = await db.shop_listings.delete_many({})
    else:
        r = await db.shop_listings.delete_many({"owner_business_id": {"$in": [exp_biz, byr_biz]}})
    print(f"Deleted {r.deleted_count} existing listings")

    docs = []
    now = _now_iso()
    for idx, item in enumerate(LISTINGS_50):
        owner = byr_biz if item[5] == "buyer_local" else exp_biz
        docs.append(to_listing_doc(idx, owner, item, now))

    await db.shop_listings.insert_many(docs)
    print(f"Inserted {len(docs)} listings")
    by_cat: dict[str, int] = {}
    for d in docs:
        by_cat[d["category"]] = by_cat.get(d["category"], 0) + 1
    for c, n in sorted(by_cat.items()):
        print(f"  · {c}: {n}")


if __name__ == "__main__":
    wipe_all = "--all" in sys.argv
    asyncio.run(main(wipe_all=wipe_all))
