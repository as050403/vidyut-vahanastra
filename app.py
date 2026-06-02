import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# -------------------------------------------------------
# MODULE IMPORTS
# -------------------------------------------------------
from modules.battery_chemistry import run_battery_chemistry_lab
from modules.pack_design import run_pack_design_lab
from modules.charging import run_charging_lab
from modules.range_model import run_range_lab
from modules.scenario_compare import run_scenario_compare
from modules.saved_scenario_compare import run_saved_scenario_compare
from modules.bms_soc import run_bms_soc_lab
from modules.motor_inverter import run_motor_inverter_lab
from modules.thermal_model import run_thermal_lab
from modules.report_generator import run_report_generator
from modules.saved_scenarios import run_saved_scenarios
from modules.scenario_import_export import run_scenario_import_export
from modules.auto_report import run_auto_report_from_saved_scenario
from modules.real_ev_presets import run_real_ev_presets
from modules.scenario_library_filters import run_scenario_library_filters
from modules.scenario_dashboard_analytics import run_scenario_dashboard_analytics
from modules.preset_to_scenario import run_preset_to_scenario

# -------------------------------------------------------
# APP HEALTH CHECK IMPORTS
# -------------------------------------------------------
from utils.app_health import (
    show_health_banner,
    run_app_health_page,
    safe_dataframe_from_equal_lists
)


# -------------------------------------------------------
# UI THEME IMPORTS
# -------------------------------------------------------
from utils.ui_theme import (
    inject_global_css,
    render_sidebar_brand,
    render_hero,
    render_section,
    render_metric_card,
    render_info_card,
    render_footer
)


# -------------------------------------------------------
# PAGE CONFIGURATION
# -------------------------------------------------------
st.set_page_config(
    page_title="Vidyut Vahanastra",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)


# -------------------------------------------------------
# GLOBAL STYLING
# -------------------------------------------------------
inject_global_css()


# -------------------------------------------------------
# SIDEBAR
# -------------------------------------------------------
render_sidebar_brand()
result = show_health_banner()
health_df, health_summary = result if result else (None, None)

page = st.sidebar.radio(
    "Navigation",
    [
    "Home",
    "App Health Check",
    "Real EV Presets",
    "Preset to Saved Scenario",
    "Battery Chemistry Lab",
    "Pack Design Lab",
    "Charging Lab",
    "Range Lab",
    "Scenario Compare",
    "Saved Scenario Compare",
    "BMS & SOC Lab",
    "Motor & Inverter Lab",
    "Thermal Lab",
    "Saved Scenarios",
    "Scenario Search & Filters",
    "Scenario Import / Export",
    "Dashboard Analytics",
    "Report Generator",
    "Auto Report from Scenario"
]
)

st.sidebar.divider()

st.sidebar.markdown("### Project Mode")
project_mode = st.sidebar.selectbox(
    "Select Mode",
    [
        "Learning Mode",
        "Engineering Mode",
        "Industry Demo Mode"
    ]
)

st.sidebar.markdown("### Current Build")
st.sidebar.success("MVP Complete")
st.sidebar.caption("Final MVP Build")


# -------------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------------
def show_header():
    render_hero()


def placeholder_page(title, description, upcoming_features):
    show_header()

    st.markdown(f"## {title}")
    st.info("This module is reserved for a future sprint.")

    render_info_card(
        title,
        description
    )

    st.markdown("### Upcoming Features")

    for feature in upcoming_features:
        st.markdown(f"- {feature}")

    render_footer()


