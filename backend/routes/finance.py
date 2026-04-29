"""Financial management routes (Anchor-powered)."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from db import db
from auth import get_current_user, require_roles
from models import User
from anchor_client import (
    initiate_nip_transfer, initiate_book_transfer, verify_transfer, apply_fee,
)
from emailer import send_email, wrap_email

router = APIRouter(prefix="/api", tags=["finance"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _balance_for(business_id: str, currency: str) -> float:
    """Compute balance from ledger transactions via aggregation (server-side, scalable)."""
    pipeline = [
        {"$match": {"business_id": business_id, "currency": currency, "status": "completed"}},
        {"$group": {
            "_id": None,
            "credits": {"$sum": {"$cond": [{"$eq": ["$type", "credit"]}, "$amount", 0]}},
            "debits": {"$sum": {"$cond": [{"$in": ["$type", ["debit", "transfer", "fee"]]}, "$amount", 0]}},
        }},
    ]
    result = await db.transactions.aggregate(pipeline).to_list(1)
    if not result:
        return 0.0
    return round(result[0]["credits"] - result[0]["debits"], 2)


@router.get("/finance/dashboard")
async def dashboard(user: User = Depends(get_current_user)):
    if not user.business_id:
        return {"ngn_balance": 0, "usd_balance": 0, "recent_transactions": [], "virtual_accounts": {}}
    biz = await db.businesses.find_one({"id": user.business_id}, {"_id": 0})
    ngn = await _balance_for(user.business_id, "NGN")
    usd = await _balance_for(user.business_id, "USD")
    recent = await db.transactions.find({"business_id": user.business_id}, {"_id": 0}).sort("timestamp", -1).limit(10).to_list(10)
    return {
        "ngn_balance": ngn,
        "usd_balance": usd,
        "recent_transactions": recent,
        "virtual_accounts": {
            "ngn": {"account_number": biz.get("anchor_ngn_virtual_account"), "account_id": biz.get("anchor_account_ngn"), "bank": "Anchor Sandbox Bank"},
            "usd": {"account_number": biz.get("anchor_usd_virtual_account"), "account_id": biz.get("anchor_account_usd"), "bank": "Anchor USD FBO Riby Inc"},
        },
        "anchor_customer_id": biz.get("anchor_customer_id"),
        "kyc_status": biz.get("kyc_status"),
        "kyb_status": biz.get("kyb_status"),
    }


@router.get("/finance/transactions")
async def transactions(
    user: User = Depends(get_current_user),
    currency: str | None = None,
    type: str | None = None,
    limit: int = 200,
):
    if not user.business_id:
        return []
    q = {"business_id": user.business_id}
    if currency:
        q["currency"] = currency
    if type:
        q["type"] = type
    items = await db.transactions.find(q, {"_id": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
    return items


@router.post("/finance/withdraw")
async def withdraw(payload: dict, user: User = Depends(get_current_user)):
    """NIP transfer from exporter NGN wallet to their Nigerian bank."""
    if not user.business_id:
        raise HTTPException(400)
    biz = await db.businesses.find_one({"id": user.business_id}, {"_id": 0})
    if not biz.get("anchor_account_ngn"):
        raise HTTPException(400, "NGN account not provisioned yet")

    amount = float(payload.get("amount", 0))
    dest_bank_code = payload.get("bank_code", "")
    dest_account = payload.get("account_number", "")
    narration = payload.get("narration", "Helix withdrawal")
    if amount <= 0:
        raise HTTPException(400, "Amount must be > 0")

    bal = await _balance_for(user.business_id, "NGN")
    if amount > bal:
        raise HTTPException(400, f"Insufficient NGN balance (available: {bal:,.2f})")

    res = initiate_nip_transfer(biz["anchor_account_ngn"], amount, dest_bank_code, dest_account, narration)

    # record debit
    tx = {
        "id": str(uuid.uuid4()),
        "business_id": user.business_id,
        "anchor_transaction_ref": res["id"],
        "type": "transfer",
        "amount": amount,
        "currency": "NGN",
        "status": res.get("status", "pending"),
        "anchor_event_type": "transfer.completed",
        "description": f"Withdrawal to {dest_bank_code} / {dest_account}",
        "counterparty": dest_account,
        "timestamp": _now_iso(),
    }
    await db.transactions.insert_one(tx)

    await send_email(
        (await db.users.find_one({"user_id": user.user_id}, {"_id": 0}))["email"],
        "Withdrawal processed",
        wrap_email("Withdrawal processed",
                   f"<p>A withdrawal of <b>NGN {amount:,.2f}</b> has been processed to account <b>{dest_account}</b>.</p>"
                   f"<p>Reference: <span style='font-family:monospace'>{res['id']}</span></p>"),
    )
    return {"status": "ok", "transfer": res, "transaction_id": tx["id"]}


@router.post("/finance/book-transfer")
async def book_transfer(payload: dict, user: User = Depends(get_current_user)):
    """Internal transfer between two Anchor deposit accounts (e.g. NGN<->USD swap stub, or escrow release)."""
    if not user.business_id:
        raise HTTPException(400)
    biz = await db.businesses.find_one({"id": user.business_id}, {"_id": 0})
    src = payload.get("source_account_id") or biz.get("anchor_account_usd")
    dest = payload.get("dest_account_id")
    amount = float(payload.get("amount", 0))
    currency = payload.get("currency", "USD")
    narration = payload.get("narration", "Internal transfer")
    if not dest or amount <= 0:
        raise HTTPException(400, "dest_account_id and amount required")
    res = initiate_book_transfer(src, dest, amount, currency, narration)
    tx = {
        "id": str(uuid.uuid4()),
        "business_id": user.business_id,
        "anchor_transaction_ref": res["id"],
        "type": "transfer",
        "amount": amount,
        "currency": currency,
        "status": res.get("status", "completed"),
        "anchor_event_type": "transfer.completed",
        "description": narration,
        "timestamp": _now_iso(),
    }
    await db.transactions.insert_one(tx)
    return {"status": "ok", "transfer": res}


@router.get("/admin/finance/overview", dependencies=[Depends(require_roles("admin", "super_admin"))])
async def admin_overview():
    txs = await db.transactions.find({}, {"_id": 0}).to_list(10000)
    total_by_ccy: dict = {}
    for t in txs:
        total_by_ccy.setdefault(t["currency"], 0)
        if t["type"] == "credit":
            total_by_ccy[t["currency"]] += t["amount"]
    fees = [t for t in txs if t["type"] == "fee"]
    fee_total = sum(t["amount"] for t in fees)
    orders = await db.orders.find({}, {"_id": 0}).to_list(10000)
    by_sector: dict = {}
    for o in orders:
        prod = await db.products.find_one({"id": o["product_id"]}, {"_id": 0})
        cat = prod["category"] if prod else "general-goods"
        by_sector.setdefault(cat, {"count": 0, "volume_usd": 0})
        by_sector[cat]["count"] += 1
        by_sector[cat]["volume_usd"] += o["agreed_price_usd"]
    businesses = await db.businesses.count_documents({})
    return {
        "total_volume_by_currency": total_by_ccy,
        "fees_collected_usd": round(fee_total, 2),
        "by_sector": by_sector,
        "order_count": len(orders),
        "business_count": businesses,
        "transaction_count": len(txs),
    }
