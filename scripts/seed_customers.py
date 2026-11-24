"""
Seed customer data from 12 campaign CSV files in data/csvs/ into Supabase 'customers' table.
"""
import os
import csv
import glob
import math
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

CSV_DIR = Path("data/csvs")

CORE_FIELDS = {
    "customer_id",
    "name",
    "phone",
    "age",
    "gender",
    "city",
    "occupation",
    "monthly_income_vnd",
    "preferred_time",
    "preferred_language",
    "last_contact_date",
    "last_contact_outcome",
}

def clean_val(val):
    if val is None or val == "" or val.strip().lower() in ["nan", "null", "none"]:
        return None
    return val.strip()

def clean_num(val, cast_type=float):
    cleaned = clean_val(val)
    if cleaned is None:
        return None
    try:
        res = cast_type(cleaned)
        if isinstance(res, float) and (math.isnan(res) or math.isinf(res)):
            return None
        return res
    except (ValueError, TypeError):
        return None

def parse_csv_file(filepath: Path):
    campaign_name = filepath.stem  # e.g. "cross_sell"
    records = []

    with open(filepath, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            customer_id = clean_val(row.get("customer_id"))
            name = clean_val(row.get("name"))
            phone = clean_val(row.get("phone"))
            if not customer_id or not name:
                continue

            age = clean_num(row.get("age"), int)
            gender = clean_val(row.get("gender"))
            city = clean_val(row.get("city"))
            occupation = clean_val(row.get("occupation"))
            monthly_income = clean_num(row.get("monthly_income_vnd"), float)
            preferred_time = clean_val(row.get("preferred_time"))
            preferred_lang = clean_val(row.get("preferred_language")) or "vietnamese"
            last_contact_date = clean_val(row.get("last_contact_date"))
            last_contact_outcome = clean_val(row.get("last_contact_outcome"))

            # Build campaign_data with all remaining campaign-specific columns
            campaign_data = {}
            for k, v in row.items():
                if k not in CORE_FIELDS and k != "campaign":
                    v_clean = clean_val(v)
                    if v_clean is not None:
                        # Try parsing numbers into campaign_data where appropriate
                        if v_clean.isdigit():
                            campaign_data[k] = int(v_clean)
                        else:
                            try:
                                campaign_data[k] = float(v_clean)
                            except ValueError:
                                campaign_data[k] = v_clean

            records.append({
                "customer_id": customer_id,
                "campaign": campaign_name,
                "name": name,
                "phone": phone,
                "age": age,
                "gender": gender,
                "city": city,
                "occupation": occupation,
                "monthly_income_vnd": monthly_income,
                "preferred_time": preferred_time,
                "preferred_language": preferred_lang,
                "last_contact_date": last_contact_date,
                "last_contact_outcome": last_contact_outcome,
                "campaign_data": campaign_data,
            })
    return records


def seed_all_customers(batch_size: int = 500):
    files = sorted(list(CSV_DIR.glob("*.csv")))
    if not files:
        print(f"No CSV files found in {CSV_DIR.resolve()}")
        return

    print(f"Found {len(files)} campaign CSV files in {CSV_DIR}:")
    for f in files:
        print(f" - {f.name}")

    total_inserted = 0

    for f in files:
        records = parse_csv_file(f)
        campaign_name = f.stem
        print(f"\nProcessing '{campaign_name}': {len(records)} records...")

        # Insert in chunks of batch_size
        for i in range(0, len(records), batch_size):
            chunk = records[i:i + batch_size]
            try:
                res = sb.table("customers").upsert(chunk, on_conflict="customer_id,campaign").execute()
                total_inserted += len(chunk)
                print(f"  Inserted chunk {i // batch_size + 1} ({len(chunk)} rows) -> Total: {total_inserted}")
            except Exception as e:
                print(f"  Error inserting chunk into 'customers': {e}")
                print("\n[NOTE] If table 'customers' does not exist yet, please run:")
                print("       scripts/create_customers_table.sql in your Supabase SQL Editor.")
                return

    print(f"\nSuccessfully seeded all {total_inserted} customer records!")


if __name__ == "__main__":
    seed_all_customers()
