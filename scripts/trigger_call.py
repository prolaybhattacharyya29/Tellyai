"""
Fire an outbound call from Retell to one customer in customers.csv.
Loads the right campaign prompt based on the customer's `campaign` field
and injects it as a dynamic variable.

Usage:
    python -m scripts.trigger_call CUST-10000
"""
import os
import sys
import httpx
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

from scripts.generate_opening import generate_opening

load_dotenv()

RETELL_KEY = os.environ["RETELL_API_KEY"]
AGENT_ID = os.environ["RETELL_AGENT_ID"]
FROM_NUMBER = os.environ["RETELL_FROM_NUMBER"]

# Map campaign names (as in the CSV) to campaign prompt filenames.
CAMPAIGN_FILES = {
    "Cross-sell": "cross_sell.md",
    "Pre-approved offer": "pre_approved.md",
    "Reactivation": "reactivation.md",
    "Winback": "winback.md",
    "Payment reminder": "payment_reminder.md",
    "Early collections": "early_collections.md",
    "Onboarding": "onboarding.md",
    "EMI conversion": "emi_conversion.md",
    "Renewal": "renewal.md",
    "Pre-closure retention": "pre_closure.md",
    "Lead follow-up": "lead_followup.md",
    "NPS feedback": "nps_feedback.md",
}


def profile_to_text(row: dict) -> str:
    """Format one CSV row as a compact profile string."""
    parts = []
    for k, v in row.items():
        if v == "" or pd.isna(v):
            continue
        parts.append(f"{k}: {v}")
    return ". ".join(parts) + "."


def load_campaign_rules(campaign: str) -> str:
    """Load the campaign-specific prompt from prompts/campaigns/."""
    filename = CAMPAIGN_FILES.get(campaign)
    if filename is None:
        return f"(No campaign rules available for '{campaign}'. Follow universal rules.)"

    path = Path("prompts/campaigns") / filename
    if not path.exists():
        return f"(Campaign file {filename} not found. Follow universal rules.)"

    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return f"(Campaign file {filename} is empty. Follow universal rules.)"

    return content


def place_call(customer: dict) -> dict:
    opening = generate_opening(customer)
    profile_text = profile_to_text(customer)
    campaign = customer.get("campaign", "")
    campaign_rules = load_campaign_rules(campaign)

    body = {
        "from_number": FROM_NUMBER,
        "to_number": customer["phone"],
        "override_agent_id": AGENT_ID,
        "retell_llm_dynamic_variables": {
            "opening_line": opening,
            "customer_profile": profile_text,
            "campaign_rules": campaign_rules,
        },
        "metadata": {
            "customer_id": customer["customer_id"],
            "campaign": campaign,
        },
    }

    print(f"  campaign:  {campaign}")
    print(f"  calling    {customer['phone']}")
    print(f"  opening:   {opening}")

    r = httpx.post(
        "https://api.retellai.com/v2/create-phone-call",
        headers={"Authorization": f"Bearer {RETELL_KEY}"},
        json=body,
        timeout=30,
    )

    if r.status_code not in (200, 201):
        print(f"\nFAIL: status {r.status_code}")
        print(r.text)
        sys.exit(1)

    return r.json()


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.trigger_call CUST-10000")
        sys.exit(1)

    cust_id = sys.argv[1]
    df = pd.read_csv("data/customers.csv", dtype={"phone": str})
    row = df[df["customer_id"] == cust_id]
    if row.empty:
        print(f"Customer {cust_id} not found in CSV")
        sys.exit(1)

    customer = row.iloc[0].to_dict()
    print(f"Triggering call for {cust_id} ({customer.get('name', '?')})")
    result = place_call(customer)
    print(f"\nOK -- call_id = {result.get('call_id', '?')}")
    print("Your phone should ring in 5-10 seconds.")


if __name__ == "__main__":
    main()