"""JompStart repayment utilities — amortized schedule + auto-debit hook."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone, timedelta, date

from db import db

log = logging.getLogger("helix.repayment")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def amortized_monthly_payment(principal: float, apr_pct: float, months: int) -> float:
    if months <= 0:
        return principal
    if apr_pct <= 0:
        return round(principal / months, 2)
    r = (apr_pct / 100) / 12
    m = (principal * r * (1 + r) ** months) / ((1 + r) ** months - 1)
    return round(m, 2)


def build_schedule(principal: float, apr_pct: float, months: int, start: date) -> list[dict]:
    monthly = amortized_monthly_payment(principal, apr_pct, months)
    r = (apr_pct / 100) / 12 if apr_pct > 0 else 0
    balance = principal
    out = []
    for i in range(1, months + 1):
        interest = round(balance * r, 2)
        principal_portion = round(monthly - interest, 2)
        if i == months:
            # adjust final to clear rounding drift
            principal_portion = round(balance, 2)
            monthly_i = round(principal_portion + interest, 2)
        else:
            monthly_i = monthly
        due = start + timedelta(days=30 * i)
        out.append({
            "installment_number": i,
            "due_date": due.isoformat(),
            "principal_usd": principal_portion,
            "interest_usd": interest,
            "total_due_usd": monthly_i,
        })
        balance = round(balance - principal_portion, 2)
    return out


async def create_schedule(application: dict) -> list[dict]:
    """Called after credit acceptance/disbursement."""
    principal = float(application["offered_amount_usd"])
    apr = float(application["offered_apr"] or application.get("indicative_apr") or 12)
    months = int(application["offered_term_months"] or application.get("term_months") or 6)
    start = datetime.now(timezone.utc).date()
    rows = build_schedule(principal, apr, months, start)
    docs = []
    for r in rows:
        docs.append({
            "id": str(uuid.uuid4()),
            "application_id": application["id"],
            "business_id": application["business_id"],
            "installment_number": r["installment_number"],
            "due_date": r["due_date"],
            "principal_usd": r["principal_usd"],
            "interest_usd": r["interest_usd"],
            "total_due_usd": r["total_due_usd"],
            "paid_usd": 0,
            "status": "pending",
            "paid_at": None,
            "created_at": _now_iso(),
        })
    await db.repayment_installments.insert_many(docs)
    return docs


async def next_due_installment(business_id: str):
    return await db.repayment_installments.find_one(
        {"business_id": business_id, "status": {"$in": ["pending", "partial", "overdue"]}},
        {"_id": 0},
        sort=[("due_date", 1)],
    )


async def auto_debit_on_credit(business_id: str, source_description: str = "Incoming USD", cap_ratio: float = 1.0):
    """Called after any completed USD credit tx on business ledger.
    Applies up to `cap_ratio * next_installment.total_due_usd` from available balance
    toward the next-due JompStart installment. Idempotent per installment.
    Returns the debit transaction dict if applied, else None.
    """
    # Find current USD balance (recompute)
    txs = await db.transactions.find(
        {"business_id": business_id, "currency": "USD", "status": "completed"}, {"_id": 0}
    ).to_list(10000)
    bal = 0.0
    for t in txs:
        if t["type"] == "credit":
            bal += t["amount"]
        else:
            bal -= t["amount"]
    if bal <= 0:
        return None

    inst = await next_due_installment(business_id)
    if not inst:
        return None

    remaining = round(inst["total_due_usd"] - inst["paid_usd"], 2)
    if remaining <= 0:
        return None

    apply_amount = round(min(remaining, bal * cap_ratio), 2)
    if apply_amount <= 0:
        return None

    # record debit tx
    tx = {
        "id": str(uuid.uuid4()),
        "business_id": business_id,
        "anchor_transaction_ref": f"jomp_debit_{uuid.uuid4().hex[:12]}",
        "type": "debit",
        "amount": apply_amount,
        "currency": "USD",
        "status": "completed",
        "anchor_event_type": "jompstart.repayment.auto_debit",
        "description": f"JompStart auto-debit · installment #{inst['installment_number']} ({source_description})",
        "counterparty": "JompStart Digital",
        "timestamp": _now_iso(),
    }
    await db.transactions.insert_one(tx)

    # update installment
    new_paid = round(inst["paid_usd"] + apply_amount, 2)
    new_status = "paid" if new_paid >= inst["total_due_usd"] - 0.01 else "partial"
    paid_at = _now_iso() if new_status == "paid" else None
    await db.repayment_installments.update_one(
        {"id": inst["id"]},
        {"$set": {"paid_usd": new_paid, "status": new_status, "paid_at": paid_at}},
    )

    tx.pop("_id", None)
    log.info("JompStart auto-debit applied: biz=%s inst#%s amount=%s", business_id, inst["installment_number"], apply_amount)
    return tx


async def mark_overdue_installments():
    """Mark pending/partial installments past due_date as overdue."""
    today = datetime.now(timezone.utc).date().isoformat()
    await db.repayment_installments.update_many(
        {"status": {"$in": ["pending", "partial"]}, "due_date": {"$lt": today}},
        {"$set": {"status": "overdue"}},
    )
