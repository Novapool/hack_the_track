"""
Quick training script to compare model performance with weather features
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import xgboost as xgb

print("=" * 80)
print("TIRE DEGRADATION MODEL TRAINING - WITH WEATHER FEATURES")
print("=" * 80)

# Load data with weather features
print("\n1. Loading data with weather features...")
X = pd.read_csv('ml_data/features_with_weather.csv')
y = pd.read_csv('ml_data/target_with_weather.csv')['tire_degradation_rate']

# Drop columns with all NaN values
nan_features = X.columns[X.isnull().all()].tolist()
if nan_features:
    print(f"   Removing {len(nan_features)} features with all NaN: {nan_features}")
    X = X.drop(columns=nan_features)

print(f"   Features shape: {X.shape}")
print(f"   Target shape: {y.shape}")
print(f"   Features: {list(X.columns)}")

# Train/test split
print("\n2. Splitting data (80/20)...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)
print(f"   Training: {X_train.shape[0]} samples")
print(f"   Test: {X_test.shape[0]} samples")

# Train Random Forest (best model from baseline)
print("\n3. Training Random Forest...")
rf_model = RandomForestRegressor(
    n_estimators=100,
    max_depth=15,
    min_samples_split=5,
    random_state=42,
    n_jobs=-1
)
rf_model.fit(X_train, y_train)

# Evaluate
y_pred = rf_model.predict(X_test)
rf_r2 = r2_score(y_test, y_pred)
rf_mae = mean_absolute_error(y_test, y_pred)
rf_rmse = np.sqrt(mean_squared_error(y_test, y_pred))

# Cross-validation
cv_scores = cross_val_score(rf_model, X_train, y_train, cv=5, scoring='r2', n_jobs=-1)

print("\n" + "=" * 80)
print("RESULTS - Random Forest with Weather Features")
print("=" * 80)
print(f"Test R²:       {rf_r2:.4f}")
print(f"Test MAE:      {rf_mae:.4f} seconds/lap")
print(f"Test RMSE:     {rf_rmse:.4f} seconds/lap")
print(f"CV R² (5-fold): {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

print("\n" + "=" * 80)
print("COMPARISON WITH BASELINE (without weather)")
print("=" * 80)
baseline_r2 = 0.4928
baseline_mae = 0.3889
baseline_rmse = 0.7437

print(f"\nBaseline (no weather):")
print(f"  R²:   {baseline_r2:.4f}")
print(f"  MAE:  {baseline_mae:.4f}")
print(f"  RMSE: {baseline_rmse:.4f}")

print(f"\nWith Weather Features:")
print(f"  R²:   {rf_r2:.4f}  ({'+' if rf_r2 > baseline_r2 else ''}{rf_r2 - baseline_r2:.4f}, {(rf_r2 - baseline_r2)/baseline_r2*100:+.2f}%)")
print(f"  MAE:  {rf_mae:.4f}  ({'+' if rf_mae > baseline_mae else ''}{rf_mae - baseline_mae:.4f}, {(rf_mae - baseline_mae)/baseline_mae*100:+.2f}%)")
print(f"  RMSE: {rf_rmse:.4f}  ({'+' if rf_rmse > baseline_rmse else ''}{rf_rmse - baseline_rmse:.4f}, {(rf_rmse - baseline_rmse)/baseline_rmse*100:+.2f}%)")

# Feature importance for weather features
print("\n" + "=" * 80)
print("WEATHER FEATURE IMPORTANCE")
print("=" * 80)
feature_importance = pd.DataFrame({
    'feature': X.columns,
    'importance': rf_model.feature_importances_
}).sort_values('importance', ascending=False)

weather_features = ['air_temp', 'track_temp', 'humidity', 'wind_speed', 'temp_delta']
weather_importance = feature_importance[feature_importance['feature'].isin(weather_features)]

print("\nWeather features ranking:")
for idx, row in weather_importance.iterrows():
    rank = feature_importance.index.get_loc(idx) + 1
    print(f"  {rank:2d}. {row['feature']:15s}: {row['importance']:.4f}")

print("\nTop 10 overall features:")
print(feature_importance.head(10).to_string(index=False))

# Save updated metadata
print("\n" + "=" * 80)
print("SAVING MODEL")
print("=" * 80)

import joblib
models_dir = Path('models')
models_dir.mkdir(exist_ok=True)

model_path = models_dir / 'tire_degradation_model_random_forest_with_weather.pkl'
joblib.dump(rf_model, model_path)
print(f"Model saved: {model_path}")

metadata = {
    'best_model': 'Random Forest (with weather)',
    'best_test_r2': rf_r2,
    'best_test_mae': rf_mae,
    'best_test_rmse': rf_rmse,
    'training_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'training_samples': X_train.shape[0],
    'test_samples': X_test.shape[0],
    'features': list(X.columns),
    'weather_features': weather_features,
    'baseline_comparison': {
        'baseline_r2': baseline_r2,
        'r2_improvement': float(rf_r2 - baseline_r2),
        'r2_improvement_pct': float((rf_r2 - baseline_r2) / baseline_r2 * 100)
    }
}

metadata_path = models_dir / 'model_metadata_with_weather.json'
with open(metadata_path, 'w') as f:
    json.dump(metadata, f, indent=2)

print(f"Metadata saved: {metadata_path}")

print("\n" + "=" * 80)
print("✅ TRAINING COMPLETE!")
print("=" * 80)
