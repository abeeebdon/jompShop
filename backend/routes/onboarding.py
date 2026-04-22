"""Onboarding & business verification routes."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from db import db
from auth import get_current_user, require_roles
from models import Business, BusinessCreate, User
from anchor_client import (
    create_business_customer, create_individual_customer, submit_kyb, submit_kyc,
    create_deposit_account,
)
from emailer import send_email, wrap_email

router = APIRouter(prefix="/api", tags=["onboarding"])
log = logging.getLogger("helix.onboarding")


def _clean(doc: dict) -> dict:
    doc.pop("_id", None)
    return doc


@router.post("/businesses", response_model=Business)
async def create_business(payload: BusinessCreate, user: User = Depends(get_current_user)):
    # one business per user for MVP
    existing = await db.businesses.find_one({"owner_user_id": user.user_id}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Business already exists for this user")

    # CAC / BVN / EIN validation
    if payload.country.lower() in ("nigeria", "ng"):
        if payload.registration_type == "business" and payload.cac_number and not payload.cac_number.strip():
            raise HTTPException(status_code=400, detail="CAC number required")
        if payload.bvn and not (payload.bvn.isdigit() and len(payload.bvn) == 11):
            raise HTTPException(status_code=400, detail="BVN must be 11 digits")
    if payload.country.lower() in ("united states", "us", "usa") and payload.ein:
        # EIN format: XX-XXXXXXX
        clean_ein = payload.ein.replace("-", "").replace(" ", "")
        if not (clean_ein.isdigit() and len(clean_ein) == 9):
            raise HTTPException(status_code=400, detail="EIN must be 9 digits")

    # call Anchor to create customer
    anchor_payload = {"name": payload.business_name, "email": payload.contact_email or user.email}
    if payload.registration_type == "business":
        anchor_res = create_business_customer(anchor_payload)
    else:
        anchor_res = create_individual_customer(anchor_payload)

    biz = Business(
        owner_user_id=user.user_id,
        anchor_customer_id=anchor_res.get("id"),
        **payload.model_dump(),
    )
    doc = biz.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    await db.businesses.insert_one(doc)

    # link user
    await db.users.update_one(
        {"user_id": user.user_id},
        {"$set": {"business_id": biz.id, "role": payload.role}},
    )
    return biz


@router.get("/businesses/me", response_model=Business | None)
async def my_business(user: User = Depends(get_current_user)):
    doc = await db.businesses.find_one({"owner_user_id": user.user_id}, {"_id": 0})
    return Business(**doc) if doc else None


@router.post("/businesses/{bid}/kyc")
async def submit_kyc_endpoint(bid: str, payload: dict, user: User = Depends(get_current_user)):
    biz_doc = await db.businesses.find_one({"id": bid}, {"_id": 0})
    if not biz_doc:
        raise HTTPException(404, "Business not found")
    if biz_doc["owner_user_id"] != user.user_id and user.role not in ("admin", "super_admin"):
        raise HTTPException(403, "Forbidden")
    # payload: { docs: [storage_path, ...], nin, bvn }
    docs = payload.get("docs", [])
    if biz_doc.get("anchor_customer_id"):
        submit_kyc(biz_doc["anchor_customer_id"], {"documents": docs})
    await db.businesses.update_one(
        {"id": bid},
        {"$set": {
            "kyc_docs": docs,
            "kyc_status": "under_review",
            "bvn": payload.get("bvn", biz_doc.get("bvn")),
            "nin": payload.get("nin", biz_doc.get("nin")),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    return {"status": "submitted", "kyc_status": "under_review"}


@router.post("/businesses/{bid}/kyb")
async def submit_kyb_endpoint(bid: str, payload: dict, user: User = Depends(get_current_user)):
    biz_doc = await db.businesses.find_one({"id": bid}, {"_id": 0})
    if not biz_doc:
        raise HTTPException(404, "Business not found")
    if biz_doc["owner_user_id"] != user.user_id and user.role not in ("admin", "super_admin"):
        raise HTTPException(403, "Forbidden")
    docs = payload.get("docs", [])
    if biz_doc.get("anchor_customer_id"):
        submit_kyb(biz_doc["anchor_customer_id"], {"documents": docs, "cac": biz_doc.get("cac_number")})
    await db.businesses.update_one(
        {"id": bid},
        {"$set": {
            "kyb_docs": docs,
            "kyb_status": "under_review",
            "cac_number": payload.get("cac_number", biz_doc.get("cac_number")),
            "tin": payload.get("tin", biz_doc.get("tin")),
            "director_name": payload.get("director_name", biz_doc.get("director_name")),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    return {"status": "submitted", "kyb_status": "under_review"}


# ---------- Admin review queue ----------

@router.get("/admin/verifications", dependencies=[Depends(require_roles("admin", "super_admin"))])
async def list_verifications():
    cursor = db.businesses.find(
        {"$or": [{"kyc_status": {"$in": ["pending", "under_review"]}}, {"kyb_status": {"$in": ["pending", "under_review"]}}]},
        {"_id": 0},
    )
    items = await cursor.to_list(500)
    return items


@router.post("/admin/verifications/{bid}/decide")
async def decide_verification(bid: str, payload: dict, user: User = Depends(require_roles("admin", "super_admin"))):
    decision = payload.get("decision")  # approved | rejected
    note = payload.get("note", "")
    if decision not in ("approved", "rejected"):
        raise HTTPException(400, "decision must be approved|rejected")

    biz = await db.businesses.find_one({"id": bid}, {"_id": 0})
    if not biz:
        raise HTTPException(404, "Not found")
    biz_obj = Business(**biz)

    update = {
        "kyc_status": decision if biz_obj.registration_type == "individual" else biz_obj.kyc_status,
        "kyb_status": decision if biz_obj.registration_type == "business" else biz_obj.kyb_status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    # If approved — auto-create Anchor NGN + USD deposit accounts (if not already)
    if decision == "approved" and biz_obj.anchor_customer_id and not biz_obj.anchor_account_ngn:
        ngn_acc = create_deposit_account(biz_obj.anchor_customer_id, "NGN")
        usd_acc = create_deposit_account(biz_obj.anchor_customer_id, "USD")
        update["anchor_account_ngn"] = ngn_acc["id"]
        update["anchor_account_usd"] = usd_acc["id"]
        update["anchor_ngn_virtual_account"] = ngn_acc["account_number"]
        update["anchor_usd_virtual_account"] = usd_acc["account_number"]

    await db.businesses.update_one({"id": bid}, {"$set": update})

    # notify user
    owner = await db.users.find_one({"user_id": biz_obj.owner_user_id}, {"_id": 0})
    if owner:
        title = "Verification Approved" if decision == "approved" else "Verification Needs Attention"
        body = (f"<p>Your business <b>{biz_obj.business_name}</b> has been <b>{decision.upper()}</b>.</p>"
                + (f"<p>{note}</p>" if note else "")
                + ("<p>Your NGN and USD accounts have been provisioned — you can start receiving payments.</p>"
                   if decision == "approved" else "<p>Please review your submission and resubmit your documents.</p>"))
        await send_email(owner["email"], f"Helix — {title}", wrap_email(title, body, cta_label="Open Helix", cta_url="/dashboard"))

    return {"status": "ok", "decision": decision}
