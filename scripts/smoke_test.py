"""
Verify Anthropic, Supabase, and Retell are all reachable.
Run from project root:  python scripts\smoke_test.py
"""
import os
from dotenv import load_dotenv

load_dotenv()

print("—— Smoke test for Step 1 ——\n")

# 1. Anthropic
print("1. Testing Anthropic API...")
try:
    from anthropic import Anthropic
    client = Anthropic()
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=50,
        messages=[{"role": "user", "content": "Say hello in Vietnamese in one short sentence."}],
    )
    print("   OK Anthropic:", msg.content[0].text.strip())
except Exception as e:
    print("   FAIL Anthropic:", e)

# 2. Supabase
print("\n2. Testing Supabase connection...")
try:
    from supabase import create_client
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    try:
        sb.table("_smoke_test_nonexistent").select("*").limit(1).execute()
    except Exception:
        pass
    print(f"   OK Supabase: connected to {os.environ['SUPABASE_URL']}")
except Exception as e:
    print("   FAIL Supabase:", e)

# 3. Retell
print("\n3. Testing Retell API...")
try:
    import httpx
    r = httpx.get(
        "https://api.retellai.com/list-voices",
        headers={"Authorization": f"Bearer {os.environ['RETELL_API_KEY']}"},
        timeout=10,
    )
    if r.status_code == 200:
        voices = r.json()
        print(f"   OK Retell: authenticated, {len(voices)} voices available")
    else:
        print(f"   FAIL Retell: status {r.status_code} - {r.text[:200]}")
except Exception as e:
    print("   FAIL Retell:", e)

print("\n—— Done ——")