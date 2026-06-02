import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from modules.battery_chemistry import load_battery_chemistry_data
from modules.pack_design import classify_voltage_class, estimate_pack_mass
from modules.charging import (
    load_charger_data,
    create_charging_curve,
    calculate_simple_charging_summary,
    get_temperature_derating_factor
)
from modules.range_model import (
    load_vehicle_presets,
    calculate_road_load_range,
    get_temperature_capacity_factor,
    get_driving_style_factor
)


def calculate_pack_from_inputs(
    chemistry_row,
    cell_nominal_voltage,
    cell_full_voltage,
    cell_capacity_ah,
    n_series,
    n_parallel,
    pack_efficiency_factor
):
    v_pack_nominal = n_series * cell_nominal_voltage
    v_pack_full = n_series * cell_full_voltage
    ah_pack = n_parallel * cell_capacity_ah
    energy_wh = v_pack_nominal * ah_pack
    energy_kwh = energy_wh / 1000
    total_cells = n_series * n_parallel

    avg_energy_density = (
        float(chemistry_row["Energy_Density_Min_Whkg"]) +
        float(chemistry_row["Energy_Density_Max_Whkg"])
    ) / 2

    cell_mass_kg, pack_mass_kg = estimate_pack_mass(
        energy_wh=energy_wh,
        avg_cell_energy_density=avg_energy_density,
        pack_efficiency_factor=pack_efficiency_factor
    )

    voltage_class, voltage_description = classify_voltage_class(v_pack_nominal)

    return {
        "Nominal Pack Voltage (V)": v_pack_nominal,
        "Full-Charge Pack Voltage (V)": v_pack_full,
        "Pack Capacity (Ah)": ah_pack,
        "Pack Energy (kWh)": energy_kwh,
        "Total Cells": total_cells,
        "Estimated Cell Mass (kg)": cell_mass_kg,
        "Estimated Pack Mass (kg)": pack_mass_kg,
        "Voltage Class": voltage_class,
        "Voltage Class Description": voltage_description,
        "Average Cell Energy Density (Wh/kg)": avg_energy_density
    }


def calculate_charging_from_inputs(
    battery_capacity_kwh,
    initial_soc,
    final_soc,
    charger_power_kw,
    charger_efficiency,
    charging_temp_condition,
    tariff_per_kwh,
    taper_start_soc
):
    temp_derating = get_temperature_derating_factor(charging_temp_condition)

    summary = calculate_simple_charging_summary(
        battery_capacity_kwh=battery_capacity_kwh,
        initial_soc=initial_soc,
        final_soc=final_soc,
        charger_power_kw=charger_power_kw,
        charger_efficiency=charger_efficiency,
        temp_derating_factor=temp_derating,
        tariff_per_kwh=tariff_per_kwh
    )

    curve = create_charging_curve(
        battery_capacity_kwh=battery_capacity_kwh,
        initial_soc=initial_soc,
        final_soc=final_soc,
        charger_power_kw=charger_power_kw,
        charger_efficiency=charger_efficiency,
        temp_derating_factor=temp_derating,
        taper_start_soc=taper_start_soc
    )

    charging_time_min = float(curve["Time (min)"].iloc[-1])

    return {
        "Charging Time (min)": charging_time_min,
        "Battery Energy Added (kWh)": summary["battery_energy_added_kwh"],
        "Grid Energy Used (kWh)": summary["energy_from_grid_kwh"],
        "Charging Cost (₹)": summary["estimated_cost"],
        "Effective Charging Power (kW)": summary["effective_battery_power_kw"],
        "Charging Temperature Derating (%)": temp_derating * 100
    }


