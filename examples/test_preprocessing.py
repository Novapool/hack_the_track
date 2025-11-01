"""
Quick test script to demonstrate the preprocessing pipeline.

This shows how to use the TireDegradationPreprocessor for loading and normalizing data.
"""

import sys
sys.path.insert(0, '..')  # Add parent directory to path

from src.data_preprocessing import TireDegradationPreprocessor
import pandas as pd

# Database configuration
db_config = {
    'host': 'localhost',
    'database': 'gr_cup_racing',
    'user': 'postgres',
    'password': ''
}

# Initialize preprocessor
print("Initializing preprocessor...")
preprocessor = TireDegradationPreprocessor(db_config)

# Example 1: Load raw data (just to see what we have)
print("\n" + "="*60)
print("Example 1: Loading raw data from SQL views")
print("="*60)

try:
    df_raw = preprocessor.get_aggression_features(
        outlier_threshold=3.0  # Remove data points beyond 3 std deviations
    )
    print(f"\nLoaded {len(df_raw)} laps from database")
    print(f"Date range: {df_raw['race_date'].min()} to {df_raw['race_date'].max()}")
    print(f"Number of vehicles: {df_raw['vehicle_id'].nunique()}")
    print(f"Number of races: {df_raw['race_id'].nunique()}")

    print("\nSample data (first 3 rows):")
    print(df_raw.head(3).to_string())

    print("\nFeature columns available:")
    feature_cols = [c for c in df_raw.columns if c not in [
        'lap_id', 'race_id', 'session_id', 'vehicle_id', 'track_id', 'race_date', 'lap_number'
    ]]
    for col in feature_cols:
        print(f"  - {col}")

except Exception as e:
    print(f"Error loading data: {e}")

# Example 2: Full preprocessing pipeline
print("\n" + "="*60)
print("Example 2: Full preprocessing for ML training")
print("="*60)

try:
    X, y = preprocessor.prepare_training_data(
        normalization_method='standard',  # Z-score normalization
        outlier_threshold=3.0,
        degradation_window=5  # 5-lap rolling window for degradation
    )

    print(f"\nTraining data shape:")
    print(f"  Features (X): {X.shape}")
    print(f"  Target (y): {y.shape}")

    print(f"\nFeature statistics (normalized):")
    print(X.describe().to_string())

    print(f"\nTarget statistics (tire degradation rate in seconds):")
    print(y.describe())

    # Save for later use
    print("\nSaving preprocessed data...")
    X.to_csv('../ml_data/features_normalized.csv', index=False)
    y.to_csv('../ml_data/target_degradation.csv', index=False)
    print("  ✓ ml_data/features_normalized.csv")
    print("  ✓ ml_data/target_degradation.csv")

except Exception as e:
    print(f"Error in preprocessing pipeline: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("Preprocessing test complete!")
print("="*60)
