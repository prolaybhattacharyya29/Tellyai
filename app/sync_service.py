"""
Service to fetch recent calls from Retell AI and sync any missing calls into Supabase.
"""

import os
import logging
import httpx
from dotenv import load_dotenv
from supabase import create_client
from app.summarize import summarize_call
from app.db import save_call_result, sb

load_dotenv()
log = logging.getLogger("sync_service")

RETELL_KEY = os.environ.get("RETELL_API_KEY")


def sync_recent_calls(limit: int = 15) -> dict:
    if not RETELL_KEY:
        return {"ok": False, "error": "Missing Retell environment variable RETELL_API_KEY."}

    try:
        existing_res = sb.table("call_results").select("call_id").execute()
        existing_call_ids = {r["call_id"] for r in (existing_res.data or [])}

        r = httpx.post(
            "https://api.retellai.com/v3/list-calls",
            headers={"Authorization": f"Bearer {RETELL_KEY}"},
            json={"limit": limit, "sort_order": "descending"},
            timeout=30,
        )

        if r.status_code != 200:
            return {"ok": False, "error": f"Retell API error: {r.status_code} {r.text}"}

        items = r.json().get("items", [])
        synced = []

        for call_item in items:
            call_id = call_item.get("call_id")
            if not call_id or call_id in existing_call_ids:
                continue

            c_resp = httpx.get(
                f"https://api.retellai.com/v2/get-call/{call_id}",
                headers={"Authorization": f"Bearer {RETELL_KEY}"},
                timeout=30,
            )
            if c_resp.status_code != 200:
                continue

            call_data = c_resp.json()
            transcript = call_data.get("transcript", "") or ""
            duration_ms = call_data.get("duration_ms")
            end_reason = call_data.get("disconnection_reason", "unknown")
            metadata = call_data.get("metadata") or {}
            customer_id = metadata.get("customer_id", "unknown")
            campaign = metadata.get("campaign", "General")
            customer_name = metadata.get("customer_name", "Customer")
            phone_number = call_data.get("to_number") or metadata.get("phone")

            customer_info = {"customer_id": customer_id, "name": customer_name}
            summary = summarize_call(transcript, customer_info, campaign, duration_ms)

            save_call_result(
                call_id=call_id,
                customer_id=customer_id,
                campaign=campaign,
                phone_number=phone_number,
                duration_ms=duration_ms,
                end_reason=end_reason,
                transcript=transcript,
                summary=summary,
            )
            existing_call_ids.add(call_id)
            synced.append(call_id)

        return {"ok": True, "synced_count": len(synced), "synced_call_ids": synced}

    except Exception as e:
        log.exception("Error during sync_recent_calls: %s", e)
        return {"ok": False, "error": str(e)}
