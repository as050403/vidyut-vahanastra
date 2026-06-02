from pathlib import Path
import importlib
import pandas as pd
import streamlit as st


# -------------------------------------------------------
# PROJECT PATHS
# -------------------------------------------------------
REQUIRED_FOLDERS = [
    "data",
    "modules",
    "utils",
    "assets"
]

REQUIRED_FILES = [
    "data/battery_chemistries.csv",
    "data/charger_presets.csv",
    "data/vehicle_presets.csv",
    "data/motor_presets.csv",
    "data/inverter_devices.csv",
    "utils/scenario_store.py",
    "utils/ui_theme.py"
]

REQUIRED_MODULES = [
    "modules.battery_chemistry",
    "modules.pack_design",
    "modules.charging",
    "modules.range_model",
    "modules.scenario_compare",
    "modules.bms_soc",
    "modules.motor_inverter",
    "modules.thermal_model",
    "modules.report_generator",
    "modules.saved_scenarios",
    "modules.auto_report",
    "modules.real_ev_presets",
    "modules.saved_scenario_compare",
    "modules.scenario_import_export",
    "modules.scenario_library_filters",
    "modules.scenario_dashboard_analytics",
    "modules.preset_to_scenario"
]


# -------------------------------------------------------
# GENERAL CHECK HELPERS
# -------------------------------------------------------
def check_required_folders():
    records = []

    for folder in REQUIRED_FOLDERS:
        path = Path(folder)

        records.append(
            {
                "Check Type": "Folder",
                "Item": folder,
                "Status": "OK" if path.exists() and path.is_dir() else "Missing",
                "Details": str(path.resolve())
            }
        )

    return records


def check_required_files():
    records = []

    for file_path in REQUIRED_FILES:
        path = Path(file_path)

        records.append(
            {
                "Check Type": "File",
                "Item": file_path,
                "Status": "OK" if path.exists() and path.is_file() else "Missing",
                "Details": str(path.resolve())
            }
        )

    return records


def check_required_modules():
    records = []

    for module_name in REQUIRED_MODULES:
        try:
            importlib.import_module(module_name)

            records.append(
                {
                    "Check Type": "Module Import",
                    "Item": module_name,
                    "Status": "OK",
                    "Details": "Imported successfully"
                }
            )

        except Exception as e:
            records.append(
                {
                    "Check Type": "Module Import",
                    "Item": module_name,
                    "Status": "Failed",
                    "Details": str(e)
                }
            )

    return records


def check_database():
    try:
        from utils.scenario_store import init_scenario_db, list_scenarios

        init_scenario_db()
        rows, _ = list_scenarios()

        return [
            {
                "Check Type": "Database",
                "Item": "SQLite scenario database",
                "Status": "OK",
                "Details": f"Database initialized. Saved scenarios: {len(rows)}"
            }
        ]

    except Exception as e:
        return [
            {
                "Check Type": "Database",
                "Item": "SQLite scenario database",
                "Status": "Failed",
                "Details": str(e)
            }
        ]


def run_all_health_checks():
    records = []
    records.extend(check_required_folders())
    records.extend(check_required_files())
    records.extend(check_required_modules())
    records.extend(check_database())

    return pd.DataFrame(records)


def health_status_summary(health_df):
    if health_df.empty:
        return {
            "total": 0,
            "ok": 0,
            "missing": 0,
            "failed": 0,
            "healthy": False
        }

    total = len(health_df)
    ok = int((health_df["Status"] == "OK").sum())
    missing = int((health_df["Status"] == "Missing").sum())
    failed = int((health_df["Status"] == "Failed").sum())

    return {
        "total": total,
        "ok": ok,
        "missing": missing,
        "failed": failed,
        "healthy": (missing == 0 and failed == 0)
    }


# -------------------------------------------------------
# SAFE CSV LOADING
# -------------------------------------------------------
def safe_read_csv(file_path, required_columns=None, fallback_df=None):
    """
    Safer CSV reader for dashboard modules.
    Returns: dataframe, status_message, is_ok
    """

    path = Path(file_path)

    if fallback_df is None:
        fallback_df = pd.DataFrame()

    if not path.exists():
        return fallback_df, f"Missing file: {file_path}", False

    try:
        df = pd.read_csv(path)

    except Exception as e:
        return fallback_df, f"Could not read {file_path}: {e}", False

    if required_columns:
        missing_columns = [
            col for col in required_columns
            if col not in df.columns
        ]

        if missing_columns:
            return (
                fallback_df,
                f"{file_path} is missing required columns: {missing_columns}",
                False
            )

    return df, f"Loaded successfully: {file_path}", True


# -------------------------------------------------------
# ROADMAP VALIDATION
# -------------------------------------------------------
def validate_equal_length_dict(data_dict):
    """
    Prevents Pandas 'All arrays must be of the same length' error.
    """

    lengths = {
        key: len(value)
        for key, value in data_dict.items()
    }

    unique_lengths = set(lengths.values())

    if len(unique_lengths) == 1:
        return True, lengths

    return False, lengths


def safe_dataframe_from_equal_lists(data_dict):
    is_valid, lengths = validate_equal_length_dict(data_dict)

    if not is_valid:
        raise ValueError(
            f"Cannot create DataFrame. Column lengths are unequal: {lengths}"
        )

    return pd.DataFrame(data_dict)


# -------------------------------------------------------
# STREAMLIT DISPLAY HELPERS
# -------------------------------------------------------
def show_health_banner():
    health_df = run_all_health_checks()
    summary = health_status_summary(health_df)

    if summary["healthy"]:
        st.sidebar.success("Health Check: OK")
    else:
        st.sidebar.error(
            f"Health Check: {summary['missing']} missing, {summary['failed']} failed"
        )

    return health_df, summary


def run_app_health_page():
    st.markdown("# App Health Check")
    st.caption("Startup checks for files, folders, modules, database, and project readiness.")

    st.info(
        "Use this page when the dashboard crashes, files are missing, CSV columns are wrong, "
        "or new modules are added."
    )

    health_df = run_all_health_checks()
    summary = health_status_summary(health_df)

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("Total Checks", summary["total"])

    with c2:
        st.metric("OK", summary["ok"])

    with c3:
        st.metric("Missing", summary["missing"])

    with c4:
        st.metric("Failed", summary["failed"])

    if summary["healthy"]:
        st.success("All project health checks passed.")
    else:
        st.error("Some checks failed. Review the table below.")

    st.dataframe(
        health_df,
        use_container_width=True,
        hide_index=True
    )

    st.markdown("## Recommended Fixes")

    failed_df = health_df[health_df["Status"] != "OK"]

    if failed_df.empty:
        st.success("No fixes required.")
    else:
        for _, row in failed_df.iterrows():
            st.warning(
                f"**{row['Check Type']} → {row['Item']}**: {row['Details']}"
            )

    csv_data = health_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download Health Check CSV",
        data=csv_data,
        file_name="vidyut_vahanastra_health_check.csv",
        mime="text/csv"
    )