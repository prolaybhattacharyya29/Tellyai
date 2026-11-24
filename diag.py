import streamlit as st

st.title("🔬 Dashboard Diagnostic")
st.write("Running checks one by one...")

# Check 1: imports
try:
    import pandas as pd
    import altair as alt
    from pathlib import Path
    from dotenv import load_dotenv
    from supabase import create_client
    import os
    st.success("✅ Step 1: All imports OK")
except Exception as e:
    st.error(f"❌ Step 1 failed: {e}")
    st.stop()

# Check 2: .env loading
try:
    PROJECT_ROOT = Path(__file__).parent
    load_dotenv(PROJECT_ROOT / ".env")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if url and key:
        st.success(f"✅ Step 2: .env loaded. URL={url[:40]}..., KEY present")
    else:
        st.error(f"❌ Step 2: Missing env vars. URL present: {bool(url)}, KEY present: {bool(key)}")
        st.stop()
except Exception as e:
    st.error(f"❌ Step 2 failed: {e}")
    st.stop()

# Check 3: create Supabase client
try:
    client = create_client(url, key)
    st.success("✅ Step 3: Supabase client created")
except Exception as e:
    st.error(f"❌ Step 3 failed: {e}")
    st.stop()

# Check 4: query call_results
try:
    with st.spinner("Querying Supabase..."):
        result = client.table("call_results").select("*").execute()
    st.success(f"✅ Step 4: Query OK. Rows returned: {len(result.data)}")
except Exception as e:
    st.error(f"❌ Step 4 failed: {e}")
    st.stop()

# Check 5: load CSV
try:
    csv_path = PROJECT_ROOT / "data" / "customers.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path, dtype={"phone": str})
        st.success(f"✅ Step 5: CSV loaded. Customers: {len(df)}")
    else:
        st.warning(f"⚠️ Step 5: CSV not found at {csv_path}")
except Exception as e:
    st.error(f"❌ Step 5 failed: {e}")

st.balloons()
st.success("🎉 ALL CHECKS PASSED — the dashboard should work")