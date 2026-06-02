import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from modules.battery_chemistry import (
    load_battery_chemistry_data,
    generate_ocv_curve
)


def get_default_bms_limits(chemistry):
    limits = {
        "LFP": {
            "OVP_V": 3.65,
            "UVP_V": 2.00,
            "OTP_C": 60.0,
            "OCP_A": 500.0,
            "Imbalance_mV": 30.0
        },
        "NMC": {
            "OVP_V": 4.25,
            "UVP_V": 2.50,
            "OTP_C": 60.0,
            "OCP_A": 500.0,
            "Imbalance_mV": 30.0
        },
        "NCA": {
            "OVP_V": 4.25,
            "UVP_V": 2.50,
            "OTP_C": 60.0,
            "OCP_A": 500.0,
            "Imbalance_mV": 30.0
        },
        "LTO": {
            "OVP_V": 2.80,
            "UVP_V": 1.50,
            "OTP_C": 60.0,
            "OCP_A": 500.0,
            "Imbalance_mV": 30.0
        }
    }

    return limits.get(
        chemistry,
        {
            "OVP_V": 4.25,
            "UVP_V": 2.50,
            "OTP_C": 60.0,
            "OCP_A": 500.0,
            "Imbalance_mV": 30.0
        }
    )


def ocv_from_soc(chemistry, soc_fraction):
    soc_percent_table, voltage_table = generate_ocv_curve(chemistry)
    soc_percent = np.clip(soc_fraction * 100, 0, 100)
    return np.interp(soc_percent, soc_percent_table, voltage_table)


def soc_from_ocv(chemistry, ocv_voltage):
    soc_percent_table, voltage_table = generate_ocv_curve(chemistry)

    sort_idx = np.argsort(voltage_table)
    voltage_sorted = voltage_table[sort_idx]
    soc_sorted = soc_percent_table[sort_idx]

    soc_percent = np.interp(
        ocv_voltage,
        voltage_sorted,
        soc_sorted,
        left=soc_sorted[0],
        right=soc_sorted[-1]
    )

    return np.clip(soc_percent / 100, 0, 1)


def generate_current_profile(
    profile_type,
    time_s,
    discharge_current_a,
    charge_current_a,
    regen_current_a
):
    current = np.zeros_like(time_s, dtype=float)
    duration = time_s[-1] if len(time_s) > 0 else 1

    if profile_type == "Constant Discharge":
        current[:] = discharge_current_a

    elif profile_type == "Constant Charge":
        current[:] = -charge_current_a

    elif profile_type == "Charge-Rest-Discharge":
        for i, t in enumerate(time_s):
            if t < 0.30 * duration:
                current[i] = -charge_current_a
            elif t < 0.50 * duration:
                current[i] = 0.0
            else:
                current[i] = discharge_current_a

    elif profile_type == "Urban Stop-Go with Regen":
        period = 120.0
        for i, t in enumerate(time_s):
            phase = t % period
            if phase < 45:
                current[i] = discharge_current_a
            elif phase < 65:
                current[i] = 0.20 * discharge_current_a
            elif phase < 85:
                current[i] = -regen_current_a
            else:
                current[i] = 0.0

    elif profile_type == "Aggressive Pulsed Drive":
        period = 90.0
        for i, t in enumerate(time_s):
            phase = t % period
            if phase < 25:
                current[i] = 1.4 * discharge_current_a
            elif phase < 55:
                current[i] = 0.6 * discharge_current_a
            elif phase < 70:
                current[i] = -0.5 * regen_current_a
            else:
                current[i] = 0.0

    else:
        current[:] = discharge_current_a

    return current


