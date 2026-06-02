import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go


CHARGER_DATA_PATH = "data/charger_presets.csv"


@st.cache_data
def load_charger_data():
    return pd.read_csv(CHARGER_DATA_PATH)


def get_temperature_derating_factor(temp_condition):
    derating_map = {
        "Cold battery (<15°C)": 0.60,
        "Cool battery (15–25°C)": 0.85,
        "Optimal battery (25–35°C)": 1.00,
        "Hot battery (35–45°C)": 0.80,
        "Very hot battery (>45°C)": 0.55
    }
    return derating_map.get(temp_condition, 1.0)


def create_charging_curve(
    battery_capacity_kwh,
    initial_soc,
    final_soc,
    charger_power_kw,
    charger_efficiency,
    temp_derating_factor,
    taper_start_soc=80,
    taper_end_fraction=0.15
):
    """
    Simplified CC-CV charging model.

    Assumption:
    - Rated charger power is input-side available power.
    - Battery-side effective power = charger_power × efficiency × temperature_derating.
    - Below taper_start_soc, charging power is nearly constant.
    - Above taper_start_soc, power linearly tapers toward taper_end_fraction at 100% SOC.
    """

    soc_points = np.linspace(initial_soc, final_soc, 250)
    time_points_min = [0]
    power_points_kw = []
    energy_added_points_kwh = [0]

    effective_max_power = charger_power_kw * charger_efficiency * temp_derating_factor

    for i in range(len(soc_points)):
        soc = soc_points[i]

        if soc <= taper_start_soc:
            power = effective_max_power
        else:
            taper_ratio = (soc - taper_start_soc) / (100 - taper_start_soc)
            taper_ratio = min(max(taper_ratio, 0), 1)
            power = effective_max_power * (1 - taper_ratio * (1 - taper_end_fraction))

        power = max(power, effective_max_power * taper_end_fraction)
        power_points_kw.append(power)

        if i > 0:
            delta_soc = soc_points[i] - soc_points[i - 1]
            delta_energy_kwh = battery_capacity_kwh * delta_soc / 100
            delta_time_hr = delta_energy_kwh / power if power > 0 else 0
            time_points_min.append(time_points_min[-1] + delta_time_hr * 60)
            energy_added_points_kwh.append(energy_added_points_kwh[-1] + delta_energy_kwh)

    df_curve = pd.DataFrame(
        {
            "SOC (%)": soc_points,
            "Time (min)": time_points_min,
            "Charging Power (kW)": power_points_kw,
            "Energy Added (kWh)": energy_added_points_kwh
        }
    )

    return df_curve


def calculate_simple_charging_summary(
    battery_capacity_kwh,
    initial_soc,
    final_soc,
    charger_power_kw,
    charger_efficiency,
    temp_derating_factor,
    tariff_per_kwh
):
    delta_soc = final_soc - initial_soc
    battery_energy_added_kwh = battery_capacity_kwh * delta_soc / 100

    energy_from_grid_kwh = battery_energy_added_kwh / charger_efficiency
    cost = energy_from_grid_kwh * tariff_per_kwh

    effective_battery_power_kw = charger_power_kw * charger_efficiency * temp_derating_factor
    ideal_time_hr = battery_energy_added_kwh / effective_battery_power_kw if effective_battery_power_kw > 0 else 0

    return {
        "delta_soc": delta_soc,
        "battery_energy_added_kwh": battery_energy_added_kwh,
        "energy_from_grid_kwh": energy_from_grid_kwh,
        "estimated_cost": cost,
        "effective_battery_power_kw": effective_battery_power_kw,
        "ideal_time_min": ideal_time_hr * 60
    }


def create_charging_power_plot(df_curve):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df_curve["Time (min)"],
            y=df_curve["Charging Power (kW)"],
            mode="lines",
            name="Charging Power"
        )
    )

    fig.update_layout(
        title="Charging Power vs Time",
        xaxis_title="Time (minutes)",
        yaxis_title="Battery-Side Charging Power (kW)",
        height=430
    )

    return fig


def create_soc_time_plot(df_curve):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df_curve["Time (min)"],
            y=df_curve["SOC (%)"],
            mode="lines",
            name="SOC"
        )
    )

    fig.update_layout(
        title="SOC Rise During Charging",
        xaxis_title="Time (minutes)",
        yaxis_title="SOC (%)",
        height=430
    )

    return fig


