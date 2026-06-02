import pandas as pd
import streamlit as st

from utils.scenario_store import save_scenario


VEHICLE_PRESET_PATH = "data/vehicle_presets.csv"


# -------------------------------------------------------
# DATA LOADING
# -------------------------------------------------------
@st.cache_data
def load_vehicle_presets_for_scenario():
    return pd.read_csv(VEHICLE_PRESET_PATH)


# -------------------------------------------------------
# SAFE HELPERS
# -------------------------------------------------------
def safe_get(row, key, default):
    try:
        value = row.get(key, default)

        if pd.isna(value):
            return default

        return value

    except Exception:
        return default


def infer_chemistry(raw_chemistry):
    """
    Converts chemistry text from preset CSV into a clean report/saved-scenario chemistry.
    """

    text = str(raw_chemistry).upper()

    if "LTO" in text:
        return "LTO"

    if "LFP" in text or "BLADE" in text:
        return "LFP"

    if "NMC" in text:
        return "NMC"

    if "NCA" in text:
        return "NCA"

    return "LFP"


def estimate_pack_voltage_by_segment(segment):
    """
    Engineering demo assumption for nominal pack voltage.
    These are not manufacturer-certified values.
    """

    segment_text = str(segment).lower()

    if "two" in segment_text or "scooter" in segment_text:
        return 48.0

    if "bus" in segment_text or "commercial" in segment_text:
        return 600.0

    if "premium" in segment_text:
        return 400.0

    return 350.0


def estimate_cell_count(pack_voltage, chemistry):
    """
    Approximate series cell count based on nominal chemistry voltage.
    """

    nominal_cell_voltage = {
        "LFP": 3.2,
        "NMC": 3.7,
        "NCA": 3.7,
        "LTO": 2.4
    }.get(chemistry, 3.2)

    return max(int(round(pack_voltage / nominal_cell_voltage)), 1)


def estimate_pack_capacity_ah(pack_energy_kwh, pack_voltage):
    if pack_voltage <= 0:
        return 0.0

    return pack_energy_kwh * 1000.0 / pack_voltage


def estimate_pack_mass(pack_energy_kwh, chemistry):
    """
    Simplified pack-level energy density assumption.
    """

    pack_density_wh_per_kg = {
        "LFP": 120,
        "NMC": 160,
        "NCA": 170,
        "LTO": 75
    }.get(chemistry, 120)

    if pack_density_wh_per_kg <= 0:
        return 0.0

    return pack_energy_kwh * 1000.0 / pack_density_wh_per_kg


def estimate_charging_time_min(pack_energy_kwh, charger_power_kw, initial_soc, final_soc):
    """
    Simplified charging time:
    Energy window / charger power, with 15% overhead for losses/taper.
    """

    if charger_power_kw <= 0:
        return 0.0

    energy_added_kwh = pack_energy_kwh * (final_soc - initial_soc) / 100.0
    time_h = energy_added_kwh / charger_power_kw
    time_min = time_h * 60.0 * 1.15

    return max(time_min, 0.0)


def estimate_charging_cost(pack_energy_kwh, initial_soc, final_soc, tariff_per_kwh):
    energy_added_kwh = pack_energy_kwh * (final_soc - initial_soc) / 100.0
    grid_energy_kwh = energy_added_kwh / 0.92
    return grid_energy_kwh * tariff_per_kwh


def estimate_wh_per_km(pack_energy_kwh, practical_range_km):
    if practical_range_km <= 0:
        return 0.0

    return pack_energy_kwh * 1000.0 / practical_range_km


def infer_motor_type(segment):
    segment_text = str(segment).lower()

    if "two" in segment_text:
        return "BLDC"

    if "bus" in segment_text or "commercial" in segment_text:
        return "IM"

    return "PMSM"


def infer_inverter_device(segment, motor_power_kw):
    segment_text = str(segment).lower()

    if "two" in segment_text:
        return "Si IGBT"

    if motor_power_kw >= 120:
        return "SiC MOSFET"

    return "Si IGBT"


