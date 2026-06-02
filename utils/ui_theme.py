from pathlib import Path
import streamlit as st


LOGO_PATH = Path("assets/vidyut_logo.svg")


def inject_global_css():
    st.markdown(
        """
        <style>
        :root {
            --vv-bg: #050B12;
            --vv-card: #0B1622;
            --vv-card-2: #0F1E2E;
            --vv-green: #00E676;
            --vv-green-soft: rgba(0, 230, 118, 0.12);
            --vv-blue: #40C4FF;
            --vv-yellow: #FFD54F;
            --vv-red: #FF5252;
            --vv-text: #E6F1FF;
            --vv-muted: #90A4AE;
            --vv-border: rgba(148, 163, 184, 0.20);
        }

        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 3rem;
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #06111D 0%, #050B12 100%);
            border-right: 1px solid rgba(148, 163, 184, 0.18);
        }

        .vv-hero {
            background:
                radial-gradient(circle at top left, rgba(0, 230, 118, 0.20), transparent 32%),
                linear-gradient(135deg, #07131F 0%, #0B1622 52%, #07131F 100%);
            border: 1px solid var(--vv-border);
            border-radius: 24px;
            padding: 30px 32px;
            margin-bottom: 22px;
            box-shadow: 0 18px 55px rgba(0, 0, 0, 0.28);
        }

        .vv-title {
            font-size: 48px;
            line-height: 1.04;
            font-weight: 850;
            letter-spacing: -0.04em;
            color: var(--vv-text);
            margin-bottom: 6px;
        }

        .vv-title span {
            color: var(--vv-green);
        }

        .vv-subtitle {
            font-size: 18px;
            color: var(--vv-muted);
            max-width: 980px;
            margin-top: 8px;
            margin-bottom: 20px;
        }

        .vv-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 16px;
        }

        .vv-chip {
            background: var(--vv-green-soft);
            color: var(--vv-green);
            border: 1px solid rgba(0, 230, 118, 0.28);
            padding: 7px 12px;
            border-radius: 999px;
            font-size: 13px;
            font-weight: 700;
        }

        .vv-card {
            background: linear-gradient(180deg, var(--vv-card) 0%, #08121E 100%);
            border: 1px solid var(--vv-border);
            border-radius: 18px;
            padding: 20px;
            margin-bottom: 16px;
            box-shadow: 0 10px 28px rgba(0, 0, 0, 0.22);
        }

        .vv-card-title {
            font-size: 19px;
            font-weight: 800;
            color: var(--vv-text);
            margin-bottom: 8px;
        }

        .vv-card-text {
            font-size: 14px;
            color: var(--vv-muted);
            line-height: 1.55;
        }

        .vv-metric {
            background: linear-gradient(145deg, #0B1622 0%, #0F1E2E 100%);
            border: 1px solid var(--vv-border);
            border-radius: 18px;
            padding: 18px;
            min-height: 120px;
        }

        .vv-metric-label {
            font-size: 13px;
            color: var(--vv-muted);
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }

        .vv-metric-value {
            font-size: 28px;
            font-weight: 850;
            color: var(--vv-text);
            margin-top: 8px;
        }

        .vv-metric-note {
            font-size: 13px;
            color: var(--vv-green);
            margin-top: 6px;
        }

        .vv-section-title {
            font-size: 25px;
            font-weight: 850;
            color: var(--vv-text);
            margin-top: 16px;
            margin-bottom: 8px;
        }

        .vv-section-caption {
            color: var(--vv-muted);
            font-size: 15px;
            margin-bottom: 18px;
        }

        .vv-status {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 800;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            border: 1px solid rgba(0, 230, 118, 0.32);
            background: rgba(0, 230, 118, 0.10);
            color: var(--vv-green);
        }

        .vv-footer {
            border-top: 1px solid var(--vv-border);
            color: var(--vv-muted);
            font-size: 13px;
            margin-top: 36px;
            padding-top: 16px;
            text-align: center;
        }

        div[data-testid="stMetric"] {
            background: linear-gradient(145deg, #0B1622, #0F1E2E);
            border: 1px solid rgba(148, 163, 184, 0.18);
            padding: 16px;
            border-radius: 16px;
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 16px;
            overflow: hidden;
        }

        button[kind="primary"], div.stButton > button {
            border-radius: 999px;
            border: 1px solid rgba(0, 230, 118, 0.35);
            background: linear-gradient(135deg, #00C853, #00E676);
            color: #04110A;
            font-weight: 800;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def render_sidebar_brand():
    if LOGO_PATH.exists():
        st.sidebar.image(str(LOGO_PATH), use_container_width=True)

    st.sidebar.markdown(
        """
        <div style="
            background: rgba(0, 230, 118, 0.08);
            border: 1px solid rgba(0, 230, 118, 0.20);
            border-radius: 16px;
            padding: 14px;
            margin-bottom: 14px;
        ">
            <div style="font-weight: 800; color: #E6F1FF;">EV Digital Twin</div>
            <div style="font-size: 13px; color: #90A4AE; margin-top: 4px;">
                Battery • BMS • Charging • Range • Powertrain • Thermal
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_hero():
    st.markdown(
        """
        <div class="vv-hero">
            <div class="vv-status">MVP Complete • Industry Hardening Active</div>
            <div class="vv-title">Vidyut <span>Vahanastra</span></div>
            <div class="vv-subtitle">
                An India-focused EV digital twin dashboard for battery chemistry, pack design, BMS/SOC,
                charging, range, motor-inverter analysis, thermal management, scenario storage, and automated reports.
            </div>
            <div class="vv-chip-row">
                <div class="vv-chip">Battery Digital Twin</div>
                <div class="vv-chip">BMS Logic</div>
                <div class="vv-chip">CC-CV Charging</div>
                <div class="vv-chip">Range Estimation</div>
                <div class="vv-chip">Motor-Inverter</div>
                <div class="vv-chip">Thermal Derating</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_section(title, caption=None):
    caption_html = f'<div class="vv-section-caption">{caption}</div>' if caption else ""
    st.markdown(
        f"""
        <div class="vv-section-title">{title}</div>
        {caption_html}
        """,
        unsafe_allow_html=True
    )


def render_metric_card(label, value, note=""):
    st.markdown(
        f"""
        <div class="vv-metric">
            <div class="vv-metric-label">{label}</div>
            <div class="vv-metric-value">{value}</div>
            <div class="vv-metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_info_card(title, text):
    st.markdown(
        f"""
        <div class="vv-card">
            <div class="vv-card-title">{title}</div>
            <div class="vv-card-text">{text}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_footer():
    st.markdown(
        """
        <div class="vv-footer">
            Vidyut Vahanastra • Interactive EV Digital Twin Dashboard • Built for EV systems experimentation
        </div>
        """,
        unsafe_allow_html=True
    )