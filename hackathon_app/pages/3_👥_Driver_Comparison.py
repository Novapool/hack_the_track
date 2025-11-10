"""
Driver Comparison Page

Compare two drivers' tire management efficiency and driving styles.
"""

import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils.data_loader import get_all_vehicles, get_vehicle_stats
from utils.model_predictor import calculate_efficiency_score
from utils.track_plotter import create_radar_chart, create_comparison_table


st.set_page_config(page_title="Driver Comparison", page_icon="👥", layout="wide")

# Title
st.title("👥 Driver Comparison")
st.markdown("Compare tire management efficiency between two drivers")

st.markdown("---")

# Load all vehicles
try:
    with st.spinner("Loading vehicle data..."):
        vehicles_df = get_all_vehicles()

    if vehicles_df.empty:
        st.error("No vehicle data available")
        st.stop()

except Exception as e:
    st.error(f"Error loading vehicles: {e}")
    st.stop()

# Sidebar - Driver Selection
with st.sidebar:
    st.header("🎛️ Select Drivers")

    # Create vehicle options
    vehicle_options = []
    for _, vehicle in vehicles_df.iterrows():
        label = f"Car #{vehicle['car_number']} ({vehicle['total_laps']} laps)"
        vehicle_options.append((label, vehicle['vehicle_id']))

    # Driver 1 selector
    driver1_label = st.selectbox(
        "Driver 1",
        options=[label for label, _ in vehicle_options],
        index=0
    )
    driver1_id = next(vid for label, vid in vehicle_options if label == driver1_label)

    # Driver 2 selector
    driver2_label = st.selectbox(
        "Driver 2",
        options=[label for label, _ in vehicle_options],
        index=min(1, len(vehicle_options) - 1)
    )
    driver2_id = next(vid for label, vid in vehicle_options if label == driver2_label)

    if driver1_id == driver2_id:
        st.warning("⚠️ Select different drivers for comparison")

    st.markdown("---")
    st.info("""
    **Efficiency Score:**
    Higher score = better tire management
    (faster lap times with less tire wear)
    """)

# Load driver stats
try:
    with st.spinner("Analyzing drivers..."):
        driver1_stats = get_vehicle_stats(driver1_id)
        driver2_stats = get_vehicle_stats(driver2_id)

    if not driver1_stats or not driver2_stats:
        st.error("Could not load driver statistics")
        st.stop()

    # Verify essential fields exist
    required_fields = ['avg_lap_time', 'car_number']
    for field in required_fields:
        if field not in driver1_stats or driver1_stats[field] is None:
            st.error(f"Driver 1 missing required data: {field}")
            st.stop()
        if field not in driver2_stats or driver2_stats[field] is None:
            st.error(f"Driver 2 missing required data: {field}")
            st.stop()

except Exception as e:
    st.error(f"Error loading driver stats: {e}")
    st.stop()

# Main comparison
st.header("📊 Performance Comparison")

# Key metrics comparison
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label=f"🏎️ Driver 1 (Car #{driver1_stats['car_number']})",
        value=f"{driver1_stats['avg_lap_time']:.2f}s",
        help="Average lap time"
    )

with col2:
    st.metric(
        label=f"🏎️ Driver 2 (Car #{driver2_stats['car_number']})",
        value=f"{driver2_stats['avg_lap_time']:.2f}s",
        help="Average lap time"
    )

with col3:
    time_delta = driver2_stats['avg_lap_time'] - driver1_stats['avg_lap_time']
    if time_delta < 0:
        winner = f"Driver 2 faster by {abs(time_delta):.3f}s"
    elif time_delta > 0:
        winner = f"Driver 1 faster by {abs(time_delta):.3f}s"
    else:
        winner = "Equal pace"

    st.metric(
        label="⏱️ Pace Comparison",
        value=winner
    )

st.markdown("---")

# Aggression profile radar chart
st.header("🎯 Driving Style Profile")

try:
    # Prepare data for radar chart
    # Normalize values for visualization
    driver1_radar = {
        'avg_brake_front': driver1_stats.get('avg_brake_front', 0),
        'max_lateral_g': driver1_stats.get('max_lateral_g', 0),
        'avg_speed': driver1_stats.get('avg_speed', 0),
        'max_speed': driver1_stats.get('max_speed', 0),
        'steering_variance': driver1_stats.get('steering_variance', 0),
        'car_number': driver1_stats['car_number']
    }

    driver2_radar = {
        'avg_brake_front': driver2_stats.get('avg_brake_front', 0),
        'max_lateral_g': driver2_stats.get('max_lateral_g', 0),
        'avg_speed': driver2_stats.get('avg_speed', 0),
        'max_speed': driver2_stats.get('max_speed', 0),
        'steering_variance': driver2_stats.get('steering_variance', 0),
        'car_number': driver2_stats['car_number']
    }

    labels = [
        'Brake Pressure',
        'Lateral G',
        'Avg Speed',
        'Max Speed',
        'Steering Variance'
    ]

    # Remove car_number for radar values
    radar1_values = {k: v for k, v in driver1_radar.items() if k != 'car_number'}
    radar2_values = {k: v for k, v in driver2_radar.items() if k != 'car_number'}

    radar_fig = create_radar_chart(
        driver1_radar,
        driver2_radar,
        labels
    )

    st.plotly_chart(radar_fig, width='stretch')

