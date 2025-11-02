"""
Tire Whisperer - Interactive Tire Degradation Dashboard
Main Landing Page

AI-Powered tire wear analysis for Toyota GR Cup racing data.
"""

import streamlit as st
from utils.model_predictor import get_model_metadata
from utils.data_loader import get_available_tracks


# Page configuration
st.set_page_config(
    page_title="Tire Whisperer - GR Cup Analytics",
    page_icon="🏁",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Hero Section
st.title("🏁 Tire Whisperer")
st.subheader("AI-Powered Tire Degradation Analysis for Toyota GR Cup Racing")

st.markdown("---")

# Quick Stats Section
st.header("📊 Dashboard Overview")

col1, col2, col3 = st.columns(3)

# Load model metadata for stats
try:
    metadata = get_model_metadata()

    with col1:
        st.metric(
            label="Model Accuracy (R² Score)",
            value=f"{metadata['test_metrics']['r2_score']:.1%}",
            help="Percentage of tire degradation variance explained by the model"
        )

    with col2:
        st.metric(
            label="Prediction Error (MAE)",
            value=f"{metadata['test_metrics']['mae']:.3f} sec/lap",
            help="Average prediction error in seconds per lap"
        )

    with col3:
        st.metric(
            label="Features Analyzed",
            value=f"{len(metadata['feature_names'])}",
            help="Number of driving and weather metrics used for predictions"
        )

except Exception as e:
    st.warning(f"Could not load model metadata: {e}")

st.markdown("---")

# Data Overview
st.header("📈 Dataset Statistics")

col1, col2, col3 = st.columns(3)

try:
    # Load track info
    tracks_df = get_available_tracks()
    total_laps = tracks_df['total_laps'].sum()
    total_tracks = len(tracks_df)
    gps_laps = tracks_df['laps_with_gps'].sum()

    with col1:
        st.metric(
            label="Total Tracks",
            value=total_tracks,
            help="Number of racing circuits in the dataset"
        )

    with col2:
        st.metric(
            label="Total Laps Analyzed",
            value=f"{total_laps:,}",
            help="Number of laps available for analysis"
        )

    with col3:
        st.metric(
            label="Laps with GPS",
            value=f"{gps_laps:,}",
            help="Laps with GPS telemetry for track visualization"
        )

    # Track details table
    st.subheader("Available Tracks")
    st.dataframe(
        tracks_df.rename(columns={
            'track_name': 'Track',
            'total_laps': 'Total Laps',
            'laps_with_gps': 'GPS Laps',
            'gps_coverage_pct': 'GPS Coverage %'
        }),
        use_container_width=True,
        hide_index=True
    )

except Exception as e:
    st.error(f"Error loading track data: {e}")

st.markdown("---")

# How It Works
st.header("🔧 How It Works")

st.markdown("""
**Tire Whisperer** uses machine learning to predict tire degradation based on driving style and track conditions.

**Our Approach:**
1. **Data Collection**: Analyze telemetry from 10,000+ laps across 7 Toyota GR Cup tracks
2. **Feature Engineering**: Extract 23 driving metrics (brake pressure, G-forces, steering smoothness, weather)
3. **ML Model**: Random Forest trained to predict tire wear in seconds per lap
4. **Interactive Analysis**: Explore what-if scenarios and compare driving styles
""")

# Model Features
with st.expander("📋 Model Features (23 total)", expanded=False):
    st.markdown("""
    **Weather Conditions (5 features)**
    - Air temperature, Track temperature, Humidity, Wind speed, Temperature delta

    **Brake Pressure (4 features)**
    - Average/Max front brake, Average/Max rear brake

    **G-Forces (6 features)**
    - Lateral G (cornering), Longitudinal G (accel/brake), Peak values

    **Steering (2 features)**
    - Steering variance (smoothness), Average steering angle

    **Speed & Engine (5 features)**
    - Average/Max/Min speed, Average/Max RPM

    **Stint Position (1 feature)**
    - Lap number within current stint
    """)

st.markdown("---")

# Navigation Cards
st.header("🚀 Explore the Dashboard")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("🏁 Track Visualization")
    st.markdown("""
    **Watch laps come alive!**
    - Animated racing line on track maps
    - Real-time telemetry charts
    - GPS-based degradation heatmap
    - Interactive lap selection
    """)
    if st.button("🏁 Go to Track Visualization", use_container_width=True):
        st.switch_page("pages/1_🏁_Track_Visualization.py")

with col2:
    st.subheader("🎮 What-If Analysis")
    st.markdown("""
    **Test driving changes!**
    - Adjust brake pressure
    - Modify cornering speed
    - Change steering smoothness
    - See instant predictions
    """)
    if st.button("🎮 Go to What-If Analysis", use_container_width=True):
        st.switch_page("pages/2_🎮_What_If_Analysis.py")

with col3:
    st.subheader("👥 Driver Comparison")
    st.markdown("""
    **Compare tire management!**
    - Side-by-side driver analysis
    - Aggression radar chart
    - Efficiency scoring
    - Coaching insights
    """)
    if st.button("👥 Go to Driver Comparison", use_container_width=True):
        st.switch_page("pages/3_👥_Driver_Comparison.py")

st.markdown("---")

# Footer
st.caption("Built with ❤️ for the Toyota GR Cup hackathon | Powered by Streamlit & scikit-learn")

# Sidebar
with st.sidebar:
    st.image("https://via.placeholder.com/300x100/E50000/FFFFFF?text=Toyota+GR+Cup", use_container_width=True)

    st.markdown("### About")
    st.markdown("""
    **Tire Whisperer** helps racing teams and drivers optimize tire management
    through data-driven insights.

    **Key Benefits:**
    - Predict tire wear in real-time
    - Optimize driving style for tire life
    - Compare driver efficiency
    - Make data-driven pit strategy decisions
    """)

    st.markdown("### Model Performance")
    try:
        metadata = get_model_metadata()
        st.markdown(f"""
        - **R² Score**: {metadata['test_metrics']['r2_score']:.3f}
        - **MAE**: {metadata['test_metrics']['mae']:.3f} sec/lap
        - **RMSE**: {metadata['test_metrics']['rmse']:.3f} sec/lap
        - **Training Samples**: {metadata['training_samples']:,}
        - **Test Samples**: {metadata['test_samples']:,}
        """)
    except:
        st.info("Model metrics loading...")

    st.markdown("### Navigation")
    st.page_link("pages/1_🏁_Track_Visualization.py", label="🏁 Track Visualization")
    st.page_link("pages/2_🎮_What_If_Analysis.py", label="🎮 What-If Analysis")
    st.page_link("pages/3_👥_Driver_Comparison.py", label="👥 Driver Comparison")
