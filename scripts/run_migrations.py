import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn_pooler = "postgresql://postgres.mkslmzogliyfckkojgyt:xtage%402026kk@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres"
conn_direct = "postgresql://postgres:xtage%402026kk@db.mkslmzogliyfckkojgyt.supabase.co:5432/postgres"

sql_files = [
    "scripts/full_schema.sql",
]

def run():
    conn = None
    try:
        print("Connecting via pooler...")
        conn = psycopg2.connect(conn_pooler)
        print("Connected via pooler successfully!")
    except Exception as e:
        print(f"Pooler failed: {e}. Trying direct connection...")
        try:
            conn = psycopg2.connect(conn_direct)
            print("Connected via direct connection successfully!")
        except Exception as e2:
            print(f"Direct connection also failed: {e2}")
            return

    conn.autocommit = True
    cursor = conn.cursor()

    # Also create call_results if not present
    call_results_sql = """
    CREATE TABLE IF NOT EXISTS public.call_results (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        call_id TEXT UNIQUE NOT NULL,
        customer_id TEXT,
        campaign TEXT NOT NULL,
        phone_number TEXT,
        duration_ms INT,
        end_reason TEXT,
        transcript TEXT,
        disposition TEXT,
        interest_level TEXT,
        customer_decision TEXT,
        escalation_needed BOOLEAN DEFAULT FALSE,
        escalation_reason TEXT,
        key_quotes JSONB DEFAULT '[]'::jsonb,
        objections_raised JSONB DEFAULT '[]'::jsonb,
        next_action TEXT,
        follow_up_within_hours INT,
        sentiment TEXT,
        notes_for_marketing TEXT,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_call_results_campaign ON public.call_results(campaign);
    CREATE INDEX IF NOT EXISTS idx_call_results_customer_id ON public.call_results(customer_id);
    """
    cursor.execute(call_results_sql)
    print("Ensured call_results table exists.")

    for sql_file in sql_files:
        with open(sql_file, "r") as f:
            sql = f.read()
            print(f"Executing {sql_file}...")
            cursor.execute(sql)
            print(f"Successfully executed {sql_file}!")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    run()
