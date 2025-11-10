"""
ML Model Predictor for Tire Degradation

Provides functions for loading the trained Random Forest model and making predictions.
Includes what-if scenario analysis for interactive dashboard features.
"""

import streamlit as st
import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path
from typing import Dict, Tuple, List
import traceback
from .logger import setup_logger, log_exception

# Setup logger
logger = setup_logger("model_predictor")


# Feature names (23 features in order expected by model)
FEATURE_NAMES = [
    'air_temp', 'track_temp', 'humidity', 'wind_speed', 'temp_delta',
    'avg_brake_front', 'max_brake_front', 'avg_brake_rear', 'max_brake_rear',
    'avg_lateral_g', 'max_lateral_g', 'avg_long_g', 'max_accel_g', 'max_brake_g',
    'steering_variance', 'avg_steering_angle', 'avg_throttle_blade',
    'avg_speed', 'max_speed', 'min_speed', 'avg_rpm', 'max_rpm', 'lap_in_stint'
]


@st.cache_resource
def load_model():
    """
    Load the trained Random Forest model (cached for performance).

    Returns:
        Tuple of (model, metadata_dict)
    """
    try:
        project_root = Path(__file__).parent.parent.parent
        model_path = project_root / "models" / "tire_degradation_model_random_forest_with_weather.pkl"
        metadata_path = project_root / "models" / "model_metadata_with_weather.json"

        logger.debug(f"Loading model from: {model_path}")
        logger.debug(f"Loading metadata from: {metadata_path}")

        if not model_path.exists():
            logger.error(f"Model file not found: {model_path}")
            raise FileNotFoundError(f"Model file not found: {model_path}")

        if not metadata_path.exists():
            logger.error(f"Metadata file not found: {metadata_path}")
            raise FileNotFoundError(f"Metadata file not found: {metadata_path}")

        # Load model
        model = joblib.load(model_path)
        logger.info(f"Model loaded successfully: {type(model).__name__}")

        # Load metadata
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        logger.info(f"Metadata loaded successfully: {len(metadata)} keys")

        return model, metadata

    except Exception as e:
        log_exception(logger, e, "Failed to load model or metadata")
        raise


def predict_degradation(features_df: pd.DataFrame) -> np.ndarray:
    """
    Predict tire degradation for feature vectors.

    Args:
        features_df: DataFrame with 23 features (can be single row or multiple rows)

    Returns:
        Array of predictions (tire degradation in seconds/lap)
    """
    try:
        logger.debug(f"Predicting degradation for {len(features_df)} samples")
        logger.debug(f"Input features shape: {features_df.shape}, columns: {features_df.columns.tolist()}")

        model, _ = load_model()

        # Validate features
        missing_features = [f for f in FEATURE_NAMES if f not in features_df.columns]
        if missing_features:
            logger.error(f"Missing features: {missing_features}")
            raise ValueError(f"Missing required features: {missing_features}")

        # Ensure features are in correct order
        features_ordered = features_df[FEATURE_NAMES].copy()

        # Check for NaN values and fill with 0
        if features_ordered.isnull().any().any():
            null_cols = features_ordered.columns[features_ordered.isnull().any()].tolist()

            # avg_throttle_blade NaN is expected (some telemetry doesn't have this sensor)
            if null_cols == ['avg_throttle_blade']:
                logger.debug(f"Expected NaN in avg_throttle_blade column, filling with 0")
            else:
                logger.warning(f"NaN values found in features: {null_cols}")
                logger.debug(f"NaN counts per column: {features_ordered.isnull().sum()[features_ordered.isnull().sum() > 0].to_dict()}")

            # Fill NaN with 0 and convert to numeric to avoid pandas FutureWarning
            # Convert object columns to numeric first, then fill NaN
            for col in features_ordered.columns:
                if features_ordered[col].dtype == 'object':
                    features_ordered[col] = pd.to_numeric(features_ordered[col], errors='coerce')
            features_ordered = features_ordered.fillna(0)

        # Check for infinite values (convert to numeric first to avoid type errors)
        try:
            features_numeric = features_ordered.apply(pd.to_numeric, errors='coerce')
            if np.isinf(features_numeric.values).any():
                logger.warning("Infinite values found in features")
                # Replace inf with large finite values
                features_ordered = features_ordered.replace([np.inf, -np.inf], [1e10, -1e10])
                logger.debug("Replaced infinite values")
        except Exception as e:
            logger.debug(f"Could not check for infinite values: {e}")

        # Make predictions
        predictions = model.predict(features_ordered)

        logger.info(f"Predictions: min={predictions.min():.3f}, max={predictions.max():.3f}, mean={predictions.mean():.3f}")

        return predictions

    except Exception as e:
        log_exception(logger, e, "Error making predictions")
        raise


