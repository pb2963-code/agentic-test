"""
Health Monitoring Platform - Streamlit Dashboard

A comprehensive multi-agent health monitoring dashboard for patients.
"""

import streamlit as st
import asyncio
from datetime import datetime, date, time, timedelta
from typing import Any
import random

# Configure page
st.set_page_config(
    page_title="Health Monitoring Platform",
    page_icon="❤️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #4f46e5;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 1rem;
        color: white;
        text-align: center;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
    }
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    .alert-critical {
        background-color: #fee2e2;
        border-left: 4px solid #ef4444;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .alert-warning {
        background-color: #fef3c7;
        border-left: 4px solid #f59e0b;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .alert-info {
        background-color: #dbeafe;
        border-left: 4px solid #3b82f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .recommendation-card {
        background-color: #f0fdf4;
        border-left: 4px solid #22c55e;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 0 20px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'patient_data' not in st.session_state:
    st.session_state.patient_data = {
        'patient_id': 'demo-patient-001',
        'first_name': 'John',
        'last_name': 'Doe',
        'age': 45,
        'email': 'john.doe@example.com',
    }

if 'vitals_history' not in st.session_state:
    # Generate demo vital history
    st.session_state.vitals_history = []
    now = datetime.now()
    for i in range(48):
        timestamp = now - timedelta(hours=i)
        st.session_state.vitals_history.append({
            'timestamp': timestamp,
            'heart_rate': random.randint(65, 85),
            'blood_pressure_systolic': random.randint(115, 130),
            'blood_pressure_diastolic': random.randint(70, 85),
            'temperature': round(random.uniform(36.2, 37.0), 1),
            'oxygen_saturation': random.randint(96, 99),
            'respiratory_rate': random.randint(14, 18),
        })

if 'medications' not in st.session_state:
    st.session_state.medications = [
        {'name': 'Lisinopril', 'dosage': '10mg', 'frequency': 'Once daily', 'time': '08:00', 'adherence': 92},
        {'name': 'Metformin', 'dosage': '500mg', 'frequency': 'Twice daily', 'time': '08:00, 20:00', 'adherence': 88},
        {'name': 'Aspirin', 'dosage': '81mg', 'frequency': 'Once daily', 'time': '08:00', 'adherence': 95},
    ]

if 'symptoms' not in st.session_state:
    st.session_state.symptoms = [
        {'name': 'Mild headache', 'severity': 'Mild', 'reported': datetime.now() - timedelta(hours=3), 'resolved': False},
    ]

if 'alerts' not in st.session_state:
    st.session_state.alerts = []

if 'wellness_data' not in st.session_state:
    st.session_state.wellness_data = {
        'steps_today': 7823,
        'steps_goal': 10000,
        'sleep_hours': 7.2,
        'sleep_quality': 'Good',
        'calories_burned': 320,
        'water_ml': 1800,
        'mood': 'Good',
        'stress_level': 4,
    }


def get_wellness_score():
    """Calculate overall wellness score."""
    score = 75
    wellness = st.session_state.wellness_data

    # Steps contribution
    step_ratio = min(wellness['steps_today'] / wellness['steps_goal'], 1)
    score += step_ratio * 10

    # Sleep contribution
    if wellness['sleep_hours'] >= 7:
        score += 10
    elif wellness['sleep_hours'] >= 6:
        score += 5

    # Active symptoms deduction
    active_symptoms = [s for s in st.session_state.symptoms if not s['resolved']]
    score -= len(active_symptoms) * 5

    # Alerts deduction
    score -= len(st.session_state.alerts) * 3

    return min(100, max(0, int(score)))


def get_risk_level():
    """Determine current risk level."""
    active_symptoms = [s for s in st.session_state.symptoms if not s['resolved']]
    critical_alerts = [a for a in st.session_state.alerts if a.get('severity', 0) >= 4]

    if critical_alerts:
        return 'Critical', '#ef4444'
    elif len(active_symptoms) > 2 or st.session_state.alerts:
        return 'Moderate', '#f59e0b'
    else:
        return 'Low', '#22c55e'


# Sidebar
with st.sidebar:
    st.markdown("## ❤️ HealthMonitor")
    st.markdown("---")

    # Patient info
    st.markdown(f"### 👤 {st.session_state.patient_data['first_name']} {st.session_state.patient_data['last_name']}")
    st.markdown(f"Age: {st.session_state.patient_data['age']} years")
    st.markdown(f"ID: `{st.session_state.patient_data['patient_id']}`")

    st.markdown("---")

    # Quick stats
    wellness_score = get_wellness_score()
    risk_level, risk_color = get_risk_level()

    st.metric("Wellness Score", f"{wellness_score}/100")
    st.markdown(f"**Risk Level:** <span style='color:{risk_color}'>{risk_level}</span>", unsafe_allow_html=True)

    st.markdown("---")

    # Emergency button
    if st.button("🚨 Emergency", type="primary", use_container_width=True):
        st.session_state.alerts.append({
            'title': 'Emergency Triggered',
            'message': 'Emergency response initiated. Help is on the way.',
            'severity': 5,
            'time': datetime.now(),
        })
        st.warning("Emergency services have been notified!")


# Main content
st.markdown('<h1 class="main-header">Health Monitoring Dashboard</h1>', unsafe_allow_html=True)
st.markdown(f"Welcome back, **{st.session_state.patient_data['first_name']}**! Here's your health overview.")

# Tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Dashboard", "💓 Vitals", "💊 Medications", "🤒 Symptoms", "🏃 Wellness", "⚠️ Alerts"
])

