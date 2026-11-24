"""
Service to initiate demo outbound calls for FE Credit AI Voice Assistant.
"""

import logging
import os
from pathlib import Path

import httpx
import pandas as pd
from anthropic import Anthropic
from dotenv import load_dotenv

from app.campaigns import CAMPAIGNS

load_dotenv()
log = logging.getLogger("call_service")

CACHE_OPENINGS_DIR = Path("cache/openings")
CACHE_OPENINGS_DIR.mkdir(parents=True, exist_ok=True)


def load_campaign_rules(filename: str) -> str:
    path = Path("prompts/campaigns") / filename
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return "Follow universal lending customer conversation guidelines."


def profile_to_text(row: dict) -> str:
    parts = []
    for k, v in row.items():
        if v == "" or pd.isna(v):
            continue
        parts.append(f"{k}: {v}")
    return ". ".join(parts) + "."


def get_customer_for_campaign(campaign_csv_name: str) -> dict:
    csv_path = Path("data/customers.csv")
    if csv_path.exists():
        df = pd.read_csv(csv_path, dtype={"phone": str})
        matching = df[df["campaign"].str.lower() == campaign_csv_name.lower()]
        if not matching.empty:
            return matching.iloc[0].to_dict()
        if not df.empty:
            c = df.iloc[0].to_dict()
            c["campaign"] = campaign_csv_name
            return c

    # Fallback template todo : need to remove this
    return {
        "customer_id": "DEMO-001",
        "name": "Nguyễn Văn Hùng",
        "phone": "",
        "age": 35,
        "city": "Hồ Chí Minh City",
        "occupation": "Office Worker",
        "monthly_income_vnd": 15000000,
        "prior_loans": 1,
        "last_loan_status": "Paid",
        "product_fit": "Personal Loan",
        "preferred_time": "Afternoon",
        "campaign": campaign_csv_name,
    }


def generate_opening_line(customer: dict, language: str = "English") -> str:
    """Generate dynamic opening line with Claude, cached per customer."""
    customer_id = customer.get("customer_id", "demo")
    cache_file = CACHE_OPENINGS_DIR / f"{customer_id}_{language[:2].lower()}.txt"
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8").strip()

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    if not anthropic_key:
        return f"Xin chào {customer.get('name', 'quý khách')}, em là trợ lý ảo gọi từ FE Credit."

    try:
        client = Anthropic(api_key=anthropic_key)
        sys_prompt_path = Path("prompts/opening_system.md")
        system_prompt = (
            sys_prompt_path.read_text(encoding="utf-8")
            if sys_prompt_path.exists()
            else ""
        )
        profile = profile_to_text(customer)

        lang_note = (
            "Respond in English."
            if "en" in language.lower()
            else "Respond in Vietnamese."
        )
        msg = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=100,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"Customer profile:\n{profile}\nLanguage instruction: {lang_note}",
                }
            ],
        )
        opening = msg.content[0].text.strip().strip('"').strip("'")
        cache_file.write_text(opening, encoding="utf-8")
        return opening
    except Exception as e:
        log.warning("Claude opening generation failed: %s", e)
        name = customer.get("name", "customer")
        if "en" in language.lower():
            return f"Hello {name}, I am calling from FE Credit regarding your account services."
        return f"Xin chào {name}, em là trợ lý ảo gọi từ FE Credit."


def trigger_call(campaign_key: str, phone: str, language: str = "English") -> dict:
    """Place an outbound call using Retell AI."""
    campaign_info = CAMPAIGNS.get(campaign_key)
    if not campaign_info:
        raise ValueError(f"Unknown campaign key: {campaign_key}")

    retell_key = os.environ.get("RETELL_API_KEY")
    agent_id = os.environ.get("RETELL_AGENT_ID")
    from_number = os.environ.get("RETELL_FROM_NUMBER")

    if not retell_key or not agent_id or not from_number:
        raise RuntimeError(
            "Retell environment variables (RETELL_API_KEY, RETELL_AGENT_ID, RETELL_FROM_NUMBER) are missing."
        )

    # Format phone number
    cleaned_phone = phone.strip()
    if not cleaned_phone.startswith("+"):
        cleaned_phone = f"+{cleaned_phone}"

    # Load matching demo customer profile
    customer = get_customer_for_campaign(campaign_info["csv_name"])
    customer["phone"] = cleaned_phone

    opening = generate_opening_line(customer, language=language)
    profile_text = profile_to_text(customer)
    campaign_rules = load_campaign_rules(campaign_info["file"])

    body = {
        "from_number": from_number,
        "to_number": cleaned_phone,
        "override_agent_id": agent_id,
        "retell_llm_dynamic_variables": {
            "opening_line": opening,
            "customer_profile": profile_text,
            "campaign_rules": campaign_rules,
        },
        "metadata": {
            "customer_id": customer.get("customer_id", "demo"),
            "campaign": campaign_info["csv_name"],
            "language": language,
        },
    }

    resp = httpx.post(
        "https://api.retellai.com/v2/create-phone-call",
        headers={"Authorization": f"Bearer {retell_key}"},
        json=body,
        timeout=30,
    )

    if resp.status_code not in (200, 201):
        err_msg = resp.text
        log.error("Retell call trigger failed [%d]: %s", resp.status_code, err_msg)
        raise RuntimeError(f"Retell API error ({resp.status_code}): {err_msg}")

    data = resp.json()
    return {
        "call_id": data.get("call_id"),
        "customer_name": customer.get("name"),
        "phone": cleaned_phone,
        "campaign": campaign_info["title"],
        "opening_line": opening,
    }
