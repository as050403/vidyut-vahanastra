import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go


VEHICLE_DATA_PATH = "data/vehicle_presets.csv"


@st.cache_data
def load_vehicle_presets():
    return pd.read_csv(VEHICLE_DATA_PATH)


def get_temperature_capacity_factor(temp_condition):
    """
    Approximate usable battery capacity derating.
    This is a simplified early-design assumption, not a cell-specific electrothermal model.
    """
    factors = {
        "Cold (<10°C)": 0.75,
        "Cool (10–20°C)": 0.90,
        "Optimal (20–35°C)": 1.00,
        "Hot (35–45°C)": 0.88,
        "Very Hot (>45°C)": 0.78
    }
    return factors.get(temp_condition, 1.0)


def get_driving_style_factor(style):
    """
    Multiplier applied to propulsion energy.
    """
    factors = {
        "Eco / Smooth": 0.90,
        "Normal": 1.00,
        "Urban Stop-Go with Regen": 0.95,
        "Highway Cruise": 1.05,
        "Aggressive": 1.25,
        "Monsoon / Wet Roads": 1.10
    }
    return factors.get(style, 1.0)


def calculate_road_load_range(
    usable_battery_kwh,
    mass_kg,
    payload_kg,
    speed_kmh,
    cd,
    frontal_area_m2,
    crr,
    drivetrain_efficiency,
    hvac_kw,
    auxiliary_kw,
    grade_percent,
    temperature_factor,
    driving_style_factor,
    regen_efficiency=0.65,
    air_density=1.225
):
    """
    Simplified steady-state EV energy model.

    Wh/km = battery-side power / speed

    Components:
    - Rolling resistance
    - Aerodynamic drag
    - Grade force
    - HVAC
    - Auxiliary load

    For downhill grade, a simplified regenerative recovery term is applied.
    """

    g = 9.81
    total_mass_kg = mass_kg + payload_kg
    speed_mps = speed_kmh / 3.6

    if speed_kmh <= 0 or drivetrain_efficiency <= 0:
        return None

    grade_angle = np.arctan(grade_percent / 100)

    force_roll = total_mass_kg * g * crr * np.cos(grade_angle)
    force_aero = 0.5 * air_density * cd * frontal_area_m2 * speed_mps ** 2
    force_grade = total_mass_kg * g * np.sin(grade_angle)

    p_roll_kw = (force_roll * speed_mps) / 1000 / drivetrain_efficiency
    p_aero_kw = (force_aero * speed_mps) / 1000 / drivetrain_efficiency

    raw_grade_power_kw = (force_grade * speed_mps) / 1000

    if raw_grade_power_kw >= 0:
        p_grade_kw = raw_grade_power_kw / drivetrain_efficiency
    else:
        # Downhill: negative power demand partially recovered by regen.
        p_grade_kw = raw_grade_power_kw * regen_efficiency

    propulsion_kw = (p_roll_kw + p_aero_kw + p_grade_kw) * driving_style_factor
    total_battery_power_kw = propulsion_kw + hvac_kw + auxiliary_kw

    # Avoid unrealistic negative consumption on steep downhill.
    total_battery_power_kw = max(total_battery_power_kw, 0.05)

    wh_per_km = total_battery_power_kw * 1000 / speed_kmh
    usable_energy_after_temp_kwh = usable_battery_kwh * temperature_factor
    estimated_range_km = usable_energy_after_temp_kwh * 1000 / wh_per_km

    breakdown = {
        "Rolling Resistance": p_roll_kw * driving_style_factor * 1000 / speed_kmh,
        "Aerodynamic Drag": p_aero_kw * driving_style_factor * 1000 / speed_kmh,
        "Grade / Recovery": p_grade_kw * driving_style_factor * 1000 / speed_kmh,
        "HVAC": hvac_kw * 1000 / speed_kmh,
        "Auxiliary Loads": auxiliary_kw * 1000 / speed_kmh
    }

    outputs = {
        "total_mass_kg": total_mass_kg,
        "force_roll_n": force_roll,
        "force_aero_n": force_aero,
        "force_grade_n": force_grade,
        "p_roll_kw": p_roll_kw,
        "p_aero_kw": p_aero_kw,
        "p_grade_kw": p_grade_kw,
        "total_battery_power_kw": total_battery_power_kw,
        "wh_per_km": wh_per_km,
        "usable_energy_after_temp_kwh": usable_energy_after_temp_kwh,
        "estimated_range_km": estimated_range_km,
        "breakdown_wh_per_km": breakdown
    }

    return outputs


