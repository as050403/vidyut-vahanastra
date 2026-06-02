import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go


def battery_heat_kw(current_a, pack_resistance_mohm):
    """
    Battery ohmic heat:
    Q = I^2 R
    """
    resistance_ohm = pack_resistance_mohm / 1000.0
    heat_w = (current_a ** 2) * resistance_ohm
    return heat_w / 1000.0


def component_loss_kw(output_power_kw, efficiency_percent):
    """
    Loss = input power - output power
    input = output / efficiency
    """
    efficiency = efficiency_percent / 100.0

    if efficiency <= 0:
        return 0.0

    input_power_kw = output_power_kw / efficiency
    loss_kw = input_power_kw - output_power_kw

    return max(loss_kw, 0.0)


def cooling_power_kw(component_temp_c, coolant_temp_c, thermal_conductance_w_per_k, cooling_limit_kw):
    """
    Cooling power:
    Qcool = hA * (T_component - T_coolant)
    limited by maximum cooling capacity.
    """
    delta_t = max(component_temp_c - coolant_temp_c, 0)
    q_w = thermal_conductance_w_per_k * delta_t
    q_kw = q_w / 1000.0

    return min(q_kw, cooling_limit_kw)


def simulate_component_temperature(
    duration_min,
    time_step_s,
    initial_temp_c,
    coolant_temp_c,
    heat_gen_kw,
    thermal_mass_kj_per_k,
    thermal_conductance_w_per_k,
    cooling_limit_kw
):
    time_s = np.arange(0, duration_min * 60 + time_step_s, time_step_s)
    temp_c = np.zeros_like(time_s, dtype=float)
    cooling_kw = np.zeros_like(time_s, dtype=float)
    net_heat_kw = np.zeros_like(time_s, dtype=float)

    temp_c[0] = initial_temp_c

    for k in range(1, len(time_s)):
        dt = time_s[k] - time_s[k - 1]

        cooling_kw[k - 1] = cooling_power_kw(
            component_temp_c=temp_c[k - 1],
            coolant_temp_c=coolant_temp_c,
            thermal_conductance_w_per_k=thermal_conductance_w_per_k,
            cooling_limit_kw=cooling_limit_kw
        )

        net_heat_kw[k - 1] = heat_gen_kw - cooling_kw[k - 1]

        dtemp = (net_heat_kw[k - 1] * dt) / max(thermal_mass_kj_per_k, 1e-6)
        temp_c[k] = temp_c[k - 1] + dtemp

    cooling_kw[-1] = cooling_power_kw(
        component_temp_c=temp_c[-1],
        coolant_temp_c=coolant_temp_c,
        thermal_conductance_w_per_k=thermal_conductance_w_per_k,
        cooling_limit_kw=cooling_limit_kw
    )

    net_heat_kw[-1] = heat_gen_kw - cooling_kw[-1]

    return pd.DataFrame(
        {
            "Time (s)": time_s,
            "Time (min)": time_s / 60.0,
            "Temperature (°C)": temp_c,
            "Heat Generated (kW)": heat_gen_kw,
            "Cooling Power (kW)": cooling_kw,
            "Net Heat (kW)": net_heat_kw
        }
    )


def merge_thermal_results(battery_df, motor_df, inverter_df):
    df = pd.DataFrame(
        {
            "Time (min)": battery_df["Time (min)"],
            "Battery Temperature (°C)": battery_df["Temperature (°C)"],
            "Motor Temperature (°C)": motor_df["Temperature (°C)"],
            "Inverter Temperature (°C)": inverter_df["Temperature (°C)"],
            "Battery Cooling (kW)": battery_df["Cooling Power (kW)"],
            "Motor Cooling (kW)": motor_df["Cooling Power (kW)"],
            "Inverter Cooling (kW)": inverter_df["Cooling Power (kW)"],
            "Battery Net Heat (kW)": battery_df["Net Heat (kW)"],
            "Motor Net Heat (kW)": motor_df["Net Heat (kW)"],
            "Inverter Net Heat (kW)": inverter_df["Net Heat (kW)"]
        }
    )

    return df


