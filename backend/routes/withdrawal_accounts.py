"""Pre-approved withdrawal account management + USD/NGN withdrawal flows.

Merchants register their bank accounts (NGN or USD) once; the platform "approves"
them (mocked auto-approval on save in sandbox) and they become re-usable
destinations for withdrawals — no need to retype bank details on every transfer.
"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from db import db
from auth import get_current_user
from models import User
from anchor_client import initiate_nip_transfer
from emailer import send_email, wrap_email

router = APIRouter(prefix="/api/finance", tags=["finance-withdrawals"])
log = logging.getLogger("helix.withdrawals")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Reuse balance helper from finance.py without circular import
async def _balance_for(business_id: str, currency: str) -> float:
    """Compute balance via server-side aggregation (matches finance.py)."""
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


# ----------------------------------------------------------------------------
# Withdrawal accounts CRUD
# ----------------------------------------------------------------------------

NGN_BANKS = {
    "058": "Guaranty Trust Bank (GTBank)",
    "044": "Access Bank",
    "011": "First Bank of Nigeria",
    "033": "United Bank for Africa (UBA)",
    "057": "Zenith Bank",
    "070": "Fidelity Bank",
    "232": "Sterling Bank",
    "221": "Stanbic IBTC",
    "076": "Polaris Bank",
    "035": "Wema Bank",
}


def _validate_account_payload(payload: dict) -> dict:
    """Normalize and validate account creation payload.

    Returns a clean account doc (without id/created_at/business_id) for storage.
    Raises HTTPException(400) on invalid input.
    """
    currency = (payload.get("currency") or "").upper()
    if currency not in ("NGN", "USD"):
        raise HTTPException(400, "currency must be NGN or USD")
    label = (payload.get("label") or "").strip() or "My account"
    account_name = (payload.get("account_name") or "").strip()
    if not account_name:
        raise HTTPException(400, "account_name (account holder) is required")

    doc: dict = {
        "currency": currency,
        "label": label,
        "account_name": account_name,
        "is_default": bool(payload.get("is_default", False)),
        "country": payload.get("country") or ("Nigeria" if currency == "NGN" else "United States"),
    }

    if currency == "NGN":
        bank_code = (payload.get("bank_code") or "").strip()
        account_number = (payload.get("account_number") or "").strip()
        if bank_code not in NGN_BANKS:
            raise HTTPException(400, f"Invalid Nigerian bank_code; one of {','.join(NGN_BANKS.keys())}")
        if not account_number.isdigit() or len(account_number) != 10:
            raise HTTPException(400, "NGN account_number must be 10 digits")
        doc["bank_code"] = bank_code
        doc["bank_name"] = NGN_BANKS[bank_code]
        doc["account_number"] = account_number
    else:  # USD
        bank_name = (payload.get("bank_name") or "").strip()
        routing_number = (payload.get("routing_number") or "").strip()
        account_number = (payload.get("account_number") or "").strip()
        account_type = (payload.get("account_type") or "checking").lower()
        swift_code = (payload.get("swift_code") or "").strip().upper()
        if not bank_name:
            raise HTTPException(400, "bank_name is required for USD accounts")
        if routing_number and (not routing_number.isdigit() or len(routing_number) != 9):
            raise HTTPException(400, "routing_number must be 9 digits (US ACH)")
        if not account_number or len(account_number) < 4:
            raise HTTPException(400, "account_number is required (≥ 4 digits)")
        if account_type not in ("checking", "savings"):
            raise HTTPException(400, "account_type must be 'checking' or 'savings'")
        doc["bank_name"] = bank_name
        doc["routing_number"] = routing_number
        doc["account_number"] = account_number
        doc["account_type"] = account_type
        doc["swift_code"] = swift_code  # optional, for international wires
    return doc


def _mask(account_number: str) -> str:
    if not account_number:
        return ""
    if len(account_number) <= 4:
        return account_number
    return "•••• " + account_number[-4:]


@router.get("/withdrawal-accounts")
async def list_accounts(user: User = Depends(get_current_user), currency: str | None = None):
    if not user.business_id:
        return []
    q: dict = {"business_id": user.business_id, "is_active": True}
    if currency:
        q["currency"] = currency.upper()
    items = await db.withdrawal_accounts.find(q, {"_id": 0}).sort("created_at", -1).to_list(200)
    for it in items:
        it["account_number_masked"] = _mask(it.get("account_number", ""))
    return items


@router.post("/withdrawal-accounts")
async def create_account(payload: dict, user: User = Depends(get_current_user)):
    if not user.business_id:
        raise HTTPException(400, "Create a business profile first")
    doc = _validate_account_payload(payload)

    # If setting as default, unset others of same currency
    if doc["is_default"]:
        await db.withdrawal_accounts.update_many(
            {"business_id": user.business_id, "currency": doc["currency"]},
            {"$set": {"is_default": False}},
        )

    full = {
        "id": str(uuid.uuid4()),
        "business_id": user.business_id,
        "is_active": True,
        # mock pre-approval: in sandbox we auto-approve once basic validation passes.
        "approval_status": "approved",
        "approved_at": _now_iso(),
        "created_at": _now_iso(),
        **doc,
    }
    await db.withdrawal_accounts.insert_one(full)
    full.pop("_id", None)
    full["account_number_masked"] = _mask(full["account_number"])
    return full


@router.patch("/withdrawal-accounts/{aid}")
async def update_account(aid: str, payload: dict, user: User = Depends(get_current_user)):
    acc = await db.withdrawal_accounts.find_one({"id": aid, "business_id": user.business_id}, {"_id": 0})
    if not acc:
        raise HTTPException(404)
    update: dict = {}
    if "label" in payload and isinstance(payload["label"], str):
        update["label"] = payload["label"].strip() or acc["label"]
    if "is_default" in payload:
        if payload["is_default"]:
            await db.withdrawal_accounts.update_many(
                {"business_id": user.business_id, "currency": acc["currency"]},
                {"$set": {"is_default": False}},
            )
        update["is_default"] = bool(payload["is_default"])
    if "is_active" in payload:
        update["is_active"] = bool(payload["is_active"])
    if update:
        update["updated_at"] = _now_iso()
        await db.withdrawal_accounts.update_one({"id": aid}, {"$set": update})
    out = await db.withdrawal_accounts.find_one({"id": aid}, {"_id": 0})
    out["account_number_masked"] = _mask(out.get("account_number", ""))
    return out


@router.delete("/withdrawal-accounts/{aid}")
async def delete_account(aid: str, user: User = Depends(get_current_user)):
    acc = await db.withdrawal_accounts.find_one({"id": aid, "business_id": user.business_id}, {"_id": 0})
    if not acc:
        raise HTTPException(404)
    # Soft delete — keep history of past withdrawals tied to this account.
    await db.withdrawal_accounts.update_one({"id": aid}, {"$set": {"is_active": False, "updated_at": _now_iso()}})
    return {"status": "deactivated"}


# ----------------------------------------------------------------------------
# Withdrawal initiation (uses pre-approved account_id)
# ----------------------------------------------------------------------------

@router.post("/withdraw-from-account")
async def withdraw_from_account(payload: dict, user: User = Depends(get_current_user)):
    """Initiate a withdrawal using a pre-approved account.

    Body: {"withdrawal_account_id": "...", "amount": 100.0, "narration": "..."}
    Currency is inferred from the account.
    """
    if not user.business_id:
        raise HTTPException(400)
    aid = payload.get("withdrawal_account_id")
    if not aid:
        raise HTTPException(400, "withdrawal_account_id is required")
    acc = await db.withdrawal_accounts.find_one(
        {"id": aid, "business_id": user.business_id, "is_active": True},
        {"_id": 0},
    )
    if not acc:
        raise HTTPException(404, "Withdrawal account not found or inactive")
    if acc.get("approval_status") != "approved":
        raise HTTPException(400, "Withdrawal account is not approved yet")

    amount = float(payload.get("amount") or 0)
    if amount <= 0:
        raise HTTPException(400, "Amount must be > 0")
    bal = await _balance_for(user.business_id, acc["currency"])
    if amount > bal:
        raise HTTPException(400, f"Insufficient {acc['currency']} balance (available: {bal:,.2f})")

    narration = (payload.get("narration") or f"Jomp Shop {acc['currency']} withdrawal").strip()

    # Real transfer rail per currency
    if acc["currency"] == "NGN":
        biz = await db.businesses.find_one({"id": user.business_id}, {"_id": 0})
        if not biz.get("anchor_account_ngn"):
            raise HTTPException(400, "NGN virtual account not provisioned")
        res = initiate_nip_transfer(
            biz["anchor_account_ngn"], amount, acc["bank_code"], acc["account_number"], narration,
        )
        rail = "NIP"
        ref = f"{acc['bank_name']} • {_mask(acc['account_number'])}"
    else:
        # USD ACH/Wire — mocked in sandbox; real Anchor flow would be initiate_book_transfer or
        # an outbound payout once Anchor adds USD payouts. For sandbox we synth a tx ref.
        biz = await db.businesses.find_one({"id": user.business_id}, {"_id": 0})
        if not biz.get("anchor_account_usd"):
            raise HTTPException(400, "USD virtual account not provisioned")
        res = {
            "id": f"anchor_usd_payout_{uuid.uuid4().hex[:14]}",
            "status": "pending",
            "rail": "ACH",
            "amount": amount,
            "currency": "USD",
            "destination": {
                "bank_name": acc["bank_name"],
                "routing_number": acc.get("routing_number"),
                "account_number_masked": _mask(acc["account_number"]),
                "account_type": acc.get("account_type"),
            },
        }
        rail = "ACH" if acc.get("routing_number") else "WIRE"
        ref = f"{acc['bank_name']} • {_mask(acc['account_number'])} ({rail})"
        log.info("[MOCK] USD payout initiated %s amount=%s acc=%s", res["id"], amount, _mask(acc["account_number"]))

    tx = {
        "id": str(uuid.uuid4()),
        "business_id": user.business_id,
        "anchor_transaction_ref": res["id"],
        "type": "transfer",
        "amount": amount,
        "currency": acc["currency"],
        "status": res.get("status", "pending"),
        "anchor_event_type": "transfer.initiated",
        "description": f"Withdrawal · {ref}",
        "counterparty": ref,
        "withdrawal_account_id": acc["id"],
        "withdrawal_rail": rail,
        "narration": narration,
        "timestamp": _now_iso(),
    }
    await db.transactions.insert_one(tx)

    # Email confirmation
    user_doc = await db.users.find_one({"user_id": user.user_id}, {"_id": 0})
    if user_doc:
        amt_fmt = f"{acc['currency']} {amount:,.2f}"
        await send_email(
            user_doc["email"],
            f"Withdrawal initiated — {amt_fmt}",
            wrap_email(
                f"{acc['currency']} withdrawal initiated",
                f"<p>A withdrawal of <b>{amt_fmt}</b> has been initiated to your pre-approved account:</p>"
                f"<p><b>{acc['label']}</b><br/>{acc['bank_name']}<br/>"
                f"Account: <span style='font-family:monospace'>{_mask(acc['account_number'])}</span><br/>"
                f"Rail: {rail}</p>"
                f"<p>Reference: <span style='font-family:monospace'>{res['id']}</span></p>",
            ),
        )

    return {"status": "ok", "transfer": res, "transaction_id": tx["id"], "rail": rail}


@router.get("/withdrawal-banks")
async def list_banks():
    """Static list of supported NGN banks (for frontend dropdowns)."""
    return [{"code": code, "name": name} for code, name in NGN_BANKS.items()]
