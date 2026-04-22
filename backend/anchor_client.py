"""GetAnchor API client with MOCK sandbox mode.

When ANCHOR_ENV=sandbox_mock (default), all calls return realistic mock data
and are logged with [MOCK]. The interface matches the real Anchor API so flipping
to ANCHOR_ENV=sandbox/live with a real ANCHOR_API_KEY will work without code changes.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import random
import uuid
from typing import Optional

import requests

log = logging.getLogger("helix.anchor")

ANCHOR_ENV = os.environ.get("ANCHOR_ENV", "sandbox_mock")
ANCHOR_API_KEY = os.environ.get("ANCHOR_API_KEY", "")
ANCHOR_WEBHOOK_SECRET = os.environ.get("ANCHOR_WEBHOOK_SECRET", "")
ANCHOR_SANDBOX_URL = os.environ.get("ANCHOR_SANDBOX_URL", "https://api.sandbox.getanchor.co")
ANCHOR_LIVE_URL = os.environ.get("ANCHOR_LIVE_URL", "https://api.getanchor.co")


def is_mock() -> bool:
    return ANCHOR_ENV == "sandbox_mock" or not ANCHOR_API_KEY


def _base_url() -> str:
    return ANCHOR_LIVE_URL if ANCHOR_ENV == "live" else ANCHOR_SANDBOX_URL


def _headers(idempotency_key: Optional[str] = None) -> dict:
    h = {"x-anchor-key": ANCHOR_API_KEY, "Content-Type": "application/json"}
    if idempotency_key:
        h["Idempotency-Key"] = idempotency_key
    return h


def _mock_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def _mock_account_number() -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(10))


def verify_webhook_signature(raw_body: bytes, signature: str) -> bool:
    if is_mock():
        log.info("[MOCK] webhook signature verification skipped")
        return True
    if not signature or not ANCHOR_WEBHOOK_SECRET:
        return False
    mac = hmac.new(ANCHOR_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, signature)


# ---------- Customers ----------

def create_individual_customer(payload: dict) -> dict:
    if is_mock():
        cid = _mock_id("cust_ind")
        log.info("[MOCK] create_individual_customer -> %s", cid)
        return {"id": cid, "type": "individual", "status": "pending", **payload}
    r = requests.post(f"{_base_url()}/customers", json=payload, headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json()


def create_business_customer(payload: dict) -> dict:
    if is_mock():
        cid = _mock_id("cust_biz")
        log.info("[MOCK] create_business_customer -> %s", cid)
        return {"id": cid, "type": "business", "status": "pending", **payload}
    r = requests.post(f"{_base_url()}/customers/businesses", json=payload, headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json()


def submit_kyc(customer_id: str, payload: dict) -> dict:
    if is_mock():
        log.info("[MOCK] submit_kyc(%s)", customer_id)
        return {"id": customer_id, "kyc_status": "under_review"}
    r = requests.post(f"{_base_url()}/customers/{customer_id}/kyc", json=payload, headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json()


def submit_kyb(customer_id: str, payload: dict) -> dict:
    if is_mock():
        log.info("[MOCK] submit_kyb(%s)", customer_id)
        return {"id": customer_id, "kyb_status": "under_review"}
    r = requests.post(f"{_base_url()}/customers/businesses/{customer_id}/kyb", json=payload, headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json()


def get_customer(customer_id: str) -> dict:
    if is_mock():
        return {"id": customer_id, "kyc_status": "approved"}
    r = requests.get(f"{_base_url()}/customers/{customer_id}", headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json()


# ---------- Deposit accounts ----------

def create_deposit_account(customer_id: str, currency: str) -> dict:
    if is_mock():
        acct_id = _mock_id(f"dep_{currency.lower()}")
        acct_number = _mock_account_number() if currency == "NGN" else f"HLX-USD-{uuid.uuid4().hex[:8].upper()}"
        log.info("[MOCK] create_deposit_account(%s, %s) -> %s", customer_id, currency, acct_id)
        return {
            "id": acct_id,
            "customer_id": customer_id,
            "currency": currency,
            "account_number": acct_number,
            "bank_name": "Anchor Sandbox Bank" if currency == "NGN" else "Anchor USD (FBO Riby Inc)",
            "balance": 0,
        }
    r = requests.post(
        f"{_base_url()}/deposit-accounts",
        json={"customer_id": customer_id, "currency": currency},
        headers=_headers(idempotency_key=f"dep-{customer_id}-{currency}"),
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def get_deposit_account_balance(account_id: str) -> dict:
    if is_mock():
        return {"id": account_id, "available_balance": 0, "ledger_balance": 0}
    r = requests.get(f"{_base_url()}/deposit-accounts/{account_id}/balance", headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json()


# ---------- Reserved accounts (per-order) ----------

def create_reserved_account(order_id: str, customer_id: str, amount: float, currency: str = "USD") -> dict:
    if is_mock():
        rid = _mock_id("res")
        acct_number = _mock_account_number()
        log.info("[MOCK] create_reserved_account(order=%s, %s %s) -> %s", order_id, amount, currency, rid)
        return {
            "id": rid,
            "order_id": order_id,
            "customer_id": customer_id,
            "account_number": acct_number,
            "bank_name": "Anchor Reserved (Helix FBO)",
            "expected_amount": amount,
            "currency": currency,
            "status": "active",
        }
    r = requests.post(
        f"{_base_url()}/reserved-accounts",
        json={"customer_id": customer_id, "expected_amount": amount, "currency": currency, "reference": order_id},
        headers=_headers(idempotency_key=f"res-{order_id}"),
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


# ---------- Transfers ----------

def initiate_nip_transfer(source_account_id: str, amount: float, dest_bank_code: str, dest_account_number: str, narration: str) -> dict:
    if is_mock():
        tid = _mock_id("nip")
        log.info("[MOCK] NIP transfer %s: %s NGN -> %s/%s", tid, amount, dest_bank_code, dest_account_number)
        return {"id": tid, "status": "completed", "amount": amount, "currency": "NGN", "reference": tid}
    r = requests.post(
        f"{_base_url()}/transfers/nip",
        json={
            "source_account_id": source_account_id,
            "amount": amount,
            "dest_bank_code": dest_bank_code,
            "dest_account_number": dest_account_number,
            "narration": narration,
        },
        headers=_headers(idempotency_key=f"nip-{source_account_id}-{uuid.uuid4().hex[:8]}"),
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def initiate_book_transfer(source_account_id: str, dest_account_id: str, amount: float, currency: str, narration: str) -> dict:
    if is_mock():
        tid = _mock_id("book")
        log.info("[MOCK] book transfer %s: %s %s %s -> %s", tid, amount, currency, source_account_id, dest_account_id)
        return {"id": tid, "status": "completed", "amount": amount, "currency": currency}
    r = requests.post(
        f"{_base_url()}/transfers/book",
        json={"source_account_id": source_account_id, "dest_account_id": dest_account_id, "amount": amount, "currency": currency, "narration": narration},
        headers=_headers(idempotency_key=f"book-{source_account_id}-{uuid.uuid4().hex[:8]}"),
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def verify_transfer(transfer_id: str) -> dict:
    if is_mock():
        return {"id": transfer_id, "status": "completed"}
    r = requests.get(f"{_base_url()}/transfers/{transfer_id}", headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json()


def apply_fee(account_id: str, amount: float, currency: str, description: str) -> dict:
    if is_mock():
        fid = _mock_id("fee")
        log.info("[MOCK] fee %s: %s %s on %s (%s)", fid, amount, currency, account_id, description)
        return {"id": fid, "status": "applied", "amount": amount, "currency": currency}
    r = requests.post(f"{_base_url()}/fees", json={"account_id": account_id, "amount": amount, "currency": currency, "description": description}, headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json()
