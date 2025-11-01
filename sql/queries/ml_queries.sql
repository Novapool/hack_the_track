-- ================================================================
-- ML Query Examples for Toyota GR Cup Racing Database
-- ================================================================
-- Common SQL queries for machine learning workflows
-- ================================================================

-- ================================================================
-- 1. FASTEST LAPS ANALYSIS
-- ================================================================

-- Get top 100 fastest laps across all tracks with telemetry
SELECT
    l.lap_id,
    t.track_name,
    v.vehicle_id,
    v.chassis_number,
    v.car_number,
    l.lap_duration,
    l.lap_number,
    r.race_date,
    ls.avg_speed,
    ls.max_speed,
    ls.avg_throttle,
    ls.max_accel_x,
    ls.max_accel_y
FROM laps l
JOIN sessions s ON l.session_id = s.session_id
JOIN races r ON s.race_id = r.race_id
JOIN tracks t ON r.track_id = t.track_id
JOIN vehicles v ON l.vehicle_id = v.vehicle_id
LEFT JOIN mv_lap_statistics ls ON l.lap_id = ls.lap_id
WHERE l.is_valid_lap = TRUE
  AND l.lap_duration IS NOT NULL
ORDER BY l.lap_duration ASC
LIMIT 100;

-- ================================================================
-- 2. TELEMETRY DATA EXTRACTION
-- ================================================================

-- Get all telemetry for a specific vehicle at a specific track
SELECT
    tr.telemetry_id,
    tr.timestamp_ecu,
    tr.meta_time,
    l.lap_number,
    tr.speed,
    tr.gear,
    tr.nmot,
    tr.ath,
    tr.aps,
    tr.pbrake_f,
    tr.pbrake_r,
    tr.accx_can,
    tr.accy_can,
    tr.steering_angle,
    tr.vbox_long_minutes,
    tr.vbox_lat_min,
    tr.laptrigger_lapdist_dls
FROM telemetry_readings tr
JOIN laps l ON tr.lap_id = l.lap_id
JOIN sessions s ON l.session_id = s.session_id
JOIN races r ON s.race_id = r.race_id
JOIN tracks t ON r.track_id = t.track_id
WHERE tr.vehicle_id = 'GR86-002-2'  -- Replace with target vehicle
  AND t.track_name = 'COTA'          -- Replace with target track
  AND l.is_valid_lap = TRUE
ORDER BY tr.meta_time ASC;

-- ================================================================
-- 3. LAP TIME PREDICTION FEATURES
-- ================================================================

-- Extract features for lap time prediction model
SELECT
    l.lap_id,
    l.lap_duration as target_lap_time,
    t.track_name,
    v.chassis_number,
    v.car_number,
    r.race_number,
    l.lap_number,
    -- Telemetry aggregates
    AVG(tr.speed) as avg_speed,
    MAX(tr.speed) as max_speed,
    MIN(tr.speed) as min_speed,
    STDDEV(tr.speed) as std_speed,
    AVG(tr.nmot) as avg_rpm,
    MAX(tr.nmot) as max_rpm,
    AVG(tr.ath) as avg_throttle,
    AVG(tr.aps) as avg_pedal,
    AVG(tr.pbrake_f) as avg_front_brake,
    AVG(tr.pbrake_r) as avg_rear_brake,
    MAX(tr.pbrake_f) as max_front_brake,
    MAX(tr.pbrake_r) as max_rear_brake,
    AVG(tr.accx_can) as avg_accel_x,
    AVG(tr.accy_can) as avg_accel_y,
    MAX(tr.accx_can) as max_accel,
    MIN(tr.accx_can) as max_decel,
    MAX(ABS(tr.accy_can)) as max_lateral_g,
    STDDEV(tr.steering_angle) as std_steering,
    -- Count of data points
    COUNT(tr.telemetry_id) as telemetry_points
FROM laps l
JOIN sessions s ON l.session_id = s.session_id
JOIN races r ON s.race_id = r.race_id
JOIN tracks t ON r.track_id = t.track_id
JOIN vehicles v ON l.vehicle_id = v.vehicle_id
LEFT JOIN telemetry_readings tr ON l.lap_id = tr.lap_id
WHERE l.is_valid_lap = TRUE
  AND l.lap_duration IS NOT NULL
  AND l.lap_duration > 0
