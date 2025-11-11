"""
Test Model Sensitivity

This script tests whether the trained Random Forest model responds to input changes.
If the model always predicts the same value regardless of inputs, it indicates:
1. Overfitting to a narrow range of training data
2. Model has learned a constant function
3. Features may not be informative enough
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from hackathon_app.utils.model_predictor import load_model, predict_degradation, FEATURE_NAMES
from hackathon_app.utils.data_loader import get_lap_features


def test_model_sensitivity():
    """
    Test if the model responds to feature changes
    """
    print("=" * 80)
    print("MODEL SENSITIVITY TEST")
    print("=" * 80)

    # Load model
    print("\n1. Loading model...")
    model, metadata = load_model()
    print(f"   Model type: {type(model).__name__}")
    print(f"   Features expected: {len(FEATURE_NAMES)}")

    # Get a real lap from database
    print("\n2. Loading real lap features from database...")
    lap_id = 32605  # Barber lap from logs
    try:
        real_features = get_lap_features(lap_id)
        print(f"   ✓ Loaded lap {lap_id}")
        print(f"   Features shape: {real_features.shape}")
    except Exception as e:
        print(f"   ✗ Could not load lap: {e}")
        print("   Creating synthetic features instead...")

        # Create synthetic baseline features
        real_features = pd.Series({
            'air_temp': 25.0,
            'track_temp': 35.0,
            'humidity': 50.0,
            'wind_speed': 5.0,
            'temp_delta': 10.0,
            'avg_brake_front': 6.0,
            'max_brake_front': 100.0,
            'avg_brake_rear': 3.0,
            'max_brake_rear': 50.0,
            'avg_lateral_g': 0.8,
            'max_lateral_g': 1.2,
            'avg_long_g': 0.3,
            'max_accel_g': 0.5,
            'max_brake_g': -1.5,
            'steering_variance': 40.0,
            'avg_steering_angle': 10.0,
            'avg_throttle_blade': 50.0,
            'avg_speed': 130.0,
            'max_speed': 190.0,
            'min_speed': 60.0,
            'avg_rpm': 5000.0,
            'max_rpm': 7000.0,
            'lap_in_stint': 5
        })

    # Test 1: Baseline prediction
    print("\n3. Testing baseline prediction...")
    baseline_df = pd.DataFrame([real_features])
    baseline_pred = predict_degradation(baseline_df)[0]
    print(f"   Baseline prediction: {baseline_pred:.6f} sec/lap")

    # Test 2: Extreme changes to brake pressure (+100%)
    print("\n4. Testing EXTREME brake pressure increase (+100%)...")
    modified_brake = real_features.copy()
    modified_brake['avg_brake_front'] = real_features['avg_brake_front'] * 2.0  # +100%
    modified_brake['max_brake_front'] = real_features['max_brake_front'] * 2.0  # +100%
    modified_df = pd.DataFrame([modified_brake])
    extreme_brake_pred = predict_degradation(modified_df)[0]
    delta_brake = extreme_brake_pred - baseline_pred
    print(f"   Modified prediction: {extreme_brake_pred:.6f} sec/lap")
    print(f"   Delta: {delta_brake:+.6f} sec/lap ({delta_brake/baseline_pred*100:+.2f}%)")

    # Test 3: Extreme changes to speed (+50%)
    print("\n5. Testing EXTREME speed increase (+50%)...")
    modified_speed = real_features.copy()
    modified_speed['avg_speed'] = real_features['avg_speed'] * 1.5  # +50%
    modified_speed['max_speed'] = real_features['max_speed'] * 1.5  # +50%
    modified_df = pd.DataFrame([modified_speed])
    extreme_speed_pred = predict_degradation(modified_df)[0]
    delta_speed = extreme_speed_pred - baseline_pred
    print(f"   Modified prediction: {extreme_speed_pred:.6f} sec/lap")
    print(f"   Delta: {delta_speed:+.6f} sec/lap ({delta_speed/baseline_pred*100:+.2f}%)")

    # Test 4: Extreme changes to lateral G (+100%)
    print("\n6. Testing EXTREME lateral G increase (+100%)...")
    modified_lateral = real_features.copy()
    modified_lateral['avg_lateral_g'] = real_features['avg_lateral_g'] * 2.0  # +100%
    modified_lateral['max_lateral_g'] = real_features['max_lateral_g'] * 2.0  # +100%
    modified_df = pd.DataFrame([modified_lateral])
    extreme_lateral_pred = predict_degradation(modified_df)[0]
    delta_lateral = extreme_lateral_pred - baseline_pred
    print(f"   Modified prediction: {extreme_lateral_pred:.6f} sec/lap")
    print(f"   Delta: {delta_lateral:+.6f} sec/lap ({delta_lateral/baseline_pred*100:+.2f}%)")

    # Test 5: Zero out steering variance (perfect smoothness)
    print("\n7. Testing ZERO steering variance (perfect smooth driving)...")
    modified_steering = real_features.copy()
    modified_steering['steering_variance'] = 0.0  # Perfect smoothness
    modified_df = pd.DataFrame([modified_steering])
    zero_steering_pred = predict_degradation(modified_df)[0]
    delta_steering = zero_steering_pred - baseline_pred
    print(f"   Modified prediction: {zero_steering_pred:.6f} sec/lap")
    print(f"   Delta: {delta_steering:+.6f} sec/lap ({delta_steering/baseline_pred*100:+.2f}%)")

    # Test 6: All zeros (edge case)
    print("\n8. Testing ALL ZEROS (edge case)...")
    zero_features = pd.Series({feat: 0.0 for feat in FEATURE_NAMES})
    zero_df = pd.DataFrame([zero_features])
    zero_pred = predict_degradation(zero_df)[0]
    delta_zero = zero_pred - baseline_pred
    print(f"   Zero-input prediction: {zero_pred:.6f} sec/lap")
    print(f"   Delta: {delta_zero:+.6f} sec/lap")

    # Test 7: Random variations
    print("\n9. Testing 10 random variations (+/- 30% on all features)...")
    predictions = []
    for i in range(10):
        random_features = real_features.copy()
        for feat in FEATURE_NAMES:
            if feat != 'lap_in_stint':  # Don't randomize lap_in_stint
                noise = np.random.uniform(0.7, 1.3)  # +/- 30%
                random_features[feat] = real_features[feat] * noise
        random_df = pd.DataFrame([random_features])
        pred = predict_degradation(random_df)[0]
        predictions.append(pred)
        print(f"   Variation {i+1}: {pred:.6f} sec/lap")

    predictions_array = np.array(predictions)
    print(f"\n   Random variations stats:")
    print(f"   Min: {predictions_array.min():.6f}")
    print(f"   Max: {predictions_array.max():.6f}")
    print(f"   Mean: {predictions_array.mean():.6f}")
    print(f"   Std: {predictions_array.std():.6f}")
    print(f"   Range: {predictions_array.max() - predictions_array.min():.6f}")

    # Analysis
    print("\n" + "=" * 80)
    print("ANALYSIS")
    print("=" * 80)

    threshold = 0.001  # 1 millisecond
    all_deltas = [
        abs(delta_brake),
        abs(delta_speed),
        abs(delta_lateral),
        abs(delta_steering),
        predictions_array.std()
    ]

    if all(d < threshold for d in all_deltas):
        print("\n⚠️  MODEL IS NOT SENSITIVE TO INPUT CHANGES")
        print("   The model returns nearly identical predictions regardless of inputs.")
        print("\n   Possible causes:")
        print("   1. Model overfitted to training data mean")
        print("   2. Features have very low importance")
        print("   3. Training data had insufficient variation")
        print("   4. Model is predicting a constant value")
        print("\n   Recommended actions:")
        print("   - Check model training code")
        print("   - Verify training data has sufficient variation")
        print("   - Check feature importance rankings")
        print("   - Consider retraining with different hyperparameters")
    else:
        print("\n✓ MODEL IS RESPONSIVE TO INPUT CHANGES")
        print(f"   Observed variation range: {max(all_deltas):.6f} sec/lap")
        print("\n   The model is working correctly.")

    # Feature importance
    print("\n" + "=" * 80)
    print("FEATURE IMPORTANCE (Top 10)")
    print("=" * 80)

    if hasattr(model, 'feature_importances_'):
        importance_df = pd.DataFrame({
            'feature': FEATURE_NAMES,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)

        for i, row in importance_df.head(10).iterrows():
            print(f"   {row['feature']:25s}: {row['importance']:.6f}")

        # Check if any features dominate
        top_feature_importance = importance_df.iloc[0]['importance']
        if top_feature_importance > 0.5:
            print(f"\n   ⚠️  Top feature accounts for {top_feature_importance*100:.1f}% of importance")
            print("   Model may be overly reliant on a single feature.")
    else:
        print("   Model does not have feature_importances_ attribute")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_model_sensitivity()
