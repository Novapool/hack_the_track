"""
What-If Analysis Page

Interactive scenario analysis to test how driving style changes
affect tire degradation predictions.
"""

import streamlit as st
import sys
from pathlib import Path
import pandas as pd

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils.data_loader import (
    get_available_tracks,
    get_available_laps,
    get_lap_features,
    get_lap_metadata
)
from utils.model_predictor import (
    what_if_prediction,
    interpret_degradation,
    get_coaching_insights
)


st.set_page_config(page_title="What-If Analysis", page_icon="🎮", layout="wide")

# Title
st.title("🎮 What-If Analysis")
st.markdown("Test driving style changes and see instant AI predictions")

st.markdown("---")

# Sidebar - Lap Selection
with st.sidebar:
    st.header("🎛️ Select Base Lap")

    # Track selector
    try:
        from utils.data_loader import get_available_tracks
        tracks_df = get_available_tracks()
        track_options = tracks_df['track_name'].tolist()

        selected_track = st.selectbox(
            "Track",
            options=track_options
        )

        # Lap selector
        laps_df = get_available_laps(selected_track, limit=30)

        if laps_df.empty:
            st.warning(f"No laps for {selected_track}")
            st.stop()

        lap_options = []
        for _, lap in laps_df.iterrows():
            lap_label = f"Lap #{lap['lap_number']} - {lap['lap_duration']:.2f}s (Car {lap['car_number']})"
            lap_options.append((lap_label, lap['lap_id']))

        selected_lap_label = st.selectbox(
            "Lap",
            options=[label for label, _ in lap_options]
        )

        selected_lap_id = next(lid for label, lid in lap_options if label == selected_lap_label)
        lap_meta = get_lap_metadata(selected_lap_id)

        st.success(f"✅ Base lap selected")

    except Exception as e:
        st.error(f"Error: {e}")
        st.stop()

st.markdown("---")

# Load base lap features
try:
    with st.spinner("Loading lap data..."):
        base_features = get_lap_features(selected_lap_id)

    if base_features is None:
        st.error("Could not load lap features")
        st.stop()

except Exception as e:
    st.error(f"Error loading features: {e}")
    st.stop()

# Main content
st.header(f"🔧 Adjust Driving Parameters - {selected_track.title()}")

# Adjustment sliders
st.subheader("🎚️ Interactive Controls")

col1, col2 = st.columns(2)

with col1:
    brake_adj = st.slider(
        "🛑 Brake Pressure Adjustment",
        min_value=-30,
        max_value=30,
        value=0,
        step=5,
        format="%d%%",
        help="Adjust average brake pressure. Negative = softer braking"
    )

    steering_adj = st.slider(
        "🔄 Steering Smoothness",
        min_value=-40,
        max_value=40,
        value=0,
        step=5,
        format="%d%%",
        help="Adjust steering variance. Negative = smoother inputs"
    )

with col2:
    speed_adj = st.slider(
        "💨 Cornering Speed",
        min_value=-20,
        max_value=20,
        value=0,
        step=5,
        format="%d%%",
        help="Adjust average speed (simulates cornering speed changes)"
    )

    throttle_adj = st.slider(
        "⚡ Throttle Application",
        min_value=-20,
        max_value=20,
        value=0,
        step=5,
        format="%d%%",
        help="Adjust throttle blade position"
    )

st.markdown("---")

# Make predictions
adjustments = {}

if brake_adj != 0:
    adjustments['avg_brake_front'] = brake_adj
    adjustments['max_brake_front'] = brake_adj

if steering_adj != 0:
    adjustments['steering_variance'] = steering_adj

if speed_adj != 0:
    adjustments['avg_speed'] = speed_adj

if throttle_adj != 0:
    adjustments['avg_throttle_blade'] = throttle_adj