def create_speed_sweep(
    usable_battery_kwh,
    mass_kg,
    payload_kg,
    cd,
    frontal_area_m2,
    crr,
    drivetrain_efficiency,
    hvac_kw,
    auxiliary_kw,
    grade_percent,
    temperature_factor,
    driving_style_factor
):
    speeds = np.arange(20, 141, 5)
    records = []

    for speed in speeds:
        result = calculate_road_load_range(
            usable_battery_kwh=usable_battery_kwh,
            mass_kg=mass_kg,
            payload_kg=payload_kg,
            speed_kmh=speed,
            cd=cd,
            frontal_area_m2=frontal_area_m2,
            crr=crr,
            drivetrain_efficiency=drivetrain_efficiency,
            hvac_kw=hvac_kw,
            auxiliary_kw=auxiliary_kw,
            grade_percent=grade_percent,
            temperature_factor=temperature_factor,
            driving_style_factor=driving_style_factor
        )

        records.append(
            {
                "Speed (km/h)": speed,
                "Wh/km": result["wh_per_km"],
                "Estimated Range (km)": result["estimated_range_km"],
                "Battery Power (kW)": result["total_battery_power_kw"]
            }
        )

    return pd.DataFrame(records)


def create_wh_per_km_plot(df_speed):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df_speed["Speed (km/h)"],
            y=df_speed["Wh/km"],
            mode="lines+markers",
            name="Wh/km"
        )
    )

    fig.update_layout(
        title="Energy Consumption vs Speed",
        xaxis_title="Speed (km/h)",
        yaxis_title="Energy Consumption (Wh/km)",
        height=430
    )

    return fig


def create_range_speed_plot(df_speed):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df_speed["Speed (km/h)"],
            y=df_speed["Estimated Range (km)"],
            mode="lines+markers",
            name="Estimated Range"
        )
    )

    fig.update_layout(
        title="Estimated Range vs Speed",
        xaxis_title="Speed (km/h)",
        yaxis_title="Range (km)",
        height=430
    )

    return fig


def create_power_speed_plot(df_speed):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df_speed["Speed (km/h)"],
            y=df_speed["Battery Power (kW)"],
            mode="lines+markers",
            name="Battery Power"
        )
    )

    fig.update_layout(
        title="Battery Power Demand vs Speed",
        xaxis_title="Speed (km/h)",
        yaxis_title="Battery Power (kW)",
        height=430
    )

    return fig


def create_breakdown_chart(breakdown):
    names = list(breakdown.keys())
    values = list(breakdown.values())

    fig = go.Figure(
        data=[
            go.Bar(
                x=names,
                y=values,
                text=[round(v, 1) for v in values],
                textposition="auto"
            )
        ]
    )

    fig.update_layout(
        title="Energy Consumption Breakdown",
        xaxis_title="Component",
        yaxis_title="Wh/km",
        height=430
    )

    return fig


def create_range_comparison_table(
    usable_battery_kwh,
    mass_kg,
    payload_kg,
    speed_kmh,
    cd,
    frontal_area_m2,
    crr,
    drivetrain_efficiency,
    hvac_kw,
    auxiliary_kw,
    grade_percent,
    driving_style_factor
):
    temp_conditions = [
        "Cold (<10°C)",
        "Cool (10–20°C)",
        "Optimal (20–35°C)",
        "Hot (35–45°C)",
        "Very Hot (>45°C)"
    ]

    records = []

    for temp in temp_conditions:
        temp_factor = get_temperature_capacity_factor(temp)

        result = calculate_road_load_range(
            usable_battery_kwh=usable_battery_kwh,
            mass_kg=mass_kg,
            payload_kg=payload_kg,
            speed_kmh=speed_kmh,
            cd=cd,
            frontal_area_m2=frontal_area_m2,
            crr=crr,
            drivetrain_efficiency=drivetrain_efficiency,
            hvac_kw=hvac_kw,
            auxiliary_kw=auxiliary_kw,
            grade_percent=grade_percent,
            temperature_factor=temp_factor,
            driving_style_factor=driving_style_factor
        )

        records.append(
            {
                "Temperature Condition": temp,
                "Usable Energy After Derating (kWh)": result["usable_energy_after_temp_kwh"],
                "Wh/km": result["wh_per_km"],
                "Estimated Range (km)": result["estimated_range_km"]
            }
        )

    return pd.DataFrame(records)


