"""Iteration 3 — Consumer e-commerce + JompStart repayment/auto-debit + role isolation tests."""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    # fall back to frontend .env
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip()
                    break
    except FileNotFoundError:
        pass
BASE_URL = (BASE_URL or "").rstrip("/")

PWD = "Helix@123"


def _login(email: str) -> str:
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": PWD}, timeout=15)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


def _h(tok: str) -> dict:
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


# ---------- Fixtures ----------

@pytest.fixture(scope="session")
def admin_tok():
    return _login("admin@helix.com")

@pytest.fixture(scope="session")
def jomp_tok():
    return _login("credit@jompstart.com")

@pytest.fixture(scope="session")
def exporter_tok():
    return _login("exporter@helix.com")

@pytest.fixture(scope="session")
def buyer_tok():
    return _login("buyer@helix.com")

@pytest.fixture(scope="session")
def consumer_tok():
    return _login("shopper@helix.com")


# ---------- Shop listings (public) ----------

class TestShopListings:
    def test_list_all_unauth(self):
        r = requests.get(f"{BASE_URL}/api/shop/listings", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 3, f"expected >=3 seeded listings, got {len(data)}"
        modes = [i["fulfillment_mode"] for i in data]
        assert modes.count("buyer_local") >= 1
        assert modes.count("riby_dtc") >= 2
        for it in data:
            if it["fulfillment_mode"] == "riby_dtc":
                assert it.get("delivery_partner_of_record") == "Riby Inc"
            assert "seller_name" in it
            assert "_id" not in it

    def test_filter_riby_dtc(self):
        r = requests.get(f"{BASE_URL}/api/shop/listings?fulfillment=riby_dtc", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 2
        assert all(i["fulfillment_mode"] == "riby_dtc" for i in data)

    def test_filter_buyer_local(self):
        r = requests.get(f"{BASE_URL}/api/shop/listings?fulfillment=buyer_local", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        assert all(i["fulfillment_mode"] == "buyer_local" for i in data)

    def test_get_listing_detail_unauth(self):
        r = requests.get(f"{BASE_URL}/api/shop/listings", timeout=15)
        lid = r.json()[0]["id"]
        r = requests.get(f"{BASE_URL}/api/shop/listings/{lid}", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "seller" in data
        assert "business_name" in data["seller"]


# ---------- Shop listings create guardrails ----------

class TestListingGuardrails:
    def test_exporter_riby_dtc_ok(self, exporter_tok):
        payload = {
            "title": "TEST_Exporter DTC Listing",
            "description": "test",
            "photos": [],
            "category": "fashion",
            "retail_price_usd": 25.0,
            "stock_qty": 5,
            "fulfillment_mode": "riby_dtc",
            "ships_from": "Lagos",
        }
        r = requests.post(f"{BASE_URL}/api/shop/listings", headers=_h(exporter_tok), json=payload, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["delivery_partner_of_record"] == "Riby Inc"
        assert data["fulfillment_mode"] == "riby_dtc"
        # cleanup
        requests.delete(f"{BASE_URL}/api/shop/listings/{data['id']}", headers=_h(exporter_tok), timeout=15)

    def test_exporter_buyer_local_forbidden(self, exporter_tok):
        payload = {
            "title": "TEST_Exporter Local",
            "retail_price_usd": 10,
            "stock_qty": 1,
            "fulfillment_mode": "buyer_local",
            "category": "fashion",
        }
        r = requests.post(f"{BASE_URL}/api/shop/listings", headers=_h(exporter_tok), json=payload, timeout=15)
        assert r.status_code == 400

    def test_buyer_local_ok(self, buyer_tok):
        payload = {
            "title": "TEST_Buyer Local Listing",
            "retail_price_usd": 15.0,
            "stock_qty": 3,
            "fulfillment_mode": "buyer_local",
            "category": "general-goods",
        }
        r = requests.post(f"{BASE_URL}/api/shop/listings", headers=_h(buyer_tok), json=payload, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["fulfillment_mode"] == "buyer_local"
        requests.delete(f"{BASE_URL}/api/shop/listings/{data['id']}", headers=_h(buyer_tok), timeout=15)

    def test_buyer_riby_dtc_forbidden(self, buyer_tok):
        payload = {
            "title": "TEST_Buyer DTC",
            "retail_price_usd": 10,
            "stock_qty": 1,
            "fulfillment_mode": "riby_dtc",
            "category": "general-goods",
        }
        r = requests.post(f"{BASE_URL}/api/shop/listings", headers=_h(buyer_tok), json=payload, timeout=15)
        assert r.status_code == 400


# ---------- Consumer checkout & finance ----------

class TestConsumerCheckout:
    def test_consumer_checkout_flow(self, consumer_tok, exporter_tok):
        # pick buyer_local listing so it hits buyer ledger (avoid interfering with exporter JompStart tests)
        listings = requests.get(f"{BASE_URL}/api/shop/listings?fulfillment=buyer_local", timeout=15).json()
        listing = listings[0]
        initial_stock = listing["stock_qty"]

        payload = {
            "listing_id": listing["id"],
            "quantity": 1,
            "shipping_name": "Jordan Bell",
            "shipping_address": "123 Test St, NY",
            "shipping_email": "shopper@helix.com",
            "shipping_phone": "555-0000",
        }
        r = requests.post(f"{BASE_URL}/api/shop/orders", headers=_h(consumer_tok), json=payload, timeout=20)
        assert r.status_code == 200, r.text
        order = r.json()
        assert order["order_number"].startswith("SHP-")
        assert order["status"] == "paid"
        assert order["total_usd"] == listing["retail_price_usd"]
        assert order["payment_ref"].startswith("shop_pay_")

        # stock decremented
        r2 = requests.get(f"{BASE_URL}/api/shop/listings/{listing['id']}", timeout=15)
        assert r2.json()["stock_qty"] == initial_stock - 1

        # consumer's orders
        r3 = requests.get(f"{BASE_URL}/api/shop/orders/mine", headers=_h(consumer_tok), timeout=15)
        assert r3.status_code == 200
        ids = [o["id"] for o in r3.json()]
        assert order["id"] in ids

    def test_consumer_checkout_credits_seller_and_fee(self, consumer_tok, buyer_tok):
        # Grab finance snapshot before
        fin_before = requests.get(f"{BASE_URL}/api/finance/dashboard", headers=_h(buyer_tok), timeout=15).json()

        # Place order on a buyer_local listing
        listings = requests.get(f"{BASE_URL}/api/shop/listings?fulfillment=buyer_local", timeout=15).json()
        listing = listings[0]
        r = requests.post(f"{BASE_URL}/api/shop/orders", headers=_h(consumer_tok), json={
            "listing_id": listing["id"], "quantity": 1,
            "shipping_name": "Jordan", "shipping_address": "NY",
            "shipping_email": "shopper@helix.com",
        }, timeout=20)
        assert r.status_code == 200, r.text
        total = r.json()["total_usd"]
        expected_fee = round(total * 0.02, 2)
        expected_credit = round(total - expected_fee, 2)

        # check transactions in finance ledger for shop events
        txs = requests.get(f"{BASE_URL}/api/finance/transactions", headers=_h(buyer_tok), timeout=15).json()
        shop_credits = [t for t in txs if t.get("anchor_event_type") == "shop.order.paid"]
        shop_fees = [t for t in txs if t.get("anchor_event_type") == "shop.fee.applied"]
        assert any(abs(t["amount"] - expected_credit) < 0.02 for t in shop_credits), \
            f"expected shop.order.paid credit of {expected_credit}"
        assert any(abs(t["amount"] - expected_fee) < 0.02 for t in shop_fees), \
            f"expected shop.fee.applied fee of {expected_fee}"

    def test_fulfillment_and_ship_deliver(self, consumer_tok, buyer_tok):
        # consumer places an order on buyer_local
        listings = requests.get(f"{BASE_URL}/api/shop/listings?fulfillment=buyer_local", timeout=15).json()
        listing = listings[0]
        r = requests.post(f"{BASE_URL}/api/shop/orders", headers=_h(consumer_tok), json={
            "listing_id": listing["id"], "quantity": 1,
            "shipping_name": "Jordan", "shipping_address": "NY",
            "shipping_email": "shopper@helix.com",
        }, timeout=20)
        assert r.status_code == 200
        oid = r.json()["id"]

        # seller (buyer) sees fulfillment queue
        fq = requests.get(f"{BASE_URL}/api/shop/orders/fulfillment", headers=_h(buyer_tok), timeout=15).json()
        assert oid in [o["id"] for o in fq]

        # ship
        sr = requests.post(f"{BASE_URL}/api/shop/orders/{oid}/ship", headers=_h(buyer_tok),
                           json={}, timeout=15)
        assert sr.status_code == 200, sr.text
        assert sr.json()["tracking_number"]

        # delivered
        dr = requests.post(f"{BASE_URL}/api/shop/orders/{oid}/delivered", headers=_h(buyer_tok),
                           json={}, timeout=15)
        assert dr.status_code == 200


# ---------- JompStart admin role isolation ----------

class TestJompStartRoleIsolation:
    def test_jomp_can_list_credit(self, jomp_tok):
        r = requests.get(f"{BASE_URL}/api/credit/admin/applications", headers=_h(jomp_tok), timeout=15)
        assert r.status_code == 200

    def test_jomp_blocked_from_verifications(self, jomp_tok):
        r = requests.get(f"{BASE_URL}/api/admin/verifications", headers=_h(jomp_tok), timeout=15)
        assert r.status_code == 403, f"expected 403 got {r.status_code}"

    def test_jomp_blocked_from_disputes(self, jomp_tok):
        r = requests.get(f"{BASE_URL}/api/admin/disputes", headers=_h(jomp_tok), timeout=15)
        assert r.status_code == 403

    def test_jomp_blocked_from_finance_overview(self, jomp_tok):
        r = requests.get(f"{BASE_URL}/api/admin/finance/overview", headers=_h(jomp_tok), timeout=15)
        assert r.status_code == 403


# ---------- JompStart schedule + auto-debit ----------

class TestJompStartRepayment:
    @pytest.fixture(scope="class")
    def app_id(self, exporter_tok, jomp_tok):
        """Submit & accept a $5000/6mo credit application via JompStart admin."""
        # Submit
        r = requests.post(f"{BASE_URL}/api/credit/applications", headers=_h(exporter_tok), json={
            "amount_usd": 5000, "term_months": 6, "purpose": "TEST_repayment"
        }, timeout=15)
        if r.status_code != 200:
            pytest.skip(f"Could not create credit app: {r.status_code} {r.text}")
        aid = r.json()["id"]

        # JompStart admin offers
        d = requests.post(f"{BASE_URL}/api/credit/admin/applications/{aid}/decision",
                          headers=_h(jomp_tok),
                          json={"decision": "offered", "offered_amount_usd": 5000,
                                "offered_apr": 15, "offered_term_months": 6,
                                "decision_note": "test offer"}, timeout=15)
        assert d.status_code == 200, d.text

        # Exporter accepts → disbursed + schedule
        a = requests.post(f"{BASE_URL}/api/credit/applications/{aid}/accept",
                          headers=_h(exporter_tok), timeout=15)
        assert a.status_code == 200, a.text
        return aid

    def test_schedule_created(self, exporter_tok, app_id):
        r = requests.get(f"{BASE_URL}/api/credit/applications/{app_id}/repayment",
                         headers=_h(exporter_tok), timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert len(data["installments"]) == 6
        # amortized 5000 @ 15% APR / 6mo ≈ 870.32 monthly, sum ≈ 5222
        per = data["installments"][0]["total_due_usd"]
        assert 850 <= per <= 900, f"monthly payment out of range: {per}"
        assert 5180 <= data["total_due_usd"] <= 5260, f"total due out of range: {data['total_due_usd']}"
        assert all(i["status"] == "pending" for i in data["installments"])

    def test_auto_debit_on_trade_payment(self, exporter_tok, app_id):
        # Find a pending order (supplier=exporter) to simulate payment on
        orders = requests.get(f"{BASE_URL}/api/orders/mine", headers=_h(exporter_tok), timeout=15).json()
        pending = [o for o in orders if o.get("payment_status") == "pending" and o.get("supplier_id")]
        if not pending:
            pytest.skip("no pending order available for trade-payment auto-debit test")
        oid = pending[0]["id"]
        r = requests.post(f"{BASE_URL}/api/orders/{oid}/simulate-payment",
                          headers=_h(exporter_tok), timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        ad = data.get("jompstart_auto_debit")
        assert ad is not None, f"auto debit not triggered: {data}"
        assert ad["type"] == "debit"
        assert ad["amount"] > 0
        assert "JompStart auto-debit" in ad["description"]

        # Verify installment marked paid/partial
        rep = requests.get(f"{BASE_URL}/api/credit/applications/{app_id}/repayment",
                           headers=_h(exporter_tok), timeout=15).json()
        inst1 = rep["installments"][0]
        assert inst1["status"] in ("paid", "partial")
        assert inst1["paid_usd"] > 0

    def test_auto_debit_on_consumer_order(self, exporter_tok, consumer_tok, app_id):
        # place a consumer order against exporter's DTC listing (Adire scarf $89 × 2 = $178)
        listings = requests.get(f"{BASE_URL}/api/shop/listings?fulfillment=riby_dtc", timeout=15).json()
        adire = next((l for l in listings if "Adire" in l["title"]), listings[0])

        rep_before = requests.get(f"{BASE_URL}/api/credit/applications/{app_id}/repayment",
                                  headers=_h(exporter_tok), timeout=15).json()
        outstanding_before = rep_before["outstanding_usd"]

        r = requests.post(f"{BASE_URL}/api/shop/orders", headers=_h(consumer_tok), json={
            "listing_id": adire["id"], "quantity": 2,
            "shipping_name": "Jordan", "shipping_address": "NY",
            "shipping_email": "shopper@helix.com",
        }, timeout=20)
        assert r.status_code == 200, r.text

        rep_after = requests.get(f"{BASE_URL}/api/credit/applications/{app_id}/repayment",
                                 headers=_h(exporter_tok), timeout=15).json()
        # outstanding should reduce (some auto-debit applied)
        assert rep_after["outstanding_usd"] < outstanding_before, \
            f"outstanding did not reduce: before={outstanding_before}, after={rep_after['outstanding_usd']}"


# ---------- Consumer role restrictions ----------

class TestConsumerRoleRestrictions:
    def test_businesses_me_null(self, consumer_tok):
        r = requests.get(f"{BASE_URL}/api/businesses/me", headers=_h(consumer_tok), timeout=15)
        # may return null body, 200, or 404
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            assert r.json() in (None, {}, [])

    def test_orders_mine_empty(self, consumer_tok):
        r = requests.get(f"{BASE_URL}/api/orders/mine", headers=_h(consumer_tok), timeout=15)
        assert r.status_code == 200
        assert r.json() == []

    def test_product_creation_blocked(self, consumer_tok):
        r = requests.post(f"{BASE_URL}/api/products", headers=_h(consumer_tok), json={
            "name": "TEST_nope", "category": "fashion", "price_usd": 10,
        }, timeout=15)
        assert r.status_code in (400, 403)


# ---------- Regression ----------

class TestRegression:
    def test_api_root(self):
        r = requests.get(f"{BASE_URL}/api/", timeout=15)
        assert r.status_code == 200

    def test_products_list(self):
        r = requests.get(f"{BASE_URL}/api/products", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_exporter_orders_mine(self, exporter_tok):
        r = requests.get(f"{BASE_URL}/api/orders/mine", headers=_h(exporter_tok), timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
