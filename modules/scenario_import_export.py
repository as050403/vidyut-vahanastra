import json
import pandas as pd
import streamlit as st

from utils.scenario_store import (
    save_scenario,
    list_scenarios,
    list_scenarios_with_hash,
    get_scenario_by_id,
    create_scenario_hash,
    scenario_hash_exists
)


# -------------------------------------------------------
# SAFE VALUE HELPERS
# -------------------------------------------------------
def get_nested(payload, section, key, default=None):
    try:
        return payload.get(section, {}).get(key, default)
    except Exception:
        return default


def to_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return float(default)


# -------------------------------------------------------
# VALIDATION HELPERS
# -------------------------------------------------------
def validate_scenario_payload(payload):
    """
    Validates whether uploaded JSON follows the expected
    Vidyut Vahanastra single-scenario structure.
    """

    required_sections = [
        "Scenario Metadata",
        "Battery Pack",
        "Charging",
        "Range"
    ]

    if not isinstance(payload, dict):
        return False, "Uploaded JSON must contain a dictionary/object at the top level."

    missing_sections = [
        section for section in required_sections
        if section not in payload
    ]

    if missing_sections:
        return False, f"Missing required sections: {', '.join(missing_sections)}"

    scenario_name = get_nested(
        payload,
        "Scenario Metadata",
        "Scenario Name",
        None
    )

    chemistry = get_nested(
        payload,
        "Battery Pack",
        "Chemistry",
        None
    )

    if scenario_name is None:
        return False, "Missing Scenario Metadata → Scenario Name."

    if chemistry is None:
        return False, "Missing Battery Pack → Chemistry."

    return True, "Scenario JSON is valid."


def is_bundle_payload(payload):
    """
    Detects whether uploaded JSON is a Vidyut Vahanastra scenario bundle.

    Expected bundle format:
    {
        "Bundle Metadata": {...},
        "Scenarios": [
            {
                "Scenario ID": ...,
                "Scenario Name": ...,
                "Scenario Data": {...}
            }
        ]
    }
    """

    if not isinstance(payload, dict):
        return False

    if "Scenarios" not in payload:
        return False

    if not isinstance(payload["Scenarios"], list):
        return False

    return True


def validate_bundle_payload(payload):
    """
    Validates complete scenario-bundle JSON.
    """

    if not is_bundle_payload(payload):
        return False, "Uploaded JSON is not a valid scenario bundle."

    scenarios = payload.get("Scenarios", [])

    if len(scenarios) == 0:
        return False, "Scenario bundle contains zero scenarios."

    invalid_items = []

    for idx, item in enumerate(scenarios):
        if not isinstance(item, dict):
            invalid_items.append(f"Item {idx + 1}: not a dictionary")
            continue

        scenario_data = item.get("Scenario Data", None)

        if scenario_data is None:
            invalid_items.append(f"Item {idx + 1}: missing Scenario Data")
            continue

        is_valid, message = validate_scenario_payload(scenario_data)

        if not is_valid:
            invalid_items.append(f"Item {idx + 1}: {message}")

    if invalid_items:
        return False, "; ".join(invalid_items)

    return True, f"Valid bundle with {len(scenarios)} scenario(s)."


# -------------------------------------------------------
# EXTRACTION / DISPLAY HELPERS
# -------------------------------------------------------
def extract_database_fields(payload):
    """
    Extracts fields required by save_scenario().
    Safe defaults are used if values are missing.
    """

    scenario_name = get_nested(
        payload,
        "Scenario Metadata",
        "Scenario Name",
        "Imported Scenario"
    )

    vehicle_segment = get_nested(
        payload,
        "Scenario Metadata",
        "Vehicle Segment",
        "Imported / Custom"
    )

    chemistry = get_nested(
        payload,
        "Battery Pack",
        "Chemistry",
        "Unknown"
    )

    pack_voltage = to_float(
        get_nested(
            payload,
            "Battery Pack",
            "Nominal Pack Voltage (V)",
            0.0
        )
    )

    pack_energy = to_float(
        get_nested(
            payload,
            "Battery Pack",
            "Pack Energy (kWh)",
            0.0
        )
    )

    estimated_range = to_float(
        get_nested(
            payload,
            "Range",
            "Estimated Range (km)",
            0.0
        )
    )

    charging_time = to_float(
        get_nested(
            payload,
            "Charging",
            "Charging Time (min)",
            0.0
        )
    )

    wh_per_km = to_float(
        get_nested(
            payload,
            "Range",
            "Energy Consumption (Wh/km)",
            0.0
        )
    )

    return {
        "scenario_name": scenario_name,
        "vehicle_segment": vehicle_segment,
        "chemistry": chemistry,
        "pack_voltage": pack_voltage,
        "pack_energy": pack_energy,
        "estimated_range": estimated_range,
        "charging_time": charging_time,
        "wh_per_km": wh_per_km
    }


