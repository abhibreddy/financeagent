import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils import load_data, compute_velocity, build_alert_queue, VELOCITY_THRESHOLD

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FraudGuard — Account Lookup",
    page_icon="🛡️",
    layout="wide",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
with open("css/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🛡️ FraudGuard")
    st.caption("Fraud Detection Platform")
    st.divider()
    st.markdown("**Agents**")
    _agents = [
        ("🔍", "Velocity Agent",  "online"),
        ("🧾", "Invoice Agent",   "online"),
        ("🔎", "Audit Agent",     "online"),
        ("📊", "Synthesis Agent", "online"),
    ]
    for _icon, _name, _status in _agents:
        st.markdown(
            f"<div class='agent-status-row'>{_icon} {_name}"
            f"<span style='flex:1'></span>"
            f"<span class='agent-dot {_status}'></span></div>",
            unsafe_allow_html=True,
        )
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
flagged_ids    = queue["account_id"].tolist()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="fd-header">
  <div class="fd-icon">🛡️</div>
  <div>
    <div class="fd-title">FraudGuard — Account Lookup</div>
    <div class="fd-sub">Transaction Velocity</div>
  </div>
</div>
""", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🔍 Single Account", "⚖️ Compare Accounts"])

# ══ TAB 1: Single Account (existing) ═════════════════════════════════════════
with tab1:
    col_input, col_btn = st.columns([4, 1])
    with col_input:
        query = st.text_input("Account ID", placeholder="e.g. ACC-00042", label_visibility="collapsed")
    with col_btn:
        st.button("Look Up", type="primary", use_container_width=True)

    st.caption(f"🔴 {len(flagged_ids)} flagged accounts detected — try one:")
    picked = st.selectbox("Quick pick", ["—"] + flagged_ids, label_visibility="collapsed")
    if picked != "—":
        query = picked

    # ── Lookup ────────────────────────────────────────────────────────────────
    if query and query.strip():
        acc_id   = query.strip().upper()
        acc_row  = accounts[accounts["account_id"] == acc_id]
        acc_txns = txns[txns["account_id"] == acc_id].sort_values("timestamp")

        if acc_row.empty:
            st.error(f"Account **{acc_id}** not found.")
            st.stop()

        acc = acc_row.iloc[0]

        # ── Account info ──────────────────────────────────────────────────────
        st.markdown('<div class="sec-label">Account Info</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="acc-info">
          <div class="acc-row"><span class="acc-key">Account ID</span><span class="acc-val">{acc['account_id']}</span></div>
          <div class="acc-row"><span class="acc-key">Customer</span><span class="acc-val">{acc['customer_name']}</span></div>
          <div class="acc-row"><span class="acc-key">Account type</span><span class="acc-val">{acc['account_type']}</span></div>
          <div class="acc-row"><span class="acc-key">Home city</span><span class="acc-val">{acc['home_city']}</span></div>
          <div class="acc-row"><span class="acc-key">Risk tier</span><span class="acc-val">{acc['risk_tier']}</span></div>
          <div class="acc-row"><span class="acc-key">KYC verified</span><span class="acc-val">{'✅ Yes' if acc['kyc_verified'] else '❌ No'}</span></div>
          <div class="acc-row"><span class="acc-key">Dormant</span><span class="acc-val">{'⚠️ Yes (' + str(int(acc['dormant_days'])) + ' days)' if acc['is_dormant'] else 'No'}</span></div>
        </div>
        """, unsafe_allow_html=True)

        # ── Compute velocity live ─────────────────────────────────────────────
        with st.spinner("Computing velocity..."):
            v = compute_velocity(acc_txns)

        max_vel    = v["max_velocity"]
        geo_flags  = v["geo_flags"]
        total_amt  = v["total_amount"]
        risk       = v["risk_level"]
        risk_score = v["risk_score"]
        peak_start, peak_end = v["peak_window"]

        # ── Metrics ───────────────────────────────────────────────────────────
        st.markdown('<div class="sec-label">Velocity Summary</div>', unsafe_allow_html=True)
        vel_color = "red" if max_vel >= VELOCITY_THRESHOLD else "green"
        geo_color = "red" if geo_flags > 0 else "green"

        peak_str = (
            f"{peak_start.strftime('%m/%d %H:%M')} – {peak_end.strftime('%H:%M')}"
            if peak_start else "—"
        )

        st.markdown(f"""
        <div class="metric-row">
          <div class="metric-box">
            <div class="label">Max txns / 5 min</div>
            <div class="value {vel_color}">{max_vel}</div>
          </div>
          <div class="metric-box">
            <div class="label">Threshold</div>
            <div class="value">{VELOCITY_THRESHOLD}</div>
          </div>
          <div class="metric-box">
            <div class="label">Risk score</div>
            <div class="value {vel_color}">{risk_score}</div>
          </div>
          <div class="metric-box">
            <div class="label">Geo flags</div>
            <div class="value {geo_color}">{geo_flags}</div>
          </div>
          <div class="metric-box">
            <div class="label">Total txns</div>
            <div class="value">{len(acc_txns)}</div>
          </div>
        </div>
        <div class="metric-row">
          <div class="metric-box">
            <div class="label">Peak window</div>
            <div class="value" style="font-size:13px">{peak_str}</div>
          </div>
          <div class="metric-box">
            <div class="label">Total amount</div>
            <div class="value">${total_amt:,.2f}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Verdict ───────────────────────────────────────────────────────────
        if risk == "High":
            verdict_class  = "verdict-high"
            verdict_icon   = "🔴"
            verdict_text   = "FLAGGED — HIGH RISK"
            verdict_detail = (
                f"Max velocity of <strong>{max_vel} txns / 5 min</strong> exceeds threshold of {VELOCITY_THRESHOLD}. "
                + (f"<strong>{geo_flags} geographic anomaly flag(s)</strong> detected. " if geo_flags else "")
                + ("Account was dormant before this activity. " if acc["is_dormant"] else "")
                + "Recommend immediate review and possible block."
            )
        elif risk == "Medium":
            verdict_class  = "verdict-medium"
            verdict_icon   = "🟡"
            verdict_text   = "REVIEW — MEDIUM RISK"
            verdict_detail = (
                f"Velocity of <strong>{max_vel} txns / 5 min</strong> is at or above threshold. "
                + "Activity warrants analyst review before further action."
            )
        else:
            verdict_class  = "verdict-low"
            verdict_icon   = "🟢"
            verdict_text   = "CLEAR — LOW RISK"
            verdict_detail = (
                f"Max velocity of <strong>{max_vel} txns / 5 min</strong> is within normal range. "
                + "No geographic anomalies detected."
            )

        st.markdown(f"""
        <div class="verdict-card {verdict_class}">
          <div class="verdict-label">Agent verdict</div>
          <div class="verdict-main">{verdict_icon} &nbsp;{verdict_text}</div>
          <div class="verdict-detail">{verdict_detail}</div>
        </div>
        """, unsafe_allow_html=True)

        # ── Agent signals ─────────────────────────────────────────────────────
        if risk in ("High", "Medium"):
            st.markdown('<div class="sec-label">Agent Signals</div>', unsafe_allow_html=True)

            if max_vel >= VELOCITY_THRESHOLD:
                st.markdown(f"""
                <div class="agent-alert danger">
                  ⚡ <span><strong>Velocity breach</strong> — {max_vel} transactions in a 5-minute window,
                  {max_vel / VELOCITY_THRESHOLD:.1f}× above the {VELOCITY_THRESHOLD} txn threshold.
                  Pattern consistent with credential stuffing or account takeover.</span>
                </div>
                """, unsafe_allow_html=True)

            if geo_flags > 0:
                cities = acc_txns[acc_txns["geo_flag"] == True]["city"].unique().tolist()
                st.markdown(f"""
                <div class="agent-alert danger">
                  🌍 <span><strong>Geographic impossibility</strong> — activity detected across
                  {', '.join(cities[:3])}. Near-simultaneous use across distant locations
                  is a strong account takeover indicator.</span>
                </div>
                """, unsafe_allow_html=True)

            if acc["is_dormant"]:
                st.markdown(f"""
                <div class="agent-alert warning">
                  💤 <span><strong>Dormant account reactivation</strong> — account was inactive for
                  {int(acc['dormant_days'])} days before this burst. Sudden reactivation
                  with high velocity is a common ATO pattern.</span>
                </div>
                """, unsafe_allow_html=True)

            if not acc["kyc_verified"]:
                st.markdown("""
                <div class="agent-alert warning">
                  🪪 <span><strong>KYC not verified</strong> — customer identity unconfirmed.
                  Elevated risk for synthetic identity fraud.</span>
                </div>
                """, unsafe_allow_html=True)

        # ── Transaction timeline ──────────────────────────────────────────────
        st.markdown('<div class="sec-label">Transaction History (last 20)</div>', unsafe_allow_html=True)

        display_txns  = acc_txns.sort_values("timestamp", ascending=False).head(20)
        timeline_html = '<div class="tl-wrap">'
        for _, row in display_txns.iterrows():
            ts    = row["timestamp"].strftime("%m/%d %H:%M")
            amt   = f"${row['amount']:,.2f}"
            ttype = row["txn_type"]
            city  = row["city"]

            if row["status"] == "Blocked":
                badge = '<span class="badge b-block">BLOCKED</span>'
            elif row["velocity_flag"] or row["geo_flag"]:
                badge = '<span class="badge b-flag">FLAGGED</span>'
            else:
                badge = '<span class="badge b-ok">OK</span>'

            timeline_html += f"""
            <div class="tl-row">
              <span class="tl-time">{ts}</span>
              <span class="tl-amt">{amt}</span>
              <span class="tl-type">{ttype}</span>
              <span class="tl-city">{city}</span>
              {badge}
            </div>"""

        timeline_html += "</div>"
        st.markdown(timeline_html, unsafe_allow_html=True)

        # ── Actions ───────────────────────────────────────────────────────────
        if risk != "Low":
            st.markdown('<div class="sec-label">Actions</div>', unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("🔒 Block Account", type="primary", use_container_width=True):
                    st.error(f"Account {acc_id} flagged for blocking. (Wire up LangGraph agent to execute.)")
            with col2:
                if st.button("📋 Draft SAR", use_container_width=True):
                    st.info("SAR draft would be generated by the LangGraph agent here.")
            with col3:
                if st.button("👥 Peer Compare", use_container_width=True):
                    st.info("Agent would compare this account's velocity against similar accounts.")

# ══ TAB 2: Compare Accounts ═══════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="sec-label">Select 2–4 accounts to compare</div>', unsafe_allow_html=True)
    all_ids = sorted(txns["account_id"].unique().tolist())
    selected_ids = st.multiselect(
        "Accounts",
        options=all_ids,
        default=flagged_ids[:3] if len(flagged_ids) >= 3 else flagged_ids,
        max_selections=4,
        label_visibility="collapsed",
    )

    if len(selected_ids) < 2:
        st.info("Select at least 2 accounts to compare.")
    else:
        from utils import compare_accounts
        comparisons = compare_accounts(selected_ids, txns, accounts)

        if not comparisons:
            st.warning("No data found for selected accounts.")
        else:
            # ── Side-by-side metric cards ─────────────────────────────────────
            st.markdown('<div class="sec-label">Risk Summary</div>', unsafe_allow_html=True)
            cols = st.columns(len(comparisons))
            for i, c in enumerate(comparisons):
                risk_color = "red" if c["risk_level"] == "High" else ("yellow" if c["risk_level"] == "Medium" else "green")
                risk_icon  = "🔴" if c["risk_level"] == "High" else ("🟡" if c["risk_level"] == "Medium" else "🟢")
                val_color  = "#dc2626" if risk_color == "red" else "#d97706" if risk_color == "yellow" else "#16a34a"
                with cols[i]:
                    st.markdown(f"""
                    <div class="acc-info">
                      <div class="compare-header">{risk_icon} {c['account_id']}</div>
                      <div class="acc-row"><span class="acc-key">Customer</span><span class="acc-val">{c['customer']}</span></div>
                      <div class="acc-row"><span class="acc-key">Risk score</span>
                        <span class="acc-val" style="color:{val_color};font-weight:700;font-size:18px">{c['risk_score']}</span></div>
                      <div class="acc-row"><span class="acc-key">Max velocity</span><span class="acc-val">{c['max_velocity']} txns/5min</span></div>
                      <div class="acc-row"><span class="acc-key">Geo flags</span><span class="acc-val">{c['geo_flags']}</span></div>
                      <div class="acc-row"><span class="acc-key">Total amount</span><span class="acc-val">${c['total_amount']:,.2f}</span></div>
                      <div class="acc-row"><span class="acc-key">KYC</span><span class="acc-val">{'✅' if c['kyc_verified'] else '❌ Unverified'}</span></div>
                      <div class="acc-row"><span class="acc-key">Dormant</span><span class="acc-val">{'⚠️ Yes' if c['is_dormant'] else 'No'}</span></div>
                    </div>
                    """, unsafe_allow_html=True)

            # ── Velocity bar chart ────────────────────────────────────────────
            st.markdown('<div class="sec-label">Velocity Comparison</div>', unsafe_allow_html=True)
            bar_colors = [
                "#dc2626" if c["risk_level"] == "High" else
                "#d97706" if c["risk_level"] == "Medium" else "#16a34a"
                for c in comparisons
            ]
            fig = go.Figure(data=[go.Bar(
                x=[c["account_id"] for c in comparisons],
                y=[c["max_velocity"] for c in comparisons],
                marker_color=bar_colors,
                text=[f'{c["max_velocity"]} txns' for c in comparisons],
                textposition="outside",
            )])
            fig.add_hline(y=5, line_dash="dash", line_color="#6b7280",
                          annotation_text="Threshold (5)", annotation_position="right")
            fig.update_layout(
                paper_bgcolor="white", plot_bgcolor="white",
                font=dict(family="Inter, sans-serif", color="#374151"),
                yaxis=dict(title="Max txns / 5 min", gridcolor="#f3f4f6"),
                xaxis=dict(gridcolor="#f3f4f6"),
                height=300, margin=dict(t=20, b=20),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)

            # ── Risk score bar chart ──────────────────────────────────────────
            st.markdown('<div class="sec-label">Risk Score Comparison</div>', unsafe_allow_html=True)
            fig2 = go.Figure(data=[go.Bar(
                x=[c["account_id"] for c in comparisons],
                y=[c["risk_score"] for c in comparisons],
                marker_color=bar_colors,
                text=[str(c["risk_score"]) for c in comparisons],
                textposition="outside",
            )])
            fig2.update_layout(
                paper_bgcolor="white", plot_bgcolor="white",
                font=dict(family="Inter, sans-serif", color="#374151"),
                yaxis=dict(title="Risk Score (0–100)", range=[0, 110], gridcolor="#f3f4f6"),
                height=280, margin=dict(t=20, b=20),
                showlegend=False,
            )
            st.plotly_chart(fig2, use_container_width=True)