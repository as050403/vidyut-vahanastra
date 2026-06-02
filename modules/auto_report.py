import json
import streamlit as st

from modules.report_generator import (
    build_report_payload,
    payload_to_summary_dataframe,
    create_markdown_report,
    create_pdf_report,
    create_json_report
)


def get_nested(payload, section, key, default="Not available"):
    try:
        return payload.get(section, {}).get(key, default)
    except Exception:
        return default


def build_payload_from_loaded_scenario(
    loaded_scenario,
    project_title,
    engineer_name,
    organization,
    battery_heat,
    motor_heat,
    inverter_heat
):
    scenario_name = get_nested(
        loaded_scenario,
        "Scenario Metadata",
        "Scenario Name",
        "Loaded Vidyut Vahanastra Scenario"
    )

    chemistry = get_nested(
        loaded_scenario,
        "Battery Pack",
        "Chemistry",
        "Not available"
    )

    pack_voltage = get_nested(
        loaded_scenario,
        "Battery Pack",
        "Nominal Pack Voltage (V)",
        "Not available"
    )

    pack_energy = get_nested(
        loaded_scenario,
        "Battery Pack",
        "Pack Energy (kWh)",
        "Not available"
    )

    pack_capacity = get_nested(
        loaded_scenario,
        "Battery Pack",
        "Pack Capacity (Ah)",
        "Not available"
    )

    total_cells = get_nested(
        loaded_scenario,
        "Battery Pack",
        "Total Cells",
        "Not available"
    )

    pack_mass = get_nested(
        loaded_scenario,
        "Battery Pack",
        "Estimated Pack Mass (kg)",
        "Not available"
    )

    charger_power = get_nested(
        loaded_scenario,
        "Charging",
        "Charger Power (kW)",
        "Not available"
    )

    charging_time = get_nested(
        loaded_scenario,
        "Charging",
        "Charging Time (min)",
        "Not available"
    )

    charging_cost = get_nested(
        loaded_scenario,
        "Charging",
        "Charging Cost (₹)",
        "Not available"
    )

    estimated_range = get_nested(
        loaded_scenario,
        "Range",
        "Estimated Range (km)",
        "Not available"
    )

    wh_per_km = get_nested(
        loaded_scenario,
        "Range",
        "Energy Consumption (Wh/km)",
        "Not available"
    )

    soc_method = get_nested(
        loaded_scenario,
        "BMS and SOC",
        "SOC Estimation Method",
        "Not available"
    )

    max_soc_error = get_nested(
        loaded_scenario,
        "BMS and SOC",
        "Maximum SOC Error (%)",
        "Not available"
    )

    motor_type = get_nested(
        loaded_scenario,
        "Motor and Inverter",
        "Motor Type",
        "Not available"
    )

    peak_motor_power = get_nested(
        loaded_scenario,
        "Motor and Inverter",
        "Peak Motor Power (kW)",
        "Not available"
    )

    inverter_device = get_nested(
        loaded_scenario,
        "Motor and Inverter",
        "Inverter Device",
        "Not available"
    )

    inverter_efficiency = get_nested(
        loaded_scenario,
        "Motor and Inverter",
        "Inverter Efficiency (%)",
        "Not available"
    )

    max_battery_temp = get_nested(
        loaded_scenario,
        "Thermal",
        "Maximum Battery Temperature (°C)",
        "Not available"
    )

    max_motor_temp = get_nested(
        loaded_scenario,
        "Thermal",
        "Maximum Motor Temperature (°C)",
        "Not available"
    )

    max_inverter_temp = get_nested(
        loaded_scenario,
        "Thermal",
        "Maximum Inverter Temperature (°C)",
        "Not available"
    )

    design_remarks = get_nested(
        loaded_scenario,
        "Engineering Remarks",
        "Remarks",
        "No remarks stored with this scenario."
    )

    return build_report_payload(
        project_title=project_title,
        engineer_name=engineer_name,
        organization=organization,
        scenario_name=scenario_name,
        chemistry=chemistry,
        pack_voltage=pack_voltage,
        pack_energy=pack_energy,
        pack_capacity=pack_capacity,
        total_cells=total_cells,
        pack_mass=pack_mass,
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
        battery_heat=battery_heat,
        motor_heat=motor_heat,
        inverter_heat=inverter_heat,
        max_battery_temp=max_battery_temp,
        max_motor_temp=max_motor_temp,
        max_inverter_temp=max_inverter_temp,
        design_remarks=design_remarks
    )


