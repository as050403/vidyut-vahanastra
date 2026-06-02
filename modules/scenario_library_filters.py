import json
import pandas as pd
import streamlit as st

from utils.scenario_store import (
    list_scenarios,
    list_scenarios_with_hash,
    get_scenario_by_id,
    delete_scenario
)


# -------------------------------------------------------
# DATA LOADING
# -------------------------------------------------------
def load_library_dataframe(show_hashes=False):
    if show_hashes:
        rows, columns = list_scenarios_with_hash()
    else:
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

    return df


# -------------------------------------------------------
# FILTER HELPERS
# -------------------------------------------------------
def safe_min_max(df, column, default_min=0.0, default_max=1.0):
    if df.empty or column not in df.columns:
        return default_min, default_max

    col_min = float(df[column].min())
    col_max = float(df[column].max())

    if col_min == col_max:
        col_max = col_min + 1.0

    return col_min, col_max


def apply_filters(
    df,
    keyword,
    selected_segments,
    selected_chemistries,
    pack_energy_range,
    estimated_range_range,
    charging_time_range,
    created_date_range
):
    if df.empty:
        return df

    filtered = df.copy()

    if keyword.strip():
        keyword_lower = keyword.strip().lower()

        mask = (
            filtered["Scenario Name"].astype(str).str.lower().str.contains(keyword_lower, na=False)
            | filtered["Vehicle Segment"].astype(str).str.lower().str.contains(keyword_lower, na=False)
            | filtered["Chemistry"].astype(str).str.lower().str.contains(keyword_lower, na=False)
        )

        filtered = filtered.loc[mask]

    if selected_segments:
        filtered = filtered.loc[
            filtered["Vehicle Segment"].isin(selected_segments)
        ]

    if selected_chemistries:
        filtered = filtered.loc[
            filtered["Chemistry"].isin(selected_chemistries)
        ]

    if "Pack Energy (kWh)" in filtered.columns:
        filtered = filtered.loc[
            (filtered["Pack Energy (kWh)"] >= pack_energy_range[0])
            & (filtered["Pack Energy (kWh)"] <= pack_energy_range[1])
        ]

    if "Estimated Range (km)" in filtered.columns:
        filtered = filtered.loc[
            (filtered["Estimated Range (km)"] >= estimated_range_range[0])
            & (filtered["Estimated Range (km)"] <= estimated_range_range[1])
        ]

    if "Charging Time (min)" in filtered.columns:
        filtered = filtered.loc[
            (filtered["Charging Time (min)"] >= charging_time_range[0])
            & (filtered["Charging Time (min)"] <= charging_time_range[1])
        ]

    if (
        created_date_range
        and len(created_date_range) == 2
        and "Created At Parsed" in filtered.columns
    ):
        start_date = pd.to_datetime(created_date_range[0])
        end_date = pd.to_datetime(created_date_range[1]) + pd.Timedelta(days=1)

        filtered = filtered.loc[
            (filtered["Created At Parsed"] >= start_date)
            & (filtered["Created At Parsed"] < end_date)
        ]

    return filtered


