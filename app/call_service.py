"""
Service to initiate demo outbound calls for Toki AI Voice Assistant.
"""

import logging
import os
from pathlib import Path

import httpx
import pandas as pd
from dotenv import load_dotenv

from app.campaigns import CAMPAIGNS

load_dotenv()
log = logging.getLogger("call_service")

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


# Campaign-specific one-liner Marissa says after the greeting
CAMPAIGN_INTROS = {
    "Cross-sell": "I'm calling with a product opportunity that might suit your profile.",
    "Pre-approved Offer": "I'm calling because you have a pre-approved loan offer ready and waiting for you.",
    "Reactivation": "It's been a while since we've connected, and I'm calling with a special offer for returning customers like yourself.",
    "Winback": "I'm calling to reconnect and share something we've put together specially for you.",
    "Payment Reminder": "I'm calling with a friendly reminder about your upcoming EMI payment.",
    "Early Collections": "I'm calling about your loan account and would like to work with you on bringing it current.",
    "Onboarding": "I'm calling to welcome you to Toki and help you make the most of your new product.",
    "EMI Conversion": "I'm calling because there's an option to convert your outstanding card balance into a more manageable EMI plan.",
    "Renewal": "I'm calling about an upcoming renewal on one of your products with us.",
    "Pre-closure Retention": "I'm calling because your loan with us is nearing its final payments, and I wanted to discuss the options available.",
    "Lead Follow-up": "I'm following up on your recent interest in one of our products.",
    "NPS / Feedback": "I'm calling to get your quick feedback on your recent experience with Toki.",
}


def extract_first_name(full_name: str) -> str:
    """For Vietnamese names the given name is the last word."""
    if not full_name or not full_name.strip():
        return "there"
    parts = full_name.strip().split()
    return parts[-1] if parts else "there"


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


def generate_opening_line(customer: dict, campaign_title: str, language: str = "English") -> str:
    """Generate a deterministic opening line with AI disclosure and campaign-specific intro."""
    full_name = customer.get("name", "there")
    first_name = extract_first_name(full_name)
    intro = CAMPAIGN_INTROS.get(
        campaign_title,
        "I'm calling from Toki with something I think might interest you.",
    )
    if "en" in language.lower():
        return (
            f"Hi {first_name}, this is Marissa, an AI assistant calling on behalf of "
            f"Toki. {intro} Do you have a quick minute to chat?"
        )
    return (
        f"Xin chào {first_name}, em là Marissa, trợ lý AI gọi từ Toki. "
        f"Do you have a quick minute to chat?"
    )


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

    opening = generate_opening_line(customer, campaign_title=campaign_info["title"], language=language)
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
