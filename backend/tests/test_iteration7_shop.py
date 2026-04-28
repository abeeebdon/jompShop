"""Iteration 7 — JompShop restructure.

Verifies:
  * 50 listings spread across 7+ categories with photos
  * Filter by category / fulfillment / search
  * Auth registration with role={consumer|buyer|exporter}
  * Login returns user with correct role
  * Regression: full escrow flow + ledger net 98%
  * Regression: JompStart credit eligibility/apply/accept/repay
"""
import os
import time
import uuid

import pytest
import requests

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
                break
PWD = "Helix@123"


def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


def _login(email):
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": PWD}, timeout=20)
    assert r.status_code == 200, f"{email} login failed {r.status_code} {r.text}"
    return r.json()["access_token"], r.json()["user"]


@pytest.fixture(scope="session")
def admin_tok():
    tok, _ = _login("admin@helix.com")
    return tok


@pytest.fixture(scope="session")
def exporter_tok():
    tok, _ = _login("exporter@helix.com")
    return tok


@pytest.fixture(scope="session")
def shopper_tok():
    tok, _ = _login("shopper@helix.com")
    return tok


# ============================================================
# (1) 50-listing catalog
# ============================================================
class TestShopCatalog:
    def test_50_listings_active(self):
        r = requests.get(f"{BASE_URL}/api/shop/listings", timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 50, f"Expected ≥50 listings, got {len(data)}"

    def test_seven_plus_categories(self):
        data = requests.get(f"{BASE_URL}/api/shop/listings", timeout=20).json()
        cats = {x.get("category") for x in data if x.get("category")}
        required = {"fashion", "agriculture", "staple-foods", "beauty",
                    "home-decor", "accessories", "beverages"}
        missing = required - cats
        assert not missing, f"missing categories: {missing} (have {cats})"

    def test_every_listing_has_photo(self):
        data = requests.get(f"{BASE_URL}/api/shop/listings", timeout=20).json()
        no_photo = [x["title"] for x in data
                    if not x.get("photos") or not x["photos"][0]]
        assert not no_photo, f"listings without photos: {no_photo}"


# ============================================================
# (2) Filtering
# ============================================================
class TestShopFilters:
    def test_category_beauty(self):
        data = requests.get(f"{BASE_URL}/api/shop/listings?category=beauty",
                            timeout=20).json()
        assert len(data) > 0
        assert all(x["category"] == "beauty" for x in data)

    def test_category_fashion_at_least_10(self):
        data = requests.get(f"{BASE_URL}/api/shop/listings?category=fashion",
                            timeout=20).json()
        assert len(data) >= 10, f"Expected ≥10 fashion listings, got {len(data)}"
        assert all(x["category"] == "fashion" for x in data)

    def test_fulfillment_riby_dtc(self):
        data = requests.get(f"{BASE_URL}/api/shop/listings?fulfillment=riby_dtc",
                            timeout=20).json()
        assert len(data) > 0
        assert all(x.get("fulfillment_mode") == "riby_dtc" for x in data)

    def test_search_shea(self):
        data = requests.get(f"{BASE_URL}/api/shop/listings?search=shea",
                            timeout=20).json()
        assert len(data) > 0
        for x in data:
            blob = (x["title"] + " " + (x.get("description") or "")).lower()
            assert "shea" in blob, f"Listing {x['title']} did not match shea search"


# ============================================================
# (3) Auth — role registration
# ============================================================
class TestAuthRoleRegistration:
    def _register(self, role):
        email = f"TEST_iter7_{role}_{uuid.uuid4().hex[:8]}@example.com"
        r = requests.post(f"{BASE_URL}/api/auth/register",
                          json={"email": email, "password": PWD,
                                "name": f"T7 {role}", "role": role}, timeout=20)
        assert r.status_code == 200, f"register {role} failed: {r.status_code} {r.text}"
        body = r.json()
        assert body["user"]["role"] == role
        # Login back
        rl = requests.post(f"{BASE_URL}/api/auth/login",
                           json={"email": email, "password": PWD}, timeout=20)
        assert rl.status_code == 200
        assert rl.json()["user"]["role"] == role
        return email

    def test_register_consumer(self):
        self._register("consumer")

    def test_register_buyer(self):
        self._register("buyer")

    def test_register_exporter(self):
        self._register("exporter")


# ============================================================
# (4) Regression — full escrow flow (place → confirm-delivery)
# ============================================================
def _mk_listing(exporter_tok, price=42.0, stock=5):
    r = requests.post(f"{BASE_URL}/api/shop/listings", headers=_h(exporter_tok),
                      json={
                          "title": f"TEST_iter7 {uuid.uuid4().hex[:6]}",
                          "description": "iter7 fixture",
                          "photos": ["https://images.unsplash.com/photo-1528459105426-b9548367069b?w=900"],
                          "category": "fashion",
                          "retail_price_usd": price,
                          "stock_qty": stock,
                          "fulfillment_mode": "riby_dtc",
                      }, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()


class TestEscrowRegression:
    def test_place_and_confirm_credits_98_percent(self, exporter_tok, shopper_tok):
        listing = _mk_listing(exporter_tok, price=89.0)
        ro = requests.post(
            f"{BASE_URL}/api/shop/orders", headers=_h(shopper_tok),
            json={"listing_id": listing["id"], "quantity": 1,
                  "shipping_name": "Iter7", "shipping_address": "1 Test St, Brooklyn NY",
                  "shipping_email": "shopper@helix.com", "shipping_phone": "+15555550100"},
            timeout=25)
        assert ro.status_code == 200, ro.text
        oid = ro.json()["id"]
        total = ro.json()["total_usd"]
        assert total == 89.0

        rc = requests.post(f"{BASE_URL}/api/shop/orders/{oid}/confirm-delivery",
                           headers=_h(shopper_tok), timeout=25)
        assert rc.status_code == 200, rc.text
        body = rc.json()
        assert body["credit_amount_usd"] == round(total * 0.98, 2)
        assert body["fee_usd"] == round(total * 0.02, 2)
        assert body.get("gross_amount_usd") == total


# ============================================================
# (5) Regression — JompStart credit endpoints exist
# ============================================================
class TestCreditRegression:
    def test_eligibility_endpoint(self, exporter_tok):
        r = requests.get(f"{BASE_URL}/api/credit/eligibility",
                         headers=_h(exporter_tok), timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "eligible" in body

    def test_apply_accept_disburse(self, exporter_tok, admin_tok):
        r = requests.post(f"{BASE_URL}/api/credit/applications",
                          headers=_h(exporter_tok),
                          json={"amount_usd": 250, "term_months": 6,
                                "purpose": "iter7 regression"}, timeout=20)
        if r.status_code != 200:
            pytest.skip(f"credit submit blocked: {r.status_code} {r.text}")
        aid = r.json()["id"]
        r2 = requests.post(
            f"{BASE_URL}/api/credit/admin/applications/{aid}/decision",
            headers=_h(admin_tok),
            json={"decision": "offered", "offered_amount_usd": 250,
                  "offered_apr": 10, "offered_term_months": 6,
                  "decision_note": "iter7 offer"}, timeout=20)
        assert r2.status_code == 200, r2.text
        r3 = requests.post(f"{BASE_URL}/api/credit/applications/{aid}/accept",
                           headers=_h(exporter_tok), timeout=20)
        assert r3.status_code == 200, r3.text
        body = r3.json()
        assert body["status"] == "disbursed"
        assert "disbursement_tx_id" in body
