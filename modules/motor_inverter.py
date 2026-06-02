import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go


MOTOR_DATA_PATH = "data/motor_presets.csv"
INVERTER_DATA_PATH = "data/inverter_devices.csv"


@st.cache_data
def load_motor_presets():
    return pd.read_csv(MOTOR_DATA_PATH)


@st.cache_data
def load_inverter_devices():
    return pd.read_csv(INVERTER_DATA_PATH)


def calculate_torque_speed_curve(peak_torque_nm, base_speed_rpm, max_speed_rpm):
    rpm = np.linspace(1, max_speed_rpm, 400)
    omega = rpm * 2 * np.pi / 60

    base_omega = base_speed_rpm * 2 * np.pi / 60
    peak_power_kw = peak_torque_nm * base_omega / 1000

    torque = np.zeros_like(rpm)

    for i, speed in enumerate(rpm):
        if speed <= base_speed_rpm:
            torque[i] = peak_torque_nm
        else:
            torque[i] = (peak_power_kw * 1000) / omega[i]

    torque = np.minimum(torque, peak_torque_nm)
    power_kw = torque * omega / 1000

    df = pd.DataFrame(
        {
            "Speed RPM": rpm,
            "Torque Nm": torque,
            "Power kW": power_kw
        }
    )

    return df, peak_power_kw


def calculate_vehicle_tractive_curve(df_motor, gear_ratio, wheel_radius_m, transmission_efficiency):
    motor_rpm = df_motor["Speed RPM"].values
    motor_torque = df_motor["Torque Nm"].values

    wheel_torque = motor_torque * gear_ratio * transmission_efficiency
    tractive_force = wheel_torque / wheel_radius_m

    wheel_rpm = motor_rpm / gear_ratio
    vehicle_speed_kmh = wheel_rpm * 2 * np.pi * wheel_radius_m * 60 / 1000

    df = pd.DataFrame(
        {
            "Vehicle Speed km/h": vehicle_speed_kmh,
            "Tractive Force N": tractive_force,
            "Wheel Torque Nm": wheel_torque
        }
    )

    return df


def create_torque_speed_plot(df_motor, base_speed_rpm):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df_motor["Speed RPM"],
            y=df_motor["Torque Nm"],
            mode="lines",
            name="Torque"
        )
    )

    fig.add_vline(
        x=base_speed_rpm,
        line_dash="dash",
        annotation_text="Base Speed",
        annotation_position="top right"
    )

    fig.update_layout(
        title="Motor Torque-Speed Curve",
        xaxis_title="Speed (RPM)",
        yaxis_title="Torque (Nm)",
        height=430
    )

    return fig


def create_power_speed_plot(df_motor, base_speed_rpm):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df_motor["Speed RPM"],
            y=df_motor["Power kW"],
            mode="lines",
            name="Power"
        )
    )

    fig.add_vline(
        x=base_speed_rpm,
        line_dash="dash",
        annotation_text="Base Speed",
        annotation_position="top right"
    )

    fig.update_layout(
        title="Motor Power-Speed Curve",
        xaxis_title="Speed (RPM)",
        yaxis_title="Power (kW)",
        height=430
    )

    return fig


def create_tractive_force_plot(df_vehicle):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df_vehicle["Vehicle Speed km/h"],
            y=df_vehicle["Tractive Force N"],
            mode="lines",
            name="Tractive Force"
        )
    )

    fig.update_layout(
        title="Wheel Tractive Force vs Vehicle Speed",
        xaxis_title="Vehicle Speed (km/h)",
        yaxis_title="Tractive Force (N)",
        height=430
    )

    return fig