# -------------------------------------------------------
# SCENARIO PAYLOAD BUILDER
# -------------------------------------------------------
def build_scenario_from_vehicle_preset(
    row,
    scenario_name,
    initial_soc,
    final_soc,
    tariff_per_kwh,
    selected_charger_kw,
    override_pack_voltage,
    override_pack_energy,
    notes
):
    vehicle_preset = safe_get(row, "Vehicle_Preset", "Unnamed Preset")
    segment = safe_get(row, "Segment", "Custom")
    reference_model = safe_get(row, "Reference_Model", vehicle_preset)

    chemistry = infer_chemistry(
        safe_get(row, "Chemistry_Assumption", "LFP")
    )

    pack_energy_kwh = float(
        override_pack_energy
        if override_pack_energy > 0
        else safe_get(row, "Usable_Battery_kWh", 0.0)
    )

    pack_voltage = float(
        override_pack_voltage
        if override_pack_voltage > 0
        else estimate_pack_voltage_by_segment(segment)
    )

    pack_capacity_ah = estimate_pack_capacity_ah(
        pack_energy_kwh=pack_energy_kwh,
        pack_voltage=pack_voltage
    )

    total_cells = estimate_cell_count(
        pack_voltage=pack_voltage,
        chemistry=chemistry
    )

    pack_mass = estimate_pack_mass(
        pack_energy_kwh=pack_energy_kwh,
        chemistry=chemistry
    )

    practical_range_km = float(
        safe_get(row, "Practical_Range_km", 0.0)
    )

    claimed_range_km = float(
        safe_get(row, "Claimed_Range_km", 0.0)
    )

    wh_per_km = estimate_wh_per_km(
        pack_energy_kwh=pack_energy_kwh,
        practical_range_km=practical_range_km
    )

    charger_power_kw = float(
        selected_charger_kw
        if selected_charger_kw > 0
        else safe_get(row, "Default_Charger_kW", 7.2)
    )

    charging_time_min = estimate_charging_time_min(
        pack_energy_kwh=pack_energy_kwh,
        charger_power_kw=charger_power_kw,
        initial_soc=initial_soc,
        final_soc=final_soc
    )

    charging_cost = estimate_charging_cost(
        pack_energy_kwh=pack_energy_kwh,
        initial_soc=initial_soc,
        final_soc=final_soc,
        tariff_per_kwh=tariff_per_kwh
    )

    motor_power_kw = float(
        safe_get(row, "Motor_Power_kW", 0.0)
    )

    motor_torque_nm = float(
        safe_get(row, "Motor_Torque_Nm", 0.0)
    )

    motor_type = infer_motor_type(segment)

    inverter_device = infer_inverter_device(
        segment=segment,
        motor_power_kw=motor_power_kw
    )

    inverter_efficiency = 97.0 if inverter_device == "SiC MOSFET" else 95.0

    max_battery_temp = 42.0
    max_motor_temp = 90.0
    max_inverter_temp = 82.0

    payload = {
        "Scenario Metadata": {
            "Scenario Name": scenario_name,
            "Vehicle Segment": segment,
            "Vehicle Preset": vehicle_preset,
            "Reference Model": reference_model,
            "Source": "Real EV Preset Auto-Load",
            "Notes": notes
        },
        "Battery Pack": {
            "Chemistry": chemistry,
            "Nominal Pack Voltage (V)": round(pack_voltage, 2),
            "Pack Energy (kWh)": round(pack_energy_kwh, 3),
            "Pack Capacity (Ah)": round(pack_capacity_ah, 3),
            "Total Cells": int(total_cells),
            "Estimated Pack Mass (kg)": round(pack_mass, 3)
        },
        "Charging": {
            "Initial SOC (%)": initial_soc,
            "Final SOC (%)": final_soc,
            "Charger Power (kW)": round(charger_power_kw, 3),
            "Charging Time (min)": round(charging_time_min, 3),
            "Charging Cost (₹)": round(charging_cost, 3),
            "Tariff (₹/kWh)": tariff_per_kwh
        },
        "Range": {
            "Claimed Range (km)": round(claimed_range_km, 3),
            "Estimated Range (km)": round(practical_range_km, 3),
            "Energy Consumption (Wh/km)": round(wh_per_km, 3),
            "Default Speed (km/h)": safe_get(row, "Default_Speed_kmh", "-"),
            "Default HVAC Load (kW)": safe_get(row, "Default_HVAC_kW", "-"),
            "Auxiliary Load (kW)": safe_get(row, "Auxiliary_Load_kW", "-")
        },
        "BMS and SOC": {
            "SOC Estimation Method": "Hybrid BMS Estimator",
            "Maximum SOC Error (%)": 2.5
        },
        "Motor and Inverter": {
            "Motor Type": motor_type,
            "Peak Motor Power (kW)": round(motor_power_kw, 3),
            "Motor Torque (Nm)": round(motor_torque_nm, 3),
            "Inverter Device": inverter_device,
            "Inverter Efficiency (%)": inverter_efficiency
        },
        "Thermal": {
            "Maximum Battery Temperature (°C)": max_battery_temp,
            "Maximum Motor Temperature (°C)": max_motor_temp,
            "Maximum Inverter Temperature (°C)": max_inverter_temp
        },
        "Engineering Remarks": {
            "Remarks": (
                f"This scenario was auto-created from the {vehicle_preset} preset. "
                f"It is intended for dashboard demonstration and early engineering comparison. "
                f"Official vehicle design work must verify battery, charging, range, thermal, and drivetrain data "
                f"from manufacturer datasheets and test data. {notes}"
            )
        }
    }

    return payload