def calculate_range_from_inputs(
    usable_battery_kwh,
    vehicle_row,
    payload_kg,
    speed_kmh,
    hvac_kw,
    auxiliary_kw,
    grade_percent,
    range_temp_condition,
    driving_style
):
    temp_factor = get_temperature_capacity_factor(range_temp_condition)
    driving_factor = get_driving_style_factor(driving_style)

    result = calculate_road_load_range(
        usable_battery_kwh=usable_battery_kwh,
        mass_kg=float(vehicle_row["Mass_kg"]),
        payload_kg=payload_kg,
        speed_kmh=speed_kmh,
        cd=float(vehicle_row["Cd"]),
        frontal_area_m2=float(vehicle_row["Frontal_Area_m2"]),
        crr=float(vehicle_row["Crr"]),
        drivetrain_efficiency=float(vehicle_row["Drivetrain_Efficiency"]),
        hvac_kw=hvac_kw,
        auxiliary_kw=auxiliary_kw,
        grade_percent=grade_percent,
        temperature_factor=temp_factor,
        driving_style_factor=driving_factor
    )

    return {
        "Estimated Range (km)": result["estimated_range_km"],
        "Energy Consumption (Wh/km)": result["wh_per_km"],
        "Battery Power Demand (kW)": result["total_battery_power_kw"],
        "Usable Energy After Temperature (kWh)": result["usable_energy_after_temp_kwh"],
        "Total Vehicle Mass (kg)": result["total_mass_kg"]
    }


