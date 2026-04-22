"""Product catalog routes."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query

from db import db
from auth import get_current_user, get_optional_user, require_roles
from models import Product, ProductCreate, User
from fx import usd_to_ngn, get_rates

router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/fx")
async def fx():
    r = get_rates()
    ngn = r["rates"].get("NGN", 1650.0)
    return {"usd_to_ngn": ngn, "fetched_at": r["fetched_at"], "source": r["source"]}


async def _require_approved_exporter(user: User) -> dict:
    if not user.business_id:
        raise HTTPException(400, "Create a business profile first")
    biz = await db.businesses.find_one({"id": user.business_id}, {"_id": 0})
    if not biz:
        raise HTTPException(400, "Business profile missing")
    approved = biz.get("kyc_status") == "approved" or biz.get("kyb_status") == "approved"
    if not approved:
        raise HTTPException(403, "Business must be KYC/KYB approved to list products")
    return biz


@router.post("/products", response_model=Product)
async def create_product(payload: ProductCreate, user: User = Depends(get_current_user)):
    biz = await _require_approved_exporter(user)
    price_ngn = usd_to_ngn(payload.price_usd)
    prod = Product(
        business_id=biz["id"],
        price_ngn=price_ngn,
        **payload.model_dump(),
    )
    doc = prod.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.products.insert_one(doc)
    return prod


@router.get("/products", response_model=list[Product])
async def list_products(
    category: str | None = None,
    country: str | None = None,
    status: str | None = Query("active"),
    business_id: str | None = None,
    search: str | None = None,
    user: User | None = Depends(get_optional_user),
):
    q: dict = {}
    if status:
        q["status"] = status
    if category:
        q["category"] = category
    if business_id:
        q["business_id"] = business_id
    if search:
        q["name"] = {"$regex": search, "$options": "i"}
    cursor = db.products.find(q, {"_id": 0}).sort("created_at", -1)
    items = await cursor.to_list(500)
    # filter by country via business join
    if country:
        biz_ids = {p["business_id"] for p in items}
        biz_list = await db.businesses.find({"id": {"$in": list(biz_ids)}, "country": {"$regex": f"^{country}$", "$options": "i"}}, {"_id": 0}).to_list(500)
        allowed = {b["id"] for b in biz_list}
        items = [p for p in items if p["business_id"] in allowed]
    return [Product(**p) for p in items]


@router.get("/products/mine", response_model=list[Product])
async def my_products(user: User = Depends(get_current_user)):
    if not user.business_id:
        return []
    cursor = db.products.find({"business_id": user.business_id}, {"_id": 0}).sort("created_at", -1)
    items = await cursor.to_list(500)
    return [Product(**p) for p in items]


@router.get("/products/{pid}")
async def get_product(pid: str):
    p = await db.products.find_one({"id": pid}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Product not found")
    biz = await db.businesses.find_one({"id": p["business_id"]}, {"_id": 0})
    return {"product": p, "supplier": biz}


@router.patch("/products/{pid}", response_model=Product)
async def update_product(pid: str, payload: dict, user: User = Depends(get_current_user)):
    p = await db.products.find_one({"id": pid}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Not found")
    if p["business_id"] != user.business_id and user.role not in ("admin", "super_admin"):
        raise HTTPException(403, "Forbidden")
    allowed = {"name", "category", "description", "photos", "price_usd", "min_order_qty", "unit", "status", "compliance_badges", "export_readiness_score"}
    update = {k: v for k, v in payload.items() if k in allowed}
    if "price_usd" in update:
        update["price_ngn"] = usd_to_ngn(update["price_usd"])
    if update:
        await db.products.update_one({"id": pid}, {"$set": update})
    p = await db.products.find_one({"id": pid}, {"_id": 0})
    return Product(**p)


@router.delete("/products/{pid}")
async def delete_product(pid: str, user: User = Depends(get_current_user)):
    p = await db.products.find_one({"id": pid}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Not found")
    if p["business_id"] != user.business_id and user.role not in ("admin", "super_admin"):
        raise HTTPException(403, "Forbidden")
    await db.products.delete_one({"id": pid})
    return {"status": "deleted"}
