"""Seed demo data for Helix Platform."""
import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone, timedelta

from db import db
from auth import hash_password
from anchor_client import create_business_customer, create_deposit_account, create_reserved_account
from fx import usd_to_ngn

log = logging.getLogger("helix.seed")


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


async def seed_if_empty():
    count = await db.users.count_documents({})
    if count > 0:
        log.info("Seed skipped (users already exist)")
        return
    log.info("Seeding demo data...")

    # ---------- Users ----------
    admin = {
        "user_id": str(uuid.uuid4()),
        "email": "admin@helix.com",
        "name": "Helix Admin",
        "role": "super_admin",
        "password_hash": hash_password("Helix@123"),
        "auth_provider": "jwt",
        "picture": None,
        "business_id": None,
        "created_at": _now_iso(),
    }
    exporter = {
        "user_id": str(uuid.uuid4()),
        "email": "exporter@helix.com",
        "name": "Adaeze Okafor",
        "role": "exporter",
        "password_hash": hash_password("Helix@123"),
        "auth_provider": "jwt",
        "picture": None,
        "business_id": None,
        "created_at": _now_iso(),
    }
    buyer = {
        "user_id": str(uuid.uuid4()),
        "email": "buyer@helix.com",
        "name": "Marcus Reid",
        "role": "buyer",
        "password_hash": hash_password("Helix@123"),
        "auth_provider": "jwt",
        "picture": None,
        "business_id": None,
        "created_at": _now_iso(),
    }
    jomp = {
        "user_id": str(uuid.uuid4()),
        "email": "credit@jompstart.com",
        "name": "Ifeoma · JompStart Credit",
        "role": "jompstart_admin",
        "password_hash": hash_password("Helix@123"),
        "auth_provider": "jwt",
        "picture": None,
        "business_id": None,
        "created_at": _now_iso(),
    }
    consumer = {
        "user_id": str(uuid.uuid4()),
        "email": "shopper@helix.com",
        "name": "Jordan Bell",
        "role": "consumer",
        "password_hash": hash_password("Helix@123"),
        "auth_provider": "jwt",
        "picture": None,
        "business_id": None,
        "created_at": _now_iso(),
    }
    await db.users.insert_many([admin, exporter, buyer, jomp, consumer])

    # ---------- Businesses ----------
    exp_cust = create_business_customer({"name": "Lagos Heritage Textiles Ltd", "email": "exporter@helix.com"})
    exp_ngn = create_deposit_account(exp_cust["id"], "NGN")
    exp_usd = create_deposit_account(exp_cust["id"], "USD")

    byr_cust = create_business_customer({"name": "Brooklyn Heritage Imports LLC", "email": "buyer@helix.com"})
    byr_ngn = create_deposit_account(byr_cust["id"], "NGN")
    byr_usd = create_deposit_account(byr_cust["id"], "USD")

    exp_biz = {
        "id": str(uuid.uuid4()),
        "owner_user_id": exporter["user_id"],
        "business_name": "Lagos Heritage Textiles Ltd",
        "registration_type": "business",
        "country": "Nigeria",
        "sector": "fashion",
        "role": "exporter",
        "cac_number": "RC-2045112",
        "tin": "20234401-0001",
        "bvn": "22190456712",
        "nin": None,
        "ein": None,
        "director_name": "Adaeze Okafor",
        "contact_phone": "+234 901 234 5678",
        "contact_email": "exporter@helix.com",
        "address": "18 Broad Street, Lagos Island, Lagos",
        "kyc_docs": [],
        "kyb_docs": [],
        "anchor_customer_id": exp_cust["id"],
        "anchor_account_ngn": exp_ngn["id"],
        "anchor_account_usd": exp_usd["id"],
        "anchor_ngn_virtual_account": exp_ngn["account_number"],
        "anchor_usd_virtual_account": exp_usd["account_number"],
        "kyc_status": "approved",
        "kyb_status": "approved",
        "compliance_score": 75,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    byr_biz = {
        "id": str(uuid.uuid4()),
        "owner_user_id": buyer["user_id"],
        "business_name": "Brooklyn Heritage Imports LLC",
        "registration_type": "business",
        "country": "United States",
        "sector": "general-goods",
        "role": "buyer",
        "cac_number": None,
        "tin": None,
        "bvn": None,
        "nin": None,
        "ein": "84-2910556",
        "director_name": "Marcus Reid",
        "contact_phone": "+1 718 555 0112",
        "contact_email": "buyer@helix.com",
        "address": "240 Kent Ave, Brooklyn, NY 11249",
        "kyc_docs": [],
        "kyb_docs": [],
        "anchor_customer_id": byr_cust["id"],
        "anchor_account_ngn": byr_ngn["id"],
        "anchor_account_usd": byr_usd["id"],
        "anchor_ngn_virtual_account": byr_ngn["account_number"],
        "anchor_usd_virtual_account": byr_usd["account_number"],
        "kyc_status": "approved",
        "kyb_status": "approved",
        "compliance_score": 0,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    await db.businesses.insert_many([exp_biz, byr_biz])
    await db.users.update_one({"user_id": exporter["user_id"]}, {"$set": {"business_id": exp_biz["id"]}})
    await db.users.update_one({"user_id": buyer["user_id"]}, {"$set": {"business_id": byr_biz["id"]}})

    # ---------- Products ----------
    _U = "https://images.unsplash.com/photo-"
    _IMG = "?auto=format&fit=crop&w=900&q=80"
    products = [
        {
            "name": "Premium Adire Indigo Fabric (6 yards)",
            "category": "fashion",
            "description": "Handwoven indigo-dyed Adire textile from Abeokuta artisans. 100% cotton, 6-yard panels. Export-ready, SON certified.",
            "photos": [f"{_U}1528459105426-b9548367069b{_IMG}"],
            "price_usd": 48.50,
            "min_order_qty": 50,
            "unit": "panel",
            "export_readiness_score": 92,
            "compliance_badges": ["SON", "Country-of-Origin Label"],
            "status": "active",
        },
        {
            "name": "Ankara Wax Print Roll (12 yards)",
            "category": "fashion",
            "description": "Vibrant wax-print Ankara fabric, 12-yard commercial roll. Designed in Lagos, printed in Nigeria.",
            "photos": [f"{_U}1503342217505-b0a15ec3261c{_IMG}"],
            "price_usd": 62.00,
            "min_order_qty": 25,
            "unit": "roll",
            "export_readiness_score": 85,
            "compliance_badges": ["SON"],
            "status": "active",
        },
        {
            "name": "Premium Ofada Rice (50kg bag)",
            "category": "staple-foods",
            "description": "Single-origin brown Ofada rice from Ogun State farmers. NAFDAC registered, parboiled and packaged for export.",
            "photos": [f"{_U}1586201375761-83865001e31c{_IMG}"],
            "price_usd": 78.00,
            "min_order_qty": 100,
            "unit": "bag",
            "export_readiness_score": 88,
            "compliance_badges": ["NAFDAC", "Phytosanitary"],
            "status": "active",
        },
        {
            "name": "Cold-Pressed Palm Oil (20L jerry can)",
            "category": "agriculture",
            "description": "Sustainably-sourced, unrefined red palm oil from family cooperatives in Edo state. 20L food-grade jerry cans.",
            "photos": [f"{_U}1604329760661-e71dc83f8f26{_IMG}"],
            "price_usd": 92.00,
            "min_order_qty": 40,
            "unit": "jerry can",
            "export_readiness_score": 78,
            "compliance_badges": ["NAFDAC"],
            "status": "active",
        },
        {
            "name": "Shea Butter — Grade A (25kg drum)",
            "category": "agriculture",
            "description": "Unrefined Grade A shea butter from Northern Nigeria women's cooperatives. Ideal for cosmetics and food industries.",
            "photos": [f"{_U}1608571423902-eed4a5ad8108{_IMG}"],
            "price_usd": 145.00,
            "min_order_qty": 20,
            "unit": "drum",
            "export_readiness_score": 95,
            "compliance_badges": ["NAFDAC", "Phytosanitary", "Fumigation"],
            "status": "active",
        },
        {
            "name": "Leather Tote — Handcrafted (Lagos Edition)",
            "category": "fashion",
            "description": "Full-grain Nigerian leather tote bag, hand-stitched in Lagos. Individually numbered, with origin certificate.",
            "photos": [f"{_U}1553062407-98eeb64c6a62{_IMG}"],
            "price_usd": 120.00,
            "min_order_qty": 10,
            "unit": "piece",
            "export_readiness_score": 70,
            "compliance_badges": ["Country-of-Origin Label"],
            "status": "active",
        },
    ]
    product_docs = []
    for p in products:
        d = {
            "id": str(uuid.uuid4()),
            "business_id": exp_biz["id"],
            "price_ngn": usd_to_ngn(p["price_usd"]),
            "created_at": _now_iso(),
            **p,
        }
        product_docs.append(d)
    await db.products.insert_many(product_docs)

    # ---------- Orders ----------
    # order 1: confirmed, payment pending
    p1 = product_docs[0]
    res1 = create_reserved_account("demo-order-1", exp_cust["id"], p1["price_usd"] * 100, "USD")
    o1_id = str(uuid.uuid4())
    o1 = {
        "id": o1_id,
        "order_number": f"HLX-{uuid.uuid4().hex[:8].upper()}",
        "buyer_id": byr_biz["id"],
        "supplier_id": exp_biz["id"],
        "buyer_user_id": buyer["user_id"],
        "supplier_user_id": exporter["user_id"],
        "product_id": p1["id"],
        "product_name": p1["name"],
        "quantity": 100,
        "unit_price_usd": p1["price_usd"],
        "agreed_price_usd": p1["price_usd"] * 100,
        "status": "confirmed",
        "payment_status": "pending",
        "delivery_address": "240 Kent Ave, Brooklyn, NY 11249, USA",
        "target_delivery_date": (datetime.now(timezone.utc) + timedelta(days=45)).date().isoformat(),
        "message": "Please prioritize packaging for retail shelving.",
        "anchor_reserved_account_id": res1["id"],
        "anchor_reserved_account_number": res1["account_number"],
        "documents": [],
        "timeline": [
            {"at": _now_iso(), "event": "rfq_submitted", "by": buyer["user_id"]},
            {"at": _now_iso(), "event": "proforma_issued", "by": exporter["user_id"]},
        ],
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }

    # order 2: in_production, payment confirmed + platform fee
    p2 = product_docs[2]
    res2 = create_reserved_account("demo-order-2", exp_cust["id"], p2["price_usd"] * 200, "USD")
    o2_id = str(uuid.uuid4())
    o2 = {
        "id": o2_id,
        "order_number": f"HLX-{uuid.uuid4().hex[:8].upper()}",
        "buyer_id": byr_biz["id"],
        "supplier_id": exp_biz["id"],
        "buyer_user_id": buyer["user_id"],
        "supplier_user_id": exporter["user_id"],
        "product_id": p2["id"],
        "product_name": p2["name"],
        "quantity": 200,
        "unit_price_usd": p2["price_usd"],
        "agreed_price_usd": p2["price_usd"] * 200,
        "status": "in_production",
        "payment_status": "confirmed",
        "delivery_address": "240 Kent Ave, Brooklyn, NY 11249, USA",
        "target_delivery_date": (datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat(),
        "message": "Per agreed milling grade.",
        "anchor_reserved_account_id": res2["id"],
        "anchor_reserved_account_number": res2["account_number"],
        "documents": [],
        "timeline": [
            {"at": _now_iso(), "event": "rfq_submitted"},
            {"at": _now_iso(), "event": "proforma_issued"},
            {"at": _now_iso(), "event": "payment_received"},
            {"at": _now_iso(), "event": "status:in_production"},
        ],
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    await db.orders.insert_many([o1, o2])

    # ---------- Transactions for order 2 ----------
    credit_amt = o2["agreed_price_usd"]
    fee_amt = round(credit_amt * 0.01, 2)
    await db.transactions.insert_many([
        {
            "id": str(uuid.uuid4()),
            "business_id": exp_biz["id"],
            "order_id": o2_id,
            "anchor_transaction_ref": f"anchor_tx_{uuid.uuid4().hex[:16]}",
            "type": "credit",
            "amount": credit_amt,
            "currency": "USD",
            "status": "completed",
            "anchor_event_type": "account.credited",
            "description": f"Payment received for order {o2['order_number']}",
            "counterparty": byr_biz["id"],
            "timestamp": _now_iso(),
        },
        {
            "id": str(uuid.uuid4()),
            "business_id": exp_biz["id"],
            "order_id": o2_id,
            "anchor_transaction_ref": f"fee_{uuid.uuid4().hex[:12]}",
            "type": "fee",
            "amount": fee_amt,
            "currency": "USD",
            "status": "completed",
            "anchor_event_type": "fee.applied",
            "description": f"Helix platform fee (1%) on order {o2['order_number']}",
            "timestamp": _now_iso(),
        },
        # NGN inflow (local sale + FX swap stub)
        {
            "id": str(uuid.uuid4()),
            "business_id": exp_biz["id"],
            "anchor_transaction_ref": f"anchor_tx_{uuid.uuid4().hex[:16]}",
            "type": "credit",
            "amount": 8_500_000,
            "currency": "NGN",
            "status": "completed",
            "anchor_event_type": "account.credited",
            "description": "Local supplier payment",
            "timestamp": _now_iso(),
        },
    ])

    # ---------- Compliance documents ----------
    today = datetime.now(timezone.utc).date()
    compliance_docs = [
        {
            "id": str(uuid.uuid4()),
            "business_id": exp_biz["id"],
            "product_id": None,
            "document_type": "SON Certification",
            "file_url": "",
            "original_filename": "son-cert-2025.pdf",
            "issued_date": (today - timedelta(days=180)).isoformat(),
            "expiry_date": (today + timedelta(days=185)).isoformat(),
            "issuing_authority": "Standards Organisation of Nigeria",
            "status": "active",
            "created_at": _now_iso(),
        },
        {
            "id": str(uuid.uuid4()),
            "business_id": exp_biz["id"],
            "product_id": None,
            "document_type": "NAFDAC",
            "file_url": "",
            "original_filename": "nafdac-reg.pdf",
            "issued_date": (today - timedelta(days=120)).isoformat(),
            "expiry_date": (today + timedelta(days=245)).isoformat(),
            "issuing_authority": "NAFDAC",
            "status": "active",
            "created_at": _now_iso(),
        },
        {
            "id": str(uuid.uuid4()),
            "business_id": exp_biz["id"],
            "product_id": None,
            "document_type": "Fumigation Certificate",
            "file_url": "",
            "original_filename": "fumigation-2026.pdf",
            "issued_date": (today - timedelta(days=30)).isoformat(),
            "expiry_date": (today + timedelta(days=335)).isoformat(),
            "issuing_authority": "Nigeria Export Promotion Council",
            "status": "active",
            "created_at": _now_iso(),
        },
        {
            "id": str(uuid.uuid4()),
            "business_id": exp_biz["id"],
            "product_id": None,
            "document_type": "FSSAI / FDA Equivalence",
            "file_url": "",
            "original_filename": "fda-fsvp.pdf",
            "issued_date": (today - timedelta(days=90)).isoformat(),
            "expiry_date": (today + timedelta(days=275)).isoformat(),
            "issuing_authority": "US FDA (FSVP)",
            "status": "active",
            "created_at": _now_iso(),
        },
        {
            "id": str(uuid.uuid4()),
            "business_id": exp_biz["id"],
            "product_id": None,
            "document_type": "Phytosanitary Certificate",
            "file_url": "",
            "original_filename": "phyto-2025.pdf",
            "issued_date": (today - timedelta(days=45)).isoformat(),
            "expiry_date": (today + timedelta(days=320)).isoformat(),
            "issuing_authority": "Nigeria Agricultural Quarantine Service",
            "status": "active",
            "created_at": _now_iso(),
        },
        {
            "id": str(uuid.uuid4()),
            "business_id": exp_biz["id"],
            "product_id": None,
            "document_type": "Country of Origin Label",
            "file_url": "",
            "original_filename": "origin-label.pdf",
            "issued_date": (today - timedelta(days=60)).isoformat(),
            "expiry_date": (today + timedelta(days=600)).isoformat(),
            "issuing_authority": "Nigerian Export Promotion Council",
            "status": "active",
            "created_at": _now_iso(),
        },
    ]
    await db.compliance_documents.insert_many(compliance_docs)

    # ---------- Shop listings ----------
    # Buyer local inventory (Brooklyn warehouse re-sell)
    buyer_listing = {
        "id": str(uuid.uuid4()),
        "owner_business_id": byr_biz["id"],
        "title": "Ofada Rice 5kg Retail Bag — From Brooklyn Warehouse",
        "description": "Authentic single-origin Ofada rice imported direct from Ogun State, Nigeria. Repackaged into retail-ready 5kg bags at our Brooklyn facility. Ships within 48 hours across the US.",
        "photos": [f"{_U}1536304929831-ee1ca9d44906{_IMG}"],
        "category": "staple-foods",
        "retail_price_usd": 24.99,
        "stock_qty": 120,
        "fulfillment_mode": "buyer_local",
        "source_order_id": o2_id,  # from the delivered trade order
        "source_product_id": p2["id"],
        "country_of_origin": "Nigeria",
        "ships_from": "Brooklyn, NY",
        "delivery_partner_of_record": "",
        "status": "active",
        "created_at": _now_iso(),
    }
    # Exporter DTC (Riby Inc of record)
    exp_listing = {
        "id": str(uuid.uuid4()),
        "owner_business_id": exp_biz["id"],
        "title": "Unrefined Shea Butter 500g Jar — Direct from Nigeria",
        "description": "Grade A unrefined shea butter hand-whipped by Northern Nigeria women's cooperatives. 500g glass jars, individually labeled. Ships direct — Riby Inc handles US import and last-mile delivery.",
        "photos": [f"{_U}1565193566173-7a0ee3dbe261{_IMG}"],
        "category": "agriculture",
        "retail_price_usd": 32.00,
        "stock_qty": 60,
        "fulfillment_mode": "riby_dtc",
        "source_product_id": product_docs[4]["id"],
        "country_of_origin": "Nigeria",
        "ships_from": "Lagos, Nigeria → Riby US fulfillment",
        "delivery_partner_of_record": "Riby Inc",
        "status": "active",
        "created_at": _now_iso(),
    }
    exp_listing_2 = {
        "id": str(uuid.uuid4()),
        "owner_business_id": exp_biz["id"],
        "title": "Handwoven Adire Scarf — Lagos Artisan Edition",
        "description": "Hand-dyed Adire indigo scarf (180×50cm) from Abeokuta artisans. Individually numbered. Riby Inc imports and fulfills in the US on behalf of the maker.",
        "photos": [f"{_U}1528459105426-b9548367069b{_IMG}"],
        "category": "fashion",
        "retail_price_usd": 89.00,
        "stock_qty": 45,
        "fulfillment_mode": "riby_dtc",
        "source_product_id": product_docs[0]["id"],
        "country_of_origin": "Nigeria",
        "ships_from": "Lagos → Riby US fulfillment",
        "delivery_partner_of_record": "Riby Inc",
        "status": "active",
        "created_at": _now_iso(),
    }
    await db.shop_listings.insert_many([buyer_listing, exp_listing, exp_listing_2])

    log.info("Seed complete: 5 users, 2 businesses, %d products, 2 orders, %d compliance docs, 3 shop listings", len(product_docs), len(compliance_docs))