try:
    baseline_pred, adjusted_pred, modified_features = what_if_prediction(
        base_features,
        adjustments
    )

    # Results section
    st.header("📊 Results")

    # Side-by-side comparison
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="🔹 Baseline Degradation",
            value=f"{baseline_pred:.3f} sec/lap"
        )
        baseline_interp = interpret_degradation(baseline_pred)
        st.markdown(f"**{baseline_interp['label']}** :{baseline_interp['color']}[●]")

    with col2:
        st.metric(
            label="🔸 Adjusted Degradation",
            value=f"{adjusted_pred:.3f} sec/lap"
        )
        adjusted_interp = interpret_degradation(adjusted_pred)
        st.markdown(f"**{adjusted_interp['label']}** :{adjusted_interp['color']}[●]")

    with col3:
        delta = adjusted_pred - baseline_pred
        delta_pct = (delta / baseline_pred * 100) if baseline_pred != 0 else 0

        st.metric(
            label="📈 Delta (Change)",
            value=f"{delta:+.3f} sec/lap",
            delta=f"{delta_pct:+.1f}%"
        )

        if delta < -0.05:
            st.success("✅ Improvement!")
        elif delta > 0.05:
            st.warning("⚠️ Increased wear")
        else:
            st.info("ℹ️ Minimal change")

    st.markdown("---")

    # AI Coaching Insights
    st.header("💡 AI Coaching Insights")

    insights = get_coaching_insights(baseline_pred, adjusted_pred, adjustments)

    for insight in insights:
        st.markdown(f"- {insight}")

    st.markdown("---")

    # Feature comparison table
    st.header("📋 Feature Changes")

    comparison_data = []

    feature_labels = {
        'avg_brake_front': 'Avg Brake Pressure',
        'max_brake_front': 'Max Brake Pressure',
        'steering_variance': 'Steering Variance',
        'avg_speed': 'Average Speed',
        'avg_throttle_blade': 'Throttle Blade'
    }

    for feature_key, label in feature_labels.items():
        if feature_key in base_features:
            # Handle None values with defaults
            baseline_val = base_features.get(feature_key, 0.0)
            adjusted_val = modified_features.get(feature_key, 0.0)

            # Convert None to 0.0 for calculations
            baseline_val = 0.0 if baseline_val is None else float(baseline_val)
            adjusted_val = 0.0 if adjusted_val is None else float(adjusted_val)

            delta_val = adjusted_val - baseline_val
            delta_pct_val = (delta_val / baseline_val * 100) if baseline_val != 0 else 0

            comparison_data.append({
                'Feature': label,
                'Baseline': f"{baseline_val:.2f}",
                'Adjusted': f"{adjusted_val:.2f}",
                'Δ': f"{delta_val:+.2f}",
                'Δ %': f"{delta_pct_val:+.1f}%"
            })

    comparison_df = pd.DataFrame(comparison_data)
    st.dataframe(comparison_df, width='stretch', hide_index=True)

    # Stint projection
    st.markdown("---")
    st.header("🏁 Stint Projection")

    stint_laps = 15
    baseline_total = baseline_pred * stint_laps
    adjusted_total = adjusted_pred * stint_laps
    stint_delta = adjusted_total - baseline_total

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label=f"Baseline ({stint_laps}-lap stint)",
            value=f"{baseline_total:.2f} sec total wear"
        )

    with col2:
        st.metric(
            label=f"Adjusted ({stint_laps}-lap stint)",
            value=f"{adjusted_total:.2f} sec total wear"
        )

    with col3:
        st.metric(
            label="Stint Delta",
            value=f"{stint_delta:+.2f} sec",
            delta=f"{(stint_delta/baseline_total*100):+.1f}%"
        )

    if stint_delta < 0:
        st.success(f"✅ Your adjustments could save {abs(stint_delta):.2f} seconds of tire life over the stint!")
    elif stint_delta > 0:
        st.warning(f"⚠️ Your adjustments add {stint_delta:.2f} seconds of tire wear over the stint.")
    else:
        st.info("ℹ️ Minimal impact on stint-long tire wear.")

except Exception as e:
    st.error(f"Error in prediction: {e}")

st.markdown("---")

# Footer navigation
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("← Track Visualization", width='stretch'):
        st.switch_page("pages/1_🏁_Track_Visualization.py")

with col2:
    if st.button("🏠 Home", width='stretch'):
        st.switch_page("app.py")

with col3:
    if st.button("Driver Comparison →", width='stretch'):
        st.switch_page("pages/3_👥_Driver_Comparison.py")
