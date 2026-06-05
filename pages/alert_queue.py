import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from utils import load_data, build_alert_queue, get_decisions, save_decision, init_db, DB_PATH, VELOCITY_THRESHOLD

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FraudGuard — Alert Queue",
    page_icon="🚨",
    layout="wide",
)

with open("css/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🛡️ FraudGuard")
    st.caption("Fraud Detection Platform")
    st.divider()
    st.page_link("account_lookup.py",        label="🔍 Account Lookup")
    st.page_link("pages/alert_queue.py",     label="🚨 Alert Queue")
    st.page_link("pages/2_Agent_Chat.py",    label="🤖 Agent Chat")

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data
def cached_load():
    return load_data()

@st.cache_data
def cached_queue(txns, accounts):
    return build_alert_queue(txns, accounts)

txns, accounts = cached_load()
queue          = cached_queue(txns, accounts)
decisions      = get_decisions()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="fd-header">
  <div class="fd-icon">🚨</div>
  <div>
    <div class="fd-title">Alert Queue</div>
    <div class="fd-sub">Ranked by risk score · Transaction Velocity</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Summary metrics ───────────────────────────────────────────────────────────
high_ct    = len(queue[queue["risk_level"] == "High"])
medium_ct  = len(queue[queue["risk_level"] == "Medium"])
blocked_ct = sum(1 for d in decisions.values() if d["decision"] == "blocked")
cleared_ct = sum(1 for d in decisions.values() if d["decision"] == "cleared")
pending_ct = len(queue) - len(decisions)

st.markdown(
    "<div class='metric-row'>"
    "<div class='metric-box'><div class='label'>🔴 High risk</div><div class='value red'>" + str(high_ct) + "</div></div>"
    "<div class='metric-box'><div class='label'>🟡 Medium risk</div><div class='value'>" + str(medium_ct) + "</div></div>"
    "<div class='metric-box'><div class='label'>⏳ Pending review</div><div class='value'>" + str(pending_ct) + "</div></div>"
    "<div class='metric-box'><div class='label'>🔒 Blocked</div><div class='value red'>" + str(blocked_ct) + "</div></div>"
    "<div class='metric-box'><div class='label'>✅ Cleared</div><div class='value green'>" + str(cleared_ct) + "</div></div>"
    "</div>",
    unsafe_allow_html=True
)

# ── Filters ───────────────────────────────────────────────────────────────────
col_f1, col_f2, col_f3 = st.columns([2, 2, 2])
with col_f1:
    risk_filter = st.selectbox("Risk level", ["All", "High", "Medium"], label_visibility="collapsed")
with col_f2:
    status_filter = st.selectbox(
        "Status", ["All", "Pending", "Blocked", "Cleared", "Escalated", "Monitoring"],
        label_visibility="collapsed"
    )
with col_f3:
    analyst_name = st.text_input("Your name", placeholder="Analyst name for decisions", label_visibility="collapsed")

# ── Apply filters ─────────────────────────────────────────────────────────────
filtered = queue.copy()
if risk_filter != "All":
    filtered = filtered[filtered["risk_level"] == risk_filter]
if status_filter != "All":
    if status_filter == "Pending":
        filtered = filtered[~filtered["account_id"].isin(decisions.keys())]
    else:
        decided_ids = [aid for aid, d in decisions.items() if d["decision"] == status_filter.lower()]
        filtered = filtered[filtered["account_id"].isin(decided_ids)]

st.markdown(
    "<div class='sec-label'>" + str(len(filtered)) + " accounts — sorted by risk score</div>",
    unsafe_allow_html=True
)

if filtered.empty:
    st.info("No accounts match the current filters.")
    st.stop()