def run_auto_report_from_saved_scenario():
    st.markdown("# Auto Report from Saved Scenario")
    st.caption("Generate a complete engineering report directly from the currently loaded saved scenario.")

    st.info(
        "First load a scenario from the Saved Scenarios page. This page will then convert it automatically into PDF, Markdown, CSV, and JSON reports."
    )

    if "loaded_scenario" not in st.session_state:
        st.warning("No scenario is currently loaded. Go to **Saved Scenarios → Scenario Library → Load Scenario** first.")
        return

    loaded_scenario = st.session_state["loaded_scenario"]

    st.success("Loaded scenario detected.")

    tab1, tab2, tab3 = st.tabs(
        [
            "Report Settings",
            "Preview",
            "Downloads"
        ]
    )

    with tab1:
        st.markdown("## Report Metadata")

        c1, c2 = st.columns(2)

        with c1:
            project_title = st.text_input(
                "Project title",
                value="Vidyut Vahanastra: Auto-Generated EV Digital Twin Report"
            )

            engineer_name = st.text_input(
                "Engineer / User name",
                value="MEPED"
            )

        with c2:
            organization = st.text_input(
                "Organization / Lab",
                value="EV Systems Laboratory"
            )

            scenario_name = get_nested(
                loaded_scenario,
                "Scenario Metadata",
                "Scenario Name",
                "Loaded Scenario"
            )

            st.text_input(
                "Loaded scenario name",
                value=str(scenario_name),
                disabled=True
            )

        st.divider()

        st.markdown("## Missing Thermal Heat Inputs")

        st.write(
            "Saved scenarios currently store maximum temperatures, but not always heat-generation values. "
            "Enter heat values here so the final report has a complete thermal summary."
        )

        h1, h2, h3 = st.columns(3)

        with h1:
            battery_heat = st.number_input(
                "Battery heat (kW)",
                min_value=0.0,
                max_value=100.0,
                value=2.25,
                step=0.1,
                format="%.2f"
            )

        with h2:
            motor_heat = st.number_input(
                "Motor heat (kW)",
                min_value=0.0,
                max_value=100.0,
                value=4.80,
                step=0.1,
                format="%.2f"
            )

        with h3:
            inverter_heat = st.number_input(
                "Inverter heat (kW)",
                min_value=0.0,
                max_value=100.0,
                value=2.40,
                step=0.1,
                format="%.2f"
            )

        st.markdown("## Loaded Scenario Snapshot")
        st.json(loaded_scenario)

    payload = build_payload_from_loaded_scenario(
        loaded_scenario=loaded_scenario,
        project_title=project_title,
        engineer_name=engineer_name,
        organization=organization,
        battery_heat=battery_heat,
        motor_heat=motor_heat,
        inverter_heat=inverter_heat
    )

    summary_df = payload_to_summary_dataframe(payload)
    markdown_report = create_markdown_report(payload)
    pdf_report = create_pdf_report(payload)
    json_report = create_json_report(payload)
    csv_report = summary_df.to_csv(index=False).encode("utf-8")

    with tab2:
        st.markdown("## Auto-Generated Report Preview")

        st.dataframe(
            summary_df,
            use_container_width=True,
            hide_index=True
        )

        st.markdown("## Markdown Preview")
        st.markdown(markdown_report)

    with tab3:
        st.markdown("## Download Auto-Generated Report")

        d1, d2, d3, d4 = st.columns(4)

        with d1:
            st.download_button(
                label="Download PDF",
                data=pdf_report,
                file_name="vidyut_vahanastra_auto_report.pdf",
                mime="application/pdf"
            )

        with d2:
            st.download_button(
                label="Download Markdown",
                data=markdown_report.encode("utf-8"),
                file_name="vidyut_vahanastra_auto_report.md",
                mime="text/markdown"
            )

        with d3:
            st.download_button(
                label="Download CSV",
                data=csv_report,
                file_name="vidyut_vahanastra_auto_report.csv",
                mime="text/csv"
            )

        with d4:
            st.download_button(
                label="Download JSON",
                data=json_report,
                file_name="vidyut_vahanastra_auto_report.json",
                mime="application/json"
            )

        st.success("Auto-report files are ready.")