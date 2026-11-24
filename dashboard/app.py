"""
Marissa — FE Credit AI Calling Dashboard v3
Campaign-first view · "Call All" button · Date filtering.
"""

import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

# ============================================================
# CONFIG
# ============================================================
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# External data folder
DATA_DIR = Path(os.getenv(
    "CAMPAIGN_DATA_DIR",
    r"C:\Users\Prolay Bhattacharyya\OneDrive\Documents\Fe Credit data"
))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

CAMPAIGNS = {
    "cross_sell":        {"label": "Cross-Sell",         "icon": "💰",
                          "desc": "Pitch additional products to active customers"},
    "pre_approved":      {"label": "Pre-Approved Loan",  "icon": "✅",
                          "desc": "Offer pre-approved loan to qualifying customers"},
    "reactivation":      {"label": "Reactivation",       "icon": "🔄",
                          "desc": "Re-engage dormant customers"},
    "winback":           {"label": "Winback",            "icon": "🎁",
                          "desc": "Win back customers who left"},
    "payment_reminder":  {"label": "Payment Reminder",   "icon": "💳",
                          "desc": "Reminder for upcoming EMI payments"},
    "early_collections": {"label": "Early Collections",  "icon": "⚠️",
                          "desc": "Follow up on missed EMIs within 30 days"},
    "onboarding":        {"label": "Onboarding",         "icon": "🎓",
                          "desc": "Welcome and onboard new customers"},
    "emi_conversion":    {"label": "EMI Conversion",     "icon": "📊",
                          "desc": "Convert outstanding balance to EMI plan"},
    "renewal":           {"label": "Renewal",            "icon": "🔁",
                          "desc": "Renew expiring loan or credit line"},
    "pre_closure":       {"label": "Pre-Closure",        "icon": "🏁",
                          "desc": "Assistance for maturing loans"},
    "lead_followup":     {"label": "Lead Follow-up",     "icon": "📞",
                          "desc": "Follow up with warm leads from marketing"},
    "nps_feedback":      {"label": "NPS Feedback",       "icon": "⭐",
                          "desc": "Collect NPS feedback from recent customers"},
}

st.set_page_config(page_title="Marissa", page_icon="🎙️", layout="wide")


# ============================================================
# DATA
# ============================================================
@st.cache_resource
def get_client():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    return create_client(SUPABASE_URL, SUPABASE_KEY)


@st.cache_data(ttl=10)
def fetch_calls():
    c = get_client()
    if c is None:
        return pd.DataFrame()
    try:
        r = c.table("call_results").select("*").order("created_at", desc=True).execute()
        if not r.data:
            return pd.DataFrame()
        df = pd.DataFrame(r.data)
        df["created_at"] = pd.to_datetime(df["created_at"])
        df["duration_sec"] = (df["duration_ms"].fillna(0) / 1000).astype(int)
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data
def load_campaign_customers(campaign):
    """Load the campaign-specific CSV (cross_sell.csv, pre_approved.csv, etc.)"""
    csv_path = DATA_DIR / f"{campaign}.csv"
    if not csv_path.exists():
        return pd.DataFrame()
    return pd.read_csv(csv_path, dtype=str)


@st.cache_data
def load_all_campaigns():
    """Load every campaign's customers tagged with a campaign column.
       Used only on the landing page for overall count."""
    frames = []
    for camp in ["cross_sell", "pre_approved", "reactivation", "winback",
                 "payment_reminder", "early_collections", "onboarding",
                 "emi_conversion", "renewal", "pre_closure",
                 "lead_followup", "nps_feedback"]:
        df = load_campaign_customers(camp)
        if not df.empty:
            df["campaign"] = camp
            frames.append(df[["customer_id", "name", "phone", "city", "campaign"]])
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


# ============================================================
# STATE
# ============================================================
if "selected_campaign" not in st.session_state:
    st.session_state.selected_campaign = None

customers_df = load_customers()
calls_df = fetch_calls()


