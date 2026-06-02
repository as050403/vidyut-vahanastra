import json
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.scenario_store import (
    list_scenarios,
    get_scenario_by_id
)


# -------------------------------------------------------
# DATA LOADING
# -------------------------------------------------------
def load_scenario_analytics_dataframe():
    rows, columns = list_scenarios()

    if not rows:
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(rows, columns=columns)

    numeric_columns = [
        "Pack Voltage (V)",
        "Pack Energy (kWh)",
        "Estimated Range (km)",
        "Charging Time (min)",
        "Wh/km"
    ]

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    if "Created At" in df.columns:
        df["Created At Parsed"] = pd.to_datetime(
            df["Created At"],
            errors="coerce"
        )

        df["Created Date"] = df["Created At Parsed"].dt.date

    return df


def get_nested(payload, section, key, default="-"):
    try:
        return payload.get(section, {}).get(key, default)
    except Exception:
        return default


def add_extended_fields_from_json(df):
    """
    Adds optional extended fields by reading saved scenario JSON.
    This allows analytics to use motor/inverter/BMS/thermal fields if available.
    """

    if df.empty:
        return df

    records = []

    for _, row in df.iterrows():
        scenario_id = int(row["ID"])
        payload = get_scenario_by_id(scenario_id)

        if payload is None:
            records.append({})
            continue

        records.append(
            {
                "SOC Method": get_nested(
                    payload,
                    "BMS and SOC",
                    "SOC Estimation Method",
                    "-"
                ),
                "Max SOC Error (%)": get_nested(
                    payload,
                    "BMS and SOC",
                    "Maximum SOC Error (%)",
                    0
                ),
                "Motor Type": get_nested(
                    payload,
                    "Motor and Inverter",
                    "Motor Type",
                    "-"
                ),
                "Peak Motor Power (kW)": get_nested(
                    payload,
                    "Motor and Inverter",
                    "Peak Motor Power (kW)",
                    0
                ),
                "Inverter Device": get_nested(
                    payload,
                    "Motor and Inverter",
                    "Inverter Device",
                    "-"
                ),
                "Inverter Efficiency (%)": get_nested(
                    payload,
                    "Motor and Inverter",
                    "Inverter Efficiency (%)",
                    0
                ),
                "Max Battery Temperature (°C)": get_nested(
                    payload,
                    "Thermal",
                    "Maximum Battery Temperature (°C)",
                    0
                ),
                "Max Motor Temperature (°C)": get_nested(
                    payload,
                    "Thermal",
                    "Maximum Motor Temperature (°C)",
                    0
                ),
                "Max Inverter Temperature (°C)": get_nested(
                    payload,
                    "Thermal",
                    "Maximum Inverter Temperature (°C)",
                    0
                )
            }
        )

    extended_df = pd.DataFrame(records)

    if extended_df.empty:
        return df

    combined = pd.concat(
        [
            df.reset_index(drop=True),
            extended_df.reset_index(drop=True)
        ],
        axis=1
    )

    extended_numeric = [
        "Max SOC Error (%)",
        "Peak Motor Power (kW)",
        "Inverter Efficiency (%)",
        "Max Battery Temperature (°C)",
        "Max Motor Temperature (°C)",
        "Max Inverter Temperature (°C)"
    ]

    for col in extended_numeric:
        if col in combined.columns:
            combined[col] = pd.to_numeric(combined[col], errors="coerce").fillna(0)

    return combined


# -------------------------------------------------------
# SUMMARY METRICS
# -------------------------------------------------------
def create_dashboard_summary(df):
    if df.empty:
        return {
            "total_scenarios": 0,
            "unique_chemistries": 0,
            "avg_pack_energy": 0,
            "avg_range": 0,
            "best_range": 0,
            "avg_wh_per_km": 0,
            "avg_charging_time": 0
        }

    return {
        "total_scenarios": len(df),
        "unique_chemistries": df["Chemistry"].nunique() if "Chemistry" in df.columns else 0,
        "avg_pack_energy": df["Pack Energy (kWh)"].mean() if "Pack Energy (kWh)" in df.columns else 0,
        "avg_range": df["Estimated Range (km)"].mean() if "Estimated Range (km)" in df.columns else 0,
        "best_range": df["Estimated Range (km)"].max() if "Estimated Range (km)" in df.columns else 0,
        "avg_wh_per_km": df["Wh/km"].mean() if "Wh/km" in df.columns else 0,
        "avg_charging_time": df["Charging Time (min)"].mean() if "Charging Time (min)" in df.columns else 0
    }


