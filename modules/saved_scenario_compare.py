import json
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.scenario_store import (
    list_scenarios,
    get_scenario_by_id
)


# -------------------------------------------------------
# SAFE VALUE HELPERS
# -------------------------------------------------------
def get_nested(payload, section, key, default="-"):
    try:
        return payload.get(section, {}).get(key, default)
    except Exception:
        return default


def to_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return float(default)


def make_scenario_label(row, columns):
    row_dict = dict(zip(columns, row))
    scenario_id = row_dict.get("ID", "-")
    name = row_dict.get("Scenario Name", "Unnamed Scenario")
    chemistry = row_dict.get("Chemistry", "-")
    pack_energy = row_dict.get("Pack Energy (kWh)", "-")
    created_at = row_dict.get("Created At", "-")

    return f"{scenario_id} | {name} | {chemistry} | {pack_energy} kWh | {created_at}"


def scenario_id_from_label(label):
    try:
        return int(str(label).split("|")[0].strip())
    except Exception:
        return None


# -------------------------------------------------------
# EXTRACT SCENARIO SUMMARY
# -------------------------------------------------------
def extract_scenario_summary(payload, scenario_label):
    summary = {
        "Scenario Label": scenario_label,

        "Scenario Name": get_nested(
            payload,
            "Scenario Metadata",
            "Scenario Name",
            "Unnamed Scenario"
        ),

        "Vehicle Segment": get_nested(
            payload,
            "Scenario Metadata",
            "Vehicle Segment",
            "-"
        ),

        "Chemistry": get_nested(
            payload,
            "Battery Pack",
            "Chemistry",
            "-"
        ),

        "Nominal Pack Voltage (V)": to_float(
            get_nested(payload, "Battery Pack", "Nominal Pack Voltage (V)", 0)
        ),

        "Pack Energy (kWh)": to_float(
            get_nested(payload, "Battery Pack", "Pack Energy (kWh)", 0)
        ),

        "Pack Capacity (Ah)": to_float(
            get_nested(payload, "Battery Pack", "Pack Capacity (Ah)", 0)
        ),

        "Total Cells": to_float(
            get_nested(payload, "Battery Pack", "Total Cells", 0)
        ),

        "Estimated Pack Mass (kg)": to_float(
            get_nested(payload, "Battery Pack", "Estimated Pack Mass (kg)", 0)
        ),

        "Charger Power (kW)": to_float(
            get_nested(payload, "Charging", "Charger Power (kW)", 0)
        ),

        "Charging Time (min)": to_float(
            get_nested(payload, "Charging", "Charging Time (min)", 0)
        ),

        "Charging Cost (₹)": to_float(
            get_nested(payload, "Charging", "Charging Cost (₹)", 0)
        ),

        "Estimated Range (km)": to_float(
            get_nested(payload, "Range", "Estimated Range (km)", 0)
        ),

        "Energy Consumption (Wh/km)": to_float(
            get_nested(payload, "Range", "Energy Consumption (Wh/km)", 0)
        ),

        "SOC Estimation Method": get_nested(
            payload,
            "BMS and SOC",
            "SOC Estimation Method",
            "-"
        ),

        "Maximum SOC Error (%)": to_float(
            get_nested(payload, "BMS and SOC", "Maximum SOC Error (%)", 0)
        ),

        "Motor Type": get_nested(
            payload,
            "Motor and Inverter",
            "Motor Type",
            "-"
        ),

        "Peak Motor Power (kW)": to_float(
            get_nested(payload, "Motor and Inverter", "Peak Motor Power (kW)", 0)
        ),

        "Inverter Device": get_nested(
            payload,
            "Motor and Inverter",
            "Inverter Device",
            "-"
        ),

        "Inverter Efficiency (%)": to_float(
            get_nested(payload, "Motor and Inverter", "Inverter Efficiency (%)", 0)
        ),

        "Maximum Battery Temperature (°C)": to_float(
            get_nested(payload, "Thermal", "Maximum Battery Temperature (°C)", 0)
        ),

        "Maximum Motor Temperature (°C)": to_float(
            get_nested(payload, "Thermal", "Maximum Motor Temperature (°C)", 0)
        ),

        "Maximum Inverter Temperature (°C)": to_float(
            get_nested(payload, "Thermal", "Maximum Inverter Temperature (°C)", 0)
        ),

        "Remarks": get_nested(
            payload,
            "Engineering Remarks",
            "Remarks",
            "-"
        )
    }

    return summary