# ============================================================
# HEADER
# ============================================================
if st.session_state.selected_campaign:
    col_back, col_title, col_refresh = st.columns([1, 5, 1])
    with col_back:
        if st.button("← Back to campaigns", use_container_width=True):
            st.session_state.selected_campaign = None
            st.rerun()
    with col_title:
        c = CAMPAIGNS[st.session_state.selected_campaign]
        st.markdown(f"## {c['icon']} {c['label']}")
        st.caption(c["desc"])
    with col_refresh:
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
else:
    col_title, col_refresh = st.columns([6, 1])
    with col_title:
        st.title("🎙️ Marissa")
        st.caption("FE Credit AI Calling · Pick a campaign to view customers and fire calls")
    with col_refresh:
        st.write("")
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

st.divider()


# ============================================================
# LANDING: CAMPAIGN GRID
# ============================================================
if st.session_state.selected_campaign is None:
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("👥 Total Customers", f"{len(customers_df):,}")
    k2.metric("📞 Total Calls", f"{len(calls_df):,}")
    hot = len(calls_df[calls_df["interest_level"].isin(["high", "highly_interested"])]) if len(calls_df) else 0
    k3.metric("🔥 Hot Leads", f"{hot:,}")
    esc = len(calls_df[calls_df["escalation_needed"] == True]) if len(calls_df) else 0
    k4.metric("⚠️ Escalations", f"{esc:,}")

    st.markdown("### 📂 Campaigns")
    st.caption("Click any campaign to see its customers and fire calls")

    campaign_codes = list(CAMPAIGNS.keys())
    for row in range(0, len(campaign_codes), 4):
        cols = st.columns(4, gap="small")
        for i, code in enumerate(campaign_codes[row:row + 4]):
            info = CAMPAIGNS[code]
            cust_count = len(customers_df[customers_df["campaign"] == code]) if not customers_df.empty else 0
            call_count = len(calls_df[calls_df["campaign"] == code]) if not calls_df.empty else 0

            with cols[i]:
                with st.container(border=True):
                    st.markdown(
                        f"<div style='font-size:36px;line-height:1'>{info['icon']}</div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"**{info['label']}**")
                    st.caption(info["desc"])
                    st.markdown(f"👥 **{cust_count:,}** customers  ·  📞 **{call_count}** called")
                    if st.button("Open →", key=f"btn_{code}", use_container_width=True):
                        st.session_state.selected_campaign = code
                        st.rerun()


# ============================================================
# CAMPAIGN DETAIL VIEW
# ============================================================
else:
    code = st.session_state.selected_campaign
    info = CAMPAIGNS[code]

    camp_customers = (
        customers_df[customers_df["campaign"] == code].copy()
        if not customers_df.empty else pd.DataFrame()
    )
    camp_calls = (
        calls_df[calls_df["campaign"] == code].copy()
        if not calls_df.empty else pd.DataFrame()
    )

    # ---- SIDEBAR: Date filter (for calls history) ----
    st.sidebar.markdown(f"### {info['icon']} {info['label']}")
    st.sidebar.markdown("**📅 Date filter (for calls)**")

    if not camp_calls.empty:
        min_date = camp_calls["created_at"].min().date()
        max_date = camp_calls["created_at"].max().date()
    else:
        today_d = datetime.now().date()
        min_date = today_d
        max_date = today_d

    date_preset = st.sidebar.radio(
        "Show calls from",
        options=["All time", "Today", "Last 7 days", "Last 30 days", "Custom"],
        index=0,
        key="date_preset",
    )

    today_d = datetime.now().date()
    if date_preset == "Today":
        date_range = (today_d, today_d)
    elif date_preset == "Last 7 days":
        date_range = (today_d - timedelta(days=7), today_d)
    elif date_preset == "Last 30 days":
        date_range = (today_d - timedelta(days=30), today_d)
    elif date_preset == "Custom":
        date_range = st.sidebar.date_input(
            "Pick date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=today_d,
        )
        if not isinstance(date_range, tuple):
            date_range = (date_range, date_range)
    else:
        date_range = None  # All time

    # Apply date filter to calls
    if date_range is not None and not camp_calls.empty:
        camp_calls_in_range = camp_calls[
            (camp_calls["created_at"].dt.date >= date_range[0])
            & (camp_calls["created_at"].dt.date <= date_range[1])
        ].copy()
    else:
        camp_calls_in_range = camp_calls.copy()

    # ---- Campaign KPIs (reflect date filter) ----
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("👥 Customers", f"{len(camp_customers):,}")
    if date_range is None:
        date_help = "all time"
    elif date_range[0] == date_range[1]:
        date_help = str(date_range[0])
    else:
        date_help = f"{date_range[0]} → {date_range[1]}"
    k2.metric("📞 Called", f"{len(camp_calls_in_range):,}", help=f"Within: {date_help}")
    hot = len(camp_calls_in_range[camp_calls_in_range["interest_level"].isin(["high", "highly_interested"])]) if len(camp_calls_in_range) else 0
    k3.metric("🔥 Hot leads", f"{hot:,}")
    esc = len(camp_calls_in_range[camp_calls_in_range["escalation_needed"] == True]) if len(camp_calls_in_range) else 0
    k4.metric("⚠️ Escalations", f"{esc:,}")

    # ---- CALL-EVERYONE SHORTCUT ----
    st.markdown("### ⚡ Fire calls for this campaign")

    uncalled = (
        camp_customers[~camp_customers["customer_id"].isin(
            set(camp_calls["customer_id"].tolist()) if not camp_calls.empty else set()
        )]
        if not camp_customers.empty else pd.DataFrame()
    )

    ca1, ca2, ca3 = st.columns([2, 2, 2])
    with ca1:
        call_all = st.button(
            f"📞 Call ALL {len(camp_customers):,} customers",
            type="primary",
            disabled=camp_customers.empty,
            use_container_width=True,
            key="call_all_camp",
        )
    with ca2:
        call_pending = st.button(
            f"📞 Call only {len(uncalled):,} pending",
            disabled=uncalled.empty,
            use_container_width=True,
            key="call_pending_camp",
        )
    with ca3:
        st.caption("Or scroll below to pick specific customers")

    def _fire(ids, label):
        if not ids:
            st.warning("No customers to call.")
            return
        prog = st.progress(0, text=f"Firing {label}…")
        log_area = st.empty()
        logs = []
        for i, cid in enumerate(ids):
            logs.append(f"⏳ [{i + 1}/{len(ids)}] `{cid}` — would call via `scripts.trigger_call {cid}`")
            log_area.markdown("\n\n".join(logs))
            prog.progress((i + 1) / len(ids))
        st.success(f"✅ Simulated firing {len(ids)} {info['label']} calls.")
        st.info("Live calling activates after webhook deploys. One flag flip in the code.")

    if call_all:
        _fire(camp_customers["customer_id"].tolist(), f"ALL {info['label']}")
    if call_pending:
        _fire(uncalled["customer_id"].tolist(), f"pending {info['label']}")

    st.divider()

    # ---- CUSTOMER TABLE + FILTERS ----
    if camp_customers.empty:
        st.info(f"No customers assigned to {info['label']} yet.")
    else:
        # Sidebar customer filters
        st.sidebar.divider()
        st.sidebar.markdown("**🎛️ Customer filters**")

        cities = sorted(camp_customers["city"].dropna().unique())
        sel_cities = st.sidebar.multiselect("City", cities, default=cities)

        age_min_val, age_max_val = int(camp_customers["age"].min()), int(camp_customers["age"].max())
        if age_min_val == age_max_val:
            age_range = (age_min_val, age_max_val)
            st.sidebar.caption(f"Age: {age_min_val} (all same)")
        else:
            age_range = st.sidebar.slider("Age", age_min_val, age_max_val, (age_min_val, age_max_val))

        income_min_val = int(camp_customers["monthly_income_vnd"].min())
        income_max_val = int(camp_customers["monthly_income_vnd"].max())
        if income_min_val == income_max_val:
            income_range = (income_min_val, income_max_val)
        else:
            step = max(1, (income_max_val - income_min_val) // 100)
            income_range = st.sidebar.slider(
                "Monthly income (₫)",
                income_min_val, income_max_val, (income_min_val, income_max_val), step=step,
            )

        products = sorted(camp_customers["product_fit"].dropna().unique())
        sel_products = st.sidebar.multiselect("Product fit", products, default=products)

        prior_loans = sorted(camp_customers["prior_loans"].dropna().unique())
        sel_prior = st.sidebar.multiselect("Prior loans", prior_loans, default=prior_loans)

        st.sidebar.divider()
        only_pending = st.sidebar.checkbox("⏳ Only show pending (not yet called)")

        # Apply filters
        f = camp_customers[
            camp_customers["city"].isin(sel_cities)
            & camp_customers["age"].between(age_range[0], age_range[1])
            & camp_customers["monthly_income_vnd"].between(income_range[0], income_range[1])
            & camp_customers["product_fit"].isin(sel_products)
            & camp_customers["prior_loans"].isin(sel_prior)
        ].copy()

        called_ids = set(camp_calls["customer_id"].tolist()) if not camp_calls.empty else set()
        f["Status"] = f["customer_id"].apply(
            lambda x: "📞 Called" if x in called_ids else "⏳ Pending"
        )
        if only_pending:
            f = f[f["Status"] == "⏳ Pending"]

        st.markdown(f"### 👥 Customers ({len(f):,} of {len(camp_customers):,} total)")

        f.insert(0, "Select", False)
        display = f[["Select", "customer_id", "name", "phone", "age", "city",
                     "occupation", "monthly_income_vnd", "product_fit",
                     "preferred_time", "Status"]].rename(columns={
            "customer_id": "ID", "name": "Name", "phone": "Phone", "age": "Age",
            "city": "City", "occupation": "Occupation",
            "monthly_income_vnd": "Income", "product_fit": "Product",
            "preferred_time": "Best Time",
        })

        edited = st.data_editor(
            display,
            use_container_width=True, hide_index=True,
            disabled=["ID", "Name", "Phone", "Age", "City", "Occupation",
                      "Income", "Product", "Best Time", "Status"],
            height=440,
        )

        sel = edited[edited["Select"]]
        n = len(sel)
        st.markdown(f"**{n}** customers selected")

        col_fire, col_dry, _ = st.columns([2, 1, 2])
        with col_fire:
            fire_sel = st.button(
                f"📞 Fire selected ({n})",
                type="primary", disabled=n == 0, use_container_width=True,
                key="fire_selected",
            )
        with col_dry:
            dry = st.button("🧪 Dry Run", disabled=n == 0, use_container_width=True, key="dry_run")

        if fire_sel:
            _fire(sel["ID"].tolist(), f"selected {info['label']}")

        if dry:
            st.success(f"Dry run: {n} customers would be called.")
            st.dataframe(sel[["ID", "Name", "Phone", "City"]],
                         use_container_width=True, hide_index=True)

    # ---- RECENT CALLS (respects the date filter) ----
    if not camp_calls_in_range.empty:
        st.divider()
        st.markdown(f"### 📜 Recent calls — {info['label']}  ({len(camp_calls_in_range)} in range)")

        merge_src = (
            customers_df[["customer_id", "name"]]
            if not customers_df.empty
            else pd.DataFrame(columns=["customer_id", "name"])
        )
        dd = camp_calls_in_range.merge(merge_src, on="customer_id", how="left")
        dd["Time"] = dd["created_at"].dt.strftime("%Y-%m-%d %H:%M")
        dd["Duration"] = dd["duration_sec"].apply(
            lambda s: f"{s // 60}:{s % 60:02d}" if s > 0 else "–"
        )

        st.dataframe(
            dd[["Time", "name", "disposition", "interest_level",
                "sentiment", "Duration"]].rename(columns={
                "name": "Customer", "disposition": "Disposition",
                "interest_level": "Interest", "sentiment": "Sentiment",
            }),
            use_container_width=True, hide_index=True, height=320,
        )


st.divider()
st.caption("Marissa Dashboard v3.0 · Campaign-first · Date filtering · Call-all support")