def simulate_bms_soc(
    chemistry,
    n_series,
    n_parallel,
    cell_capacity_ah,
    initial_soc_percent,
    initial_estimation_error_percent,
    profile_type,
    duration_min,
    time_step_s,
    discharge_current_a,
    charge_current_a,
    regen_current_a,
    current_sensor_offset_a,
    cell_resistance_mohm,
    voltage_noise_mV,
    enable_voltage_correction,
    rest_current_threshold_a,
    continuous_kf_correction,
    ambient_temp_c,
    initial_temp_c,
    cooling_coefficient_w_per_k,
    thermal_mass_kj_per_k,
    max_cell_imbalance_mV,
    bms_limits
):
    time_s = np.arange(0, duration_min * 60 + time_step_s, time_step_s)
    current_true = generate_current_profile(
        profile_type=profile_type,
        time_s=time_s,
        discharge_current_a=discharge_current_a,
        charge_current_a=charge_current_a,
        regen_current_a=regen_current_a
    )

    capacity_as = cell_capacity_ah * n_parallel * 3600.0
    r_cell_ohm = cell_resistance_mohm / 1000.0
    pack_resistance_ohm = r_cell_ohm * n_series / max(n_parallel, 1)

    true_soc = np.zeros_like(time_s, dtype=float)
    coulomb_soc = np.zeros_like(time_s, dtype=float)
    kf_soc = np.zeros_like(time_s, dtype=float)

    ocv_true = np.zeros_like(time_s, dtype=float)
    terminal_cell_v = np.zeros_like(time_s, dtype=float)
    measured_cell_v = np.zeros_like(time_s, dtype=float)
    high_cell_v = np.zeros_like(time_s, dtype=float)
    low_cell_v = np.zeros_like(time_s, dtype=float)
    pack_voltage = np.zeros_like(time_s, dtype=float)
    temperature_c = np.zeros_like(time_s, dtype=float)

    ovp_flag = np.zeros_like(time_s, dtype=int)
    uvp_flag = np.zeros_like(time_s, dtype=int)
    otp_flag = np.zeros_like(time_s, dtype=int)
    ocp_flag = np.zeros_like(time_s, dtype=int)
    imbalance_flag = np.zeros_like(time_s, dtype=int)

    true_soc[0] = np.clip(initial_soc_percent / 100.0, 0, 1)
    coulomb_soc[0] = np.clip((initial_soc_percent + initial_estimation_error_percent) / 100.0, 0, 1)
    kf_soc[0] = coulomb_soc[0]
    temperature_c[0] = initial_temp_c

    p_cov = 0.01
    process_noise = 1e-6
    rest_measurement_noise = (0.015) ** 2
    dynamic_measurement_noise = (0.08) ** 2

    for k in range(len(time_s)):
        i_true = current_true[k]
        i_measured = i_true + current_sensor_offset_a
        cell_current = i_true / max(n_parallel, 1)
        measured_cell_current = i_measured / max(n_parallel, 1)

        if k > 0:
            dt = time_s[k] - time_s[k - 1]

            true_soc[k] = true_soc[k - 1] - (i_true * dt / capacity_as)
            coulomb_soc[k] = coulomb_soc[k - 1] - (i_measured * dt / capacity_as)

            true_soc[k] = np.clip(true_soc[k], 0, 1)
            coulomb_soc[k] = np.clip(coulomb_soc[k], 0, 1)

            # Kalman-style SOC prediction using Coulomb counting.
            kf_pred = kf_soc[k - 1] - (i_measured * dt / capacity_as)
            kf_pred = np.clip(kf_pred, 0, 1)

            p_cov = p_cov + process_noise

            kf_soc[k] = kf_pred

            # Thermal model.
            heat_gen_w = (i_true ** 2) * pack_resistance_ohm
            cooling_w = cooling_coefficient_w_per_k * max(temperature_c[k - 1] - ambient_temp_c, 0)
            dtemp = (heat_gen_w - cooling_w) * dt / max(thermal_mass_kj_per_k * 1000.0, 1)
            temperature_c[k] = temperature_c[k - 1] + dtemp

        else:
            temperature_c[k] = initial_temp_c

        ocv_true[k] = ocv_from_soc(chemistry, true_soc[k])
        terminal_cell_v[k] = ocv_true[k] - cell_current * r_cell_ohm

        deterministic_noise_v = (voltage_noise_mV / 1000.0) * np.sin(0.01 * time_s[k])
        measured_cell_v[k] = terminal_cell_v[k] + deterministic_noise_v

        # Simple OCV reconstruction using internal resistance compensation.
        reconstructed_ocv = measured_cell_v[k] + measured_cell_current * r_cell_ohm
        measured_soc_from_ocv = soc_from_ocv(chemistry, reconstructed_ocv)

        if k > 0 and enable_voltage_correction:
            if abs(i_true) <= rest_current_threshold_a:
                kalman_gain = p_cov / (p_cov + rest_measurement_noise)
                kf_soc[k] = kf_soc[k] + kalman_gain * (measured_soc_from_ocv - kf_soc[k])
                p_cov = (1 - kalman_gain) * p_cov

            elif continuous_kf_correction:
                kalman_gain = p_cov / (p_cov + dynamic_measurement_noise)
                kalman_gain = 0.10 * kalman_gain
                kf_soc[k] = kf_soc[k] + kalman_gain * (measured_soc_from_ocv - kf_soc[k])
                p_cov = (1 - kalman_gain) * p_cov

            kf_soc[k] = np.clip(kf_soc[k], 0, 1)

        half_imbalance_v = (max_cell_imbalance_mV / 1000.0) / 2.0
        high_cell_v[k] = terminal_cell_v[k] + half_imbalance_v
        low_cell_v[k] = terminal_cell_v[k] - half_imbalance_v
        pack_voltage[k] = terminal_cell_v[k] * n_series

        ovp_flag[k] = int(high_cell_v[k] > bms_limits["OVP_V"])
        uvp_flag[k] = int(low_cell_v[k] < bms_limits["UVP_V"])
        otp_flag[k] = int(temperature_c[k] > bms_limits["OTP_C"])
        ocp_flag[k] = int(abs(i_true) > bms_limits["OCP_A"])
        imbalance_flag[k] = int(max_cell_imbalance_mV > bms_limits["Imbalance_mV"])

    df = pd.DataFrame(
        {
            "Time (s)": time_s,
            "Time (min)": time_s / 60.0,
            "Current True (A)": current_true,
            "Current Measured (A)": current_true + current_sensor_offset_a,
            "True SOC (%)": true_soc * 100,
            "Coulomb SOC (%)": coulomb_soc * 100,
            "Kalman-Corrected SOC (%)": kf_soc * 100,
            "Coulomb Error (%)": (coulomb_soc - true_soc) * 100,
            "Kalman Error (%)": (kf_soc - true_soc) * 100,
            "OCV True (V/cell)": ocv_true,
            "Terminal Voltage (V/cell)": terminal_cell_v,
            "Measured Voltage (V/cell)": measured_cell_v,
            "High Cell Voltage (V)": high_cell_v,
            "Low Cell Voltage (V)": low_cell_v,
            "Pack Voltage (V)": pack_voltage,
            "Temperature (°C)": temperature_c,
            "OVP": ovp_flag,
            "UVP": uvp_flag,
            "OTP": otp_flag,
            "OCP": ocp_flag,
            "Imbalance": imbalance_flag
        }
    )

    return df