# -------------------------------------------------------
# COMPARISON TABLES
# -------------------------------------------------------
def create_comparison_dataframe(summary_a, summary_b):
    metrics = [
        "Scenario Name",
        "Vehicle Segment",
        "Chemistry",
        "Nominal Pack Voltage (V)",
        "Pack Energy (kWh)",
        "Pack Capacity (Ah)",
        "Total Cells",
        "Estimated Pack Mass (kg)",
        "Charger Power (kW)",
        "Charging Time (min)",
        "Charging Cost (₹)",
        "Estimated Range (km)",
        "Energy Consumption (Wh/km)",
        "SOC Estimation Method",
        "Maximum SOC Error (%)",
        "Motor Type",
        "Peak Motor Power (kW)",
        "Inverter Device",
        "Inverter Efficiency (%)",
        "Maximum Battery Temperature (°C)",
        "Maximum Motor Temperature (°C)",
        "Maximum Inverter Temperature (°C)",
        "Remarks"
    ]

    rows = []

    for metric in metrics:
        a_val = summary_a.get(metric, "-")
        b_val = summary_b.get(metric, "-")

        if isinstance(a_val, float):
            a_val = round(a_val, 3)

        if isinstance(b_val, float):
            b_val = round(b_val, 3)

        rows.append(
            {
                "Metric": metric,
                "Scenario A": a_val,
                "Scenario B": b_val
            }
        )

    return pd.DataFrame(rows)


def create_difference_dataframe(summary_a, summary_b):
    numeric_metrics = [
        "Nominal Pack Voltage (V)",
        "Pack Energy (kWh)",
        "Pack Capacity (Ah)",
        "Total Cells",
        "Estimated Pack Mass (kg)",
        "Charger Power (kW)",
        "Charging Time (min)",
        "Charging Cost (₹)",
        "Estimated Range (km)",
        "Energy Consumption (Wh/km)",
        "Maximum SOC Error (%)",
        "Peak Motor Power (kW)",
        "Inverter Efficiency (%)",
        "Maximum Battery Temperature (°C)",
        "Maximum Motor Temperature (°C)",
        "Maximum Inverter Temperature (°C)"
    ]

    rows = []

    for metric in numeric_metrics:
        a_val = to_float(summary_a.get(metric, 0))
        b_val = to_float(summary_b.get(metric, 0))
        diff = b_val - a_val

        rows.append(
            {
                "Metric": metric,
                "Scenario A": round(a_val, 3),
                "Scenario B": round(b_val, 3),
                "Difference B - A": round(diff, 3),
                "Absolute Difference": round(abs(diff), 3)
            }
        )

    return pd.DataFrame(rows)


def create_winner_dataframe(summary_a, summary_b):
    rows = []

    range_a = to_float(summary_a.get("Estimated Range (km)", 0))
    range_b = to_float(summary_b.get("Estimated Range (km)", 0))

    charge_a = to_float(summary_a.get("Charging Time (min)", 0))
    charge_b = to_float(summary_b.get("Charging Time (min)", 0))

    wh_a = to_float(summary_a.get("Energy Consumption (Wh/km)", 0))
    wh_b = to_float(summary_b.get("Energy Consumption (Wh/km)", 0))

    mass_a = to_float(summary_a.get("Estimated Pack Mass (kg)", 0))
    mass_b = to_float(summary_b.get("Estimated Pack Mass (kg)", 0))

    temp_a = to_float(summary_a.get("Maximum Battery Temperature (°C)", 0))
    temp_b = to_float(summary_b.get("Maximum Battery Temperature (°C)", 0))

    soc_error_a = to_float(summary_a.get("Maximum SOC Error (%)", 0))
    soc_error_b = to_float(summary_b.get("Maximum SOC Error (%)", 0))

    def winner_high(a, b):
        if a > b:
            return "Scenario A"
        if b > a:
            return "Scenario B"
        return "Tie"

    def winner_low(a, b):
        if a < b:
            return "Scenario A"
        if b < a:
            return "Scenario B"
        return "Tie"

    rows.append(
        {
            "Category": "Range",
            "Winner": winner_high(range_a, range_b),
            "Reason": "Higher estimated range is preferred."
        }
    )

    rows.append(
        {
            "Category": "Charging",
            "Winner": winner_low(charge_a, charge_b),
            "Reason": "Lower charging time is preferred."
        }
    )

    rows.append(
        {
            "Category": "Energy Efficiency",
            "Winner": winner_low(wh_a, wh_b),
            "Reason": "Lower Wh/km is preferred."
        }
    )

    rows.append(
        {
            "Category": "Pack Mass",
            "Winner": winner_low(mass_a, mass_b),
            "Reason": "Lower estimated pack mass is preferred."
        }
    )

    rows.append(
        {
            "Category": "Battery Thermal Stress",
            "Winner": winner_low(temp_a, temp_b),
            "Reason": "Lower maximum battery temperature is preferred."
        }
    )

    rows.append(
        {
            "Category": "SOC Estimation Accuracy",
            "Winner": winner_low(soc_error_a, soc_error_b),
            "Reason": "Lower maximum SOC error is preferred."
        }
    )

    return pd.DataFrame(rows)