def collect_scenario_inputs(
    label,
    key_prefix,
    chemistry_df,
    vehicle_df,
    charger_df,
    default_chemistry_index,
    default_vehicle_index,
    default_charger_index,
    default_series,
    default_parallel,
    default_cell_ah
):
    st.markdown(f"### {label}")

    selected_chemistry = st.selectbox(
        f"{label} chemistry",
        options=chemistry_df["Chemistry"].tolist(),
        index=default_chemistry_index,
        key=f"{key_prefix}_chemistry"
    )

    chemistry_row = chemistry_df[chemistry_df["Chemistry"] == selected_chemistry].iloc[0]

    selected_vehicle = st.selectbox(
        f"{label} vehicle preset",
        options=vehicle_df["Vehicle_Preset"].tolist(),
        index=default_vehicle_index,
        key=f"{key_prefix}_vehicle"
    )

    vehicle_row = vehicle_df[vehicle_df["Vehicle_Preset"] == selected_vehicle].iloc[0]

    charger_options = [
        f"{row['Charger_Type']} - {row['Power_kW']} kW"
        for _, row in charger_df.iterrows()
    ]

    selected_charger_option = st.selectbox(
        f"{label} charger preset",
        options=charger_options,
        index=default_charger_index,
        key=f"{key_prefix}_charger"
    )

    selected_charger_index = charger_options.index(selected_charger_option)
    charger_row = charger_df.iloc[selected_charger_index]

    st.markdown("#### Battery Pack Inputs")

    col1, col2 = st.columns(2)

    with col1:
        cell_nominal_voltage = st.number_input(
            f"{label} cell nominal voltage (V)",
            min_value=1.0,
            max_value=5.0,
            value=float(chemistry_row["Nominal_Voltage_V"]),
            step=0.1,
            format="%.2f",
            key=f"{key_prefix}_cell_nom"
        )

        cell_capacity_ah = st.number_input(
            f"{label} cell capacity (Ah)",
            min_value=1.0,
            max_value=500.0,
            value=float(default_cell_ah),
            step=1.0,
            format="%.1f",
            key=f"{key_prefix}_cell_ah"
        )

        n_series = st.number_input(
            f"{label} series cells (S)",
            min_value=1,
            max_value=300,
            value=int(default_series),
            step=1,
            key=f"{key_prefix}_series"
        )

    with col2:
        cell_full_voltage = st.number_input(
            f"{label} cell full-charge voltage (V)",
            min_value=1.0,
            max_value=5.0,
            value=float(chemistry_row["Full_Charge_V"]),
            step=0.1,
            format="%.2f",
            key=f"{key_prefix}_cell_full"
        )

        n_parallel = st.number_input(
            f"{label} parallel strings (P)",
            min_value=1,
            max_value=100,
            value=int(default_parallel),
            step=1,
            key=f"{key_prefix}_parallel"
        )

        pack_efficiency_factor = st.slider(
            f"{label} pack density factor",
            min_value=0.50,
            max_value=0.90,
            value=0.65,
            step=0.01,
            key=f"{key_prefix}_pack_factor"
        )

    st.markdown("#### Charging Inputs")

    col3, col4 = st.columns(2)

    with col3:
        soc_range = st.slider(
            f"{label} charging SOC window (%)",
            min_value=0,
            max_value=100,
            value=(10, 80),
            step=1,
            key=f"{key_prefix}_soc_range"
        )

        charger_power_kw = st.number_input(
            f"{label} charger power (kW)",
            min_value=0.5,
            max_value=500.0,
            value=float(charger_row["Power_kW"]),
            step=0.5,
            format="%.1f",
            key=f"{key_prefix}_charger_power"
        )

        charging_temp_condition = st.selectbox(
            f"{label} charging temperature",
            [
                "Cold battery (<15°C)",
                "Cool battery (15–25°C)",
                "Optimal battery (25–35°C)",
                "Hot battery (35–45°C)",
                "Very hot battery (>45°C)"
            ],
            index=2,
            key=f"{key_prefix}_charge_temp"
        )

    with col4:
        charger_efficiency = st.slider(
            f"{label} charger efficiency",
            min_value=0.80,
            max_value=0.99,
            value=0.92,
            step=0.01,
            key=f"{key_prefix}_charger_eff"
        )

        tariff_per_kwh = st.number_input(
            f"{label} tariff (₹/kWh)",
            min_value=1.0,
            max_value=50.0,
            value=15.0,
            step=0.5,
            format="%.1f",
            key=f"{key_prefix}_tariff"
        )

        taper_start_soc = st.slider(
            f"{label} taper start SOC (%)",
            min_value=50,
            max_value=95,
            value=80,
            step=1,
            key=f"{key_prefix}_taper"
        )

    st.markdown("#### Range Inputs")

    col5, col6 = st.columns(2)

    with col5:
        speed_kmh = st.slider(
            f"{label} average speed (km/h)",
            min_value=10,
            max_value=140,
            value=int(vehicle_row["Default_Speed_kmh"]),
            step=5,
            key=f"{key_prefix}_speed"
        )

        payload_kg = st.number_input(
            f"{label} payload (kg)",
            min_value=0.0,
            max_value=3000.0,
            value=150.0,
            step=10.0,
            format="%.1f",
            key=f"{key_prefix}_payload"
        )

        hvac_kw = st.number_input(
            f"{label} HVAC load (kW)",
            min_value=0.0,
            max_value=10.0,
            value=float(vehicle_row["Default_HVAC_kW"]),
            step=0.1,
            format="%.1f",
            key=f"{key_prefix}_hvac"
        )

    with col6:
        auxiliary_kw = st.number_input(
            f"{label} auxiliary load (kW)",
            min_value=0.0,
            max_value=5.0,
            value=float(vehicle_row["Auxiliary_Load_kW"]),
            step=0.1,
            format="%.1f",
            key=f"{key_prefix}_aux"
        )

        grade_percent = st.slider(
            f"{label} road grade (%)",
            min_value=-5.0,
            max_value=10.0,
            value=0.0,
            step=0.5,
            key=f"{key_prefix}_grade"
        )

        range_temp_condition = st.selectbox(
            f"{label} range temperature",
            [
                "Cold (<10°C)",
                "Cool (10–20°C)",
                "Optimal (20–35°C)",
                "Hot (35–45°C)",
                "Very Hot (>45°C)"
            ],
            index=2,
            key=f"{key_prefix}_range_temp"
        )

    driving_style = st.selectbox(
        f"{label} driving style",
        [
            "Eco / Smooth",
            "Normal",
            "Urban Stop-Go with Regen",
            "Highway Cruise",
            "Aggressive",
            "Monsoon / Wet Roads"
        ],
        index=1,
        key=f"{key_prefix}_style"
    )

    return {
        "Scenario": label,
        "Chemistry": selected_chemistry,
        "Chemistry Row": chemistry_row,
        "Vehicle Preset": selected_vehicle,
        "Vehicle Row": vehicle_row,
        "Charger Preset": selected_charger_option,
        "Cell Nominal Voltage": cell_nominal_voltage,
        "Cell Full Voltage": cell_full_voltage,
        "Cell Capacity Ah": cell_capacity_ah,
        "Series": int(n_series),
        "Parallel": int(n_parallel),
        "Pack Efficiency Factor": pack_efficiency_factor,
        "Initial SOC": soc_range[0],
        "Final SOC": soc_range[1],
        "Charger Power kW": charger_power_kw,
        "Charger Efficiency": charger_efficiency,
        "Charging Temperature": charging_temp_condition,
        "Tariff": tariff_per_kwh,
        "Taper Start SOC": taper_start_soc,
        "Speed kmh": speed_kmh,
        "Payload kg": payload_kg,
        "HVAC kW": hvac_kw,
        "Auxiliary kW": auxiliary_kw,
        "Grade Percent": grade_percent,
        "Range Temperature": range_temp_condition,
        "Driving Style": driving_style
    }