def create_efficiency_map(peak_efficiency_percent, max_speed_rpm, peak_torque_nm):
    speed_grid = np.linspace(0, max_speed_rpm, 80)
    torque_grid = np.linspace(0, peak_torque_nm, 80)

    speed_norm = speed_grid / max_speed_rpm
    torque_norm = torque_grid / peak_torque_nm

    z = np.zeros((len(torque_grid), len(speed_grid)))

    for i, tq in enumerate(torque_norm):
        for j, spd in enumerate(speed_norm):
            distance_from_sweet_spot = ((spd - 0.45) ** 2 + (tq - 0.45) ** 2) ** 0.5
            low_speed_penalty = 0.10 * np.exp(-spd * 12)
            high_speed_penalty = 0.08 * max(spd - 0.75, 0)
            high_torque_penalty = 0.08 * max(tq - 0.75, 0)

            efficiency = (
                peak_efficiency_percent / 100
                - 0.22 * distance_from_sweet_spot
                - low_speed_penalty
                - high_speed_penalty
                - high_torque_penalty
            )

            z[i, j] = np.clip(efficiency * 100, 55, peak_efficiency_percent)

    fig = go.Figure(
        data=go.Heatmap(
            x=speed_grid,
            y=torque_grid,
            z=z,
            colorbar=dict(title="Efficiency (%)")
        )
    )

    fig.update_layout(
        title="Approximate Motor Efficiency Map",
        xaxis_title="Speed (RPM)",
        yaxis_title="Torque (Nm)",
        height=500
    )

    return fig


def calculate_inverter_losses(
    device_type,
    motor_output_power_kw,
    vdc,
    irms,
    iavg,
    fsw_khz,
    rds_mohm,
    vce_sat,
    rce_mohm,
    eon_mj,
    eoff_mj,
    diode_loss_w
):
    fsw_hz = fsw_khz * 1000

    if device_type == "Si IGBT":
        p_cond_w = 3 * (vce_sat * iavg + (irms ** 2) * (rce_mohm / 1000))
    else:
        p_cond_w = 3 * (irms ** 2) * (rds_mohm / 1000)

    p_sw_w = 6 * fsw_hz * (eon_mj + eoff_mj) * 1e-3 * (vdc / 400) * (irms / 100)

    total_loss_w = p_cond_w + p_sw_w + diode_loss_w

    motor_output_power_w = motor_output_power_kw * 1000
    inverter_input_power_w = motor_output_power_w + total_loss_w

    if inverter_input_power_w > 0:
        inverter_efficiency_percent = motor_output_power_w / inverter_input_power_w * 100
    else:
        inverter_efficiency_percent = 0

    return {
        "Conduction Loss W": p_cond_w,
        "Switching Loss W": p_sw_w,
        "Diode / Misc Loss W": diode_loss_w,
        "Total Inverter Loss W": total_loss_w,
        "Inverter Efficiency Percent": inverter_efficiency_percent,
        "Cooling Load kW": total_loss_w / 1000
    }


def create_loss_breakdown_chart(loss_result):
    labels = ["Conduction Loss", "Switching Loss", "Diode / Misc Loss"]
    values = [
        loss_result["Conduction Loss W"],
        loss_result["Switching Loss W"],
        loss_result["Diode / Misc Loss W"]
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
        title="Inverter Loss Breakdown",
        xaxis_title="Loss Component",
        yaxis_title="Power Loss (W)",
        height=430
    )

    return fig


def create_device_comparison_chart(inverter_df):
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=inverter_df["Device_Type"],
            y=inverter_df["Typical_Switching_Max_kHz"],
            name="Max Typical Switching Frequency (kHz)"
        )
    )

    fig.update_layout(
        title="Inverter Device Switching Capability",
        xaxis_title="Device",
        yaxis_title="Switching Frequency (kHz)",
        height=430
    )

    return fig


def create_motor_score_chart(motor_df):
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=motor_df["Motor_Type"],
            y=motor_df["Peak_Efficiency_Percent"],
            name="Peak Efficiency (%)"
        )
    )

    fig.update_layout(
        title="Motor Type Peak Efficiency Comparison",
        xaxis_title="Motor Type",
        yaxis_title="Peak Efficiency (%)",
        height=430
    )

    return fig


def make_motor_interpretation(motor_type):
    if motor_type == "PMSM":
        return (
            "PMSM is a strong default for passenger EVs because it provides high efficiency, high power density, "
            "and smooth torque control. The main limitation is rare-earth magnet dependence."
        )
    if motor_type == "IM":
        return (
            "Induction motors are rugged and magnet-free, but usually have lower efficiency and higher mass than PMSM/IPM designs."
        )
    if motor_type == "BLDC":
        return (
            "BLDC motors are suitable for low-cost two-wheelers and smaller EVs, but they are less ideal for high-performance traction applications."
        )
    if motor_type == "IPM":
        return (
            "IPM motors are excellent for modern high-performance EVs because embedded magnets improve field weakening and high-speed operation."
        )
    return "Selected motor type should be evaluated using torque, efficiency, cost, cooling, and control complexity."


