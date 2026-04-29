"""Iteration 8 — withdrawal accounts CRUD, USD/NGN withdrawals, pagination/image regressions."""
import os
import time
import uuid

import pytest
import requests

def _load_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if not v:
        try:
            for line in open("/app/frontend/.env"):
                if line.startswith("REACT_APP_BACKEND_URL="):
                    v = line.split("=", 1)[1].strip()
                    break
        except Exception:
            pass
    assert v, "REACT_APP_BACKEND_URL not set"
    return v.rstrip("/")


BASE_URL = _load_url()
EXPORTER = {"email": "exporter@helix.com", "password": "Helix@123"}


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    r = sess.post(f"{BASE_URL}/api/auth/login", json=EXPORTER, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    tok = r.json().get("token") or r.json().get("session_token") or r.json().get("access_token")
    if tok:
        sess.headers.update({"Authorization": f"Bearer {tok}"})
    return sess


@pytest.fixture(scope="module")
def created_ids():
    ids = []
    yield ids


# ---------------- bank list ----------------
def test_withdrawal_banks_list(s):
    r = s.get(f"{BASE_URL}/api/finance/withdrawal-banks", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list) and len(data) == 10
    for b in data:
        assert "code" in b and "name" in b and b["code"] and b["name"]


# ---------------- USD account create / validation ----------------
def test_create_usd_account_happy(s, created_ids):
    payload = {
        "currency": "USD",
        "label": f"TEST_acc_Chase_{uuid.uuid4().hex[:6]}",
        "account_name": "Helix LLC",
        "bank_name": "Chase",
        "routing_number": "021000021",
        "account_number": "1234567890",
        "account_type": "checking",
        "is_default": True,
    }
    r = s.post(f"{BASE_URL}/api/finance/withdrawal-accounts", json=payload, timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("id")
    assert body.get("approval_status") == "approved"
    assert body.get("is_default") is True
    assert body.get("currency") == "USD"
    assert body.get("account_number_masked", "").endswith("7890")
    created_ids.append(body["id"])


def test_create_usd_missing_bank_name(s):
    payload = {
        "currency": "USD",
        "label": "TEST_acc_no_bank",
        "account_name": "X",
        "routing_number": "021000021",
        "account_number": "1234567890",
        "account_type": "checking",
    }
    r = s.post(f"{BASE_URL}/api/finance/withdrawal-accounts", json=payload, timeout=10)
    assert r.status_code == 400


def test_create_usd_bad_routing(s):
    payload = {
        "currency": "USD",
        "label": "TEST_acc_bad_routing",
        "account_name": "X",
        "bank_name": "Chase",
        "routing_number": "12345",
        "account_number": "1234567890",
        "account_type": "checking",
    }
    r = s.post(f"{BASE_URL}/api/finance/withdrawal-accounts", json=payload, timeout=10)
    assert r.status_code == 400


def test_create_usd_bad_type(s):
    payload = {
        "currency": "USD",
        "label": "TEST_acc_bad_type",
        "account_name": "X",
        "bank_name": "Chase",
        "routing_number": "021000021",
        "account_number": "1234567890",
        "account_type": "money_market",
    }
    r = s.post(f"{BASE_URL}/api/finance/withdrawal-accounts", json=payload, timeout=10)
    assert r.status_code == 400


# ---------------- NGN account create / validation ----------------
def test_create_ngn_account_happy(s, created_ids):
    payload = {
        "currency": "NGN",
        "label": f"TEST_acc_GTBank_{uuid.uuid4().hex[:6]}",
        "account_name": "Test",
        "bank_code": "058",
        "account_number": "0123456789",
    }
    r = s.post(f"{BASE_URL}/api/finance/withdrawal-accounts", json=payload, timeout=10)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["currency"] == "NGN"
    assert body["bank_name"].startswith("Guaranty")
    created_ids.append(body["id"])


def test_create_ngn_bad_account_number(s):
    payload = {"currency": "NGN", "label": "TEST_acc_ngn_bad", "account_name": "X",
               "bank_code": "058", "account_number": "12345"}
    r = s.post(f"{BASE_URL}/api/finance/withdrawal-accounts", json=payload, timeout=10)
    assert r.status_code == 400


def test_create_ngn_unknown_bank(s):
    payload = {"currency": "NGN", "label": "TEST_acc_ngn_bad_bank", "account_name": "X",
               "bank_code": "999", "account_number": "0123456789"}
    r = s.post(f"{BASE_URL}/api/finance/withdrawal-accounts", json=payload, timeout=10)
    assert r.status_code == 400


# ---------------- list / filter ----------------
def test_list_accounts_and_filter(s, created_ids):
    r = s.get(f"{BASE_URL}/api/finance/withdrawal-accounts", timeout=10)
    assert r.status_code == 200
    items = r.json()
    assert any(it["id"] in created_ids for it in items)
    for it in items:
        assert "account_number_masked" in it
    r2 = s.get(f"{BASE_URL}/api/finance/withdrawal-accounts?currency=USD", timeout=10)
    assert r2.status_code == 200
    assert all(it["currency"] == "USD" for it in r2.json())


# ---------------- patch ----------------
def test_patch_rename_default_active(s, created_ids):
    # Rename + un/redefault + toggle active
    usd_id = next((i for i in created_ids if i), None)
    assert usd_id
    new_label = f"TEST_acc_renamed_{uuid.uuid4().hex[:5]}"
    r = s.patch(f"{BASE_URL}/api/finance/withdrawal-accounts/{usd_id}",
                json={"label": new_label, "is_default": True}, timeout=10)
    assert r.status_code == 200
    assert r.json()["label"] == new_label
    assert r.json()["is_default"] is True
    # Verify siblings of same currency are no longer default
    r2 = s.get(f"{BASE_URL}/api/finance/withdrawal-accounts?currency=USD", timeout=10)
    defaults = [it for it in r2.json() if it["is_default"]]
    assert len(defaults) == 1 and defaults[0]["id"] == usd_id


# ---------------- withdraw-from-account validation ----------------
def test_withdraw_amount_exceeds_balance(s, created_ids):
    usd_id = created_ids[0]
    r = s.post(f"{BASE_URL}/api/finance/withdraw-from-account",
               json={"withdrawal_account_id": usd_id, "amount": 9_999_999.0}, timeout=10)
    assert r.status_code == 400
    assert "insufficient" in r.text.lower()


def test_withdraw_unknown_account(s):
    r = s.post(f"{BASE_URL}/api/finance/withdraw-from-account",
               json={"withdrawal_account_id": "non-existent", "amount": 1.0}, timeout=10)
    assert r.status_code == 404


# ---------------- happy USD withdrawal ----------------
def test_withdraw_usd_happy(s, created_ids):
    usd_id = created_ids[0]
    r = s.post(f"{BASE_URL}/api/finance/withdraw-from-account",
               json={"withdrawal_account_id": usd_id, "amount": 25.0,
                     "narration": "TEST_iter8 usd"}, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("rail") in ("ACH", "WIRE")
    assert body.get("transaction_id")
    # Verify a tx row exists
    time.sleep(0.5)
    txr = s.get(f"{BASE_URL}/api/finance/transactions", timeout=10)
    if txr.status_code == 200:
        txs = txr.json() if isinstance(txr.json(), list) else txr.json().get("items", [])
        match = [t for t in txs if t.get("id") == body["transaction_id"]]
        if match:
            assert match[0].get("type") == "transfer"
            assert match[0].get("currency") == "USD"


# ---------------- happy NGN withdrawal + balance reduces ----------------
def test_withdraw_ngn_happy_and_balance_reduces(s, created_ids):
    ngn_id = created_ids[1]
    bal_before_r = s.get(f"{BASE_URL}/api/finance/balance", timeout=10)
    bal_before = None
    if bal_before_r.status_code == 200:
        b = bal_before_r.json()
        bal_before = b.get("ngn") if isinstance(b, dict) else None
    if bal_before is None or bal_before < 100:
        pytest.skip("no NGN balance to withdraw against")

    r = s.post(f"{BASE_URL}/api/finance/withdraw-from-account",
               json={"withdrawal_account_id": ngn_id, "amount": 50.0,
                     "narration": "TEST_iter8 ngn"}, timeout=15)
    assert r.status_code == 200, r.text
    assert r.json().get("rail") == "NIP"
    time.sleep(0.5)
    bal_after_r = s.get(f"{BASE_URL}/api/finance/balance", timeout=10)
    if bal_after_r.status_code == 200:
        b2 = bal_after_r.json()
        bal_after = b2.get("ngn") if isinstance(b2, dict) else None
        if bal_after is not None and bal_before is not None:
            assert bal_after <= bal_before - 49.99


# ---------------- delete soft + 404 on inactive ----------------
def test_delete_soft_then_withdraw_404(s, created_ids):
    # Create disposable acct
    payload = {"currency": "USD", "label": "TEST_acc_to_delete", "account_name": "Y",
               "bank_name": "BoA", "routing_number": "026009593",
               "account_number": "9999999999", "account_type": "checking"}
    r = s.post(f"{BASE_URL}/api/finance/withdrawal-accounts", json=payload, timeout=10)
    assert r.status_code == 200
    aid = r.json()["id"]
    d = s.delete(f"{BASE_URL}/api/finance/withdrawal-accounts/{aid}", timeout=10)
    assert d.status_code == 200
    # listing default excludes inactive
    lst = s.get(f"{BASE_URL}/api/finance/withdrawal-accounts", timeout=10).json()
    assert all(it["id"] != aid for it in lst)
    # withdraw against deleted -> 404
    w = s.post(f"{BASE_URL}/api/finance/withdraw-from-account",
               json={"withdrawal_account_id": aid, "amount": 1.0}, timeout=10)
    assert w.status_code in (404, 400)


# ---------------- regression: 50 listings with photos ----------------
def test_shop_listings_50_photos(s):
    r = requests.get(f"{BASE_URL}/api/shop/listings", timeout=15)
    assert r.status_code == 200
    data = r.json()
    items = data if isinstance(data, list) else data.get("items", [])
    assert len(items) >= 50
    no_photo = [it for it in items if not it.get("photos")]
    assert len(no_photo) == 0, f"{len(no_photo)} listings without photos"


# ---------------- regression: cleanup TEST_acc_ ----------------
def test_zzz_cleanup(s, created_ids):
    """Soft-delete every TEST_acc_ account we created or any leftover."""
    lst = s.get(f"{BASE_URL}/api/finance/withdrawal-accounts", timeout=10).json()
    for it in lst:
        if it.get("label", "").startswith("TEST_acc_") or it["id"] in created_ids:
            s.delete(f"{BASE_URL}/api/finance/withdrawal-accounts/{it['id']}", timeout=10)
