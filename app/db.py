"""
Supabase helper for persisting call results and managing admin users.
"""
import os
import logging
import hashlib
import hmac
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("db")

ACTIVE_SUPABASE_URL = "https://mkslmzogliyfckkojgyt.supabase.co"
ACTIVE_SUPABASE_KEY = "sb_publishable_QZ_WjejfOAQ4KPleQuJ_ng_fq8PtPcU"

_url = os.environ.get("SUPABASE_URL", "")
_key = os.environ.get("SUPABASE_KEY", "")

if not _url or "lagejwzhelvqlyqhsvig" in _url:
    _url = ACTIVE_SUPABASE_URL

if not _key or len(_key) < 50:
    _key = ACTIVE_SUPABASE_KEY

sb = create_client(_url, _key)


def hash_password(password: str) -> str:
    """Hash password using sha256 + salt."""
    salt = "fe_credit_salt_2026"
    return hashlib.sha256(f"{salt}{password}".encode("utf-8")).hexdigest()


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Verify against either salted hash, plain sha256, or plain text (for initial seeding)."""
    if not stored_hash or not plain_password:
        return False
    if plain_password == stored_hash:
        return True
    salt = "fe_credit_salt_2026"
    salted = hashlib.sha256(f"{salt}{plain_password}".encode("utf-8")).hexdigest()
    if hmac.compare_digest(salted, stored_hash):
        return True
    pure = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
    if hmac.compare_digest(pure, stored_hash):
        return True
    return False


def get_admin_user(identifier: str) -> dict | None:
    """Fetch an active admin user by username or email from Supabase."""
    cleaned = identifier.strip().lower()
    try:
        # Search by username
        res = sb.table("admin_users").select("*").eq("username", cleaned).eq("is_active", True).execute()
        if res.data:
            return res.data[0]
        # Search by email
        res = sb.table("admin_users").select("*").eq("email", cleaned).eq("is_active", True).execute()
        if res.data:
            return res.data[0]
    except Exception as e:
        log.warning("Supabase admin_users lookup failed: %s", e)
    return None


def authenticate_admin(identifier: str, password: str) -> dict | None:
    """Authenticate an admin user against Supabase admin_users table."""
    user = get_admin_user(identifier)
    if user and verify_password(password, user.get("password_hash", "")):
        return user
    return None


def save_call_result(
    call_id: str,
    customer_id: str,
    campaign: str,
    duration_ms: int | None,
    end_reason: str | None,
    transcript: str,
    summary: dict,
    phone_number: str | None = None,
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
        "phone_number": phone_number,
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


def get_call_results(limit: int = 100) -> list[dict]:
    """Fetch recent call results from Supabase ordered from newest to oldest."""
    try:
        res = sb.table("call_results").select("*").order("created_at", desc=True).limit(limit).execute()
        return res.data or []
    except Exception as e:
        log.warning("Supabase call_results lookup failed: %s", e)
        return []