"""
Supabase helper for persisting call results.
"""
import os
import logging
from supabase import create_client

log = logging.getLogger("db")

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


def save_call_result(
    call_id: str,
    customer_id: str,
    campaign: str,
    duration_ms: int | None,
    end_reason: str | None,
    transcript: str,
    summary: dict,
):
    """
    Insert one call's summary into the call_results table.
    Upserts on call_id — re-running the same call replaces (doesn't duplicate).
    """
    if not summary:
        log.warning("Empty summary, skipping DB insert for call_id=%s", call_id)
        return

    row = {
        "call_id": call_id,
        "customer_id": customer_id,
        "campaign": campaign,
        "duration_ms": duration_ms,
        "end_reason": end_reason,
        "transcript": transcript,
        "disposition": summary.get("disposition"),
        "interest_level": summary.get("interest_level"),
        "customer_decision": summary.get("customer_decision"),
        "escalation_needed": summary.get("escalation_needed", False),
        "escalation_reason": summary.get("escalation_reason", ""),
        "key_quotes": summary.get("key_quotes", []),
        "objections_raised": summary.get("objections_raised", []),
        "next_action": summary.get("next_action"),
        "follow_up_within_hours": summary.get("follow_up_within_hours"),
        "sentiment": summary.get("sentiment"),
        "notes_for_marketing": summary.get("notes_for_marketing"),
    }

    try:
        sb.table("call_results").upsert(row, on_conflict="call_id").execute()
        log.info("  -> row saved to Supabase (call_id=%s)", call_id[:12])
    except Exception as e:
        log.exception("Supabase insert failed: %s", e)