# -------------------------------------------------------
# CHARTS
# -------------------------------------------------------
def create_metric_bar_chart(summary_a, summary_b, metric, title, y_axis):
    a_val = to_float(summary_a.get(metric, 0))
    b_val = to_float(summary_b.get(metric, 0))

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=["Scenario A", "Scenario B"],
            y=[a_val, b_val],
            text=[round(a_val, 2), round(b_val, 2)],
            textposition="auto"
        )
    )

    fig.update_layout(
        title=title,
        xaxis_title="Scenario",
        yaxis_title=y_axis,
        height=420
    )

    return fig


def create_multi_metric_chart(summary_a, summary_b):
    metrics = [
        "Pack Energy (kWh)",
        "Estimated Range (km)",
        "Charging Time (min)",
        "Energy Consumption (Wh/km)",
        "Estimated Pack Mass (kg)"
    ]

    scenario_a_values = [
        to_float(summary_a.get(metric, 0))
        for metric in metrics
    ]

    scenario_b_values = [
        to_float(summary_b.get(metric, 0))
        for metric in metrics
    ]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=metrics,
            y=scenario_a_values,
            name="Scenario A",
            text=[round(v, 2) for v in scenario_a_values],
            textposition="auto"
        )
    )

    fig.add_trace(
        go.Bar(
            x=metrics,
            y=scenario_b_values,
            name="Scenario B",
            text=[round(v, 2) for v in scenario_b_values],
            textposition="auto"
        )
    )

    fig.update_layout(
        title="Key Metric Comparison",
        xaxis_title="Metric",
        yaxis_title="Value",
        barmode="group",
        height=500
    )

    return fig


