"""Resend email helpers."""
import asyncio
import logging
import os
from typing import Optional

import resend
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")

log = logging.getLogger("helix.email")

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "Helix Platform <onboarding@resend.dev>")

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY


async def send_email(recipient: str, subject: str, html: str, text: Optional[str] = None) -> dict:
    if not RESEND_API_KEY:
        log.warning("[EMAIL STUB] to=%s subject=%s", recipient, subject)
        return {"status": "stubbed", "id": None}
    params = {"from": SENDER_EMAIL, "to": [recipient], "subject": subject, "html": html}
    if text:
        params["text"] = text
    try:
        res = await asyncio.to_thread(resend.Emails.send, params)
        log.info("Email sent to %s (%s) id=%s", recipient, subject, res.get("id") if isinstance(res, dict) else res)
        return {"status": "sent", "id": res.get("id") if isinstance(res, dict) else None}
    except Exception as e:
        log.error("Email send failed: %s", e)
        return {"status": "failed", "error": str(e)}


# ---- templates ----

_BRAND_HEADER = """
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0A1628;padding:24px 0;">
  <tr><td align="center">
    <span style="color:#C9922A;font-family:Inter,Arial,sans-serif;font-weight:700;letter-spacing:2px;font-size:20px;">HELIX PLATFORM</span>
  </td></tr>
</table>
"""

def wrap_email(title: str, body_html: str, cta_label: Optional[str] = None, cta_url: Optional[str] = None) -> str:
    cta = ""
    if cta_label and cta_url:
        cta = f'<p style="margin:32px 0;"><a href="{cta_url}" style="background:#C9922A;color:#0A1628;text-decoration:none;padding:12px 24px;font-weight:700;font-family:Inter,Arial,sans-serif;display:inline-block;">{cta_label}</a></p>'
    return f"""
    <html><body style="margin:0;background:#F5F5F5;font-family:Inter,Arial,sans-serif;color:#1A1A2E;">
    {_BRAND_HEADER}
    <table width="100%" cellpadding="0" cellspacing="0" style="padding:32px 16px;">
      <tr><td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border:1px solid #e5e7eb;max-width:600px;">
          <tr><td style="padding:32px;">
            <h1 style="color:#0A1628;font-size:22px;margin:0 0 16px 0;">{title}</h1>
            <div style="color:#1A1A2E;font-size:15px;line-height:1.6;">{body_html}</div>
            {cta}
            <p style="margin-top:32px;color:#6b7280;font-size:11px;line-height:1.5;">
              Helix Platform · Connecting Africa to the World, One Trade at a Time<br/>
              Powered by <b>DobbleHelix Limited</b> (Nigeria &amp; Africa Operations) · <b>Riby Inc</b> (United States &amp; Global Operations) · <b>JompStart Digital Limited</b> (Business Credit) · <b>Anchor</b> (Global Banking &amp; Payment Service)
            </p>
          </td></tr>
        </table>
      </td></tr>
    </table>
    </body></html>
    """