def flatten_payload_for_display(payload):
    records = []

    for section, values in payload.items():
        if isinstance(values, dict):
            for parameter, value in values.items():
                records.append(
                    {
                        "Section": section,
                        "Parameter": parameter,
                        "Value": value
                    }
                )
        else:
            records.append(
                {
                    "Section": section,
                    "Parameter": "-",
                    "Value": values
                }
            )

    return pd.DataFrame(records)


# -------------------------------------------------------
# STREAMLIT PAGE
# -------------------------------------------------------
def run_preset_to_scenario():
    st.markdown("# Preset to Saved Scenario")
    st.caption("Auto-create a saved EV scenario directly from a Real EV Preset.")

    st.info(
        "This page converts one vehicle preset into a full saved scenario payload. "
        "After saving, the scenario can be used in Saved Scenario Compare, Search & Filters, Dashboard Analytics, and Report Generator."
    )

    vehicle_df = load_vehicle_presets_for_scenario()

    if vehicle_df.empty:
        st.error("No vehicle presets found. Check data/vehicle_presets.csv.")
        return

    tab1, tab2, tab3 = st.tabs(
        [
            "Build from Preset",
            "Scenario Preview",
            "Save Result"
        ]
    )

    with tab1:
        st.markdown("## Select Vehicle Preset")

        selected_preset = st.selectbox(
            "Vehicle preset",
            options=vehicle_df["Vehicle_Preset"].tolist()
        )

        row = vehicle_df[vehicle_df["Vehicle_Preset"] == selected_preset].iloc[0]

        default_scenario_name = f"{selected_preset} Auto Scenario"

        scenario_name = st.text_input(
            "Scenario name",
            value=default_scenario_name
        )

        st.markdown("## Preset Snapshot")

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric(
                "Battery",
                f"{safe_get(row, 'Usable_Battery_kWh', 0)} kWh"
            )

        with c2:
            st.metric(
                "Claimed Range",
                f"{safe_get(row, 'Claimed_Range_km', 0)} km"
            )

        with c3:
            st.metric(
                "Practical Range",
                f"{safe_get(row, 'Practical_Range_km', 0)} km"
            )

        with c4:
            st.metric(
                "Motor Power",
                f"{safe_get(row, 'Motor_Power_kW', 0)} kW"
            )

        st.divider()

        st.markdown("## Scenario Assumptions")

        a1, a2, a3 = st.columns(3)

        with a1:
            soc_window = st.slider(
                "Charging SOC window (%)",
                min_value=0,
                max_value=100,
                value=(10, 80),
                step=1
            )

            initial_soc = soc_window[0]
            final_soc = soc_window[1]

        with a2:
            tariff_per_kwh = st.number_input(
                "Tariff (₹/kWh)",
                min_value=1.0,
                max_value=50.0,
                value=15.0,
                step=0.5,
                format="%.1f"
            )

        with a3:
            selected_charger_kw = st.number_input(
                "Charger power override (kW, 0 = use preset)",
                min_value=0.0,
                max_value=500.0,
                value=0.0,
                step=1.0,
                format="%.1f"
            )

        b1, b2 = st.columns(2)

        with b1:
            override_pack_voltage = st.number_input(
                "Pack voltage override (V, 0 = estimate)",
                min_value=0.0,
                max_value=1000.0,
                value=0.0,
                step=10.0,
                format="%.1f"
            )

        with b2:
            override_pack_energy = st.number_input(
                "Pack energy override (kWh, 0 = use preset)",
                min_value=0.0,
                max_value=300.0,
                value=0.0,
                step=1.0,
                format="%.1f"
            )

        notes = st.text_area(
            "Extra scenario notes",
            value="",
            height=120
        )

        if final_soc <= initial_soc:
            st.error("Final SOC must be greater than initial SOC.")
            return

        payload = build_scenario_from_vehicle_preset(
            row=row,
            scenario_name=scenario_name,
            initial_soc=initial_soc,
            final_soc=final_soc,
            tariff_per_kwh=tariff_per_kwh,
            selected_charger_kw=selected_charger_kw,
            override_pack_voltage=override_pack_voltage,
            override_pack_energy=override_pack_energy,
            notes=notes
        )

        st.session_state["preset_auto_scenario_payload"] = payload

        st.success("Scenario payload generated from selected preset.")

    with tab2:
        st.markdown("## Generated Scenario Preview")

        payload = st.session_state.get("preset_auto_scenario_payload", None)

        if payload is None:
            st.warning("Build a scenario from the first tab.")
        else:
            preview_df = flatten_payload_for_display(payload)

            st.dataframe(
                preview_df,
                use_container_width=True,
                hide_index=True
            )

            st.markdown("## Raw JSON")
            st.json(payload)

    with tab3:
        st.markdown("## Save Generated Scenario")

        payload = st.session_state.get("preset_auto_scenario_payload", None)

        if payload is None:
            st.warning("Build a scenario from the first tab before saving.")
        else:
            scenario_name = payload["Scenario Metadata"]["Scenario Name"]
            segment = payload["Scenario Metadata"]["Vehicle Segment"]
            chemistry = payload["Battery Pack"]["Chemistry"]
            pack_voltage = payload["Battery Pack"]["Nominal Pack Voltage (V)"]
            pack_energy = payload["Battery Pack"]["Pack Energy (kWh)"]
            estimated_range = payload["Range"]["Estimated Range (km)"]
            charging_time = payload["Charging"]["Charging Time (min)"]
            wh_per_km = payload["Range"]["Energy Consumption (Wh/km)"]

            st.markdown("### Save Summary")

            summary_df = pd.DataFrame(
                {
                    "Field": [
                        "Scenario Name",
                        "Vehicle Segment",
                        "Chemistry",
                        "Pack Voltage (V)",
                        "Pack Energy (kWh)",
                        "Estimated Range (km)",
                        "Charging Time (min)",
                        "Wh/km"
                    ],
                    "Value": [
                        scenario_name,
                        segment,
                        chemistry,
                        pack_voltage,
                        pack_energy,
                        estimated_range,
                        charging_time,
                        wh_per_km
                    ]
                }
            )

            st.dataframe(
                summary_df,
                use_container_width=True,
                hide_index=True
            )

            skip_duplicates = st.checkbox(
                "Skip duplicate if identical scenario already exists",
                value=True
            )

            if st.button("Save Preset Scenario to Library"):
                result = save_scenario(
                    scenario_name=scenario_name,
                    vehicle_segment=segment,
                    chemistry=chemistry,
                    pack_voltage=pack_voltage,
                    pack_energy=pack_energy,
                    estimated_range=estimated_range,
                    charging_time=charging_time,
                    wh_per_km=wh_per_km,
                    scenario_data=payload,
                    skip_duplicates=skip_duplicates
                )

                if result["saved"]:
                    st.success(
                        f"Preset scenario saved successfully. Database ID: {result['inserted_id']}"
                    )
                else:
                    st.warning(
                        f"Duplicate skipped. Existing scenario ID: {result['existing_id']} "
                        f"({result['existing_name']})"
                    )