GROUP BY l.lap_id, l.lap_duration, t.track_name, v.chassis_number,
         v.car_number, r.race_number, l.lap_number
HAVING COUNT(tr.telemetry_id) > 100  -- Only laps with sufficient telemetry
ORDER BY l.lap_duration ASC;

-- ================================================================
-- 4. SECTOR TIME ANALYSIS
-- ================================================================

-- Compare sector times across laps
SELECT
    sa.sector_id,
    t.track_name,
    sa.car_number,
    sa.lap_number,
    sa.lap_time_seconds as total_lap_time,
    sa.s1_seconds,
    sa.s2_seconds,
    sa.s3_seconds,
    -- Calculate sector percentages
    ROUND(100.0 * sa.s1_seconds / NULLIF(sa.lap_time_seconds, 0), 2) as s1_pct,
    ROUND(100.0 * sa.s2_seconds / NULLIF(sa.lap_time_seconds, 0), 2) as s2_pct,
    ROUND(100.0 * sa.s3_seconds / NULLIF(sa.lap_time_seconds, 0), 2) as s3_pct,
    sa.top_speed,
    sa.average_kph,
    sa.flag_at_finish
FROM sector_analysis sa
JOIN races r ON sa.race_id = r.race_id
JOIN tracks t ON r.track_id = t.track_id
WHERE sa.lap_time_seconds IS NOT NULL
  AND sa.lap_time_seconds > 0
ORDER BY sa.lap_time_seconds ASC
LIMIT 100;

-- ================================================================
-- 5. VEHICLE PERFORMANCE COMPARISON
-- ================================================================

-- Compare average performance metrics across vehicles
SELECT
    v.vehicle_id,
    v.chassis_number,
    v.car_number,
    COUNT(DISTINCT l.lap_id) as total_laps,
    COUNT(DISTINCT CASE WHEN l.is_valid_lap THEN l.lap_id END) as valid_laps,
    ROUND(AVG(CASE WHEN l.is_valid_lap THEN l.lap_duration END), 3) as avg_lap_time,
    ROUND(MIN(CASE WHEN l.is_valid_lap THEN l.lap_duration END), 3) as best_lap_time,
    ROUND(STDDEV(CASE WHEN l.is_valid_lap THEN l.lap_duration END), 3) as lap_time_std,
    -- Telemetry aggregates
    ROUND(AVG(tr.speed), 2) as avg_speed,
    ROUND(MAX(tr.speed), 2) as max_speed,
    ROUND(AVG(tr.nmot), 2) as avg_rpm,
    ROUND(AVG(tr.ath), 2) as avg_throttle
FROM vehicles v
LEFT JOIN laps l ON v.vehicle_id = l.vehicle_id
LEFT JOIN telemetry_readings tr ON l.lap_id = tr.lap_id
GROUP BY v.vehicle_id, v.chassis_number, v.car_number
HAVING COUNT(DISTINCT l.lap_id) > 0
ORDER BY avg_lap_time ASC;

-- ================================================================
-- 6. TRACK-SPECIFIC CHARACTERISTICS
-- ================================================================

-- Analyze track characteristics from telemetry
SELECT
    t.track_name,
    COUNT(DISTINCT l.lap_id) as total_laps,
    ROUND(AVG(l.lap_duration), 2) as avg_lap_time,
    ROUND(MIN(l.lap_duration), 2) as fastest_lap,
    -- Speed analysis
    ROUND(AVG(tr.speed), 2) as avg_speed,
    ROUND(MAX(tr.speed), 2) as max_speed_recorded,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY tr.speed), 2) as speed_95th_percentile,
    -- G-force analysis
    ROUND(AVG(ABS(tr.accx_can)), 3) as avg_longitudinal_g,
    ROUND(AVG(ABS(tr.accy_can)), 3) as avg_lateral_g,
    ROUND(MAX(tr.accx_can), 3) as max_acceleration,
    ROUND(MIN(tr.accx_can), 3) as max_braking,
    -- Braking analysis
    ROUND(AVG(tr.pbrake_f), 2) as avg_front_brake,
    ROUND(MAX(tr.pbrake_f), 2) as max_front_brake
