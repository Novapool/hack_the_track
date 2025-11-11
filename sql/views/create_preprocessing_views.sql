-- SQL Views for Fast Data Retrieval
-- These views pre-compute common aggregations for faster querying

-- View 1: Lap-level aggression metrics
-- Use this view when you need quick access to aggression features
CREATE OR REPLACE VIEW lap_aggression_metrics AS
SELECT
    l.lap_id,
    s.race_id,
    l.session_id,
    l.vehicle_id,
    l.lap_number,
    EXTRACT(EPOCH FROM (l.lap_end_time - l.lap_start_time)) as lap_time_seconds,
    r.track_id,
    r.race_date,

    -- Weather conditions (matched to lap start time)
    w.air_temp,
    w.track_temp,
    w.humidity,
    w.wind_speed,
    (w.track_temp - w.air_temp) as temp_delta,

    -- Brake aggression
    AVG(tr.pbrake_f) as avg_brake_front,
    MAX(tr.pbrake_f) as max_brake_front,
    AVG(tr.pbrake_r) as avg_brake_rear,
    MAX(tr.pbrake_r) as max_brake_rear,

    -- Cornering aggression (lateral G's)
    AVG(ABS(tr.accy_can)) as avg_lateral_g,
    MAX(ABS(tr.accy_can)) as max_lateral_g,

    -- Acceleration aggression (longitudinal G's)
    AVG(ABS(tr.accx_can)) as avg_long_g,
    MAX(tr.accx_can) as max_accel_g,
    MIN(tr.accx_can) as max_brake_g,

    -- Steering smoothness (higher variance = more jerky)
    VARIANCE(tr.steering_angle) as steering_variance,
    AVG(ABS(tr.steering_angle)) as avg_steering_angle,

    -- Throttle aggression
    AVG(tr.aps) as avg_throttle_pos,
    MAX(tr.aps) as max_throttle_pos,
    VARIANCE(tr.aps) as throttle_variance,

    AVG(tr.ath) as avg_throttle_blade,

    -- Speed metrics
    AVG(tr.speed) as avg_speed,
    MAX(tr.speed) as max_speed,
    MIN(tr.speed) as min_speed,

    -- Engine usage
    AVG(tr.nmot) as avg_rpm,
    MAX(tr.nmot) as max_rpm

FROM laps l
JOIN sessions s ON l.session_id = s.session_id
JOIN telemetry_readings tr ON l.lap_id = tr.lap_id
JOIN races r ON s.race_id = r.race_id
LEFT JOIN LATERAL (
    SELECT air_temp, track_temp, humidity, wind_speed
    FROM weather_data w2
    WHERE w2.race_id = r.race_id
    ORDER BY ABS(EXTRACT(EPOCH FROM (w2.timestamp - l.lap_start_time)))
    LIMIT 1
) w ON true
WHERE l.is_valid_lap = true
  AND l.lap_number < 32768
  AND l.lap_number > 0
  AND l.lap_start_time IS NOT NULL
  AND l.lap_end_time IS NOT NULL
  AND EXTRACT(EPOCH FROM (l.lap_end_time - l.lap_start_time)) > 0
  AND EXTRACT(EPOCH FROM (l.lap_end_time - l.lap_start_time)) < 300  -- Exclude laps > 5 minutes
GROUP BY l.lap_id, s.race_id, l.session_id, l.vehicle_id, l.lap_number,
         l.lap_start_time, l.lap_end_time, r.track_id, r.race_date,
         w.air_temp, w.track_temp, w.humidity, w.wind_speed;

-- View 2: Stint progression with degradation indicators
-- Shows how lap times degrade over a stint
CREATE OR REPLACE VIEW stint_degradation AS
SELECT
    lam.*,
    ROW_NUMBER() OVER (
        PARTITION BY lam.vehicle_id, lam.race_id
        ORDER BY lam.lap_number
    ) as lap_in_stint,

    -- Lap time delta vs first lap (tire degradation indicator)
    lam.lap_time_seconds - FIRST_VALUE(lam.lap_time_seconds) OVER (
        PARTITION BY lam.vehicle_id, lam.race_id
        ORDER BY lam.lap_number
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) as lap_time_delta,

    -- Rolling 5-lap average degradation
    AVG(lam.lap_time_seconds) OVER (
        PARTITION BY lam.vehicle_id, lam.race_id
        ORDER BY lam.lap_number
        ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
    ) - FIRST_VALUE(lam.lap_time_seconds) OVER (
        PARTITION BY lam.vehicle_id, lam.race_id
        ORDER BY lam.lap_number
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) as rolling_5lap_degradation

FROM lap_aggression_metrics lam;

-- View 3: Vehicle aggression profile (summary across all laps)
-- Useful for comparing different vehicles' driving styles
CREATE OR REPLACE VIEW vehicle_aggression_profile AS
SELECT
    vehicle_id,
    COUNT(*) as total_laps,
    AVG(avg_brake_front) as avg_brake_front,
    AVG(max_lateral_g) as avg_max_lateral_g,
    AVG(steering_variance) as avg_steering_variance,
    AVG(throttle_variance) as avg_throttle_variance,
    AVG(avg_speed) as avg_speed,
    AVG(lap_time_seconds) as avg_lap_time
FROM lap_aggression_metrics
GROUP BY vehicle_id
ORDER BY vehicle_id;

-- Create indexes on the base view for faster queries
-- Note: Indexes on views are not directly supported, but the underlying tables are already indexed

COMMENT ON VIEW lap_aggression_metrics IS 'Pre-computed aggression metrics per lap for faster ML data retrieval';
COMMENT ON VIEW stint_degradation IS 'Lap progression and tire degradation indicators';
COMMENT ON VIEW vehicle_aggression_profile IS 'Average driving style profile per vehicle';