def flatten_payload_for_display(payload):
    """
    Converts nested scenario JSON into a display table.
    """

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


def summarize_bundle_payload(payload):
    """
    Converts uploaded bundle into a summary table before import.
    """

    scenarios = payload.get("Scenarios", [])
    records = []

    for idx, item in enumerate(scenarios):
        scenario_data = item.get("Scenario Data", {})
        fields = extract_database_fields(scenario_data)

        records.append(
            {
                "Bundle Row": idx + 1,
                "Original Scenario ID": item.get("Scenario ID", "-"),
                "Scenario Name": fields["scenario_name"],
                "Vehicle Segment": fields["vehicle_segment"],
                "Chemistry": fields["chemistry"],
                "Pack Voltage (V)": fields["pack_voltage"],
                "Pack Energy (kWh)": fields["pack_energy"],
                "Estimated Range (km)": fields["estimated_range"],
                "Charging Time (min)": fields["charging_time"],
                "Wh/km": fields["wh_per_km"]
            }
        )

    return pd.DataFrame(records)


def add_duplicate_status_to_bundle_summary(bundle_df, payload):
    """
    Adds duplicate/new status to each scenario inside an uploaded bundle.
    """

    scenarios = payload.get("Scenarios", [])
    statuses = []
    existing_ids = []
    hashes = []

    for item in scenarios:
        scenario_data = item.get("Scenario Data", {})
        scenario_hash = create_scenario_hash(scenario_data)
        existing = scenario_hash_exists(scenario_hash)

        hashes.append(scenario_hash)

        if existing is None:
            statuses.append("New")
            existing_ids.append("-")
        else:
            statuses.append("Duplicate")
            existing_ids.append(existing[0])

    bundle_df = bundle_df.copy()
    bundle_df["Duplicate Status"] = statuses
    bundle_df["Existing ID"] = existing_ids
    bundle_df["Scenario Hash"] = hashes

    return bundle_df


# -------------------------------------------------------
# IMPORT / EXPORT LOGIC
# -------------------------------------------------------
def import_single_scenario(payload, skip_duplicates=True):
    """
    Imports one valid scenario into SQLite scenario library.
    If skip_duplicates=True, identical scenario JSON will not be inserted again.
    """

    fields = extract_database_fields(payload)

    result = save_scenario(
        scenario_name=fields["scenario_name"],
        vehicle_segment=fields["vehicle_segment"],
        chemistry=fields["chemistry"],
        pack_voltage=fields["pack_voltage"],
        pack_energy=fields["pack_energy"],
        estimated_range=fields["estimated_range"],
        charging_time=fields["charging_time"],
        wh_per_km=fields["wh_per_km"],
        scenario_data=payload,
        skip_duplicates=skip_duplicates
    )

    fields["import_result"] = result

    return fields


def import_bundle_scenarios(payload, skip_duplicates=True):
    """
    Imports every valid scenario inside a bundle.
    Duplicate scenarios are skipped when skip_duplicates=True.
    """

    scenarios = payload.get("Scenarios", [])
    imported_records = []

    for idx, item in enumerate(scenarios):
        scenario_data = item.get("Scenario Data", {})

        fields = import_single_scenario(
            scenario_data,
            skip_duplicates=skip_duplicates
        )

        result = fields["import_result"]

        if result["saved"]:
            status = "Imported"
            database_id = result.get("inserted_id", "-")
        else:
            status = "Skipped Duplicate"
            database_id = result.get("existing_id", "-")

        imported_records.append(
            {
                "Bundle Row": idx + 1,
                "Scenario Name": fields["scenario_name"],
                "Vehicle Segment": fields["vehicle_segment"],
                "Chemistry": fields["chemistry"],
                "Pack Voltage (V)": fields["pack_voltage"],
                "Pack Energy (kWh)": fields["pack_energy"],
                "Estimated Range (km)": fields["estimated_range"],
                "Charging Time (min)": fields["charging_time"],
                "Wh/km": fields["wh_per_km"],
                "Database ID": database_id,
                "Status": status,
                "Scenario Hash": result.get("scenario_hash", "-")
            }
        )

    return pd.DataFrame(imported_records)