def interpret_range(wh_per_km, estimated_range_km, speed_kmh, hvac_kw, grade_percent):
    messages = []

    if wh_per_km < 80:
        messages.append("This is a very efficient configuration, typical of two-wheelers or very light EVs.")
    elif wh_per_km < 140:
        messages.append("This is an efficient passenger EV configuration.")
    elif wh_per_km < 190:
        messages.append("This is a normal compact car or compact SUV consumption range.")
    elif wh_per_km < 260:
        messages.append("This is a high-consumption SUV or heavy EV condition.")
    else:
        messages.append("This is a very high energy-consumption condition; check speed, mass, grade, HVAC, and drag.")

    if speed_kmh >= 100:
        messages.append("High speed is strongly increasing aerodynamic drag and reducing range.")

    if hvac_kw >= 3:
        messages.append("High HVAC load is significantly reducing available driving range.")

    if grade_percent > 3:
        messages.append("Road grade is increasing traction power demand; climbing routes can reduce range sharply.")

    if estimated_range_km < 100:
        messages.append("Estimated range is low; this configuration needs either more battery energy or lower consumption.")

    return messages


def run_range_lab():
    st.markdown("# Range Lab")
    st.caption("Estimate EV range using road-load physics, Wh/km, temperature derating, HVAC load, and Indian driving conditions.")

    st.info(
        "This is a simplified early-stage range model. Final validation should use real drive-cycle data, measured efficiency maps, "
        "battery test data, and vehicle-road testing."
    )

    vehicle_df = load_vehicle_presets()

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "Input & Main Results",
            "Energy Breakdown",
            "Speed Sweep",
            "Temperature Comparison"
        ]
    )

    with tab1:
        st.markdown("## Vehicle and Route Inputs")

        col1, col2, col3 = st.columns(3)

        with col1:
            selected_vehicle = st.selectbox(
                "Select vehicle preset",
                options=vehicle_df["Vehicle_Preset"].tolist(),
                index=2
            )

        selected_row = vehicle_df[vehicle_df["Vehicle_Preset"] == selected_vehicle].iloc[0]

        with col2:
            usable_battery_kwh = st.number_input(
                "Usable battery capacity (kWh)",
                min_value=1.0,
                max_value=300.0,
                value=float(selected_row["Usable_Battery_kWh"]),
                step=0.5,
                format="%.1f"
            )

        with col3:
            rated_range_km = st.number_input(
                "Optional rated / claimed range (km)",
                min_value=0.0,
                max_value=1000.0,
                value=0.0,
                step=5.0,
                format="%.1f"
            )

        col4, col5, col6 = st.columns(3)

        with col4:
            mass_kg = st.number_input(
                "Vehicle mass without payload (kg)",
                min_value=50.0,
                max_value=20000.0,
                value=float(selected_row["Mass_kg"]),
                step=10.0,
                format="%.1f"
            )

        with col5:
            payload_kg = st.number_input(
                "Payload / passengers / luggage (kg)",
                min_value=0.0,
                max_value=3000.0,
                value=150.0,
                step=10.0,
                format="%.1f"
            )

        with col6:
            speed_kmh = st.slider(
                "Average driving speed (km/h)",
                min_value=10,
                max_value=140,
                value=int(selected_row["Default_Speed_kmh"]),
                step=5
            )

        col7, col8, col9 = st.columns(3)

        with col7:
            cd = st.number_input(
                "Drag coefficient, Cd",
                min_value=0.10,
                max_value=1.50,
                value=float(selected_row["Cd"]),
                step=0.01,
                format="%.2f"
            )

        with col8:
            frontal_area_m2 = st.number_input(
                "Frontal area (m²)",
                min_value=0.20,
                max_value=12.00,
                value=float(selected_row["Frontal_Area_m2"]),
                step=0.05,
                format="%.2f"
            )

        with col9:
            crr = st.number_input(
                "Rolling resistance coefficient, Crr",
                min_value=0.004,
                max_value=0.030,
                value=float(selected_row["Crr"]),
                step=0.001,
                format="%.3f"
            )

        col10, col11, col12 = st.columns(3)

        with col10:
            drivetrain_efficiency = st.slider(
                "Drivetrain efficiency",
                min_value=0.60,
                max_value=0.98,
                value=float(selected_row["Drivetrain_Efficiency"]),
                step=0.01
            )

        with col11:
            hvac_kw = st.number_input(
                "HVAC load (kW)",
                min_value=0.0,
                max_value=10.0,
                value=float(selected_row["Default_HVAC_kW"]),
                step=0.1,
                format="%.1f"
            )

        with col12:
            auxiliary_kw = st.number_input(
                "Auxiliary electrical load (kW)",
                min_value=0.0,
                max_value=5.0,
                value=float(selected_row["Auxiliary_Load_kW"]),
                step=0.1,
                format="%.1f"
            )

        col13, col14 = st.columns(2)

        with col13:
            grade_percent = st.slider(
                "Average road grade (%)",
                min_value=-5.0,
                max_value=10.0,
                value=0.0,
                step=0.5
            )

        with col14:
            temp_condition = st.selectbox(
                "Battery temperature condition",
                [
                    "Cold (<10°C)",
                    "Cool (10–20°C)",
                    "Optimal (20–35°C)",
                    "Hot (35–45°C)",
                    "Very Hot (>45°C)"
                ],
                index=2
            )

        driving_style = st.selectbox(
            "Driving style / route condition",
            [
                "Eco / Smooth",
                "Normal",
                "Urban Stop-Go with Regen",
                "Highway Cruise",
                "Aggressive",
                "Monsoon / Wet Roads"
            ],
            index=1
        )

        temperature_factor = get_temperature_capacity_factor(temp_condition)
        driving_factor = get_driving_style_factor(driving_style)

        result = calculate_road_load_range(
            usable_battery_kwh=usable_battery_kwh,
            mass_kg=mass_kg,
            payload_kg=payload_kg,
            speed_kmh=speed_kmh,
            cd=cd,
            frontal_area_m2=frontal_area_m2,
            crr=crr,
            drivetrain_efficiency=drivetrain_efficiency,
            hvac_kw=hvac_kw,
            auxiliary_kw=auxiliary_kw,
            grade_percent=grade_percent,
            temperature_factor=temperature_factor,
            driving_style_factor=driving_factor
        )

        st.divider()

        st.markdown("## Main Range Outputs")

        m1, m2, m3, m4 = st.columns(4)

        with m1:
            st.metric("Estimated Range", f"{result['estimated_range_km']:.1f} km")
            st.caption("Usable energy / Wh per km")

        with m2:
            st.metric("Energy Consumption", f"{result['wh_per_km']:.1f} Wh/km")
            st.caption("Lower is better")

        with m3:
            st.metric("Battery Power Demand", f"{result['total_battery_power_kw']:.2f} kW")
            st.caption("At selected average speed")

        with m4:
            st.metric("Usable Energy After Temp", f"{result['usable_energy_after_temp_kwh']:.2f} kWh")
            st.caption(f"Temperature factor: {temperature_factor * 100:.0f}%")

        m5, m6, m7, m8 = st.columns(4)

        with m5:
            st.metric("Total Mass", f"{result['total_mass_kg']:.0f} kg")
            st.caption("Vehicle + payload")

        with m6:
            st.metric("Rolling Force", f"{result['force_roll_n']:.0f} N")

        with m7:
            st.metric("Aero Force", f"{result['force_aero_n']:.0f} N")

        with m8:
            st.metric("Grade Force", f"{result['force_grade_n']:.0f} N")

        if rated_range_km > 0:
            real_world_ratio = result["estimated_range_km"] / rated_range_km * 100
            st.metric(
                "Estimated Range vs Rated Range",
                f"{real_world_ratio:.1f}%",
                help="Compares calculated range against the optional rated/claimed range input."
            )

        st.markdown("## Interpretation")

        for msg in interpret_range(
            wh_per_km=result["wh_per_km"],
            estimated_range_km=result["estimated_range_km"],
            speed_kmh=speed_kmh,
            hvac_kw=hvac_kw,
            grade_percent=grade_percent
        ):
            st.write(f"- {msg}")

    with tab2:
        st.markdown("## Energy Consumption Breakdown")

        breakdown_fig = create_breakdown_chart(result["breakdown_wh_per_km"])
        st.plotly_chart(breakdown_fig, use_container_width=True)

        breakdown_df = pd.DataFrame(
            {
                "Component": list(result["breakdown_wh_per_km"].keys()),
                "Wh/km": list(result["breakdown_wh_per_km"].values())
            }
        )

        st.dataframe(breakdown_df.round(2), use_container_width=True, hide_index=True)

        st.markdown("### Engineering Notes")

        st.write(
            """
            Rolling resistance dominates at lower speeds and heavier vehicle mass.  
            Aerodynamic drag increases strongly with speed, so highway range falls faster than city range.  
            HVAC load becomes more damaging at low speeds because the vehicle spends more time per kilometre.  
            Uphill grade adds large energy demand, while downhill grade may recover some energy through regeneration.
            """
        )

    with tab3:
        st.markdown("## Speed Sweep Analysis")

        df_speed = create_speed_sweep(
            usable_battery_kwh=usable_battery_kwh,
            mass_kg=mass_kg,
            payload_kg=payload_kg,
            cd=cd,
            frontal_area_m2=frontal_area_m2,
            crr=crr,
            drivetrain_efficiency=drivetrain_efficiency,
            hvac_kw=hvac_kw,
            auxiliary_kw=auxiliary_kw,
            grade_percent=grade_percent,
            temperature_factor=temperature_factor,
            driving_style_factor=driving_factor
        )

        col_a, col_b = st.columns(2)

        with col_a:
            st.plotly_chart(create_wh_per_km_plot(df_speed), use_container_width=True)

        with col_b:
            st.plotly_chart(create_range_speed_plot(df_speed), use_container_width=True)

        st.plotly_chart(create_power_speed_plot(df_speed), use_container_width=True)

        st.markdown("### Speed Sweep Data")

        st.dataframe(df_speed.round(2), use_container_width=True, hide_index=True)

    with tab4:
        st.markdown("## Temperature Comparison")

        temp_df = create_range_comparison_table(
            usable_battery_kwh=usable_battery_kwh,
            mass_kg=mass_kg,
            payload_kg=payload_kg,
            speed_kmh=speed_kmh,
            cd=cd,
            frontal_area_m2=frontal_area_m2,
            crr=crr,
            drivetrain_efficiency=drivetrain_efficiency,
            hvac_kw=hvac_kw,
            auxiliary_kw=auxiliary_kw,
            grade_percent=grade_percent,
            driving_style_factor=driving_factor
        )

        st.dataframe(temp_df.round(2), use_container_width=True, hide_index=True)

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=temp_df["Temperature Condition"],
                y=temp_df["Estimated Range (km)"],
                text=temp_df["Estimated Range (km)"].round(1),
                textposition="auto",
                name="Estimated Range"
            )
        )

        fig.update_layout(
            title="Range Impact of Battery Temperature",
            xaxis_title="Temperature Condition",
            yaxis_title="Estimated Range (km)",
            height=430
        )

        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Temperature Interpretation")

        st.write(
            """
            Cold temperatures reduce usable battery capacity and increase internal resistance.  
            Hot temperatures increase cooling demand and can trigger BMS derating.  
            For Indian EVs, high ambient temperature and air-conditioning load are especially important range factors.
            """
        )