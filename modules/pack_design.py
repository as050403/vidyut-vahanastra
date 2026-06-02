import streamlit as st
import pandas as pd
import plotly.graph_objects as go


CHEMISTRY_DATA_PATH = "data/battery_chemistries.csv"


@st.cache_data
def load_battery_chemistry_data():
    return pd.read_csv(CHEMISTRY_DATA_PATH)


def classify_voltage_class(v_pack):
    if v_pack < 60:
        return "Low Voltage / 48 V Class", "Used in mild hybrids, two-wheelers, and low-power EV systems."
    elif 60 <= v_pack < 250:
        return "Intermediate Voltage Class", "Higher than 48 V but below typical passenger EV high-voltage packs."
    elif 250 <= v_pack < 500:
        return "Standard 400 V EV Class", "Common for passenger EVs and mainstream electric cars."
    elif 500 <= v_pack < 900:
        return "High Voltage / 800 V EV Class", "Used for high-power EVs, faster charging, and lower current for the same power."
    else:
        return "Ultra High Voltage Class", "Specialized design; insulation, safety, and component rating must be carefully checked."


def estimate_pack_mass(energy_wh, avg_cell_energy_density, pack_efficiency_factor):
    """
    avg_cell_energy_density: Wh/kg at cell level
    pack_efficiency_factor: pack-level usable density fraction compared with cell-level density.
    Example: 0.65 means pack-level density is 65% of cell-level density.
    """
    if avg_cell_energy_density <= 0 or pack_efficiency_factor <= 0:
        return 0, 0

    cell_mass_kg = energy_wh / avg_cell_energy_density
    pack_mass_kg = cell_mass_kg / pack_efficiency_factor

    return cell_mass_kg, pack_mass_kg


def create_voltage_gauge(v_pack):
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=v_pack,
            title={"text": "Nominal Pack Voltage (V)"},
            gauge={
                "axis": {"range": [0, 1000]},
                "steps": [
                    {"range": [0, 60]},
                    {"range": [60, 250]},
                    {"range": [250, 500]},
                    {"range": [500, 900]},
                    {"range": [900, 1000]},
                ],
                "threshold": {
                    "line": {"width": 4},
                    "thickness": 0.75,
                    "value": v_pack
                }
            }
        )
    )

    fig.update_layout(height=350)
    return fig


def create_energy_gauge(energy_kwh):
    max_range = max(120, energy_kwh * 1.25)

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=energy_kwh,
            number={"suffix": " kWh"},
            title={"text": "Pack Energy"},
            gauge={
                "axis": {"range": [0, max_range]},
                "threshold": {
                    "line": {"width": 4},
                    "thickness": 0.75,
                    "value": energy_kwh
                }
            }
        )
    )

    fig.update_layout(height=350)
    return fig


def create_pack_breakdown_chart(cell_mass_kg, pack_mass_kg):
    overhead_mass = max(pack_mass_kg - cell_mass_kg, 0)

    fig = go.Figure(
        data=[
            go.Bar(
                x=["Cells", "Pack Overhead"],
                y=[cell_mass_kg, overhead_mass],
                text=[round(cell_mass_kg, 1), round(overhead_mass, 1)],
                textposition="auto"
            )
        ]
    )

    fig.update_layout(
        title="Estimated Pack Mass Breakdown",
        xaxis_title="Component",
        yaxis_title="Mass (kg)",
        height=380
    )

    return fig


def create_series_parallel_summary(ns, np_count):
    total_cells = ns * np_count

    data = pd.DataFrame(
        {
            "Parameter": [
                "Series cells",
                "Parallel strings",
                "Total cells",
                "Configuration notation"
            ],
            "Value": [
                ns,
                np_count,
                total_cells,
                f"{ns}S{np_count}P"
            ]
        }
    )

    return data