def build_bundle_from_database():
    """
    Exports all saved scenarios into one JSON bundle.
    """

    rows, columns = list_scenarios()

    bundle = {
        "Bundle Metadata": {
            "Tool": "Vidyut Vahanastra",
            "Description": "Exported saved scenario bundle",
            "Scenario Count": len(rows)
        },
        "Scenarios": []
    }

    for row in rows:
        row_dict = dict(zip(columns, row))
        scenario_id = row_dict["ID"]
        scenario_payload = get_scenario_by_id(int(scenario_id))

        if scenario_payload is not None:
            bundle["Scenarios"].append(
                {
                    "Scenario ID": scenario_id,
                    "Scenario Name": row_dict.get("Scenario Name", "Unnamed Scenario"),
                    "Scenario Data": scenario_payload
                }
            )

    return bundle


# -------------------------------------------------------
# STREAMLIT PAGE
# -------------------------------------------------------
def run_scenario_import_export():
    st.markdown("# Scenario Import / Export")
    st.caption("Import saved scenario JSON files and export the complete scenario library.")

    st.info(
        "Use this page to move Vidyut Vahanastra scenarios between systems, restore previous test cases, "
        "or share EV design configurations with another user."
    )

    tab1, tab2, tab3 = st.tabs(
        [
            "Import Scenario JSON / Bundle",
            "Export Scenario Library",
            "Current Library"
        ]
    )

    # ---------------------------------------------------
    # TAB 1: IMPORT SINGLE SCENARIO OR BUNDLE
    # ---------------------------------------------------
    with tab1:
        st.markdown("## Import Scenario JSON or Scenario Bundle")

        uploaded_file = st.file_uploader(
            "Upload a Vidyut Vahanastra scenario JSON file or bundle JSON file",
            type=["json"]
        )

        if uploaded_file is None:
            st.warning("Upload a `.json` scenario file or scenario bundle to continue.")
        else:
            try:
                raw_bytes = uploaded_file.read()
                raw_text = raw_bytes.decode("utf-8")
                uploaded_payload = json.loads(raw_text)

                # -------------------------------
                # CASE 1: BUNDLE IMPORT
                # -------------------------------
                if is_bundle_payload(uploaded_payload):
                    is_valid_bundle, bundle_message = validate_bundle_payload(uploaded_payload)

                    if not is_valid_bundle:
                        st.error(bundle_message)
                        st.markdown("### Uploaded Bundle Preview")
                        st.json(uploaded_payload)

                    else:
                        st.success(bundle_message)

                        st.markdown("## Bundle Preview")

                        bundle_summary_df = summarize_bundle_payload(uploaded_payload)
                        bundle_summary_df = add_duplicate_status_to_bundle_summary(
                            bundle_summary_df,
                            uploaded_payload
                        )

                        st.dataframe(
                            bundle_summary_df,
                            use_container_width=True,
                            hide_index=True
                        )

                        st.markdown("## Bundle Metadata")
                        st.json(uploaded_payload.get("Bundle Metadata", {}))

                        skip_duplicates = st.checkbox(
                            "Skip duplicate scenarios during import",
                            value=True
                        )

                        if st.button("Import Full Bundle into Library"):
                            imported_df = import_bundle_scenarios(
                                uploaded_payload,
                                skip_duplicates=skip_duplicates
                            )

                            imported_count = int(
                                (imported_df["Status"] == "Imported").sum()
                            )

                            skipped_count = int(
                                (imported_df["Status"] == "Skipped Duplicate").sum()
                            )

                            st.success(
                                f"Bundle import complete. Imported {imported_count} scenario(s), "
                                f"skipped {skipped_count} duplicate(s)."
                            )

                            st.dataframe(
                                imported_df,
                                use_container_width=True,
                                hide_index=True
                            )

                # -------------------------------
                # CASE 2: SINGLE SCENARIO IMPORT
                # -------------------------------
                else:
                    is_valid, validation_message = validate_scenario_payload(uploaded_payload)

                    if not is_valid:
                        st.error(validation_message)
                        st.markdown("### Uploaded JSON Preview")
                        st.json(uploaded_payload)

                    else:
                        st.success(validation_message)

                        st.markdown("## Uploaded Scenario Preview")

                        preview_df = flatten_payload_for_display(uploaded_payload)

                        st.dataframe(
                            preview_df,
                            use_container_width=True,
                            hide_index=True
                        )

                        fields = extract_database_fields(uploaded_payload)

                        st.markdown("## Database Import Summary")

                        summary_df = pd.DataFrame(
                            {
                                "Field": list(fields.keys()),
                                "Value": list(fields.values())
                            }
                        )

                        st.dataframe(
                            summary_df,
                            use_container_width=True,
                            hide_index=True
                        )

                        scenario_hash = create_scenario_hash(uploaded_payload)
                        existing = scenario_hash_exists(scenario_hash)

                        st.markdown("## Duplicate Check")

                        if existing is None:
                            st.success("This scenario is new and can be imported.")
                        else:
                            st.warning(
                                f"This scenario already exists as ID {existing[0]}: "
                                f"{existing[1]} created at {existing[2]}"
                            )

                        skip_duplicate_single = st.checkbox(
                            "Skip import if this single scenario is duplicate",
                            value=True
                        )

                        if st.button("Import Scenario into Library"):
                            imported_fields = import_single_scenario(
                                uploaded_payload,
                                skip_duplicates=skip_duplicate_single
                            )

                            result = imported_fields["import_result"]

                            if result["saved"]:
                                st.success(
                                    f"Scenario imported successfully: "
                                    f"{imported_fields['scenario_name']}"
                                )
                            else:
                                st.warning(
                                    f"Duplicate skipped. Existing scenario ID: "
                                    f"{result['existing_id']} ({result['existing_name']})"
                                )

            except json.JSONDecodeError:
                st.error("Invalid JSON file. Please upload a valid `.json` file.")

            except UnicodeDecodeError:
                st.error("Could not decode the uploaded file. Please upload a UTF-8 encoded JSON file.")

            except Exception as e:
                st.error(f"Import failed: {e}")

    # ---------------------------------------------------
    # TAB 2: EXPORT FULL LIBRARY
    # ---------------------------------------------------
    with tab2:
        st.markdown("## Export Complete Scenario Library")

        rows, columns = list_scenarios()

        if not rows:
            st.warning("No scenarios are currently saved.")
        else:
            library_df = pd.DataFrame(rows, columns=columns)

            st.markdown("### Saved Scenario Library")

            st.dataframe(
                library_df,
                use_container_width=True,
                hide_index=True
            )

            bundle = build_bundle_from_database()

            bundle_json = json.dumps(
                bundle,
                indent=4
            ).encode("utf-8")

            st.download_button(
                label="Download Full Scenario Library JSON",
                data=bundle_json,
                file_name="vidyut_vahanastra_scenario_library_bundle.json",
                mime="application/json"
            )

            st.success(
                f"Export bundle ready. Scenario count: {len(bundle['Scenarios'])}"
            )

    # ---------------------------------------------------
    # TAB 3: CURRENT LIBRARY
    # ---------------------------------------------------
    with tab3:
        st.markdown("## Current Saved Scenario Library")

        show_hashes = st.checkbox(
            "Show scenario hashes",
            value=False
        )

        if show_hashes:
            rows, columns = list_scenarios_with_hash()
        else:
            rows, columns = list_scenarios()

        if not rows:
            st.warning("No saved scenarios found.")
        else:
            library_df = pd.DataFrame(rows, columns=columns)

            st.dataframe(
                library_df,
                use_container_width=True,
                hide_index=True
            )

            selected_id = st.number_input(
                "Enter Scenario ID to preview JSON",
                min_value=1,
                value=int(library_df["ID"].iloc[0]),
                step=1
            )

            selected_payload = get_scenario_by_id(int(selected_id))

            if selected_payload is None:
                st.error("Scenario ID not found.")
            else:
                st.markdown("## Selected Scenario JSON")
                st.json(selected_payload)

                selected_hash = create_scenario_hash(selected_payload)

                st.markdown("## Selected Scenario Hash")
                st.code(selected_hash)

                selected_json = json.dumps(
                    selected_payload,
                    indent=4
                ).encode("utf-8")

                st.download_button(
                    label="Download Selected Scenario JSON",
                    data=selected_json,
                    file_name=f"vidyut_vahanastra_scenario_{selected_id}.json",
                    mime="application/json"
                )