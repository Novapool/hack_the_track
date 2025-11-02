"""
Utility modules for Tire Whisperer Dashboard
"""

from .data_loader import (
    get_available_tracks,
    get_available_laps,
    load_lap_telemetry,
    load_lap_gps,
    get_lap_features,
    get_vehicle_stats,
    get_all_vehicles,
    get_lap_metadata
)

from .model_predictor import (
    load_model,
    predict_degradation,
    predict_lap_degradation,
    what_if_prediction,
    get_feature_importance,
    calculate_efficiency_score,
    get_coaching_insights,
    interpret_degradation
)

from .track_plotter import (
    load_track_image,
    plot_track_with_overlay,
    create_telemetry_charts,
    create_degradation_meter,
    create_radar_chart,
    create_comparison_table,
    create_feature_importance_chart,
    animate_lap_trace
)

__all__ = [
    # Data loader
    'get_available_tracks',
    'get_available_laps',
    'load_lap_telemetry',
    'load_lap_gps',
    'get_lap_features',
    'get_vehicle_stats',
    'get_all_vehicles',
    'get_lap_metadata',
    # Model predictor
    'load_model',
    'predict_degradation',
    'predict_lap_degradation',
    'what_if_prediction',
    'get_feature_importance',
    'calculate_efficiency_score',
    'get_coaching_insights',
    'interpret_degradation',
    # Track plotter
    'load_track_image',
    'plot_track_with_overlay',
    'create_telemetry_charts',
    'create_degradation_meter',
    'create_radar_chart',
    'create_comparison_table',
    'create_feature_importance_chart',
    'animate_lap_trace'
]