def evaluate_scenario(inputs):
    pack = calculate_pack_from_inputs(
        chemistry_row=inputs["Chemistry Row"],
        cell_nominal_voltage=inputs["Cell Nominal Voltage"],
        cell_full_voltage=inputs["Cell Full Voltage"],
        cell_capacity_ah=inputs["Cell Capacity Ah"],
        n_series=inputs["Series"],
        n_parallel=inputs["Parallel"],
        pack_efficiency_factor=inputs["Pack Efficiency Factor"]
    )

    charging = calculate_charging_from_inputs(
        battery_capacity_kwh=pack["Pack Energy (kWh)"],
        initial_soc=inputs["Initial SOC"],
        final_soc=inputs["Final SOC"],
        charger_power_kw=inputs["Charger Power kW"],
        charger_efficiency=inputs["Charger Efficiency"],
        charging_temp_condition=inputs["Charging Temperature"],
        tariff_per_kwh=inputs["Tariff"],
        taper_start_soc=inputs["Taper Start SOC"]
    )

    range_outputs = calculate_range_from_inputs(
        usable_battery_kwh=pack["Pack Energy (kWh)"],
        vehicle_row=inputs["Vehicle Row"],
        payload_kg=inputs["Payload kg"],
        speed_kmh=inputs["Speed kmh"],
        hvac_kw=inputs["HVAC kW"],
        auxiliary_kw=inputs["Auxiliary kW"],
        grade_percent=inputs["Grade Percent"],
        range_temp_condition=inputs["Range Temperature"],
        driving_style=inputs["Driving Style"]
    )

    combined = {
        "Scenario": inputs["Scenario"],
        "Chemistry": inputs["Chemistry"],
        "Vehicle Preset": inputs["Vehicle Preset"],
        "Charger Preset": inputs["Charger Preset"],
        "Configuration": f"{inputs['Series']}S{inputs['Parallel']}P",
        **pack,
        **charging,
        **range_outputs
    }

    return combined


def create_comparison_dataframe(result_a, result_b):
    rows = [
        "Chemistry",
        "Vehicle Preset",
        "Charger Preset",
        "Configuration",
        "Voltage Class",
        "Nominal Pack Voltage (V)",
        "Full-Charge Pack Voltage (V)",
        "Pack Capacity (Ah)",
        "Pack Energy (kWh)",
        "Total Cells",
        "Estimated Pack Mass (kg)",
        "Charging Time (min)",
        "Battery Energy Added (kWh)",
        "Charging Cost (₹)",
        "Effective Charging Power (kW)",
        "Estimated Range (km)",
        "Energy Consumption (Wh/km)",
        "Battery Power Demand (kW)",
        "Usable Energy After Temperature (kWh)",
        "Total Vehicle Mass (kg)"
    ]

    data = []

    for row in rows:
        a_val = result_a.get(row, "-")
        b_val = result_b.get(row, "-")

        if isinstance(a_val, float):
            a_val = round(a_val, 2)
        if isinstance(b_val, float):
            b_val = round(b_val, 2)

        data.append(
            {
                "Metric": row,
                "Scenario A": a_val,
                "Scenario B": b_val
            }
        )

    return pd.DataFrame(data)


def create_metric_bar_chart(result_a, result_b, metric_name, title, y_axis):
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=["Scenario A", "Scenario B"],
            y=[result_a[metric_name], result_b[metric_name]],
            text=[round(result_a[metric_name], 2), round(result_b[metric_name], 2)],
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