def predict_lap_degradation(lap_features: pd.Series) -> float:
    """
    Predict degradation for a single lap.

    Args:
        lap_features: Series with 23 features

    Returns:
        Predicted tire degradation (seconds/lap)
    """
    try:
        logger.debug(f"Predicting single lap degradation, features type: {type(lap_features)}")

        # Check if lap_features is actually a tuple (common error)
        if isinstance(lap_features, tuple):
            logger.error(f"lap_features is a tuple (expected pd.Series): {lap_features}")
            raise TypeError(f"Expected pd.Series but got tuple: {lap_features}")

        # Convert Series to DataFrame (single row)
        features_df = pd.DataFrame([lap_features])
        logger.debug(f"Created DataFrame with shape: {features_df.shape}")

        # Get prediction
        prediction = predict_degradation(features_df)[0]

        logger.info(f"Single lap prediction: {prediction:.3f} sec/lap")

        return prediction

    except IndexError as e:
        log_exception(logger, e, "IndexError in predict_lap_degradation - possibly empty prediction array")
        raise
    except Exception as e:
        log_exception(logger, e, "Error in predict_lap_degradation")
        raise


def what_if_prediction(base_features: pd.Series, adjustments: Dict[str, float]) -> Tuple[float, float, pd.Series]:
    """
    Perform what-if analysis by adjusting driving parameters.

    Args:
        base_features: Original lap features (Series)
        adjustments: Dictionary of feature adjustments as percentages
                    e.g., {'avg_brake_front': -20} means reduce by 20%

    Returns:
        Tuple of (baseline_prediction, adjusted_prediction, modified_features)
    """
    # Get baseline prediction
    baseline_pred = predict_lap_degradation(base_features)

    # Create modified features
    modified_features = base_features.copy()

    for feature_name, pct_change in adjustments.items():
        if feature_name in modified_features:
            # Apply percentage change
            original_value = base_features[feature_name]
            modified_features[feature_name] = original_value * (1 + pct_change / 100)

    # Get adjusted prediction
    adjusted_pred = predict_lap_degradation(modified_features)

    return baseline_pred, adjusted_pred, modified_features


def get_feature_importance() -> pd.DataFrame:
    """
    Get feature importance rankings from the trained model.

    Returns:
        DataFrame with columns: feature, importance (sorted descending)
    """
    model, metadata = load_model()

    # Extract feature importance
    importance = model.feature_importances_

    # Create DataFrame
    importance_df = pd.DataFrame({
        'feature': FEATURE_NAMES,
        'importance': importance
    })

    # Sort by importance
    importance_df = importance_df.sort_values('importance', ascending=False)

    return importance_df


def calculate_efficiency_score(lap_time: float, degradation: float) -> float:
    """
    Calculate tire management efficiency score.

    Higher score = better tire management (fast lap with low degradation)

    Args:
        lap_time: Lap time in seconds
        degradation: Tire degradation rate (seconds/lap)

    Returns:
        Efficiency score (normalized metric)
    """
    # Avoid division by zero
    if lap_time <= 0 or lap_time is None:
        lap_time = 1.0  # Default to prevent division by zero
    if degradation <= 0 or degradation is None:
        degradation = 0.01

    # Efficiency = speed per unit of tire wear
    # Lower lap time / lower degradation = higher efficiency
    efficiency = (100.0 / lap_time) * (1.0 / degradation)

    return efficiency


