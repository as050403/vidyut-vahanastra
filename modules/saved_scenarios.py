import json
import pandas as pd
import streamlit as st

from utils.scenario_store import (
    save_scenario,
    list_scenarios,
    get_scenario_by_id,
    delete_scenario
)


def build_manual_scenario_payload(
    scenario_name,
    vehicle_segment,
    chemistry,
    pack_voltage,
    pack_energy,
    pack_capacity,
    total_cells,
    estimated_pack_mass,
    charger_power,
    charging_time,
    charging_cost,
    estimated_range,
    wh_per_km,
    soc_method,
    max_soc_error,
    motor_type,
    peak_motor_power,
    inverter_device,
    inverter_efficiency,
    max_battery_temp,
    max_motor_temp,
    max_inverter_temp,
    remarks
):
    return {
        "Scenario Metadata": {
            "Scenario Name": scenario_name,
            "Vehicle Segment": vehicle_segment
        },
        "Battery Pack": {
            "Chemistry": chemistry,
            "Nominal Pack Voltage (V)": pack_voltage,
            "Pack Energy (kWh)": pack_energy,
            "Pack Capacity (Ah)": pack_capacity,
            "Total Cells": total_cells,
            "Estimated Pack Mass (kg)": estimated_pack_mass
        },
        "Charging": {
            "Charger Power (kW)": charger_power,
            "Charging Time (min)": charging_time,
            "Charging Cost (₹)": charging_cost
        },
        "Range": {
            "Estimated Range (km)": estimated_range,
            "Energy Consumption (Wh/km)": wh_per_km
        },
        "BMS and SOC": {
            "SOC Estimation Method": soc_method,
            "Maximum SOC Error (%)": max_soc_error
        },
        "Motor and Inverter": {
            "Motor Type": motor_type,
            "Peak Motor Power (kW)": peak_motor_power,
            "Inverter Device": inverter_device,
            "Inverter Efficiency (%)": inverter_efficiency
        },
        "Thermal": {
            "Maximum Battery Temperature (°C)": max_battery_temp,
            "Maximum Motor Temperature (°C)": max_motor_temp,
            "Maximum Inverter Temperature (°C)": max_inverter_temp
        },
        "Engineering Remarks": {
            "Remarks": remarks
        }
    }


def flatten_payload_for_display(payload):
    records = []

    for section, values in payload.items():
        for parameter, value in values.items():
            records.append(
                {
                    "Section": section,
                    "Parameter": parameter,
                    "Value": value
                }
            )

    return pd.DataFrame(records)