def ev_architecture_diagram():
    labels = [
        "Charger",
        "Battery Pack",
        "BMS",
        "Inverter",
        "Motor",
        "Gearbox",
        "Wheels",
        "Thermal System",
        "Scenario Store",
        "Report Generator"
    ]
 
    source = [
        0, 1, 2, 3, 4, 5,
        7, 7, 7,
        1, 3, 4,
        8, 8
    ]
 
    target = [
        1, 2, 3, 4, 5, 6,
        1, 3, 4,
        8, 8, 8,
        9, 6
    ]
 
    value = [
        1.00, 1.00, 1.00, 1.00, 1.00, 1.00,
        0.18, 0.14, 0.14,
        0.12, 0.12, 0.12,
        0.20, 0.10
    ]
 
    node_colors = [
        "#40C4FF",  # Charger
        "#00E676",  # Battery Pack
        "#FFD54F",  # BMS
        "#FFAB40",  # Inverter
        "#FF5252",  # Motor
        "#7C4DFF",  # Gearbox
        "#18FFFF",  # Wheels
        "#69F0AE",  # Thermal System
        "#B388FF",  # Scenario Store
        "#FFEA00"   # Report Generator
    ]
 
    # ── FIXED node positions (Bug 5) ────────────────────────────────────────
    node_x = [
        0.02,   # Charger
        0.20,   # Battery Pack
        0.34,   # BMS
        0.48,   # Inverter
        0.62,   # Motor
        0.76,   # Gearbox
        0.94,   # Wheels
        0.06,   # Thermal System  ← was 0.02 (shared with Charger)
        0.80,   # Scenario Store  ← was 0.76 (shared with Gearbox)
        0.94    # Report Generator
    ]
 
    node_y = [
        0.20,   # Charger
        0.28,   # Battery Pack
        0.36,   # BMS
        0.42,   # Inverter
        0.42,   # Motor
        0.20,   # Gearbox
        0.20,   # Wheels
        0.72,   # Thermal System
        0.70,   # Scenario Store
        0.78    # Report Generator  ← was 0.72 (shared with Scenario Store)
    ]
 
    fig = go.Figure(
        data=[
            go.Sankey(
                arrangement="fixed",
                node=dict(
                    pad=22,
                    thickness=18,
                    line=dict(
                        color="rgba(230,241,255,0.45)",
                        width=0.8
                    ),
                    label=labels,
                    x=node_x,
                    y=node_y,
                    color=node_colors,
                    hovertemplate="%{label}<extra></extra>"
                ),
                link=dict(
                    source=source,
                    target=target,
                    value=value,
                    color=[
                        "rgba(0,230,118,0.30)",
                        "rgba(0,230,118,0.30)",
                        "rgba(0,230,118,0.30)",
                        "rgba(0,230,118,0.30)",
                        "rgba(0,230,118,0.30)",
                        "rgba(0,230,118,0.30)",
                        "rgba(105,240,174,0.20)",
                        "rgba(105,240,174,0.20)",
                        "rgba(105,240,174,0.20)",
                        "rgba(179,136,255,0.18)",
                        "rgba(179,136,255,0.18)",
                        "rgba(179,136,255,0.18)",
                        "rgba(255,234,0,0.22)",
                        "rgba(255,234,0,0.16)"
                    ],
                    hovertemplate="Flow strength: %{value}<extra></extra>"
                )
            )
        ]
    )
 
    fig.update_layout(
        title=dict(
            text="EV Digital Twin Energy, Control, Thermal, Scenario, and Report Flow",
            x=0.02,
            xanchor="left",
            font=dict(size=16, color="#E6F1FF")
        ),
        font=dict(
            size=12,
            color="#E6F1FF"
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=560,
        margin=dict(l=20, r=30, t=70, b=35)
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# -------------------------------------------------------
# HOME PAGE
# -------------------------------------------------------
if page == "Home":
    show_header()


    left, right = st.columns([1.35, 1])

    with left:
        render_info_card(
            "Project Vision",
            (
                "Vidyut Vahanastra is designed as a virtual EV engineering bench where users can "
                "experiment with battery chemistry, pack sizing, SOC estimation, BMS protection, "
                "motor selection, inverter losses, charging behavior, vehicle range, thermal management, "
                "scenario storage, and automated report generation."
            )
        )

        render_section(
            "Dashboard Architecture",
            "Energy, control, charging, thermal, scenario, and reporting flow across the EV digital twin."
        )

        ev_architecture_diagram()

    with right:
        render_info_card(
            "What the Dashboard Does",
            (
                "Compare LFP, NMC, NCA, and LTO batteries; design 48 V, 400 V, and 800 V packs; "
                "simulate SOC drift and correction; estimate charging time and CC-CV taper; "
                "predict range under Indian driving conditions; compare motor and inverter technologies; "
                "estimate battery, motor, and inverter temperatures; save scenarios; and generate reports."
            )
        )


    st.divider()

    render_section(
        "Industry Workflow",
        "The platform supports a full engineering loop from design input to report export."
    )

    w1, w2, w3, w4 = st.columns(4)

    with w1:
        render_info_card(
            "1. Design",
            (
                "Select chemistry, pack architecture, charger power, vehicle parameters, motor type, "
                "inverter device, and thermal limits."
            )
        )

    with w2:
        render_info_card(
            "2. Simulate",
            (
                "Run subsystem models for charging, range, BMS/SOC, motor-inverter behavior, "
                "and thermal response."
            )
        )

    with w3:
        render_info_card(
            "3. Compare",
            (
                "Compare EV scenarios using range, Wh/km, charging time, pack mass, voltage class, "
                "and safety indicators."
            )
        )

    with w4:
        render_info_card(
            "4. Report",
            (
                "Save scenarios locally and generate PDF, Markdown, CSV, and JSON reports "
                "for review or presentation."
            )
        )

    st.divider()

    render_section(
        "Recommended Demo Flow"
    )

    demo_flow = pd.DataFrame(
        {
            "Step": [
                "1",
                "2",
                "3",
                "4",
                "5",
                "6",
                "7"
            ],
            "Page": [
                "Battery Chemistry Lab",
                "Pack Design Lab",
                "Charging Lab",
                "Range Lab",
                "Scenario Compare",
                "Saved Scenarios",
                "Auto Report from Scenario"
            ],
            "Demo Purpose": [
                "Show LFP vs NMC/NCA/LTO tradeoff",
                "Build 400 V or 800 V EV battery pack",
                "Show 10–80% charging and taper effect",
                "Show Indian driving-condition range effect",
                "Compare two EV architectures",
                "Save selected EV design case",
                "Generate professional engineering report"
            ]
        }
    )

    st.dataframe(
        demo_flow,
        use_container_width=True,
        hide_index=True
    )

    render_footer()


# -------------------------------------------------------
# REAL EV PRESETS
# -------------------------------------------------------
elif page == "Real EV Presets":
    run_real_ev_presets()


# -------------------------------------------------------
# BATTERY CHEMISTRY LAB
# -------------------------------------------------------
elif page == "Battery Chemistry Lab":
    run_battery_chemistry_lab()


# -------------------------------------------------------
# PACK DESIGN LAB
# -------------------------------------------------------
elif page == "Pack Design Lab":
    run_pack_design_lab()


# -------------------------------------------------------
# CHARGING LAB
# -------------------------------------------------------
elif page == "Charging Lab":
    run_charging_lab()


# -------------------------------------------------------
# RANGE LAB
# -------------------------------------------------------
elif page == "Range Lab":
    run_range_lab()


# -------------------------------------------------------
# SCENARIO COMPARE
# -------------------------------------------------------
elif page == "Scenario Compare":
    run_scenario_compare()


# -------------------------------------------------------
# BMS & SOC LAB
# -------------------------------------------------------
elif page == "BMS & SOC Lab":
    run_bms_soc_lab()


# -------------------------------------------------------
# MOTOR & INVERTER LAB
# -------------------------------------------------------
elif page == "Motor & Inverter Lab":
    run_motor_inverter_lab()


# -------------------------------------------------------
# THERMAL LAB
# -------------------------------------------------------
elif page == "Thermal Lab":
    run_thermal_lab()


# -------------------------------------------------------
# SAVED SCENARIOS
# -------------------------------------------------------
elif page == "Saved Scenarios":
    run_saved_scenarios()

# -------------------------------------------------------
# SAVED SCENARIO COMPARE
# -------------------------------------------------------
elif page == "Saved Scenario Compare":
    run_saved_scenario_compare()

# -------------------------------------------------------
# SCENARIO IMPORT / EXPORT
# -------------------------------------------------------
elif page == "Scenario Import / Export":
    run_scenario_import_export()


# -------------------------------------------------------
# REPORT GENERATOR
# -------------------------------------------------------
elif page == "Report Generator":
    run_report_generator()


# -------------------------------------------------------
# AUTO REPORT FROM SCENARIO
# -------------------------------------------------------
elif page == "Auto Report from Scenario":
    run_auto_report_from_saved_scenario()


# -------------------------------------------------------
# SCENARIO LIBRARY FILTERS
# -------------------------------------------------------
elif page == "Scenario Search & Filters":
    run_scenario_library_filters()

# -------------------------------------------------------
# DASHBOARD ANALYTICS
# -------------------------------------------------------
elif page == "Dashboard Analytics":
    run_scenario_dashboard_analytics()

# -------------------------------------------------------
# PRESET TO SCENARIO
# -------------------------------------------------------
elif page == "Preset to Saved Scenario":
    run_preset_to_scenario()

# -------------------------------------------------------
# APP HEALTH CHECK
# -------------------------------------------------------
elif page == "App Health Check":
    run_app_health_page()


# -------------------------------------------------------
# FALLBACK
# -------------------------------------------------------
else:
    placeholder_page(
        "Module Not Found",
        "The selected module is not available in the current build.",
        [
            "Check sidebar page name",
            "Check module imports",
            "Restart Streamlit app"
        ]
    )