# -------------------------------------------------------
# MAIN PAGE
# -------------------------------------------------------
def run_saved_scenario_compare():
    st.markdown("# Saved Scenario Compare")
    st.caption("Compare two saved EV design scenarios directly from the local scenario database.")

    st.info(
        "Select two saved scenarios from the database. The page extracts battery, charging, range, BMS, motor-inverter, and thermal values for direct comparison."
    )

    rows, columns = list_scenarios()

    if not rows:
        st.warning("No saved scenarios found. First create and save scenarios from the Saved Scenarios page.")
        return

    if len(rows) < 2:
        st.warning("At least two saved scenarios are required for comparison.")
        return

    labels = [
        make_scenario_label(row, columns)
        for row in rows
    ]

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "Select Scenarios",
            "Comparison Table",
            "Visual Comparison",
            "Decision Summary"
        ]
    )

    with tab1:
        st.markdown("## Select Two Scenarios")

        col1, col2 = st.columns(2)

        with col1:
            selected_label_a = st.selectbox(
                "Select Scenario A",
                options=labels,
                index=0
            )

        with col2:
            selected_label_b = st.selectbox(
                "Select Scenario B",
                options=labels,
                index=1
            )

        scenario_id_a = scenario_id_from_label(selected_label_a)
        scenario_id_b = scenario_id_from_label(selected_label_b)

        if scenario_id_a == scenario_id_b:
            st.error("Scenario A and Scenario B must be different.")
            return

        payload_a = get_scenario_by_id(scenario_id_a)
        payload_b = get_scenario_by_id(scenario_id_b)

        if payload_a is None or payload_b is None:
            st.error("Could not load one or both selected scenarios.")
            return

        st.session_state["saved_compare_payload_a"] = payload_a
        st.session_state["saved_compare_payload_b"] = payload_b
        st.session_state["saved_compare_label_a"] = selected_label_a
        st.session_state["saved_compare_label_b"] = selected_label_b

        st.success("Scenarios loaded for comparison.")

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("### Scenario A Raw JSON")
            st.json(payload_a)

        with col_b:
            st.markdown("### Scenario B Raw JSON")
            st.json(payload_b)

    payload_a = st.session_state.get("saved_compare_payload_a", None)
    payload_b = st.session_state.get("saved_compare_payload_b", None)

    label_a = st.session_state.get("saved_compare_label_a", "Scenario A")
    label_b = st.session_state.get("saved_compare_label_b", "Scenario B")

    if payload_a is None or payload_b is None:
        st.warning("Select scenarios first.")
        return

    summary_a = extract_scenario_summary(payload_a, label_a)
    summary_b = extract_scenario_summary(payload_b, label_b)

    comparison_df = create_comparison_dataframe(summary_a, summary_b)
    difference_df = create_difference_dataframe(summary_a, summary_b)
    winner_df = create_winner_dataframe(summary_a, summary_b)

    with tab2:
        st.markdown("## Full Scenario Comparison")

        st.dataframe(
            comparison_df,
            use_container_width=True,
            hide_index=True
        )

        st.markdown("## Numeric Difference Table")

        st.dataframe(
            difference_df,
            use_container_width=True,
            hide_index=True
        )

        csv_data = comparison_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download Comparison CSV",
            data=csv_data,
            file_name="vidyut_vahanastra_saved_scenario_comparison.csv",
            mime="text/csv"
        )

    with tab3:
        st.markdown("## Visual Comparison")

        st.plotly_chart(
            create_multi_metric_chart(summary_a, summary_b),
            use_container_width=True
        )

        c1, c2 = st.columns(2)

        with c1:
            st.plotly_chart(
                create_metric_bar_chart(
                    summary_a,
                    summary_b,
                    metric="Estimated Range (km)",
                    title="Estimated Range",
                    y_axis="Range (km)"
                ),
                use_container_width=True
            )

        with c2:
            st.plotly_chart(
                create_metric_bar_chart(
                    summary_a,
                    summary_b,
                    metric="Charging Time (min)",
                    title="Charging Time",
                    y_axis="Time (min)"
                ),
                use_container_width=True
            )

        c3, c4 = st.columns(2)

        with c3:
            st.plotly_chart(
                create_metric_bar_chart(
                    summary_a,
                    summary_b,
                    metric="Energy Consumption (Wh/km)",
                    title="Energy Consumption",
                    y_axis="Wh/km"
                ),
                use_container_width=True
            )

        with c4:
            st.plotly_chart(
                create_metric_bar_chart(
                    summary_a,
                    summary_b,
                    metric="Estimated Pack Mass (kg)",
                    title="Estimated Pack Mass",
                    y_axis="Mass (kg)"
                ),
                use_container_width=True
            )

    with tab4:
        st.markdown("## Decision Summary")

        st.dataframe(
            winner_df,
            use_container_width=True,
            hide_index=True
        )

        st.markdown("## Engineering Interpretation")

        range_winner = winner_df[winner_df["Category"] == "Range"]["Winner"].iloc[0]
        charging_winner = winner_df[winner_df["Category"] == "Charging"]["Winner"].iloc[0]
        efficiency_winner = winner_df[winner_df["Category"] == "Energy Efficiency"]["Winner"].iloc[0]

        st.write(
            f"""
            **Range Winner:** {range_winner}  
            **Charging Winner:** {charging_winner}  
            **Efficiency Winner:** {efficiency_winner}
            """
        )

        st.warning(
            "This comparison is based on saved scenario values. If the saved scenario values were manually entered, verify them before using this output in a formal report."
        )