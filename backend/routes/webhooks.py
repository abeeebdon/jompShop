"""Anchor webhook receiver (signature verified). Mocked in sandbox_mock mode."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from db import db
from anchor_client import verify_webhook_signature, is_mock

router = APIRouter(prefix="/api", tags=["webhooks"])
log = logging.getLogger("helix.webhooks")


EVENT_HANDLERS = {}


def handler(event_type: str):
    def dec(fn):
        EVENT_HANDLERS[event_type] = fn
        return fn
    return dec


@handler("customer.kyc.approved")
async def _on_kyc_approved(event: dict):
    cust_id = event.get("data", {}).get("customer_id")
    await db.businesses.update_one({"anchor_customer_id": cust_id}, {"$set": {"kyc_status": "approved"}})


@handler("customer.kyb.approved")
async def _on_kyb_approved(event: dict):
    cust_id = event.get("data", {}).get("customer_id")
    await db.businesses.update_one({"anchor_customer_id": cust_id}, {"$set": {"kyb_status": "approved"}})


@handler("account.credited")
async def _on_account_credited(event: dict):
    data = event.get("data", {})
    # map by order reference if available
    order_ref = data.get("reference")
    if order_ref:
        await db.orders.update_one({"id": order_ref}, {"$set": {"payment_status": "confirmed"}})


@router.post("/webhooks/anchor")
async def anchor_webhook(request: Request):
    raw = await request.body()
    sig = request.headers.get("X-Anchor-Signature", "")
    if not verify_webhook_signature(raw, sig):
        raise HTTPException(401, "Invalid signature")
    try:
        event = await request.json()
    except Exception:
        event = {}
    evt_type = event.get("type") or event.get("event_type", "")
    log.info("[anchor webhook %s] mock=%s", evt_type, is_mock())
    # persist raw event for audit
    await db.webhook_events.insert_one({"received_at": datetime.now(timezone.utc).isoformat(), "type": evt_type, "payload": event})
    handler_fn = EVENT_HANDLERS.get(evt_type)
    if handler_fn:
        try:
            await handler_fn(event)
        except Exception as e:
            log.exception("webhook handler failed: %s", e)
    return JSONResponse({"ok": True, "handled": bool(handler_fn)})