FROM tracks t
JOIN races r ON t.track_id = r.track_id
JOIN sessions s ON r.race_id = s.race_id
JOIN laps l ON s.session_id = l.session_id
LEFT JOIN telemetry_readings tr ON l.lap_id = tr.lap_id
WHERE l.is_valid_lap = TRUE
GROUP BY t.track_name
ORDER BY t.track_name;

-- ================================================================
-- 7. TIME SERIES DATA FOR SPECIFIC LAP
-- ================================================================

-- Get complete telemetry time series for a specific lap
-- (Use for detailed lap analysis or visualization)
SELECT
    tr.meta_time,
    tr.timestamp_ecu,
    tr.laptrigger_lapdist_dls as distance_from_start,
    tr.speed,
    tr.gear,
    tr.nmot as rpm,
    tr.ath as throttle_position,
    tr.aps as pedal_position,
    tr.pbrake_f as front_brake,
    tr.pbrake_r as rear_brake,
    tr.accx_can as accel_longitudinal,
    tr.accy_can as accel_lateral,
    tr.steering_angle,
    tr.vbox_long_minutes as longitude,
    tr.vbox_lat_min as latitude
FROM telemetry_readings tr
WHERE tr.lap_id = 12345  -- Replace with specific lap_id
ORDER BY tr.meta_time ASC;

-- ================================================================
-- 8. BRAKING ZONES DETECTION
-- ================================================================

-- Identify braking zones (significant brake pressure events)
SELECT
    t.track_name,
    l.lap_id,
    tr.meta_time,
    tr.laptrigger_lapdist_dls as distance,
    tr.speed as entry_speed,
    tr.pbrake_f as front_brake_pressure,
    LAG(tr.speed) OVER (PARTITION BY l.lap_id ORDER BY tr.meta_time) as previous_speed,
    tr.speed - LAG(tr.speed) OVER (PARTITION BY l.lap_id ORDER BY tr.meta_time) as speed_delta
FROM telemetry_readings tr
JOIN laps l ON tr.lap_id = l.lap_id
JOIN sessions s ON l.session_id = s.session_id
JOIN races r ON s.race_id = r.race_id
JOIN tracks t ON r.track_id = t.track_id
WHERE tr.pbrake_f > 50  -- Significant brake pressure
  AND l.is_valid_lap = TRUE
  AND t.track_name = 'COTA'  -- Replace with target track
ORDER BY tr.meta_time;

-- ================================================================
-- 9. DRIVER CONSISTENCY ANALYSIS
-- ================================================================

-- Analyze driver consistency across laps
SELECT
    v.vehicle_id,
    v.chassis_number,
    t.track_name,
    COUNT(l.lap_id) as laps_completed,
    ROUND(AVG(l.lap_duration), 3) as avg_lap_time,
    ROUND(STDDEV(l.lap_duration), 3) as lap_time_std_dev,
    ROUND(MIN(l.lap_duration), 3) as best_lap,
    ROUND(MAX(l.lap_duration), 3) as worst_lap,
    ROUND(MAX(l.lap_duration) - MIN(l.lap_duration), 3) as lap_time_range,
    -- Coefficient of variation (lower = more consistent)
    ROUND(100.0 * STDDEV(l.lap_duration) / AVG(l.lap_duration), 2) as cv_percent
FROM vehicles v
JOIN laps l ON v.vehicle_id = l.vehicle_id
JOIN sessions s ON l.session_id = s.session_id
JOIN races r ON s.race_id = r.race_id
JOIN tracks t ON r.track_id = t.track_id
WHERE l.is_valid_lap = TRUE
  AND l.lap_duration IS NOT NULL
GROUP BY v.vehicle_id, v.chassis_number, t.track_name
HAVING COUNT(l.lap_id) >= 5  -- At least 5 laps
ORDER BY cv_percent ASC;

-- ================================================================
-- 10. RACE PACE DEGRADATION
-- ================================================================

