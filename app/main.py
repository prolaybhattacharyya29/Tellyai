"""
FastAPI webhook server that receives Retell call events.
Run from project root:
    uvicorn app.main:app --reload --port 8000

Keep this running in a dedicated terminal during testing.
"""
import os
import json
import logging
from datetime import datetime
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, Request
from dotenv import load_dotenv

from app.summarize import summarize_call
from app.db import save_call_result

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("webhook")

RAW_DIR = Path("cache/webhook_raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

SUMMARY_DIR = Path("cache/call_summaries")
SUMMARY_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI()

# Load customer DB once at startup so webhook has access to profiles
CUSTOMERS_DF = pd.read_csv("data/customers.csv", dtype={"phone": str})
CUSTOMERS_BY_ID = {row["customer_id"]: row.to_dict() for _, row in CUSTOMERS_DF.iterrows()}


@app.get("/")
async def root():
    return {
        "status": "ok",
        "server": "FE Credit AI calling webhook",
        "time": datetime.now().isoformat(timespec="seconds"),
    }


@app.post("/retell-webhook")
async def retell_webhook(request: Request):
    body = await request.json()
    event = body.get("event", "<no-event>")
    call = body.get("call", {}) or {}
    call_id = call.get("call_id", "?")
    customer_id = (call.get("metadata") or {}).get("customer_id", "unknown")
    campaign = (call.get("metadata") or {}).get("campaign", "unknown")

    log.info("EVENT=%s  call_id=%s  customer=%s  campaign=%s",
             event, call_id, customer_id, campaign)

    # Save raw webhook event
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = RAW_DIR / f"{timestamp}_{event}_{call_id[:12]}.json"
    raw_path.write_text(json.dumps(body, indent=2, ensure_ascii=False), encoding="utf-8")

    if event == "call_ended":
        transcript = call.get("transcript", "") or ""
        duration_ms = call.get("duration_ms")
        end_reason = call.get("disconnection_reason", "unknown")

        log.info("  → call ended: duration=%sms, reason=%s, transcript_len=%d",
                 duration_ms, end_reason, len(transcript))

        # Look up customer profile
        customer = CUSTOMERS_BY_ID.get(customer_id, {"customer_id": customer_id})

        # Summarize via Claude
        log.info("  → summarizing with Claude...")
        summary = summarize_call(transcript, customer, campaign, duration_ms)

        if summary:
            log.info("  → disposition=%s  interest=%s  escalation=%s",
                     summary.get("disposition"),
                     summary.get("interest_level"),
                     summary.get("escalation_needed"))

            # Save summary to disk for inspection
            summary_record = {
                "call_id": call_id,
                "customer_id": customer_id,
                "campaign": campaign,
                "duration_ms": duration_ms,
                "end_reason": end_reason,
                "transcript": transcript,
                "summary": summary,
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
            summary_path = SUMMARY_DIR / f"{timestamp}_{call_id[:12]}.json"
            summary_path.write_text(
                json.dumps(summary_record, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            log.info("  → summary saved to %s", summary_path.name)
            
            # Insert into Supabase
            save_call_result(
                call_id=call_id,
                customer_id=customer_id,
                campaign=campaign,
                duration_ms=duration_ms,
                end_reason=end_reason,
                transcript=transcript,
                summary=summary,
            )

    elif event == "call_analyzed":
        log.info("  → Retell's own analysis arrived (we use our own)")

    return {"ok": True, "received_event": event}