# -------------------------------------------------------
# CHART HELPERS
# -------------------------------------------------------
def create_pie_chart(df, column, title):
    if df.empty or column not in df.columns:
        return None

    counts = df[column].fillna("Unknown").astype(str).value_counts()

    fig = go.Figure(
        data=[
            go.Pie(
                labels=counts.index,
                values=counts.values,
                hole=0.38
            )
        ]
    )

    fig.update_layout(
        title=title,
        height=430
    )

    return fig


def create_bar_count_chart(df, column, title, x_title, y_title):
    if df.empty or column not in df.columns:
        return None

    counts = (
        df[column]
        .fillna("Unknown")
        .astype(str)
        .value_counts()
        .reset_index()
    )

    counts.columns = [column, "Count"]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=counts[column],
            y=counts["Count"],
            text=counts["Count"],
            textposition="auto"
        )
    )

    fig.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis_title=y_title,
        height=430
    )

    return fig


def create_histogram(df, column, title, x_title):
    if df.empty or column not in df.columns:
        return None

    fig = go.Figure()

    fig.add_trace(
        go.Histogram(
            x=df[column],
            nbinsx=12,
            name=column
        )
    )

    fig.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis_title="Scenario Count",
        height=430
    )

    return fig


def create_range_vs_energy_scatter(df):
    if df.empty:
        return None

    required = [
        "Pack Energy (kWh)",
        "Estimated Range (km)",
        "Chemistry",
        "Scenario Name"
    ]

    for col in required:
        if col not in df.columns:
            return None

    fig = go.Figure()

    chemistries = sorted(df["Chemistry"].fillna("Unknown").astype(str).unique())

    for chemistry in chemistries:
        sub = df[df["Chemistry"].astype(str) == chemistry]

        fig.add_trace(
            go.Scatter(
                x=sub["Pack Energy (kWh)"],
                y=sub["Estimated Range (km)"],
                mode="markers",
                name=chemistry,
                text=sub["Scenario Name"],
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "Pack Energy: %{x:.2f} kWh<br>"
                    "Range: %{y:.1f} km<br>"
                    "<extra></extra>"
                ),
                marker=dict(
                    size=12,
                    opacity=0.78
                )
            )
        )

    fig.update_layout(
        title="Estimated Range vs Pack Energy",
        xaxis_title="Pack Energy (kWh)",
        yaxis_title="Estimated Range (km)",
        height=500
    )

    return fig


def create_wh_per_km_vs_range_scatter(df):
    if df.empty:
        return None

    required = [
        "Wh/km",
        "Estimated Range (km)",
        "Chemistry",
        "Scenario Name"
    ]

    for col in required:
        if col not in df.columns:
            return None

    fig = go.Figure()

    chemistries = sorted(df["Chemistry"].fillna("Unknown").astype(str).unique())

    for chemistry in chemistries:
        sub = df[df["Chemistry"].astype(str) == chemistry]

        fig.add_trace(
            go.Scatter(
                x=sub["Wh/km"],
                y=sub["Estimated Range (km)"],
                mode="markers",
                name=chemistry,
                text=sub["Scenario Name"],
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "Wh/km: %{x:.2f}<br>"
                    "Range: %{y:.1f} km<br>"
                    "<extra></extra>"
                ),
                marker=dict(
                    size=12,
                    opacity=0.78
                )
            )
        )

    fig.update_layout(
        title="Range vs Energy Consumption",
        xaxis_title="Energy Consumption (Wh/km)",
        yaxis_title="Estimated Range (km)",
        height=500
    )

    return fig


def create_timeline_chart(df):
    if df.empty or "Created Date" not in df.columns:
        return None

    timeline = (
        df.dropna(subset=["Created Date"])
        .groupby("Created Date")
        .size()
        .reset_index(name="Scenario Count")
    )

    if timeline.empty:
        return None

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=timeline["Created Date"],
            y=timeline["Scenario Count"],
            mode="lines+markers",
            name="Scenarios Created"
        )
    )

    fig.update_layout(
        title="Scenario Creation Timeline",
        xaxis_title="Date",
        yaxis_title="Scenario Count",
        height=430
    )

    return fig


def create_group_summary(df, group_column):
    if df.empty or group_column not in df.columns:
        return pd.DataFrame()

    summary = (
        df.groupby(group_column)
        .agg(
            Scenario_Count=("ID", "count"),
            Avg_Pack_Energy_kWh=("Pack Energy (kWh)", "mean"),
            Avg_Range_km=("Estimated Range (km)", "mean"),
            Best_Range_km=("Estimated Range (km)", "max"),
            Avg_Wh_per_km=("Wh/km", "mean"),
            Avg_Charging_Time_min=("Charging Time (min)", "mean")
        )
        .reset_index()
    )

    return summary