def run_saved_scenarios():
    st.markdown("# Saved Scenarios")
    st.caption("Save, load, view, delete, and export EV design scenarios.")

    st.info(
        "This page adds persistence to Vidyut Vahanastra. Scenarios are saved locally in a SQLite database inside the data folder."
    )

    tab_save, tab_library, tab_loaded = st.tabs(
        [
            "Create / Save Scenario",
            "Scenario Library",
            "Loaded Scenario"
        ]
    )

    with tab_save:
        st.markdown("## Create Scenario Snapshot")

        c1, c2, c3 = st.columns(3)

        with c1:
            scenario_name = st.text_input(
                "Scenario name",
                value="Indian Compact SUV EV - LFP 400 V Class"
            )

            vehicle_segment = st.selectbox(
                "Vehicle segment",
                [
                    "Two-Wheeler",
                    "Compact City EV",
                    "Compact SUV EV",
                    "Premium Sedan EV",
                    "Commercial EV",
                    "Electric Bus",
                    "Custom"
                ],
                index=2
            )

        with c2:
            chemistry = st.selectbox(
                "Battery chemistry",
                ["LFP", "NMC", "NCA", "LTO"],
                index=0
            )

            pack_voltage = st.number_input(
                "Pack voltage (V)",
                min_value=12.0,
                max_value=1000.0,
                value=307.2,
                step=1.0,
                format="%.1f"
            )

        with c3:
            pack_energy = st.number_input(
                "Pack energy (kWh)",
                min_value=1.0,
                max_value=300.0,
                value=30.72,
                step=0.5,
                format="%.2f"
            )

            pack_capacity = st.number_input(
                "Pack capacity (Ah)",
                min_value=1.0,
                max_value=1000.0,
                value=100.0,
                step=1.0,
                format="%.1f"
            )

        b1, b2, b3 = st.columns(3)

        with b1:
            total_cells = st.number_input(
                "Total cells",
                min_value=1,
                max_value=50000,
                value=96,
                step=1
            )

            estimated_pack_mass = st.number_input(
                "Estimated pack mass (kg)",
                min_value=1.0,
                max_value=3000.0,
                value=295.0,
                step=5.0,
                format="%.1f"
            )

        with b2:
            charger_power = st.number_input(
                "Charger power (kW)",
                min_value=0.5,
                max_value=500.0,
                value=50.0,
                step=0.5,
                format="%.1f"
            )

            charging_time = st.number_input(
                "Charging time (min)",
                min_value=1.0,
                max_value=3000.0,
                value=42.0,
                step=1.0,
                format="%.1f"
            )

        with b3:
            charging_cost = st.number_input(
                "Charging cost (₹)",
                min_value=0.0,
                max_value=20000.0,
                value=350.0,
                step=10.0,
                format="%.1f"
            )

            estimated_range = st.number_input(
                "Estimated range (km)",
                min_value=1.0,
                max_value=1200.0,
                value=230.0,
                step=5.0,
                format="%.1f"
            )

        r1, r2, r3 = st.columns(3)

        with r1:
            wh_per_km = st.number_input(
                "Energy consumption (Wh/km)",
                min_value=10.0,
                max_value=600.0,
                value=135.0,
                step=5.0,
                format="%.1f"
            )

            soc_method = st.selectbox(
                "SOC estimation method",
                ["Coulomb Counting", "OCV Lookup", "Kalman-Corrected", "Hybrid BMS Estimator"],
                index=2
            )

        with r2:
            max_soc_error = st.number_input(
                "Maximum SOC error (%)",
                min_value=0.0,
                max_value=50.0,
                value=2.5,
                step=0.1,
                format="%.1f"
            )

            motor_type = st.selectbox(
                "Motor type",
                ["PMSM", "IM", "BLDC", "IPM"],
                index=0
            )

        with r3:
            peak_motor_power = st.number_input(
                "Peak motor power (kW)",
                min_value=1.0,
                max_value=500.0,
                value=105.0,
                step=5.0,
                format="%.1f"
            )

            inverter_device = st.selectbox(
                "Inverter device",
                ["Si IGBT", "SiC MOSFET", "GaN HEMT"],
                index=1
            )

        t1, t2, t3, t4 = st.columns(4)

        with t1:
            inverter_efficiency = st.number_input(
                "Inverter efficiency (%)",
                min_value=70.0,
                max_value=99.9,
                value=97.0,
                step=0.1,
                format="%.1f"
            )

        with t2:
            max_battery_temp = st.number_input(
                "Max battery temperature (°C)",
                min_value=-10.0,
                max_value=120.0,
                value=38.0,
                step=0.5,
                format="%.1f"
            )

        with t3:
            max_motor_temp = st.number_input(
                "Max motor temperature (°C)",
                min_value=-10.0,
                max_value=220.0,
                value=92.0,
                step=1.0,
                format="%.1f"
            )

        with t4:
            max_inverter_temp = st.number_input(
                "Max inverter temperature (°C)",
                min_value=-10.0,
                max_value=220.0,
                value=85.0,
                step=1.0,
                format="%.1f"
            )

        remarks = st.text_area(
            "Engineering remarks",
            value=(
                "This scenario represents a practical Indian compact SUV EV configuration. "
                "The LFP pack supports safety and thermal stability, while the selected range and charging values are suitable for daily-use evaluation."
            ),
            height=130
        )

        payload = build_manual_scenario_payload(
            scenario_name=scenario_name,
            vehicle_segment=vehicle_segment,
            chemistry=chemistry,
            pack_voltage=pack_voltage,
            pack_energy=pack_energy,
            pack_capacity=pack_capacity,
            total_cells=total_cells,
            estimated_pack_mass=estimated_pack_mass,
            charger_power=charger_power,
            charging_time=charging_time,
            charging_cost=charging_cost,
            estimated_range=estimated_range,
            wh_per_km=wh_per_km,
            soc_method=soc_method,
            max_soc_error=max_soc_error,
            motor_type=motor_type,
            peak_motor_power=peak_motor_power,
            inverter_device=inverter_device,
            inverter_efficiency=inverter_efficiency,
            max_battery_temp=max_battery_temp,
            max_motor_temp=max_motor_temp,
            max_inverter_temp=max_inverter_temp,
            remarks=remarks
        )

        st.markdown("## Scenario Preview")

        preview_df = flatten_payload_for_display(payload)
        st.dataframe(preview_df, use_container_width=True, hide_index=True)

        if st.button("Save Scenario"):
            save_scenario(
                scenario_name=scenario_name,
                vehicle_segment=vehicle_segment,
                chemistry=chemistry,
                pack_voltage=pack_voltage,
                pack_energy=pack_energy,
                estimated_range=estimated_range,
                charging_time=charging_time,
                wh_per_km=wh_per_km,
                scenario_data=payload
            )

            st.success(f"Scenario saved: {scenario_name}")

    with tab_library:
        st.markdown("## Scenario Library")

        rows, columns = list_scenarios()

        if not rows:
            st.warning("No scenarios saved yet.")
        else:
            library_df = pd.DataFrame(rows, columns=columns)
            st.dataframe(library_df, use_container_width=True, hide_index=True)

            selected_id = st.number_input(
                "Enter Scenario ID to load / delete",
                min_value=1,
                value=int(library_df["ID"].iloc[0]),
                step=1
            )

            a1, a2, a3 = st.columns(3)

            with a1:
                if st.button("Load Scenario"):
                    scenario = get_scenario_by_id(int(selected_id))

                    if scenario is None:
                        st.error("Scenario ID not found.")
                    else:
                        st.session_state["loaded_scenario"] = scenario
                        st.success("Scenario loaded into session state.")

            with a2:
                scenario_for_download = get_scenario_by_id(int(selected_id))

                if scenario_for_download is not None:
                    json_bytes = json.dumps(scenario_for_download, indent=4).encode("utf-8")

                    st.download_button(
                        label="Download Scenario JSON",
                        data=json_bytes,
                        file_name=f"vidyut_vahanastra_scenario_{selected_id}.json",
                        mime="application/json"
                    )

            with a3:
                if st.button("Delete Scenario"):
                    delete_scenario(int(selected_id))
                    st.warning("Scenario deleted. Refresh or revisit this page to update the library.")

    with tab_loaded:
        st.markdown("## Loaded Scenario")

        if "loaded_scenario" not in st.session_state:
            st.warning("No scenario loaded yet. Load one from the Scenario Library tab.")
        else:
            loaded = st.session_state["loaded_scenario"]

            st.success("A scenario is currently loaded in session state.")

            loaded_df = flatten_payload_for_display(loaded)
            st.dataframe(loaded_df, use_container_width=True, hide_index=True)

            st.markdown("## Raw JSON")

            st.json(loaded)

            json_bytes = json.dumps(loaded, indent=4).encode("utf-8")

            st.download_button(
                label="Download Loaded Scenario JSON",
                data=json_bytes,
                file_name="loaded_vidyut_vahanastra_scenario.json",
                mime="application/json"
            )