def create_soc_plot(df):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["Time (min)"],
            y=df["True SOC (%)"],
            mode="lines",
            name="True SOC"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["Time (min)"],
            y=df["Coulomb SOC (%)"],
            mode="lines",
            name="Coulomb Counting SOC"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["Time (min)"],
            y=df["Kalman-Corrected SOC (%)"],
            mode="lines",
            name="Kalman-Corrected SOC"
        )
    )

    fig.update_layout(
        title="SOC Estimation Comparison",
        xaxis_title="Time (min)",
        yaxis_title="SOC (%)",
        height=460
    )

    return fig


def create_error_plot(df):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["Time (min)"],
            y=df["Coulomb Error (%)"],
            mode="lines",
            name="Coulomb Error"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["Time (min)"],
            y=df["Kalman Error (%)"],
            mode="lines",
            name="Kalman-Corrected Error"
        )
    )

    fig.update_layout(
        title="SOC Estimation Error",
        xaxis_title="Time (min)",
        yaxis_title="Error (%)",
        height=430
    )

    return fig


def create_current_plot(df):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["Time (min)"],
            y=df["Current True (A)"],
            mode="lines",
            name="True Current"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["Time (min)"],
            y=df["Current Measured (A)"],
            mode="lines",
            name="Measured Current"
        )
    )

    fig.update_layout(
        title="Current Profile",
        xaxis_title="Time (min)",
        yaxis_title="Current (A), Positive = Discharge",
        height=430
    )

    return fig


