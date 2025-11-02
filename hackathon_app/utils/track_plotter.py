"""
Track Visualization and Plotting Utilities

Provides functions for creating track maps, GPS overlays, telemetry charts,
and degradation heatmaps for the Tire Whisperer dashboard.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
from PIL import Image
from typing import Optional, Tuple, List


# Color scale for degradation heatmap
DEGRADATION_COLORS = {
    'excellent': '#00FF00',  # Green (0.0-0.2)
    'good': '#FFFF00',       # Yellow (0.2-0.5)
    'high': '#FFA500',       # Orange (0.5-0.8)
    'critical': '#FF0000'    # Red (0.8+)
}


@st.cache_data
def load_track_image(track_name: str) -> Optional[Image.Image]:
    """
    Load track map PNG image.

    Args:
        track_name: Name of track (e.g., 'barber', 'cota', 'indianapolis')

    Returns:
        PIL Image object (or None if not found)
    """
    project_root = Path(__file__).parent.parent.parent
    image_path = project_root / "hackathon_app" / "assets" / "track_images" / f"{track_name}.png"

    if not image_path.exists():
        return None

    return Image.open(image_path)


def plot_track_with_overlay(
    track_name: str,
    gps_data: Optional[pd.DataFrame] = None,
    color_values: Optional[np.ndarray] = None,
    title: str = "Track Map"
) -> go.Figure:
    """
    Create track map with optional GPS overlay and color coding.

    Args:
        track_name: Name of track
        gps_data: DataFrame with 'latitude', 'longitude' columns (optional)
        color_values: Array of values to color-code the GPS trace (optional)
        title: Plot title

    Returns:
        Plotly Figure object
    """
    fig = go.Figure()

    # Load track image
    track_img = load_track_image(track_name)

    if track_img is not None:
        # Add track image as background
        fig.add_layout_image(
            dict(
                source=track_img,
                xref="x",
                yref="y",
                x=0,
                y=1,
                sizex=1,
                sizey=1,
                sizing="stretch",
                opacity=0.7,
                layer="below"
            )
        )

    # Add GPS trace if available
    if gps_data is not None and not gps_data.empty:
        # Normalize coordinates to [0, 1] range for overlay
        lat_min, lat_max = gps_data['latitude'].min(), gps_data['latitude'].max()
        lon_min, lon_max = gps_data['longitude'].min(), gps_data['longitude'].max()

        if lat_max > lat_min and lon_max > lon_min:
            gps_data['x'] = (gps_data['longitude'] - lon_min) / (lon_max - lon_min)
            gps_data['y'] = (gps_data['latitude'] - lat_min) / (lat_max - lat_min)

            # Create scatter plot with color coding
            if color_values is not None:
                # Color-coded by degradation or other metric
                fig.add_trace(go.Scatter(
                    x=gps_data['x'],
                    y=gps_data['y'],
                    mode='markers+lines',
                    marker=dict(
                        size=5,
                        color=color_values,
                        colorscale='RdYlGn_r',  # Red-Yellow-Green reversed
                        showscale=True,
                        colorbar=dict(title="Degradation<br>(sec/lap)")
                    ),
                    line=dict(width=2),
                    name='Racing Line',
                    hovertemplate='<b>Lap Position</b><br>Lat: %{customdata[0]:.6f}<br>Lon: %{customdata[1]:.6f}<extra></extra>',
                    customdata=gps_data[['latitude', 'longitude']].values
                ))
            else:
                # Simple trace without color coding
                fig.add_trace(go.Scatter(
                    x=gps_data['x'],
                    y=gps_data['y'],
                    mode='markers+lines',
                    marker=dict(size=4, color='#E50000'),  # Toyota Red
                    line=dict(width=2, color='#E50000'),
                    name='Racing Line'
                ))

    # Update layout
    fig.update_layout(
        title=title,
        xaxis=dict(visible=False, range=[0, 1]),
        yaxis=dict(visible=False, range=[0, 1]),
        showlegend=False,
        height=600,
        margin=dict(l=0, r=0, t=40, b=0),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )

    return fig


def create_telemetry_charts(telemetry_df: pd.DataFrame) -> Tuple[go.Figure, go.Figure, go.Figure]:
    """
    Create telemetry time-series charts (speed, brake, G-forces).

    Args:
        telemetry_df: DataFrame with telemetry columns

    Returns:
        Tuple of 3 Plotly figures (speed_chart, brake_chart, g_force_chart)
    """
    # Speed chart
    speed_fig = go.Figure()
    speed_fig.add_trace(go.Scatter(
        y=telemetry_df['speed'],
        mode='lines',
        name='Speed',
        line=dict(color='#00BFFF', width=2)
    ))
    speed_fig.update_layout(
        title='Speed (km/h)',
        height=200,
        margin=dict(l=40, r=10, t=40, b=30),
        yaxis_title='km/h'
    )

    # Brake pressure chart
    brake_fig = go.Figure()
    brake_fig.add_trace(go.Scatter(
        y=telemetry_df['pbrake_f'],
        mode='lines',
        name='Front Brake',
        line=dict(color='#FF4444', width=2)
    ))
    brake_fig.add_trace(go.Scatter(
        y=telemetry_df['pbrake_r'],
        mode='lines',
        name='Rear Brake',
        line=dict(color='#FF8888', width=2)
    ))
    brake_fig.update_layout(
        title='Brake Pressure (bar)',
        height=200,
        margin=dict(l=40, r=10, t=40, b=30),
        yaxis_title='bar'
    )

    # G-force chart
    g_fig = go.Figure()
    g_fig.add_trace(go.Scatter(
        y=telemetry_df['accy_can'],
        mode='lines',
        name='Lateral G',
        line=dict(color='#00FF00', width=2)
    ))
    g_fig.add_trace(go.Scatter(
        y=telemetry_df['accx_can'],
        mode='lines',
        name='Longitudinal G',
        line=dict(color='#FFA500', width=2)
    ))
    g_fig.update_layout(
        title='G-Forces',
        height=200,
        margin=dict(l=40, r=10, t=40, b=30),
        yaxis_title='G'
    )

    return speed_fig, brake_fig, g_fig


def create_degradation_meter(degradation_value: float, max_value: float = 1.5) -> go.Figure:
    """
    Create a gauge/meter chart for tire degradation.

    Args:
        degradation_value: Predicted degradation (seconds/lap)
        max_value: Maximum value for gauge scale

    Returns:
        Plotly Figure with gauge chart
    """
    # Determine color based on value
    if degradation_value < 0.2:
        color = '#00FF00'  # Green
    elif degradation_value < 0.5:
        color = '#FFFF00'  # Yellow
    elif degradation_value < 0.8:
        color = '#FFA500'  # Orange
    else:
        color = '#FF0000'  # Red

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=degradation_value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Tire Degradation<br>(sec/lap)"},
        number={'suffix': " sec/lap", 'font': {'size': 24}},
        gauge={
            'axis': {'range': [None, max_value], 'tickwidth': 1},
            'bar': {'color': color},
            'steps': [
                {'range': [0, 0.2], 'color': 'rgba(0, 255, 0, 0.3)'},
                {'range': [0.2, 0.5], 'color': 'rgba(255, 255, 0, 0.3)'},
                {'range': [0.5, 0.8], 'color': 'rgba(255, 165, 0, 0.3)'},
                {'range': [0.8, max_value], 'color': 'rgba(255, 0, 0, 0.3)'}
            ],
            'threshold': {
                'line': {'color': "white", 'width': 4},
                'thickness': 0.75,
                'value': degradation_value
            }
        }
    ))

    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=50, b=20)
    )

    return fig


def create_radar_chart(driver1_stats: dict, driver2_stats: dict, labels: List[str]) -> go.Figure:
    """
    Create radar chart comparing two drivers' aggression profiles.

    Args:
        driver1_stats: Dictionary of stats for driver 1
        driver2_stats: Dictionary of stats for driver 2
        labels: List of metric labels for radar axes

    Returns:
        Plotly Figure with radar chart
    """
    fig = go.Figure()

    # Driver 1
    fig.add_trace(go.Scatterpolar(
        r=list(driver1_stats.values()),
        theta=labels,
        fill='toself',
        name=f"Driver {driver1_stats.get('car_number', '1')}",
        line=dict(color='#E50000', width=2)
    ))

    # Driver 2
    fig.add_trace(go.Scatterpolar(
        r=list(driver2_stats.values()),
        theta=labels,
        fill='toself',
        name=f"Driver {driver2_stats.get('car_number', '2')}",
        line=dict(color='#0066FF', width=2)
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, max(
                max(driver1_stats.values()),
                max(driver2_stats.values())
            ) * 1.1])
        ),
        showlegend=True,
        height=500,
        title="Driver Aggression Profile"
    )

    return fig


def create_feature_importance_chart(importance_df: pd.DataFrame, top_n: int = 10) -> go.Figure:
    """
    Create horizontal bar chart for feature importance.

    Args:
        importance_df: DataFrame with 'feature' and 'importance' columns
        top_n: Number of top features to display

    Returns:
        Plotly Figure with bar chart
    """
    # Get top N features
    top_features = importance_df.head(top_n)

    fig = go.Figure(go.Bar(
        x=top_features['importance'],
        y=top_features['feature'],
        orientation='h',
        marker=dict(color='#E50000')
    ))

    fig.update_layout(
        title=f"Top {top_n} Feature Importance",
        xaxis_title="Importance",
        yaxis_title="Feature",
        height=400,
        margin=dict(l=150, r=20, t=50, b=50)
    )

    return fig


def create_comparison_table(driver1_stats: dict, driver2_stats: dict) -> pd.DataFrame:
    """
    Create comparison table for two drivers.

    Args:
        driver1_stats: Stats dictionary for driver 1
        driver2_stats: Stats dictionary for driver 2

    Returns:
        DataFrame formatted for display
    """
    metrics = [
        ('Avg Lap Time', 'avg_lap_time', 's'),
        ('Avg Brake Pressure', 'avg_brake_front', 'bar'),
        ('Max Brake Pressure', 'max_brake_front', 'bar'),
        ('Avg Lateral G', 'avg_lateral_g', 'G'),
        ('Max Lateral G', 'max_lateral_g', 'G'),
        ('Avg Speed', 'avg_speed', 'km/h'),
        ('Max Speed', 'max_speed', 'km/h'),
        ('Steering Smoothness', 'steering_variance', '°')
    ]

    data = []
    for label, key, unit in metrics:
        val1 = driver1_stats.get(key, 0)
        val2 = driver2_stats.get(key, 0)
        delta = ((val2 - val1) / val1 * 100) if val1 != 0 else 0

        data.append({
            'Metric': label,
            f"Driver {driver1_stats.get('car_number', '1')}": f"{val1:.2f} {unit}",
            f"Driver {driver2_stats.get('car_number', '2')}": f"{val2:.2f} {unit}",
            'Δ %': f"{delta:+.1f}%"
        })

    return pd.DataFrame(data)


def animate_lap_trace(gps_data: pd.DataFrame, frame_step: int = 10) -> go.Figure:
    """
    Create animated GPS trace for lap visualization.

    Args:
        gps_data: DataFrame with GPS coordinates
        frame_step: Number of data points to skip per frame

    Returns:
        Plotly Figure with animation
    """
    # Normalize coordinates
    lat_min, lat_max = gps_data['latitude'].min(), gps_data['latitude'].max()
    lon_min, lon_max = gps_data['longitude'].min(), gps_data['longitude'].max()

    gps_data['x'] = (gps_data['longitude'] - lon_min) / (lon_max - lon_min)
    gps_data['y'] = (gps_data['latitude'] - lat_min) / (lat_max - lat_min)

    # Create frames
    frames = []
    for i in range(0, len(gps_data), frame_step):
        frame_data = gps_data.iloc[:i+frame_step]
        frames.append(go.Frame(
            data=[go.Scatter(
                x=frame_data['x'],
                y=frame_data['y'],
                mode='lines+markers',
                marker=dict(size=6, color='#E50000'),
                line=dict(width=3, color='#E50000')
            )]
        ))

    # Create initial figure
    fig = go.Figure(
        data=[go.Scatter(x=[], y=[], mode='lines+markers')],
        layout=go.Layout(
            xaxis=dict(range=[0, 1], visible=False),
            yaxis=dict(range=[0, 1], visible=False),
            updatemenus=[dict(
                type="buttons",
                buttons=[
                    dict(label="Play", method="animate", args=[None, {"frame": {"duration": 50}}]),
                    dict(label="Pause", method="animate", args=[[None], {"frame": {"duration": 0}, "mode": "immediate"}])
                ]
            )]
        ),
        frames=frames
    )

    fig.update_layout(height=600, title="Animated Lap Trace")

    return fig
