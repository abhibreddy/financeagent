import streamlit as st
import pandas as pd
import sqlite3
from utils import (
    load_invoice_data, analyze_invoice, build_invoice_queue,
    get_invoice_decisions, save_invoice_decision, init_db, DB_PATH
)

st.set_page_config(
    page_title="FraudGuard — Invoice Fraud",
    page_icon="🧾",
    layout="centered",
)

with open("css/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data
def cached_invoice_data():
    return load_invoice_data()

@st.cache_data
def cached_invoice_queue(invoices, vendors):
    return build_invoice_queue(invoices, vendors)

invoices, vendors = cached_invoice_data()
queue             = cached_invoice_queue(invoices, vendors)
decisions         = get_invoice_decisions()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="fd-header">
  <div class="fd-icon">🧾</div>
  <div>
    <div class="fd-title">Invoice Fraud Detection</div>
    <div class="fd-sub">Live signal analysis · Vendor risk · Payment integrity</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["🔍  Invoice Lookup", "🚨  Flagged Queue"])


# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — Invoice Lookup
# ════════════════════════════════════════════════════════════════════════════
with tab1:

    # ── Search ────────────────────────────────────────────────────────────────
    col_input, col_btn = st.columns([4, 1])
    with col_input:
        query = st.text_input("Invoice ID", placeholder="e.g. INV-F0001", label_visibility="collapsed")
    with col_btn:
        st.button("Look Up", type="primary", use_container_width=True)

    flagged_ids = queue["invoice_id"].tolist()
    st.caption("🔴 " + str(len(flagged_ids)) + " flagged invoices — try one:")
    picked = st.selectbox("Quick pick", ["—"] + flagged_ids[:30], label_visibility="collapsed")
    if picked != "—":
        query = picked

    if not query or not query.strip():
        st.stop()

    inv_id = query.strip().upper()
    result = analyze_invoice(inv_id, invoices, vendors)

    if not result:
        st.error("Invoice **" + inv_id + "** not found.")
        st.stop()

    inv    = result["invoice"]
    vendor = result["vendor"]
    risk   = result["risk_level"]
    score  = result["risk_score"]

    # ── Invoice info ──────────────────────────────────────────────────────────
    st.markdown('<div class="sec-label">Invoice Details</div>', unsafe_allow_html=True)

    po_val       = str(inv["po_number"]) if pd.notna(inv.get("po_number")) and inv["po_number"] else "None"
    dup_val      = str(inv["duplicate_of"]) if pd.notna(inv.get("duplicate_of")) and inv["duplicate_of"] else "No"
    altered_val  = "Yes — original: ${:,.2f}".format(inv["original_amount"]) if inv["amount_altered"] and pd.notna(inv.get("original_amount")) else "No"
    bank_val     = "⚠️ Yes" if inv["bank_changed"] else "No"
    new_ven_val  = "⚠️ Yes" if inv["new_vendor"] else "No"

    st.markdown(
        "<div class='acc-info'>"
        "<div class='acc-row'><span class='acc-key'>Invoice ID</span><span class='acc-val'>" + str(inv["invoice_id"]) + "</span></div>"
        "<div class='acc-row'><span class='acc-key'>Vendor</span><span class='acc-val'>" + str(inv["vendor_name"]) + "</span></div>"
        "<div class='acc-row'><span class='acc-key'>Category</span><span class='acc-val'>" + str(inv["category"]) + "</span></div>"
        "<div class='acc-row'><span class='acc-key'>Amount</span><span class='acc-val'>${:,.2f}".format(inv["amount"]) + "</span></div>"
        "<div class='acc-row'><span class='acc-key'>Submitted</span><span class='acc-val'>" + str(inv["submitted_date"].date() if pd.notna(inv["submitted_date"]) else "—") + "</span></div>"
        "<div class='acc-row'><span class='acc-key'>PO number</span><span class='acc-val'>" + po_val + "</span></div>"
        "<div class='acc-row'><span class='acc-key'>Duplicate of</span><span class='acc-val'>" + dup_val + "</span></div>"
        "<div class='acc-row'><span class='acc-key'>Amount altered</span><span class='acc-val'>" + altered_val + "</span></div>"
        "<div class='acc-row'><span class='acc-key'>Bank changed</span><span class='acc-val'>" + bank_val + "</span></div>"
        "<div class='acc-row'><span class='acc-key'>New vendor</span><span class='acc-val'>" + new_ven_val + "</span></div>"
        "</div>",
        unsafe_allow_html=True
    )

    # ── Vendor info ───────────────────────────────────────────────────────────
    if vendor is not None:
        st.markdown('<div class="sec-label">Vendor Profile</div>', unsafe_allow_html=True)
        ein_val  = "✅ Verified" if vendor["ein_verified"] else "❌ Not verified"
        kyc_val  = "✅ Yes" if vendor["kyc_verified"] else "❌ No"
        duns_val = str(vendor["duns_number"]) if pd.notna(vendor["duns_number"]) else "None"

        st.markdown(
            "<div class='acc-info'>"
            "<div class='acc-row'><span class='acc-key'>Vendor ID</span><span class='acc-val'>" + str(vendor["vendor_id"]) + "</span></div>"
            "<div class='acc-row'><span class='acc-key'>Address</span><span class='acc-val'>" + str(vendor["address"])[:60] + "...</span></div>"
            "<div class='acc-row'><span class='acc-key'>Registered</span><span class='acc-val'>" + str(vendor["registered_date"]) + " (" + str(int(vendor["days_registered"])) + " days ago)</span></div>"
            "<div class='acc-row'><span class='acc-key'>EIN</span><span class='acc-val'>" + ein_val + "</span></div>"
            "<div class='acc-row'><span class='acc-key'>DUNS</span><span class='acc-val'>" + duns_val + "</span></div>"
            "<div class='acc-row'><span class='acc-key'>KYC verified</span><span class='acc-val'>" + kyc_val + "</span></div>"
            "<div class='acc-row'><span class='acc-key'>Prior invoices</span><span class='acc-val'>" + str(int(vendor["prior_invoices"])) + "</span></div>"
            "<div class='acc-row'><span class='acc-key'>Avg invoice</span><span class='acc-val'>${:,.2f}".format(vendor["avg_invoice_amt"]) + "</span></div>"
            "</div>",
            unsafe_allow_html=True
        )

    # ── Risk metrics ──────────────────────────────────────────────────────────
    st.markdown('<div class="sec-label">Risk Assessment</div>', unsafe_allow_html=True)
    score_color  = "red" if risk == "High" else "" if risk == "Medium" else "green"
    signal_color = "red" if len(result["signals"]) >= 3 else ""

    st.markdown(
        "<div class='metric-row'>"
        "<div class='metric-box'><div class='label'>Risk score</div><div class='value " + score_color + "'>" + str(score) + "</div></div>"
        "<div class='metric-box'><div class='label'>Risk level</div><div class='value " + score_color + "'>" + risk + "</div></div>"
        "<div class='metric-box'><div class='label'>Signals fired</div><div class='value " + signal_color + "'>" + str(len(result["signals"])) + "</div></div>"
        "<div class='metric-box'><div class='label'>Invoice amount</div><div class='value'>${:,.0f}".format(inv["amount"]) + "</div></div>"
        "</div>",
        unsafe_allow_html=True
    )

    # ── Verdict ───────────────────────────────────────────────────────────────
    if risk == "High":
        verdict_class  = "verdict-high"
        verdict_icon   = "🔴"
        verdict_text   = "FLAGGED — HIGH RISK"
        verdict_detail = "Multiple fraud signals detected. Payment should be held pending full investigation."
    elif risk == "Medium":
        verdict_class  = "verdict-medium"
        verdict_icon   = "🟡"
        verdict_text   = "REVIEW — MEDIUM RISK"
        verdict_detail = "One or more risk signals detected. Analyst review recommended before approving payment."
    else:
        verdict_class  = "verdict-low"
        verdict_icon   = "🟢"
        verdict_text   = "CLEAR — LOW RISK"
        verdict_detail = "No significant fraud signals detected."

    st.markdown(
        "<div class='verdict-card " + verdict_class + "'>"
        "<div class='verdict-label'>Agent verdict</div>"
        "<div class='verdict-main'>" + verdict_icon + " &nbsp;" + verdict_text + "</div>"
        "<div class='verdict-detail'>" + verdict_detail + "</div>"
        "</div>",
        unsafe_allow_html=True
    )

    # ── Signals ───────────────────────────────────────────────────────────────
    if result["signals"]:
        st.markdown('<div class="sec-label">Fraud Signals</div>', unsafe_allow_html=True)
        for sig in result["signals"]:
            alert_class = "danger" if sig["type"] == "danger" else "warning"
            st.markdown(
                "<div class='agent-alert " + alert_class + "'>"
                + sig["icon"] + " <span><strong>" + sig["title"] + "</strong> — " + sig["detail"] + "</span>"
                "</div>",
                unsafe_allow_html=True
            )

    # ── Actions ───────────────────────────────────────────────────────────────
    if risk != "Low":
        st.markdown('<div class="sec-label">Actions</div>', unsafe_allow_html=True)
        existing = decisions.get(inv_id)
        if existing:
            st.info("Decision already recorded: **" + existing["decision"].title() + "** by " + existing["analyst"] + " on " + existing["decided_at"][:10])
            if st.button("↩ Undo decision", key="undo_lookup"):
                init_db()
                con = sqlite3.connect(DB_PATH)
                con.execute("DELETE FROM invoice_decisions WHERE invoice_id = ?", (inv_id,))
                con.commit()
                con.close()
                st.rerun()
        else:
            analyst = st.text_input("Analyst name", placeholder="Your name", key="analyst_lookup")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("🔒 Hold Payment", type="primary", use_container_width=True):
                    save_invoice_decision(inv_id, "held", analyst or "unknown", "")
                    st.error("Payment for " + inv_id + " held pending investigation.")
            with col2:
                if st.button("✅ Approve", use_container_width=True):
                    save_invoice_decision(inv_id, "approved", analyst or "unknown", "")
                    st.success("Invoice " + inv_id + " approved for payment.")
            with col3:
                if st.button("📋 Escalate", use_container_width=True):
                    save_invoice_decision(inv_id, "escalated", analyst or "unknown", "")
                    st.warning("Invoice " + inv_id + " escalated to compliance.")


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — Flagged Queue
# ════════════════════════════════════════════════════════════════════════════
with tab2:

    # ── Metrics ───────────────────────────────────────────────────────────────
    high_ct    = len(queue[queue["risk_level"] == "High"])
    medium_ct  = len(queue[queue["risk_level"] == "Medium"])
    held_ct    = sum(1 for d in decisions.values() if d["decision"] == "held")
    cleared_ct = sum(1 for d in decisions.values() if d["decision"] == "approved")
    pending_ct = len(queue) - len(decisions)
    exposure   = queue["amount"].sum()

    st.markdown(
        "<div class='metric-row'>"
        "<div class='metric-box'><div class='label'>🔴 High risk</div><div class='value red'>" + str(high_ct) + "</div></div>"
        "<div class='metric-box'><div class='label'>🟡 Medium risk</div><div class='value'>" + str(medium_ct) + "</div></div>"
        "<div class='metric-box'><div class='label'>⏳ Pending</div><div class='value'>" + str(pending_ct) + "</div></div>"
        "<div class='metric-box'><div class='label'>💰 Total exposure</div><div class='value red'>${:,.0f}".format(exposure) + "</div></div>"
        "</div>",
        unsafe_allow_html=True
    )

    # ── Filters ───────────────────────────────────────────────────────────────
    col_f1, col_f2, col_f3 = st.columns([2, 2, 2])
    with col_f1:
        risk_filter = st.selectbox("Risk", ["All", "High", "Medium"], label_visibility="collapsed", key="q_risk")
    with col_f2:
        type_filter = st.selectbox(
            "Fraud type",
            ["All", "shell_vendor", "phantom_billing", "bank_redirect", "duplicate", "altered_amount"],
            label_visibility="collapsed", key="q_type"
        )
    with col_f3:
        analyst_name = st.text_input("Analyst name", placeholder="Your name for decisions", label_visibility="collapsed", key="q_analyst")

    filtered = queue.copy()
    if risk_filter != "All":
        filtered = filtered[filtered["risk_level"] == risk_filter]
    if type_filter != "All":
        filtered = filtered[filtered["fraud_type"] == type_filter]

    st.markdown(
        "<div class='sec-label'>" + str(len(filtered)) + " invoices — sorted by risk score</div>",
        unsafe_allow_html=True
    )

    if filtered.empty:
        st.info("No invoices match the current filters.")
        st.stop()

    # ── Invoice cards ─────────────────────────────────────────────────────────
    for _, row in filtered.iterrows():
        inv_id   = row["invoice_id"]
        decision = decisions.get(inv_id)
        status   = decision["decision"].title() if decision else "Pending"
        risk     = row["risk_level"]
        border   = "#6e2929" if risk == "High" else "#4d3608"
        bg       = "#1c0d0d" if risk == "High" else "#1c1300"
        risk_icon    = "🔴" if risk == "High" else "🟡"
        score_color  = "#f85149" if risk == "High" else "#d29922"

        status_badges = {
            "Pending":   '<span class="badge b-flag">PENDING</span>',
            "Held":      '<span class="badge b-block">HELD</span>',
            "Approved":  '<span class="badge b-ok">APPROVED</span>',
            "Escalated": '<span class="badge b-flag">ESCALATED</span>',
        }
        status_badge = status_badges.get(status, "<span class='badge'>" + status + "</span>")

        amount_fmt   = "${:,.0f}".format(row["amount"])
        fraud_label  = str(row["fraud_type"]).replace("_", " ")

        decision_html = ""
        if decision:
            decided_at    = decision["decided_at"][:16].replace("T", " ")
            decision_html = (
                "<div style='font-size:11px;color:#7d8590;margin-top:8px;'>"
                "Decided by <strong>" + str(decision["analyst"]) + "</strong> · " + decided_at +
                "</div>"
            )

        card = (
            "<div style='background:" + bg + ";border:1px solid " + border + ";border-radius:10px;padding:16px 20px;margin-bottom:12px;'>"
              "<div style='display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;'>"
                "<div style='display:flex;align-items:center;gap:8px;flex-wrap:wrap;'>"
                  "<span style='font-size:15px;font-weight:600;color:#e6edf3;'>" + risk_icon + " " + inv_id + "</span>"
                  "<span style='font-size:12px;color:#7d8590;'>" + str(row["vendor_name"]) + "</span>"
                  "<span style='font-size:11px;color:#7d8590;'>· " + str(row["category"]) + "</span>"
                "</div>"
                "<div style='display:flex;align-items:center;gap:8px;'>"
                  "<span style='font-size:11px;color:#7d8590;'>Risk score</span>"
                  "<span style='font-size:18px;font-weight:600;color:" + score_color + ";'>" + str(row["risk_score"]) + "</span>"
                  + status_badge +
                "</div>"
              "</div>"
              "<div style='display:flex;gap:20px;font-size:12px;color:#8b949e;flex-wrap:wrap;'>"
                "<span>💰 <strong style='color:#e6edf3;'>" + amount_fmt + "</strong></span>"
                "<span>📅 " + str(row["submitted"]) + "</span>"
                "<span>🔍 " + fraud_label + "</span>"
                "<span>⚠️ <strong style='color:#e6edf3;'>" + str(row["signal_count"]) + "</strong> signals</span>"
              "</div>"
              + decision_html +
            "</div>"
        )
        st.markdown(card, unsafe_allow_html=True)

        if status == "Pending":
            col1, col2, col3, spacer = st.columns([1, 1, 1, 5])
            with col1:
                if st.button("🔒 Hold", key="hold_" + inv_id, type="primary"):
                    save_invoice_decision(inv_id, "held", analyst_name or "unknown", "")
                    st.rerun()
            with col2:
                if st.button("✅ Approve", key="approve_" + inv_id):
                    save_invoice_decision(inv_id, "approved", analyst_name or "unknown", "")
                    st.rerun()
            with col3:
                if st.button("📋 Escalate", key="esc_" + inv_id):
                    save_invoice_decision(inv_id, "escalated", analyst_name or "unknown", "")
                    st.rerun()
        else:
            col1, spacer = st.columns([1, 7])
            with col1:
                if st.button("↩ Undo", key="undo_" + inv_id):
                    init_db()
                    con = sqlite3.connect(DB_PATH)
                    con.execute("DELETE FROM invoice_decisions WHERE invoice_id = ?", (inv_id,))
                    con.commit()
                    con.close()
                    st.rerun()

        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
