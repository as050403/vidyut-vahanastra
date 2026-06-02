import io
import json
import datetime
import streamlit as st
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak
)


# -------------------------------------------------------
# PAYLOAD CREATION
# -------------------------------------------------------
def build_report_payload(
    project_title,
    engineer_name,
    organization,
    scenario_name,
    chemistry,
    pack_voltage,
    pack_energy,
    pack_capacity,
    total_cells,
    pack_mass,
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
    battery_heat,
    motor_heat,
    inverter_heat,
    max_battery_temp,
    max_motor_temp,
    max_inverter_temp,
    design_remarks
):
    created_on = datetime.datetime.now().strftime("%d %B %Y, %I:%M %p")

    payload = {
        "Report Metadata": {
            "Project Title": project_title,
            "Engineer / User": engineer_name,
            "Organization": organization,
            "Scenario Name": scenario_name,
            "Generated On": created_on
        },
        "Battery Pack Summary": {
            "Chemistry": chemistry,
            "Nominal Pack Voltage (V)": pack_voltage,
            "Pack Energy (kWh)": pack_energy,
            "Pack Capacity (Ah)": pack_capacity,
            "Total Cells": total_cells,
            "Estimated Pack Mass (kg)": pack_mass
        },
        "Charging Summary": {
            "Charger Power (kW)": charger_power,
            "Estimated Charging Time (min)": charging_time,
            "Estimated Charging Cost (₹)": charging_cost
        },
        "Range Summary": {
            "Estimated Range (km)": estimated_range,
            "Energy Consumption (Wh/km)": wh_per_km
        },
        "BMS and SOC Summary": {
            "SOC Estimation Method": soc_method,
            "Maximum SOC Error (%)": max_soc_error
        },
        "Motor and Inverter Summary": {
            "Motor Type": motor_type,
            "Estimated Peak Motor Power (kW)": peak_motor_power,
            "Inverter Device": inverter_device,
            "Inverter Efficiency (%)": inverter_efficiency
        },
        "Thermal Summary": {
            "Battery Heat (kW)": battery_heat,
            "Motor Heat (kW)": motor_heat,
            "Inverter Heat (kW)": inverter_heat,
            "Maximum Battery Temperature (°C)": max_battery_temp,
            "Maximum Motor Temperature (°C)": max_motor_temp,
            "Maximum Inverter Temperature (°C)": max_inverter_temp
        },
        "Engineering Remarks": {
            "Remarks": design_remarks
        }
    }

    return payload


def payload_to_summary_dataframe(payload):
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


# -------------------------------------------------------
# LOADED SCENARIO DEFAULT HELPERS
# -------------------------------------------------------
def get_loaded_value(payload, section, key, default):
    try:
        return payload.get(section, {}).get(key, default)
    except Exception:
        return default


def to_float(value, default):
    try:
        return float(value)
    except Exception:
        return float(default)


def to_int(value, default):
    try:
        return int(value)
    except Exception:
        return int(default)


