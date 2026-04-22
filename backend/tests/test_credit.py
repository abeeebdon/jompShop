"""Helix · JompStart Business Credit module backend tests (Iteration 2).

Covers eligibility engine, application submission, admin queue & decision,
exporter accept → disbursement transaction, plus a few regression checks.
Anchor remains MOCKED (sandbox_mock).
"""
import os
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://trade-nexus-110.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
PASSWORD = "Helix@123"


def _login(email: str) -> str:
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": PASSWORD}, timeout=30)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    data = r.json()
    assert data["user"]["email"] == email
    return data["access_token"]


def _h(tok: str):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def admin_token():
    return _login("admin@helix.com")


@pytest.fixture(scope="module")
def exporter_token():
    return _login("exporter@helix.com")


@pytest.fixture(scope="module")
def buyer_token():
    return _login("buyer@helix.com")


# ============== Regression smoke (per request — light only) ==============

class TestRegression:
    def test_root_online(self):
        r = requests.get(f"{API}", timeout=20)
        assert r.status_code == 200
        assert r.json().get("status") == "online"

    def test_login_exporter(self, exporter_token):
        assert exporter_token

    def test_finance_dashboard_balances(self, exporter_token):
        r = requests.get(f"{API}/finance/dashboard", headers=_h(exporter_token), timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["usd_balance"] > 0, f"exporter usd_balance expected > 0, got {d['usd_balance']}"

    def test_orders_mine(self, exporter_token):
        r = requests.get(f"{API}/orders/mine", headers=_h(exporter_token), timeout=20)
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list) and len(items) >= 1

    def test_compliance_score_75_plus(self, exporter_token):
        r = requests.get(f"{API}/compliance/score", headers=_h(exporter_token), timeout=20)
        assert r.status_code == 200
        d = r.json()
        # iteration 2 seed: NAFDAC active + Fumigation + FSSAI ⇒ ~75+
        assert d["score"] >= 70, f"expected compliance score ≥70 (≈75 per seed), got {d['score']}"


# ============== Eligibility engine ==============