def create_temperature_plot(df):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["Time (min)"],
            y=df["Battery Temperature (°C)"],
            mode="lines",
            name="Battery"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["Time (min)"],
            y=df["Motor Temperature (°C)"],
            mode="lines",
            name="Motor"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["Time (min)"],
            y=df["Inverter Temperature (°C)"],
            mode="lines",
            name="Inverter"
        )
    )

    fig.update_layout(
        title="Component Temperature Rise",
        xaxis_title="Time (min)",
        yaxis_title="Temperature (°C)",
        height=460
    )

    return fig


def create_cooling_plot(df):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["Time (min)"],
            y=df["Battery Cooling (kW)"],
            mode="lines",
            name="Battery Cooling"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["Time (min)"],
            y=df["Motor Cooling (kW)"],
            mode="lines",
            name="Motor Cooling"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["Time (min)"],
            y=df["Inverter Cooling (kW)"],
            mode="lines",
            name="Inverter Cooling"
        )
    )

    fig.update_layout(
        title="Cooling Power vs Time",
        xaxis_title="Time (min)",
        yaxis_title="Cooling Power (kW)",
        height=430
    )

    return fig


def create_net_heat_plot(df):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["Time (min)"],
            y=df["Battery Net Heat (kW)"],
            mode="lines",
            name="Battery Net Heat"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["Time (min)"],
            y=df["Motor Net Heat (kW)"],
            mode="lines",
            name="Motor Net Heat"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["Time (min)"],
            y=df["Inverter Net Heat (kW)"],
            mode="lines",
            name="Inverter Net Heat"
        )
    )

    fig.update_layout(
        title="Net Heat After Cooling",
        xaxis_title="Time (min)",
        yaxis_title="Net Heat (kW)",
        height=430
    )

    return fig


def create_heat_generation_bar(battery_heat, motor_heat, inverter_heat):
    labels = ["Battery", "Motor", "Inverter"]
    values = [battery_heat, motor_heat, inverter_heat]

    fig = go.Figure(
        data=[
            go.Bar(
                x=labels,
                y=values,
                text=[round(v, 3) for v in values],
                textposition="auto"
            )
        ]
    )

    fig.update_layout(
        title="Heat Generation by Component",
        xaxis_title="Component",
        yaxis_title="Heat Generated (kW)",
        height=430
    )

    return fig


def create_temperature_gauge(value, title, limit_value):
    axis_max = max(limit_value * 1.25, value * 1.25, 80)

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={"suffix": " °C"},
            title={"text": title},
            gauge={
                "axis": {"range": [0, axis_max]},
                "threshold": {
                    "line": {"width": 4},
                    "thickness": 0.75,
                    "value": limit_value
                }
            }
        )
    )

    fig.update_layout(height=330)
    return fig


def thermal_status(component_name, max_temp, normal_limit, derate_limit, critical_limit):
    if max_temp < normal_limit:
        return "Safe", f"{component_name} stayed inside the normal thermal region."
    elif max_temp < derate_limit:
        return "Caution", f"{component_name} exceeded the normal region. Thermal margin is reducing."
    elif max_temp < critical_limit:
        return "Derating Required", f"{component_name} entered the derating region. Power reduction is recommended."
    else:
        return "Critical", f"{component_name} crossed the critical thermal threshold. Shutdown/protection action is required."


def calculate_hvac_comparison(
    cabin_thermal_load_kw,
    ptc_cop,
    heat_pump_cop,
    speed_kmh,
    base_consumption_wh_per_km,
    usable_battery_kwh
):
    ptc_electric_kw = cabin_thermal_load_kw / max(ptc_cop, 0.01)
    heat_pump_electric_kw = cabin_thermal_load_kw / max(heat_pump_cop, 0.01)

    ptc_hvac_wh_per_km = ptc_electric_kw * 1000 / max(speed_kmh, 1)
    heat_pump_hvac_wh_per_km = heat_pump_electric_kw * 1000 / max(speed_kmh, 1)

    ptc_total_wh_per_km = base_consumption_wh_per_km + ptc_hvac_wh_per_km
    heat_pump_total_wh_per_km = base_consumption_wh_per_km + heat_pump_hvac_wh_per_km

    ptc_range_km = usable_battery_kwh * 1000 / max(ptc_total_wh_per_km, 1)
    heat_pump_range_km = usable_battery_kwh * 1000 / max(heat_pump_total_wh_per_km, 1)

    return {
        "PTC Electric Power (kW)": ptc_electric_kw,
        "Heat Pump Electric Power (kW)": heat_pump_electric_kw,
        "PTC HVAC Wh/km": ptc_hvac_wh_per_km,
        "Heat Pump HVAC Wh/km": heat_pump_hvac_wh_per_km,
        "PTC Total Wh/km": ptc_total_wh_per_km,
        "Heat Pump Total Wh/km": heat_pump_total_wh_per_km,
        "PTC Range (km)": ptc_range_km,
        "Heat Pump Range (km)": heat_pump_range_km,
        "Range Benefit (km)": heat_pump_range_km - ptc_range_km
    }


