"""
Data Preprocessing Pipeline for Tire Degradation Model

This module provides a hybrid approach:
1. SQL layer: Efficient aggregation and filtering
2. Python layer: ML-specific normalization and feature engineering
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from sklearn.preprocessing import StandardScaler, MinMaxScaler
import psycopg2
from psycopg2.extras import RealDictCursor


class TireDegradationPreprocessor:
    """
    Preprocessor for tire degradation analysis.

    Features extracted:
    - Aggression metrics: brake pressure, lateral G's, steering angle variance
    - Speed metrics: corner entry/exit speeds, max speeds
    - Lap degradation: lap time progression over stint
    """

    def __init__(self, db_config: Dict[str, str]):
        """
        Initialize preprocessor with database connection.

        Args:
            db_config: Dict with keys: host, database, user, password
        """
        self.db_config = db_config
        self.scalers = {
            'standard': StandardScaler(),
            'minmax': MinMaxScaler()
        }
        self.fitted = False

    def connect(self):
        """Create database connection."""
        return psycopg2.connect(
            host=self.db_config['host'],
            database=self.db_config['database'],
            user=self.db_config['user'],
            password=self.db_config.get('password', '')
        )

    def get_aggression_features(
        self,
        race_ids: Optional[List[int]] = None,
        outlier_threshold: float = 3.0,
        filter_erroneous_laps: bool = True
    ) -> pd.DataFrame:
        """
        Extract aggression features from telemetry data using SQL views.

        Uses the pre-computed 'stint_degradation' SQL view for fast data retrieval.

        Features include:
        - Brake aggression (front/rear pressure)
        - Cornering aggression (lateral G's)
        - Acceleration/braking metrics (longitudinal G's)
        - Steering smoothness (variance)
        - Throttle usage patterns
        - Speed metrics
        - Lap degradation indicators

        Data Quality Notes (from Hackathon 2025 documentation):
        - Lap counts sometimes show erroneous value of 32768 (filtered automatically)
        - ECU timestamps may be inaccurate (we use meta_time instead)
        - Vehicle IDs use chassis number for consistent tracking

        Args:
            race_ids: Optional list of race IDs to filter
            outlier_threshold: Z-score threshold for outlier removal
            filter_erroneous_laps: Remove laps with known erroneous lap numbers (default: True)

        Returns:
            DataFrame with aggression features per lap
        """
        # Use the pre-computed view for much faster queries!
        query = """
        SELECT * FROM stint_degradation
        WHERE 1=1
            {race_filter}
            {lap_filter}
        ORDER BY race_id, vehicle_id, lap_number;
        """

        race_filter = ""
        if race_ids:
            race_filter = f"AND race_id IN ({','.join(map(str, race_ids))})"

        # Filter erroneous lap numbers (known issue: lap #32768)
        lap_filter = ""
        if filter_erroneous_laps:
            lap_filter = "AND lap_number < 32768 AND lap_number >= 0"

        query = query.format(race_filter=race_filter, lap_filter=lap_filter)

        with self.connect() as conn:
            df = pd.read_sql_query(query, conn)

        if len(df) == 0:
            print("WARNING: No data loaded from database. Check race_ids filter.")
            return df

        # Remove outliers using Z-score method
        df = self._remove_outliers(df, threshold=outlier_threshold)

        # Data quality reporting
        print(f"\nData Quality Report:")
        print(f"  Total laps loaded: {len(df)}")
        print(f"  Unique vehicles: {df['vehicle_id'].nunique()}")
        print(f"  Date range: {df['race_date'].min()} to {df['race_date'].max()}")

        # Check for potential data issues
        if df['lap_time_seconds'].isna().sum() > 0:
            print(f"  ⚠ Warning: {df['lap_time_seconds'].isna().sum()} laps with missing lap times")

        # Check for null telemetry values
        null_cols = df.columns[df.isna().any()].tolist()
        if null_cols:
            print(f"  ⚠ Columns with null values: {', '.join(null_cols)}")

        return df

    def _remove_outliers(
        self,
        df: pd.DataFrame,
        threshold: float = 3.0,
        columns: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Remove outliers using Z-score method.

        Outliers can occur due to:
        - Sensor errors
        - Pit stops (extremely slow "lap times")
        - Data transmission issues
        - Track incidents (accidents, safety cars)

        Args:
            df: Input dataframe
            threshold: Z-score threshold (default: 3.0)
            columns: Columns to check for outliers (default: all numeric)

        Returns:
            DataFrame with outliers removed
        """
        if len(df) == 0:
            return df

        if columns is None:
            # Get all numeric columns except IDs and lap numbers
            columns = df.select_dtypes(include=[np.number]).columns
            columns = [c for c in columns if not c.endswith('_id') and c != 'lap_number' and c != 'lap_in_stint']

        initial_count = len(df)

        for col in columns:
            if col in df.columns and df[col].notna().sum() > 0:
                # Calculate z-scores
                mean = df[col].mean()
                std = df[col].std()

                if std > 0:  # Avoid division by zero
                    z_scores = np.abs((df[col] - mean) / std)
                    df = df[z_scores < threshold]

        removed_count = initial_count - len(df)
        if removed_count > 0:
            print(f"Outlier Removal: Removed {removed_count} rows ({removed_count/initial_count*100:.2f}%)")

        return df

    def normalize_features(
        self,
        df: pd.DataFrame,
        method: str = 'standard',
        fit: bool = True
    ) -> pd.DataFrame:
        """
        Normalize features for ML training.

        Args:
            df: DataFrame with features
            method: 'standard' (z-score) or 'minmax' (0-1 scaling)
            fit: Whether to fit the scaler (True for training, False for inference)

        Returns:
            DataFrame with normalized features
        """
        # Identify feature columns (exclude IDs, dates, categorical)
        feature_cols = df.select_dtypes(include=[np.number]).columns
        exclude_cols = [c for c in feature_cols if c.endswith('_id') or c in ['lap_number', 'lap_in_stint']]
        feature_cols = [c for c in feature_cols if c not in exclude_cols]

        df_normalized = df.copy()

        scaler = self.scalers[method]

        if fit:
            df_normalized[feature_cols] = scaler.fit_transform(df[feature_cols])
            self.fitted = True
        else:
            if not self.fitted:
                raise ValueError("Scaler must be fitted before transforming. Call with fit=True first.")
            df_normalized[feature_cols] = scaler.transform(df[feature_cols])

        return df_normalized

    def create_degradation_target(
        self,
        df: pd.DataFrame,
        window_size: int = 5
    ) -> pd.DataFrame:
        """
        Create target variable: lap time degradation over rolling window.

        Args:
            df: DataFrame with lap_time_seconds
            window_size: Number of laps to calculate degradation slope

        Returns:
            DataFrame with 'tire_degradation_rate' column
        """
        df = df.copy()

        # Calculate rolling average of lap time increase
        df['tire_degradation_rate'] = df.groupby(['vehicle_id', 'race_id'])['lap_time_delta'].transform(
            lambda x: x.rolling(window=window_size, min_periods=1).mean()
        )

        return df

    def prepare_training_data(
        self,
        race_ids: Optional[List[int]] = None,
        normalization_method: str = 'standard',
        outlier_threshold: float = 3.0,
        degradation_window: int = 5,
        drop_null_targets: bool = True
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        End-to-end pipeline: Load, preprocess, normalize data.

        Pipeline steps:
        1. Load from database (with data quality filters)
        2. Remove outliers (sensor errors, pit stops, etc.)
        3. Create degradation target variable
        4. Normalize features for ML
        5. Separate features (X) and target (y)

        Args:
            race_ids: Optional race IDs to filter
            normalization_method: 'standard' (Z-score) or 'minmax' (0-1 range)
            outlier_threshold: Z-score for outlier removal
            degradation_window: Window size for degradation calculation (laps)
            drop_null_targets: Drop rows where target is null (default: True)

        Returns:
            Tuple of (features_df, target_series)
        """
        print("="*60)
        print("TIRE DEGRADATION PREPROCESSING PIPELINE")
        print("="*60)

        print("\nStep 1: Loading data from database...")
        df = self.get_aggression_features(race_ids, outlier_threshold)

        if len(df) == 0:
            raise ValueError("No data loaded from database. Check filters and database connection.")

        print(f"\nStep 2: Creating degradation target (window={degradation_window} laps)...")
        df = self.create_degradation_target(df, window_size=degradation_window)

        # Drop rows where target is null (if requested)
        if drop_null_targets:
            initial_count = len(df)
            df = df.dropna(subset=['tire_degradation_rate'])
            dropped = initial_count - len(df)
            if dropped > 0:
                print(f"  Dropped {dropped} rows with null degradation targets")

        print(f"\nStep 3: Normalizing features using {normalization_method} method...")
        df_normalized = self.normalize_features(df, method=normalization_method, fit=True)

        # Separate features and target
        exclude_cols = [
            'tire_degradation_rate', 'lap_time_delta', 'lap_time_seconds',
            'lap_id', 'race_id', 'session_id', 'vehicle_id', 'track_id',
            'race_date', 'lap_number', 'rolling_5lap_degradation'
        ]
        feature_cols = [c for c in df_normalized.columns if c not in exclude_cols]

        X = df_normalized[feature_cols]
        y = df_normalized['tire_degradation_rate']

        print(f"\nStep 4: Pipeline Complete!")
        print(f"  Features (X): {X.shape}")
        print(f"  Target (y): {y.shape}")
        print(f"\n  Feature columns ({len(feature_cols)}):")
        for i, col in enumerate(feature_cols, 1):
            print(f"    {i:2d}. {col}")

        print("\n" + "="*60)

        return X, y


# Example usage
if __name__ == "__main__":
    # Database configuration
    db_config = {
        'host': 'localhost',
        'database': 'gr_cup_racing',
        'user': 'postgres',
        'password': ''
    }

    # Initialize preprocessor
    preprocessor = TireDegradationPreprocessor(db_config)

    # Load and preprocess data
    X, y = preprocessor.prepare_training_data(
        normalization_method='standard',  # Z-score normalization
        outlier_threshold=3.0,
        degradation_window=5
    )

    # Save preprocessed data for training
    X.to_csv('features_normalized.csv', index=False)
    y.to_csv('target_degradation.csv', index=False)

    print("\nData preprocessing complete!")
    print(f"Features saved to: features_normalized.csv")
    print(f"Target saved to: target_degradation.csv")
