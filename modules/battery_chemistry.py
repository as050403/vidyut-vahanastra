import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go


DATA_PATH = "data/battery_chemistries.csv"


@st.cache_data
def load_battery_chemistry_data():
    return pd.read_csv(DATA_PATH)


def get_average_energy_density(row):
    return (row["Energy_Density_Min_Whkg"] + row["Energy_Density_Max_Whkg"]) / 2


def get_average_cycle_life(row):
    return (row["Cycle_Life_Min"] + row["Cycle_Life_Max"]) / 2


def generate_ocv_curve(chemistry):
    """
    Simplified OCV-SOC curves for dashboard visualization.
    These are not manufacturer-specific cell test curves.
    They are conceptual curves based on common chemistry behavior:
    - LFP: flatter middle region
    - NMC/NCA: more sloped relationship
    - LTO: lower-voltage chemistry
    """
    soc = np.linspace(0.01, 1.0, 120)

    if chemistry == "LFP":
        ocv = 3.05 + 0.18 * soc
        ocv += 0.10 / (1 + np.exp(-80 * (soc - 0.92)))
        ocv -= 0.10 / (1 + np.exp(80 * (soc - 0.08)))

    elif chemistry == "NMC":
        ocv = 3.00 + 1.15 * soc - 0.06 * np.sin(np.pi * soc)

    elif chemistry == "NCA":
        ocv = 3.02 + 1.13 * soc - 0.04 * np.sin(np.pi * soc)

    elif chemistry == "LTO":
        ocv = 1.75 + 0.65 * soc - 0.03 * np.sin(np.pi * soc)

    else:
        ocv = 3.0 + soc

    return soc * 100, ocv


def chemistry_recommendation(selected_chemistry):
    recommendations = {
        "LFP": {
            "Best Use": "Indian mass-market EVs, two-wheelers, buses, taxis, and commercial EVs",
            "Why": "Best balance of safety, cost, thermal stability, and cycle life.",
            "Caution": "Lower energy density means the pack may be heavier or larger for the same range."
        },
        "NMC": {
            "Best Use": "Passenger EVs where range and pack compactness are important",
            "Why": "Higher energy density than LFP with balanced performance.",
            "Caution": "Needs stronger BMS and thermal management than LFP."
        },
        "NCA": {
            "Best Use": "Premium long-range EVs where maximum energy density is prioritized",
            "Why": "Very high energy density and power capability.",
            "Caution": "Lower thermal stability and cycle life compared with LFP."
        },
        "LTO": {
            "Best Use": "Fast-charging buses, grid storage, and high-cycle applications",
            "Why": "Extremely long cycle life and excellent fast-charging capability.",
            "Caution": "Very low energy density and high cost make it less suitable for long-range passenger EVs."
        }
    }

    return recommendations.get(selected_chemistry, None)


def create_radar_chart(df_selected):
    metrics = [
        "Safety_Score",
        "Cost_Score",
        "Power_Score",
        "Indian_Suitability_Score"
    ]

    readable_metrics = [
        "Safety",
        "Cost Advantage",
        "Power Capability",
        "Indian Suitability"
    ]

    fig = go.Figure()

    for _, row in df_selected.iterrows():
        values = [row[m] for m in metrics]
        values.append(values[0])

        theta = readable_metrics + [readable_metrics[0]]

        fig.add_trace(
            go.Scatterpolar(
                r=values,
                theta=theta,
                fill="toself",
                name=row["Chemistry"]
            )
        )

    fig.update_layout(
        title="Battery Chemistry Radar Comparison",
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 10]
            )
        ),
        showlegend=True,
        height=520
    )

    return fig


def create_energy_density_chart(df_selected):
    df_plot = df_selected.copy()
    df_plot["Average_Energy_Density_Whkg"] = df_plot.apply(get_average_energy_density, axis=1)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df_plot["Chemistry"],
            y=df_plot["Average_Energy_Density_Whkg"],
            text=df_plot["Average_Energy_Density_Whkg"].round(1),
            textposition="auto"
        )
    )

    fig.update_layout(
        title="Average Gravimetric Energy Density",
        xaxis_title="Chemistry",
        yaxis_title="Wh/kg",
        height=420
    )

    return fig


def create_cycle_life_chart(df_selected):
    df_plot = df_selected.copy()
    df_plot["Average_Cycle_Life"] = df_plot.apply(get_average_cycle_life, axis=1)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df_plot["Chemistry"],
            y=df_plot["Average_Cycle_Life"],
            text=df_plot["Average_Cycle_Life"].round(0),
            textposition="auto"
        )
    )

    fig.update_layout(
        title="Average Cycle Life Estimate",
        xaxis_title="Chemistry",
        yaxis_title="Cycles",
        height=420
    )

    return fig


