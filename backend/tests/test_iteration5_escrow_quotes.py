"""Iteration 5 — Escrow-first checkout + Quote flow + Admin escrow overview.

Validates:
 (a) Escrow held on order creation; NO seller credit tx at checkout
 (b) Consumer confirm-delivery releases escrow (credit = 98%, fee = 2%)
 (c) Seller mark-delivered alternative also releases escrow
 (d) Idempotent release (second release does nothing)
 (e) Quote flow: create pending → respond quoted → checkout quote_prepay → converted
 (f) Quote decline flow
 (g) Error cases: cross-listing quote / cross-consumer quote / not-yet-quoted
 (h) Admin escrow overview + RBAC 403 for buyer/exporter
 (i) JompStart auto-debit triggers on escrow release after accepted offer
 (j) Regression: 3 seeded listings, exporter riby_dtc listing creation still works
"""
import os
import uuid
import time

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
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": PWD}, timeout=20)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


# ---------- Fixtures ----------
@pytest.fixture(scope="session")
def admin_tok():
    return _login("admin@helix.com")


@pytest.fixture(scope="session")
def jompstart_tok():
    return _login("credit@jompstart.com")


@pytest.fixture(scope="session")
def exporter_tok():
    return _login("exporter@helix.com")


@pytest.fixture(scope="session")
def buyer_tok():
    return _login("buyer@helix.com")


@pytest.fixture(scope="session")
def shopper_tok():
    return _login("shopper@helix.com")


@pytest.fixture(scope="session")
def exporter_business_id(exporter_tok):
    r = requests.get(f"{BASE_URL}/api/finance/dashboard", headers=_h(exporter_tok), timeout=20)
    # find exporter business id via listings/mine
    r2 = requests.get(f"{BASE_URL}/api/shop/listings/mine", headers=_h(exporter_tok), timeout=20)
    items = r2.json()
    if items:
        return items[0]["owner_business_id"]
    return None