except Exception as e:
    st.warning(f"Could not create radar chart: {e}")

st.markdown("---")

# Detailed comparison table
st.header("📋 Detailed Statistics")

try:
    comparison_df = create_comparison_table(driver1_stats, driver2_stats)
    st.dataframe(comparison_df, width='stretch', hide_index=True)

except Exception as e:
    st.warning(f"Could not create comparison table: {e}")

st.markdown("---")

# Efficiency analysis
st.header("⚡ Tire Management Efficiency")

try:
    # Calculate efficiency scores (using dummy degradation for now)
    # In production, would calculate from actual lap degradation data
    avg_degradation_driver1 = 0.4  # Placeholder
    avg_degradation_driver2 = 0.45  # Placeholder

    efficiency1 = calculate_efficiency_score(
        driver1_stats['avg_lap_time'],
        avg_degradation_driver1
    )

    efficiency2 = calculate_efficiency_score(
        driver2_stats['avg_lap_time'],
        avg_degradation_driver2
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label=f"Driver 1 Efficiency",
            value=f"{efficiency1:.2f}",
            help="Higher = better tire management"
        )

    with col2:
        st.metric(
            label=f"Driver 2 Efficiency",
            value=f"{efficiency2:.2f}",
            help="Higher = better tire management"
        )

    with col3:
        efficiency_delta = ((efficiency2 - efficiency1) / efficiency1 * 100) if efficiency1 != 0 else 0
        st.metric(
            label="Efficiency Difference",
            value=f"{efficiency_delta:+.1f}%",
            delta=f"Driver {'2' if efficiency2 > efficiency1 else '1'} more efficient"
        )

except Exception as e:
    st.warning(f"Could not calculate efficiency: {e}")

st.markdown("---")

# Insights
st.header("💡 Insights & Recommendations")

insights_col1, insights_col2 = st.columns(2)

with insights_col1:
    st.subheader("🏎️ Driver 1 Profile")

    # Analyze driver 1
    if driver1_stats.get('max_brake_front', 0) > 80:
        st.markdown("- 🛑 **Aggressive braking** - High brake pressure")
    else:
        st.markdown("- ✅ **Smooth braking** - Moderate brake pressure")

    if driver1_stats.get('max_lateral_g', 0) > 1.5:
        st.markdown("- 🔥 **Aggressive cornering** - High lateral G-forces")
    else:
        st.markdown("- ✅ **Conservative cornering** - Moderate G-forces")

    if driver1_stats.get('steering_variance', 0) > 30:
        st.markdown("- ⚡ **Abrupt steering** - High variance")
    else:
        st.markdown("- ✨ **Smooth steering** - Low variance")

with insights_col2:
    st.subheader("🏎️ Driver 2 Profile")

    # Analyze driver 2
    if driver2_stats.get('max_brake_front', 0) > 80:
        st.markdown("- 🛑 **Aggressive braking** - High brake pressure")
    else:
        st.markdown("- ✅ **Smooth braking** - Moderate brake pressure")

    if driver2_stats.get('max_lateral_g', 0) > 1.5:
        st.markdown("- 🔥 **Aggressive cornering** - High lateral G-forces")
    else:
        st.markdown("- ✅ **Conservative cornering** - Moderate G-forces")

    if driver2_stats.get('steering_variance', 0) > 30:
        st.markdown("- ⚡ **Abrupt steering** - High variance")
    else:
        st.markdown("- ✨ **Smooth steering** - Low variance")

# Recommendations
st.markdown("---")
st.subheader("🎯 Coaching Recommendations")

# Compare brake pressure
if driver1_stats.get('avg_brake_front', 0) > driver2_stats.get('avg_brake_front', 0):
    st.info(f"💡 Driver 1: Consider reducing brake pressure to match Driver 2's smoother style")
else:
    st.info(f"💡 Driver 2: Consider reducing brake pressure to match Driver 1's smoother style")

# Compare speed
if driver1_stats.get('avg_speed', 0) > driver2_stats.get('avg_speed', 0):
    st.success(f"✅ Driver 1 maintains higher average speed")
else:
    st.success(f"✅ Driver 2 maintains higher average speed")

st.markdown("---")

# Footer navigation
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("← What-If Analysis", width='stretch'):
        st.switch_page("pages/2_🎮_What_If_Analysis.py")

with col2:
    if st.button("🏠 Home", width='stretch'):
        st.switch_page("app.py")

with col3:
    if st.button("Track Visualization →", width='stretch'):
        st.switch_page("pages/1_🏁_Track_Visualization.py")
