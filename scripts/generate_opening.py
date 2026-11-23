"""
Generate a personalized opening line for a single customer using Claude.
Caches results to cache/openings/<customer_id>.txt so repeat runs are free.

Usage:
    python scripts/generate_opening.py CUST-10000
    python scripts/generate_opening.py                 # generates for all
"""
import os
import sys
import pandas as pd
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()
SYSTEM_PROMPT = Path("prompts/opening_system.md").read_text(encoding="utf-8")
CACHE_DIR = Path("cache/openings")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

MODEL = "claude-haiku-4-5"  # fast + cheap, perfect for short greetings


def profile_to_text(row: dict) -> str:
    """Format one CSV row as a short profile string."""
    return ". ".join(f"{k}: {v}" for k, v in row.items() if v != "" and pd.notna(v)) + "."


def generate_opening(customer: dict) -> str:
    """Return a cached opening if present, else call Claude and cache."""
    customer_id = customer["customer_id"]
    cache_path = CACHE_DIR / f"{customer_id}.txt"

    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8").strip()

    profile = profile_to_text(customer)
    msg = client.messages.create(
        model=MODEL,
        max_tokens=100,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Customer profile:\n{profile}"}],
    )
    opening = msg.content[0].text.strip().strip('"').strip("'")
    cache_path.write_text(opening, encoding="utf-8")
    return opening


def main():
    df = pd.read_csv("data/customers.csv")

    if len(sys.argv) > 1:
        # single customer by id
        cust_id = sys.argv[1]
        row = df[df["customer_id"] == cust_id]
        if row.empty:
            print(f"Customer {cust_id} not found")
            sys.exit(1)
        customers = row.to_dict(orient="records")
    else:
        # all customers
        customers = df.to_dict(orient="records")

    for c in customers:
        opening = generate_opening(c)
        name = c.get("name") or c.get("full_name") or "(no name)"
        print(f"{c['customer_id']}  {name:<30}  {opening}")


if __name__ == "__main__":
    main()