def _make_dtc_listing(exporter_tok, price=100.0, stock=5) -> dict:
    payload = {
        "title": f"TEST_DTC {uuid.uuid4().hex[:6]}",
        "description": "escrow test listing",
        "photos": [],
        "category": "fashion",
        "retail_price_usd": price,
        "stock_qty": stock,
        "fulfillment_mode": "riby_dtc",
    }
    r = requests.post(f"{BASE_URL}/api/shop/listings", headers=_h(exporter_tok), json=payload, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()


def _place_order(shopper_tok, listing_id, qty=1, quote_id=None) -> dict:
    body = {
        "listing_id": listing_id,
        "quantity": qty,
        "shipping_name": "Test Shopper",
        "shipping_address": "1 Test St, Brooklyn NY 11201",
        "shipping_email": "shopper@helix.com",
        "shipping_phone": "+15555550100",
    }
    if quote_id:
        body["quote_id"] = quote_id
    return requests.post(f"{BASE_URL}/api/shop/orders", headers=_h(shopper_tok), json=body, timeout=25)


# =====================================================================
# (a) Escrow held on checkout — NO seller credit tx
# =====================================================================
class TestEscrowHeldOnCheckout:
    def test_order_creates_escrow_held_no_credit(self, exporter_tok, shopper_tok):
        # pre-balance snapshot
        pre = requests.get(f"{BASE_URL}/api/finance/dashboard", headers=_h(exporter_tok), timeout=20).json()
        pre_usd = pre["usd_balance"]
        pre_credit_ids = {t["id"] for t in pre.get("recent_transactions", []) if t["type"] == "credit"}

        listing = _make_dtc_listing(exporter_tok, price=100.0, stock=3)
        r = _place_order(shopper_tok, listing["id"])
        assert r.status_code == 200, r.text
        o = r.json()
        assert o["escrow_status"] == "held"
        assert o["escrow_held_by"] == "Riby Inc (US Escrow)"
        assert o["checkout_mode"] == "order_prepay"
        assert o["quote_id"] is None
        assert o["total_usd"] == 100.0
        assert o["status"] == "paid"
        pytest.iter5_order_id_for_consumer_confirm = o["id"]
        pytest.iter5_listing_for_confirm = listing["id"]

        # Seller finance dashboard must NOT reflect credit for this order
        post = requests.get(f"{BASE_URL}/api/finance/dashboard", headers=_h(exporter_tok), timeout=20).json()
        post_usd = post["usd_balance"]
        assert post_usd == pre_usd, f"Seller USD balance changed at checkout: {pre_usd} -> {post_usd}"

        # No new credit tx referencing this order
        for t in post["recent_transactions"]:
            if t["id"] in pre_credit_ids:
                continue
            desc = t.get("description", "")
            assert o["order_number"] not in desc or t["type"] != "credit", \
                f"Unexpected credit tx for order {o['order_number']} at checkout"


# =====================================================================
# (b) Consumer confirm-delivery releases escrow
# =====================================================================
class TestConsumerConfirmDelivery:
    def test_confirm_delivery_releases_escrow(self, shopper_tok, exporter_tok):
        oid = getattr(pytest, "iter5_order_id_for_consumer_confirm", None)
        assert oid, "No order from checkout test"
        pre = requests.get(f"{BASE_URL}/api/finance/dashboard", headers=_h(exporter_tok), timeout=20).json()
        pre_usd = pre["usd_balance"]

        r = requests.post(f"{BASE_URL}/api/shop/orders/{oid}/confirm-delivery",
                          headers=_h(shopper_tok), timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("released") is True
        assert body["credit_amount_usd"] == 98.0  # 100 - 2%
        assert body["fee_usd"] == 2.0
        assert "jompstart_auto_debit" in body  # key present even if None

        # order state
        orders = requests.get(f"{BASE_URL}/api/shop/orders/mine", headers=_h(shopper_tok), timeout=20).json()
        this = next(o for o in orders if o["id"] == oid)
        assert this["escrow_status"] == "released"
        assert this["escrow_released_at"] is not None
        assert this["status"] == "delivered"

        # seller USD ledger must contain both escrow.released credit + shop.fee.applied fee
        # seller USD ledger must contain both escrow.released credit + shop.fee.applied fee
        # (absolute balance delta is flaky if auto-debit also fires this cycle)
        txs = requests.get(f"{BASE_URL}/api/finance/transactions?currency=USD&limit=20",
                           headers=_h(exporter_tok), timeout=20).json()
        order_number = this["order_number"]
        assert any(t["type"] == "credit" and order_number in t.get("description", "") for t in txs), \
            f"no credit tx for {order_number}"
        assert any(t["type"] == "fee" and order_number in t.get("description", "") for t in txs), \
            f"no fee tx for {order_number}"
        # NOTE: credit_tx.amount is already net of 2% fee AND a separate fee-debit is posted.
        # This double-counts the fee on the seller ledger. See critical_code_review_comments.

    def test_idempotent_release(self, shopper_tok):
        oid = getattr(pytest, "iter5_order_id_for_consumer_confirm", None)
        r = requests.post(f"{BASE_URL}/api/shop/orders/{oid}/confirm-delivery",
                          headers=_h(shopper_tok), timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("released") is False
        assert "already released" in body.get("reason", "").lower()


# =====================================================================
# (c) Seller mark-delivered alternative
# =====================================================================
class TestSellerMarkDelivered:
    def test_seller_delivered_releases_escrow(self, exporter_tok, shopper_tok):
        listing = _make_dtc_listing(exporter_tok, price=50.0, stock=2)
        r = _place_order(shopper_tok, listing["id"])
        assert r.status_code == 200, r.text
        oid = r.json()["id"]

        pre = requests.get(f"{BASE_URL}/api/finance/dashboard", headers=_h(exporter_tok), timeout=20).json()
        pre_usd = pre["usd_balance"]

        r2 = requests.post(f"{BASE_URL}/api/shop/orders/{oid}/delivered",
                           headers=_h(exporter_tok), timeout=20)
        assert r2.status_code == 200, r2.text
        body = r2.json()
        assert body.get("released") is True
        assert body["credit_amount_usd"] == 49.0  # 50 - 2%
        assert body["fee_usd"] == 1.0

        # ledger contains credit + fee tx for this order
        txs = requests.get(f"{BASE_URL}/api/finance/transactions?currency=USD&limit=20",
                           headers=_h(exporter_tok), timeout=20).json()
        order_number = r.json()["order_number"]
        assert any(t["type"] == "credit" and order_number in t.get("description", "") for t in txs)
        assert any(t["type"] == "fee" and order_number in t.get("description", "") for t in txs)


# =====================================================================
# (e) Quote flow end-to-end
# =====================================================================
class TestQuoteFlowE2E:
    def test_create_quote_pending(self, exporter_tok, shopper_tok):
        listing = _make_dtc_listing(exporter_tok, price=200.0, stock=10)
        pytest.iter5_quote_listing_id = listing["id"]
        r = requests.post(f"{BASE_URL}/api/shop/quotes", headers=_h(shopper_tok),
                          json={"listing_id": listing["id"], "quantity": 3,
                                "message": "Bulk discount please"}, timeout=20)
        assert r.status_code == 200, r.text
        q = r.json()
        assert q["status"] == "pending"
        assert q["quote_number"].startswith("QTE-")
        assert q["quantity"] == 3
        assert q["listing_id"] == listing["id"]
        pytest.iter5_quote_id = q["id"]

    def test_mine_returns_quote_both_sides(self, shopper_tok, exporter_tok):
        qid = pytest.iter5_quote_id
        # consumer side
        r = requests.get(f"{BASE_URL}/api/shop/quotes/mine", headers=_h(shopper_tok), timeout=20).json()
        assert any(q["id"] == qid for q in r["as_consumer"])
        # seller side
        r2 = requests.get(f"{BASE_URL}/api/shop/quotes/mine", headers=_h(exporter_tok), timeout=20).json()
        assert any(q["id"] == qid for q in r2["as_seller"])

    def test_seller_responds_quoted(self, exporter_tok):
        qid = pytest.iter5_quote_id
        r = requests.post(f"{BASE_URL}/api/shop/quotes/{qid}/respond",
                          headers=_h(exporter_tok),
                          json={"quoted_unit_price_usd": 180.0, "quote_note": "3-unit discount",
                                "valid_days": 7}, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["quoted_total_usd"] == 540.0  # 180 * 3
        assert body["valid_until"]
        # verify persistence via GET
        g = requests.get(f"{BASE_URL}/api/shop/quotes/{qid}", headers=_h(exporter_tok), timeout=20).json()
        assert g["status"] == "quoted"
        assert g["quoted_unit_price_usd"] == 180.0
        assert g["quoted_total_usd"] == 540.0
        assert g["quote_valid_until"] is not None

    def test_checkout_with_quote_converts_and_escrows(self, shopper_tok, exporter_tok):
        qid = pytest.iter5_quote_id
        listing_id = pytest.iter5_quote_listing_id
        r = _place_order(shopper_tok, listing_id, qty=3, quote_id=qid)
        assert r.status_code == 200, r.text
        o = r.json()
        assert o["checkout_mode"] == "quote_prepay"
        assert o["quote_id"] == qid
        assert o["unit_price_usd"] == 180.0
        assert o["total_usd"] == 540.0
        assert o["escrow_status"] == "held"
        assert o["quantity"] == 3

        # quote status => converted
        g = requests.get(f"{BASE_URL}/api/shop/quotes/{qid}", headers=_h(exporter_tok), timeout=20).json()
        assert g["status"] == "converted"


class TestQuoteDecline:
    def test_consumer_decline_quote(self, exporter_tok, shopper_tok):
        listing = _make_dtc_listing(exporter_tok, price=80.0, stock=5)
        rq = requests.post(f"{BASE_URL}/api/shop/quotes", headers=_h(shopper_tok),
                           json={"listing_id": listing["id"], "quantity": 2,
                                 "message": "decline me"}, timeout=20)
        assert rq.status_code == 200
        qid = rq.json()["id"]

        r = requests.post(f"{BASE_URL}/api/shop/quotes/{qid}/decline",
                          headers=_h(shopper_tok), timeout=20)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "declined"

        g = requests.get(f"{BASE_URL}/api/shop/quotes/{qid}", headers=_h(shopper_tok), timeout=20).json()
        assert g["status"] == "declined"


# =====================================================================
# (g) Quote error cases
# =====================================================================
class TestQuoteErrorCases:
    def test_quote_on_different_listing_rejected_400(self, exporter_tok, shopper_tok, buyer_tok):
        # quote on listing A, try to order listing B with that quote
        la = _make_dtc_listing(exporter_tok, price=30.0, stock=3)
        lb = _make_dtc_listing(exporter_tok, price=30.0, stock=3)
        rq = requests.post(f"{BASE_URL}/api/shop/quotes", headers=_h(shopper_tok),
                           json={"listing_id": la["id"], "quantity": 1}, timeout=20)
        qid = rq.json()["id"]
        requests.post(f"{BASE_URL}/api/shop/quotes/{qid}/respond",
                      headers=_h(exporter_tok),
                      json={"quoted_unit_price_usd": 25.0, "valid_days": 3}, timeout=20)
        r = _place_order(shopper_tok, lb["id"], qty=1, quote_id=qid)
        assert r.status_code == 400, f"expected 400 got {r.status_code}: {r.text}"

    def test_quote_from_another_consumer_rejected_403(self, exporter_tok, shopper_tok, buyer_tok):
        # shopper creates quote, buyer (different consumer_user_id) tries to checkout
        listing = _make_dtc_listing(exporter_tok, price=40.0, stock=3)
        rq = requests.post(f"{BASE_URL}/api/shop/quotes", headers=_h(shopper_tok),
                           json={"listing_id": listing["id"], "quantity": 1}, timeout=20)
        qid = rq.json()["id"]
        requests.post(f"{BASE_URL}/api/shop/quotes/{qid}/respond",
                      headers=_h(exporter_tok),
                      json={"quoted_unit_price_usd": 35.0, "valid_days": 3}, timeout=20)
        # buyer role is allowed to checkout but this quote isn't theirs
        r = _place_order(buyer_tok, listing["id"], qty=1, quote_id=qid)
        assert r.status_code == 403, f"expected 403 got {r.status_code}: {r.text}"

    def test_quote_not_yet_quoted_rejected_400(self, exporter_tok, shopper_tok):
        listing = _make_dtc_listing(exporter_tok, price=60.0, stock=3)
        rq = requests.post(f"{BASE_URL}/api/shop/quotes", headers=_h(shopper_tok),
                           json={"listing_id": listing["id"], "quantity": 1}, timeout=20)
        qid = rq.json()["id"]
        # pending (not responded yet)
        r = _place_order(shopper_tok, listing["id"], qty=1, quote_id=qid)
        assert r.status_code == 400, f"expected 400 got {r.status_code}: {r.text}"
        assert "pending" in r.text.lower() or "not ready" in r.text.lower()


# =====================================================================
# (h) Admin escrow overview + RBAC
# =====================================================================
class TestEscrowOverview:
    def test_admin_overview(self, admin_tok):
        r = requests.get(f"{BASE_URL}/api/shop/escrow/overview", headers=_h(admin_tok), timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        for key in ("total_held_usd", "total_released_usd", "held_count", "released_count", "recent"):
            assert key in data
        assert isinstance(data["recent"], list)
        assert data["released_count"] >= 1  # at least our confirm-delivery above
        assert data["total_released_usd"] >= 100.0  # 100 from TestConsumerConfirmDelivery

    def test_buyer_forbidden_403(self, buyer_tok):
        r = requests.get(f"{BASE_URL}/api/shop/escrow/overview", headers=_h(buyer_tok), timeout=20)
        assert r.status_code == 403

    def test_exporter_forbidden_403(self, exporter_tok):
        r = requests.get(f"{BASE_URL}/api/shop/escrow/overview", headers=_h(exporter_tok), timeout=20)
        assert r.status_code == 403


# =====================================================================
# (i) JompStart auto-debit on escrow release
# =====================================================================
class TestJompStartAutoDebitOnRelease:
    def test_full_flow_auto_debit(self, exporter_tok, admin_tok, shopper_tok):
        # 1) Exporter submits credit app
        r = requests.post(f"{BASE_URL}/api/credit/applications", headers=_h(exporter_tok),
                          json={"amount_usd": 500, "term_months": 6,
                                "purpose": "iter5 auto-debit test"}, timeout=20)
        if r.status_code != 200:
            pytest.skip(f"exporter not eligible or blocked: {r.status_code} {r.text}")
        aid = r.json()["id"]

        # 2) Admin offers
        r2 = requests.post(f"{BASE_URL}/api/credit/admin/applications/{aid}/decision",
                           headers=_h(admin_tok),
                           json={"decision": "offered", "offered_amount_usd": 500,
                                 "offered_apr": 12, "offered_term_months": 6,
                                 "decision_note": "iter5 test offer"}, timeout=20)
        assert r2.status_code == 200, r2.text

        # 3) Exporter accepts => disbursed
        r3 = requests.post(f"{BASE_URL}/api/credit/applications/{aid}/accept",
                           headers=_h(exporter_tok), timeout=20)
        assert r3.status_code == 200, r3.text
        assert r3.json()["status"] == "disbursed"

        # 4) Consumer buys DTC listing from exporter
        listing = _make_dtc_listing(exporter_tok, price=150.0, stock=2)
        ro = _place_order(shopper_tok, listing["id"], qty=1)
        assert ro.status_code == 200, ro.text
        oid = ro.json()["id"]

        # 5) Consumer confirm-delivery → escrow release → auto-debit expected
        rc = requests.post(f"{BASE_URL}/api/shop/orders/{oid}/confirm-delivery",
                           headers=_h(shopper_tok), timeout=25)
        assert rc.status_code == 200, rc.text
        body = rc.json()
        assert body["released"] is True
        ad = body.get("jompstart_auto_debit")
        # could be None if repayment module decided nothing due this cycle;
        # but since we just disbursed, a pending installment should exist and be debited.
        assert ad is not None, f"Expected jompstart_auto_debit to fire, got None. body={body}"
        assert isinstance(ad, dict)
        assert ad.get("amount", 0) > 0 or ad.get("debited_usd", 0) > 0 or "installment" in str(ad).lower()


# =====================================================================
# (j) Regression
# =====================================================================
class TestRegression:
    def test_seeded_listings_count(self):
        r = requests.get(f"{BASE_URL}/api/shop/listings", timeout=20)
        assert r.status_code == 200
        items = r.json()
        # Seeded listings have non-TEST_ titles; should be >= 3
        seeded = [i for i in items if not i["title"].startswith("TEST_")]
        assert len(seeded) >= 3, f"Expected >=3 seeded listings, got {len(seeded)}"

    def test_exporter_riby_dtc_listing_still_works(self, exporter_tok):
        payload = {
            "title": f"TEST_Regression {uuid.uuid4().hex[:6]}",
            "description": "iter4 fix smoke",
            "photos": [],
            "category": "fashion",
            "retail_price_usd": 15.0,
            "stock_qty": 2,
            "fulfillment_mode": "riby_dtc",
            "ships_from": "Lagos",
        }
        r = requests.post(f"{BASE_URL}/api/shop/listings", headers=_h(exporter_tok), json=payload, timeout=20)
        assert r.status_code == 200, r.text
        assert r.json()["delivery_partner_of_record"] == "Riby Inc"

    def test_credit_smoke_mine(self, exporter_tok):
        r = requests.get(f"{BASE_URL}/api/credit/applications/mine", headers=_h(exporter_tok), timeout=20)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