# Dashboard Tab
with tab1:
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Wellness Score",
            value=f"{get_wellness_score()}%",
            delta="2% from yesterday"
        )

    with col2:
        risk_level, _ = get_risk_level()
        st.metric(
            label="Risk Level",
            value=risk_level
        )

    with col3:
        active_symptoms = len([s for s in st.session_state.symptoms if not s['resolved']])
        st.metric(
            label="Active Symptoms",
            value=active_symptoms
        )

    with col4:
        st.metric(
            label="Active Alerts",
            value=len(st.session_state.alerts)
        )

    st.markdown("---")

    # Two columns layout
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("### 💓 Current Vitals")

        if st.session_state.vitals_history:
            latest = st.session_state.vitals_history[0]

            vital_col1, vital_col2, vital_col3 = st.columns(3)

            with vital_col1:
                st.metric("Heart Rate", f"{latest['heart_rate']} bpm")
                st.metric("Temperature", f"{latest['temperature']}°C")

            with vital_col2:
                st.metric("Blood Pressure", f"{latest['blood_pressure_systolic']}/{latest['blood_pressure_diastolic']}")
                st.metric("Respiratory Rate", f"{latest['respiratory_rate']} /min")

            with vital_col3:
                st.metric("O₂ Saturation", f"{latest['oxygen_saturation']}%")

    with col_right:
        st.markdown("### 💡 Recommendations")

        recommendations = [
            ("🚶 Activity", "You're at 78% of your daily step goal. A short walk could help!"),
            ("💧 Hydration", "Consider drinking more water today - you're at 72% of your goal."),
            ("😴 Sleep", "Good sleep quality last night! Keep maintaining your sleep schedule."),
        ]

        for title, rec in recommendations:
            st.markdown(f"""
            <div class="recommendation-card">
                <strong>{title}</strong><br>
                <span style="color: #666">{rec}</span>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # Vital trends chart
    st.markdown("### 📈 Heart Rate Trend (Last 24 Hours)")

    import pandas as pd

    chart_data = pd.DataFrame([
        {'Time': v['timestamp'], 'Heart Rate': v['heart_rate']}
        for v in st.session_state.vitals_history[:24]
    ])

    st.line_chart(chart_data.set_index('Time')['Heart Rate'])


# Vitals Tab
with tab2:
    st.markdown("### 💓 Vital Signs Monitoring")

    # Record new vital
    with st.expander("➕ Record New Vital", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            vital_type = st.selectbox(
                "Vital Type",
                ["Heart Rate", "Blood Pressure", "Temperature", "Oxygen Saturation", "Respiratory Rate"]
            )

        with col2:
            if vital_type == "Blood Pressure":
                systolic = st.number_input("Systolic (mmHg)", min_value=60, max_value=250, value=120)
                diastolic = st.number_input("Diastolic (mmHg)", min_value=40, max_value=150, value=80)
            else:
                vital_value = st.number_input(
                    "Value",
                    min_value=0.0,
                    max_value=500.0,
                    value=72.0 if vital_type == "Heart Rate" else 36.5
                )

        if st.button("Record Vital", type="primary"):
            new_vital = {
                'timestamp': datetime.now(),
                'heart_rate': st.session_state.vitals_history[0]['heart_rate'],
                'blood_pressure_systolic': st.session_state.vitals_history[0]['blood_pressure_systolic'],
                'blood_pressure_diastolic': st.session_state.vitals_history[0]['blood_pressure_diastolic'],
                'temperature': st.session_state.vitals_history[0]['temperature'],
                'oxygen_saturation': st.session_state.vitals_history[0]['oxygen_saturation'],
                'respiratory_rate': st.session_state.vitals_history[0]['respiratory_rate'],
            }

            if vital_type == "Heart Rate":
                new_vital['heart_rate'] = int(vital_value)
            elif vital_type == "Blood Pressure":
                new_vital['blood_pressure_systolic'] = systolic
                new_vital['blood_pressure_diastolic'] = diastolic
            elif vital_type == "Temperature":
                new_vital['temperature'] = vital_value
            elif vital_type == "Oxygen Saturation":
                new_vital['oxygen_saturation'] = int(vital_value)
            elif vital_type == "Respiratory Rate":
                new_vital['respiratory_rate'] = int(vital_value)

            st.session_state.vitals_history.insert(0, new_vital)
            st.success("✅ Vital recorded successfully!")
            st.rerun()

    st.markdown("---")

    # Current vitals display
    st.markdown("### Current Readings")

    if st.session_state.vitals_history:
        latest = st.session_state.vitals_history[0]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("""
            <div style="background: #fef2f2; padding: 1.5rem; border-radius: 1rem; text-align: center;">
                <div style="font-size: 2.5rem; font-weight: bold; color: #ef4444;">❤️ {}</div>
                <div style="color: #666;">Heart Rate (bpm)</div>
            </div>
            """.format(latest['heart_rate']), unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            st.markdown("""
            <div style="background: #fef3c7; padding: 1.5rem; border-radius: 1rem; text-align: center;">
                <div style="font-size: 2.5rem; font-weight: bold; color: #f59e0b;">🌡️ {}</div>
                <div style="color: #666;">Temperature (°C)</div>
            </div>
            """.format(latest['temperature']), unsafe_allow_html=True)

        with col2:
            st.markdown("""
            <div style="background: #dbeafe; padding: 1.5rem; border-radius: 1rem; text-align: center;">
                <div style="font-size: 2.5rem; font-weight: bold; color: #3b82f6;">🩸 {}/{}</div>
                <div style="color: #666;">Blood Pressure (mmHg)</div>
            </div>
            """.format(latest['blood_pressure_systolic'], latest['blood_pressure_diastolic']), unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            st.markdown("""
            <div style="background: #dcfce7; padding: 1.5rem; border-radius: 1rem; text-align: center;">
                <div style="font-size: 2.5rem; font-weight: bold; color: #22c55e;">💨 {}</div>
                <div style="color: #666;">Respiratory Rate (/min)</div>
            </div>
            """.format(latest['respiratory_rate']), unsafe_allow_html=True)

        with col3:
            st.markdown("""
            <div style="background: #f0fdf4; padding: 1.5rem; border-radius: 1rem; text-align: center;">
                <div style="font-size: 2.5rem; font-weight: bold; color: #22c55e;">🫁 {}%</div>
                <div style="color: #666;">Oxygen Saturation</div>
            </div>
            """.format(latest['oxygen_saturation']), unsafe_allow_html=True)

    st.markdown("---")

    # Vitals history table
    st.markdown("### 📋 Recent Readings")

    history_df = pd.DataFrame([
        {
            'Time': v['timestamp'].strftime('%Y-%m-%d %H:%M'),
            'HR': v['heart_rate'],
            'BP': f"{v['blood_pressure_systolic']}/{v['blood_pressure_diastolic']}",
            'Temp': v['temperature'],
            'SpO2': f"{v['oxygen_saturation']}%",
            'RR': v['respiratory_rate'],
        }
        for v in st.session_state.vitals_history[:10]
    ])

    st.dataframe(history_df, use_container_width=True, hide_index=True)


# Medications Tab
with tab3:
    st.markdown("### 💊 Medication Management")

    # Add new medication
    with st.expander("➕ Add New Medication", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            med_name = st.text_input("Medication Name")
            med_dosage = st.text_input("Dosage (e.g., 10mg)")

        with col2:
            med_frequency = st.selectbox("Frequency", ["Once daily", "Twice daily", "Three times daily", "As needed"])
            med_time = st.time_input("Scheduled Time", value=time(8, 0))

        if st.button("Add Medication", type="primary"):
            if med_name and med_dosage:
                st.session_state.medications.append({
                    'name': med_name,
                    'dosage': med_dosage,
                    'frequency': med_frequency,
                    'time': med_time.strftime('%H:%M'),
                    'adherence': 100,
                })
                st.success(f"✅ {med_name} added to your medications!")
                st.rerun()
            else:
                st.error("Please fill in all fields")

    st.markdown("---")

    # Adherence overview
    col1, col2 = st.columns([1, 2])

    with col1:
        avg_adherence = sum(m['adherence'] for m in st.session_state.medications) / len(st.session_state.medications) if st.session_state.medications else 0

        st.markdown(f"""
        <div style="background: {'#dcfce7' if avg_adherence >= 80 else '#fef3c7' if avg_adherence >= 60 else '#fee2e2'};
                    padding: 2rem; border-radius: 1rem; text-align: center;">
            <div style="font-size: 3rem; font-weight: bold; color: {'#22c55e' if avg_adherence >= 80 else '#f59e0b' if avg_adherence >= 60 else '#ef4444'};">
                {avg_adherence:.0f}%
            </div>
            <div style="color: #666; font-size: 1.1rem;">Overall Adherence</div>
            <div style="color: #999; font-size: 0.9rem;">Last 30 days</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("### 📅 Today's Schedule")

        for med in st.session_state.medications:
            col_a, col_b, col_c = st.columns([3, 1, 1])

            with col_a:
                st.markdown(f"**{med['name']}** - {med['dosage']}")
                st.caption(f"⏰ {med['time']} • {med['frequency']}")

            with col_b:
                st.progress(med['adherence'] / 100)

            with col_c:
                if st.button("✓ Taken", key=f"take_{med['name']}"):
                    st.success(f"Recorded: {med['name']}")

    st.markdown("---")

    # Medication list
    st.markdown("### 📋 All Medications")

    for med in st.session_state.medications:
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

            with col1:
                st.markdown(f"**{med['name']}**")
            with col2:
                st.write(med['dosage'])
            with col3:
                st.write(med['frequency'])
            with col4:
                adherence_color = "🟢" if med['adherence'] >= 80 else "🟡" if med['adherence'] >= 60 else "🔴"
                st.write(f"{adherence_color} {med['adherence']}%")


# Symptoms Tab
with tab4:
    st.markdown("### 🤒 Symptom Tracking")

    # Report new symptom
    with st.expander("➕ Report New Symptom", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            symptom_name = st.selectbox(
                "Symptom",
                ["Headache", "Fatigue", "Nausea", "Dizziness", "Chest Pain", "Shortness of Breath",
                 "Fever", "Cough", "Back Pain", "Joint Pain", "Other"]
            )
            if symptom_name == "Other":
                symptom_name = st.text_input("Describe symptom")

        with col2:
            severity = st.select_slider(
                "Severity",
                options=["Mild", "Moderate", "Severe", "Critical"]
            )
            description = st.text_area("Additional details (optional)")

        if st.button("Report Symptom", type="primary"):
            if symptom_name:
                st.session_state.symptoms.append({
                    'name': symptom_name,
                    'severity': severity,
                    'description': description,
                    'reported': datetime.now(),
                    'resolved': False,
                })

                # Auto-generate alert for severe symptoms
                if severity in ["Severe", "Critical"]:
                    st.session_state.alerts.append({
                        'title': f'Symptom Alert: {symptom_name}',
                        'message': f'{severity} {symptom_name} reported. Consider seeking medical attention.',
                        'severity': 4 if severity == "Critical" else 3,
                        'time': datetime.now(),
                    })

                st.success(f"✅ Symptom reported: {symptom_name}")
                st.rerun()

    st.markdown("---")

    # Risk assessment
    active_symptoms = [s for s in st.session_state.symptoms if not s['resolved']]

    col1, col2 = st.columns([1, 2])

    with col1:
        if not active_symptoms:
            risk = "Low"
            color = "#22c55e"
        elif any(s['severity'] in ['Critical', 'Severe'] for s in active_symptoms):
            risk = "High"
            color = "#ef4444"
        else:
            risk = "Moderate"
            color = "#f59e0b"

        st.markdown(f"""
        <div style="background: white; padding: 2rem; border-radius: 1rem; text-align: center; border: 2px solid {color};">
            <div style="font-size: 1.5rem; font-weight: bold; color: {color};">
                {risk} Risk
            </div>
            <div style="color: #666; margin-top: 0.5rem;">
                {len(active_symptoms)} active symptom(s)
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("### Active Symptoms")

        if active_symptoms:
            for symptom in active_symptoms:
                severity_color = {
                    'Mild': '#22c55e',
                    'Moderate': '#f59e0b',
                    'Severe': '#ef4444',
                    'Critical': '#dc2626',
                }.get(symptom['severity'], '#666')

                col_a, col_b, col_c = st.columns([3, 1, 1])

                with col_a:
                    st.markdown(f"**{symptom['name']}**")
                    st.caption(f"Reported: {symptom['reported'].strftime('%Y-%m-%d %H:%M')}")

                with col_b:
                    st.markdown(f"<span style='color:{severity_color}; font-weight: bold;'>{symptom['severity']}</span>",
                              unsafe_allow_html=True)

                with col_c:
                    if st.button("Resolve", key=f"resolve_{symptom['name']}_{symptom['reported']}"):
                        symptom['resolved'] = True
                        st.rerun()
        else:
            st.info("No active symptoms. You're doing great!")


# Wellness Tab
with tab5:
    st.markdown("### 🏃 Wellness Tracking")

    wellness = st.session_state.wellness_data

    # Daily stats
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        step_pct = min(100, int(wellness['steps_today'] / wellness['steps_goal'] * 100))
        st.metric("Steps Today", f"{wellness['steps_today']:,}", f"{step_pct}% of goal")
        st.progress(step_pct / 100)

    with col2:
        st.metric("Sleep", f"{wellness['sleep_hours']} hrs", wellness['sleep_quality'])

    with col3:
        st.metric("Calories Burned", wellness['calories_burned'])

    with col4:
        water_pct = int(wellness['water_ml'] / 2500 * 100)
        st.metric("Water", f"{wellness['water_ml']} ml", f"{water_pct}% of goal")

    st.markdown("---")

    # Log wellness activities
    st.markdown("### 📝 Log Activity")

    log_tab1, log_tab2, log_tab3, log_tab4 = st.tabs(["🚶 Steps", "😴 Sleep", "🏋️ Exercise", "😊 Mood"])

    with log_tab1:
        steps = st.number_input("Steps", min_value=0, max_value=100000, value=1000)
        if st.button("Add Steps", type="primary"):
            st.session_state.wellness_data['steps_today'] += steps
            st.success(f"✅ Added {steps} steps!")
            st.rerun()

    with log_tab2:
        col1, col2 = st.columns(2)
        with col1:
            sleep_hours = st.number_input("Hours slept", min_value=0.0, max_value=24.0, value=7.0, step=0.5)
        with col2:
            sleep_quality = st.select_slider("Quality", options=["Poor", "Fair", "Good", "Excellent"])

        if st.button("Log Sleep", type="primary"):
            st.session_state.wellness_data['sleep_hours'] = sleep_hours
            st.session_state.wellness_data['sleep_quality'] = sleep_quality
            st.success("✅ Sleep logged!")
            st.rerun()

    with log_tab3:
        col1, col2 = st.columns(2)
        with col1:
            activity = st.selectbox("Activity", ["Walking", "Running", "Cycling", "Swimming", "Strength", "Yoga"])
        with col2:
            duration = st.number_input("Duration (minutes)", min_value=1, max_value=300, value=30)

        if st.button("Log Exercise", type="primary"):
            calories = duration * 7  # Rough estimate
            st.session_state.wellness_data['calories_burned'] += calories
            st.success(f"✅ Logged {duration} min of {activity} (~{calories} calories)")
            st.rerun()

    with log_tab4:
        col1, col2 = st.columns(2)
        with col1:
            mood = st.select_slider("Mood", options=["😢 Very Low", "😕 Low", "😐 Neutral", "🙂 Good", "😄 Excellent"])
        with col2:
            stress = st.slider("Stress Level", 1, 10, 5)

        if st.button("Log Mood", type="primary"):
            st.session_state.wellness_data['mood'] = mood.split()[-1]
            st.session_state.wellness_data['stress_level'] = stress
            st.success("✅ Mood logged!")
            st.rerun()

    st.markdown("---")

    # Weekly summary
    st.markdown("### 📊 This Week")

    chart_data = pd.DataFrame({
        'Day': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        'Steps': [8500, 7200, 9100, 6800, 7823, 0, 0],
        'Goal': [10000] * 7,
    })

    st.bar_chart(chart_data.set_index('Day'))


# Alerts Tab
with tab6:
    st.markdown("### ⚠️ Health Alerts")

    # Alert stats
    col1, col2, col3 = st.columns(3)

    critical_alerts = [a for a in st.session_state.alerts if a.get('severity', 0) >= 4]
    warning_alerts = [a for a in st.session_state.alerts if 2 <= a.get('severity', 0) < 4]

    with col1:
        st.metric("Critical", len(critical_alerts))
    with col2:
        st.metric("Warnings", len(warning_alerts))
    with col3:
        st.metric("Total Active", len(st.session_state.alerts))

    st.markdown("---")

    # Display alerts
    if st.session_state.alerts:
        for i, alert in enumerate(st.session_state.alerts):
            severity = alert.get('severity', 1)

            if severity >= 4:
                alert_class = "alert-critical"
                icon = "🚨"
            elif severity >= 2:
                alert_class = "alert-warning"
                icon = "⚠️"
            else:
                alert_class = "alert-info"
                icon = "ℹ️"

            col1, col2 = st.columns([5, 1])

            with col1:
                st.markdown(f"""
                <div class="{alert_class}">
                    <strong>{icon} {alert['title']}</strong><br>
                    <span style="color: #666;">{alert['message']}</span><br>
                    <small style="color: #999;">{alert['time'].strftime('%Y-%m-%d %H:%M')}</small>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                if st.button("Dismiss", key=f"dismiss_{i}"):
                    st.session_state.alerts.pop(i)
                    st.rerun()
    else:
        st.success("✅ No active alerts. All clear!")

    st.markdown("---")

    # Test alert button
    if st.button("🔔 Generate Test Alert"):
        st.session_state.alerts.append({
            'title': 'Test Alert',
            'message': 'This is a test alert to demonstrate the alerting system.',
            'severity': 2,
            'time': datetime.now(),
        })
        st.rerun()


# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #999; padding: 1rem;">
    <small>Health Monitoring Platform v1.0 | Multi-Agent System |
    Powered by VitalSignsAgent, MedicationAgent, SymptomAnalysisAgent, WellnessAgent, AlertAgent & CoordinatorAgent</small>
</div>
""", unsafe_allow_html=True)