-- Analyze lap time degradation over race duration (tire wear, fuel load)
WITH lap_progression AS (
    SELECT
        l.lap_id,
        l.vehicle_id,
        v.chassis_number,
        t.track_name,
        r.race_number,
        l.lap_number,
        l.lap_duration,
        ROW_NUMBER() OVER (PARTITION BY l.vehicle_id, r.race_id ORDER BY l.lap_number) as lap_sequence
    FROM laps l
    JOIN sessions s ON l.session_id = s.session_id
    JOIN races r ON s.race_id = r.race_id
    JOIN tracks t ON r.track_id = t.track_id
    JOIN vehicles v ON l.vehicle_id = v.vehicle_id
    WHERE l.is_valid_lap = TRUE
      AND l.lap_duration IS NOT NULL
)
SELECT
    chassis_number,
    track_name,
    race_number,
    lap_number,
    lap_duration,
    lap_sequence,
    -- Moving average (3-lap window)
    ROUND(AVG(lap_duration) OVER (
        PARTITION BY vehicle_id, track_name, race_number
        ORDER BY lap_sequence
        ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING
    ), 3) as lap_time_3lap_avg,
    -- Compare to best lap
    ROUND(lap_duration - MIN(lap_duration) OVER (
        PARTITION BY vehicle_id, track_name, race_number
    ), 3) as delta_to_best
FROM lap_progression
ORDER BY chassis_number, track_name, race_number, lap_sequence;

-- ================================================================
-- 11. EXPORT DATA FOR ML TRAINING
-- ================================================================

-- Create a comprehensive dataset for ML model training
-- This query can be saved as a view or exported to CSV/Parquet
CREATE OR REPLACE VIEW v_ml_training_dataset AS
SELECT
    -- Identifiers
    l.lap_id,
    t.track_name,
    v.chassis_number,
    v.car_number,
    r.race_number,
    l.lap_number,
    -- Target variable
    l.lap_duration as target_lap_time,
    -- Features from telemetry
    AVG(tr.speed) as avg_speed,
    MAX(tr.speed) as max_speed,
    MIN(tr.speed) as min_speed,
    STDDEV(tr.speed) as std_speed,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY tr.speed) as median_speed,
    AVG(tr.nmot) as avg_rpm,
    MAX(tr.nmot) as max_rpm,
    AVG(tr.ath) as avg_throttle,
    MAX(tr.ath) as max_throttle,
    AVG(tr.aps) as avg_pedal,
    AVG(tr.pbrake_f) as avg_front_brake,
    MAX(tr.pbrake_f) as max_front_brake,
    AVG(tr.pbrake_r) as avg_rear_brake,
    MAX(tr.pbrake_r) as max_rear_brake,
    AVG(tr.accx_can) as avg_accel_x,
    MAX(tr.accx_can) as max_acceleration,
    MIN(tr.accx_can) as max_braking,
    STDDEV(tr.accx_can) as std_accel_x,
    AVG(ABS(tr.accy_can)) as avg_lateral_g,
    MAX(ABS(tr.accy_can)) as max_lateral_g,
    AVG(ABS(tr.steering_angle)) as avg_steering_input,
    STDDEV(tr.steering_angle) as std_steering,
    -- Data quality indicators
    COUNT(tr.telemetry_id) as telemetry_point_count,
    l.is_valid_lap
FROM laps l
JOIN sessions s ON l.session_id = s.session_id
JOIN races r ON s.race_id = r.race_id
JOIN tracks t ON r.track_id = t.track_id
JOIN vehicles v ON l.vehicle_id = v.vehicle_id
LEFT JOIN telemetry_readings tr ON l.lap_id = tr.lap_id
WHERE l.lap_duration IS NOT NULL
GROUP BY l.lap_id, t.track_name, v.chassis_number, v.car_number,
         r.race_number, l.lap_number, l.lap_duration, l.is_valid_lap;

-- Use the view:
-- SELECT * FROM v_ml_training_dataset WHERE is_valid_lap = TRUE;

-- ================================================================
-- 12. REFRESH MATERIALIZED VIEWS
-- ================================================================

-- Refresh materialized views for up-to-date statistics
REFRESH MATERIALIZED VIEW mv_lap_statistics;

-- ================================================================
-- END OF ML QUERIES
-- ================================================================
