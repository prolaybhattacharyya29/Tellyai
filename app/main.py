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
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv

from app.summarize import summarize_call
from app.db import save_call_result, authenticate_admin, get_call_results
from app.call_service import trigger_call
from app.sync_service import sync_recent_calls
from app.campaigns import CAMPAIGNS_LIST

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

# Session support for authentication
SESSION_SECRET = os.environ.get("SESSION_SECRET", "fe-credit-demo-secret-key-2026")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, max_age=86400 * 7)

# Jinja2 Templates Engine
templates = Jinja2Templates(directory="frontend")

# Demo Login Credentials
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "admin123")
DEMO_USERS = {
    os.environ.get("DEMO_USER", "admin@fecredit.com").lower(): DEMO_PASSWORD,
    "admin": DEMO_PASSWORD,
    "demo@fecredit.com": DEMO_PASSWORD,
    "demo": DEMO_PASSWORD,
    "admin@xtagelabs.com": "xtage@2026kk",
}

# Mount frontend static assets
if Path("frontend/css").exists():
    app.mount("/css", StaticFiles(directory="frontend/css"), name="css")
if Path("frontend/js").exists():
    app.mount("/js", StaticFiles(directory="frontend/js"), name="js")

# Load customer DB once at startup so webhook has access to profiles
CUSTOMERS_DF = pd.read_csv("data/customers.csv", dtype={"phone": str})
CUSTOMERS_BY_ID = {row["customer_id"]: row.to_dict() for _, row in CUSTOMERS_DF.iterrows()}

FAVICON_PATH = Path("frontend/favicon.svg")


@app.get("/favicon.ico", include_in_schema=False)
@app.get("/favicon.svg", include_in_schema=False)
async def get_favicon():
    if FAVICON_PATH.exists():
        return FileResponse(FAVICON_PATH, media_type="image/svg+xml")
    return JSONResponse(status_code=404, content={"error": "Favicon not found"})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.session.get("user"):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(request=request, name="login.html", context={"error": None})


@app.post("/login", response_class=HTMLResponse)
async def handle_login(request: Request):
    form = await request.form()
    username = form.get("username", "").strip().lower()
    password = form.get("password", "").strip()

    # 1. First authenticate against database table (admin_users in Supabase)
    db_user = authenticate_admin(username, password)
    if db_user:
        request.session["user"] = db_user.get("username", username)
        request.session["user_name"] = db_user.get("full_name") or db_user.get("name") or "admin"
        request.session["user_role"] = db_user.get("role", "admin")
        log.info("Admin user '%s' (%s) authenticated via database.", username, db_user.get("role"))
        return RedirectResponse(url="/", status_code=303)

    # 2. Fallback to configured DEMO_USERS in .env
    expected_pwd = DEMO_USERS.get(username)
    if expected_pwd and expected_pwd == password:
        request.session["user"] = username
        log.info("User '%s' logged in via fallback demo credentials.", username)
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": "Invalid username or password. Please try again."},
        status_code=400,
    )


@app.get("/logout")
async def logout(request: Request):
    user = request.session.pop("user", None)
    if user:
        log.info("User '%s' logged out.", user)
    return RedirectResponse(url="/login", status_code=303)


@app.get("/api/campaigns")
async def get_campaigns():
    return CAMPAIGNS_LIST


@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard(request: Request):
    # Require login first
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "user": request.session.get("user"),
            "campaigns_json": json.dumps(CAMPAIGNS_LIST, ensure_ascii=False),
        },
    )


@app.get("/logs", response_class=HTMLResponse)
async def serve_logs(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=303)

    calls = get_call_results(limit=100)
    return templates.TemplateResponse(
        request=request,
        name="logs.html",
        context={
            "user": request.session.get("user"),
            "calls": calls,
            "calls_json": json.dumps(calls, default=str, ensure_ascii=False),
        },
    )


@app.get("/api/debug-diag")
async def api_debug_diag():
    from app.db import sb, _url, _key
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    retell_key = os.environ.get("RETELL_API_KEY", "")

    db_err = None
    row_count = None
    try:
        res = sb.table("call_results").select("call_id").limit(10).execute()
        row_count = len(res.data) if res.data else 0
    except Exception as e:
        db_err = str(e)

    return {
        "supabase_url": _url,
        "supabase_key_len": len(_key),
        "anthropic_key_present": bool(anthropic_key),
        "retell_key_present": bool(retell_key),
        "db_row_count": row_count,
        "db_error": db_err,
    }


@app.get("/api/call-results")
async def api_call_results(limit: int = 100):
    calls = get_call_results(limit=limit)
    return {"ok": True, "count": len(calls), "data": calls}


@app.api_route("/health", methods=["GET", "HEAD", "POST"])
@app.api_route("/health/", methods=["GET", "HEAD", "POST"])
async def health_check():
    return {
        "status": "ok",
        "server": "FE Credit AI calling webhook",
        "time": datetime.now().isoformat(timespec="seconds"),
    }


@app.post("/api/trigger-call")
async def api_trigger_call(request: Request):
    if not request.session.get("user"):
        return JSONResponse(status_code=401, content={"ok": False, "error": "Authentication required. Please sign in."})

    try:
        payload = await request.json()
        campaign = payload.get("campaign")
        phone = payload.get("phone")
        language = payload.get("language", "English")

        if not campaign or not phone:
            return JSONResponse(status_code=400, content={"ok": False, "error": "Campaign and phone number are required."})

        result = trigger_call(campaign_key=campaign, phone=phone, language=language)
        return {"ok": True, **result}
    except Exception as e:
        log.exception("Call trigger error: %s", e)
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})


@app.api_route("/api/sync-calls", methods=["GET", "POST"])
async def api_sync_calls():
    """Manual sync endpoint to fetch completed calls from Retell AI into Supabase."""
    res = sync_recent_calls(limit=15)
    return res


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

    if event in ("call_ended", "call_analyzed"):
        transcript = call.get("transcript", "") or ""
        duration_ms = call.get("duration_ms")
        end_reason = call.get("disconnection_reason", "unknown")

        log.info("  → call ended/analyzed: duration=%sms, reason=%s, transcript_len=%d",
                 duration_ms, end_reason, len(transcript))

        # Look up customer profile
        customer = CUSTOMERS_BY_ID.get(customer_id, {"customer_id": customer_id})

        # Summarize via Claude
        log.info("  → summarizing with Claude...")
        summary = summarize_call(transcript, customer, campaign, duration_ms)

        if not summary:
            log.warning("Empty summary from Claude, using fallback summary.")
            is_connected = (duration_ms or 0) > 8000
            summary = {
                "disposition": "completed" if is_connected else "no_answer",
                "interest_level": "Medium" if is_connected else "None",
                "customer_decision": "Call completed." if is_connected else "No customer response or short interaction.",
                "call_duration_seconds": (duration_ms or 0) // 1000,
                "escalation_needed": False,
                "escalation_reason": "",
                "key_quotes": [],
                "objections_raised": [],
                "next_action": "Follow up as appropriate.",
                "follow_up_within_hours": 24,
                "sentiment": "Neutral",
                "notes_for_marketing": "Auto-processed interaction.",
            }

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
        phone_number = call.get("to_number") or customer.get("phone")
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

    elif event == "call_analyzed":
        log.info("  → Retell's own analysis arrived (we use our own)")

    return {"ok": True, "received_event": event}