def get_report_defaults_from_loaded_scenario():
    """
    Reads currently loaded scenario from st.session_state and converts it
    into default values for the Report Generator page.
    """

    loaded = st.session_state.get("loaded_scenario", None)

    defaults = {
        "project_title": "Vidyut Vahanastra: EV Digital Twin Engineering Report",
        "engineer_name": "MEPED",
        "organization": "EV Systems Laboratory",
        "scenario_name": "Indian Compact SUV EV - LFP 400 V Class",

        "chemistry": "LFP",
        "pack_voltage": 307.2,
        "pack_energy": 30.72,
        "pack_capacity": 100.0,
        "total_cells": 96,
        "pack_mass": 295.0,

        "charger_power": 50.0,
        "charging_time": 42.0,
        "charging_cost": 350.0,

        "estimated_range": 230.0,
        "wh_per_km": 135.0,

        "soc_method": "Kalman-Corrected",
        "max_soc_error": 2.5,

        "motor_type": "PMSM",
        "peak_motor_power": 105.0,
        "inverter_device": "SiC MOSFET",
        "inverter_efficiency": 97.0,

        "battery_heat": 2.25,
        "motor_heat": 4.80,
        "inverter_heat": 2.40,
        "max_battery_temp": 38.0,
        "max_motor_temp": 92.0,
        "max_inverter_temp": 85.0,

        "design_remarks": (
            "The selected configuration is suitable for an Indian compact EV use case. "
            "Further validation should include real drive-cycle data, thermal testing, "
            "BMS calibration, and component datasheet verification."
        )
    }

    if loaded is None:
        return defaults, False

    defaults["scenario_name"] = get_loaded_value(
        loaded,
        "Scenario Metadata",
        "Scenario Name",
        defaults["scenario_name"]
    )

    defaults["chemistry"] = get_loaded_value(
        loaded,
        "Battery Pack",
        "Chemistry",
        defaults["chemistry"]
    )

    defaults["pack_voltage"] = to_float(
        get_loaded_value(
            loaded,
            "Battery Pack",
            "Nominal Pack Voltage (V)",
            defaults["pack_voltage"]
        ),
        defaults["pack_voltage"]
    )

    defaults["pack_energy"] = to_float(
        get_loaded_value(
            loaded,
            "Battery Pack",
            "Pack Energy (kWh)",
            defaults["pack_energy"]
        ),
        defaults["pack_energy"]
    )

    defaults["pack_capacity"] = to_float(
        get_loaded_value(
            loaded,
            "Battery Pack",
            "Pack Capacity (Ah)",
            defaults["pack_capacity"]
        ),
        defaults["pack_capacity"]
    )

    defaults["total_cells"] = to_int(
        get_loaded_value(
            loaded,
            "Battery Pack",
            "Total Cells",
            defaults["total_cells"]
        ),
        defaults["total_cells"]
    )

    defaults["pack_mass"] = to_float(
        get_loaded_value(
            loaded,
            "Battery Pack",
            "Estimated Pack Mass (kg)",
            defaults["pack_mass"]
        ),
        defaults["pack_mass"]
    )

    defaults["charger_power"] = to_float(
        get_loaded_value(
            loaded,
            "Charging",
            "Charger Power (kW)",
            defaults["charger_power"]
        ),
        defaults["charger_power"]
    )

    defaults["charging_time"] = to_float(
        get_loaded_value(
            loaded,
            "Charging",
            "Charging Time (min)",
            defaults["charging_time"]
        ),
        defaults["charging_time"]
    )

    defaults["charging_cost"] = to_float(
        get_loaded_value(
            loaded,
            "Charging",
            "Charging Cost (₹)",
            defaults["charging_cost"]
        ),
        defaults["charging_cost"]
    )

    defaults["estimated_range"] = to_float(
        get_loaded_value(
            loaded,
            "Range",
            "Estimated Range (km)",
            defaults["estimated_range"]
        ),
        defaults["estimated_range"]
    )

    defaults["wh_per_km"] = to_float(
        get_loaded_value(
            loaded,
            "Range",
            "Energy Consumption (Wh/km)",
            defaults["wh_per_km"]
        ),
        defaults["wh_per_km"]
    )

    defaults["soc_method"] = get_loaded_value(
        loaded,
        "BMS and SOC",
        "SOC Estimation Method",
        defaults["soc_method"]
    )

    defaults["max_soc_error"] = to_float(
        get_loaded_value(
            loaded,
            "BMS and SOC",
            "Maximum SOC Error (%)",
            defaults["max_soc_error"]
        ),
        defaults["max_soc_error"]
    )

    defaults["motor_type"] = get_loaded_value(
        loaded,
        "Motor and Inverter",
        "Motor Type",
        defaults["motor_type"]
    )

    defaults["peak_motor_power"] = to_float(
        get_loaded_value(
            loaded,
            "Motor and Inverter",
            "Peak Motor Power (kW)",
            defaults["peak_motor_power"]
        ),
        defaults["peak_motor_power"]
    )

    defaults["inverter_device"] = get_loaded_value(
        loaded,
        "Motor and Inverter",
        "Inverter Device",
        defaults["inverter_device"]
    )

    defaults["inverter_efficiency"] = to_float(
        get_loaded_value(
            loaded,
            "Motor and Inverter",
            "Inverter Efficiency (%)",
            defaults["inverter_efficiency"]
        ),
        defaults["inverter_efficiency"]
    )

    defaults["max_battery_temp"] = to_float(
        get_loaded_value(
            loaded,
            "Thermal",
            "Maximum Battery Temperature (°C)",
            defaults["max_battery_temp"]
        ),
        defaults["max_battery_temp"]
    )

    defaults["max_motor_temp"] = to_float(
        get_loaded_value(
            loaded,
            "Thermal",
            "Maximum Motor Temperature (°C)",
            defaults["max_motor_temp"]
        ),
        defaults["max_motor_temp"]
    )

    defaults["max_inverter_temp"] = to_float(
        get_loaded_value(
            loaded,
            "Thermal",
            "Maximum Inverter Temperature (°C)",
            defaults["max_inverter_temp"]
        ),
        defaults["max_inverter_temp"]
    )

    defaults["design_remarks"] = get_loaded_value(
        loaded,
        "Engineering Remarks",
        "Remarks",
        defaults["design_remarks"]
    )

    return defaults, True


