"""Iteration 4 — TARGETED RETEST of iteration 3 fixes.

Focus:
 (a) POST /api/shop/listings no-longer-500 happy path + role guardrails
 (b) Atomicity of stock decrement under concurrency
 (c) simulate-payment resilience (auto-debit cannot 500 the response)
 (d) Regression: consumer checkout on buyer_local listing still works
"""
import os
import threading
import time
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip()
                break
BASE_URL = (BASE_URL or "").rstrip("/")
PWD = "Helix@123"


def _login(email: str) -> str:
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": PWD}, timeout=15)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


# ---------- Fixtures ----------
@pytest.fixture(scope="session")
def exporter_tok():
    return _login("exporter@helix.com")


@pytest.fixture(scope="session")
def buyer_tok():
    return _login("buyer@helix.com")


@pytest.fixture(scope="session")
def shopper_tok():
    return _login("shopper@helix.com")


# =====================================================================
# (a) POST /api/shop/listings — the CRITICAL iter3 fix
# =====================================================================
class TestCreateListing:
    """Verify ships_from kwarg collision is gone + role guardrails."""

    def test_exporter_riby_dtc_happy_path(self, exporter_tok):
        payload = {
            "title": f"TEST_Adire Scarf {uuid.uuid4().hex[:6]}",
            "description": "Hand-dyed Nigerian adire scarf",
            "photos": [],
            "category": "fashion",
            "retail_price_usd": 49.99,
            "stock_qty": 5,
            "fulfillment_mode": "riby_dtc",
            "ships_from": "Lagos, Nigeria",
        }
        r = requests.post(f"{BASE_URL}/api/shop/listings", headers=_h(exporter_tok), json=payload, timeout=15)
        assert r.status_code == 200, f"expected 200 got {r.status_code}: {r.text}"
        data = r.json()
        # Assertions on the fix
        assert data["fulfillment_mode"] == "riby_dtc"
        assert data["delivery_partner_of_record"] == "Riby Inc"
        assert data["ships_from"] == "Lagos, Nigeria"
        assert data["title"] == payload["title"]
        assert data["stock_qty"] == 5
        assert data["retail_price_usd"] == 49.99
        assert data["country_of_origin"] == "Nigeria"
        assert "id" in data
        # Persistence check
        lid = data["id"]
        g = requests.get(f"{BASE_URL}/api/shop/listings/{lid}", timeout=15)
        assert g.status_code == 200
        assert g.json()["id"] == lid
        # stash id for cleanup test
        pytest.exporter_test_listing_id = lid

    def test_exporter_buyer_local_rejected(self, exporter_tok):
        payload = {
            "title": f"TEST_Invalid Exporter Local {uuid.uuid4().hex[:6]}",
            "description": "should fail",
            "photos": [],
            "category": "fashion",
            "retail_price_usd": 10.0,
            "stock_qty": 1,
            "fulfillment_mode": "buyer_local",
        }
        r = requests.post(f"{BASE_URL}/api/shop/listings", headers=_h(exporter_tok), json=payload, timeout=15)
        assert r.status_code == 400, f"expected 400 got {r.status_code}: {r.text}"

    def test_buyer_local_happy_path(self, buyer_tok):
        payload = {
            "title": f"TEST_Brooklyn Local {uuid.uuid4().hex[:6]}",
            "description": "Buyer local inventory",
            "photos": [],
            "category": "general-goods",
            "retail_price_usd": 22.5,
            "stock_qty": 10,
            "fulfillment_mode": "buyer_local",
            "ships_from": "Brooklyn, NY",
        }
        r = requests.post(f"{BASE_URL}/api/shop/listings", headers=_h(buyer_tok), json=payload, timeout=15)
        assert r.status_code == 200, f"expected 200 got {r.status_code}: {r.text}"
        data = r.json()
        assert data["fulfillment_mode"] == "buyer_local"
        # no DPoR for buyer_local
        assert data["delivery_partner_of_record"] == ""
        assert data["ships_from"] == "Brooklyn, NY"
        pytest.buyer_test_listing_id = data["id"]

    def test_buyer_riby_dtc_rejected(self, buyer_tok):
        payload = {
            "title": "TEST_Invalid Buyer DTC",
            "description": "should fail",
            "photos": [],
            "category": "general-goods",
            "retail_price_usd": 10.0,
            "stock_qty": 1,
            "fulfillment_mode": "riby_dtc",
        }
        r = requests.post(f"{BASE_URL}/api/shop/listings", headers=_h(buyer_tok), json=payload, timeout=15)
        assert r.status_code == 400, f"expected 400 got {r.status_code}: {r.text}"


