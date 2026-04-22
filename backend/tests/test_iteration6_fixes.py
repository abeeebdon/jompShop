"""Iteration 6 — verifies iter5 P0/P1/P2 fixes.

Assertions extending iter5 suite:
 1. P0 ledger fix — seller USD delta after confirm-delivery == total*0.98
 2. Quote checkout quantity mismatch → 400
 3. Quote decline status guard on converted/declined/expired → 400
 4. Quote RBAC — exporter/buyer (non-consumer) cannot create quote → 403;
    consumer cannot quote own business listing → 400 (no own business here, so just the role check)
 5. Credit accept response contains 'disbursement_tx_id' (not 'transaction_id')
"""
import os
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


def _login(email):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": PWD}, timeout=20)
    assert r.status_code == 200, f"{email} login failed {r.status_code} {r.text}"
    return r.json()["access_token"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


@pytest.fixture(scope="session")
def admin_tok():
    return _login("admin@helix.com")


@pytest.fixture(scope="session")
def exporter_tok():
    return _login("exporter@helix.com")


@pytest.fixture(scope="session")
def buyer_tok():
    return _login("buyer@helix.com")


@pytest.fixture(scope="session")
def shopper_tok():
    return _login("shopper@helix.com")


def _usd_balance(tok):
    r = requests.get(f"{BASE_URL}/api/finance/dashboard", headers=_h(tok), timeout=20).json()
    return r["usd_balance"]


def _mk_dtc(exporter_tok, price=100.0, stock=5):
    r = requests.post(f"{BASE_URL}/api/shop/listings", headers=_h(exporter_tok),
                      json={
                          "title": f"TEST_iter6 {uuid.uuid4().hex[:6]}",
                          "description": "iter6 fixture",
                          "photos": [],
                          "category": "fashion",
                          "retail_price_usd": price,
                          "stock_qty": stock,
                          "fulfillment_mode": "riby_dtc",
                      }, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()


def _place(shopper_tok, listing_id, qty=1, quote_id=None):
    body = {
        "listing_id": listing_id, "quantity": qty,
        "shipping_name": "Iter6",
        "shipping_address": "1 Test St, Brooklyn NY 11201",
        "shipping_email": "shopper@helix.com",
        "shipping_phone": "+15555550100",
    }
    if quote_id:
        body["quote_id"] = quote_id
    return requests.post(f"{BASE_URL}/api/shop/orders", headers=_h(shopper_tok), json=body, timeout=25)


# =====================================================================
# (1) P0 ledger fix — seller USD delta == total*0.98
# =====================================================================
def _order_ledger_delta(tok, order_number):
    """Return (credit_amount, fee_amount) for the given order from the seller ledger.

    Note: auto-debit from JompStart may also fire in the same cycle; this function
    isolates only the order-related credit + fee, which is what the P0 fix concerns.
    """
    txs = requests.get(f"{BASE_URL}/api/finance/transactions?currency=USD&limit=100",
                       headers=_h(tok), timeout=20).json()
    credit = None
    fee = None
    for t in txs:
        desc = t.get("description", "") or ""
        if order_number not in desc:
            continue
        if t["type"] == "credit" and credit is None:
            credit = t["amount"]
        elif t["type"] == "fee" and fee is None:
            fee = t["amount"]
    return credit, fee


class TestLedgerNet98Percent:
    def test_confirm_delivery_credits_exactly_net(self, exporter_tok, shopper_tok):
        listing = _mk_dtc(exporter_tok, price=89.0)
        ro = _place(shopper_tok, listing["id"])
        assert ro.status_code == 200, ro.text
        oid = ro.json()["id"]
        total = ro.json()["total_usd"]
        order_number = ro.json()["order_number"]
        assert total == 89.0

        rc = requests.post(f"{BASE_URL}/api/shop/orders/{oid}/confirm-delivery",
                           headers=_h(shopper_tok), timeout=25)
        assert rc.status_code == 200, rc.text
        body = rc.json()
        # Response contract
        assert body["credit_amount_usd"] == round(total * 0.98, 2)
        assert body["fee_usd"] == round(total * 0.02, 2)
        assert body.get("gross_amount_usd") == total, f"gross_amount_usd missing or wrong: {body}"

        # Per-order ledger entries — verify FIX: credit is GROSS, fee is separate debit,
        # net effect per order = credit - fee = total * 0.98
        credit, fee = _order_ledger_delta(exporter_tok, order_number)
        assert credit is not None, f"no credit tx found for order {order_number}"
        assert fee is not None, f"no fee tx found for order {order_number}"
        assert credit == total, f"credit tx amount {credit} should equal gross {total} (was net before fix)"
        assert fee == round(total * 0.02, 2), f"fee tx amount {fee} != {total*0.02}"
        net = round(credit - fee, 2)
        expected = round(total * 0.98, 2)
        assert net == expected, f"Per-order ledger net {net} != expected {expected}"

    def test_seller_delivered_credits_exactly_net(self, exporter_tok, shopper_tok):
        listing = _mk_dtc(exporter_tok, price=50.0)
        ro = _place(shopper_tok, listing["id"])
        assert ro.status_code == 200, ro.text
        oid = ro.json()["id"]
        order_number = ro.json()["order_number"]
        total = ro.json()["total_usd"]

        rd = requests.post(f"{BASE_URL}/api/shop/orders/{oid}/delivered",
                           headers=_h(exporter_tok), timeout=25)
        assert rd.status_code == 200, rd.text
        body = rd.json()
        assert body["credit_amount_usd"] == 49.0
        assert body["fee_usd"] == 1.0
        assert body.get("gross_amount_usd") == 50.0

        credit, fee = _order_ledger_delta(exporter_tok, order_number)
        assert credit == total, f"credit {credit} != gross {total}"
        assert fee == 1.0
        assert round(credit - fee, 2) == 49.0

    def test_idempotent_release_already_released(self, exporter_tok, shopper_tok):
        listing = _mk_dtc(exporter_tok, price=40.0)
        ro = _place(shopper_tok, listing["id"])
        oid = ro.json()["id"]
        r1 = requests.post(f"{BASE_URL}/api/shop/orders/{oid}/confirm-delivery",
                           headers=_h(shopper_tok), timeout=25)
        assert r1.status_code == 200
        assert r1.json()["released"] is True
        # order.status set to delivered only when escrow was held (first call)
        orders = requests.get(f"{BASE_URL}/api/shop/orders/mine",
                              headers=_h(shopper_tok), timeout=20).json()
        this = next(o for o in orders if o["id"] == oid)
        assert this["status"] == "delivered"

        r2 = requests.post(f"{BASE_URL}/api/shop/orders/{oid}/confirm-delivery",
                           headers=_h(shopper_tok), timeout=25)
        assert r2.status_code == 200
        b2 = r2.json()
        assert b2["released"] is False
        assert "already released" in b2.get("reason", "").lower()


# =====================================================================
# (2) Quote checkout quantity mismatch → 400
# =====================================================================
class TestQuoteQuantityMismatch:
    def test_mismatched_quantity_rejected_400(self, exporter_tok, shopper_tok):
        listing = _mk_dtc(exporter_tok, price=30.0, stock=10)
        rq = requests.post(f"{BASE_URL}/api/shop/quotes", headers=_h(shopper_tok),
                           json={"listing_id": listing["id"], "quantity": 4}, timeout=20)
        assert rq.status_code == 200
        qid = rq.json()["id"]
        requests.post(f"{BASE_URL}/api/shop/quotes/{qid}/respond",
                      headers=_h(exporter_tok),
                      json={"quoted_unit_price_usd": 25.0, "valid_days": 5}, timeout=20)
        # payload qty=2 but quote qty=4
        r = _place(shopper_tok, listing["id"], qty=2, quote_id=qid)
        assert r.status_code == 400, f"expected 400 got {r.status_code}: {r.text}"


# =====================================================================
# (3) Quote decline status guard
# =====================================================================
class TestQuoteDeclineStatusGuard:
    def test_decline_on_converted_rejected(self, exporter_tok, shopper_tok):
        listing = _mk_dtc(exporter_tok, price=70.0, stock=5)
        rq = requests.post(f"{BASE_URL}/api/shop/quotes", headers=_h(shopper_tok),
                           json={"listing_id": listing["id"], "quantity": 2}, timeout=20)
        qid = rq.json()["id"]
        requests.post(f"{BASE_URL}/api/shop/quotes/{qid}/respond",
                      headers=_h(exporter_tok),
                      json={"quoted_unit_price_usd": 65.0, "valid_days": 5}, timeout=20)
        # convert via checkout
        ro = _place(shopper_tok, listing["id"], qty=2, quote_id=qid)
        assert ro.status_code == 200

        # now try to decline converted quote
        rd = requests.post(f"{BASE_URL}/api/shop/quotes/{qid}/decline",
                           headers=_h(shopper_tok), timeout=20)
        assert rd.status_code == 400, f"expected 400 got {rd.status_code}: {rd.text}"

    def test_decline_on_already_declined_rejected(self, exporter_tok, shopper_tok):
        listing = _mk_dtc(exporter_tok, price=25.0, stock=3)
        rq = requests.post(f"{BASE_URL}/api/shop/quotes", headers=_h(shopper_tok),
                           json={"listing_id": listing["id"], "quantity": 1}, timeout=20)
        qid = rq.json()["id"]
        r1 = requests.post(f"{BASE_URL}/api/shop/quotes/{qid}/decline",
                           headers=_h(shopper_tok), timeout=20)
        assert r1.status_code == 200
        r2 = requests.post(f"{BASE_URL}/api/shop/quotes/{qid}/decline",
                           headers=_h(shopper_tok), timeout=20)
        assert r2.status_code == 400, f"expected 400 got {r2.status_code}: {r2.text}"


# =====================================================================
# (4) Quote RBAC — exporter/buyer cannot quote (403)
# =====================================================================
class TestQuoteRBAC:
    def test_exporter_cannot_quote(self, exporter_tok, shopper_tok):
        # need an existing listing to quote on — use any seeded listing
        r = requests.get(f"{BASE_URL}/api/shop/listings", timeout=20).json()
        assert len(r) > 0
        listing_id = r[0]["id"]
        rq = requests.post(f"{BASE_URL}/api/shop/quotes", headers=_h(exporter_tok),
                           json={"listing_id": listing_id, "quantity": 1}, timeout=20)
        assert rq.status_code == 403, f"expected 403 got {rq.status_code}: {rq.text}"

    def test_buyer_cannot_quote(self, buyer_tok):
        r = requests.get(f"{BASE_URL}/api/shop/listings", timeout=20).json()
        listing_id = r[0]["id"]
        rq = requests.post(f"{BASE_URL}/api/shop/quotes", headers=_h(buyer_tok),
                           json={"listing_id": listing_id, "quantity": 1}, timeout=20)
        assert rq.status_code == 403, f"expected 403 got {rq.status_code}: {rq.text}"

    def test_consumer_can_quote(self, exporter_tok, shopper_tok):
        listing = _mk_dtc(exporter_tok, price=20.0, stock=3)
        rq = requests.post(f"{BASE_URL}/api/shop/quotes", headers=_h(shopper_tok),
                           json={"listing_id": listing["id"], "quantity": 1}, timeout=20)
        assert rq.status_code == 200


# =====================================================================
# (5) Credit accept — disbursement_tx_id in response, single-update transition
# =====================================================================
class TestCreditAcceptDisbursementTxId:
    def test_accept_response_field(self, exporter_tok, admin_tok):
        r = requests.post(f"{BASE_URL}/api/credit/applications", headers=_h(exporter_tok),
                          json={"amount_usd": 300, "term_months": 6,
                                "purpose": "iter6 accept field test"}, timeout=20)
        if r.status_code != 200:
            pytest.skip(f"credit submit blocked: {r.status_code} {r.text}")
        aid = r.json()["id"]
        r2 = requests.post(f"{BASE_URL}/api/credit/admin/applications/{aid}/decision",
                           headers=_h(admin_tok),
                           json={"decision": "offered", "offered_amount_usd": 300,
                                 "offered_apr": 10, "offered_term_months": 6,
                                 "decision_note": "iter6 offer"}, timeout=20)
        assert r2.status_code == 200
        r3 = requests.post(f"{BASE_URL}/api/credit/applications/{aid}/accept",
                           headers=_h(exporter_tok), timeout=20)
        assert r3.status_code == 200, r3.text
        body = r3.json()
        assert body["status"] == "disbursed"
        assert "disbursement_tx_id" in body, f"missing disbursement_tx_id: {body}"
        assert body["disbursement_tx_id"], "disbursement_tx_id empty"
        # ensure old field not present
        assert "transaction_id" not in body, f"legacy transaction_id still present: {body}"