def create_voltage_plot(df):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["Time (min)"],
            y=df["Terminal Voltage (V/cell)"],
            mode="lines",
            name="Cell Terminal Voltage"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["Time (min)"],
            y=df["High Cell Voltage (V)"],
            mode="lines",
            name="Highest Cell"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["Time (min)"],
            y=df["Low Cell Voltage (V)"],
            mode="lines",
            name="Lowest Cell"
        )
    )

    fig.update_layout(
        title="Cell Voltage Monitoring",
        xaxis_title="Time (min)",
        yaxis_title="Voltage (V)",
        height=430
    )

    return fig


def create_temperature_plot(df):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["Time (min)"],
            y=df["Temperature (°C)"],
            mode="lines",
            name="Battery Temperature"
        )
    )

    fig.update_layout(
        title="Battery Temperature Response",
        xaxis_title="Time (min)",
        yaxis_title="Temperature (°C)",
        height=430
    )

    return fig


def create_flag_summary(df):
    flags = ["OVP", "UVP", "OTP", "OCP", "Imbalance"]
    values = [int(df[f].sum()) for f in flags]

    flag_df = pd.DataFrame(
        {
            "BMS Flag": flags,
            "Triggered Samples": values
        }
    )

    fig = go.Figure(
        data=[
            go.Bar(
                x=flags,
                y=values,
                text=values,
                textposition="auto"
            )
        ]
    )

    fig.update_layout(
        title="BMS Protection Flag Summary",
        xaxis_title="Flag",
        yaxis_title="Triggered Samples",
        height=400
    )

    return flag_df, fig


def estimate_passive_balancing_time(cell_capacity_ah, imbalance_equivalent_soc_percent, balance_current_ma):
    imbalance_charge_ah = cell_capacity_ah * imbalance_equivalent_soc_percent / 100.0
    balance_current_a = balance_current_ma / 1000.0

    if balance_current_a <= 0:
        return np.nan

    return imbalance_charge_ah / balance_current_a