def make_device_interpretation(device_type):
    if device_type == "Si IGBT":
        return (
            "Si IGBT is mature and low-cost for mainstream traction inverters, but switching losses are higher than SiC."
        )
    if device_type == "SiC MOSFET":
        return (
            "SiC MOSFET is attractive for high-efficiency EV inverters because it reduces switching loss, supports higher switching frequency, "
            "and can reduce cooling and passive-component stress."
        )
    if device_type == "GaN HEMT":
        return (
            "GaN is very fast and promising for OBC/DC-DC stages, but present voltage limits make it less common for high-voltage traction inverters."
        )
    return "Selected inverter device should be evaluated using voltage rating, current rating, switching frequency, efficiency, cost, and thermal limits."


def run_motor_inverter_lab():
    st.markdown("# Motor & Inverter Lab")
    st.caption("Analyze EV motor torque-speed behavior, tractive force, approximate efficiency map, and inverter losses.")

    st.info(
        "This module uses simplified engineering equations. Production motor and inverter design requires measured efficiency maps, "
        "thermal models, current limits, magnetic design data, switching-energy curves, gate-driver design, and EMC validation."
    )

    motor_df = load_motor_presets()
    inverter_df = load_inverter_devices()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "Motor Inputs",
            "Torque-Speed Analysis",
            "Inverter Losses",
            "Efficiency Map",
            "Technology Comparison"
        ]
    )

    with tab1:
        st.markdown("## Motor Selection")

        col1, col2, col3 = st.columns(3)

        with col1:
            selected_motor = st.selectbox(
                "Select motor type",
                options=motor_df["Motor_Type"].tolist(),
                index=0
            )

        selected_motor_row = motor_df[motor_df["Motor_Type"] == selected_motor].iloc[0]

        with col2:
            peak_torque_nm = st.number_input(
                "Peak motor torque (Nm)",
                min_value=1.0,
                max_value=2000.0,
                value=float(selected_motor_row["Default_Peak_Torque_Nm"]),
                step=5.0,
                format="%.1f"
            )

        with col3:
            peak_efficiency_percent = st.number_input(
                "Peak motor efficiency (%)",
                min_value=50.0,
                max_value=99.5,
                value=float(selected_motor_row["Peak_Efficiency_Percent"]),
                step=0.5,
                format="%.1f"
            )

        col4, col5, col6 = st.columns(3)

        with col4:
            base_speed_rpm = st.number_input(
                "Base speed (RPM)",
                min_value=100.0,
                max_value=30000.0,
                value=float(selected_motor_row["Default_Base_Speed_RPM"]),
                step=100.0,
                format="%.0f"
            )

        with col5:
            max_speed_rpm = st.number_input(
                "Maximum speed (RPM)",
                min_value=500.0,
                max_value=40000.0,
                value=float(selected_motor_row["Default_Max_Speed_RPM"]),
                step=100.0,
                format="%.0f"
            )

        with col6:
            gear_ratio = st.number_input(
                "Single-speed gear ratio",
                min_value=1.0,
                max_value=20.0,
                value=float(selected_motor_row["Default_Gear_Ratio"]),
                step=0.1,
                format="%.1f"
            )

        col7, col8 = st.columns(2)

        with col7:
            wheel_radius_m = st.number_input(
                "Wheel radius (m)",
                min_value=0.10,
                max_value=1.00,
                value=0.32,
                step=0.01,
                format="%.2f"
            )

        with col8:
            transmission_efficiency = st.slider(
                "Transmission efficiency",
                min_value=0.70,
                max_value=0.99,
                value=0.95,
                step=0.01
            )

        if max_speed_rpm <= base_speed_rpm:
            st.error("Maximum speed must be greater than base speed.")
            return

        df_motor, peak_power_kw = calculate_torque_speed_curve(
            peak_torque_nm=peak_torque_nm,
            base_speed_rpm=base_speed_rpm,
            max_speed_rpm=max_speed_rpm
        )

        df_vehicle = calculate_vehicle_tractive_curve(
            df_motor=df_motor,
            gear_ratio=gear_ratio,
            wheel_radius_m=wheel_radius_m,
            transmission_efficiency=transmission_efficiency
        )

        st.divider()

        m1, m2, m3, m4 = st.columns(4)

        with m1:
            st.metric("Estimated Peak Power", f"{peak_power_kw:.1f} kW")

        with m2:
            st.metric("Peak Torque", f"{peak_torque_nm:.1f} Nm")

        with m3:
            st.metric("Base Speed", f"{base_speed_rpm:.0f} RPM")

        with m4:
            estimated_top_speed = df_vehicle["Vehicle Speed km/h"].max()
            st.metric("Speed at Max Motor RPM", f"{estimated_top_speed:.1f} km/h")

        st.markdown("### Motor Interpretation")
        st.success(make_motor_interpretation(selected_motor))

    with tab2:
        st.markdown("## Torque-Speed and Vehicle Tractive Force")

        col_a, col_b = st.columns(2)

        with col_a:
            st.plotly_chart(
                create_torque_speed_plot(df_motor, base_speed_rpm),
                use_container_width=True
            )

        with col_b:
            st.plotly_chart(
                create_power_speed_plot(df_motor, base_speed_rpm),
                use_container_width=True
            )

        st.plotly_chart(
            create_tractive_force_plot(df_vehicle),
            use_container_width=True
        )

        st.markdown("### Torque-Speed Data")

        st.dataframe(
            df_motor.round(2),
            use_container_width=True,
            hide_index=True
        )

        st.markdown("### Engineering Notes")

        st.write(
            """
            Below base speed, the motor operates in the **constant-torque region**.  
            Above base speed, torque reduces as speed rises and the motor enters a **constant-power / field-weakening region**.  
            The gear ratio converts motor torque into wheel torque and determines the tradeoff between launch force and top speed.
            """
        )

    with tab3:
        st.markdown("## Inverter Loss Estimator")

        col1, col2, col3 = st.columns(3)

        with col1:
            selected_device = st.selectbox(
                "Select inverter device",
                options=inverter_df["Device_Type"].tolist(),
                index=1
            )

        selected_device_row = inverter_df[inverter_df["Device_Type"] == selected_device].iloc[0]

        with col2:
            vdc = st.number_input(
                "DC bus voltage (V)",
                min_value=24.0,
                max_value=1200.0,
                value=400.0,
                step=10.0,
                format="%.1f"
            )

        with col3:
            motor_output_power_kw = st.number_input(
                "Motor output power for loss point (kW)",
                min_value=0.1,
                max_value=500.0,
                value=min(float(peak_power_kw), 100.0),
                step=1.0,
                format="%.1f"
            )

        col4, col5, col6 = st.columns(3)

        with col4:
            irms = st.number_input(
                "Phase RMS current (A)",
                min_value=1.0,
                max_value=2000.0,
                value=150.0,
                step=5.0,
                format="%.1f"
            )

        with col5:
            iavg = st.number_input(
                "Average device current (A)",
                min_value=1.0,
                max_value=2000.0,
                value=100.0,
                step=5.0,
                format="%.1f"
            )

        with col6:
            fsw_khz = st.number_input(
                "Switching frequency (kHz)",
                min_value=1.0,
                max_value=500.0,
                value=float(selected_device_row["Typical_Switching_Min_kHz"]),
                step=1.0,
                format="%.1f"
            )

        col7, col8, col9 = st.columns(3)

        with col7:
            rds_mohm = st.number_input(
                "MOSFET/GaN Rds(on) (mΩ)",
                min_value=0.0,
                max_value=500.0,
                value=float(selected_device_row["Default_Rds_mOhm"]),
                step=0.5,
                format="%.2f"
            )

        with col8:
            vce_sat = st.number_input(
                "IGBT Vce(sat) (V)",
                min_value=0.0,
                max_value=10.0,
                value=float(selected_device_row["Default_Vce_sat_V"]),
                step=0.1,
                format="%.2f"
            )

        with col9:
            rce_mohm = st.number_input(
                "IGBT equivalent Rce (mΩ)",
                min_value=0.0,
                max_value=100.0,
                value=float(selected_device_row["Default_Rce_mOhm"]),
                step=0.5,
                format="%.2f"
            )

        col10, col11, col12 = st.columns(3)

        with col10:
            eon_mj = st.number_input(
                "Turn-on energy, Eon (mJ)",
                min_value=0.0,
                max_value=100.0,
                value=float(selected_device_row["Default_Eon_mJ"]),
                step=0.5,
                format="%.2f"
            )

        with col11:
            eoff_mj = st.number_input(
                "Turn-off energy, Eoff (mJ)",
                min_value=0.0,
                max_value=100.0,
                value=float(selected_device_row["Default_Eoff_mJ"]),
                step=0.5,
                format="%.2f"
            )

        with col12:
            diode_loss_w = st.number_input(
                "Diode / reverse recovery / misc loss (W)",
                min_value=0.0,
                max_value=5000.0,
                value=300.0 if selected_device == "Si IGBT" else 80.0,
                step=10.0,
                format="%.1f"
            )

        loss_result = calculate_inverter_losses(
            device_type=selected_device,
            motor_output_power_kw=motor_output_power_kw,
            vdc=vdc,
            irms=irms,
            iavg=iavg,
            fsw_khz=fsw_khz,
            rds_mohm=rds_mohm,
            vce_sat=vce_sat,
            rce_mohm=rce_mohm,
            eon_mj=eon_mj,
            eoff_mj=eoff_mj,
            diode_loss_w=diode_loss_w
        )

        st.divider()

        l1, l2, l3, l4 = st.columns(4)

        with l1:
            st.metric("Conduction Loss", f"{loss_result['Conduction Loss W']:.1f} W")

        with l2:
            st.metric("Switching Loss", f"{loss_result['Switching Loss W']:.1f} W")

        with l3:
            st.metric("Total Inverter Loss", f"{loss_result['Total Inverter Loss W']:.1f} W")

        with l4:
            st.metric("Inverter Efficiency", f"{loss_result['Inverter Efficiency Percent']:.2f}%")

        st.plotly_chart(
            create_loss_breakdown_chart(loss_result),
            use_container_width=True
        )

        st.markdown("### Inverter Interpretation")
        st.success(make_device_interpretation(selected_device))

        st.warning(
            "The loss model is simplified. Real inverter losses require manufacturer switching-energy curves, modulation index, power factor, junction temperature, gate resistance, dead time, and thermal impedance."
        )

    with tab4:
        st.markdown("## Approximate Motor Efficiency Map")

        st.plotly_chart(
            create_efficiency_map(
                peak_efficiency_percent=peak_efficiency_percent,
                max_speed_rpm=max_speed_rpm,
                peak_torque_nm=peak_torque_nm
            ),
            use_container_width=True
        )

        st.markdown("### Efficiency Map Interpretation")

        st.write(
            """
            The highest-efficiency region is normally around moderate speed and moderate torque.  
            Very low speed, very high torque, and very high speed can reduce efficiency due to copper loss, iron loss, and mechanical/windage effects.
            """
        )

    with tab5:
        st.markdown("## Motor Technology Comparison")

        st.dataframe(motor_df, use_container_width=True, hide_index=True)
        st.plotly_chart(create_motor_score_chart(motor_df), use_container_width=True)

        st.markdown("## Inverter Device Comparison")

        st.dataframe(inverter_df, use_container_width=True, hide_index=True)
        st.plotly_chart(create_device_comparison_chart(inverter_df), use_container_width=True)

        st.markdown("## Selection Guidance")

        st.write(
            """
            **PMSM/IPM** are best for high-efficiency passenger EVs.  
            **IM** is useful when ruggedness and magnet-free construction are important.  
            **BLDC** is practical for smaller and lower-cost EVs.  
            **Si IGBT** is mature and cost-effective.  
            **SiC MOSFET** is preferred when efficiency, switching frequency, and thermal performance are priorities.  
            **GaN** is promising for OBC and DC-DC applications, but traction-inverter use is limited by voltage and maturity.
            """
        )