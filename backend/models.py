"""Pydantic models for Helix Platform."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, date
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, EmailStr, ConfigDict

# ---------- helpers ----------

def _uuid() -> str:
    return str(uuid.uuid4())

def _now() -> datetime:
    return datetime.now(timezone.utc)


Role = Literal["exporter", "buyer", "admin", "super_admin", "jompstart_admin", "consumer"]
RegistrationType = Literal["individual", "business"]
Sector = Literal["fashion", "agriculture", "staple-foods", "general-goods"]
KycStatus = Literal["pending", "under_review", "approved", "rejected"]
ProductStatus = Literal["draft", "active", "archived"]
OrderStatus = Literal["draft", "confirmed", "in_production", "ready_to_ship", "shipped", "delivered", "disputed"]
PaymentStatus = Literal["pending", "received", "confirmed", "failed"]
TxType = Literal["credit", "debit", "transfer", "fee"]
Currency = Literal["NGN", "USD"]
TxStatus = Literal["pending", "completed", "failed"]
DocStatus = Literal["active", "expiring_soon", "expired", "pending_review"]


# ---------- User & Auth ----------

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str = Field(default_factory=_uuid)
    email: EmailStr
    name: str
    role: Role = "exporter"
    business_id: Optional[str] = None
    password_hash: Optional[str] = None  # None for OAuth-only users
    picture: Optional[str] = None
    auth_provider: Literal["jwt", "emergent"] = "jwt"
    created_at: datetime = Field(default_factory=_now)


class UserPublic(BaseModel):
    user_id: str
    email: EmailStr
    name: str
    role: Role
    business_id: Optional[str] = None
    picture: Optional[str] = None


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: Role = "exporter"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


# ---------- Business ----------

class Business(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=_uuid)
    owner_user_id: str
    business_name: str
    registration_type: RegistrationType
    country: str
    sector: Sector
    role: Role = "exporter"  # the role the business uses platform as
    # Identity doc fields
    cac_number: Optional[str] = None
    tin: Optional[str] = None
    bvn: Optional[str] = None
    nin: Optional[str] = None
    ein: Optional[str] = None
    director_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    address: Optional[str] = None
    # KYC/KYB docs (storage paths)
    kyc_docs: List[str] = Field(default_factory=list)
    kyb_docs: List[str] = Field(default_factory=list)
    # Anchor
    anchor_customer_id: Optional[str] = None
    anchor_account_ngn: Optional[str] = None
    anchor_account_usd: Optional[str] = None
    anchor_ngn_virtual_account: Optional[str] = None  # account number string
    anchor_usd_virtual_account: Optional[str] = None
    kyc_status: KycStatus = "pending"
    kyb_status: KycStatus = "pending"
    compliance_score: int = 0
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class BusinessCreate(BaseModel):
    business_name: str
    registration_type: RegistrationType
    country: str
    sector: Sector
    role: Role = "exporter"
    cac_number: Optional[str] = None
    tin: Optional[str] = None
    bvn: Optional[str] = None
    nin: Optional[str] = None
    ein: Optional[str] = None
    director_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    address: Optional[str] = None


# ---------- Product ----------

class Product(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=_uuid)
    business_id: str
    name: str
    category: Sector
    description: str = ""
    photos: List[str] = Field(default_factory=list)  # storage paths
    price_ngn: float = 0
    price_usd: float = 0
    min_order_qty: int = 1
    unit: str = "unit"
    export_readiness_score: int = 0
    compliance_badges: List[str] = Field(default_factory=list)
    status: ProductStatus = "draft"
    created_at: datetime = Field(default_factory=_now)


class ProductCreate(BaseModel):
    name: str
    category: Sector
    description: str = ""
    price_usd: float
    min_order_qty: int = 1
    unit: str = "unit"
    photos: List[str] = Field(default_factory=list)
    status: ProductStatus = "draft"


# ---------- RFQ / Order ----------

class RFQCreate(BaseModel):
    product_id: str
    quantity: int
    delivery_address: str
    target_delivery_date: Optional[str] = None
    message: Optional[str] = ""


class Order(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=_uuid)
    order_number: str = Field(default_factory=lambda: f"HLX-{uuid.uuid4().hex[:8].upper()}")
    buyer_id: str  # business id
    supplier_id: str  # business id
    buyer_user_id: str
    supplier_user_id: str
    product_id: str
    product_name: str
    quantity: int
    unit_price_usd: float
    agreed_price_usd: float
    status: OrderStatus = "draft"
    payment_status: PaymentStatus = "pending"
    delivery_address: str = ""
    target_delivery_date: Optional[str] = None
    message: Optional[str] = ""
    anchor_reserved_account_id: Optional[str] = None
    anchor_reserved_account_number: Optional[str] = None
    documents: List[str] = Field(default_factory=list)  # storage paths
    timeline: List[dict] = Field(default_factory=list)  # events
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


# ---------- Transaction ----------

class Transaction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=_uuid)
    business_id: str
    order_id: Optional[str] = None
    anchor_transaction_ref: str
    type: TxType
    amount: float
    currency: Currency
    status: TxStatus = "completed"
    anchor_event_type: Optional[str] = None
    description: str = ""
    counterparty: Optional[str] = None
    timestamp: datetime = Field(default_factory=_now)


# ---------- Compliance ----------

class ComplianceDocument(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=_uuid)
    business_id: str
    product_id: Optional[str] = None
    document_type: str
    file_url: str  # storage path
    original_filename: str = ""
    issued_date: Optional[str] = None  # iso
    expiry_date: Optional[str] = None  # iso
    issuing_authority: str = ""
    status: DocStatus = "pending_review"
    created_at: datetime = Field(default_factory=_now)


# ---------- Dispute ----------

class Dispute(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=_uuid)
    order_id: str
    raised_by_user_id: str
    raised_by_business_id: str
    reason: str
    description: str
    evidence_urls: List[str] = Field(default_factory=list)
    status: Literal["open", "under_review", "resolved", "rejected"] = "open"
    resolution: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)


# ---------- Consumer Shop ----------

FulfillmentMode = Literal["buyer_local", "riby_dtc"]


class ShopListing(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=_uuid)
    owner_business_id: str  # Buyer (buyer_local) or Exporter (riby_dtc)
    title: str
    description: str = ""
    photos: List[str] = Field(default_factory=list)
    category: Sector = "general-goods"
    retail_price_usd: float
    stock_qty: int = 0
    fulfillment_mode: FulfillmentMode  # buyer_local | riby_dtc
    source_order_id: Optional[str] = None  # the trade order this stock came from
    source_product_id: Optional[str] = None
    country_of_origin: str = "Nigeria"
    ships_from: str = ""
    delivery_partner_of_record: str = ""  # "Riby Inc" for riby_dtc listings
    status: Literal["active", "out_of_stock", "archived"] = "active"
    created_at: datetime = Field(default_factory=_now)


class ShopListingCreate(BaseModel):
    title: str
    description: str = ""
    photos: List[str] = Field(default_factory=list)
    category: Sector = "general-goods"
    retail_price_usd: float
    stock_qty: int = 1
    fulfillment_mode: FulfillmentMode
    source_order_id: Optional[str] = None
    source_product_id: Optional[str] = None
    ships_from: str = ""


class ConsumerOrder(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=_uuid)
    order_number: str = Field(default_factory=lambda: f"SHP-{uuid.uuid4().hex[:8].upper()}")
    consumer_user_id: str
    listing_id: str
    listing_title: str
    quantity: int
    unit_price_usd: float
    total_usd: float
    seller_business_id: str
    fulfillment_mode: FulfillmentMode
    delivery_partner_of_record: str = ""  # "Riby Inc" if DTC
    shipping_name: str
    shipping_address: str
    shipping_email: EmailStr
    shipping_phone: str = ""
    status: Literal["paid", "processing", "shipped", "delivered", "cancelled"] = "paid"
    tracking_number: Optional[str] = None
    payment_ref: str
    created_at: datetime = Field(default_factory=_now)


class ConsumerOrderCreate(BaseModel):
    listing_id: str
    quantity: int = 1
    shipping_name: str
    shipping_address: str
    shipping_email: EmailStr
    shipping_phone: str = ""


# ---------- JompStart repayments ----------

InstallmentStatus = Literal["pending", "paid", "partial", "overdue"]


class RepaymentInstallment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=_uuid)
    application_id: str
    business_id: str
    installment_number: int
    due_date: str  # iso date
    principal_usd: float
    interest_usd: float
    total_due_usd: float
    paid_usd: float = 0
    status: InstallmentStatus = "pending"
    paid_at: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)