def run_bms_soc_lab():
    st.markdown("# BMS & SOC Lab")
    st.caption("Simulate SOC estimation, current-sensor drift, OCV correction, BMS protection limits, and passive balancing.")

    st.info(
        "This is an educational engineering model. A production BMS requires cell-specific OCV maps, current-sensor calibration, "
        "thermal characterization, validated ECM parameters, redundancy, diagnostics, and functional-safety design."
    )

    chemistry_df = load_battery_chemistry_data()

    tab_inputs, tab_soc, tab_voltage_temp, tab_flags, tab_balancing = st.tabs(
        [
            "Inputs",
            "SOC Estimation",
            "Voltage & Thermal",
            "BMS Protection Flags",
            "Cell Balancing"
        ]
    )

    with tab_inputs:
        st.markdown("## Pack and Chemistry Inputs")

        col1, col2, col3 = st.columns(3)

        with col1:
            chemistry = st.selectbox(
                "Cell chemistry",
                options=chemistry_df["Chemistry"].tolist(),
                index=0
            )

        selected_row = chemistry_df[chemistry_df["Chemistry"] == chemistry].iloc[0]
        default_limits = get_default_bms_limits(chemistry)

        with col2:
            n_series = st.number_input(
                "Series cells (S)",
                min_value=1,
                max_value=300,
                value=96,
                step=1
            )

        with col3:
            n_parallel = st.number_input(
                "Parallel strings (P)",
                min_value=1,
                max_value=100,
                value=1,
                step=1
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
            initial_soc_percent = st.slider(
                "Initial true SOC (%)",
                min_value=0,
                max_value=100,
                value=80,
                step=1
            )

        with col6:
            initial_estimation_error_percent = st.slider(
                "Initial SOC estimation error (%)",
                min_value=-20,
                max_value=20,
                value=0,
                step=1
            )

        st.divider()

        st.markdown("## Current Profile and Sensor Inputs")

        col7, col8, col9 = st.columns(3)

        with col7:
            profile_type = st.selectbox(
                "Current profile",
                [
                    "Constant Discharge",
                    "Constant Charge",
                    "Charge-Rest-Discharge",
                    "Urban Stop-Go with Regen",
                    "Aggressive Pulsed Drive"
                ],
                index=3
            )

        with col8:
            duration_min = st.number_input(
                "Simulation duration (min)",
                min_value=1.0,
                max_value=240.0,
                value=60.0,
                step=5.0,
                format="%.1f"
            )

        with col9:
            time_step_s = st.number_input(
                "Time step (s)",
                min_value=0.5,
                max_value=60.0,
                value=2.0,
                step=0.5,
                format="%.1f"
            )

        col10, col11, col12 = st.columns(3)

        with col10:
            discharge_current_a = st.number_input(
                "Discharge current (A)",
                min_value=0.0,
                max_value=2000.0,
                value=150.0,
                step=10.0,
                format="%.1f"
            )

        with col11:
            charge_current_a = st.number_input(
                "Charge current (A)",
                min_value=0.0,
                max_value=2000.0,
                value=100.0,
                step=10.0,
                format="%.1f"
            )

        with col12:
            regen_current_a = st.number_input(
                "Regen current (A)",
                min_value=0.0,
                max_value=2000.0,
                value=60.0,
                step=10.0,
                format="%.1f"
            )

        col13, col14, col15 = st.columns(3)

        with col13:
            current_sensor_offset_a = st.number_input(
                "Current sensor offset (A)",
                min_value=-20.0,
                max_value=20.0,
                value=0.5,
                step=0.1,
                format="%.2f"
            )

        with col14:
            cell_resistance_mohm = st.number_input(
                "Cell internal resistance (mΩ)",
                min_value=0.05,
                max_value=20.0,
                value=1.0,
                step=0.05,
                format="%.2f"
            )

        with col15:
            voltage_noise_mV = st.number_input(
                "Voltage measurement noise (mV)",
                min_value=0.0,
                max_value=50.0,
                value=2.0,
                step=0.5,
                format="%.1f"
            )

        st.divider()

        st.markdown("## SOC Correction Settings")

        col16, col17, col18 = st.columns(3)

        with col16:
            enable_voltage_correction = st.checkbox(
                "Enable OCV/Kalman-style correction",
                value=True
            )

        with col17:
            rest_current_threshold_a = st.number_input(
                "Rest-current threshold (A)",
                min_value=0.0,
                max_value=100.0,
                value=5.0,
                step=1.0,
                format="%.1f"
            )

        with col18:
            continuous_kf_correction = st.checkbox(
                "Allow weak correction during dynamic operation",
                value=True
            )

        st.divider()

        st.markdown("## Thermal and BMS Limit Inputs")

        col19, col20, col21 = st.columns(3)

        with col19:
            ambient_temp_c = st.number_input(
                "Ambient temperature (°C)",
                min_value=-10.0,
                max_value=60.0,
                value=35.0,
                step=1.0,
                format="%.1f"
            )

        with col20:
            initial_temp_c = st.number_input(
                "Initial battery temperature (°C)",
                min_value=-10.0,
                max_value=80.0,
                value=35.0,
                step=1.0,
                format="%.1f"
            )

        with col21:
            cooling_coefficient_w_per_k = st.number_input(
                "Cooling coefficient (W/K)",
                min_value=0.0,
                max_value=1000.0,
                value=80.0,
                step=5.0,
                format="%.1f"
            )

        col22, col23, col24 = st.columns(3)

        with col22:
            thermal_mass_kj_per_k = st.number_input(
                "Pack thermal mass (kJ/K)",
                min_value=1.0,
                max_value=5000.0,
                value=500.0,
                step=10.0,
                format="%.1f"
            )

        with col23:
            max_cell_imbalance_mV = st.number_input(
                "Maximum cell imbalance (mV)",
                min_value=0.0,
                max_value=300.0,
                value=20.0,
                step=1.0,
                format="%.1f"
            )

        with col24:
            st.write("")
            st.write("")
            st.caption("Positive current = discharge; negative current = charge/regen.")

        col25, col26, col27, col28, col29 = st.columns(5)

        with col25:
            ovp_v = st.number_input(
                "OVP limit (V/cell)",
                min_value=1.0,
                max_value=5.0,
                value=float(default_limits["OVP_V"]),
                step=0.01,
                format="%.2f"
            )

        with col26:
            uvp_v = st.number_input(
                "UVP limit (V/cell)",
                min_value=0.5,
                max_value=5.0,
                value=float(default_limits["UVP_V"]),
                step=0.01,
                format="%.2f"
            )

        with col27:
            otp_c = st.number_input(
                "OTP limit (°C)",
                min_value=30.0,
                max_value=100.0,
                value=float(default_limits["OTP_C"]),
                step=1.0,
                format="%.1f"
            )

        with col28:
            ocp_a = st.number_input(
                "OCP limit (A)",
                min_value=10.0,
                max_value=3000.0,
                value=float(default_limits["OCP_A"]),
                step=10.0,
                format="%.1f"
            )

        with col29:
            imbalance_limit_mV = st.number_input(
                "Imbalance warning (mV)",
                min_value=1.0,
                max_value=300.0,
                value=float(default_limits["Imbalance_mV"]),
                step=1.0,
                format="%.1f"
            )

    bms_limits = {
        "OVP_V": ovp_v,
        "UVP_V": uvp_v,
        "OTP_C": otp_c,
        "OCP_A": ocp_a,
        "Imbalance_mV": imbalance_limit_mV
    }

    df = simulate_bms_soc(
        chemistry=chemistry,
        n_series=int(n_series),
        n_parallel=int(n_parallel),
        cell_capacity_ah=cell_capacity_ah,
        initial_soc_percent=initial_soc_percent,
        initial_estimation_error_percent=initial_estimation_error_percent,
        profile_type=profile_type,
        duration_min=duration_min,
        time_step_s=time_step_s,
        discharge_current_a=discharge_current_a,
        charge_current_a=charge_current_a,
        regen_current_a=regen_current_a,
        current_sensor_offset_a=current_sensor_offset_a,
        cell_resistance_mohm=cell_resistance_mohm,
        voltage_noise_mV=voltage_noise_mV,
        enable_voltage_correction=enable_voltage_correction,
        rest_current_threshold_a=rest_current_threshold_a,
        continuous_kf_correction=continuous_kf_correction,
        ambient_temp_c=ambient_temp_c,
        initial_temp_c=initial_temp_c,
        cooling_coefficient_w_per_k=cooling_coefficient_w_per_k,
        thermal_mass_kj_per_k=thermal_mass_kj_per_k,
        max_cell_imbalance_mV=max_cell_imbalance_mV,
        bms_limits=bms_limits
    )

    with tab_soc:
        st.markdown("## SOC Estimation Results")

        final_true_soc = df["True SOC (%)"].iloc[-1]
        final_coulomb_soc = df["Coulomb SOC (%)"].iloc[-1]
        final_kf_soc = df["Kalman-Corrected SOC (%)"].iloc[-1]
        max_coulomb_error = df["Coulomb Error (%)"].abs().max()
        max_kf_error = df["Kalman Error (%)"].abs().max()

        c1, c2, c3, c4, c5 = st.columns(5)

        with c1:
            st.metric("Final True SOC", f"{final_true_soc:.2f}%")

        with c2:
            st.metric("Final Coulomb SOC", f"{final_coulomb_soc:.2f}%")

        with c3:
            st.metric("Final Corrected SOC", f"{final_kf_soc:.2f}%")

        with c4:
            st.metric("Max Coulomb Error", f"{max_coulomb_error:.2f}%")

        with c5:
            st.metric("Max Corrected Error", f"{max_kf_error:.2f}%")

        st.plotly_chart(create_soc_plot(df), use_container_width=True)
        st.plotly_chart(create_error_plot(df), use_container_width=True)
        st.plotly_chart(create_current_plot(df), use_container_width=True)

        st.markdown("### SOC Interpretation")

        if max_coulomb_error > max_kf_error:
            st.success(
                "The correction layer reduced SOC estimation error compared with pure Coulomb counting."
            )
        else:
            st.warning(
                "The correction layer did not significantly improve SOC error in this case. Check OCV curve flatness, voltage noise, current profile, and rest periods."
            )

        if chemistry == "LFP":
            st.info(
                "LFP has a flatter OCV-SOC region, so voltage-based correction is less sensitive in the middle SOC range."
            )

    with tab_voltage_temp:
        st.markdown("## Voltage and Thermal Monitoring")

        v1, v2, v3, v4 = st.columns(4)

        with v1:
            st.metric("Final Pack Voltage", f"{df['Pack Voltage (V)'].iloc[-1]:.1f} V")

        with v2:
            st.metric("Max Cell Voltage", f"{df['High Cell Voltage (V)'].max():.3f} V")

        with v3:
            st.metric("Min Cell Voltage", f"{df['Low Cell Voltage (V)'].min():.3f} V")

        with v4:
            st.metric("Max Temperature", f"{df['Temperature (°C)'].max():.1f} °C")

        col_a, col_b = st.columns(2)

        with col_a:
            st.plotly_chart(create_voltage_plot(df), use_container_width=True)

        with col_b:
            st.plotly_chart(create_temperature_plot(df), use_container_width=True)

        st.markdown("### Thermal Interpretation")

        if df["Temperature (°C)"].max() > otp_c:
            st.error("Battery temperature crossed the OTP limit. BMS should reduce power or open contactors.")
        elif df["Temperature (°C)"].max() > otp_c - 5:
            st.warning("Battery temperature is close to the OTP limit. Thermal derating may be required.")
        else:
            st.success("Battery temperature remained below the OTP limit.")

    with tab_flags:
        st.markdown("## BMS Protection Flags")

        flag_df, flag_fig = create_flag_summary(df)

        st.plotly_chart(flag_fig, use_container_width=True)
        st.dataframe(flag_df, use_container_width=True, hide_index=True)

        st.markdown("### Protection Status")

        total_flag_count = int(flag_df["Triggered Samples"].sum())

        if total_flag_count == 0:
            st.success("No BMS protection flags were triggered in this simulation.")
        else:
            st.error("One or more BMS protection flags were triggered. Review voltage, current, temperature, and imbalance settings.")

        st.markdown("### Detailed Simulation Data")

        display_columns = [
            "Time (min)",
            "Current True (A)",
            "True SOC (%)",
            "Coulomb SOC (%)",
            "Kalman-Corrected SOC (%)",
            "Terminal Voltage (V/cell)",
            "High Cell Voltage (V)",
            "Low Cell Voltage (V)",
            "Pack Voltage (V)",
            "Temperature (°C)",
            "OVP",
            "UVP",
            "OTP",
            "OCP",
            "Imbalance"
        ]

        st.dataframe(
            df[display_columns].round(3),
            use_container_width=True,
            hide_index=True
        )

    with tab_balancing:
        st.markdown("## Passive Cell Balancing Estimator")

        st.write(
            "Passive balancing discharges higher-voltage cells through resistors. It is simple and low-cost, but energy is lost as heat and balancing can be slow."
        )

        b1, b2, b3 = st.columns(3)

        with b1:
            imbalance_equivalent_soc_percent = st.number_input(
                "Equivalent SOC imbalance (%)",
                min_value=0.01,
                max_value=20.0,
                value=2.0,
                step=0.1,
                format="%.2f"
            )

        with b2:
            balance_current_ma = st.number_input(
                "Passive balancing current (mA)",
                min_value=1.0,
                max_value=1000.0,
                value=50.0,
                step=5.0,
                format="%.1f"
            )

        with b3:
            balance_resistor_ohm = st.number_input(
                "Balance resistor (Ω)",
                min_value=1.0,
                max_value=1000.0,
                value=68.0,
                step=1.0,
                format="%.1f"
            )

        balance_time_h = estimate_passive_balancing_time(
            cell_capacity_ah=cell_capacity_ah,
            imbalance_equivalent_soc_percent=imbalance_equivalent_soc_percent,
            balance_current_ma=balance_current_ma
        )

        balance_current_a = balance_current_ma / 1000.0
        balance_loss_w = (balance_current_a ** 2) * balance_resistor_ohm

        d1, d2, d3 = st.columns(3)

        with d1:
            st.metric("Estimated Balance Time", f"{balance_time_h:.1f} h")

        with d2:
            st.metric("Balance Current", f"{balance_current_ma:.1f} mA")

        with d3:
            st.metric("Heat in Balance Resistor", f"{balance_loss_w:.3f} W")

        st.warning(
            "This is a simplified balancing-time estimate. Real BMS balancing depends on cell voltage curve, balancing threshold, thermal limits, charge state, and AFE hardware."
        )

        st.markdown("## BMS Design Notes")

        st.write(
            """
            A production BMS would normally include:
            - Cell voltage sensing through an AFE
            - Temperature sensors across modules
            - Pack current sensing using shunt or Hall sensor
            - SOC, SOH, and SOP estimation
            - Passive or active balancing
            - OVP, UVP, OTP, OCP, and short-circuit protection
            - Contactor and precharge control
            - CAN communication with the vehicle controller
            """
        )