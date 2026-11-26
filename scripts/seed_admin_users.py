"""
Seed default demo admin users into Supabase admin_users table.
Run: uv run python scripts/seed_admin_users.py
"""
import os
from dotenv import load_dotenv
from supabase import create_client
from app.db import hash_password

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_KEY must be set in .env")
    exit(1)

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

DEMO_ACCOUNTS = [
    {
        "username": "admin",
        "email": "admin@xtagelabs.com",
        "password_hash": hash_password("xtage@2026kk"),
        "full_name": "admin",
        "role": "superadmin",
        "is_active": True,
    },
    {
        "username": "fe_admin",
        "email": "admin@fecredit.com",
        "password_hash": hash_password("admin123"),
        "full_name": "Platform Administrator",
        "role": "superadmin",
        "is_active": True,
    },
    {
        "username": "demo",
        "email": "demo@fecredit.com",
        "password_hash": hash_password("admin123"),
        "full_name": "Demo Presenter",
        "role": "admin",
        "is_active": True,
    },
]

print("—— Seeding Admin Users into Supabase ——\n")

try:
    for acc in DEMO_ACCOUNTS:
        res = sb.table("admin_users").upsert(acc, on_conflict="username").execute()
        print(f"  OK: User '{acc['username']}' ({acc['email']}) seeded successfully.")
    print("\nAll demo admin users are active in the database!")
except Exception as e:
    err_str = str(e)
    if "PGRST205" in err_str or "Could not find the table" in err_str:
        print("Note: The 'admin_users' table has not been created in Supabase yet.")
        print("\nPlease run the SQL migration in your Supabase SQL editor:")
        print(f"👉 Link: https://supabase.com/dashboard/project/lagejwzhelvqlyqhsvig/sql")
        print("👉 File: scripts/create_users_table.sql")
        print("\n(Meanwhile, the application fallback in app/main.py will still let you log in with these demo credentials!)")
    else:
        print(f"Failed to seed admin users: {e}")