# ── Helper: build card HTML using string concatenation only (no f-strings) ────
def build_card(row, decision, status, decisions):
    acc_id    = row["account_id"]
    risk      = row["risk_level"]
    border    = "#6e2929" if risk == "High" else "#4d3608"
    bg        = "#1c0d0d" if risk == "High" else "#1c1300"
    risk_icon = "🔴" if risk == "High" else "🟡"
    score_color = "#f85149" if risk == "High" else "#d29922"

    status_badge_map = {
        "Pending":    '<span class="badge b-flag">PENDING</span>',
        "Blocked":    '<span class="badge b-block">BLOCKED</span>',
        "Cleared":    '<span class="badge b-ok">CLEARED</span>',
        "Escalated":  '<span class="badge b-flag">ESCALATED</span>',
        "Monitoring": '<span class="badge b-info">MONITORING</span>',
    }
    status_badge  = status_badge_map.get(status, "<span class='badge'>" + status + "</span>")
    dormant_badge = '<span class="badge b-flag">DORMANT</span>' if row["is_dormant"] else ""
    kyc_badge     = '<span class="badge b-block">KYC ❌</span>' if not row["kyc_verified"] else ""

    peak_str = "—"
    if pd.notna(row.get("peak_start")) and row["peak_start"]:
        try:
            ps = pd.to_datetime(row["peak_start"])
            pe = pd.to_datetime(row["peak_end"])
            peak_str = ps.strftime("%m/%d %H:%M") + " – " + pe.strftime("%H:%M")
        except Exception:
            pass

    fraud_label = str(row["fraud_types"]) if str(row["fraud_types"]) != "—" else "unknown pattern"
    total_fmt   = "${:,.0f}".format(row["total_amount"])

    decision_html = ""
    if decision:
        decided_at    = decision["decided_at"][:16].replace("T", " ")
        notes_str     = " · " + decision["notes"] if decision["notes"] else ""
        decision_html = (
            "<div style='font-size:11px;color:#7d8590;margin-bottom:8px;'>"
            "Decided by <strong>" + str(decision["analyst"]) + "</strong>"
            " · " + decided_at + notes_str +
            "</div>"
        )

    card = (
        "<div style='background:" + bg + ";border:1px solid " + border + ";border-radius:10px;padding:16px 20px;margin-bottom:12px;'>"

          "<div style='display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;'>"

            "<div style='display:flex;align-items:center;gap:8px;flex-wrap:wrap;'>"
              "<span style='font-size:15px;font-weight:600;color:#e6edf3;'>" + risk_icon + " " + acc_id + "</span>"
              "<span style='font-size:12px;color:#7d8590;'>" + str(row["customer"]) + "</span>"
              + dormant_badge + kyc_badge +
            "</div>"

            "<div style='display:flex;align-items:center;gap:8px;'>"
              "<span style='font-size:11px;color:#7d8590;'>Risk score</span>"
              "<span style='font-size:18px;font-weight:600;color:" + score_color + ";'>" + str(row["risk_score"]) + "</span>"
              + status_badge +
            "</div>"

          "</div>"

          "<div style='display:flex;gap:20px;font-size:12px;color:#8b949e;flex-wrap:wrap;'>"
            "<span>⚡ <strong style='color:#e6edf3;'>" + str(row["max_velocity"]) + "</strong> txns/5min</span>"
            "<span>🌍 <strong style='color:#e6edf3;'>" + str(row["geo_flags"]) + "</strong> geo flags</span>"
            "<span>💰 <strong style='color:#e6edf3;'>" + total_fmt + "</strong></span>"
            "<span>🏦 " + str(row["account_type"]) + " · " + str(row["home_city"]) + "</span>"
            "<span>🕐 " + peak_str + "</span>"
            "<span>🔍 " + fraud_label + "</span>"
          "</div>"

          + decision_html +
        "</div>"
    )
    return card

# ── Alert cards ───────────────────────────────────────────────────────────────
for _, row in filtered.iterrows():
    acc_id   = row["account_id"]
    decision = decisions.get(acc_id)
    status   = decision["decision"].title() if decision else "Pending"

    st.markdown(build_card(row, decision, status, decisions), unsafe_allow_html=True)

    if status == "Pending":
        col1, col2, col3, col4, spacer = st.columns([1, 1, 1, 1, 4])
        with col1:
            if st.button("🔒 Block", key="block_" + acc_id, type="primary"):
                save_decision(acc_id, "blocked", analyst_name or "unknown", "")
                st.rerun()
        with col2:
            if st.button("✅ Clear", key="clear_" + acc_id):
                save_decision(acc_id, "cleared", analyst_name or "unknown", "")
                st.rerun()
        with col3:
            if st.button("📋 Escalate", key="esc_" + acc_id):
                save_decision(acc_id, "escalated", analyst_name or "unknown", "")
                st.rerun()
        with col4:
            if st.button("👁 Monitor", key="mon_" + acc_id):
                save_decision(acc_id, "monitoring", analyst_name or "unknown", "")
                st.rerun()
    else:
        col1, spacer = st.columns([1, 7])
        with col1:
            if st.button("↩ Undo", key="undo_" + acc_id):
                init_db()
                con = sqlite3.connect(DB_PATH)
                con.execute("DELETE FROM alert_decisions WHERE account_id = ?", (acc_id,))
                con.commit()
                con.close()
                st.rerun()

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)