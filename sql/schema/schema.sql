-- ================================================================
-- Toyota GR Cup Racing Database Schema
-- ================================================================
-- Database: gr_cup_racing
-- Purpose: Store and organize racing telemetry, lap timing, and results data
-- for machine learning analysis
-- ================================================================

-- Drop existing tables (in reverse dependency order)
DROP TABLE IF EXISTS championship_standings CASCADE;
DROP TABLE IF EXISTS weather_data CASCADE;
DROP TABLE IF EXISTS sector_analysis CASCADE;
DROP TABLE IF EXISTS race_results CASCADE;
DROP TABLE IF EXISTS telemetry_readings CASCADE;
DROP TABLE IF EXISTS laps CASCADE;
DROP TABLE IF EXISTS sessions CASCADE;
DROP TABLE IF EXISTS drivers CASCADE;
DROP TABLE IF EXISTS vehicles CASCADE;
DROP TABLE IF EXISTS races CASCADE;
DROP TABLE IF EXISTS tracks CASCADE;

-- ================================================================
-- DIMENSION TABLES (Lookup/Reference Tables)
-- ================================================================

-- Tracks: Racing circuits
CREATE TABLE tracks (
    track_id SERIAL PRIMARY KEY,
    track_name VARCHAR(100) NOT NULL UNIQUE,
    track_full_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tracks_name ON tracks(track_name);

-- Races: Individual race events at tracks
CREATE TABLE races (
    race_id SERIAL PRIMARY KEY,
    track_id INTEGER NOT NULL REFERENCES tracks(track_id),
    race_number INTEGER NOT NULL CHECK (race_number IN (1, 2)),
    meta_event VARCHAR(100) NOT NULL,
    meta_session VARCHAR(50) NOT NULL,
    race_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(track_id, race_number, meta_event)
);

CREATE INDEX idx_races_track ON races(track_id);
CREATE INDEX idx_races_date ON races(race_date);
CREATE INDEX idx_races_meta_event ON races(meta_event);

-- Vehicles: Individual race cars
CREATE TABLE vehicles (
    vehicle_id VARCHAR(50) PRIMARY KEY,
    chassis_number VARCHAR(10) NOT NULL,
    car_number INTEGER,
    manufacturer VARCHAR(100) DEFAULT 'Toyota Gazoo Racing',
    vehicle_class VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_vehicles_chassis ON vehicles(chassis_number);
CREATE INDEX idx_vehicles_car_number ON vehicles(car_number);

-- Drivers: Race drivers
CREATE TABLE drivers (
    driver_id SERIAL PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    full_name VARCHAR(255),
    country VARCHAR(100),
    team VARCHAR(255),
    participant_number INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(first_name, last_name, participant_number)
);

CREATE INDEX idx_drivers_name ON drivers(last_name, first_name);
CREATE INDEX idx_drivers_participant ON drivers(participant_number);

-- Sessions: Racing sessions within a race
CREATE TABLE sessions (
    session_id SERIAL PRIMARY KEY,
    race_id INTEGER NOT NULL REFERENCES races(race_id),
    meta_source VARCHAR(100),
    session_start_time TIMESTAMP,
    session_end_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sessions_race ON sessions(race_id);
CREATE INDEX idx_sessions_start_time ON sessions(session_start_time);

-- ================================================================
-- FACT TABLES (Transactional Data)
-- ================================================================

-- Laps: Individual lap data
CREATE TABLE laps (
    lap_id BIGSERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES sessions(session_id),
    vehicle_id VARCHAR(50) NOT NULL REFERENCES vehicles(vehicle_id),
    outing INTEGER,
    lap_number INTEGER,
    lap_start_time TIMESTAMP,
    lap_end_time TIMESTAMP,
    lap_duration DECIMAL(10, 4),
    lap_start_meta_time TIMESTAMP,
    lap_end_meta_time TIMESTAMP,
    lap_start_timestamp_ecu TIMESTAMP,
    lap_end_timestamp_ecu TIMESTAMP,
    is_valid_lap BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_laps_session ON laps(session_id);
CREATE INDEX idx_laps_vehicle ON laps(vehicle_id);
CREATE INDEX idx_laps_session_vehicle_lap ON laps(session_id, vehicle_id, lap_number);
CREATE INDEX idx_laps_start_time ON laps(lap_start_time);
CREATE INDEX idx_laps_duration ON laps(lap_duration) WHERE lap_duration IS NOT NULL;
CREATE INDEX idx_laps_valid ON laps(is_valid_lap);

-- Telemetry Readings: High-frequency sensor data (PIVOTED from EAV)
-- Note: This is the largest table - consider partitioning for production
CREATE TABLE telemetry_readings (
    telemetry_id BIGSERIAL PRIMARY KEY,
    lap_id BIGINT REFERENCES laps(lap_id),
    session_id INTEGER NOT NULL REFERENCES sessions(session_id),
    vehicle_id VARCHAR(50) NOT NULL REFERENCES vehicles(vehicle_id),
    timestamp_ecu TIMESTAMP,
    meta_time TIMESTAMP NOT NULL,
    outing INTEGER,
    -- Telemetry parameters
    speed DECIMAL(10, 4),              -- Vehicle speed (km/h)
    gear INTEGER,                       -- Current gear selection
    nmot DECIMAL(10, 2),               -- Engine RPM
    ath DECIMAL(10, 4),                -- Throttle blade position (%)
    aps DECIMAL(10, 4),                -- Accelerator pedal position (%)
    pbrake_f DECIMAL(10, 4),           -- Front brake pressure (bar)
    pbrake_r DECIMAL(10, 4),           -- Rear brake pressure (bar)
    accx_can DECIMAL(10, 6),           -- Forward/backward acceleration (G)
    accy_can DECIMAL(10, 6),           -- Lateral acceleration (G)
    steering_angle DECIMAL(10, 4),     -- Steering wheel angle (degrees)
    vbox_long_minutes DECIMAL(15, 10), -- GPS longitude
    vbox_lat_min DECIMAL(15, 10),      -- GPS latitude
    laptrigger_lapdist_dls DECIMAL(10, 4), -- Distance from start/finish (m)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Critical indexes for telemetry queries
CREATE INDEX idx_telemetry_session ON telemetry_readings(session_id);
CREATE INDEX idx_telemetry_vehicle ON telemetry_readings(vehicle_id);
CREATE INDEX idx_telemetry_lap ON telemetry_readings(lap_id);
CREATE INDEX idx_telemetry_meta_time ON telemetry_readings(meta_time);
CREATE INDEX idx_telemetry_lap_time ON telemetry_readings(lap_id, meta_time);
CREATE INDEX idx_telemetry_vehicle_time ON telemetry_readings(vehicle_id, meta_time);

-- Consider partitioning by meta_time for production:
-- ALTER TABLE telemetry_readings PARTITION BY RANGE (meta_time);

-- Race Results: Final race positions and statistics
CREATE TABLE race_results (
    result_id SERIAL PRIMARY KEY,
    race_id INTEGER NOT NULL REFERENCES races(race_id),
    driver_id INTEGER REFERENCES drivers(driver_id),
    vehicle_id VARCHAR(50) REFERENCES vehicles(vehicle_id),
    position INTEGER,
    car_number INTEGER,
    status VARCHAR(50),
    laps_completed INTEGER,
    total_time VARCHAR(50),
    gap_to_first VARCHAR(50),
    gap_to_previous VARCHAR(50),
    fastest_lap_number INTEGER,
    fastest_lap_time DECIMAL(10, 4),
    fastest_lap_kph DECIMAL(10, 4),
    class VARCHAR(50),
    division VARCHAR(50),
    vehicle_type VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_results_race ON race_results(race_id);
CREATE INDEX idx_results_driver ON race_results(driver_id);
CREATE INDEX idx_results_vehicle ON race_results(vehicle_id);
CREATE INDEX idx_results_position ON race_results(position);

-- Sector Analysis: Detailed sector timing data
CREATE TABLE sector_analysis (
    sector_id BIGSERIAL PRIMARY KEY,
    race_id INTEGER NOT NULL REFERENCES races(race_id),
    vehicle_id VARCHAR(50) REFERENCES vehicles(vehicle_id),
    driver_number INTEGER,
    car_number INTEGER,
    lap_number INTEGER,
    lap_time VARCHAR(50),
    lap_time_seconds DECIMAL(10, 4),
    crossing_finish_in_pit BOOLEAN,
    -- Sector times
    s1_time VARCHAR(50),
    s1_seconds DECIMAL(10, 4),
    s1_improvement VARCHAR(50),
    s2_time VARCHAR(50),
    s2_seconds DECIMAL(10, 4),
    s2_improvement VARCHAR(50),
    s3_time VARCHAR(50),
    s3_seconds DECIMAL(10, 4),
    s3_improvement VARCHAR(50),
    -- Intermediate times
    im1a_time DECIMAL(10, 4),
    im1a_elapsed DECIMAL(10, 4),
    im1_time DECIMAL(10, 4),
    im1_elapsed DECIMAL(10, 4),
    im2a_time DECIMAL(10, 4),
    im2a_elapsed DECIMAL(10, 4),
    im2_time DECIMAL(10, 4),
    im2_elapsed DECIMAL(10, 4),
    im3a_time DECIMAL(10, 4),
    im3a_elapsed DECIMAL(10, 4),
    fl_time DECIMAL(10, 4),
    fl_elapsed DECIMAL(10, 4),
    -- Additional data
    top_speed DECIMAL(10, 4),
    average_kph DECIMAL(10, 4),
    elapsed_time VARCHAR(50),
    elapsed_seconds DECIMAL(10, 4),
    flag_at_finish VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sector_race ON sector_analysis(race_id);
CREATE INDEX idx_sector_vehicle ON sector_analysis(vehicle_id);
CREATE INDEX idx_sector_lap ON sector_analysis(lap_number);
CREATE INDEX idx_sector_race_lap ON sector_analysis(race_id, lap_number);

-- Weather Data: Track conditions during race
CREATE TABLE weather_data (
    weather_id SERIAL PRIMARY KEY,
    race_id INTEGER NOT NULL REFERENCES races(race_id),
    timestamp TIMESTAMP,
    air_temp DECIMAL(10, 2),
    track_temp DECIMAL(10, 2),
    humidity DECIMAL(10, 2),
    pressure DECIMAL(10, 2),
    wind_speed DECIMAL(10, 2),
    wind_direction VARCHAR(50),
    conditions TEXT,
    raw_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_weather_race ON weather_data(race_id);
CREATE INDEX idx_weather_timestamp ON weather_data(timestamp);

-- Championship Standings: Season points and standings
CREATE TABLE championship_standings (
    standing_id SERIAL PRIMARY KEY,
    driver_id INTEGER NOT NULL REFERENCES drivers(driver_id),
    season_year INTEGER NOT NULL,
    position INTEGER,
    total_points INTEGER,
    participant_number INTEGER,
    race_results JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(driver_id, season_year)
);

CREATE INDEX idx_standings_season ON championship_standings(season_year);
CREATE INDEX idx_standings_position ON championship_standings(position);
CREATE INDEX idx_standings_driver ON championship_standings(driver_id);

-- ================================================================
-- MATERIALIZED VIEWS FOR ML WORKFLOWS
-- ================================================================

-- Aggregated lap statistics
CREATE MATERIALIZED VIEW mv_lap_statistics AS
SELECT
    l.lap_id,
    l.session_id,
    l.vehicle_id,
    l.lap_number,
    l.lap_duration,
    r.track_id,
    t.track_name,
    r.race_number,
    COUNT(tr.telemetry_id) as telemetry_points,
    AVG(tr.speed) as avg_speed,
    MAX(tr.speed) as max_speed,
    AVG(tr.nmot) as avg_rpm,
    MAX(tr.nmot) as max_rpm,
    AVG(tr.ath) as avg_throttle,
    AVG(tr.pbrake_f) as avg_front_brake,
    AVG(tr.pbrake_r) as avg_rear_brake,
    MAX(tr.accx_can) as max_accel_x,
    MAX(tr.accy_can) as max_accel_y,
    MIN(tr.accx_can) as max_decel_x
FROM laps l
JOIN sessions s ON l.session_id = s.session_id
JOIN races r ON s.race_id = r.race_id
JOIN tracks t ON r.track_id = t.track_id
LEFT JOIN telemetry_readings tr ON l.lap_id = tr.lap_id
WHERE l.is_valid_lap = TRUE
GROUP BY l.lap_id, l.session_id, l.vehicle_id, l.lap_number,
         l.lap_duration, r.track_id, t.track_name, r.race_number;

CREATE INDEX idx_mv_lap_stats_vehicle ON mv_lap_statistics(vehicle_id);
CREATE INDEX idx_mv_lap_stats_track ON mv_lap_statistics(track_id);
CREATE INDEX idx_mv_lap_stats_duration ON mv_lap_statistics(lap_duration);

-- ================================================================
-- HELPER FUNCTIONS
-- ================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply update triggers to tables with updated_at
CREATE TRIGGER update_tracks_updated_at BEFORE UPDATE ON tracks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_races_updated_at BEFORE UPDATE ON races
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_vehicles_updated_at BEFORE UPDATE ON vehicles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_drivers_updated_at BEFORE UPDATE ON drivers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_laps_updated_at BEFORE UPDATE ON laps
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_results_updated_at BEFORE UPDATE ON race_results
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sector_updated_at BEFORE UPDATE ON sector_analysis
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_weather_updated_at BEFORE UPDATE ON weather_data
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_standings_updated_at BEFORE UPDATE ON championship_standings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ================================================================
-- COMMENTS AND DOCUMENTATION
-- ================================================================

COMMENT ON TABLE tracks IS 'Racing circuit information';
COMMENT ON TABLE races IS 'Individual race events at specific tracks';
COMMENT ON TABLE vehicles IS 'Race cars with chassis and car numbers';
COMMENT ON TABLE drivers IS 'Driver information and team affiliations';
COMMENT ON TABLE sessions IS 'Racing sessions within a race event';
COMMENT ON TABLE laps IS 'Individual lap timing data with start/end times';
COMMENT ON TABLE telemetry_readings IS 'High-frequency sensor readings (pivoted from EAV format)';
COMMENT ON TABLE race_results IS 'Final race positions and results';
COMMENT ON TABLE sector_analysis IS 'Detailed sector and intermediate timing';
COMMENT ON TABLE weather_data IS 'Weather conditions during races';
COMMENT ON TABLE championship_standings IS 'Season championship points and standings';

COMMENT ON COLUMN laps.is_valid_lap IS 'False when lap_number = 32768 (known data issue)';
COMMENT ON COLUMN telemetry_readings.meta_time IS 'Reliable message received time';
COMMENT ON COLUMN telemetry_readings.timestamp_ecu IS 'ECU timestamp (may be inaccurate)';
COMMENT ON COLUMN vehicles.chassis_number IS 'Unique chassis identifier (e.g., 004 from GR86-004-78)';
COMMENT ON COLUMN vehicles.car_number IS 'Car number displayed on vehicle (may change, can be 0 if unassigned)';

-- ================================================================
-- INITIAL DATA GRANTS (adjust as needed)
-- ================================================================

-- Grant read-only access to ml_user (create this user separately)
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO ml_user;
-- GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO ml_user;

-- ================================================================
-- COMPLETION
-- ================================================================

-- Schema creation complete
SELECT 'Schema created successfully!' as status;