def create_ocv_soc_chart(selected_chemistries):
    fig = go.Figure()

    for chemistry in selected_chemistries:
        soc, ocv = generate_ocv_curve(chemistry)
        fig.add_trace(
            go.Scatter(
                x=soc,
                y=ocv,
                mode="lines",
                name=chemistry
            )
        )

    fig.update_layout(
        title="Simplified OCV-SOC Curve",
        xaxis_title="SOC (%)",
        yaxis_title="Open Circuit Voltage (V)",
        height=480
    )

    return fig


def run_battery_chemistry_lab():
    st.markdown("# Battery Chemistry Lab")
    st.caption("Compare EV battery chemistries for energy density, cycle life, safety, power capability, cost, and Indian EV suitability.")

    df = load_battery_chemistry_data()

    st.info(
        "This module uses simplified engineering-level values for early design comparison. "
        "Manufacturer-specific cell datasheets should be used for final pack design."
    )

    selected_chemistries = st.multiselect(
        "Select chemistries to compare",
        options=df["Chemistry"].tolist(),
        default=df["Chemistry"].tolist()
    )

    if not selected_chemistries:
        st.warning("Select at least one chemistry to continue.")
        return

    df_selected = df[df["Chemistry"].isin(selected_chemistries)].copy()

    st.divider()

    st.markdown("## Chemistry Snapshot")

    metric_cols = st.columns(len(df_selected))

    for idx, (_, row) in enumerate(df_selected.iterrows()):
        with metric_cols[idx]:
            avg_energy = get_average_energy_density(row)
            avg_cycles = get_average_cycle_life(row)

            st.metric(
                label=f"{row['Chemistry']} Voltage",
                value=f"{row['Nominal_Voltage_V']} V"
            )
            st.caption(row["Full_Name"])
            st.write(f"**Avg. Energy Density:** {avg_energy:.0f} Wh/kg")
            st.write(f"**Avg. Cycle Life:** {avg_cycles:.0f} cycles")
            st.write(f"**Thermal Stability:** {row['Thermal_Stability']}")

    st.divider()

    st.markdown("## Interactive Comparison Table")

    display_df = df_selected[
        [
            "Chemistry",
            "Full_Name",
            "Nominal_Voltage_V",
            "Full_Charge_V",
            "Energy_Density_Min_Whkg",
            "Energy_Density_Max_Whkg",
            "Cycle_Life_Min",
            "Cycle_Life_Max",
            "Safety_Score",
            "Cost_Score",
            "Power_Score",
            "Indian_Suitability_Score",
            "Thermal_Stability",
            "Major_Strength",
            "Major_Limitation"
        ]
    ]

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.divider()

    st.markdown("## Visual Comparison")

    col1, col2 = st.columns(2)

    with col1:
        radar_fig = create_radar_chart(df_selected)
        st.plotly_chart(radar_fig, use_container_width=True)

    with col2:
        energy_fig = create_energy_density_chart(df_selected)
        st.plotly_chart(energy_fig, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        cycle_fig = create_cycle_life_chart(df_selected)
        st.plotly_chart(cycle_fig, use_container_width=True)

    with col4:
        ocv_fig = create_ocv_soc_chart(selected_chemistries)
        st.plotly_chart(ocv_fig, use_container_width=True)

    st.divider()

    st.markdown("## Chemistry Decision Assistant")

    selected_single = st.selectbox(
        "Choose one chemistry for recommendation",
        options=df_selected["Chemistry"].tolist()
    )

    recommendation = chemistry_recommendation(selected_single)

    if recommendation:
        col_a, col_b, col_c = st.columns(3)

        with col_a:
            st.success("Best Use Case")
            st.write(recommendation["Best Use"])

        with col_b:
            st.info("Why it fits")
            st.write(recommendation["Why"])

        with col_c:
            st.warning("Design Caution")
            st.write(recommendation["Caution"])

    st.divider()

    st.markdown("## Engineering Interpretation")

    st.write(
        """
        **LFP** is the strongest default option for Indian mass-market EVs because it offers high safety, low cost, and long cycle life.  
        **NMC** is suitable where higher range and compact pack design matter.  
        **NCA** is more suitable for premium long-range EVs but requires stronger thermal and BMS control.  
        **LTO** is excellent for ultra-fast charging and high-cycle applications, but its low energy density makes it less suitable for normal passenger EV range targets.
        """
    )