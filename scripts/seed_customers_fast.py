import os
import csv
import json
import math
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

CONN_STR = "postgresql://postgres.mkslmzogliyfckkojgyt:xtage%402026kk@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres"
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
    campaign_name = filepath.stem
    rows = []

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

            campaign_data = {}
            for k, v in row.items():
                if k not in CORE_FIELDS and k != "campaign":
                    v_clean = clean_val(v)
                    if v_clean is not None:
                        if v_clean.isdigit():
                            campaign_data[k] = int(v_clean)
                        else:
                            try:
                                campaign_data[k] = float(v_clean)
                            except ValueError:
                                campaign_data[k] = v_clean

            rows.append((
                customer_id,
                campaign_name,
                name,
                phone,
                age,
                gender,
                city,
                occupation,
                monthly_income,
                preferred_time,
                preferred_lang,
                last_contact_date,
                last_contact_outcome,
                json.dumps(campaign_data)
            ))
    return rows


def seed_all():
    files = sorted(list(CSV_DIR.glob("*.csv")))
    print(f"Connecting to database to seed from {len(files)} CSV files...")
    conn = psycopg2.connect(CONN_STR)
    conn.autocommit = True
    cursor = conn.cursor()

    insert_query = """
    INSERT INTO public.customers (
        customer_id, campaign, name, phone, age, gender, city, occupation,
        monthly_income_vnd, preferred_time, preferred_language,
        last_contact_date, last_contact_outcome, campaign_data
    ) VALUES %s
    ON CONFLICT (customer_id, campaign) DO UPDATE SET
        name = EXCLUDED.name,
        phone = EXCLUDED.phone,
        age = EXCLUDED.age,
        gender = EXCLUDED.gender,
        city = EXCLUDED.city,
        occupation = EXCLUDED.occupation,
        monthly_income_vnd = EXCLUDED.monthly_income_vnd,
        preferred_time = EXCLUDED.preferred_time,
        preferred_language = EXCLUDED.preferred_language,
        last_contact_date = EXCLUDED.last_contact_date,
        last_contact_outcome = EXCLUDED.last_contact_outcome,
        campaign_data = EXCLUDED.campaign_data,
        updated_at = NOW();
    """

    total = 0
    for f in files:
        rows = parse_csv_file(f)
        campaign_name = f.stem
        execute_values(cursor, insert_query, rows, template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)", page_size=1000)
        total += len(rows)
        print(f"✓ Seeded {len(rows)} records for campaign '{campaign_name}' (Total: {total})")

    cursor.close()
    conn.close()
    print(f"\n🎉 Successfully seeded all {total} customer records across 12 campaigns!")

if __name__ == "__main__":
    seed_all()