# -------------------------------------------------------
# MARKDOWN REPORT
# -------------------------------------------------------
def create_markdown_report(payload):
    lines = []

    title = payload["Report Metadata"]["Project Title"]
    scenario = payload["Report Metadata"]["Scenario Name"]

    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"## Scenario: {scenario}")
    lines.append("")

    for section, values in payload.items():
        lines.append(f"## {section}")
        lines.append("")

        for parameter, value in values.items():
            lines.append(f"- **{parameter}:** {value}")

        lines.append("")

    lines.append("## Disclaimer")
    lines.append("")
    lines.append(
        "This report is generated from simplified engineering models inside Vidyut Vahanastra. "
        "Final EV design validation requires manufacturer datasheets, experimental testing, "
        "drive-cycle validation, thermal characterization, BMS validation, and safety compliance review."
    )

    return "\n".join(lines)


# -------------------------------------------------------
# PDF REPORT
# -------------------------------------------------------
def add_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.drawString(
        0.7 * inch,
        0.45 * inch,
        "Generated by Vidyut Vahanastra - Interactive EV Digital Twin Dashboard"
    )
    canvas.drawRightString(
        7.6 * inch,
        0.45 * inch,
        f"Page {doc.page}"
    )
    canvas.restoreState()


def table_from_dict(title, data_dict, styles):
    elements = []

    elements.append(Paragraph(title, styles["SectionTitle"]))
    elements.append(Spacer(1, 8))

    table_data = [["Parameter", "Value"]]

    for key, value in data_dict.items():
        table_data.append(
            [
                Paragraph(str(key), styles["TableCell"]),
                Paragraph(str(value), styles["TableCell"])
            ]
        )

    table = Table(
        table_data,
        colWidths=[2.7 * inch, 3.8 * inch],
        repeatRows=1
    )

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F8FAFC")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    elements.append(table)
    elements.append(Spacer(1, 14))

    return elements


def create_pdf_report(payload):
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.75 * inch
    )

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="MainTitle",
            parent=styles["Title"],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#0F766E"),
            spaceAfter=14
        )
    )

    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            parent=styles["Heading2"],
            fontSize=12,
            leading=14,
            textColor=colors.HexColor("#0F172A"),
            spaceBefore=8,
            spaceAfter=6
        )
    )

    styles.add(
        ParagraphStyle(
            name="BodySmall",
            parent=styles["BodyText"],
            fontSize=9,
            leading=12
        )
    )

    styles.add(
        ParagraphStyle(
            name="TableCell",
            parent=styles["BodyText"],
            fontSize=8,
            leading=10
        )
    )

    story = []

    title = payload["Report Metadata"]["Project Title"]
    scenario = payload["Report Metadata"]["Scenario Name"]

    story.append(Paragraph(str(title), styles["MainTitle"]))
    story.append(Paragraph(f"<b>Scenario:</b> {scenario}", styles["BodySmall"]))
    story.append(Spacer(1, 12))

    intro_text = (
        "This report summarizes a selected EV design scenario generated using Vidyut Vahanastra, "
        "an interactive EV digital twin dashboard for battery, BMS, powertrain, charging, range, "
        "and thermal experimentation."
    )

    story.append(Paragraph(intro_text, styles["BodySmall"]))
    story.append(Spacer(1, 12))

    for section, values in payload.items():
        story.extend(table_from_dict(section, values, styles))

        if section == "Range Summary":
            story.append(PageBreak())

    disclaimer = (
        "<b>Disclaimer:</b> This report is based on simplified engineering models. "
        "Final vehicle design must be validated using manufacturer datasheets, experimental tests, "
        "drive-cycle data, thermal characterization, BMS validation, insulation coordination, and safety standards."
    )

    story.append(Spacer(1, 10))
    story.append(Paragraph(disclaimer, styles["BodySmall"]))

    doc.build(
        story,
        onFirstPage=add_footer,
        onLaterPages=add_footer
    )

    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes


# -------------------------------------------------------
# JSON REPORT
# -------------------------------------------------------
def create_json_report(payload):
    return json.dumps(payload, indent=4).encode("utf-8")


