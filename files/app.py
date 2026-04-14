"""
app.py — Acne Studios AI Clienteling Engine
Streamlit entry point. All business logic lives in modules/.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import streamlit as st
from openai import OpenAI

from modules.content_generator import (
    PERSONAS,
    HALLEROED_FALLBACK,
    generate_blog,
    generate_newsletters,
    generate_editorial_image,
    save_campaign_content,
    load_recent_campaigns,
)
from modules.crm_client import (
    upsert_contacts,
    log_campaign,
    simulate_send,
    load_campaign_history,
)
from modules.analytics import (
    run_ab_test,
    simulate_campaign_performance,
    generate_performance_summary,
    load_performance_history,
)

st.set_page_config(
    layout="wide",
    page_title="Acne Studios Clienteling Engine",
    page_icon="🖤",
)

st.markdown("""
<style>
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 1.5rem;
    background-color: #F7F7F7;
}
h1, h2, h3 { font-weight: 500; color: #1a1a1a; letter-spacing: -0.8px; }

[data-testid="stVerticalBlock"] > div {
    background-color: white;
    padding: 16px 20px;
    border-radius: 10px;
    box-shadow: 0 1px 6px rgba(0,0,0,0.04);
}

.stButton > button {
    background-color: #1a1a1a; color: #F7F7F7;
    border-radius: 6px; border: none;
    padding: 9px 20px; font-size: 13.5px;
    transition: background 0.2s;
}
.stButton > button:hover { background-color: #E6C1B3; color: #1a1a1a; }

.email-card {
    background: #FAFAFA;
    border: 1px solid #E8E8E8;
    border-radius: 8px;
    padding: 14px;
    height: 360px;
    overflow-y: auto;
    white-space: pre-wrap;
    font-family: 'Georgia', serif;
    font-size: 12.5px;
    line-height: 1.6;
    color: #2a2a2a;
}
.email-label {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #C8826A;
    margin-bottom: 6px;
}

[data-testid="stMetric"] {
    background: white;
    border-radius: 8px;
    padding: 12px 14px !important;
    border: 1px solid #F0EDED;
}
[data-testid="stMetricLabel"] { font-size: 11px !important; }
[data-testid="stMetricValue"] { font-size: 20px !important; }

.pill-success { background:#e6f4ea; color:#1e7e34; border-radius:20px; padding:3px 10px; font-size:11px; font-weight:600; }
.pill-warn    { background:#fff8e1; color:#9c6f00; border-radius:20px; padding:3px 10px; font-size:11px; font-weight:600; }
.pill-gray    { background:#f0f0f0; color:#555;    border-radius:20px; padding:3px 10px; font-size:11px; font-weight:600; }

.section-title {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #bbb;
    margin: 4px 0 8px 0;
}

[data-testid="stExpander"] {
    border: 1px solid #F0EDED !important;
    border-radius: 8px !important;
}

button[data-baseweb="tab"] { font-size: 13px; padding: 8px 14px; }
.element-container { margin-bottom: 0.35rem !important; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔑 API Credentials")
    openai_key    = st.text_input("OpenAI API Key",       type="password", help="gpt-4o + dall-e-3")
    hubspot_token = st.text_input("HubSpot Bearer Token", type="password",
                                  help="Private App token from HubSpot → Settings → Integrations")
    st.markdown("### ⚙️ Options")
    generate_image = st.toggle("Generate editorial image", value=True)
    run_ab         = st.toggle("Run A/B test simulation",  value=True)
    sync_hubspot   = st.toggle("Sync to HubSpot CRM",      value=bool(hubspot_token))
    st.caption("Acne Studios Clienteling Engine · v2.0")

openai_client: OpenAI | None = OpenAI(api_key=openai_key) if openai_key else None


# ── Header ─────────────────────────────────────────────────────
st.markdown(
    "<div style='display:flex; align-items:baseline; gap:10px; margin-bottom:4px;'>"
    "<span style='font-size:20px; font-weight:500; letter-spacing:-0.5px;'>🖤 Acne Studios Clienteling Engine</span>"
    "<span style='font-size:11px; color:#bbb; margin-left:4px;'>generate → personalise → distribute → analyse</span>"
    "</div>",
    unsafe_allow_html=True,
)

tab_pipeline, tab_history, tab_crm = st.tabs(["🚀 Pipeline", "📊 History", "🗂️ CRM Log"])


# ═══════════════════════════════════════════════════════════════
#  TAB 1 — PIPELINE
# ═══════════════════════════════════════════════════════════════

with tab_pipeline:

    col_setup, col_preview = st.columns([1.2, 1], gap="medium")
    with col_setup:
        st.markdown('<div class="section-title">Campaign Setup</div>', unsafe_allow_html=True)
        product_input = st.text_input(
            "Product / Topic", value="Distressed Denim Jacket",
            placeholder="e.g. Oversized Mohair Cardigan",
            label_visibility="collapsed",
        )
        run_btn = st.button("▶  Generate Full Pipeline", use_container_width=True)
    with col_preview:
        st.image(st.session_state.get("hero_image", HALLEROED_FALLBACK), use_container_width=True)

    # ── Execution ──────────────────────────────────────────────
    if run_btn:
        if not openai_key:
            st.error("⚠️  Please enter your OpenAI API Key in the sidebar.")
            st.stop()

        progress = st.progress(0, text="Starting pipeline…")

        if generate_image:
            progress.progress(10, "Generating editorial image…")
            if product_input == "Distressed Denim Jacket":
                st.session_state.hero_image = HALLEROED_FALLBACK
            else:
                try:
                    st.session_state.hero_image = generate_editorial_image(product_input, openai_client)
                except Exception as e:
                    st.warning(f"Image generation failed: {e}")
                    st.session_state.hero_image = HALLEROED_FALLBACK

        progress.progress(25, "Writing editorial blog…")
        try:
            blog = generate_blog(product_input, openai_client)
        except RuntimeError as e:
            st.error(str(e)); st.stop()

        progress.progress(50, "Personalising newsletters…")
        newsletters = generate_newsletters(blog, product_input, openai_client)

        progress.progress(60, "Saving content…")
        content_file = save_campaign_content(product_input, blog, newsletters)

        crm_result = {"success": 0, "errors": [], "skipped": True}
        send_counts: dict[str, int] = {}
        if sync_hubspot and hubspot_token:
            progress.progress(70, "Syncing contacts to HubSpot…")
            crm_result = upsert_contacts(hubspot_token)
            progress.progress(78, "Simulating newsletter send…")
            send_counts = simulate_send(hubspot_token, newsletters, product_input)
        else:
            send_counts = {"VIP": 2, "REGULAR": 2, "AT_RISK": 2}

        ab_results = {}
        if run_ab:
            progress.progress(85, "Running A/B test…")
            ab_results = run_ab_test()

        progress.progress(90, "Simulating performance…")
        perf_record = simulate_campaign_performance(
            product_input,
            campaign_id=f"LIVE-{pd.Timestamp.utcnow().strftime('%H%M%S')}",
        )

        progress.progress(95, "Generating AI summary…")
        ai_summary = generate_performance_summary(product_input, perf_record, ab_results, openai_client)

        log_campaign(hubspot_token or "", product_input, newsletters, ab_results)
        progress.progress(100, "Pipeline complete ✓")

        st.session_state.update({
            "blog": blog, "newsletters": newsletters,
            "ab": ab_results, "perf": perf_record,
            "ai_summary": ai_summary, "crm_result": crm_result,
            "send_counts": send_counts, "content_file": str(content_file),
            "product": product_input,
        })

    if "blog" not in st.session_state:
        st.stop()

    product_label = st.session_state.get("product", "")
    cr = st.session_state.get("crm_result", {})
    sc = st.session_state.get("send_counts", {})
    ab = st.session_state.get("ab", {})

    # ── Status strip ──────────────────────────────────────────
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    with col_s1:
        synced = cr.get("success", 0)
        st.markdown(f'<span class="pill-{"success" if synced else "gray"}">{"✔" if synced else "○"} HubSpot: {synced} synced</span>', unsafe_allow_html=True)
    with col_s2:
        st.markdown(f'<span class="pill-success">✉ {sum(sc.values())} queued</span>', unsafe_allow_html=True)
    with col_s3:
        cf = st.session_state.get("content_file", "")
        st.markdown(f'<span class="pill-gray">💾 {Path(cf).name if cf else "—"}</span>', unsafe_allow_html=True)
    with col_s4:
        sig = ab.get("significant", False)
        st.markdown(f'<span class="pill-{"success" if sig else "warn"}">A/B: {"Significant ✓" if sig else "Inconclusive"}</span>', unsafe_allow_html=True)

    # ── Editorial content ─────────────────────────────────────
    st.markdown('<div class="section-title" style="margin-top:12px;">Editorial Content</div>', unsafe_allow_html=True)
    t_blog, t_news = st.tabs(["📖 Blog Post", "✉️ Newsletters"])

    with t_blog:
        st.markdown(st.session_state.blog)

    with t_news:
        cols = st.columns(3, gap="small")
        for col, (key, meta) in zip(cols, PERSONAS.items()):
            with col:
                count = sc.get(key, 0)
                st.markdown(f'<div class="email-label">{meta["label"]} · {count} recipients</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="email-card">{st.session_state.newsletters[key]}</div>', unsafe_allow_html=True)

    # ── A/B Test ──────────────────────────────────────────────
    if ab_data := st.session_state.get("ab"):
        st.markdown('<div class="section-title" style="margin-top:12px;">🧪 A/B Experiment</div>', unsafe_allow_html=True)
        with st.expander("Experiment Design", expanded=True):
            c1, c2 = st.columns(2, gap="medium")
            with c1:
                st.markdown(f"**Objective:** Maximise CTR for *{product_label}* via AI-personalised copy.")
                st.markdown("**Key Result:** >15% CTR lift at p < 0.05 confidence.")
            with c2:
                st.markdown("**Version A (Control):** Craftsmanship & material focus.")
                st.markdown("**Version B (AI-optimised):** Emotional storytelling & lifestyle.")
                st.markdown("**Sample size:** 1,000 per variant.")

        m1, m2, m3, m4 = st.columns(4, gap="small")
        m1.metric("Version A CTR", f"{ab_data['A']:.1%}")
        m2.metric("Version B CTR", f"{ab_data['B']:.1%}", delta=f"{ab_data['lift']:+.1%}")
        m3.metric("Z-statistic",   f"{ab_data['z_stat']:.2f}")
        m4.metric("p-value",       f"{ab_data['p']:.4f}",
                  delta="Significant ✓" if ab_data["significant"] else "Not significant",
                  delta_color="normal" if ab_data["significant"] else "off")

    # ── Performance snapshot ──────────────────────────────────
    if perf := st.session_state.get("perf"):
        st.markdown('<div class="section-title" style="margin-top:12px;">📊 Campaign Performance</div>', unsafe_allow_html=True)
        perf_data = perf["personas"]
        chart_df = pd.DataFrame(
            {p: {"Open Rate": m["open_rate"], "CTR": m["click_rate"]}
             for p, m in perf_data.items()}
        ).T
        p1, p2 = st.columns([1.4, 1], gap="medium")
        with p1:
            st.bar_chart(chart_df, color=["#E6C1B3", "#1a1a1a"])
        with p2:
            for persona, m in perf_data.items():
                st.markdown(f"""
<div style="background:white; border:1px solid #F0EDED; border-radius:8px;
            padding:9px 13px; margin-bottom:6px;
            display:flex; justify-content:space-between; align-items:center;">
    <div style="font-size:11px; color:#888;">{PERSONAS[persona]["label"]}</div>
    <div style="font-size:12px; font-weight:600; color:#1a1a1a;">
        CTR {m['click_rate']:.0%}
        <span style="font-size:11px; color:#27ae60; margin-left:6px;">↑ Open {m['open_rate']:.0%}</span>
    </div>
</div>""", unsafe_allow_html=True)

    # ── AI Summary ────────────────────────────────────────────
    if summary := st.session_state.get("ai_summary"):
        st.markdown('<div class="section-title" style="margin-top:12px;">💡 AI Strategy Insight</div>', unsafe_allow_html=True)
        st.info(summary)


# ═══════════════════════════════════════════════════════════════
#  TAB 2 — HISTORY
# ═══════════════════════════════════════════════════════════════

with tab_history:
    st.markdown('<div class="section-title">Historical Campaign Performance</div>', unsafe_allow_html=True)
    df = load_performance_history()

    if df.empty:
        st.info("No performance data yet. Run at least one pipeline to populate history.")
    else:
        latest = df.sort_values("recorded_at").groupby("persona").last().reset_index()
        st.dataframe(
            latest[["persona", "open_rate", "click_rate", "unsub_rate", "sent"]],
            use_container_width=True, hide_index=True,
        )
        if df["recorded_at"].nunique() > 1:
            st.markdown("**CTR trend over time**")
            pivot = df.pivot_table(index="recorded_at", columns="persona", values="click_rate")
            st.line_chart(pivot)
        with st.expander("Raw performance log"):
            st.dataframe(df, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════
#  TAB 3 — CRM LOG
# ═══════════════════════════════════════════════════════════════

with tab_crm:
    st.markdown('<div class="section-title">Campaign Log</div>', unsafe_allow_html=True)
    history = load_campaign_history()

    if not history:
        st.info("No campaigns logged yet.")
    else:
        for rec in history[:10]:
            with st.expander(
                f"🗂 {rec['campaign_id']}  ·  {rec['product']}  ·  {rec['sent_at'][:10]}",
                expanded=False,
            ):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Version A CTR", f"{rec.get('ab_variant_a_ctr', 0):.1%}")
                c2.metric("Version B CTR", f"{rec.get('ab_variant_b_ctr', 0):.1%}")
                c3.metric("p-value",       f"{rec.get('ab_p_value', 1):.4f}")
                c4.markdown(
                    f'<span class="pill-{"success" if rec.get("hubspot_synced") else "gray"}">'
                    f'HubSpot {"✔ synced" if rec.get("hubspot_synced") else "○ local only"}</span>',
                    unsafe_allow_html=True,
                )
                st.caption(f"Segments sent: {', '.join(rec.get('personas_sent', []))}")

    st.markdown('<div class="section-title" style="margin-top:12px;">Recent Saved Content</div>', unsafe_allow_html=True)
    recent = load_recent_campaigns()
    if not recent:
        st.info("No saved content files found.")
    else:
        for c in recent:
            with st.expander(f"📄 {c['product']}  ·  {c['generated_at'][:10]}"):
                st.markdown(f"**Blog excerpt:** {c['blog'][:300]}…")
                st.caption(f"Newsletters: {list(c['newsletters'].keys())}")