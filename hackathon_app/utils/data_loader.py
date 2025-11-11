"""
Data Loader for Tire Whisperer Dashboard

Provides cached database query functions for loading racing data.
Uses Streamlit's caching to minimize database queries and improve performance.
"""

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from typing import Dict, List, Optional, Tuple
import traceback
from .logger import setup_logger, log_exception, log_data_operation


# Setup logger
logger = setup_logger("data_loader")

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'database': 'gr_cup_racing',
    'user': 'postgres',
    'password': 'password',
    'port': 5432
}


def get_db_engine():
    """
    Create a SQLAlchemy database engine.

    Returns:
        SQLAlchemy engine object
    """
    try:
        connection_string = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
        logger.debug(f"Creating DB engine for {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
        return create_engine(connection_string)
    except Exception as e:
        logger.error(f"Failed to create database engine: {str(e)}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        raise


@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_available_tracks() -> pd.DataFrame:
    """
    Get list of tracks with lap counts and GPS availability.

    Returns:
        DataFrame with columns: track_name, track_id, total_laps, laps_with_gps, gps_coverage_pct
    """
    query = """
    WITH track_laps AS (
        SELECT
            t.track_id,
            t.track_name,
            COUNT(DISTINCT l.lap_id) as total_laps,
            COUNT(DISTINCT CASE
                WHEN EXISTS (
                    SELECT 1 FROM telemetry_readings tr
                    WHERE tr.lap_id = l.lap_id
                    AND tr.vbox_lat_min IS NOT NULL
                    AND tr.vbox_long_minutes IS NOT NULL
                ) THEN l.lap_id
            END) as laps_with_gps
        FROM tracks t
        LEFT JOIN races r ON r.track_id = t.track_id
        LEFT JOIN sessions s ON s.race_id = r.race_id
        LEFT JOIN laps l ON l.session_id = s.session_id
        WHERE l.lap_number < 32768  -- Filter erroneous laps
        GROUP BY t.track_id, t.track_name
    )
    SELECT
        track_name,
        track_id,
        total_laps,
        laps_with_gps,
        ROUND((laps_with_gps::NUMERIC / NULLIF(total_laps, 0) * 100), 1) as gps_coverage_pct
    FROM track_laps
    ORDER BY track_name;
    """

    engine = get_db_engine()
    df = pd.read_sql(query, engine)
    return df


@st.cache_data(ttl=600)
def get_available_laps(track_name: str, limit: int = 100) -> pd.DataFrame:
    """
    Get available laps for a specific track with metadata.

    Args:
        track_name: Name of the track (e.g., 'barber', 'cota')
        limit: Maximum number of laps to return

    Returns:
        DataFrame with columns: lap_id, lap_number, lap_duration, vehicle_id, has_gps
    """
    query = """
    SELECT
        l.lap_id,
        l.lap_number,
        COALESCE(
            l.lap_duration,
            EXTRACT(EPOCH FROM (l.lap_end_time - l.lap_start_time))
        ) as lap_duration,
        l.vehicle_id,
        v.car_number,
        EXISTS (
            SELECT 1 FROM telemetry_readings tr
            WHERE tr.lap_id = l.lap_id
            AND tr.vbox_lat_min IS NOT NULL
            LIMIT 1
        ) as has_gps,
        COUNT(tr.telemetry_id) as telemetry_count
    FROM laps l
    JOIN sessions s ON l.session_id = s.session_id
    JOIN races r ON s.race_id = r.race_id
    JOIN tracks t ON r.track_id = t.track_id
    LEFT JOIN vehicles v ON l.vehicle_id = v.vehicle_id
    LEFT JOIN telemetry_readings tr ON l.lap_id = tr.lap_id
    WHERE t.track_name = %s
      AND l.lap_number < 32768
      AND l.lap_number > 0
      AND l.lap_start_time IS NOT NULL
      AND l.lap_end_time IS NOT NULL
    GROUP BY l.lap_id, l.lap_number, l.lap_duration, l.lap_start_time, l.lap_end_time, l.vehicle_id, v.car_number
    HAVING COUNT(tr.telemetry_id) > 0
    ORDER BY l.lap_number ASC
    LIMIT %s;
    """

    try:
        engine = get_db_engine()
        df = pd.read_sql(query, engine, params=(track_name, limit))
        logger.info(f"Loaded {len(df)} laps for track '{track_name}'")
        return df
    except Exception as e:
        log_exception(logger, e, f"Error loading laps for track '{track_name}'")
        raise


@st.cache_data(ttl=600)
def load_lap_telemetry(lap_id: int) -> pd.DataFrame:
    """
    Load full telemetry data for a specific lap.

    Args:
        lap_id: Lap ID to load

    Returns:
        DataFrame with telemetry readings (meta_time, speed, brake, g-forces, etc.)
    """
    query = """
    SELECT
        meta_time,
        speed,
        pbrake_f,
        pbrake_r,
        accy_can,
        accx_can,
        steering_angle,
        aps,
        ath,
        gear,
        nmot,
        laptrigger_lapdist_dls,
        vbox_lat_min,
        vbox_long_minutes
    FROM telemetry_readings
    WHERE lap_id = %s
    ORDER BY meta_time;
    """

    engine = get_db_engine()
    # Convert numpy.int64 to Python int (psycopg2 compatibility)
    lap_id = int(lap_id)
    df = pd.read_sql(query, engine, params=(lap_id,))
    return df


@st.cache_data(ttl=600)
def load_lap_gps(lap_id: int) -> Optional[pd.DataFrame]:
    """
    Load GPS coordinates for a specific lap.

    Args:
        lap_id: Lap ID to load

    Returns:
        DataFrame with columns: latitude, longitude, speed (or None if no GPS data)
    """
    log_data_operation(logger, "load_lap_gps", lap_id=lap_id)

    query = """
    SELECT
        vbox_lat_min as latitude,
        vbox_long_minutes as longitude,
        speed,
        meta_time
    FROM telemetry_readings
    WHERE lap_id = %s
      AND vbox_lat_min IS NOT NULL
      AND vbox_long_minutes IS NOT NULL
    ORDER BY meta_time;
    """

    try:
        engine = get_db_engine()
        # Convert numpy.int64 to Python int (psycopg2 compatibility)
        lap_id = int(lap_id)
        df = pd.read_sql(query, engine, params=(lap_id,))

        if df.empty:
            logger.warning(f"No GPS data available for lap_id={lap_id}")
            return None

        logger.info(f"Loaded {len(df)} GPS points for lap_id={lap_id}")
        return df

    except Exception as e:
        log_exception(logger, e, f"Error loading GPS data for lap_id={lap_id}")
        raise


@st.cache_data(ttl=600)
def get_vehicle_stats(vehicle_id: int) -> Dict:
    """
    Get aggregated statistics for a vehicle (driver profile).

    Args:
        vehicle_id: Vehicle ID

    Returns:
        Dictionary with aggregated driving stats
    """
    query = """
    SELECT
        v.vehicle_id,
        v.car_number,
        v.chassis_number,
        COUNT(DISTINCT l.lap_id) as total_laps,
        AVG(l.lap_duration) as avg_lap_time,
        AVG(tr.pbrake_f) as avg_brake_front,
        MAX(tr.pbrake_f) as max_brake_front,
        AVG(tr.accy_can) as avg_lateral_g,
        MAX(tr.accy_can) as max_lateral_g,
        AVG(tr.speed) as avg_speed,
        MAX(tr.speed) as max_speed,
        STDDEV(tr.steering_angle) as steering_variance
    FROM vehicles v
    LEFT JOIN laps l ON v.vehicle_id = l.vehicle_id
    LEFT JOIN telemetry_readings tr ON l.lap_id = tr.lap_id
    WHERE v.vehicle_id = %s
      AND l.lap_number < 32768
    GROUP BY v.vehicle_id, v.car_number, v.chassis_number;
    """

    engine = get_db_engine()
    # Convert numpy.int64 to Python int (psycopg2 compatibility)
    vehicle_id = int(vehicle_id)
    df = pd.read_sql(query, engine, params=(vehicle_id,))
    if df.empty:
        return {}

    # Convert to dict and replace None values with defaults
    stats = df.iloc[0].to_dict()

    # Set default values for None entries to prevent formatting errors
    defaults = {
        'avg_lap_time': 0.0,
        'avg_brake_front': 0.0,
        'max_brake_front': 0.0,
        'avg_lateral_g': 0.0,
        'max_lateral_g': 0.0,
        'avg_speed': 0.0,
        'max_speed': 0.0,
        'steering_variance': 0.0
    }

    for key, default_value in defaults.items():
        if key in stats and stats[key] is None:
            stats[key] = default_value

    return stats


@st.cache_data(ttl=600)
def get_lap_features(lap_id: int) -> Optional[pd.Series]:
    """
    Get ML feature vector for a specific lap.

    Args:
        lap_id: Lap ID

    Returns:
        Series with 23 features ready for ML model prediction (or None if unavailable)
    """
    log_data_operation(logger, "get_lap_features", lap_id=lap_id)

    query = """
    SELECT
        -- Weather features (with defaults if no weather data)
        COALESCE(MAX(wd.air_temp), 25.0) as air_temp,
        COALESCE(MAX(wd.track_temp), 30.0) as track_temp,
        COALESCE(MAX(wd.humidity), 50.0) as humidity,
        COALESCE(MAX(wd.wind_speed), 5.0) as wind_speed,
        COALESCE(MAX(wd.track_temp) - MAX(wd.air_temp), 5.0) as temp_delta,

        -- Brake pressure features
        COALESCE(AVG(tr.pbrake_f), 0.0) as avg_brake_front,
        COALESCE(MAX(tr.pbrake_f), 0.0) as max_brake_front,
        COALESCE(AVG(tr.pbrake_r), 0.0) as avg_brake_rear,
        COALESCE(MAX(tr.pbrake_r), 0.0) as max_brake_rear,

        -- G-force features
        COALESCE(AVG(ABS(tr.accy_can)), 0.0) as avg_lateral_g,
        COALESCE(MAX(ABS(tr.accy_can)), 0.0) as max_lateral_g,
        COALESCE(AVG(tr.accx_can), 0.0) as avg_long_g,
        COALESCE(MAX(tr.accx_can), 0.0) as max_accel_g,
        COALESCE(MIN(tr.accx_can), 0.0) as max_brake_g,

        -- Steering features
        COALESCE(STDDEV(tr.steering_angle), 0.0) as steering_variance,
        COALESCE(AVG(ABS(tr.steering_angle)), 0.0) as avg_steering_angle,

        -- Throttle features
        COALESCE(AVG(tr.ath), 0.0) as avg_throttle_blade,

        -- Speed features
        COALESCE(AVG(tr.speed), 0.0) as avg_speed,
        COALESCE(MAX(tr.speed), 0.0) as max_speed,
        COALESCE(MIN(tr.speed), 0.0) as min_speed,

        -- Engine features
        COALESCE(AVG(tr.nmot), 0.0) as avg_rpm,
        COALESCE(MAX(tr.nmot), 0.0) as max_rpm,

        -- Stint position (approximate from lap number)
        l.lap_number %% 15 as lap_in_stint

    FROM laps l
    LEFT JOIN telemetry_readings tr ON l.lap_id = tr.lap_id
    LEFT JOIN sessions s ON l.session_id = s.session_id
    LEFT JOIN races r ON s.race_id = r.race_id
    LEFT JOIN weather_data wd ON r.race_id = wd.race_id
    WHERE l.lap_id = %s
    GROUP BY l.lap_id, l.lap_number;
    """

    try:
        engine = get_db_engine()
        # Convert numpy.int64 to Python int (psycopg2 compatibility)
        lap_id = int(lap_id)
        # Query uses lap_id once
        df = pd.read_sql(query, engine, params=(lap_id,))

        logger.debug(f"Query returned {len(df)} rows for lap_id={lap_id}")

        # Validate query results
        if df.empty or len(df) == 0:
            logger.warning(f"No data returned for lap_id={lap_id}")
            return None

        logger.debug(f"DataFrame shape: {df.shape}, columns: {df.columns.tolist()}")
        logger.debug(f"DataFrame dtypes: {df.dtypes.to_dict()}")

        # Access first row safely
        try:
            result = df.iloc[0]
            logger.debug(f"Successfully accessed first row, type: {type(result)}")
        except IndexError as e:
            logger.error(f"IndexError accessing first row: {str(e)}")
            logger.error(f"DataFrame info: shape={df.shape}, empty={df.empty}")
            return None

        # Check if result is a tuple (invalid) or has too many null values
        if isinstance(result, tuple):
            logger.error(f"Result is a tuple (expected pd.Series): {result}")
            return None

        # Check if most features are null (indicates bad data)
        null_count = result.isnull().sum()
        total_count = len(result)
        null_percentage = null_count / total_count if total_count > 0 else 0

        logger.debug(f"Null values: {null_count}/{total_count} ({null_percentage:.1%})")

        if null_percentage > 0.5:  # More than 50% null
            logger.warning(f"Too many null values ({null_percentage:.1%}) for lap_id={lap_id}")
            logger.debug(f"Null columns: {result[result.isnull()].index.tolist()}")
            return None

        logger.info(f"Successfully loaded {total_count} features for lap_id={lap_id}")
        return result

    except SQLAlchemyError as e:
        log_exception(logger, e, f"Database error while loading features for lap_id={lap_id}")
        raise
    except Exception as e:
        log_exception(logger, e, f"Unexpected error while loading features for lap_id={lap_id}")
        raise


@st.cache_data(ttl=600)
def get_all_vehicles() -> pd.DataFrame:
    """
    Get list of all vehicles with basic stats.

    Returns:
        DataFrame with vehicle info and lap counts
    """
    query = """
    SELECT
        v.vehicle_id,
        v.car_number,
        v.chassis_number,
        COUNT(DISTINCT l.lap_id) as total_laps
    FROM vehicles v
    LEFT JOIN laps l ON v.vehicle_id = l.vehicle_id
    WHERE l.lap_number < 32768
    GROUP BY v.vehicle_id, v.car_number, v.chassis_number
    HAVING COUNT(DISTINCT l.lap_id) > 0
    ORDER BY v.car_number;
    """

    engine = get_db_engine()
    df = pd.read_sql(query, engine)
    return df


@st.cache_data(ttl=600)
def get_lap_metadata(lap_id: int) -> Dict:
    """
    Get metadata for a specific lap (track, session, vehicle info).

    Args:
        lap_id: Lap ID

    Returns:
        Dictionary with lap metadata
    """
    query = """
    SELECT
        l.lap_id,
        l.lap_number,
        l.lap_duration,
        l.vehicle_id,
        v.car_number,
        t.track_name,
        t.track_id,
        s.session_id,
        r.race_id,
        r.race_date
    FROM laps l
    JOIN sessions s ON l.session_id = s.session_id
    JOIN races r ON s.race_id = r.race_id
    JOIN tracks t ON r.track_id = t.track_id
    LEFT JOIN vehicles v ON l.vehicle_id = v.vehicle_id
    WHERE l.lap_id = %s;
    """

    engine = get_db_engine()
    # Convert numpy.int64 to Python int (psycopg2 compatibility)
    lap_id = int(lap_id)
    df = pd.read_sql(query, engine, params=(lap_id,))
    if df.empty:
        return {}
    return df.iloc[0].to_dict()


@st.cache_data(ttl=600)
def get_representative_laps(track_name: str) -> pd.DataFrame:
    """
    Get representative laps for a track (fast, average, slow).

    Returns 3 representative laps per track:
    - Fast lap: Median of fastest 10% of laps
    - Average lap: Median lap time
    - Slow lap: Median of slowest 10% of laps

    Args:
        track_name: Name of the track (e.g., 'barber', 'cota')

    Returns:
        DataFrame with columns: lap_type, lap_id, lap_number, lap_duration, vehicle_id, car_number
    """
    log_data_operation(logger, "get_representative_laps", track_name=track_name)

    query = """
    WITH lap_times AS (
        SELECT
            l.lap_id,
            l.lap_number,
            COALESCE(
                l.lap_duration,
                EXTRACT(EPOCH FROM (l.lap_end_time - l.lap_start_time))
            ) as lap_duration,
            l.vehicle_id,
            v.car_number,
            NTILE(10) OVER (ORDER BY COALESCE(
                l.lap_duration,
                EXTRACT(EPOCH FROM (l.lap_end_time - l.lap_start_time))
            )) as decile
        FROM laps l
        JOIN sessions s ON l.session_id = s.session_id
        JOIN races r ON s.race_id = r.race_id
        JOIN tracks t ON r.track_id = t.track_id
        LEFT JOIN vehicles v ON l.vehicle_id = v.vehicle_id
        WHERE t.track_name = %s
          AND l.lap_number < 32768
          AND l.lap_number > 0
          AND l.lap_start_time IS NOT NULL
          AND l.lap_end_time IS NOT NULL
          AND COALESCE(
              l.lap_duration,
              EXTRACT(EPOCH FROM (l.lap_end_time - l.lap_start_time))
          ) > 0
    ),
    representative AS (
        SELECT
            'Fast Lap' as lap_type,
            1 as sort_order,
            lap_id,
            lap_number,
            lap_duration,
            vehicle_id,
            car_number,
            ROW_NUMBER() OVER (PARTITION BY decile ORDER BY lap_duration) as rn
        FROM lap_times
        WHERE decile = 1  -- Fastest 10%
        UNION ALL
        SELECT
            'Average Lap' as lap_type,
            2 as sort_order,
            lap_id,
            lap_number,
            lap_duration,
            vehicle_id,
            car_number,
            ROW_NUMBER() OVER (PARTITION BY decile ORDER BY lap_duration) as rn
        FROM lap_times
        WHERE decile = 5  -- Middle 50%
        UNION ALL
        SELECT
            'Slow Lap' as lap_type,
            3 as sort_order,
            lap_id,
            lap_number,
            lap_duration,
            vehicle_id,
            car_number,
            ROW_NUMBER() OVER (PARTITION BY decile ORDER BY lap_duration) as rn
        FROM lap_times
        WHERE decile = 9  -- Slowest 10-20%
    )
    SELECT
        lap_type,
        lap_id,
        lap_number,
        lap_duration,
        vehicle_id,
        car_number
    FROM representative
    WHERE rn = 1  -- Get median lap from each decile
    ORDER BY sort_order;
    """

    try:
        engine = get_db_engine()
        df = pd.read_sql(query, engine, params=(track_name,))

        if df.empty:
            logger.warning(f"No representative laps found for track '{track_name}'")
            return pd.DataFrame()

        logger.info(f"Loaded {len(df)} representative laps for track '{track_name}'")
        return df

    except Exception as e:
        log_exception(logger, e, f"Error loading representative laps for track '{track_name}'")
        raise


@st.cache_data(ttl=600)
def get_gps_availability(track_name: str) -> Dict:
    """
    Get GPS availability statistics for a track.

    Args:
        track_name: Name of the track

    Returns:
        Dictionary with total_laps, laps_with_gps, gps_coverage_pct
    """
    query = """
    SELECT
        COUNT(DISTINCT l.lap_id) as total_laps,
        COUNT(DISTINCT CASE WHEN EXISTS (
            SELECT 1 FROM telemetry_readings tr
            WHERE tr.lap_id = l.lap_id
            AND tr.vbox_lat_min IS NOT NULL
            LIMIT 1
        ) THEN l.lap_id END) as laps_with_gps
    FROM laps l
    JOIN sessions s ON l.session_id = s.session_id
    JOIN races r ON s.race_id = r.race_id
    JOIN tracks t ON r.track_id = t.track_id
    WHERE t.track_name = %s
      AND l.lap_number < 32768
      AND l.lap_number > 0;
    """

    try:
        engine = get_db_engine()
        df = pd.read_sql(query, engine, params=(track_name,))

        if df.empty:
            return {'total_laps': 0, 'laps_with_gps': 0, 'gps_coverage_pct': 0.0}

        result = df.iloc[0].to_dict()
        result['gps_coverage_pct'] = (
            (result['laps_with_gps'] / result['total_laps'] * 100)
            if result['total_laps'] > 0 else 0.0
        )

        return result

    except Exception as e:
        log_exception(logger, e, f"Error getting GPS availability for track '{track_name}'")
        return {'total_laps': 0, 'laps_with_gps': 0, 'gps_coverage_pct': 0.0}
