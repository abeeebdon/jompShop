"""Helix Platform backend regression tests.

Covers all 5 modules: Auth, Catalog, Onboarding/KYB, Orders/PDF, Compliance, Finance, Webhooks.
Hits the live preview URL through /api prefix. Anchor is mocked via ANCHOR_ENV=sandbox_mock.
"""
import io
import os
import time
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://trade-nexus-110.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
PASSWORD = "Helix@123"

# ------------- session helpers -------------

def _login(email: str) -> str:
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": PASSWORD}, timeout=30)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    data = r.json()
    assert "access_token" in data and data["user"]["email"] == email
    return data["access_token"]


@pytest.fixture(scope="session")
def admin_token():
    return _login("admin@helix.com")


@pytest.fixture(scope="session")
def exporter_token():
    return _login("exporter@helix.com")


@pytest.fixture(scope="session")
def buyer_token():
    return _login("buyer@helix.com")


def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


# ------------- 1. Service metadata + auth -------------

class TestService:
    def test_root(self):
        r = requests.get(f"{API}", timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["service"] == "Helix Platform"
        assert d["anchor_env"] == "sandbox_mock"

    def test_login_exporter(self, exporter_token):
        assert exporter_token

    def test_me(self, exporter_token):
        r = requests.get(f"{API}/auth/me", headers=_h(exporter_token), timeout=20)
        assert r.status_code == 200
        u = r.json()
        assert u["email"] == "exporter@helix.com"
        assert u["business_id"]
        assert "_id" not in u

    def test_register_new_user(self):
        email = f"test_{uuid.uuid4().hex[:8]}@helix.com"
        r = requests.post(f"{API}/auth/register", json={
            "email": email, "password": PASSWORD, "name": "Test User", "role": "buyer",
        }, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["access_token"] and d["user"]["email"] == email
        # verify token works
        me = requests.get(f"{API}/auth/me", headers=_h(d["access_token"]), timeout=20)
        assert me.status_code == 200

    def test_unauth_protected(self):
        r = requests.get(f"{API}/auth/me", timeout=20)
        assert r.status_code == 401

    def test_buyer_cannot_admin(self, buyer_token):
        r = requests.get(f"{API}/admin/verifications", headers=_h(buyer_token), timeout=20)
        assert r.status_code == 403


# ------------- 2. FX + Catalog -------------

class TestCatalog:
    def test_fx(self):
        r = requests.get(f"{API}/fx", timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d.get("usd_to_ngn"), (int, float)) and d["usd_to_ngn"] > 0

    def test_list_products(self):
        r = requests.get(f"{API}/products", timeout=20)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list) and len(items) >= 6, f"expected >=6 seeded products, got {len(items)}"
        for p in items:
            assert "_id" not in p
            assert p["status"] == "active"

    def test_get_product(self):
        items = requests.get(f"{API}/products", timeout=20).json()
        pid = items[0]["id"]
        r = requests.get(f"{API}/products/{pid}", timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["product"]["id"] == pid
        assert d["supplier"] is not None and "_id" not in d["supplier"]

    def test_products_mine_exporter(self, exporter_token):
        r = requests.get(f"{API}/products/mine", headers=_h(exporter_token), timeout=20)
        assert r.status_code == 200
        items = r.json()
        assert len(items) >= 6

    def test_create_update_delete(self, exporter_token):
        payload = {
            "name": f"TEST_Product_{uuid.uuid4().hex[:6]}",
            "category": "fashion",
            "description": "test product",
            "price_usd": 100.0,
            "min_order_qty": 5,
            "unit": "piece",
            "status": "draft",
        }
        r = requests.post(f"{API}/products", headers=_h(exporter_token), json=payload, timeout=20)
        assert r.status_code == 200, r.text
        prod = r.json()
        pid = prod["id"]
        assert prod["price_ngn"] > 0  # auto FX
        assert prod["price_usd"] == 100.0

        # update
        r2 = requests.patch(f"{API}/products/{pid}", headers=_h(exporter_token),
                            json={"price_usd": 250.0, "status": "active"}, timeout=20)
        assert r2.status_code == 200
        u = r2.json()
        assert u["price_usd"] == 250.0
        assert u["status"] == "active"
        assert u["price_ngn"] > prod["price_ngn"]  # recomputed

        # delete
        r3 = requests.delete(f"{API}/products/{pid}", headers=_h(exporter_token), timeout=20)
        assert r3.status_code == 200
        # verify gone
        g = requests.get(f"{API}/products/{pid}", timeout=20)
        assert g.status_code == 404


# ------------- 3. Businesses / KYC-KYB / Admin verify -------------

class TestOnboarding:
    def test_business_me_exporter(self, exporter_token):
        r = requests.get(f"{API}/businesses/me", headers=_h(exporter_token), timeout=20)
        assert r.status_code == 200
        biz = r.json()
        assert biz and biz["business_name"]
        assert biz.get("anchor_customer_id")

    def test_admin_verifications(self, admin_token):
        r = requests.get(f"{API}/admin/verifications", headers=_h(admin_token), timeout=20)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_business_creation_kyb_and_admin_decide(self, admin_token):
        # fresh user -> register -> create business -> kyb -> admin approve
        email = f"kyb_{uuid.uuid4().hex[:6]}@helix.com"
        reg = requests.post(f"{API}/auth/register", json={
            "email": email, "password": PASSWORD, "name": "KYB User", "role": "exporter"}, timeout=20)
        assert reg.status_code == 200
        tok = reg.json()["access_token"]

        # try to create product before business -> should fail
        bad = requests.post(f"{API}/products", headers=_h(tok), json={
            "name": "X", "category": "fashion", "price_usd": 1}, timeout=20)
        assert bad.status_code == 400

        biz_payload = {
            "business_name": f"TEST_Biz_{uuid.uuid4().hex[:5]}",
            "registration_type": "business",
            "country": "Nigeria",
            "sector": "fashion",
            "role": "exporter",
            "cac_number": "RC1234567",
            "tin": "12345678-0001",
        }
        r = requests.post(f"{API}/businesses", headers=_h(tok), json=biz_payload, timeout=30)
        assert r.status_code == 200, r.text
        biz = r.json()
        bid = biz["id"]
        assert biz["anchor_customer_id"]  # mock created

        # KYB
        r2 = requests.post(f"{API}/businesses/{bid}/kyb", headers=_h(tok), json={
            "docs": ["/storage/cac.pdf"], "cac_number": "RC1234567", "director_name": "John Doe"}, timeout=20)
        assert r2.status_code == 200
        assert r2.json()["kyb_status"] == "under_review"

        # Admin sees it & decides
        adm = requests.get(f"{API}/admin/verifications", headers=_h(admin_token), timeout=20).json()
        assert any(b["id"] == bid for b in adm)

        dec = requests.post(f"{API}/admin/verifications/{bid}/decide", headers=_h(admin_token),
                            json={"decision": "approved", "note": "ok"}, timeout=30)
        assert dec.status_code == 200, dec.text
        assert dec.json()["decision"] == "approved"

        # verify accounts provisioned
        meb = requests.get(f"{API}/businesses/me", headers=_h(tok), timeout=20).json()
        assert meb["kyb_status"] == "approved"
        assert meb["anchor_account_ngn"] and meb["anchor_account_usd"]
        assert meb["anchor_ngn_virtual_account"] and meb["anchor_usd_virtual_account"]


# ------------- 4. Orders / PDF / Lifecycle -------------

class TestOrders:
    def test_orders_mine_exporter(self, exporter_token):
        r = requests.get(f"{API}/orders/mine", headers=_h(exporter_token), timeout=20)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list) and len(items) >= 1

    def test_full_order_flow_buyer_to_payment(self, buyer_token, exporter_token):
        # pick a product
        items = requests.get(f"{API}/products", timeout=20).json()
        pid = items[0]["id"]

        # buyer submits RFQ
        r = requests.post(f"{API}/rfq", headers=_h(buyer_token), json={
            "product_id": pid, "quantity": 3, "delivery_address": "Brooklyn NY",
            "target_delivery_date": "2026-06-01", "message": "TEST_RFQ"}, timeout=20)
        assert r.status_code == 200, r.text
        order = r.json()
        oid = order["id"]
        assert order["status"] == "draft"
        assert order["agreed_price_usd"] == order["unit_price_usd"] * 3

        # supplier (exporter) issues proforma
        r2 = requests.post(f"{API}/orders/{oid}/proforma", headers=_h(exporter_token), timeout=30)
        assert r2.status_code == 200, r2.text
        upd = r2.json()
        assert upd["status"] == "confirmed"
        assert upd["anchor_reserved_account_number"]

        # idempotency: second proforma should 400
        r2b = requests.post(f"{API}/orders/{oid}/proforma", headers=_h(exporter_token), timeout=20)
        assert r2b.status_code == 400

        # buyer simulates payment
        r3 = requests.post(f"{API}/orders/{oid}/simulate-payment", headers=_h(buyer_token), timeout=20)
        assert r3.status_code == 200, r3.text
        d = r3.json()
        assert d["status"] == "confirmed"
        assert d["fee"] == round(order["agreed_price_usd"] * 0.01, 2)

        # advance status
        r4 = requests.post(f"{API}/orders/{oid}/status", headers=_h(exporter_token),
                           json={"status": "ready_to_ship"}, timeout=20)
        assert r4.status_code == 200
        assert r4.json()["new_status"] == "ready_to_ship"

        # PDFs - test all 4 doc types
        for doc_type in ("proforma", "commercial", "packing", "origin"):
            rp = requests.get(f"{API}/orders/{oid}/pdf/{doc_type}", headers=_h(exporter_token), timeout=30)
            assert rp.status_code == 200, f"{doc_type}: {rp.status_code}"
            assert rp.headers.get("content-type", "").startswith("application/pdf")
            assert rp.content[:4] == b"%PDF", f"{doc_type} not PDF"
            assert len(rp.content) > 500


# ------------- 5. Compliance -------------

class TestCompliance:
    def test_documents(self, exporter_token):
        r = requests.get(f"{API}/compliance/documents", headers=_h(exporter_token), timeout=20)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list) and len(items) >= 1

    def test_score(self, exporter_token):
        r = requests.get(f"{API}/compliance/score", headers=_h(exporter_token), timeout=20)
        assert r.status_code == 200
        d = r.json()
        for k in ("score", "missing", "category_scores"):
            assert k in d
        assert isinstance(d["score"], int)

    def test_requirements(self):
        r = requests.get(f"{API}/compliance/requirements?category=fashion", timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["category"] == "fashion"
        assert isinstance(d["required"], list) and len(d["required"]) >= 1
        assert isinstance(d["us_import_guide"], list) and len(d["us_import_guide"]) >= 1

    def test_add_document(self, exporter_token):
        payload = {
            "document_type": "TEST_DOC",
            "file_url": "/storage/test.pdf",
            "original_filename": "test.pdf",
            "issuing_authority": "Test Authority",
            "expiry_date": "2027-01-01T00:00:00",
        }
        r = requests.post(f"{API}/compliance/documents", headers=_h(exporter_token), json=payload, timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["document_type"] == "TEST_DOC"
        # cleanup
        requests.delete(f"{API}/compliance/documents/{d['id']}", headers=_h(exporter_token), timeout=20)


# ------------- 6. Finance -------------

class TestFinance:
    def test_dashboard(self, exporter_token):
        r = requests.get(f"{API}/finance/dashboard", headers=_h(exporter_token), timeout=20)
        assert r.status_code == 200
        d = r.json()
        for k in ("ngn_balance", "usd_balance", "recent_transactions", "virtual_accounts"):
            assert k in d
        # seed: 15600 credit minus 156 fee = 15444 (>= since other tests in same run may add credits)
        assert d["usd_balance"] >= 15444.0, f"usd_balance expected >=15444 got {d['usd_balance']}"
        assert d["virtual_accounts"]["ngn"]["account_number"]
        assert d["virtual_accounts"]["usd"]["account_number"]

    def test_transactions(self, exporter_token):
        r = requests.get(f"{API}/finance/transactions", headers=_h(exporter_token), timeout=20)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list) and len(items) >= 2

    def test_withdraw_insufficient_ngn(self, exporter_token):
        # withdraw amount large enough to guarantee insufficient
        r = requests.post(f"{API}/finance/withdraw", headers=_h(exporter_token), json={
            "amount": 999_999_999_999, "bank_code": "044", "account_number": "0123456789", "narration": "TEST_WD"}, timeout=20)
        assert r.status_code == 400, r.text  # insufficient

    def test_admin_overview(self, admin_token):
        r = requests.get(f"{API}/admin/finance/overview", headers=_h(admin_token), timeout=20)
        assert r.status_code == 200
        d = r.json()
        for k in ("total_volume_by_currency", "fees_collected_usd", "by_sector", "order_count", "business_count"):
            assert k in d


# ------------- 7. Webhook -------------

class TestWebhooks:
    def test_anchor_webhook_mock(self):
        r = requests.post(f"{API}/webhooks/anchor", json={
            "type": "account.credited", "data": {"reference": "non-existent-order"}}, timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["ok"] is True
