"""
Post-call summarizer.
Takes a call transcript + customer profile + campaign and asks Claude to
return a structured JSON summary.
"""
import os
import json
import logging
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("summarize")

client = Anthropic()
SYSTEM_PROMPT = Path("prompts/summary.md").read_text(encoding="utf-8")


def summarize_call(transcript: str, customer: dict, campaign: str, duration_ms: int | None = None) -> dict:
    """
    Send transcript + context to Claude, return the structured summary dict.
    Returns an empty dict on failure (logged).
    """
    if not transcript or not transcript.strip():
        return {
            "disposition": "no_answer",
            "interest_level": "None",
            "customer_decision": "No transcript — customer did not engage.",
            "call_duration_seconds": (duration_ms or 0) // 1000,
            "escalation_needed": False,
            "escalation_reason": "",
            "key_quotes": [],
            "objections_raised": [],
            "next_action": "Retry after 24 hours.",
            "follow_up_within_hours": 24,
            "sentiment": "Neutral",
            "notes_for_marketing": "Empty transcript — likely no-answer or very short call.",
        }

    user_content = (
        f"CAMPAIGN: {campaign}\n\n"
        f"CUSTOMER PROFILE: {json.dumps(customer, ensure_ascii=False)}\n\n"
        f"CALL DURATION: {(duration_ms or 0) // 1000} seconds\n\n"
        f"TRANSCRIPT:\n{transcript}"
    )

    try:
        msg = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1200,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        raw = msg.content[0].text.strip()

        # Strip possible markdown fences
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        summary = json.loads(raw)
        return summary

    except json.JSONDecodeError as e:
        log.error("Claude returned non-JSON: %s", raw[:500])
        return {
            "disposition": "no_answer",
            "interest_level": "None",
            "customer_decision": "Summary generation failed — see raw webhook file.",
            "call_duration_seconds": (duration_ms or 0) // 1000,
            "escalation_needed": False,
            "escalation_reason": "",
            "key_quotes": [],
            "objections_raised": [],
            "next_action": "Manual review.",
            "follow_up_within_hours": 24,
            "sentiment": "Neutral",
            "notes_for_marketing": f"Summarizer parse error: {e}",
        }

    except Exception as e:
        log.exception("Summarize failed: %s", e)
        return {}