def create_winner_summary(result_a, result_b):
    summary = []

    if result_a["Estimated Range (km)"] > result_b["Estimated Range (km)"]:
        summary.append(("Range Winner", "Scenario A", "Higher estimated driving range."))
    elif result_b["Estimated Range (km)"] > result_a["Estimated Range (km)"]:
        summary.append(("Range Winner", "Scenario B", "Higher estimated driving range."))
    else:
        summary.append(("Range Winner", "Tie", "Both scenarios have similar estimated range."))

    if result_a["Charging Time (min)"] < result_b["Charging Time (min)"]:
        summary.append(("Charging Winner", "Scenario A", "Lower estimated charging time."))
    elif result_b["Charging Time (min)"] < result_a["Charging Time (min)"]:
        summary.append(("Charging Winner", "Scenario B", "Lower estimated charging time."))
    else:
        summary.append(("Charging Winner", "Tie", "Both scenarios have similar charging time."))

    if result_a["Estimated Pack Mass (kg)"] < result_b["Estimated Pack Mass (kg)"]:
        summary.append(("Pack Mass Winner", "Scenario A", "Lower estimated pack mass."))
    elif result_b["Estimated Pack Mass (kg)"] < result_a["Estimated Pack Mass (kg)"]:
        summary.append(("Pack Mass Winner", "Scenario B", "Lower estimated pack mass."))
    else:
        summary.append(("Pack Mass Winner", "Tie", "Both packs have similar estimated mass."))

    if result_a["Energy Consumption (Wh/km)"] < result_b["Energy Consumption (Wh/km)"]:
        summary.append(("Efficiency Winner", "Scenario A", "Lower Wh/km consumption."))
    elif result_b["Energy Consumption (Wh/km)"] < result_a["Energy Consumption (Wh/km)"]:
        summary.append(("Efficiency Winner", "Scenario B", "Lower Wh/km consumption."))
    else:
        summary.append(("Efficiency Winner", "Tie", "Both scenarios have similar Wh/km."))

    return pd.DataFrame(summary, columns=["Category", "Winner", "Reason"])


