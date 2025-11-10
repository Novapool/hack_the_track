"""
Data Loader for Tire Whisperer Dashboard

Provides cached database query functions for loading racing data.
Uses Streamlit's caching to minimize database queries and improve performance.
"""

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from typing import Dict, List, Optional, Tuple


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
    connection_string = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    return create_engine(connection_string)


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
        l.lap_duration,
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
      AND l.lap_duration IS NOT NULL
    GROUP BY l.lap_id, l.lap_number, l.lap_duration, l.vehicle_id, v.car_number
    ORDER BY l.lap_duration ASC
    LIMIT %s;
    """

    engine = get_db_engine()
    df = pd.read_sql(query, engine, params=(track_name, limit))
    return df


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

    engine = get_db_engine()
    df = pd.read_sql(query, engine, params=(lap_id,))
    if df.empty:
        return None
    return df


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
    query = """
    SELECT
        -- Weather features
        COALESCE(wd.air_temp, 25.0) as air_temp,
        COALESCE(wd.track_temp, 30.0) as track_temp,
        COALESCE(wd.humidity, 50.0) as humidity,
        COALESCE(wd.wind_speed, 5.0) as wind_speed,
        COALESCE(wd.track_temp - wd.air_temp, 5.0) as temp_delta,

        -- Brake pressure features
        AVG(tr.pbrake_f) as avg_brake_front,
        MAX(tr.pbrake_f) as max_brake_front,
        AVG(tr.pbrake_r) as avg_brake_rear,
        MAX(tr.pbrake_r) as max_brake_rear,

        -- G-force features
        AVG(ABS(tr.accy_can)) as avg_lateral_g,
        MAX(ABS(tr.accy_can)) as max_lateral_g,
        AVG(tr.accx_can) as avg_long_g,
        MAX(tr.accx_can) as max_accel_g,
        MIN(tr.accx_can) as max_brake_g,

        -- Steering features
        STDDEV(tr.steering_angle) as steering_variance,
        AVG(ABS(tr.steering_angle)) as avg_steering_angle,

        -- Throttle features
        AVG(tr.ath) as avg_throttle_blade,

        -- Speed features
        AVG(tr.speed) as avg_speed,
        MAX(tr.speed) as max_speed,
        MIN(tr.speed) as min_speed,

        -- Engine features
        AVG(tr.nmot) as avg_rpm,
        MAX(tr.nmot) as max_rpm,

        -- Stint position (approximate from lap number)
        l.lap_number % 15 as lap_in_stint

    FROM laps l
    LEFT JOIN telemetry_readings tr ON l.lap_id = tr.lap_id
    LEFT JOIN sessions s ON l.session_id = s.session_id
    LEFT JOIN races r ON s.race_id = r.race_id
    LEFT JOIN weather_data wd ON r.race_id = wd.race_id
    WHERE l.lap_id = %s
    GROUP BY l.lap_id, l.lap_number, wd.air_temp, wd.track_temp, wd.humidity, wd.wind_speed;
    """

    engine = get_db_engine()
    df = pd.read_sql(query, engine, params=(lap_id,))
    if df.empty:
        return None
    return df.iloc[0]


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
    df = pd.read_sql(query, engine, params=(lap_id,))
    if df.empty:
        return {}
    return df.iloc[0].to_dict()