def create_hvac_bar_chart(hvac_result):
    labels = ["PTC Heater", "Heat Pump"]
    values = [
        hvac_result["PTC Electric Power (kW)"],
        hvac_result["Heat Pump Electric Power (kW)"]
    ]

    fig = go.Figure(
        data=[
            go.Bar(
                x=labels,
                y=values,
                text=[round(v, 2) for v in values],
                textposition="auto"
            )
        ]
    )

    fig.update_layout(
        title="HVAC Electrical Power Comparison",
        xaxis_title="Heating/Cooling Method",
        yaxis_title="Electrical Power (kW)",
        height=420
    )

    return fig


def create_hvac_range_chart(hvac_result):
    labels = ["PTC Heater", "Heat Pump"]
    values = [
        hvac_result["PTC Range (km)"],
        hvac_result["Heat Pump Range (km)"]
    ]

    fig = go.Figure(
        data=[
            go.Bar(
                x=labels,
                y=values,
                text=[round(v, 1) for v in values],
                textposition="auto"
            )
        ]
    )

    fig.update_layout(
        title="Estimated Range with HVAC Load",
        xaxis_title="Heating/Cooling Method",
        yaxis_title="Range (km)",
        height=420
    )

    return fig


def create_cooling_requirement_table(
    battery_heat,
    motor_heat,
    inverter_heat,
    battery_max_temp,
    motor_max_temp,
    inverter_max_temp,
    battery_limit,
    motor_limit,
    inverter_limit
):
    records = []

    components = [
        ("Battery", battery_heat, battery_max_temp, battery_limit),
        ("Motor", motor_heat, motor_max_temp, motor_limit),
        ("Inverter", inverter_heat, inverter_max_temp, inverter_limit)
    ]

    for name, heat_kw, max_temp, limit in components:
        margin = limit - max_temp

        if margin > 10:
            recommendation = "Cooling margin acceptable"
        elif margin > 0:
            recommendation = "Close to limit; increase cooling or reduce load"
        else:
            recommendation = "Limit exceeded; derating/shutdown required"

        records.append(
            {
                "Component": name,
                "Heat Generated (kW)": heat_kw,
                "Max Temperature (°C)": max_temp,
                "Limit (°C)": limit,
                "Thermal Margin (°C)": margin,
                "Recommendation": recommendation
            }
        )

    return pd.DataFrame(records)