class TestEligibility:
    def test_eligibility_exporter_eligible(self, exporter_token):
        r = requests.get(f"{API}/credit/eligibility", headers=_h(exporter_token), timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["partner"] == "JompStart Digital Limited"
        assert d["eligible"] is True, f"exporter expected eligible, reasons: {d.get('reasons_blocked')}"
        assert isinstance(d["max_limit_usd"], (int, float)) and d["max_limit_usd"] > 0
        assert isinstance(d["indicative_apr_percent"], (int, float))
        sales = d.get("sales") or {}
        assert sales.get("paid_order_count", 0) >= 1, f"expected ≥1 paid order, got sales={sales}"

    def test_eligibility_buyer_not_eligible(self, buyer_token):
        r = requests.get(f"{API}/credit/eligibility", headers=_h(buyer_token), timeout=20)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("eligible") is False
        # Either reasons_blocked list (has business but no sales) OR a top-level reason (no business)
        has_reasons = bool(d.get("reasons_blocked")) or bool(d.get("reason"))
        assert has_reasons, f"expected reasons explaining ineligibility: {d}"


# ============== Happy path: submit → admin offer → accept → disbursement ==============

class TestCreditHappyPath:
    @pytest.fixture(scope="class")
    def state(self):
        # shared state across tests in this class
        return {}

    def test_submit_application(self, exporter_token, state):
        # fetch eligibility for current max
        elig = requests.get(f"{API}/credit/eligibility", headers=_h(exporter_token), timeout=20).json()
        assert elig["eligible"] is True
        amount = round(min(elig["max_limit_usd"] * 0.5, max(elig["max_limit_usd"] - 100, 100)), 2)
        state["amount"] = amount
        state["max_limit"] = elig["max_limit_usd"]

        r = requests.post(f"{API}/credit/applications", headers=_h(exporter_token), json={
            "amount_usd": amount,
            "term_months": 6,
            "purpose": "TEST_purchase raw cotton & fund production",
        }, timeout=30)
        assert r.status_code == 200, r.text
        app = r.json()
        assert "_id" not in app
        assert app["status"] == "submitted"
        assert app["application_number"].startswith("JMP-"), app["application_number"]
        assert app["amount_usd"] == amount
        state["aid"] = app["id"]
        state["app_number"] = app["application_number"]

    def test_submit_exceeds_limit_400(self, exporter_token, state):
        too_much = state["max_limit"] + 1
        r = requests.post(f"{API}/credit/applications", headers=_h(exporter_token), json={
            "amount_usd": too_much, "term_months": 6}, timeout=30)
        assert r.status_code == 400, f"expected 400 for over-limit got {r.status_code} {r.text}"

    def test_my_applications_lists_submitted(self, exporter_token, state):
        r = requests.get(f"{API}/credit/applications/mine", headers=_h(exporter_token), timeout=20)
        assert r.status_code == 200
        items = r.json()
        assert any(it["id"] == state["aid"] for it in items), "submitted app missing in /mine"
        for it in items:
            assert "_id" not in it

    def test_get_own_application(self, exporter_token, state):
        r = requests.get(f"{API}/credit/applications/{state['aid']}", headers=_h(exporter_token), timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert d["id"] == state["aid"]
        assert "_id" not in d

    def test_get_other_users_application_403(self, buyer_token, state):
        r = requests.get(f"{API}/credit/applications/{state['aid']}", headers=_h(buyer_token), timeout=20)
        assert r.status_code == 403

    def test_admin_list_buyer_403(self, buyer_token):
        r = requests.get(f"{API}/credit/admin/applications", headers=_h(buyer_token), timeout=20)
        assert r.status_code == 403

    def test_admin_list_includes_decoration(self, admin_token, state):
        r = requests.get(f"{API}/credit/admin/applications", headers=_h(admin_token), timeout=20)
        assert r.status_code == 200
        items = r.json()
        target = next((it for it in items if it["id"] == state["aid"]), None)
        assert target is not None, "admin list missing our submitted app"
        assert "business_name" in target and target["business_name"]
        assert "business_country" in target and target["business_country"]

    def test_admin_offer_decision(self, admin_token, state):
        offered = round(state["amount"] * 0.9, 2)
        r = requests.post(f"{API}/credit/admin/applications/{state['aid']}/decision",
                          headers=_h(admin_token),
                          json={
                              "decision": "offered",
                              "offered_amount_usd": offered,
                              "offered_apr": 13.5,
                              "offered_term_months": 6,
                              "decision_note": "TEST offer",
                          }, timeout=30)
        assert r.status_code == 200, r.text
        # verify state via GET
        g = requests.get(f"{API}/credit/applications/{state['aid']}", headers=_h(admin_token), timeout=20).json()
        assert g["status"] == "offered"
        assert g["offered_amount_usd"] == offered
        assert g["offered_apr"] == 13.5
        assert g["offered_term_months"] == 6
        state["offered_amount"] = offered

    def test_exporter_accept_creates_disbursement_tx(self, exporter_token, state):
        r = requests.post(f"{API}/credit/applications/{state['aid']}/accept",
                          headers=_h(exporter_token), timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "disbursed"
        # endpoint returns transaction_id (NOT disbursement_tx_id). Spec asks for disbursement id; either field is acceptable.
        tx_id = d.get("transaction_id") or d.get("disbursement_tx_id")
        assert tx_id, f"no disbursement tx id returned: {d}"
        assert d["amount_usd"] == state["offered_amount"]
        state["tx_id"] = tx_id

        # application doc should reflect disbursed + disbursement_tx_id
        g = requests.get(f"{API}/credit/applications/{state['aid']}", headers=_h(exporter_token), timeout=20).json()
        assert g["status"] == "disbursed"
        assert g.get("disbursement_tx_id") == tx_id

    def test_disbursement_tx_appears_in_finance(self, exporter_token, state):
        r = requests.get(f"{API}/finance/transactions", headers=_h(exporter_token), timeout=20)
        assert r.status_code == 200
        items = r.json()
        match = next((t for t in items if t.get("id") == state["tx_id"]), None)
        assert match is not None, "JompStart disbursement tx not found in finance ledger"
        assert match["type"] == "credit"
        assert match["currency"] == "USD"
        assert match["amount"] == state["offered_amount"]
        assert match["anchor_event_type"] == "jompstart.credit.disbursed"
        assert "JompStart" in (match.get("description") or "") or "JompStart" in (match.get("counterparty") or "")


# ============== Rejection path on a separate fresh application ==============

class TestCreditRejection:
    def test_reject_fresh_application(self, exporter_token, admin_token):
        elig = requests.get(f"{API}/credit/eligibility", headers=_h(exporter_token), timeout=20).json()
        assert elig["eligible"] is True
        amount = round(min(elig["max_limit_usd"] * 0.2, 1000), 2) or 100
        r = requests.post(f"{API}/credit/applications", headers=_h(exporter_token), json={
            "amount_usd": amount, "term_months": 3, "purpose": "TEST_rejection_path"}, timeout=30)
        assert r.status_code == 200, r.text
        aid = r.json()["id"]

        r2 = requests.post(f"{API}/credit/admin/applications/{aid}/decision",
                           headers=_h(admin_token),
                           json={"decision": "rejected", "decision_note": "TEST rejection"}, timeout=30)
        assert r2.status_code == 200, r2.text

        g = requests.get(f"{API}/credit/applications/{aid}", headers=_h(exporter_token), timeout=20).json()
        assert g["status"] == "rejected"
        assert g.get("decision_note") == "TEST rejection"
