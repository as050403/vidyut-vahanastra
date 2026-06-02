import streamlit as st
import pandas as pd
import plotly.graph_objects as go


VEHICLE_PRESET_PATH = "data/vehicle_presets.csv"
CHARGER_PRESET_PATH = "data/charger_presets.csv"


@st.cache_data
def load_real_vehicle_presets():
    return pd.read_csv(VEHICLE_PRESET_PATH)


@st.cache_data
def load_charger_presets():
    return pd.read_csv(CHARGER_PRESET_PATH)


def create_range_comparison_chart(df):
    if "Claimed_Range_km" not in df.columns or "Practical_Range_km" not in df.columns:
        return None

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=df["Vehicle_Preset"],
            y=df["Claimed_Range_km"],
            name="Claimed Range",
            text=df["Claimed_Range_km"],
            textposition="auto"
        )
    )

    fig.add_trace(
        go.Bar(
            x=df["Vehicle_Preset"],
            y=df["Practical_Range_km"],
            name="Practical Demo Range",
            text=df["Practical_Range_km"],
            textposition="auto"
        )
    )

    fig.update_layout(
        title="Claimed vs Practical Demo Range",
        xaxis_title="Vehicle Preset",
        yaxis_title="Range (km)",
        barmode="group",
        height=520
    )

    return fig


def create_battery_size_chart(df):
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=df["Vehicle_Preset"],
            y=df["Usable_Battery_kWh"],
            text=df["Usable_Battery_kWh"],
            textposition="auto",
            name="Battery Capacity"
        )
    )

    fig.update_layout(
        title="Usable Battery Capacity by Preset",
        xaxis_title="Vehicle Preset",
        yaxis_title="Usable Battery Capacity (kWh)",
        height=500
    )

    return fig


def create_motor_power_chart(df):
    if "Motor_Power_kW" not in df.columns:
        return None

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=df["Vehicle_Preset"],
            y=df["Motor_Power_kW"],
            text=df["Motor_Power_kW"],
            textposition="auto",
            name="Motor Power"
        )
    )

    fig.update_layout(
        title="Motor Power by Preset",
        xaxis_title="Vehicle Preset",
        yaxis_title="Motor Power (kW)",
        height=500
    )

    return fig


def create_selected_preset_table(row):
    data = {
        "Parameter": [
            "Vehicle Preset",
            "Segment",
            "Reference Model",
            "Usable Battery",
            "Claimed Range",
            "Practical Demo Range",
            "Motor Power",
            "Motor Torque",
            "Vehicle Mass",
            "Drag Coefficient",
            "Frontal Area",
            "Rolling Resistance",
            "Drivetrain Efficiency",
            "Default Speed",
            "Default HVAC Load",
            "Auxiliary Load",
            "Default Charger",
            "Chemistry Assumption",
            "Notes"
        ],
        "Value": [
            row.get("Vehicle_Preset", "-"),
            row.get("Segment", "-"),
            row.get("Reference_Model", "-"),
            f"{row.get('Usable_Battery_kWh', '-') } kWh",
            f"{row.get('Claimed_Range_km', '-') } km",
            f"{row.get('Practical_Range_km', '-') } km",
            f"{row.get('Motor_Power_kW', '-') } kW",
            f"{row.get('Motor_Torque_Nm', '-') } Nm",
            f"{row.get('Mass_kg', '-') } kg",
            row.get("Cd", "-"),
            f"{row.get('Frontal_Area_m2', '-') } m²",
            row.get("Crr", "-"),
            row.get("Drivetrain_Efficiency", "-"),
            f"{row.get('Default_Speed_kmh', '-') } km/h",
            f"{row.get('Default_HVAC_kW', '-') } kW",
            f"{row.get('Auxiliary_Load_kW', '-') } kW",
            f"{row.get('Default_Charger_kW', '-') } kW",
            row.get("Chemistry_Assumption", "-"),
            row.get("Notes", "-")
        ]
    }

    return pd.DataFrame(data)


def run_real_ev_presets():
    st.markdown("# Real EV Presets")
    st.caption("Review Indian EV-style vehicle presets used by the Range Lab and Scenario Compare modules.")

    st.info(
        "These presets are demonstration presets based on public specification anchors and engineering assumptions. "
        "Use official brochures or manufacturer datasheets before using any value in a formal design report."
    )

    vehicle_df = load_real_vehicle_presets()
    charger_df = load_charger_presets()

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "Preset Library",
            "Selected Preset",
            "Charts",
            "Charger Library"
        ]
    )

    with tab1:
        st.markdown("## Vehicle Preset Library")

        st.dataframe(
            vehicle_df,
            use_container_width=True,
            hide_index=True
        )

        csv_data = vehicle_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download Vehicle Presets CSV",
            data=csv_data,
            file_name="vidyut_vahanastra_vehicle_presets.csv",
            mime="text/csv"
        )

    with tab2:
        st.markdown("## Selected Preset Details")

        selected_preset = st.selectbox(
            "Select a vehicle preset",
            options=vehicle_df["Vehicle_Preset"].tolist()
        )

        row = vehicle_df[vehicle_df["Vehicle_Preset"] == selected_preset].iloc[0]

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric(
                "Battery",
                f"{row['Usable_Battery_kWh']} kWh"
            )

        with c2:
            st.metric(
                "Claimed Range",
                f"{row.get('Claimed_Range_km', '-')} km"
            )

        with c3:
            st.metric(
                "Practical Demo Range",
                f"{row.get('Practical_Range_km', '-')} km"
            )

        with c4:
            st.metric(
                "Motor Power",
                f"{row.get('Motor_Power_kW', '-')} kW"
            )

        selected_df = create_selected_preset_table(row)
        st.dataframe(
            selected_df,
            use_container_width=True,
            hide_index=True
        )

        st.success(
            "This preset is already available in Range Lab and Scenario Compare because both modules read from data/vehicle_presets.csv."
        )

    with tab3:
        st.markdown("## Preset Charts")

        battery_fig = create_battery_size_chart(vehicle_df)
        st.plotly_chart(battery_fig, use_container_width=True)

        range_fig = create_range_comparison_chart(vehicle_df)
        if range_fig is not None:
            st.plotly_chart(range_fig, use_container_width=True)

        motor_fig = create_motor_power_chart(vehicle_df)
        if motor_fig is not None:
            st.plotly_chart(motor_fig, use_container_width=True)

    with tab4:
        st.markdown("## Charger Preset Library")

        st.dataframe(
            charger_df,
            use_container_width=True,
            hide_index=True
        )

        charger_csv = charger_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download Charger Presets CSV",
            data=charger_csv,
            file_name="vidyut_vahanastra_charger_presets.csv",
            mime="text/csv"
        )

        st.markdown("## Usage Note")

        st.write(
            """
            Charger presets are used by the Charging Lab and Scenario Compare modules. 
            For exact vehicle validation, the charger power must be limited by both the external charger rating and the EV battery/BMS acceptance limit.
            """
        )