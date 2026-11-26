"""
scripts/trigger_call.py

Fires an outbound Retell AI call for a specific campaign + customer.
Reads campaign CSVs from the OneDrive data folder.
Generates opening_line and first_name so the prompt's {{opening_line}}
and {{first_name}} placeholders resolve.

Usage:
    python -m scripts.trigger_call --campaign cross_sell --customer_id XS-10000
"""

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from retell import Retell

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = Path(os.getenv(
    "CAMPAIGN_DATA_DIR",
    r"C:\Users\Prolay Bhattacharyya\OneDrive\Documents\Fe Credit data"
))

RETELL_API_KEY = os.getenv("RETELL_API_KEY")
RETELL_AGENT_ID = os.getenv("RETELL_AGENT_ID")
RETELL_LLM_ID = os.getenv("RETELL_LLM_ID")
RETELL_FROM_NUMBER = os.getenv("RETELL_FROM_NUMBER")

CAMPAIGNS = [
    "cross_sell", "pre_approved", "reactivation", "winback",
    "payment_reminder", "early_collections", "onboarding",
    "emi_conversion", "renewal", "pre_closure",
    "lead_followup", "nps_feedback",
]

# One-line campaign intro Marissa says after the greeting.
CAMPAIGN_INTROS = {
    "cross_sell":         "I'm calling with a product opportunity that might suit your profile.",
    "pre_approved":       "I'm calling because you have a pre-approved loan offer ready and waiting for you.",
    "reactivation":       "It's been a while since we've connected, and I'm calling with a special offer for returning customers like yourself.",
    "winback":            "I'm calling to reconnect and share something we've put together specially for you.",
    "payment_reminder":   "I'm calling with a friendly reminder about your upcoming EMI payment.",
    "early_collections":  "I'm calling about your loan account and would like to work with you on bringing it current.",
    "onboarding":         "I'm calling to welcome you to FE Credit and help you make the most of your new product.",
    "emi_conversion":     "I'm calling because there's an option to convert your outstanding card balance into a more manageable EMI plan.",
    "renewal":            "I'm calling about an upcoming renewal on one of your products with us.",
    "pre_closure":        "I'm calling because your loan with us is nearing its final payments, and I wanted to discuss the options available.",
    "lead_followup":      "I'm following up on your recent interest in one of our products.",
    "nps_feedback":       "I'm calling to get your quick feedback on your recent experience with FE Credit.",
}


def load_campaign_data(campaign):
    csv_path = DATA_DIR / f"{campaign}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Campaign data not found: {csv_path}\n"
            f"Check the file exists in: {DATA_DIR}"
        )
    return pd.read_csv(csv_path, dtype=str)


def load_campaign_prompt(campaign):
    prompt_path = PROJECT_ROOT / "prompts" / "campaigns" / f"{campaign}.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Campaign prompt not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def extract_first_name(full_name):
    """For Vietnamese names like 'Nguyen Thi Minh Chi', the given name is the
    last word ('Chi'). For other names, same rule works well enough."""
    if not full_name or not full_name.strip():
        return "there"
    parts = full_name.strip().split()
    return parts[-1] if parts else "there"


def make_opening_line(campaign, first_name):
    """Generate a short, campaign-aware opening line Marissa speaks first.
    Must explicitly disclose AI identity — regulatory requirement."""
    intro = CAMPAIGN_INTROS.get(
        campaign,
        "I'm calling from FE Credit with something I think might interest you."
    )
    return (
        f"Hi {first_name}, this is Marissa, an AI assistant calling on behalf of "
        f"FE Credit. {intro} Do you have a quick minute to chat?"
    )


def row_to_variables(row):
    """Convert row → {str: str} for Retell dynamic variables. Skip blanks."""
    out = {}
    for col, val in row.items():
        s = str(val).strip()
        if not s or s.lower() == "nan":
            continue
        out[col] = s
    return out


def main():
    parser = argparse.ArgumentParser(description="Trigger a Retell AI outbound call")
    parser.add_argument("--campaign", required=True, choices=CAMPAIGNS)
    parser.add_argument("--customer_id", required=True)
    args = parser.parse_args()

    missing = [k for k, v in {
        "RETELL_API_KEY": RETELL_API_KEY,
        "RETELL_AGENT_ID": RETELL_AGENT_ID,
        "RETELL_LLM_ID": RETELL_LLM_ID,
        "RETELL_FROM_NUMBER": RETELL_FROM_NUMBER,
    }.items() if not v]
    if missing:
        print(f"❌ Missing env vars: {', '.join(missing)}")
        sys.exit(1)

    print(f"📁 Data folder: {DATA_DIR}")
    print(f"📂 Campaign: {args.campaign}")
    print(f"👤 Customer:  {args.customer_id}")

    df = load_campaign_data(args.campaign)
    match = df[df["customer_id"] == args.customer_id]
    if len(match) == 0:
        print(f"❌ Customer {args.customer_id} not found in {args.campaign}.csv")
        sys.exit(1)
    row = match.iloc[0]

    prompt_template = load_campaign_prompt(args.campaign)

    # Build dynamic variables from the row
    variables = row_to_variables(row)
    variables["campaign"] = args.campaign

    # Derive first_name + opening_line so prompts can use these placeholders
    full_name = variables.get("name", "")
    first_name = extract_first_name(full_name)
    variables["first_name"] = first_name
    variables["opening_line"] = make_opening_line(args.campaign, first_name)

    to_number = row["phone"]

    client = Retell(api_key=RETELL_API_KEY)

    try:
        client.llm.update(
            llm_id=RETELL_LLM_ID,
            general_prompt=prompt_template,
        )
        print(f"✓ Updated Retell LLM with {args.campaign} prompt")
    except Exception as e:
        print(f"❌ Failed to update Retell LLM: {e}")
        sys.exit(1)

    try:
        call = client.call.create_phone_call(
            from_number=RETELL_FROM_NUMBER,
            to_number=to_number,
            override_agent_id=RETELL_AGENT_ID,
            retell_llm_dynamic_variables=variables,
            metadata={
                "campaign": args.campaign,
                "customer_id": args.customer_id,
                "customer_name": full_name,
            },
        )
        print(f"✓ Call initiated")
        print(f"  Call ID       : {call.call_id}")
        print(f"  Customer      : {full_name}")
        print(f"  First name    : {first_name}")
        print(f"  Opening line  : {variables['opening_line']}")
        print(f"  Phone         : {to_number}")
        print(f"  Campaign      : {args.campaign}")
        print(f"  Variables sent: {len(variables)}")
    except Exception as e:
        print(f"❌ Failed to create call: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()