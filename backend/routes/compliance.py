"""Compliance management routes."""
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException

from db import db
from auth import get_current_user, require_roles
from models import ComplianceDocument, User

router = APIRouter(prefix="/api", tags=["compliance"])


REQUIRED_BY_CATEGORY = {
    "fashion": ["SON Certification", "Country of Origin Label"],
    "agriculture": ["NAFDAC", "Phytosanitary Certificate", "Fumigation Certificate", "SON"],
    "staple-foods": ["NAFDAC", "FSSAI / FDA Equivalence", "Halal Certification (if applicable)"],
    "general-goods": ["SON Certification"],
}

GUIDE_BY_CATEGORY = {
    "fashion": [
        "US CBP: HTS classification required on commercial invoice.",
        "Country-of-origin labeling per 19 CFR 134.",
        "Textile Fiber Products Identification Act (TFPIA) labels.",
    ],
    "agriculture": [
        "USDA APHIS import permit for many agricultural products.",
        "FDA Prior Notice for food shipments.",
        "Phytosanitary certificate from origin country.",
    ],
    "staple-foods": [
        "FDA Facility Registration (FSMA).",
        "Prior Notice filed before arrival.",
        "Foreign Supplier Verification Program (FSVP) compliance.",
    ],
    "general-goods": [
        "CBP classification & duty determination.",
        "Manufacturer identifier code (MID).",
    ],
}


@router.get("/compliance/requirements")
async def requirements(category: str):
    return {
        "category": category,
        "required": REQUIRED_BY_CATEGORY.get(category, []),
        "us_import_guide": GUIDE_BY_CATEGORY.get(category, []),
    }


@router.post("/compliance/documents", response_model=ComplianceDocument)
async def add_document(payload: dict, user: User = Depends(get_current_user)):
    if not user.business_id:
        raise HTTPException(400, "Create a business first")
    doc = ComplianceDocument(
        business_id=user.business_id,
        product_id=payload.get("product_id"),
        document_type=payload.get("document_type", "Other"),
        file_url=payload.get("file_url", ""),
        original_filename=payload.get("original_filename", ""),
        issued_date=payload.get("issued_date"),
        expiry_date=payload.get("expiry_date"),
        issuing_authority=payload.get("issuing_authority", ""),
        status="pending_review",
    )
    d = doc.model_dump()
    d["created_at"] = d["created_at"].isoformat()
    await db.compliance_documents.insert_one(d)
    await _recompute_status(doc.id)
    await _recompute_score(user.business_id)
    return doc


@router.get("/compliance/documents")
async def list_documents(user: User = Depends(get_current_user)):
    if not user.business_id:
        return []
    items = await db.compliance_documents.find({"business_id": user.business_id}, {"_id": 0}).sort("created_at", -1).to_list(500)
    # recompute statuses
    for it in items:
        it["status"] = _status_for(it.get("expiry_date"))
    return items


@router.delete("/compliance/documents/{did}")
async def delete_document(did: str, user: User = Depends(get_current_user)):
    d = await db.compliance_documents.find_one({"id": did}, {"_id": 0})
    if not d:
        raise HTTPException(404)
    if d["business_id"] != user.business_id and user.role not in ("admin", "super_admin"):
        raise HTTPException(403)
    await db.compliance_documents.delete_one({"id": did})
    await _recompute_score(d["business_id"])
    return {"status": "deleted"}


@router.get("/compliance/score")
async def score(user: User = Depends(get_current_user)):
    if not user.business_id:
        return {"score": 0, "missing": [], "category_scores": {}}
    biz = await db.businesses.find_one({"id": user.business_id}, {"_id": 0})
    score, missing, cat_scores = await _compute_score(user.business_id)
    return {"score": score, "missing": missing, "category_scores": cat_scores, "business_name": biz.get("business_name") if biz else ""}


# ---------- helpers ----------

def _status_for(expiry_iso: str | None) -> str:
    if not expiry_iso:
        return "active"
    try:
        exp = datetime.fromisoformat(expiry_iso)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
    except Exception:
        return "active"
    now = datetime.now(timezone.utc)
    if exp < now:
        return "expired"
    if exp < now + timedelta(days=30):
        return "expiring_soon"
    return "active"


async def _recompute_status(doc_id: str):
    d = await db.compliance_documents.find_one({"id": doc_id}, {"_id": 0})
    if not d:
        return
    st = _status_for(d.get("expiry_date"))
    await db.compliance_documents.update_one({"id": doc_id}, {"$set": {"status": st}})


async def _compute_score(business_id: str):
    # look at products for this business; for each category, check required docs
    products = await db.products.find({"business_id": business_id}, {"_id": 0}).to_list(1000)
    categories = sorted({p["category"] for p in products}) or ["general-goods"]
    docs = await db.compliance_documents.find({"business_id": business_id}, {"_id": 0}).to_list(1000)
    active_types = {d["document_type"].lower() for d in docs if _status_for(d.get("expiry_date")) == "active"}

    total_required, total_present = 0, 0
    missing = []
    cat_scores = {}
    for cat in categories:
        req = REQUIRED_BY_CATEGORY.get(cat, [])
        present = sum(1 for r in req if r.lower() in active_types)
        total_required += len(req)
        total_present += present
        cat_scores[cat] = {"required": len(req), "present": present, "missing": [r for r in req if r.lower() not in active_types]}
        missing.extend(cat_scores[cat]["missing"])
    score = int(round((total_present / total_required) * 100)) if total_required else 0
    return score, list(dict.fromkeys(missing)), cat_scores


async def _recompute_score(business_id: str):
    score, _, _ = await _compute_score(business_id)
    await db.businesses.update_one({"id": business_id}, {"$set": {"compliance_score": score, "updated_at": datetime.now(timezone.utc).isoformat()}})