# -------------------------------------------------------
# STREAMLIT REPORT GENERATOR PAGE
# -------------------------------------------------------
def run_report_generator():
    st.markdown("# Report Generator")
    st.caption("Generate an exportable engineering summary report for Vidyut Vahanastra.")

    defaults, loaded_available = get_report_defaults_from_loaded_scenario()

    if loaded_available:
        st.success(
            "Loaded scenario detected. Report fields are auto-filled from the saved scenario. "
            "You can still manually edit any field before downloading."
        )
    else:
        st.info(
            "No saved scenario is currently loaded. Manual report defaults are shown. "
            "To auto-fill this page, load a scenario from Saved Scenarios first."
        )

    tab1, tab2, tab3 = st.tabs(
        [
            "Report Inputs",
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
                value=defaults["project_title"]
            )

            engineer_name = st.text_input(
                "Engineer / User name",
                value=defaults["engineer_name"]
            )

        with c2:
            organization = st.text_input(
                "Organization / Lab",
                value=defaults["organization"]
            )

            scenario_name = st.text_input(
                "Scenario name",
                value=str(defaults["scenario_name"])
            )

        st.divider()

        st.markdown("## Battery Pack Summary")

        battery_options = ["LFP", "NMC", "NCA", "LTO"]

        if defaults["chemistry"] in battery_options:
            chemistry_index = battery_options.index(defaults["chemistry"])
        else:
            chemistry_index = 0

        b1, b2, b3 = st.columns(3)

        with b1:
            chemistry = st.selectbox(
                "Battery chemistry",
                battery_options,
                index=chemistry_index
            )

            pack_voltage = st.number_input(
                "Nominal pack voltage (V)",
                min_value=12.0,
                max_value=1000.0,
                value=to_float(defaults["pack_voltage"], 307.2),
                step=1.0,
                format="%.1f"
            )

        with b2:
            pack_energy = st.number_input(
                "Pack energy (kWh)",
                min_value=1.0,
                max_value=250.0,
                value=to_float(defaults["pack_energy"], 30.72),
                step=0.5,
                format="%.2f"
            )

            pack_capacity = st.number_input(
                "Pack capacity (Ah)",
                min_value=1.0,
                max_value=1000.0,
                value=to_float(defaults["pack_capacity"], 100.0),
                step=1.0,
                format="%.1f"
            )

        with b3:
            total_cells = st.number_input(
                "Total cell count",
                min_value=1,
                max_value=30000,
                value=to_int(defaults["total_cells"], 96),
                step=1
            )

            pack_mass = st.number_input(
                "Estimated pack mass (kg)",
                min_value=1.0,
                max_value=2000.0,
                value=to_float(defaults["pack_mass"], 295.0),
                step=5.0,
                format="%.1f"
            )

        st.divider()

        st.markdown("## Charging and Range Summary")

        cr1, cr2, cr3 = st.columns(3)

        with cr1:
            charger_power = st.number_input(
                "Charger power (kW)",
                min_value=0.5,
                max_value=500.0,
                value=to_float(defaults["charger_power"], 50.0),
                step=0.5,
                format="%.1f"
            )

            charging_time = st.number_input(
                "Estimated charging time (min)",
                min_value=1.0,
                max_value=2000.0,
                value=to_float(defaults["charging_time"], 42.0),
                step=1.0,
                format="%.1f"
            )

        with cr2:
            charging_cost = st.number_input(
                "Estimated charging cost (₹)",
                min_value=0.0,
                max_value=10000.0,
                value=to_float(defaults["charging_cost"], 350.0),
                step=10.0,
                format="%.1f"
            )

            estimated_range = st.number_input(
                "Estimated range (km)",
                min_value=1.0,
                max_value=1000.0,
                value=to_float(defaults["estimated_range"], 230.0),
                step=5.0,
                format="%.1f"
            )

        with cr3:
            wh_per_km = st.number_input(
                "Energy consumption (Wh/km)",
                min_value=20.0,
                max_value=500.0,
                value=to_float(defaults["wh_per_km"], 135.0),
                step=5.0,
                format="%.1f"
            )

        st.divider()

        st.markdown("## BMS, Motor-Inverter, and Thermal Summary")

        soc_options = [
            "Coulomb Counting",
            "OCV Lookup",
            "Kalman-Corrected",
            "Hybrid BMS Estimator"
        ]

        if defaults["soc_method"] in soc_options:
            soc_index = soc_options.index(defaults["soc_method"])
        else:
            soc_index = 2

        motor_options = ["PMSM", "IM", "BLDC", "IPM"]

        if defaults["motor_type"] in motor_options:
            motor_index = motor_options.index(defaults["motor_type"])
        else:
            motor_index = 0

        inverter_options = ["Si IGBT", "SiC MOSFET", "GaN HEMT"]

        if defaults["inverter_device"] in inverter_options:
            inverter_index = inverter_options.index(defaults["inverter_device"])
        else:
            inverter_index = 1

        s1, s2, s3 = st.columns(3)

        with s1:
            soc_method = st.selectbox(
                "SOC estimation method",
                soc_options,
                index=soc_index
            )

            max_soc_error = st.number_input(
                "Maximum SOC error (%)",
                min_value=0.0,
                max_value=50.0,
                value=to_float(defaults["max_soc_error"], 2.5),
                step=0.1,
                format="%.1f"
            )

        with s2:
            motor_type = st.selectbox(
                "Motor type",
                motor_options,
                index=motor_index
            )

            peak_motor_power = st.number_input(
                "Estimated peak motor power (kW)",
                min_value=1.0,
                max_value=500.0,
                value=to_float(defaults["peak_motor_power"], 105.0),
                step=5.0,
                format="%.1f"
            )

        with s3:
            inverter_device = st.selectbox(
                "Inverter device",
                inverter_options,
                index=inverter_index
            )

            inverter_efficiency = st.number_input(
                "Inverter efficiency (%)",
                min_value=70.0,
                max_value=99.9,
                value=to_float(defaults["inverter_efficiency"], 97.0),
                step=0.1,
                format="%.1f"
            )

        t1, t2, t3 = st.columns(3)

        with t1:
            battery_heat = st.number_input(
                "Battery heat (kW)",
                min_value=0.0,
                max_value=100.0,
                value=to_float(defaults["battery_heat"], 2.25),
                step=0.1,
                format="%.2f"
            )

            max_battery_temp = st.number_input(
                "Max battery temperature (°C)",
                min_value=-10.0,
                max_value=120.0,
                value=to_float(defaults["max_battery_temp"], 38.0),
                step=0.5,
                format="%.1f"
            )

        with t2:
            motor_heat = st.number_input(
                "Motor heat (kW)",
                min_value=0.0,
                max_value=100.0,
                value=to_float(defaults["motor_heat"], 4.80),
                step=0.1,
                format="%.2f"
            )

            max_motor_temp = st.number_input(
                "Max motor temperature (°C)",
                min_value=-10.0,
                max_value=220.0,
                value=to_float(defaults["max_motor_temp"], 92.0),
                step=1.0,
                format="%.1f"
            )

        with t3:
            inverter_heat = st.number_input(
                "Inverter heat (kW)",
                min_value=0.0,
                max_value=100.0,
                value=to_float(defaults["inverter_heat"], 2.40),
                step=0.1,
                format="%.2f"
            )

            max_inverter_temp = st.number_input(
                "Max inverter temperature (°C)",
                min_value=-10.0,
                max_value=220.0,
                value=to_float(defaults["max_inverter_temp"], 85.0),
                step=1.0,
                format="%.1f"
            )

        st.divider()

        design_remarks = st.text_area(
            "Engineering remarks",
            value=str(defaults["design_remarks"]),
            height=160
        )

    payload = build_report_payload(
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

    summary_df = payload_to_summary_dataframe(payload)
    markdown_report = create_markdown_report(payload)
    pdf_report = create_pdf_report(payload)
    json_report = create_json_report(payload)
    csv_report = summary_df.to_csv(index=False).encode("utf-8")

    with tab2:
        st.markdown("## Report Preview")

        st.dataframe(
            summary_df,
            use_container_width=True,
            hide_index=True
        )

        st.markdown("## Markdown Preview")
        st.markdown(markdown_report)

    with tab3:
        st.markdown("## Download Report Files")

        d1, d2, d3, d4 = st.columns(4)

        with d1:
            st.download_button(
                label="Download PDF",
                data=pdf_report,
                file_name="vidyut_vahanastra_report.pdf",
                mime="application/pdf"
            )

        with d2:
            st.download_button(
                label="Download Markdown",
                data=markdown_report.encode("utf-8"),
                file_name="vidyut_vahanastra_report.md",
                mime="text/markdown"
            )

        with d3:
            st.download_button(
                label="Download CSV",
                data=csv_report,
                file_name="vidyut_vahanastra_report.csv",
                mime="text/csv"
            )

        with d4:
            st.download_button(
                label="Download JSON",
                data=json_report,
                file_name="vidyut_vahanastra_report.json",
                mime="application/json"
            )

        st.success("Report files are ready for download.")