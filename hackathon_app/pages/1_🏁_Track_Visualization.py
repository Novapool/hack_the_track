"""
Track Visualization Page

Shows animated racing line on track maps with real-time telemetry
and tire degradation predictions.
"""

import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils.data_loader import (
    get_available_tracks,
    get_available_laps,
    load_lap_telemetry,
    load_lap_gps,
    get_lap_features,
    get_lap_metadata
)
from utils.model_predictor import predict_lap_degradation, interpret_degradation
from utils.track_plotter import (
    plot_track_with_overlay,
    create_telemetry_charts,
    create_degradation_meter
)


st.set_page_config(page_title="Track Visualization", page_icon="🏁", layout="wide")

# Title
st.title("🏁 Track Visualization")
st.markdown("Watch laps come alive with real-time telemetry and AI predictions")

st.markdown("---")

# Sidebar controls
with st.sidebar:
    st.header("🎛️ Controls")

    # Track selector
    try:
        tracks_df = get_available_tracks()
        track_options = tracks_df['track_name'].tolist()

        selected_track = st.selectbox(
            "Select Track",
            options=track_options,
            help="Choose a racing circuit to analyze"
        )

        # Show track info
        track_info = tracks_df[tracks_df['track_name'] == selected_track].iloc[0]
        st.info(f"""
        **Track Info:**
        - Total Laps: {track_info['total_laps']:,}
        - GPS Laps: {track_info['laps_with_gps']:,}
        - GPS Coverage: {track_info['gps_coverage_pct']:.1f}%
        """)

    except Exception as e:
        st.error(f"Error loading tracks: {e}")
        st.stop()

    # Lap selector
    try:
        laps_df = get_available_laps(selected_track, limit=50)

        if laps_df.empty:
            st.warning(f"No laps available for {selected_track}")
            st.stop()

        # Create lap options with metadata
        lap_options = []
        for _, lap in laps_df.iterrows():
            gps_indicator = "📍" if lap['has_gps'] else "❌"
            lap_label = f"{gps_indicator} Lap #{lap['lap_number']} - {lap['lap_duration']:.2f}s (Car {lap['car_number']})"
            lap_options.append((lap_label, lap['lap_id']))

        selected_lap_label = st.selectbox(
            "Select Lap",
            options=[label for label, _ in lap_options],
            help="Choose a lap to visualize (📍 = GPS available)"
        )

        # Get selected lap ID
        selected_lap_id = next(lid for label, lid in lap_options if label == selected_lap_label)

        # Get lap metadata
        lap_meta = get_lap_metadata(selected_lap_id)

        st.success(f"✅ Lap {lap_meta['lap_number']} selected")

    except Exception as e:
        st.error(f"Error loading laps: {e}")
        st.stop()

st.markdown("---")

# Main content area
col1, col2 = st.columns([3, 1])

with col1:
    st.subheader(f"🗺️ {selected_track.title()} - Lap {lap_meta['lap_number']}")

    # Load GPS data
    try:
        with st.spinner("Loading GPS data..."):
            gps_data = load_lap_gps(selected_lap_id)

        if gps_data is not None and not gps_data.empty:
            # Plot track with GPS overlay
            fig = plot_track_with_overlay(
                track_name=selected_track,
                gps_data=gps_data,
                title=f"{selected_track.title()} - Lap {lap_meta['lap_number']}"
            )
            st.plotly_chart(fig, width='stretch')

            st.success(f"✅ GPS trace plotted ({len(gps_data):,} data points)")
        else:
            # No GPS - show track image only
            st.warning("⚠️ No GPS data available for this lap")
            fig = plot_track_with_overlay(
                track_name=selected_track,
                title=f"{selected_track.title()} - Lap {lap_meta['lap_number']}"
            )
            st.plotly_chart(fig, width='stretch')

    except Exception as e:
        st.error(f"Error visualizing track: {e}")

    # Telemetry charts
    st.subheader("📊 Telemetry Data")

    try:
        with st.spinner("Loading telemetry..."):
            telemetry_df = load_lap_telemetry(selected_lap_id)

        if not telemetry_df.empty:
            # Create charts
            speed_fig, brake_fig, g_fig = create_telemetry_charts(telemetry_df)

            # Display in columns
            tcol1, tcol2 = st.columns(2)

            with tcol1:
                st.plotly_chart(speed_fig, width='stretch')
                st.plotly_chart(g_fig, width='stretch')

            with tcol2:
                st.plotly_chart(brake_fig, width='stretch')

                # Telemetry stats
                st.metric("Telemetry Points", f"{len(telemetry_df):,}")

        else:
            st.warning("No telemetry data available")

    except Exception as e:
        st.error(f"Error loading telemetry: {e}")

with col2:
    st.subheader("🎯 AI Predictions")

    # Load features and predict
    try:
        with st.spinner("Analyzing lap..."):
            lap_features = get_lap_features(selected_lap_id)

        if lap_features is not None:
            # Make prediction
            predicted_deg = predict_lap_degradation(lap_features)

            # Interpret prediction
            interpretation = interpret_degradation(predicted_deg)

            # Show degradation meter
            deg_fig = create_degradation_meter(predicted_deg)
            st.plotly_chart(deg_fig, width='stretch')

            # Interpretation
            st.markdown(f"""
            ### {interpretation['label']} Wear
            **Color:** :{interpretation['color']}[●]

            {interpretation['description']}
            """)

            # Feature highlights
            with st.expander("📋 Key Driving Metrics", expanded=True):
                # Use .get() with defaults to handle None values
                avg_brake = lap_features.get('avg_brake_front', 0.0) or 0.0
                max_lat_g = lap_features.get('max_lateral_g', 0.0) or 0.0
                avg_spd = lap_features.get('avg_speed', 0.0) or 0.0
                steer_var = lap_features.get('steering_variance', 0.0) or 0.0

                st.metric("Avg Brake Pressure", f"{avg_brake:.1f} bar")
                st.metric("Max Lateral G", f"{max_lat_g:.2f} G")
                st.metric("Avg Speed", f"{avg_spd:.1f} km/h")
                st.metric("Steering Smoothness", f"{steer_var:.1f}°")

            # Lap info
            with st.expander("ℹ️ Lap Info", expanded=False):
                st.markdown(f"""
                - **Lap Time**: {lap_meta['lap_duration']:.3f}s
                - **Vehicle**: Car #{lap_meta['car_number']}
                - **Track**: {lap_meta['track_name'].title()}
                - **Date**: {lap_meta.get('race_date', 'N/A')}
                """)

        else:
            st.warning("⚠️ Insufficient data for prediction")

    except Exception as e:
        st.error(f"Error making prediction: {e}")

st.markdown("---")

# Footer navigation
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("← Back to Home", width='stretch'):
        st.switch_page("app.py")

with col2:
    if st.button("🎮 What-If Analysis →", width='stretch'):
        st.switch_page("pages/2_🎮_What_If_Analysis.py")

with col3:
    if st.button("👥 Driver Comparison →", width='stretch'):
        st.switch_page("pages/3_👥_Driver_Comparison.py")