def create_summary_metrics(df):
    if df.empty:
        return {
            "count": 0,
            "avg_energy": 0,
            "avg_range": 0,
            "avg_charge_time": 0,
            "best_range": 0
        }

    return {
        "count": len(df),
        "avg_energy": df["Pack Energy (kWh)"].mean() if "Pack Energy (kWh)" in df.columns else 0,
        "avg_range": df["Estimated Range (km)"].mean() if "Estimated Range (km)" in df.columns else 0,
        "avg_charge_time": df["Charging Time (min)"].mean() if "Charging Time (min)" in df.columns else 0,
        "best_range": df["Estimated Range (km)"].max() if "Estimated Range (km)" in df.columns else 0
    }


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
# PAGE
# -------------------------------------------------------
def run_scenario_library_filters():
    st.markdown("# Scenario Search and Filters")
    st.caption("Search, filter, preview, export, and delete saved EV scenarios.")

    st.info(
        "Use this page when the scenario library becomes large. You can filter by chemistry, vehicle segment, "
        "battery size, estimated range, charging time, and created date."
    )

    show_hashes = st.checkbox(
        "Show scenario hashes",
        value=False
    )

    df = load_library_dataframe(show_hashes=show_hashes)

    if df.empty:
        st.warning("No saved scenarios found. Save or import scenarios first.")
        return

    filter_tab, preview_tab, export_tab = st.tabs(
        [
            "Search & Filter",
            "Preview / Delete",
            "Export Filtered Results"
        ]
    )

    with filter_tab:
        st.markdown("## Filter Controls")

        c1, c2, c3 = st.columns(3)

        with c1:
            keyword = st.text_input(
                "Search keyword",
                value="",
                placeholder="Search name, segment, or chemistry"
            )

        with c2:
            segment_options = sorted(
                df["Vehicle Segment"].dropna().astype(str).unique().tolist()
            )

            selected_segments = st.multiselect(
                "Vehicle segment",
                options=segment_options,
                default=[]
            )

        with c3:
            chemistry_options = sorted(
                df["Chemistry"].dropna().astype(str).unique().tolist()
            )

            selected_chemistries = st.multiselect(
                "Chemistry",
                options=chemistry_options,
                default=[]
            )

        e_min, e_max = safe_min_max(df, "Pack Energy (kWh)", 0.0, 300.0)
        r_min, r_max = safe_min_max(df, "Estimated Range (km)", 0.0, 1200.0)
        t_min, t_max = safe_min_max(df, "Charging Time (min)", 0.0, 3000.0)

        c4, c5, c6 = st.columns(3)

        with c4:
            pack_energy_range = st.slider(
                "Pack energy range (kWh)",
                min_value=float(e_min),
                max_value=float(e_max),
                value=(float(e_min), float(e_max)),
                step=0.5
            )

        with c5:
            estimated_range_range = st.slider(
                "Estimated range window (km)",
                min_value=float(r_min),
                max_value=float(r_max),
                value=(float(r_min), float(r_max)),
                step=5.0
            )

        with c6:
            charging_time_range = st.slider(
                "Charging time window (min)",
                min_value=float(t_min),
                max_value=float(t_max),
                value=(float(t_min), float(t_max)),
                step=1.0
            )

        created_date_range = None

        if "Created At Parsed" in df.columns and df["Created At Parsed"].notna().any():
            min_date = df["Created At Parsed"].min().date()
            max_date = df["Created At Parsed"].max().date()

            created_date_range = st.date_input(
                "Created date range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )

        filtered_df = apply_filters(
            df=df,
            keyword=keyword,
            selected_segments=selected_segments,
            selected_chemistries=selected_chemistries,
            pack_energy_range=pack_energy_range,
            estimated_range_range=estimated_range_range,
            charging_time_range=charging_time_range,
            created_date_range=created_date_range
        )

        st.session_state["filtered_scenario_library_df"] = filtered_df

        st.divider()

        st.markdown("## Filtered Library")

        metrics = create_summary_metrics(filtered_df)

        m1, m2, m3, m4, m5 = st.columns(5)

        with m1:
            st.metric("Matched Scenarios", f"{metrics['count']}")

        with m2:
            st.metric("Average Pack Energy", f"{metrics['avg_energy']:.2f} kWh")

        with m3:
            st.metric("Average Range", f"{metrics['avg_range']:.1f} km")

        with m4:
            st.metric("Average Charge Time", f"{metrics['avg_charge_time']:.1f} min")

        with m5:
            st.metric("Best Range", f"{metrics['best_range']:.1f} km")

        if filtered_df.empty:
            st.warning("No scenarios match the selected filters.")
        else:
            display_df = filtered_df.drop(
                columns=["Created At Parsed"],
                errors="ignore"
            )

            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )

    with preview_tab:
        st.markdown("## Preview or Delete Scenario")

        filtered_df = st.session_state.get("filtered_scenario_library_df", df)

        if filtered_df.empty:
            st.warning("No filtered scenarios available to preview.")
        else:
            available_ids = filtered_df["ID"].astype(int).tolist()

            selected_id = st.selectbox(
                "Select Scenario ID",
                options=available_ids,
                index=0
            )

            payload = get_scenario_by_id(int(selected_id))

            if payload is None:
                st.error("Scenario ID not found.")
            else:
                st.markdown("## Scenario Table Preview")

                preview_df = flatten_payload_for_display(payload)

                st.dataframe(
                    preview_df,
                    use_container_width=True,
                    hide_index=True
                )

                st.markdown("## Raw JSON")
                st.json(payload)

                c1, c2 = st.columns(2)

                with c1:
                    scenario_json = json.dumps(
                        payload,
                        indent=4
                    ).encode("utf-8")

                    st.download_button(
                        label="Download Selected Scenario JSON",
                        data=scenario_json,
                        file_name=f"vidyut_vahanastra_scenario_{selected_id}.json",
                        mime="application/json"
                    )

                with c2:
                    confirm_delete = st.checkbox(
                        f"Confirm delete scenario ID {selected_id}",
                        value=False
                    )

                    if st.button("Delete Selected Scenario"):
                        if confirm_delete:
                            delete_scenario(int(selected_id))
                            st.success(f"Scenario ID {selected_id} deleted. Refresh page to update table.")
                        else:
                            st.warning("Please tick the confirmation checkbox before deleting.")

    with export_tab:
        st.markdown("## Export Filtered Results")

        filtered_df = st.session_state.get("filtered_scenario_library_df", df)

        if filtered_df.empty:
            st.warning("No filtered results available for export.")
        else:
            export_df = filtered_df.drop(
                columns=["Created At Parsed"],
                errors="ignore"
            )

            csv_data = export_df.to_csv(index=False).encode("utf-8")

            st.download_button(
                label="Download Filtered Library CSV",
                data=csv_data,
                file_name="vidyut_vahanastra_filtered_scenarios.csv",
                mime="text/csv"
            )

            bundle = {
                "Bundle Metadata": {
                    "Tool": "Vidyut Vahanastra",
                    "Description": "Filtered scenario export bundle",
                    "Scenario Count": len(export_df)
                },
                "Scenarios": []
            }

            for scenario_id in export_df["ID"].astype(int).tolist():
                payload = get_scenario_by_id(int(scenario_id))

                if payload is not None:
                    row = export_df[export_df["ID"] == scenario_id].iloc[0]

                    bundle["Scenarios"].append(
                        {
                            "Scenario ID": int(scenario_id),
                            "Scenario Name": row.get("Scenario Name", "Unnamed Scenario"),
                            "Scenario Data": payload
                        }
                    )

            bundle_json = json.dumps(
                bundle,
                indent=4
            ).encode("utf-8")

            st.download_button(
                label="Download Filtered Scenario Bundle JSON",
                data=bundle_json,
                file_name="vidyut_vahanastra_filtered_scenario_bundle.json",
                mime="application/json"
            )

            st.success(f"Filtered export ready. Scenario count: {len(export_df)}")