"""JompStart — Business Credit module.

Exporters can apply for credit to finance exports, with eligibility
derived from their successful sales records on Helix.
JompStart Digital Limited is the business credit partner.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException

from db import db
from auth import get_current_user, require_roles
from models import User
from emailer import send_email, wrap_email
from repayment import create_schedule, mark_overdue_installments

router = APIRouter(prefix="/api/credit", tags=["credit"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- eligibility engine ----------

async def _sales_history(business_id: str) -> dict:
    """Successful export sales = delivered OR paid orders for this supplier."""
    orders = await db.orders.find({"supplier_id": business_id}, {"_id": 0}).to_list(5000)
    paid_orders = [o for o in orders if o.get("payment_status") == "confirmed"]
    total_volume = sum(o.get("agreed_price_usd", 0) for o in paid_orders)
    delivered = [o for o in paid_orders if o.get("status") in ("delivered", "shipped", "in_production", "ready_to_ship")]
    return {
        "paid_order_count": len(paid_orders),
        "delivered_count": len(delivered),
        "total_volume_usd": round(total_volume, 2),
        "average_order_usd": round(total_volume / len(paid_orders), 2) if paid_orders else 0,
    }


async def _compute_eligibility(business_id: str) -> dict:
    biz = await db.businesses.find_one({"id": business_id}, {"_id": 0})
    if not biz:
        return {"eligible": False, "reason": "Business not found", "max_limit_usd": 0, "sales": {}, "score": 0}

    sales = await _sales_history(business_id)
    kyb_ok = biz.get("kyb_status") == "approved" or biz.get("kyc_status") == "approved"
    compliance = int(biz.get("compliance_score") or 0)
    volume = sales["total_volume_usd"]

    # Eligibility rules
    reasons: list[str] = []
    if not kyb_ok:
        reasons.append("KYB/KYC must be approved")
    if sales["paid_order_count"] < 1:
        reasons.append("At least 1 paid order on Helix is required")
    if compliance < 40:
        reasons.append("Compliance score must be ≥ 40")

    eligible = len(reasons) == 0

    # Credit limit formula: 40% of trailing volume, capped at $100k, plus compliance bonus
    base = min(volume * 0.4, 100_000)
    compliance_multiplier = 0.7 + (compliance / 100) * 0.6  # 0.7 → 1.3
    order_count_bonus = min(sales["paid_order_count"] * 500, 5000)
    max_limit = round((base * compliance_multiplier) + order_count_bonus, 2) if eligible else 0

    # Risk score 0–100
    score = 0
    if kyb_ok:
        score += 20
    score += min(sales["paid_order_count"] * 5, 30)
    score += int(compliance * 0.3)
    score += min(int(volume / 1000), 20)
    score = min(score, 100)

    # Indicative APR — 9% base + 20% max premium inversely scaled to score
    apr = round(9 + (100 - score) * 0.15, 2) if eligible else None

    return {
        "eligible": eligible,
        "reasons_blocked": reasons,
        "max_limit_usd": max_limit,
        "indicative_apr_percent": apr,
        "indicative_term_months": 6,
        "sales": sales,
        "compliance_score": compliance,
        "risk_score": score,
        "partner": "JompStart Digital Limited",
    }


# ---------- routes ----------

@router.get("/eligibility")
async def eligibility(user: User = Depends(get_current_user)):
    if not user.business_id:
        return {"eligible": False, "reason": "Create a business profile first", "max_limit_usd": 0, "partner": "JompStart Digital Limited"}
    return await _compute_eligibility(user.business_id)


@router.post("/applications")
async def create_application(payload: dict, user: User = Depends(get_current_user)):
    if not user.business_id:
        raise HTTPException(400, "Create a business profile first")
    elig = await _compute_eligibility(user.business_id)
    requested = float(payload.get("amount_usd") or 0)
    if requested <= 0:
        raise HTTPException(400, "amount_usd must be > 0")
    if not elig["eligible"]:
        raise HTTPException(400, f"Not eligible: {', '.join(elig['reasons_blocked'])}")
    if requested > elig["max_limit_usd"]:
        raise HTTPException(400, f"Exceeds indicative limit of ${elig['max_limit_usd']:,.2f}")

    app_doc = {
        "id": str(uuid.uuid4()),
        "application_number": f"JMP-{uuid.uuid4().hex[:8].upper()}",
        "business_id": user.business_id,
        "user_id": user.user_id,
        "amount_usd": round(requested, 2),
        "term_months": int(payload.get("term_months") or elig["indicative_term_months"]),
        "purpose": payload.get("purpose") or "Export production financing",
        "order_id": payload.get("order_id"),  # optional — tied to a specific order
        "indicative_apr": elig["indicative_apr_percent"],
        "risk_score": elig["risk_score"],
        "snapshot_sales": elig["sales"],
        "status": "submitted",  # submitted → under_review → offered → accepted → disbursed → repaying → closed | rejected
        "decision_note": None,
        "offered_apr": None,
        "offered_term_months": None,
        "offered_amount_usd": None,
        "timeline": [{"at": _now_iso(), "event": "submitted", "by": user.user_id}],
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    await db.credit_applications.insert_one(app_doc)
    app_doc.pop("_id", None)

    # Notify JompStart ops via in-app admin queue (email optional — the ops inbox is admins)
    admins = await db.users.find({"role": {"$in": ["admin", "super_admin"]}}, {"_id": 0}).to_list(50)
    for a in admins:
        await send_email(
            a["email"],
            f"[JompStart] New credit application — {app_doc['application_number']}",
            wrap_email(
                "New credit application",
                f"<p>A Helix exporter has submitted a credit application.</p>"
                f"<p><b>Amount:</b> USD {requested:,.2f}<br/>"
                f"<b>Term:</b> {app_doc['term_months']} months<br/>"
                f"<b>Risk score:</b> {elig['risk_score']}/100<br/>"
                f"<b>Indicative APR:</b> {elig['indicative_apr_percent']}%</p>",
                cta_label="Review application", cta_url="/admin/credit",
            ),
        )

    return app_doc


@router.get("/applications/mine")
async def my_applications(user: User = Depends(get_current_user)):
    if not user.business_id:
        return []
    items = await db.credit_applications.find({"business_id": user.business_id}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return items


@router.get("/applications/{aid}")
async def get_application(aid: str, user: User = Depends(get_current_user)):
    doc = await db.credit_applications.find_one({"id": aid}, {"_id": 0})
    if not doc:
        raise HTTPException(404)
    if doc["business_id"] != user.business_id and user.role not in ("admin", "super_admin"):
        raise HTTPException(403)
    return doc


@router.post("/applications/{aid}/accept")
async def accept_offer(aid: str, user: User = Depends(get_current_user)):
    doc = await db.credit_applications.find_one({"id": aid}, {"_id": 0})
    if not doc:
        raise HTTPException(404)
    if doc["business_id"] != user.business_id:
        raise HTTPException(403)
    if doc["status"] != "offered":
        raise HTTPException(400, "No offer to accept")
    now = _now_iso()
    # Simulate disbursement: credit supplier USD account (mock Anchor book transfer)
    tx_id = str(uuid.uuid4())
    await db.transactions.insert_one({
        "id": tx_id,
        "business_id": doc["business_id"],
        "anchor_transaction_ref": f"jomp_disb_{uuid.uuid4().hex[:12]}",
        "type": "credit",
        "amount": doc["offered_amount_usd"],
        "currency": "USD",
        "status": "completed",
        "anchor_event_type": "jompstart.credit.disbursed",
        "description": f"JompStart credit disbursement · {doc['application_number']}",
        "counterparty": "JompStart Digital",
        "timestamp": now,
    })
    tl = doc["timeline"] + [
        {"at": now, "event": "offer_accepted", "by": user.user_id},
        {"at": now, "event": "disbursed", "by": "jompstart_system"},
    ]
    await db.credit_applications.update_one(
        {"id": aid},
        {"$set": {
            "status": "disbursed",
            "disbursed_at": now,
            "disbursement_tx_id": tx_id,
            "timeline": tl,
            "updated_at": now,
        }},
    )
    # Generate repayment schedule
    refreshed = await db.credit_applications.find_one({"id": aid}, {"_id": 0})
    try:
        await create_schedule(refreshed)
    except Exception as e:
        # don't block accept on schedule generation
        import logging
        logging.getLogger("helix.credit").exception("schedule gen failed: %s", e)
    return {"status": "disbursed", "disbursement_tx_id": tx_id, "amount_usd": doc["offered_amount_usd"]}


# ---------- repayment ----------

@router.get("/applications/{aid}/repayment")
async def get_repayment(aid: str, user: User = Depends(get_current_user)):
    doc = await db.credit_applications.find_one({"id": aid}, {"_id": 0})
    if not doc:
        raise HTTPException(404)
    if doc["business_id"] != user.business_id and user.role not in ("admin", "super_admin", "jompstart_admin"):
        raise HTTPException(403)
    await mark_overdue_installments()
    items = await db.repayment_installments.find({"application_id": aid}, {"_id": 0}).sort("installment_number", 1).to_list(500)
    total_due = sum(i["total_due_usd"] for i in items)
    total_paid = sum(i["paid_usd"] for i in items)
    next_due = next((i for i in items if i["status"] in ("pending", "partial", "overdue")), None)
    return {
        "application": doc,
        "installments": items,
        "total_due_usd": round(total_due, 2),
        "total_paid_usd": round(total_paid, 2),
        "outstanding_usd": round(total_due - total_paid, 2),
        "next_due": next_due,
    }


@router.get("/repayments/mine")
async def my_repayments(user: User = Depends(get_current_user)):
    if not user.business_id:
        return {"applications": [], "total_outstanding_usd": 0}
    await mark_overdue_installments()
    # all disbursed apps
    apps = await db.credit_applications.find(
        {"business_id": user.business_id, "status": {"$in": ["disbursed"]}}, {"_id": 0}
    ).to_list(500)
    result = []
    total_outstanding = 0.0
    for a in apps:
        inst = await db.repayment_installments.find({"application_id": a["id"]}, {"_id": 0}).sort("installment_number", 1).to_list(500)
        due = sum(i["total_due_usd"] for i in inst)
        paid = sum(i["paid_usd"] for i in inst)
        outstanding = round(due - paid, 2)
        total_outstanding += outstanding
        next_due = next((i for i in inst if i["status"] in ("pending", "partial", "overdue")), None)
        result.append({
            "application": a,
            "installments": inst,
            "outstanding_usd": outstanding,
            "next_due": next_due,
        })
    return {"applications": result, "total_outstanding_usd": round(total_outstanding, 2)}


# ---------- admin ----------

@router.get("/admin/applications", dependencies=[Depends(require_roles("admin", "super_admin", "jompstart_admin"))])
async def admin_list():
    items = await db.credit_applications.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    # decorate with business name
    for it in items:
        biz = await db.businesses.find_one({"id": it["business_id"]}, {"_id": 0})
        it["business_name"] = biz.get("business_name") if biz else ""
        it["business_country"] = biz.get("country") if biz else ""
    return items


@router.post("/admin/applications/{aid}/decision", dependencies=[Depends(require_roles("admin", "super_admin", "jompstart_admin"))])
async def admin_decision(aid: str, payload: dict):
    """decision: offered | rejected.
    For offered: provide offered_amount_usd, offered_apr, offered_term_months, decision_note.
    """
    decision = payload.get("decision")
    if decision not in ("offered", "rejected"):
        raise HTTPException(400, "decision must be offered|rejected")
    doc = await db.credit_applications.find_one({"id": aid}, {"_id": 0})
    if not doc:
        raise HTTPException(404)

    update = {"status": decision, "updated_at": _now_iso(), "decision_note": payload.get("decision_note", "")}
    if decision == "offered":
        update["offered_amount_usd"] = float(payload.get("offered_amount_usd") or doc["amount_usd"])
        update["offered_apr"] = float(payload.get("offered_apr") or doc.get("indicative_apr") or 12)
        update["offered_term_months"] = int(payload.get("offered_term_months") or doc.get("term_months") or 6)

    tl = doc["timeline"] + [{"at": _now_iso(), "event": f"decision:{decision}"}]
    update["timeline"] = tl
    await db.credit_applications.update_one({"id": aid}, {"$set": update})

    # notify applicant
    applicant = await db.users.find_one({"user_id": doc["user_id"]}, {"_id": 0})
    if applicant:
        if decision == "offered":
            body = (
                f"<p>JompStart Digital has reviewed your application <b>{doc['application_number']}</b> and extended an offer:</p>"
                f"<ul>"
                f"<li>Amount: <b>USD {update['offered_amount_usd']:,.2f}</b></li>"
                f"<li>APR: <b>{update['offered_apr']}%</b></li>"
                f"<li>Term: <b>{update['offered_term_months']} months</b></li>"
                f"</ul>"
                f"<p>{payload.get('decision_note') or ''}</p>"
            )
            title = "Credit offer extended"
            cta = "Review & accept"
        else:
            body = f"<p>Your credit application <b>{doc['application_number']}</b> was not approved at this time.</p><p>{payload.get('decision_note') or ''}</p>"
            title = "Credit application update"
            cta = "Open Helix"
        await send_email(applicant["email"], f"Helix × JompStart — {title}", wrap_email(title, body, cta_label=cta, cta_url=f"/credit/{aid}"))

    return {"status": "ok", "decision": decision}