class TestListingsMineAndMutations:
    def test_exporter_listings_mine_has_created(self, exporter_tok):
        r = requests.get(f"{BASE_URL}/api/shop/listings/mine", headers=_h(exporter_tok), timeout=15)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        assert len(items) >= 1
        # Expect the newly created listing is present
        lid = getattr(pytest, "exporter_test_listing_id", None)
        if lid:
            assert any(it["id"] == lid for it in items), "Newly created exporter listing missing from /mine"

    def test_patch_own_listing_title(self, exporter_tok):
        lid = getattr(pytest, "exporter_test_listing_id", None)
        if not lid:
            pytest.skip("no test listing id")
        new_title = f"TEST_Updated {uuid.uuid4().hex[:6]}"
        r = requests.patch(f"{BASE_URL}/api/shop/listings/{lid}", headers=_h(exporter_tok),
                           json={"title": new_title}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["title"] == new_title
        # verify persistence
        g = requests.get(f"{BASE_URL}/api/shop/listings/{lid}", timeout=15).json()
        assert g["title"] == new_title

    def test_delete_own_listing_cleanup(self, exporter_tok, buyer_tok):
        # cleanup both exporter + buyer TEST_ listings
        for tok, attr in [(exporter_tok, "exporter_test_listing_id"), (buyer_tok, "buyer_test_listing_id")]:
            lid = getattr(pytest, attr, None)
            if not lid:
                continue
            r = requests.delete(f"{BASE_URL}/api/shop/listings/{lid}", headers=_h(tok), timeout=15)
            assert r.status_code == 200, f"delete {lid} failed: {r.text}"
            # 404 afterwards
            g = requests.get(f"{BASE_URL}/api/shop/listings/{lid}", timeout=15)
            assert g.status_code == 404


# =====================================================================
# (b) Atomic stock decrement under concurrency
# =====================================================================
class TestAtomicStock:
    def test_concurrent_checkout_single_stock(self, exporter_tok, shopper_tok):
        # 1. Exporter creates a stock_qty=1 DTC listing
        payload = {
            "title": f"TEST_SingleStock {uuid.uuid4().hex[:6]}",
            "description": "last one",
            "photos": [],
            "category": "fashion",
            "retail_price_usd": 9.99,
            "stock_qty": 1,
            "fulfillment_mode": "riby_dtc",
        }
        r = requests.post(f"{BASE_URL}/api/shop/listings", headers=_h(exporter_tok), json=payload, timeout=15)
        assert r.status_code == 200, r.text
        lid = r.json()["id"]

        # 2. Fire two concurrent orders
        order_payload = {
            "listing_id": lid,
            "quantity": 1,
            "shipping_name": "Test Shopper",
            "shipping_address": "1 Test St, NY",
            "shipping_email": "shopper@helix.com",
            "shipping_phone": "+15555550100",
        }
        results = [None, None]

        def _place(i):
            try:
                resp = requests.post(f"{BASE_URL}/api/shop/orders", headers=_h(shopper_tok),
                                     json=order_payload, timeout=20)
                results[i] = (resp.status_code, resp.text)
            except Exception as e:  # pragma: no cover
                results[i] = (0, str(e))

        t1 = threading.Thread(target=_place, args=(0,))
        t2 = threading.Thread(target=_place, args=(1,))
        t1.start()
        t2.start()
        t1.join(timeout=30)
        t2.join(timeout=30)

        codes = sorted([results[0][0], results[1][0]])
        # exactly one 200 and one 400
        assert codes == [200, 400], f"Expected [200, 400], got {codes}. r1={results[0]} r2={results[1]}"

        # 3. Verify listing is now out_of_stock
        g = requests.get(f"{BASE_URL}/api/shop/listings/{lid}", timeout=15).json()
        assert g["stock_qty"] == 0
        assert g["status"] == "out_of_stock"

        # cleanup
        requests.delete(f"{BASE_URL}/api/shop/listings/{lid}", headers=_h(exporter_tok), timeout=15)


# =====================================================================
# (c) simulate-payment auto-debit resilience
# =====================================================================
class TestSimulatePaymentResilience:
    def test_simulate_payment_returns_200_no_outstanding(self, buyer_tok, exporter_tok):
        """End-to-end RFQ → proforma → simulate-payment. Must be 200 even if
        auto_debit raises (gracefully) or returns None when no outstanding loan."""
        # Find an exporter product to RFQ against
        prods = requests.get(f"{BASE_URL}/api/products", timeout=15).json()
        exp_prod = None
        # filter to exporter business
        for p in prods:
            if "country" in p and p.get("country") == "Nigeria":
                exp_prod = p
                break
        if not exp_prod:
            # fallback — take the first product
            exp_prod = prods[0] if prods else None
        if not exp_prod:
            pytest.skip("no products available for RFQ")

        rfq = {
            "product_id": exp_prod["id"],
            "quantity": 2,
            "delivery_address": "100 Test Ave, Brooklyn NY",
            "target_delivery_date": "2026-06-01",
            "message": "TEST retest iter4",
        }
        r = requests.post(f"{BASE_URL}/api/rfq", headers=_h(buyer_tok), json=rfq, timeout=20)
        assert r.status_code == 200, r.text
        oid = r.json()["id"]

        # proforma issued by supplier (exporter)
        r2 = requests.post(f"{BASE_URL}/api/orders/{oid}/proforma", headers=_h(exporter_tok), timeout=20)
        assert r2.status_code == 200, r2.text

        # simulate-payment from buyer context (any authenticated user works in mock)
        r3 = requests.post(f"{BASE_URL}/api/orders/{oid}/simulate-payment", headers=_h(buyer_tok), timeout=20)
        assert r3.status_code == 200, f"simulate-payment returned {r3.status_code}: {r3.text}"
        body = r3.json()
        assert body["status"] == "confirmed"
        assert body["amount"] == r.json()["agreed_price_usd"]
        # key must be present — null or a dict depending on outstanding loan
        assert "jompstart_auto_debit" in body
        # if exporter has no outstanding loan → None; if has → dict with id/amount
        if body["jompstart_auto_debit"] is not None:
            assert isinstance(body["jompstart_auto_debit"], dict)
            assert "amount" in body["jompstart_auto_debit"]


# =====================================================================
# (d) Regression: buyer_local consumer checkout still works
# =====================================================================
class TestBuyerLocalRegression:
    def test_consumer_buy_seeded_buyer_local(self, shopper_tok):
        # Fetch active buyer_local listings
        r = requests.get(f"{BASE_URL}/api/shop/listings?fulfillment=buyer_local", timeout=15)
        assert r.status_code == 200
        listings = r.json()
        # need something with stock
        target = next((l for l in listings if l.get("stock_qty", 0) > 0), None)
        if not target:
            pytest.skip("no buyer_local listing with stock to checkout")

        order_payload = {
            "listing_id": target["id"],
            "quantity": 1,
            "shipping_name": "Regression Shopper",
            "shipping_address": "77 Regression Rd, Brooklyn NY",
            "shipping_email": "shopper@helix.com",
            "shipping_phone": "+15555550111",
        }
        r2 = requests.post(f"{BASE_URL}/api/shop/orders", headers=_h(shopper_tok), json=order_payload, timeout=20)
        assert r2.status_code == 200, r2.text
        o = r2.json()
        assert o["status"] == "paid"
        assert o["quantity"] == 1
        assert o["total_usd"] == target["retail_price_usd"]
        assert o["fulfillment_mode"] == "buyer_local"