def create_energy_added_plot(df_curve):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df_curve["Time (min)"],
            y=df_curve["Energy Added (kWh)"],
            mode="lines",
            name="Energy Added"
        )
    )

    fig.update_layout(
        title="Battery Energy Added vs Time",
        xaxis_title="Time (minutes)",
        yaxis_title="Energy Added (kWh)",
        height=430
    )

    return fig


def interpret_charger(charger_power_kw):
    if charger_power_kw <= 3.3:
        return "Slow AC charging: best for overnight home charging, not for quick turnaround."
    elif charger_power_kw <= 7.4:
        return "Standard AC charging: suitable for home, apartment, workplace, and daily charging."
    elif charger_power_kw <= 22:
        return "High-power AC charging: useful only if the vehicle OBC supports it."
    elif charger_power_kw <= 50:
        return "Moderate DC fast charging: useful for city/public fast charging and smaller battery packs."
    elif charger_power_kw <= 150:
        return "DC fast charging: suitable for highway charging and 10–80% quick charging."
    else:
        return "Ultra-fast DC charging: mainly useful for high-voltage EVs that can actually accept this power."


def run_charging_lab():
    st.markdown("# Charging Lab")
    st.caption("Simulate EV charging time, CC-CV tapering, charging cost, and temperature derating.")

    st.info(
        "This module uses a simplified CC-CV charging model. Real EV charging depends on BMS limits, charger communication, "
        "battery temperature, pack voltage, SOC window, SOH, and vehicle-specific charging curves."
    )

    charger_df = load_charger_data()

    st.divider()

    st.markdown("## Input Section")

    col1, col2, col3 = st.columns(3)

    with col1:
        battery_capacity_kwh = st.number_input(
            "Battery capacity (kWh)",
            min_value=1.0,
            max_value=250.0,
            value=40.5,
            step=0.5,
            format="%.1f"
        )

    with col2:
        soc_range = st.slider(
            "Charging SOC window (%)",
            min_value=0,
            max_value=100,
            value=(10, 80),
            step=1
        )
        initial_soc, final_soc = soc_range

    with col3:
        charger_option = st.selectbox(
            "Select charger preset",
            options=[
                f"{row['Charger_Type']} - {row['Power_kW']} kW"
                for _, row in charger_df.iterrows()
            ],
            index=7
        )

    selected_index = [
        f"{row['Charger_Type']} - {row['Power_kW']} kW"
        for _, row in charger_df.iterrows()
    ].index(charger_option)

    selected_charger = charger_df.iloc[selected_index]
    default_power_kw = float(selected_charger["Power_kW"])

    col4, col5, col6 = st.columns(3)

    with col4:
        charger_power_kw = st.number_input(
            "Charger power (kW)",
            min_value=0.5,
            max_value=500.0,
            value=default_power_kw,
            step=0.5,
            format="%.1f"
        )

    with col5:
        charger_efficiency = st.slider(
            "Charger efficiency",
            min_value=0.80,
            max_value=0.99,
            value=0.92,
            step=0.01
        )

    with col6:
        tariff_per_kwh = st.number_input(
            "Electricity tariff (₹/kWh)",
            min_value=1.0,
            max_value=50.0,
            value=15.0,
            step=0.5,
            format="%.1f"
        )

    col7, col8 = st.columns(2)

    with col7:
        temp_condition = st.selectbox(
            "Battery temperature condition",
            [
                "Cold battery (<15°C)",
                "Cool battery (15–25°C)",
                "Optimal battery (25–35°C)",
                "Hot battery (35–45°C)",
                "Very hot battery (>45°C)"
            ],
            index=2
        )

    with col8:
        taper_start_soc = st.slider(
            "Taper start SOC (%)",
            min_value=50,
            max_value=95,
            value=80,
            step=1
        )

    temp_derating_factor = get_temperature_derating_factor(temp_condition)

    if final_soc <= initial_soc:
        st.error("Final SOC must be greater than initial SOC.")
        return

    st.divider()

    st.markdown("## Charging Outputs")

    summary = calculate_simple_charging_summary(
        battery_capacity_kwh=battery_capacity_kwh,
        initial_soc=initial_soc,
        final_soc=final_soc,
        charger_power_kw=charger_power_kw,
        charger_efficiency=charger_efficiency,
        temp_derating_factor=temp_derating_factor,
        tariff_per_kwh=tariff_per_kwh
    )

    df_curve = create_charging_curve(
        battery_capacity_kwh=battery_capacity_kwh,
        initial_soc=initial_soc,
        final_soc=final_soc,
        charger_power_kw=charger_power_kw,
        charger_efficiency=charger_efficiency,
        temp_derating_factor=temp_derating_factor,
        taper_start_soc=taper_start_soc
    )

    total_time_min = float(df_curve["Time (min)"].iloc[-1])
    battery_energy_added_kwh = summary["battery_energy_added_kwh"]
    energy_from_grid_kwh = summary["energy_from_grid_kwh"]
    estimated_cost = summary["estimated_cost"]
    effective_power_kw = summary["effective_battery_power_kw"]

    m1, m2, m3, m4 = st.columns(4)

    with m1:
        st.metric("SOC Added", f"{summary['delta_soc']:.0f}%")
        st.caption(f"{initial_soc}% → {final_soc}%")

    with m2:
        st.metric("Battery Energy Added", f"{battery_energy_added_kwh:.2f} kWh")
        st.caption("Energy stored in battery")

    with m3:
        st.metric("Estimated Time", f"{total_time_min:.1f} min")
        st.caption("Includes taper model")

    with m4:
        st.metric("Estimated Cost", f"₹{estimated_cost:.0f}")
        st.caption("Based on input tariff")

    m5, m6, m7, m8 = st.columns(4)

    with m5:
        st.metric("Effective Battery Power", f"{effective_power_kw:.1f} kW")
        st.caption("Power after efficiency and temperature derating")

    with m6:
        st.metric("Energy From Grid", f"{energy_from_grid_kwh:.2f} kWh")
        st.caption("Includes charger losses")

    with m7:
        st.metric("Temperature Derating", f"{temp_derating_factor * 100:.0f}%")
        st.caption(temp_condition)

    with m8:
        st.metric("Connector Example", str(selected_charger["Connector_Example"]))
        st.caption(str(selected_charger["Typical_Use"]))

    st.divider()

    st.markdown("## Charging Curve Visualization")

    col_a, col_b = st.columns(2)

    with col_a:
        power_fig = create_charging_power_plot(df_curve)
        st.plotly_chart(power_fig, use_container_width=True)

    with col_b:
        soc_fig = create_soc_time_plot(df_curve)
        st.plotly_chart(soc_fig, use_container_width=True)

    energy_fig = create_energy_added_plot(df_curve)
    st.plotly_chart(energy_fig, use_container_width=True)

    st.divider()

    st.markdown("## Charging Data Table")

    st.dataframe(
        df_curve.round(
            {
                "SOC (%)": 2,
                "Time (min)": 2,
                "Charging Power (kW)": 2,
                "Energy Added (kWh)": 3
            }
        ),
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    st.markdown("## Engineering Interpretation")

    st.success(interpret_charger(charger_power_kw))

    if final_soc > 80:
        st.warning(
            "The selected final SOC is above 80%. Charging time increases because the model enters the constant-voltage taper region."
        )
    else:
        st.info(
            "The selected SOC window mostly stays in the faster constant-current region."
        )

    if temp_derating_factor < 1:
        st.warning(
            f"The selected temperature condition reduces effective charging power to {temp_derating_factor * 100:.0f}% of normal."
        )
    else:
        st.success(
            "Battery temperature is in the optimal region, so no temperature derating is applied."
        )

    st.markdown("### Design Notes")

    st.write(
        f"""
        The selected configuration charges a **{battery_capacity_kwh:.1f} kWh** battery from **{initial_soc}% to {final_soc}%** 
        using a **{charger_power_kw:.1f} kW** charger.

        The battery receives approximately **{battery_energy_added_kwh:.2f} kWh**, while the grid supplies approximately 
        **{energy_from_grid_kwh:.2f} kWh** after accounting for charger efficiency.

        The estimated charging time is **{total_time_min:.1f} minutes**. In real EVs, this value may increase if the battery is hot, cold, aged, 
        or if the charger cannot sustain rated power.
        """
    )