def run_thermal_lab():
    st.markdown("# Thermal Lab")
    st.caption("Estimate battery, motor, and inverter heat generation, cooling demand, temperature rise, and derating risk.")

    st.info(
        "This module uses a lumped thermal model. Industry-grade validation requires CFD, coolant-loop design, cell/module test data, "
        "inverter thermal impedance, motor winding thermal models, and measured drive-cycle heat generation."
    )

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "Inputs",
            "Temperature Response",
            "Cooling & Derating",
            "HVAC Impact",
            "Design Summary"
        ]
    )

    with tab1:
        st.markdown("## Battery Thermal Inputs")

        b1, b2, b3 = st.columns(3)

        with b1:
            pack_current_a = st.number_input(
                "Battery pack current (A)",
                min_value=0.0,
                max_value=2000.0,
                value=150.0,
                step=10.0,
                format="%.1f"
            )

        with b2:
            pack_resistance_mohm = st.number_input(
                "Pack internal resistance (mΩ)",
                min_value=1.0,
                max_value=1000.0,
                value=100.0,
                step=5.0,
                format="%.1f"
            )

        with b3:
            battery_thermal_mass_kj_per_k = st.number_input(
                "Battery thermal mass (kJ/K)",
                min_value=10.0,
                max_value=10000.0,
                value=800.0,
                step=10.0,
                format="%.1f"
            )

        b4, b5, b6 = st.columns(3)

        with b4:
            battery_initial_temp_c = st.number_input(
                "Battery initial temperature (°C)",
                min_value=-10.0,
                max_value=90.0,
                value=35.0,
                step=1.0,
                format="%.1f"
            )

        with b5:
            battery_cooling_conductance_w_per_k = st.number_input(
                "Battery thermal conductance hA (W/K)",
                min_value=0.0,
                max_value=5000.0,
                value=300.0,
                step=10.0,
                format="%.1f"
            )

        with b6:
            battery_cooling_limit_kw = st.number_input(
                "Battery cooling limit (kW)",
                min_value=0.0,
                max_value=100.0,
                value=5.0,
                step=0.5,
                format="%.1f"
            )

        st.divider()

        st.markdown("## Motor Thermal Inputs")

        m1, m2, m3 = st.columns(3)

        with m1:
            motor_output_power_kw = st.number_input(
                "Motor mechanical output power (kW)",
                min_value=0.0,
                max_value=500.0,
                value=75.0,
                step=5.0,
                format="%.1f"
            )

        with m2:
            motor_efficiency_percent = st.number_input(
                "Motor efficiency (%)",
                min_value=50.0,
                max_value=99.5,
                value=94.0,
                step=0.5,
                format="%.1f"
            )

        with m3:
            motor_thermal_mass_kj_per_k = st.number_input(
                "Motor thermal mass (kJ/K)",
                min_value=1.0,
                max_value=5000.0,
                value=250.0,
                step=10.0,
                format="%.1f"
            )

        m4, m5, m6 = st.columns(3)

        with m4:
            motor_initial_temp_c = st.number_input(
                "Motor initial temperature (°C)",
                min_value=-10.0,
                max_value=160.0,
                value=45.0,
                step=1.0,
                format="%.1f"
            )

        with m5:
            motor_cooling_conductance_w_per_k = st.number_input(
                "Motor thermal conductance hA (W/K)",
                min_value=0.0,
                max_value=5000.0,
                value=450.0,
                step=10.0,
                format="%.1f"
            )

        with m6:
            motor_cooling_limit_kw = st.number_input(
                "Motor cooling limit (kW)",
                min_value=0.0,
                max_value=100.0,
                value=10.0,
                step=0.5,
                format="%.1f"
            )

        st.divider()

        st.markdown("## Inverter Thermal Inputs")

        i1, i2, i3 = st.columns(3)

        with i1:
            inverter_output_power_kw = st.number_input(
                "Inverter output power (kW)",
                min_value=0.0,
                max_value=500.0,
                value=80.0,
                step=5.0,
                format="%.1f"
            )

        with i2:
            inverter_efficiency_percent = st.number_input(
                "Inverter efficiency (%)",
                min_value=70.0,
                max_value=99.9,
                value=97.0,
                step=0.1,
                format="%.1f"
            )

        with i3:
            inverter_thermal_mass_kj_per_k = st.number_input(
                "Inverter thermal mass (kJ/K)",
                min_value=1.0,
                max_value=2000.0,
                value=80.0,
                step=5.0,
                format="%.1f"
            )

        i4, i5, i6 = st.columns(3)

        with i4:
            inverter_initial_temp_c = st.number_input(
                "Inverter initial temperature (°C)",
                min_value=-10.0,
                max_value=160.0,
                value=45.0,
                step=1.0,
                format="%.1f"
            )

        with i5:
            inverter_cooling_conductance_w_per_k = st.number_input(
                "Inverter thermal conductance hA (W/K)",
                min_value=0.0,
                max_value=5000.0,
                value=250.0,
                step=10.0,
                format="%.1f"
            )

        with i6:
            inverter_cooling_limit_kw = st.number_input(
                "Inverter cooling limit (kW)",
                min_value=0.0,
                max_value=100.0,
                value=6.0,
                step=0.5,
                format="%.1f"
            )

        st.divider()

        st.markdown("## Simulation and Limit Inputs")

        s1, s2, s3 = st.columns(3)

        with s1:
            duration_min = st.number_input(
                "Simulation duration (min)",
                min_value=1.0,
                max_value=240.0,
                value=30.0,
                step=5.0,
                format="%.1f"
            )

        with s2:
            time_step_s = st.number_input(
                "Time step (s)",
                min_value=0.5,
                max_value=60.0,
                value=2.0,
                step=0.5,
                format="%.1f"
            )

        with s3:
            coolant_temp_c = st.number_input(
                "Coolant / ambient reference temperature (°C)",
                min_value=-10.0,
                max_value=80.0,
                value=30.0,
                step=1.0,
                format="%.1f"
            )

        l1, l2, l3 = st.columns(3)

        with l1:
            battery_derate_limit_c = st.number_input(
                "Battery derating limit (°C)",
                min_value=30.0,
                max_value=90.0,
                value=45.0,
                step=1.0,
                format="%.1f"
            )

        with l2:
            motor_derate_limit_c = st.number_input(
                "Motor derating limit (°C)",
                min_value=80.0,
                max_value=220.0,
                value=150.0,
                step=5.0,
                format="%.1f"
            )

        with l3:
            inverter_derate_limit_c = st.number_input(
                "Inverter derating limit (°C)",
                min_value=80.0,
                max_value=220.0,
                value=150.0,
                step=5.0,
                format="%.1f"
            )

    battery_heat = battery_heat_kw(
        current_a=pack_current_a,
        pack_resistance_mohm=pack_resistance_mohm
    )

    motor_heat = component_loss_kw(
        output_power_kw=motor_output_power_kw,
        efficiency_percent=motor_efficiency_percent
    )

    inverter_heat = component_loss_kw(
        output_power_kw=inverter_output_power_kw,
        efficiency_percent=inverter_efficiency_percent
    )

    battery_df = simulate_component_temperature(
        duration_min=duration_min,
        time_step_s=time_step_s,
        initial_temp_c=battery_initial_temp_c,
        coolant_temp_c=coolant_temp_c,
        heat_gen_kw=battery_heat,
        thermal_mass_kj_per_k=battery_thermal_mass_kj_per_k,
        thermal_conductance_w_per_k=battery_cooling_conductance_w_per_k,
        cooling_limit_kw=battery_cooling_limit_kw
    )

    motor_df = simulate_component_temperature(
        duration_min=duration_min,
        time_step_s=time_step_s,
        initial_temp_c=motor_initial_temp_c,
        coolant_temp_c=coolant_temp_c,
        heat_gen_kw=motor_heat,
        thermal_mass_kj_per_k=motor_thermal_mass_kj_per_k,
        thermal_conductance_w_per_k=motor_cooling_conductance_w_per_k,
        cooling_limit_kw=motor_cooling_limit_kw
    )

    inverter_df = simulate_component_temperature(
        duration_min=duration_min,
        time_step_s=time_step_s,
        initial_temp_c=inverter_initial_temp_c,
        coolant_temp_c=coolant_temp_c,
        heat_gen_kw=inverter_heat,
        thermal_mass_kj_per_k=inverter_thermal_mass_kj_per_k,
        thermal_conductance_w_per_k=inverter_cooling_conductance_w_per_k,
        cooling_limit_kw=inverter_cooling_limit_kw
    )

    thermal_df = merge_thermal_results(
        battery_df=battery_df,
        motor_df=motor_df,
        inverter_df=inverter_df
    )

    battery_max_temp = thermal_df["Battery Temperature (°C)"].max()
    motor_max_temp = thermal_df["Motor Temperature (°C)"].max()
    inverter_max_temp = thermal_df["Inverter Temperature (°C)"].max()

    with tab2:
        st.markdown("## Temperature Response")

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric("Battery Heat", f"{battery_heat:.3f} kW")

        with c2:
            st.metric("Motor Heat", f"{motor_heat:.3f} kW")

        with c3:
            st.metric("Inverter Heat", f"{inverter_heat:.3f} kW")

        with c4:
            st.metric("Total Heat", f"{battery_heat + motor_heat + inverter_heat:.3f} kW")

        st.plotly_chart(create_temperature_plot(thermal_df), use_container_width=True)

        g1, g2, g3 = st.columns(3)

        with g1:
            st.plotly_chart(
                create_temperature_gauge(
                    value=battery_max_temp,
                    title="Battery Max Temp",
                    limit_value=battery_derate_limit_c
                ),
                use_container_width=True
            )

        with g2:
            st.plotly_chart(
                create_temperature_gauge(
                    value=motor_max_temp,
                    title="Motor Max Temp",
                    limit_value=motor_derate_limit_c
                ),
                use_container_width=True
            )

        with g3:
            st.plotly_chart(
                create_temperature_gauge(
                    value=inverter_max_temp,
                    title="Inverter Max Temp",
                    limit_value=inverter_derate_limit_c
                ),
                use_container_width=True
            )

        st.markdown("## Thermal Data Table")

        st.dataframe(
            thermal_df.round(3),
            use_container_width=True,
            hide_index=True
        )

    with tab3:
        st.markdown("## Cooling and Derating Analysis")

        col_a, col_b = st.columns(2)

        with col_a:
            st.plotly_chart(
                create_heat_generation_bar(
                    battery_heat=battery_heat,
                    motor_heat=motor_heat,
                    inverter_heat=inverter_heat
                ),
                use_container_width=True
            )

        with col_b:
            st.plotly_chart(create_cooling_plot(thermal_df), use_container_width=True)

        st.plotly_chart(create_net_heat_plot(thermal_df), use_container_width=True)

        cooling_table = create_cooling_requirement_table(
            battery_heat=battery_heat,
            motor_heat=motor_heat,
            inverter_heat=inverter_heat,
            battery_max_temp=battery_max_temp,
            motor_max_temp=motor_max_temp,
            inverter_max_temp=inverter_max_temp,
            battery_limit=battery_derate_limit_c,
            motor_limit=motor_derate_limit_c,
            inverter_limit=inverter_derate_limit_c
        )

        st.markdown("## Cooling Requirement Summary")

        st.dataframe(cooling_table.round(3), use_container_width=True, hide_index=True)

        st.markdown("## Derating Status")

        battery_status, battery_message = thermal_status(
            "Battery",
            max_temp=battery_max_temp,
            normal_limit=35.0,
            derate_limit=battery_derate_limit_c,
            critical_limit=60.0
        )

        motor_status, motor_message = thermal_status(
            "Motor",
            max_temp=motor_max_temp,
            normal_limit=90.0,
            derate_limit=motor_derate_limit_c,
            critical_limit=motor_derate_limit_c + 25
        )

        inverter_status, inverter_message = thermal_status(
            "Inverter",
            max_temp=inverter_max_temp,
            normal_limit=90.0,
            derate_limit=inverter_derate_limit_c,
            critical_limit=inverter_derate_limit_c + 25
        )

        status_df = pd.DataFrame(
            {
                "Component": ["Battery", "Motor", "Inverter"],
                "Status": [battery_status, motor_status, inverter_status],
                "Message": [battery_message, motor_message, inverter_message]
            }
        )

        st.dataframe(status_df, use_container_width=True, hide_index=True)

        for status, message in [
            (battery_status, battery_message),
            (motor_status, motor_message),
            (inverter_status, inverter_message)
        ]:
            if status == "Safe":
                st.success(message)
            elif status == "Caution":
                st.warning(message)
            else:
                st.error(message)

    with tab4:
        st.markdown("## HVAC Impact: PTC vs Heat Pump")

        h1, h2, h3 = st.columns(3)

        with h1:
            cabin_thermal_load_kw = st.number_input(
                "Cabin thermal load required (kW)",
                min_value=0.1,
                max_value=10.0,
                value=5.0,
                step=0.1,
                format="%.1f"
            )

        with h2:
            ptc_cop = st.number_input(
                "PTC COP",
                min_value=0.5,
                max_value=2.0,
                value=1.0,
                step=0.1,
                format="%.1f"
            )

        with h3:
            heat_pump_cop = st.number_input(
                "Heat pump COP",
                min_value=1.0,
                max_value=5.0,
                value=2.5,
                step=0.1,
                format="%.1f"
            )

        h4, h5, h6 = st.columns(3)

        with h4:
            hvac_speed_kmh = st.number_input(
                "Average vehicle speed (km/h)",
                min_value=5.0,
                max_value=140.0,
                value=50.0,
                step=5.0,
                format="%.1f"
            )

        with h5:
            base_consumption_wh_per_km = st.number_input(
                "Base vehicle consumption without HVAC (Wh/km)",
                min_value=20.0,
                max_value=500.0,
                value=150.0,
                step=5.0,
                format="%.1f"
            )

        with h6:
            usable_battery_kwh = st.number_input(
                "Usable battery energy (kWh)",
                min_value=1.0,
                max_value=250.0,
                value=40.0,
                step=1.0,
                format="%.1f"
            )

        hvac_result = calculate_hvac_comparison(
            cabin_thermal_load_kw=cabin_thermal_load_kw,
            ptc_cop=ptc_cop,
            heat_pump_cop=heat_pump_cop,
            speed_kmh=hvac_speed_kmh,
            base_consumption_wh_per_km=base_consumption_wh_per_km,
            usable_battery_kwh=usable_battery_kwh
        )

        k1, k2, k3, k4 = st.columns(4)

        with k1:
            st.metric("PTC Electric Load", f"{hvac_result['PTC Electric Power (kW)']:.2f} kW")

        with k2:
            st.metric("Heat Pump Electric Load", f"{hvac_result['Heat Pump Electric Power (kW)']:.2f} kW")

        with k3:
            st.metric("PTC Range", f"{hvac_result['PTC Range (km)']:.1f} km")

        with k4:
            st.metric("Heat Pump Range", f"{hvac_result['Heat Pump Range (km)']:.1f} km")

        col_h1, col_h2 = st.columns(2)

        with col_h1:
            st.plotly_chart(create_hvac_bar_chart(hvac_result), use_container_width=True)

        with col_h2:
            st.plotly_chart(create_hvac_range_chart(hvac_result), use_container_width=True)

        hvac_df = pd.DataFrame(
            {
                "Metric": [
                    "Electric Power Required (kW)",
                    "HVAC Wh/km",
                    "Total Wh/km",
                    "Estimated Range (km)"
                ],
                "PTC Heater": [
                    hvac_result["PTC Electric Power (kW)"],
                    hvac_result["PTC HVAC Wh/km"],
                    hvac_result["PTC Total Wh/km"],
                    hvac_result["PTC Range (km)"]
                ],
                "Heat Pump": [
                    hvac_result["Heat Pump Electric Power (kW)"],
                    hvac_result["Heat Pump HVAC Wh/km"],
                    hvac_result["Heat Pump Total Wh/km"],
                    hvac_result["Heat Pump Range (km)"]
                ]
            }
        )

        st.dataframe(hvac_df.round(3), use_container_width=True, hide_index=True)

        st.info(
            f"Heat pump benefit for this condition: approximately {hvac_result['Range Benefit (km)']:.1f} km additional range."
        )

    with tab5:
        st.markdown("## Thermal Design Summary")

        summary_df = pd.DataFrame(
            {
                "Parameter": [
                    "Battery heat generation",
                    "Motor heat generation",
                    "Inverter heat generation",
                    "Total heat generation",
                    "Battery max temperature",
                    "Motor max temperature",
                    "Inverter max temperature",
                    "Battery derating limit",
                    "Motor derating limit",
                    "Inverter derating limit"
                ],
                "Value": [
                    f"{battery_heat:.3f} kW",
                    f"{motor_heat:.3f} kW",
                    f"{inverter_heat:.3f} kW",
                    f"{battery_heat + motor_heat + inverter_heat:.3f} kW",
                    f"{battery_max_temp:.2f} °C",
                    f"{motor_max_temp:.2f} °C",
                    f"{inverter_max_temp:.2f} °C",
                    f"{battery_derate_limit_c:.2f} °C",
                    f"{motor_derate_limit_c:.2f} °C",
                    f"{inverter_derate_limit_c:.2f} °C"
                ]
            }
        )

        st.dataframe(summary_df, use_container_width=True, hide_index=True)

        st.markdown("## Engineering Interpretation")

        st.write(
            """
            Battery heat rises with the square of current, so fast charging and high-power acceleration can quickly increase thermal load.  
            Motor heat depends on operating power and efficiency.  
            Inverter heat depends on device losses, switching conditions, and cooling path.  
            If cooling power is lower than generated heat for a long duration, component temperature will continue rising and derating becomes necessary.
            """
        )

        st.markdown("## Next Industry-Level Improvements")

        st.write(
            """
            To move this module toward industry-grade accuracy, add:
            - Battery module-level thermal network
            - Coolant flow-rate and radiator model
            - Chiller/refrigerant loop model
            - Motor winding and rotor temperature separation
            - Inverter junction-to-case thermal impedance
            - Drive-cycle-dependent heat generation
            - Fast-charging preconditioning logic
            - Thermal runaway warning logic
            - Exportable thermal test report
            """
        )