def create_top_scenarios_table(df):
    if df.empty:
        return pd.DataFrame()

    columns = [
        "ID",
        "Scenario Name",
        "Vehicle Segment",
        "Chemistry",
        "Pack Energy (kWh)",
        "Estimated Range (km)",
        "Wh/km",
        "Charging Time (min)",
        "Created At"
    ]

    available_cols = [col for col in columns if col in df.columns]

    return df[available_cols].copy()


# -------------------------------------------------------
# PAGE
# -------------------------------------------------------
def run_scenario_dashboard_analytics():
    st.markdown("# Dashboard Analytics")
    st.caption("Analyze the complete saved scenario database using charts, rankings, and summary statistics.")

    st.info(
        "This page turns saved EV scenarios into a management-style analytics dashboard. "
        "Use it to understand chemistry trends, pack-size distribution, range performance, charging behaviour, and scenario creation history."
    )

    df = load_scenario_analytics_dataframe()
    df = add_extended_fields_from_json(df)

    if df.empty:
        st.warning("No saved scenarios found. Save or import scenarios before using analytics.")
        return

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "Overview",
            "Battery & Range",
            "Charging & Efficiency",
            "Technology Mix",
            "Rankings & Export"
        ]
    )

    # ---------------------------------------------------
    # TAB 1: OVERVIEW
    # ---------------------------------------------------
    with tab1:
        st.markdown("## Scenario Database Overview")

        summary = create_dashboard_summary(df)

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric("Total Scenarios", f"{summary['total_scenarios']}")

        with c2:
            st.metric("Chemistries Used", f"{summary['unique_chemistries']}")

        with c3:
            st.metric("Average Pack Energy", f"{summary['avg_pack_energy']:.2f} kWh")

        with c4:
            st.metric("Best Range", f"{summary['best_range']:.1f} km")

        c5, c6, c7 = st.columns(3)

        with c5:
            st.metric("Average Range", f"{summary['avg_range']:.1f} km")

        with c6:
            st.metric("Average Wh/km", f"{summary['avg_wh_per_km']:.1f}")

        with c7:
            st.metric("Average Charging Time", f"{summary['avg_charging_time']:.1f} min")

        st.divider()

        col_a, col_b = st.columns(2)

        with col_a:
            fig = create_pie_chart(
                df,
                column="Chemistry",
                title="Chemistry Distribution"
            )

            if fig is not None:
                st.plotly_chart(fig, use_container_width=True)

        with col_b:
            fig = create_bar_count_chart(
                df,
                column="Vehicle Segment",
                title="Vehicle Segment Distribution",
                x_title="Vehicle Segment",
                y_title="Scenario Count"
            )

            if fig is not None:
                st.plotly_chart(fig, use_container_width=True)

        timeline_fig = create_timeline_chart(df)

        if timeline_fig is not None:
            st.plotly_chart(timeline_fig, use_container_width=True)

    # ---------------------------------------------------
    # TAB 2: BATTERY & RANGE
    # ---------------------------------------------------
    with tab2:
        st.markdown("## Battery and Range Analytics")

        col_a, col_b = st.columns(2)

        with col_a:
            fig = create_histogram(
                df,
                column="Pack Energy (kWh)",
                title="Pack Energy Distribution",
                x_title="Pack Energy (kWh)"
            )

            if fig is not None:
                st.plotly_chart(fig, use_container_width=True)

        with col_b:
            fig = create_histogram(
                df,
                column="Estimated Range (km)",
                title="Estimated Range Distribution",
                x_title="Estimated Range (km)"
            )

            if fig is not None:
                st.plotly_chart(fig, use_container_width=True)

        scatter_fig = create_range_vs_energy_scatter(df)

        if scatter_fig is not None:
            st.plotly_chart(scatter_fig, use_container_width=True)

        st.markdown("## Chemistry-Level Summary")

        chemistry_summary = create_group_summary(df, "Chemistry")

        if chemistry_summary.empty:
            st.warning("Chemistry summary unavailable.")
        else:
            st.dataframe(
                chemistry_summary.round(3),
                use_container_width=True,
                hide_index=True
            )

    # ---------------------------------------------------
    # TAB 3: CHARGING & EFFICIENCY
    # ---------------------------------------------------
    with tab3:
        st.markdown("## Charging and Efficiency Analytics")

        col_a, col_b = st.columns(2)

        with col_a:
            fig = create_histogram(
                df,
                column="Charging Time (min)",
                title="Charging Time Distribution",
                x_title="Charging Time (min)"
            )

            if fig is not None:
                st.plotly_chart(fig, use_container_width=True)

        with col_b:
            fig = create_histogram(
                df,
                column="Wh/km",
                title="Energy Consumption Distribution",
                x_title="Wh/km"
            )

            if fig is not None:
                st.plotly_chart(fig, use_container_width=True)

        wh_range_fig = create_wh_per_km_vs_range_scatter(df)

        if wh_range_fig is not None:
            st.plotly_chart(wh_range_fig, use_container_width=True)

        st.markdown("## Vehicle-Segment Summary")

        segment_summary = create_group_summary(df, "Vehicle Segment")

        if segment_summary.empty:
            st.warning("Vehicle segment summary unavailable.")
        else:
            st.dataframe(
                segment_summary.round(3),
                use_container_width=True,
                hide_index=True
            )

    # ---------------------------------------------------
    # TAB 4: TECHNOLOGY MIX
    # ---------------------------------------------------
    with tab4:
        st.markdown("## Technology Mix Analytics")

        col_a, col_b = st.columns(2)

        with col_a:
            fig = create_bar_count_chart(
                df,
                column="Motor Type",
                title="Motor Type Distribution",
                x_title="Motor Type",
                y_title="Scenario Count"
            )

            if fig is not None:
                st.plotly_chart(fig, use_container_width=True)

        with col_b:
            fig = create_bar_count_chart(
                df,
                column="Inverter Device",
                title="Inverter Device Distribution",
                x_title="Inverter Device",
                y_title="Scenario Count"
            )

            if fig is not None:
                st.plotly_chart(fig, use_container_width=True)

        col_c, col_d = st.columns(2)

        with col_c:
            fig = create_histogram(
                df,
                column="Max Battery Temperature (°C)",
                title="Maximum Battery Temperature Distribution",
                x_title="Maximum Battery Temperature (°C)"
            )

            if fig is not None:
                st.plotly_chart(fig, use_container_width=True)

        with col_d:
            fig = create_histogram(
                df,
                column="Max SOC Error (%)",
                title="Maximum SOC Error Distribution",
                x_title="Maximum SOC Error (%)"
            )

            if fig is not None:
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("## Motor-Type Summary")

        if "Motor Type" in df.columns:
            motor_summary = create_group_summary(df, "Motor Type")

            if not motor_summary.empty:
                st.dataframe(
                    motor_summary.round(3),
                    use_container_width=True,
                    hide_index=True
                )

    # ---------------------------------------------------
    # TAB 5: RANKINGS & EXPORT
    # ---------------------------------------------------
    with tab5:
        st.markdown("## Scenario Rankings")

        base_table = create_top_scenarios_table(df)

        if base_table.empty:
            st.warning("No ranking data available.")
        else:
            st.markdown("### Top Range Scenarios")

            top_range = base_table.sort_values(
                by="Estimated Range (km)",
                ascending=False
            ).head(10)

            st.dataframe(
                top_range.round(3),
                use_container_width=True,
                hide_index=True
            )

            st.markdown("### Most Efficient Scenarios")

            efficient = base_table.sort_values(
                by="Wh/km",
                ascending=True
            ).head(10)

            st.dataframe(
                efficient.round(3),
                use_container_width=True,
                hide_index=True
            )

            st.markdown("### Fastest Charging Scenarios")

            fast_charge = base_table.sort_values(
                by="Charging Time (min)",
                ascending=True
            ).head(10)

            st.dataframe(
                fast_charge.round(3),
                use_container_width=True,
                hide_index=True
            )

        st.divider()

        st.markdown("## Export Analytics Dataset")

        export_df = df.drop(
            columns=["Created At Parsed"],
            errors="ignore"
        )

        csv_data = export_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download Analytics Dataset CSV",
            data=csv_data,
            file_name="vidyut_vahanastra_dashboard_analytics.csv",
            mime="text/csv"
        )

        analytics_payload = {
            "Summary": create_dashboard_summary(df),
            "Scenario Count": len(df),
            "Dataset": export_df.to_dict(orient="records")
        }

        analytics_json = json.dumps(
            analytics_payload,
            indent=4,
            default=str
        ).encode("utf-8")

        st.download_button(
            label="Download Analytics Dataset JSON",
            data=analytics_json,
            file_name="vidyut_vahanastra_dashboard_analytics.json",
            mime="application/json"
        )