def run_pack_design_lab():
    st.markdown("# Pack Design Lab")
    st.caption("Design an EV battery pack using cell chemistry, series count, parallel count, and cell capacity.")

    st.info(
        "This is an early-stage sizing tool. Final EV pack design must use manufacturer cell datasheets, "
        "thermal limits, current limits, busbar design, insulation coordination, crash protection, and BMS constraints."
    )

    chemistry_df = load_battery_chemistry_data()

    st.divider()

    st.markdown("## Input Section")

    col1, col2, col3 = st.columns(3)

    with col1:
        selected_chemistry = st.selectbox(
            "Select cell chemistry",
            options=chemistry_df["Chemistry"].tolist(),
            index=0
        )

    selected_row = chemistry_df[chemistry_df["Chemistry"] == selected_chemistry].iloc[0]

    default_v_nom = float(selected_row["Nominal_Voltage_V"])
    default_v_full = float(selected_row["Full_Charge_V"])
    avg_energy_density = (
        float(selected_row["Energy_Density_Min_Whkg"]) +
        float(selected_row["Energy_Density_Max_Whkg"])
    ) / 2

    with col2:
        cell_nominal_voltage = st.number_input(
            "Cell nominal voltage (V)",
            min_value=1.0,
            max_value=5.0,
            value=default_v_nom,
            step=0.1,
            format="%.2f"
        )

    with col3:
        cell_full_voltage = st.number_input(
            "Cell full-charge voltage (V)",
            min_value=1.0,
            max_value=5.0,
            value=default_v_full,
            step=0.1,
            format="%.2f"
        )

    col4, col5, col6 = st.columns(3)

    with col4:
        cell_capacity_ah = st.number_input(
            "Cell capacity (Ah)",
            min_value=1.0,
            max_value=500.0,
            value=100.0,
            step=1.0,
            format="%.1f"
        )

    with col5:
        n_series = st.number_input(
            "Number of cells in series (S)",
            min_value=1,
            max_value=300,
            value=96,
            step=1
        )

    with col6:
        n_parallel = st.number_input(
            "Number of parallel strings (P)",
            min_value=1,
            max_value=100,
            value=1,
            step=1
        )

    col7, col8 = st.columns(2)

    with col7:
        user_energy_density = st.number_input(
            "Average cell energy density (Wh/kg)",
            min_value=30.0,
            max_value=350.0,
            value=float(avg_energy_density),
            step=5.0,
            format="%.1f"
        )

    with col8:
        pack_efficiency_factor = st.slider(
            "Pack-level efficiency factor compared with cell-level density",
            min_value=0.50,
            max_value=0.90,
            value=0.65,
            step=0.01
        )

    st.divider()

    st.markdown("## Calculated Pack Outputs")

    v_pack_nominal = n_series * cell_nominal_voltage
    v_pack_full = n_series * cell_full_voltage
    ah_pack = n_parallel * cell_capacity_ah
    energy_wh = v_pack_nominal * ah_pack
    energy_kwh = energy_wh / 1000
    total_cells = n_series * n_parallel

    cell_mass_kg, pack_mass_kg = estimate_pack_mass(
        energy_wh=energy_wh,
        avg_cell_energy_density=user_energy_density,
        pack_efficiency_factor=pack_efficiency_factor
    )

    voltage_class, voltage_class_description = classify_voltage_class(v_pack_nominal)

    metric1, metric2, metric3, metric4 = st.columns(4)

    with metric1:
        st.metric("Nominal Voltage", f"{v_pack_nominal:.1f} V")
        st.caption("Nseries × cell nominal voltage")

    with metric2:
        st.metric("Full-Charge Voltage", f"{v_pack_full:.1f} V")
        st.caption("Nseries × cell full-charge voltage")

    with metric3:
        st.metric("Pack Capacity", f"{ah_pack:.1f} Ah")
        st.caption("Nparallel × cell Ah")

    with metric4:
        st.metric("Pack Energy", f"{energy_kwh:.2f} kWh")
        st.caption("Vnom × Ah / 1000")

    metric5, metric6, metric7, metric8 = st.columns(4)

    with metric5:
        st.metric("Total Cells", f"{total_cells}")
        st.caption(f"{n_series}S{n_parallel}P")

    with metric6:
        st.metric("Estimated Cell Mass", f"{cell_mass_kg:.1f} kg")
        st.caption("Based on cell-level Wh/kg")

    with metric7:
        st.metric("Estimated Pack Mass", f"{pack_mass_kg:.1f} kg")
        st.caption("Includes pack-level overhead")

    with metric8:
        st.metric("Voltage Class", voltage_class)
        st.caption(voltage_class_description)

    st.divider()

    st.markdown("## Visual Pack Dashboard")

    col_a, col_b = st.columns(2)

    with col_a:
        voltage_fig = create_voltage_gauge(v_pack_nominal)
        st.plotly_chart(voltage_fig, use_container_width=True)

    with col_b:
        energy_fig = create_energy_gauge(energy_kwh)
        st.plotly_chart(energy_fig, use_container_width=True)

    mass_fig = create_pack_breakdown_chart(cell_mass_kg, pack_mass_kg)
    st.plotly_chart(mass_fig, use_container_width=True)

    st.divider()

    st.markdown("## Series-Parallel Configuration Summary")

    config_df = create_series_parallel_summary(n_series, n_parallel)
    st.dataframe(config_df, use_container_width=True, hide_index=True)

    st.divider()

    st.markdown("## Engineering Interpretation")

    if selected_chemistry == "LFP":
        st.success(
            "LFP is a strong choice for Indian EVs because it gives high safety, long cycle life, and better thermal stability, "
            "but the pack may become heavier than NMC/NCA for the same energy target."
        )
    elif selected_chemistry == "NMC":
        st.info(
            "NMC is suitable when range and compactness are important. It offers higher energy density than LFP, "
            "but needs stronger BMS and thermal management."
        )
    elif selected_chemistry == "NCA":
        st.warning(
            "NCA is more suitable for premium long-range EVs. It offers high energy density but has stronger thermal-safety demands."
        )
    elif selected_chemistry == "LTO":
        st.info(
            "LTO is excellent for ultra-fast charging and very high cycle life, but its low energy density makes the pack large and heavy."
        )

    st.markdown("### Design Notes")

    st.write(
        f"""
        The selected pack is **{n_series}S{n_parallel}P**, using **{selected_chemistry}** cells.  
        It produces approximately **{v_pack_nominal:.1f} V nominal**, **{v_pack_full:.1f} V at full charge**, 
        and **{energy_kwh:.2f} kWh** of nominal energy.

        For a company-grade pack design, this calculation should later be extended with:
        - Maximum discharge current
        - C-rate limit
        - Busbar current density
        - Fuse and contactor rating
        - Precharge resistor sizing
        - Cell balancing strategy
        - Thermal model
        - IP rating and crash protection
        """
    )