def run_scenario_compare():
    st.markdown("# Scenario Compare")
    st.caption("Compare two EV configurations across battery pack, charging, and range performance.")

    st.info(
        "Scenario Compare connects the Battery Chemistry Lab, Pack Design Lab, Charging Lab, and Range Lab into one decision-support view."
    )

    chemistry_df = load_battery_chemistry_data()
    vehicle_df = load_vehicle_presets()
    charger_df = load_charger_data()

    with st.form("scenario_compare_form"):
        col_a, col_b = st.columns(2)

        with col_a:
            scenario_a_inputs = collect_scenario_inputs(
                label="Scenario A",
                key_prefix="a",
                chemistry_df=chemistry_df,
                vehicle_df=vehicle_df,
                charger_df=charger_df,
                default_chemistry_index=0,
                default_vehicle_index=2,
                default_charger_index=7,
                default_series=96,
                default_parallel=1,
                default_cell_ah=100
            )

        with col_b:
            scenario_b_inputs = collect_scenario_inputs(
                label="Scenario B",
                key_prefix="b",
                chemistry_df=chemistry_df,
                vehicle_df=vehicle_df,
                charger_df=charger_df,
                default_chemistry_index=1,
                default_vehicle_index=3,
                default_charger_index=8,
                default_series=216,
                default_parallel=2,
                default_cell_ah=50
            )

        submitted = st.form_submit_button("Compare Scenarios")

    if not submitted:
        st.warning("Adjust the two scenarios and click **Compare Scenarios**.")
        return

    if scenario_a_inputs["Final SOC"] <= scenario_a_inputs["Initial SOC"]:
        st.error("Scenario A final SOC must be greater than initial SOC.")
        return

    if scenario_b_inputs["Final SOC"] <= scenario_b_inputs["Initial SOC"]:
        st.error("Scenario B final SOC must be greater than initial SOC.")
        return

    result_a = evaluate_scenario(scenario_a_inputs)
    result_b = evaluate_scenario(scenario_b_inputs)

    st.divider()

    st.markdown("## Top-Level Comparison")

    m1, m2, m3, m4 = st.columns(4)

    with m1:
        st.metric(
            "Range Difference",
            f"{abs(result_a['Estimated Range (km)'] - result_b['Estimated Range (km)']):.1f} km"
        )

    with m2:
        st.metric(
            "Charging Time Difference",
            f"{abs(result_a['Charging Time (min)'] - result_b['Charging Time (min)']):.1f} min"
        )

    with m3:
        st.metric(
            "Pack Energy Difference",
            f"{abs(result_a['Pack Energy (kWh)'] - result_b['Pack Energy (kWh)']):.1f} kWh"
        )

    with m4:
        st.metric(
            "Pack Mass Difference",
            f"{abs(result_a['Estimated Pack Mass (kg)'] - result_b['Estimated Pack Mass (kg)']):.1f} kg"
        )

    st.divider()

    st.markdown("## Scenario Comparison Table")

    comparison_df = create_comparison_dataframe(result_a, result_b)
    st.dataframe(comparison_df, use_container_width=True, hide_index=True)

    st.divider()

    st.markdown("## Visual Comparison")

    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(
            create_metric_bar_chart(
                result_a,
                result_b,
                metric_name="Estimated Range (km)",
                title="Estimated Range Comparison",
                y_axis="Range (km)"
            ),
            use_container_width=True
        )

    with col2:
        st.plotly_chart(
            create_metric_bar_chart(
                result_a,
                result_b,
                metric_name="Charging Time (min)",
                title="Charging Time Comparison",
                y_axis="Time (min)"
            ),
            use_container_width=True
        )

    col3, col4 = st.columns(2)

    with col3:
        st.plotly_chart(
            create_metric_bar_chart(
                result_a,
                result_b,
                metric_name="Pack Energy (kWh)",
                title="Pack Energy Comparison",
                y_axis="Energy (kWh)"
            ),
            use_container_width=True
        )

    with col4:
        st.plotly_chart(
            create_metric_bar_chart(
                result_a,
                result_b,
                metric_name="Energy Consumption (Wh/km)",
                title="Energy Consumption Comparison",
                y_axis="Wh/km"
            ),
            use_container_width=True
        )

    st.divider()

    st.markdown("## Decision Summary")

    winner_df = create_winner_summary(result_a, result_b)
    st.dataframe(winner_df, use_container_width=True, hide_index=True)

    st.markdown("## Engineering Interpretation")

    if result_a["Chemistry"] == "LFP":
        st.success("Scenario A uses LFP, which is generally strong for Indian EV safety, thermal stability, and cycle life.")
    if result_b["Chemistry"] == "LFP":
        st.success("Scenario B uses LFP, which is generally strong for Indian EV safety, thermal stability, and cycle life.")

    if result_a["Pack Energy (kWh)"] > result_b["Pack Energy (kWh)"]:
        st.info("Scenario A has the larger battery pack, so it has a higher energy reserve but may also carry more mass.")
    elif result_b["Pack Energy (kWh)"] > result_a["Pack Energy (kWh)"]:
        st.info("Scenario B has the larger battery pack, so it has a higher energy reserve but may also carry more mass.")

    if result_a["Charging Time (min)"] < result_b["Charging Time (min)"]:
        st.success("Scenario A is faster to charge for the selected SOC window.")
    elif result_b["Charging Time (min)"] < result_a["Charging Time (min)"]:
        st.success("Scenario B is faster to charge for the selected SOC window.")

    if result_a["Energy Consumption (Wh/km)"] < result_b["Energy Consumption (Wh/km)"]:
        st.success("Scenario A is more energy efficient under the selected driving condition.")
    elif result_b["Energy Consumption (Wh/km)"] < result_a["Energy Consumption (Wh/km)"]:
        st.success("Scenario B is more energy efficient under the selected driving condition.")

    st.warning(
        "This comparison is an early engineering estimate. For industry validation, add drive-cycle simulation, "
        "battery current limits, thermal derating maps, inverter efficiency maps, motor efficiency maps, and real charger curves."
    )