"""Jomp Shop — consumer e-commerce + Riby Inc escrow + quote flow.

Two listing fulfillment modes:
- buyer_local: Buyer (importer) lists local US inventory.
- riby_dtc: Exporter sells DTC; Riby Inc is Delivery Partner of Record.

Two consumer checkout modes:
- order_prepay: buyer pays listed price immediately → escrow held by Riby Inc → released on delivery.
- quote_prepay: consumer requests a quote; seller responds; consumer accepts and prepays → escrow.

Escrow: funds DO NOT credit the seller at checkout. They sit in Riby Inc's escrow ledger
and release on `mark_delivered` (by seller) or `confirm_delivery` (by consumer). JompStart
auto-debit fires at escrow RELEASE (not at payment), reflecting real cash flow.
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from db import db
from auth import get_current_user, get_optional_user
from models import (
    User, ShopListing, ShopListingCreate, ConsumerOrder, ConsumerOrderCreate,
    QuoteRequest, QuoteRequestCreate, QuoteRespond,
)
from emailer import send_email, wrap_email
from repayment import auto_debit_on_credit

router = APIRouter(prefix="/api/shop", tags=["shop"])
log = logging.getLogger("helix.shop")

RIBY_PARTNER = "Riby Inc"
ESCROW_HOLDER = "Riby Inc (US Escrow)"
PLATFORM_FEE_RATE = 0.02  # 2% Jomp Trade marketplace fee


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
    for it in items:
        biz = await db.businesses.find_one({"id": it["owner_business_id"]}, {"_id": 0})
        it["seller_name"] = biz.get("business_name") if biz else "Jomp Seller"
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
    if user.role == "exporter" and payload.fulfillment_mode != "riby_dtc":
        raise HTTPException(400, "Exporters can only create riby_dtc listings (Riby Inc is delivery partner of record)")
    if user.role == "buyer" and payload.fulfillment_mode != "buyer_local":
        raise HTTPException(400, "Buyers list from their local inventory (buyer_local)")
    if user.role not in ("exporter", "buyer", "admin", "super_admin"):
        raise HTTPException(403, "Only exporters and buyers can list")

    data = payload.model_dump()
    data.pop("ships_from", None)
    listing = ShopListing(
        owner_business_id=user.business_id,
        country_of_origin="Nigeria" if user.role == "exporter" else (biz.get("country") or "United States"),
        ships_from=payload.ships_from or (biz.get("address") or ""),
        delivery_partner_of_record=RIBY_PARTNER if payload.fulfillment_mode == "riby_dtc" else "",
        **data,
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


# ---------- Quote requests ----------

@router.post("/quotes")
async def create_quote(payload: QuoteRequestCreate, user: User = Depends(get_current_user)):
    if user.role not in ("consumer", "admin", "super_admin"):
        raise HTTPException(403, "Only consumers can request quotes on Jomp Shop")
    listing = await db.shop_listings.find_one({"id": payload.listing_id}, {"_id": 0})
    if not listing:
        raise HTTPException(404, "Listing not found")
    if listing["owner_business_id"] == user.business_id:
        raise HTTPException(400, "You cannot request a quote on your own listing")
    q = QuoteRequest(
        consumer_user_id=user.user_id,
        consumer_email=user.email,
        consumer_name=user.name,
        listing_id=listing["id"],
        listing_title=listing["title"],
        seller_business_id=listing["owner_business_id"],
        quantity=payload.quantity,
        message=payload.message,
    )
    doc = q.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    await db.quote_requests.insert_one(doc)

    # notify seller
    biz = await db.businesses.find_one({"id": listing["owner_business_id"]}, {"_id": 0})
    if biz:
        owner = await db.users.find_one({"user_id": biz["owner_user_id"]}, {"_id": 0})
        if owner:
            await send_email(
                owner["email"],
                f"New quote request — {q.quote_number}",
                wrap_email(
                    "Consumer quote request",
                    f"<p>A consumer has requested a quote for <b>{listing['title']}</b>.</p>"
                    f"<p>Qty: <b>{payload.quantity}</b><br/>From: {user.name} &lt;{user.email}&gt;</p>"
                    f"<p><i>{payload.message or '—'}</i></p>",
                    cta_label="Respond with quote", cta_url="/fulfillment",
                ),
            )
    return q


@router.get("/quotes/mine")
async def my_quotes(user: User = Depends(get_current_user)):
    # consumer side
    as_consumer = await db.quote_requests.find({"consumer_user_id": user.user_id}, {"_id": 0}).sort("created_at", -1).to_list(500)
    # seller side
    as_seller = []
    if user.business_id:
        as_seller = await db.quote_requests.find({"seller_business_id": user.business_id}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"as_consumer": as_consumer, "as_seller": as_seller}


@router.get("/quotes/{qid}")
async def get_quote(qid: str, user: User = Depends(get_current_user)):
    q = await db.quote_requests.find_one({"id": qid}, {"_id": 0})
    if not q:
        raise HTTPException(404)
    if q["consumer_user_id"] != user.user_id and q["seller_business_id"] != user.business_id and user.role not in ("admin", "super_admin"):
        raise HTTPException(403)
    return q


@router.post("/quotes/{qid}/respond")
async def respond_to_quote(qid: str, payload: QuoteRespond, user: User = Depends(get_current_user)):
    q = await db.quote_requests.find_one({"id": qid}, {"_id": 0})
    if not q:
        raise HTTPException(404)
    if q["seller_business_id"] != user.business_id and user.role not in ("admin", "super_admin"):
        raise HTTPException(403)
    quoted_total = round(payload.quoted_unit_price_usd * q["quantity"], 2)
    valid_until = (datetime.now(timezone.utc) + timedelta(days=payload.valid_days)).date().isoformat()
    update = {
        "quoted_unit_price_usd": payload.quoted_unit_price_usd,
        "quoted_total_usd": quoted_total,
        "quote_note": payload.quote_note or "",
        "quote_valid_until": valid_until,
        "status": "quoted",
        "updated_at": _now_iso(),
    }
    await db.quote_requests.update_one({"id": qid}, {"$set": update})

    # notify consumer
    consumer = await db.users.find_one({"user_id": q["consumer_user_id"]}, {"_id": 0})
    if consumer:
        await send_email(
            consumer["email"],
            f"Your quote is ready — {q['quote_number']}",
            wrap_email(
                "Your Jomp Shop quote",
                f"<p>The seller has responded to your quote for <b>{q['listing_title']}</b>.</p>"
                f"<p>Quoted: <b>USD {quoted_total:,.2f}</b> (USD {payload.quoted_unit_price_usd:,.2f} × {q['quantity']})<br/>"
                f"Valid until: {valid_until}</p>"
                f"<p>{payload.quote_note or ''}</p>",
                cta_label="Review & accept", cta_url="/shop/orders",
            ),
        )
    return {"status": "ok", "quoted_total_usd": quoted_total, "valid_until": valid_until}


@router.post("/quotes/{qid}/decline")
async def decline_quote(qid: str, user: User = Depends(get_current_user)):
    q = await db.quote_requests.find_one({"id": qid}, {"_id": 0})
    if not q:
        raise HTTPException(404)
    if q["consumer_user_id"] != user.user_id:
        raise HTTPException(403)
    if q["status"] not in ("pending", "quoted"):
        raise HTTPException(400, f"Cannot decline a quote in status '{q['status']}'")
    await db.quote_requests.update_one({"id": qid}, {"$set": {"status": "declined", "updated_at": _now_iso()}})
    return {"status": "declined"}


# ---------- Consumer orders (escrow-first) ----------

@router.post("/orders")
async def place_order(payload: ConsumerOrderCreate, user: User = Depends(get_current_user)):
    """Checkout with Riby Inc escrow. Funds held until delivery.

    Two modes:
    - order_prepay: use listing price.
    - quote_prepay: use price from an accepted QuoteRequest (payload.quote_id).
    """
    if user.role not in ("consumer", "buyer", "exporter", "admin", "super_admin"):
        raise HTTPException(403, "Sign in required")

    listing = await db.shop_listings.find_one({"id": payload.listing_id}, {"_id": 0})
    if not listing:
        raise HTTPException(404, "Listing not found")

    # Resolve unit price + checkout mode
    checkout_mode = "order_prepay"
    quoted_quote_id = None
    unit_price = listing["retail_price_usd"]
    qty = payload.quantity

    if payload.quote_id:
        q = await db.quote_requests.find_one({"id": payload.quote_id}, {"_id": 0})
        if not q:
            raise HTTPException(404, "Quote not found")
        if q["consumer_user_id"] != user.user_id:
            raise HTTPException(403, "This quote belongs to another user")
        if q["listing_id"] != listing["id"]:
            raise HTTPException(400, "Quote does not match listing")
        if q["status"] != "quoted":
            raise HTTPException(400, f"Quote not ready (status: {q['status']})")
        if q.get("quote_valid_until") and q["quote_valid_until"] < datetime.now(timezone.utc).date().isoformat():
            raise HTTPException(400, "Quote has expired")
        if payload.quantity != q["quantity"]:
            raise HTTPException(400, f"Quantity mismatch — quote is for {q['quantity']} units, checkout requested {payload.quantity}")
        unit_price = q["quoted_unit_price_usd"]
        qty = q["quantity"]
        checkout_mode = "quote_prepay"
        quoted_quote_id = q["id"]

    total = round(unit_price * qty, 2)

    # Atomic stock decrement
    decremented = await db.shop_listings.find_one_and_update(
        {"id": listing["id"], "status": "active", "stock_qty": {"$gte": qty}},
        {"$inc": {"stock_qty": -qty}},
        return_document=True,
        projection={"_id": 0},
    )
    if not decremented:
        raise HTTPException(400, "Not enough stock")
    if decremented["stock_qty"] <= 0:
        await db.shop_listings.update_one({"id": listing["id"]}, {"$set": {"status": "out_of_stock"}})

    payment_ref = f"shop_pay_{uuid.uuid4().hex[:14]}"
    order_id = str(uuid.uuid4())
    order = {
        "id": order_id,
        "order_number": f"SHP-{uuid.uuid4().hex[:8].upper()}",
        "consumer_user_id": user.user_id,
        "listing_id": listing["id"],
        "listing_title": listing["title"],
        "quantity": qty,
        "unit_price_usd": unit_price,
        "total_usd": total,
        "seller_business_id": listing["owner_business_id"],
        "fulfillment_mode": listing["fulfillment_mode"],
        "delivery_partner_of_record": listing.get("delivery_partner_of_record") or (RIBY_PARTNER if listing["fulfillment_mode"] == "riby_dtc" else ""),
        "shipping_name": payload.shipping_name,
        "shipping_address": payload.shipping_address,
        "shipping_email": payload.shipping_email,
        "shipping_phone": payload.shipping_phone,
        "checkout_mode": checkout_mode,
        "quote_id": quoted_quote_id,
        "status": "paid",
        "escrow_status": "held",
        "escrow_held_by": ESCROW_HOLDER,
        "escrow_released_at": None,
        "tracking_number": None,
        "payment_ref": payment_ref,
        "created_at": _now_iso(),
    }
    await db.consumer_orders.insert_one(order)
    order.pop("_id", None)

    # Mark quote converted
    if quoted_quote_id:
        await db.quote_requests.update_one({"id": quoted_quote_id}, {"$set": {"status": "converted", "updated_at": _now_iso()}})

    # ---- Escrow ledger (NO seller credit yet) ----
    escrow_doc = {
        "id": str(uuid.uuid4()),
        "order_id": order_id,
        "order_number": order["order_number"],
        "beneficiary_business_id": listing["owner_business_id"],
        "consumer_user_id": user.user_id,
        "amount_usd": total,
        "held_by": ESCROW_HOLDER,
        "status": "held",  # held | released | refunded
        "created_at": _now_iso(),
        "released_at": None,
        "release_tx_id": None,
        "fee_tx_id": None,
    }
    await db.escrow_holdings.insert_one(escrow_doc)

    # notify seller (order received — funds in escrow)
    biz = await db.businesses.find_one({"id": listing["owner_business_id"]}, {"_id": 0})
    owner = await db.users.find_one({"user_id": biz["owner_user_id"]}, {"_id": 0}) if biz else None
    if owner:
        dpor_line = f"<p>Delivery partner of record: <b>{order['delivery_partner_of_record'] or 'Buyer (local)'}</b></p>" if order["delivery_partner_of_record"] else ""
        await send_email(
            owner["email"],
            f"New consumer order — {order['order_number']} (funds in escrow)",
            wrap_email(
                "Consumer order received — funds in escrow",
                f"<p>You have a new consumer order.</p>"
                f"<p><b>{listing['title']}</b><br/>Qty: {qty}<br/>Amount: USD {total:,.2f}</p>"
                f"<p>Funds (<b>USD {total:,.2f}</b>) are held in escrow by <b>Riby Inc</b> and will release to your USD wallet "
                f"(net of the 2% marketplace fee) once the order is marked <b>delivered</b>.</p>"
                f"<p>Ship to: {payload.shipping_name}, {payload.shipping_address}</p>{dpor_line}",
                cta_label="View in fulfillment queue", cta_url="/fulfillment",
            ),
        )

    return order


async def _release_escrow(order: dict, triggered_by: str) -> dict:
    """Release held escrow to seller → credit USD (gross) + fee debit (2%). Idempotent.

    Ledger: credit_tx records the gross inflow (total_usd) and a separate fee_tx
    debits the 2% marketplace fee, so seller's net USD balance delta is exactly total * 0.98.
    """
    if order["escrow_status"] != "held":
        return {"released": False, "reason": "already released"}

    total = float(order["total_usd"])
    fee = round(total * PLATFORM_FEE_RATE, 2)
    net_amount = round(total - fee, 2)
    seller_biz_id = order["seller_business_id"]

    # credit_tx = gross inflow; fee_tx = -2% marketplace fee debit.
    credit_tx = {
        "id": str(uuid.uuid4()),
        "business_id": seller_biz_id,
        "anchor_transaction_ref": f"escrow_rel_{uuid.uuid4().hex[:12]}",
        "type": "credit",
        "amount": total,
        "currency": "USD",
        "status": "completed",
        "anchor_event_type": "escrow.released",
        "description": f"Escrow release · {order['order_number']} (gross)",
        "counterparty": ESCROW_HOLDER,
        "timestamp": _now_iso(),
    }
    fee_tx = {
        "id": str(uuid.uuid4()),
        "business_id": seller_biz_id,
        "anchor_transaction_ref": f"shop_fee_{uuid.uuid4().hex[:10]}",
        "type": "fee",
        "amount": fee,
        "currency": "USD",
        "status": "completed",
        "anchor_event_type": "shop.fee.applied",
        "description": f"Jomp marketplace fee (2%) · {order['order_number']}",
        "timestamp": _now_iso(),
    }
    await db.transactions.insert_many([credit_tx, fee_tx])

    await db.consumer_orders.update_one(
        {"id": order["id"]},
        {"$set": {"status": "delivered", "escrow_status": "released", "escrow_released_at": _now_iso()}},
    )
    await db.escrow_holdings.update_one(
        {"order_id": order["id"]},
        {"$set": {"status": "released", "released_at": _now_iso(), "release_tx_id": credit_tx["id"], "fee_tx_id": fee_tx["id"]}},
    )

    # JompStart auto-debit (best effort)
    debit = None
    try:
        debit = await auto_debit_on_credit(seller_biz_id, source_description=f"Escrow release {order['order_number']}")
    except Exception as e:
        log.exception("auto-debit failed: %s", e)

    log.info("escrow released: order=%s gross=%s net=%s fee=%s triggered_by=%s", order["order_number"], total, net_amount, fee, triggered_by)
    return {"released": True, "credit_amount_usd": net_amount, "gross_amount_usd": total, "fee_usd": fee, "jompstart_auto_debit": debit}


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
    tracking = payload.get("tracking_number") or f"TRK{uuid.uuid4().hex[:10].upper()}"
    await db.consumer_orders.update_one({"id": oid}, {"$set": {"status": "shipped", "tracking_number": tracking}})
    consumer = await db.users.find_one({"user_id": o["consumer_user_id"]}, {"_id": 0})
    if consumer:
        dpor = f"<p>Fulfilled via <b>{o['delivery_partner_of_record']}</b> as delivery partner of record.</p>" if o["delivery_partner_of_record"] else ""
        await send_email(
            consumer["email"],
            f"Your order has shipped — {o['order_number']}",
            wrap_email(
                "Your Jomp Shop order has shipped",
                f"<p><b>{o['listing_title']}</b></p>"
                f"<p>Tracking: <span style='font-family:monospace'>{tracking}</span></p>{dpor}"
                f"<p>Once you receive your order, tap <b>Confirm Delivery</b> in your orders to release escrow to the seller.</p>",
                cta_label="View order", cta_url="/shop/orders",
            ),
        )
    return {"status": "ok", "tracking_number": tracking}


@router.post("/orders/{oid}/delivered")
async def seller_mark_delivered(oid: str, user: User = Depends(get_current_user)):
    """Seller marks delivered → release escrow to seller."""
    o = await db.consumer_orders.find_one({"id": oid}, {"_id": 0})
    if not o:
        raise HTTPException(404)
    if o["seller_business_id"] != user.business_id and user.role not in ("admin", "super_admin"):
        raise HTTPException(403)
    # Status flip happens inside _release_escrow (only when escrow was 'held')
    release = await _release_escrow(o, triggered_by=f"seller:{user.user_id}")
    return {"status": "ok", **release}


@router.post("/orders/{oid}/confirm-delivery")
async def consumer_confirm_delivery(oid: str, user: User = Depends(get_current_user)):
    """Consumer confirms receipt → release escrow."""
    o = await db.consumer_orders.find_one({"id": oid}, {"_id": 0})
    if not o:
        raise HTTPException(404)
    if o["consumer_user_id"] != user.user_id:
        raise HTTPException(403)
    release = await _release_escrow(o, triggered_by=f"consumer:{user.user_id}")
    return {"status": "ok", **release}


# ---------- Source: inventory from delivered trade orders ----------

@router.get("/inventory/source-orders")
async def available_source_orders(user: User = Depends(get_current_user)):
    if user.role != "buyer" or not user.business_id:
        return []
    items = await db.orders.find(
        {"buyer_id": user.business_id, "status": {"$in": ["delivered", "shipped", "in_production", "ready_to_ship"]}, "payment_status": "confirmed"},
        {"_id": 0},
    ).sort("created_at", -1).to_list(500)
    return items


# ---------- Riby escrow overview (admin) ----------

@router.get("/escrow/overview")
async def escrow_overview(user: User = Depends(get_current_user)):
    if user.role not in ("admin", "super_admin"):
        raise HTTPException(403)
    items = await db.escrow_holdings.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    held = [i for i in items if i["status"] == "held"]
    total_held = round(sum(i["amount_usd"] for i in held), 2)
    total_released = round(sum(i["amount_usd"] for i in items if i["status"] == "released"), 2)
    return {
        "total_held_usd": total_held,
        "total_released_usd": total_released,
        "held_count": len(held),
        "released_count": len([i for i in items if i["status"] == "released"]),
        "recent": items[:50],
    }