def get_coaching_insights(baseline_pred: float, adjusted_pred: float, adjustments: Dict[str, float]) -> List[str]:
    """
    Generate AI coaching insights based on what-if predictions.

    Args:
        baseline_pred: Baseline degradation prediction
        adjusted_pred: Adjusted degradation prediction
        adjustments: Dictionary of applied adjustments

    Returns:
        List of coaching insight strings
    """
    insights = []
    delta = adjusted_pred - baseline_pred

    # Overall impact
    if delta < -0.1:
        insights.append(f"✅ Great adjustment! You could save {abs(delta):.2f} seconds/lap in tire wear.")
    elif delta > 0.1:
        insights.append(f"⚠️ This change increases tire wear by {delta:.2f} seconds/lap.")
    else:
        insights.append(f"ℹ️ Minimal impact on tire degradation ({abs(delta):.2f} sec/lap).")

    # Specific adjustments
    for feature, pct in adjustments.items():
        if 'brake' in feature.lower():
            if pct < 0:
                insights.append("🎯 Softer braking reduces heat buildup in tires.")
            elif pct > 0:
                insights.append("⚠️ Harder braking increases tire temperature and wear.")

        if 'lateral_g' in feature.lower() or 'cornering' in feature.lower():
            if pct < 0:
                insights.append("🔄 Slower cornering speeds reduce lateral tire stress.")
            elif pct > 0:
                insights.append("🔥 Aggressive cornering increases edge wear.")

        if 'steering' in feature.lower():
            if pct < 0:
                insights.append("✨ Smoother steering inputs preserve tire life.")
            elif pct > 0:
                insights.append("⚡ Abrupt steering heats up tire shoulders.")

    # Stint prediction
    if delta < 0:
        laps_saved = abs(delta) * 15  # Assume 15-lap stint
        insights.append(f"📊 Over a 15-lap stint, this saves ~{laps_saved:.1f} seconds of tire life.")

    return insights


def get_model_metadata() -> Dict:
    """
    Get model metadata (performance metrics, training info).

    Returns:
        Dictionary with model metadata
    """
    _, metadata = load_model()
    return metadata


def batch_predict(features_list: List[pd.Series]) -> pd.DataFrame:
    """
    Make predictions for multiple laps efficiently.

    Args:
        features_list: List of feature Series

    Returns:
        DataFrame with predictions and lap indices
    """
    # Convert list of Series to DataFrame
    features_df = pd.DataFrame(features_list)

    # Get predictions
    predictions = predict_degradation(features_df)

    # Create results DataFrame
    results = pd.DataFrame({
        'lap_index': range(len(predictions)),
        'predicted_degradation': predictions
    })

    return results


def interpret_degradation(degradation_value: float) -> Dict[str, str]:
    """
    Interpret degradation value with human-readable descriptions.

    Args:
        degradation_value: Predicted degradation in seconds/lap

    Returns:
        Dictionary with color, label, and description
    """
    if degradation_value < 0.2:
        return {
            'color': 'green',
            'label': 'Excellent',
            'description': 'Minimal tire wear - very efficient driving'
        }
    elif degradation_value < 0.5:
        return {
            'color': 'yellow',
            'label': 'Good',
            'description': 'Moderate tire wear - sustainable pace'
        }
    elif degradation_value < 0.8:
        return {
            'color': 'orange',
            'label': 'High',
            'description': 'Elevated tire wear - consider adjusting style'
        }
    else:
        return {
            'color': 'red',
            'label': 'Critical',
            'description': 'Excessive tire wear - unsustainable pace'
        }
