"""Order / trade management routes."""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from db import db
from auth import get_current_user, require_roles
from models import Order, RFQCreate, User
from anchor_client import create_reserved_account
from emailer import send_email, wrap_email
from pdf_gen import (
    proforma_invoice_pdf, commercial_invoice_pdf, packing_list_pdf, certificate_of_origin_pdf,
)
from repayment import auto_debit_on_credit

router = APIRouter(prefix="/api", tags=["orders"])
log = logging.getLogger("helix.orders")

LIFECYCLE = ["draft", "confirmed", "in_production", "ready_to_ship", "shipped", "delivered"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("/rfq")
async def submit_rfq(payload: RFQCreate, user: User = Depends(get_current_user)):
    """Buyer submits RFQ -> creates Order(status=draft, pending supplier proforma)."""
    if not user.business_id:
        raise HTTPException(400, "Create a business profile first")
    prod = await db.products.find_one({"id": payload.product_id}, {"_id": 0})
    if not prod:
        raise HTTPException(404, "Product not found")
    supplier_biz = await db.businesses.find_one({"id": prod["business_id"]}, {"_id": 0})
    if not supplier_biz:
        raise HTTPException(404, "Supplier not found")
    supplier_user = await db.users.find_one({"user_id": supplier_biz["owner_user_id"]}, {"_id": 0})

    unit_price = float(prod["price_usd"])
    order = Order(
        buyer_id=user.business_id,
        supplier_id=supplier_biz["id"],
        buyer_user_id=user.user_id,
        supplier_user_id=supplier_biz["owner_user_id"],
        product_id=prod["id"],
        product_name=prod["name"],
        quantity=payload.quantity,
        unit_price_usd=unit_price,
        agreed_price_usd=unit_price * payload.quantity,
        status="draft",
        delivery_address=payload.delivery_address,
        target_delivery_date=payload.target_delivery_date,
        message=payload.message or "",
        timeline=[{"at": _now_iso(), "event": "rfq_submitted", "by": user.user_id}],
    )
    doc = order.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    await db.orders.insert_one(doc)

    # notify supplier
    if supplier_user:
        await send_email(
            supplier_user["email"],
            f"New RFQ — {order.order_number}",
            wrap_email("New Request for Quotation",
                       f"<p>A buyer has submitted an RFQ for <b>{prod['name']}</b>.</p>"
                       f"<p>Quantity: <b>{payload.quantity}</b><br/>Estimated: <b>USD {order.agreed_price_usd:,.2f}</b></p>"
                       f"<p>Message: <i>{payload.message or '—'}</i></p>",
                       cta_label="Review RFQ", cta_url=f"/orders/{order.id}"),
        )
    return order


@router.post("/orders/{oid}/proforma")
async def issue_proforma(oid: str, user: User = Depends(get_current_user)):
    """Supplier confirms & issues proforma. Triggers reserved-account creation."""
    o = await db.orders.find_one({"id": oid}, {"_id": 0})
    if not o:
        raise HTTPException(404, "Order not found")
    if o["supplier_user_id"] != user.user_id and user.role not in ("admin", "super_admin"):
        raise HTTPException(403, "Only supplier can issue proforma")
    if o["status"] not in ("draft",):
        raise HTTPException(400, "Proforma already issued")

    supplier_biz = await db.businesses.find_one({"id": o["supplier_id"]}, {"_id": 0})
    # reserved account (USD) for buyer payment
    anchor_cust_id = supplier_biz.get("anchor_customer_id")
    if anchor_cust_id:
        res = create_reserved_account(o["id"], anchor_cust_id, o["agreed_price_usd"], currency="USD")
        reserved_id = res["id"]
        reserved_acct_number = res["account_number"]
    else:
        reserved_id, reserved_acct_number = None, None

    timeline = o.get("timeline", []) + [{"at": _now_iso(), "event": "proforma_issued", "by": user.user_id}]
    await db.orders.update_one(
        {"id": oid},
        {"$set": {
            "status": "confirmed",
            "anchor_reserved_account_id": reserved_id,
            "anchor_reserved_account_number": reserved_acct_number,
            "timeline": timeline,
            "updated_at": _now_iso(),
        }},
    )
    # Notify buyer
    buyer_user = await db.users.find_one({"user_id": o["buyer_user_id"]}, {"_id": 0})
    if buyer_user:
        await send_email(
            buyer_user["email"],
            f"Proforma Ready — {o['order_number']}",
            wrap_email(
                "Proforma Invoice Issued",
                f"<p>Your order <b>{o['order_number']}</b> has been confirmed and a proforma invoice is ready.</p>"
                f"<p>Virtual Account: <b style='font-family:monospace'>{reserved_acct_number or '—'}</b><br/>"
                f"Amount Due: <b>USD {o['agreed_price_usd']:,.2f}</b></p>",
                cta_label="View Payment Instructions", cta_url=f"/orders/{oid}",
            ),
        )
    o = await db.orders.find_one({"id": oid}, {"_id": 0})
    return Order(**o)


@router.post("/orders/{oid}/confirm")
async def buyer_confirm(oid: str, user: User = Depends(get_current_user)):
    """Buyer confirms order (marks they will pay)."""
    o = await db.orders.find_one({"id": oid}, {"_id": 0})
    if not o:
        raise HTTPException(404)
    if o["buyer_user_id"] != user.user_id:
        raise HTTPException(403)
    tl = o.get("timeline", []) + [{"at": _now_iso(), "event": "buyer_confirmed", "by": user.user_id}]
    await db.orders.update_one({"id": oid}, {"$set": {"timeline": tl, "updated_at": _now_iso()}})
    return {"status": "ok"}


@router.post("/orders/{oid}/status")
async def update_status(oid: str, payload: dict, user: User = Depends(get_current_user)):
    new_status = payload.get("status")
    if new_status not in LIFECYCLE + ["disputed"]:
        raise HTTPException(400, "Invalid status")
    o = await db.orders.find_one({"id": oid}, {"_id": 0})
    if not o:
        raise HTTPException(404)
    if user.user_id not in (o["supplier_user_id"], o["buyer_user_id"]) and user.role not in ("admin", "super_admin"):
        raise HTTPException(403)
    tl = o.get("timeline", []) + [{"at": _now_iso(), "event": f"status:{new_status}", "by": user.user_id}]
    await db.orders.update_one({"id": oid}, {"$set": {"status": new_status, "timeline": tl, "updated_at": _now_iso()}})
    return {"status": "ok", "new_status": new_status}


@router.get("/orders/mine")
async def my_orders(user: User = Depends(get_current_user)):
    if not user.business_id:
        return []
    q = {"$or": [{"buyer_id": user.business_id}, {"supplier_id": user.business_id}]}
    items = await db.orders.find(q, {"_id": 0}).sort("created_at", -1).to_list(500)
    return items


@router.get("/orders/{oid}")
async def get_order(oid: str, user: User = Depends(get_current_user)):
    o = await db.orders.find_one({"id": oid}, {"_id": 0})
    if not o:
        raise HTTPException(404)
    if user.user_id not in (o["supplier_user_id"], o["buyer_user_id"]) and user.role not in ("admin", "super_admin"):
        raise HTTPException(403)
    supplier = await db.businesses.find_one({"id": o["supplier_id"]}, {"_id": 0})
    buyer = await db.businesses.find_one({"id": o["buyer_id"]}, {"_id": 0})
    product = await db.products.find_one({"id": o["product_id"]}, {"_id": 0})
    return {"order": o, "supplier": supplier, "buyer": buyer, "product": product}


# ---------- PDFs ----------

async def _load_parties(oid: str):
    o = await db.orders.find_one({"id": oid}, {"_id": 0})
    if not o:
        raise HTTPException(404)
    supplier = await db.businesses.find_one({"id": o["supplier_id"]}, {"_id": 0})
    buyer = await db.businesses.find_one({"id": o["buyer_id"]}, {"_id": 0})
    seller = {"name": supplier["business_name"], "address": supplier.get("address") or "", "country": supplier.get("country") or ""}
    byr = {"name": buyer["business_name"], "address": buyer.get("address") or "", "country": buyer.get("country") or ""}
    return o, seller, byr


@router.get("/orders/{oid}/pdf/{doc_type}")
async def order_pdf(oid: str, doc_type: str, user: User = Depends(get_current_user)):
    o, seller, buyer = await _load_parties(oid)
    if user.user_id not in (o["supplier_user_id"], o["buyer_user_id"]) and user.role not in ("admin", "super_admin"):
        raise HTTPException(403)
    if doc_type == "proforma":
        pdf = proforma_invoice_pdf(o, seller, buyer)
    elif doc_type == "commercial":
        pdf = commercial_invoice_pdf(o, seller, buyer)
    elif doc_type == "packing":
        pdf = packing_list_pdf(o, seller, buyer)
    elif doc_type == "origin":
        pdf = certificate_of_origin_pdf(o, seller, buyer)
    else:
        raise HTTPException(400, "Unknown document type")
    filename = f"{o['order_number']}-{doc_type}.pdf"
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


# ---------- Payment simulation (mock) ----------

@router.post("/orders/{oid}/simulate-payment")
async def simulate_payment(oid: str, user: User = Depends(get_current_user)):
    """DEV ONLY: emulate an Anchor account.credited webhook for a given order.
    In mock mode, this is how buyers confirm their payment landed.
    """
    o = await db.orders.find_one({"id": oid}, {"_id": 0})
    if not o:
        raise HTTPException(404)
    if o["payment_status"] == "confirmed":
        return {"status": "already_confirmed"}
    # create a transaction (credit to supplier USD)
    tx = {
        "id": str(uuid.uuid4()),
        "business_id": o["supplier_id"],
        "order_id": oid,
        "anchor_transaction_ref": f"anchor_tx_{uuid.uuid4().hex[:16]}",
        "type": "credit",
        "amount": o["agreed_price_usd"],
        "currency": "USD",
        "status": "completed",
        "anchor_event_type": "account.credited",
        "description": f"Payment received for order {o['order_number']}",
        "counterparty": o["buyer_id"],
        "timestamp": _now_iso(),
    }
    await db.transactions.insert_one(tx)

    # fee (1% platform fee) on supplier side
    fee_amount = round(o["agreed_price_usd"] * 0.01, 2)
    fee_tx = {
        "id": str(uuid.uuid4()),
        "business_id": o["supplier_id"],
        "order_id": oid,
        "anchor_transaction_ref": f"fee_{uuid.uuid4().hex[:12]}",
        "type": "fee",
        "amount": fee_amount,
        "currency": "USD",
        "status": "completed",
        "anchor_event_type": "fee.applied",
        "description": f"Helix platform fee (1%) on order {o['order_number']}",
        "timestamp": _now_iso(),
    }
    await db.transactions.insert_one(fee_tx)

    tl = o.get("timeline", []) + [
        {"at": _now_iso(), "event": "payment_received", "by": "anchor_webhook_mock"},
        {"at": _now_iso(), "event": "fee_applied", "by": "system", "detail": f"USD {fee_amount}"},
    ]
    await db.orders.update_one({"id": oid}, {"$set": {"payment_status": "confirmed", "status": "in_production" if o["status"] == "confirmed" else o["status"], "timeline": tl, "updated_at": _now_iso()}})

    supplier_user = await db.users.find_one({"user_id": o["supplier_user_id"]}, {"_id": 0})
    if supplier_user:
        await send_email(
            supplier_user["email"],
            f"Payment Received — {o['order_number']}",
            wrap_email(
                "Payment Confirmed",
                f"<p>Payment of <b>USD {o['agreed_price_usd']:,.2f}</b> has been received for order <b>{o['order_number']}</b>.</p>"
                f"<p>Platform fee (1%): USD {fee_amount:.2f}</p>"
                f"<p>Funds have been credited to your USD account.</p>",
                cta_label="View Order", cta_url=f"/orders/{oid}",
            ),
        )
    # JompStart auto-debit against outstanding credit (if any) — best effort
    debit_tx = None
    try:
        debit_tx = await auto_debit_on_credit(o["supplier_id"], source_description=f"Order {o['order_number']}")
    except Exception as e:
        log.exception("auto-debit failed: %s", e)
    return {"status": "confirmed", "amount": o["agreed_price_usd"], "fee": fee_amount, "jompstart_auto_debit": debit_tx}


# ---------- Disputes ----------

@router.post("/orders/{oid}/dispute")
async def raise_dispute(oid: str, payload: dict, user: User = Depends(get_current_user)):
    o = await db.orders.find_one({"id": oid}, {"_id": 0})
    if not o:
        raise HTTPException(404)
    if user.user_id not in (o["supplier_user_id"], o["buyer_user_id"]):
        raise HTTPException(403)
    dispute = {
        "id": str(uuid.uuid4()),
        "order_id": oid,
        "raised_by_user_id": user.user_id,
        "raised_by_business_id": user.business_id or "",
        "reason": payload.get("reason", "Unspecified"),
        "description": payload.get("description", ""),
        "evidence_urls": payload.get("evidence_urls", []),
        "status": "open",
        "created_at": _now_iso(),
    }
    await db.disputes.insert_one(dispute)
    tl = o.get("timeline", []) + [{"at": _now_iso(), "event": "dispute_raised", "by": user.user_id}]
    await db.orders.update_one({"id": oid}, {"$set": {"status": "disputed", "timeline": tl, "updated_at": _now_iso()}})
    return dispute


@router.get("/admin/disputes", dependencies=[Depends(require_roles("admin", "super_admin"))])
async def list_disputes():
    items = await db.disputes.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return items


@router.post("/admin/disputes/{did}/resolve", dependencies=[Depends(require_roles("admin", "super_admin"))])
async def resolve_dispute(did: str, payload: dict):
    resolution = payload.get("resolution", "")
    status = payload.get("status", "resolved")
    await db.disputes.update_one({"id": did}, {"$set": {"status": status, "resolution": resolution}})
    return {"status": "ok"}
