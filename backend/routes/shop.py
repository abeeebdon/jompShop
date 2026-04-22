"""Consumer e-commerce module.

Two listing types:
- buyer_local: Buyer (importer) lists local inventory from goods already imported.
  Fulfilled by the Buyer's US entity.
- riby_dtc: Exporter sells direct-to-consumer. Riby Inc is "Delivery Partner of Record".
  Exporter prepares the goods; Riby handles US last-mile + acts as Buyer of Record.
"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from db import db
from auth import get_current_user, get_optional_user, require_roles
from models import User, ShopListing, ShopListingCreate, ConsumerOrder, ConsumerOrderCreate
from emailer import send_email, wrap_email
from repayment import auto_debit_on_credit

router = APIRouter(prefix="/api/shop", tags=["shop"])
log = logging.getLogger("helix.shop")

RIBY_PARTNER = "Riby Inc"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- Listings ----------

@router.get("/listings")
async def list_listings(
    category: str | None = None,
    fulfillment: str | None = None,
    search: str | None = None,
):
    q: dict = {"status": "active", "stock_qty": {"$gt": 0}}
    if category:
        q["category"] = category
    if fulfillment:
        q["fulfillment_mode"] = fulfillment
    if search:
        q["title"] = {"$regex": search, "$options": "i"}
    items = await db.shop_listings.find(q, {"_id": 0}).sort("created_at", -1).to_list(200)
    # decorate with seller info
    for it in items:
        biz = await db.businesses.find_one({"id": it["owner_business_id"]}, {"_id": 0})
        it["seller_name"] = biz.get("business_name") if biz else "Helix Seller"
        it["seller_country"] = biz.get("country") if biz else ""
    return items


@router.get("/listings/mine")
async def my_listings(user: User = Depends(get_current_user)):
    if not user.business_id:
        return []
    items = await db.shop_listings.find({"owner_business_id": user.business_id}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return items


@router.get("/listings/{lid}")
async def get_listing(lid: str):
    it = await db.shop_listings.find_one({"id": lid}, {"_id": 0})
    if not it:
        raise HTTPException(404)
    biz = await db.businesses.find_one({"id": it["owner_business_id"]}, {"_id": 0})
    it["seller"] = {
        "business_name": biz.get("business_name") if biz else "",
        "country": biz.get("country") if biz else "",
        "compliance_score": biz.get("compliance_score") if biz else 0,
    }
    return it


@router.post("/listings", response_model=ShopListing)
async def create_listing(payload: ShopListingCreate, user: User = Depends(get_current_user)):
    if not user.business_id:
        raise HTTPException(400, "Create a business profile first")
    biz = await db.businesses.find_one({"id": user.business_id}, {"_id": 0})
    if not biz:
        raise HTTPException(400, "Business missing")
    # Guardrails — exporter can only list DTC, buyer can only list local
    if user.role == "exporter" and payload.fulfillment_mode != "riby_dtc":
        raise HTTPException(400, "Exporters can only create riby_dtc listings (Riby Inc is delivery partner of record)")
    if user.role == "buyer" and payload.fulfillment_mode != "buyer_local":
        raise HTTPException(400, "Buyers list from their local inventory (buyer_local)")
    if user.role not in ("exporter", "buyer", "admin", "super_admin"):
        raise HTTPException(403, "Only exporters and buyers can list")

    listing = ShopListing(
        owner_business_id=user.business_id,
        country_of_origin="Nigeria" if user.role == "exporter" else (biz.get("country") or "United States"),
        ships_from=payload.ships_from or (biz.get("address") or ""),
        delivery_partner_of_record=RIBY_PARTNER if payload.fulfillment_mode == "riby_dtc" else "",
        **payload.model_dump(),
    )
    doc = listing.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.shop_listings.insert_one(doc)
    return listing


@router.patch("/listings/{lid}", response_model=ShopListing)
async def update_listing(lid: str, payload: dict, user: User = Depends(get_current_user)):
    it = await db.shop_listings.find_one({"id": lid}, {"_id": 0})
    if not it:
        raise HTTPException(404)
    if it["owner_business_id"] != user.business_id and user.role not in ("admin", "super_admin"):
        raise HTTPException(403)
    allowed = {"title", "description", "photos", "category", "retail_price_usd", "stock_qty", "ships_from", "status"}
    update = {k: v for k, v in payload.items() if k in allowed}
    if update:
        await db.shop_listings.update_one({"id": lid}, {"$set": update})
    it = await db.shop_listings.find_one({"id": lid}, {"_id": 0})
    return ShopListing(**it)


@router.delete("/listings/{lid}")
async def delete_listing(lid: str, user: User = Depends(get_current_user)):
    it = await db.shop_listings.find_one({"id": lid}, {"_id": 0})
    if not it:
        raise HTTPException(404)
    if it["owner_business_id"] != user.business_id and user.role not in ("admin", "super_admin"):
        raise HTTPException(403)
    await db.shop_listings.delete_one({"id": lid})
    return {"status": "deleted"}


# ---------- Consumer orders ----------

@router.post("/orders")
async def place_order(payload: ConsumerOrderCreate, user: User = Depends(get_current_user)):
    """Simulated consumer checkout — immediate payment, creates seller USD credit."""
    if user.role not in ("consumer", "buyer", "exporter", "admin", "super_admin"):
        raise HTTPException(403, "Sign in required")

    listing = await db.shop_listings.find_one({"id": payload.listing_id}, {"_id": 0})
    if not listing:
        raise HTTPException(404, "Listing not found")
    if listing["status"] != "active" or listing["stock_qty"] < payload.quantity:
        raise HTTPException(400, "Not enough stock")

    total = round(listing["retail_price_usd"] * payload.quantity, 2)
    order_id = str(uuid.uuid4())
    payment_ref = f"shop_pay_{uuid.uuid4().hex[:14]}"

    order = {
        "id": order_id,
        "order_number": f"SHP-{uuid.uuid4().hex[:8].upper()}",
        "consumer_user_id": user.user_id,
        "listing_id": listing["id"],
        "listing_title": listing["title"],
        "quantity": payload.quantity,
        "unit_price_usd": listing["retail_price_usd"],
        "total_usd": total,
        "seller_business_id": listing["owner_business_id"],
        "fulfillment_mode": listing["fulfillment_mode"],
        "delivery_partner_of_record": listing.get("delivery_partner_of_record") or (RIBY_PARTNER if listing["fulfillment_mode"] == "riby_dtc" else ""),
        "shipping_name": payload.shipping_name,
        "shipping_address": payload.shipping_address,
        "shipping_email": payload.shipping_email,
        "shipping_phone": payload.shipping_phone,
        "status": "paid",
        "tracking_number": None,
        "payment_ref": payment_ref,
        "created_at": _now_iso(),
    }
    await db.consumer_orders.insert_one(order)
    order.pop("_id", None)

    # decrement stock
    new_stock = listing["stock_qty"] - payload.quantity
    listing_update = {"stock_qty": new_stock}
    if new_stock <= 0:
        listing_update["status"] = "out_of_stock"
    await db.shop_listings.update_one({"id": listing["id"]}, {"$set": listing_update})

    # credit seller USD (net of 2% Helix platform fee on retail)
    fee = round(total * 0.02, 2)
    credit_amount = round(total - fee, 2)
    biz = await db.businesses.find_one({"id": listing["owner_business_id"]}, {"_id": 0})
    if biz:
        await db.transactions.insert_many([
            {
                "id": str(uuid.uuid4()),
                "business_id": biz["id"],
                "anchor_transaction_ref": f"shop_{uuid.uuid4().hex[:12]}",
                "type": "credit",
                "amount": credit_amount,
                "currency": "USD",
                "status": "completed",
                "anchor_event_type": "shop.order.paid",
                "description": f"Consumer sale · {order['order_number']} · {listing['title']}",
                "counterparty": user.user_id,
                "timestamp": _now_iso(),
            },
            {
                "id": str(uuid.uuid4()),
                "business_id": biz["id"],
                "anchor_transaction_ref": f"shop_fee_{uuid.uuid4().hex[:10]}",
                "type": "fee",
                "amount": fee,
                "currency": "USD",
                "status": "completed",
                "anchor_event_type": "shop.fee.applied",
                "description": f"Helix marketplace fee (2%) · {order['order_number']}",
                "timestamp": _now_iso(),
            },
        ])
        # JompStart auto-debit if outstanding credit
        await auto_debit_on_credit(biz["id"], source_description=f"Consumer order {order['order_number']}")

    # Notify seller owner
    owner = await db.users.find_one({"user_id": biz["owner_user_id"]}, {"_id": 0}) if biz else None
    if owner:
        dpor_line = f"<p>Delivery partner of record: <b>{order['delivery_partner_of_record'] or 'Buyer (local)'}</b></p>" if order["delivery_partner_of_record"] else ""
        await send_email(
            owner["email"],
            f"New consumer order — {order['order_number']}",
            wrap_email(
                "Consumer order received",
                f"<p>You have a new direct-to-consumer order.</p>"
                f"<p><b>{listing['title']}</b><br/>Qty: {payload.quantity}<br/>Amount: USD {total:,.2f}<br/>Credit to your USD wallet: USD {credit_amount:,.2f}</p>"
                f"<p>Ship to: {payload.shipping_name}, {payload.shipping_address}</p>{dpor_line}",
                cta_label="View in fulfillment queue", cta_url="/fulfillment",
            ),
        )
    return order


@router.get("/orders/mine")
async def my_consumer_orders(user: User = Depends(get_current_user)):
    items = await db.consumer_orders.find({"consumer_user_id": user.user_id}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return items


@router.get("/orders/fulfillment")
async def fulfillment_queue(user: User = Depends(get_current_user)):
    if not user.business_id:
        return []
    items = await db.consumer_orders.find({"seller_business_id": user.business_id}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return items


@router.post("/orders/{oid}/ship")
async def ship_order(oid: str, payload: dict, user: User = Depends(get_current_user)):
    o = await db.consumer_orders.find_one({"id": oid}, {"_id": 0})
    if not o:
        raise HTTPException(404)
    if o["seller_business_id"] != user.business_id and user.role not in ("admin", "super_admin"):
        raise HTTPException(403)
    tracking = payload.get("tracking_number", f"TRK{uuid.uuid4().hex[:10].upper()}")
    await db.consumer_orders.update_one({"id": oid}, {"$set": {"status": "shipped", "tracking_number": tracking}})
    # Notify consumer
    consumer = await db.users.find_one({"user_id": o["consumer_user_id"]}, {"_id": 0})
    if consumer:
        dpor = f"<p>Fulfilled via <b>{o['delivery_partner_of_record']}</b> as delivery partner of record.</p>" if o["delivery_partner_of_record"] else ""
        await send_email(
            consumer["email"],
            f"Your order has shipped — {o['order_number']}",
            wrap_email(
                "Your Helix Shop order has shipped",
                f"<p><b>{o['listing_title']}</b></p>"
                f"<p>Tracking: <span style='font-family:monospace'>{tracking}</span></p>{dpor}",
                cta_label="View order", cta_url="/shop/orders",
            ),
        )
    return {"status": "ok", "tracking_number": tracking}


@router.post("/orders/{oid}/delivered")
async def mark_delivered(oid: str, user: User = Depends(get_current_user)):
    o = await db.consumer_orders.find_one({"id": oid}, {"_id": 0})
    if not o:
        raise HTTPException(404)
    if o["seller_business_id"] != user.business_id and user.role not in ("admin", "super_admin"):
        raise HTTPException(403)
    await db.consumer_orders.update_one({"id": oid}, {"$set": {"status": "delivered"}})
    return {"status": "ok"}


# ---------- Source: inventory from delivered trade orders ----------

@router.get("/inventory/source-orders")
async def available_source_orders(user: User = Depends(get_current_user)):
    """Delivered/shipped trade orders the buyer has received and can re-list."""
    if user.role != "buyer" or not user.business_id:
        return []
    items = await db.orders.find(
        {"buyer_id": user.business_id, "status": {"$in": ["delivered", "shipped", "in_production", "ready_to_ship"]}, "payment_status": "confirmed"},
        {"_id": 0},
    ).sort("created_at", -1).to_list(500)
    return items
