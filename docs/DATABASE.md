# Toyota GR Cup Racing Database Guide

## Table of Contents
1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Database Schema](#database-schema)
4. [Table Reference](#table-reference)
5. [Views Reference](#views-reference)
6. [Data Quality](#data-quality)
7. [Querying Data for ML](#querying-data-for-ml)
8. [Performance Optimization](#performance-optimization)
9. [Troubleshooting](#troubleshooting)

---

## Overview

This database stores and organizes Toyota GR Cup racing data for machine learning analysis. The schema is designed to:

- **Normalize** repeated metadata into lookup tables
- **Pivot** telemetry data from EAV (Entity-Attribute-Value) to columnar format for fast queries
- **Preserve** original data integrity for reproducibility
- **Enable** efficient subset extraction for ML training
- **Support** data quality validation and outlier detection

### Database Statistics

- **Database Name**: `gr_cup_racing`
- **Total Size**: ~6.2 GB
- **Telemetry Rows**: 23,179,647 (23.1 million high-frequency sensor readings)
- **Total Laps**: 13,701 laps
  - **Valid Laps**: 9,549 (usable for analysis)
  - **ML-Ready Laps**: 3,737 (with complete telemetry + weather)
- **Tracks**: 7 (Barber, COTA, Indianapolis, Road America, Sebring, Sonoma, VIR)
- **Vehicles**: 65 race cars
- **Races**: 14 (2 per track)
- **Sessions**: 14
- **Weather Records**: 567

---

## Getting Started

### Prerequisites

1. **PostgreSQL 14+** installed and running
2. **Python 3.9+** with required packages
3. **Sufficient disk space** (10+ GB for current dataset)

### Quick Start

#### Connect to Database

**Command line:**
```bash
psql -h localhost -U postgres -d gr_cup_racing
```

**Python:**
```python
import psycopg2

conn = psycopg2.connect(
    host='localhost',
    database='gr_cup_racing',
    user='postgres',
    password='password'
)
```

**Environment variable (for scripts):**
```bash
export PGPASSWORD=password
psql -h localhost -U postgres -d gr_cup_racing -c "SELECT COUNT(*) FROM laps;"
```

#### Verify Installation

```sql
-- Check table counts
SELECT
  'tracks' as table_name, COUNT(*) as rows FROM tracks
UNION ALL
SELECT 'races', COUNT(*) FROM races
UNION ALL
SELECT 'sessions', COUNT(*) FROM sessions
UNION ALL
SELECT 'laps', COUNT(*) FROM laps
UNION ALL
SELECT 'vehicles', COUNT(*) FROM vehicles
UNION ALL
SELECT 'telemetry_readings', COUNT(*) FROM telemetry_readings
UNION ALL
SELECT 'weather_data', COUNT(*) FROM weather_data;
```

Expected output:
```
      table_name       | rows
-----------------------+----------
 tracks                | 7
 races                 | 14
 sessions              | 14
 laps                  | 13701
 vehicles              | 65
 telemetry_readings    | 23179647
 weather_data          | 567
```

---

## Database Schema

### Entity Relationship Diagram

```
tracks (7)
  ↓
races (14)
  ↓ ↘
sessions (14)  weather_data (567)
  ↓
laps (13,701) ← vehicles (65)
  ↓
telemetry_readings (23M)

Pre-computed Views (ML):
├─ lap_aggression_metrics (3,737)
├─ stint_degradation (3,737)
└─ vehicle_aggression_profile (64)
```

---

## Table Reference

### **tracks** - Racing Circuits

**Rows**: 7
**Purpose**: Circuit information
**Columns**:
- `track_id` (integer, PK) - Unique identifier
- `track_name` (varchar) - Short name (e.g., "COTA", "Sebring")
- `track_full_name` (varchar) - Full name (e.g., "Circuit of the Americas")
- `created_at`, `updated_at` (timestamp)

**NULL Patterns**: None (all fields populated)

**Sample Data**:
```sql
SELECT track_name, track_full_name FROM tracks ORDER BY track_name;
```
| track_name | track_full_name |
|------------|-----------------|
| COTA | Circuit of the Americas |
| Sebring | Sebring International Raceway |
| Sonoma | Sonoma Raceway |
| VIR | Virginia International Raceway |
| barber | Barber Motorsports Park |
| indianapolis | Indianapolis Motor Speedway |
| Road America | Road America |

---

### **races** - Race Events

**Rows**: 14 (2 per track)
**Purpose**: Individual race events at specific tracks
**Columns**:
- `race_id` (integer, PK)
- `track_id` (integer, FK → tracks)
- `race_number` (integer) - Usually 1 or 2
- `meta_event` (varchar)
- `meta_session` (varchar)
- `race_date` (date)
- `created_at`, `updated_at` (timestamp)

**NULL Patterns**: None (all critical fields populated)

**Track Distribution**:
```sql
SELECT t.track_name, COUNT(r.race_id) as race_count
FROM tracks t
LEFT JOIN races r ON t.track_id = r.track_id
GROUP BY t.track_name;
```

---

### **sessions** - Racing Sessions

**Rows**: 14 (1 per race)
**Purpose**: Racing sessions within each race event
**Columns**:
- `session_id` (integer, PK)
- `race_id` (integer, FK → races)
- `meta_source` (varchar)
- `session_start_time` (timestamp)
- `session_end_time` (timestamp)
- `created_at`, `updated_at` (timestamp)

**NULL Patterns**:
- `session_start_time`: 2 NULL (12 populated)
- `session_end_time`: **14 NULL** (never populated - can derive from lap data)

---

### **vehicles** - Race Cars

**Rows**: 65
**Purpose**: Race cars (Toyota GR86s)
**Format**: `vehicle_id` = "GR86-{chassis}-{car_number}"
**Columns**:
- `vehicle_id` (varchar, PK) - e.g., "GR86-049-88"
- `chassis_number` (varchar) - Unique chassis identifier (e.g., "049")
- `car_number` (varchar) - Racing number (e.g., "88")
- `manufacturer` (varchar) - "Toyota"
- `vehicle_class` (varchar) - "GR86"
- `created_at`, `updated_at` (timestamp)

**NULL Patterns**:
- `car_number`: 1 NULL (vehicle GR86-002-000 has no assigned number)

**Note**: Use `chassis_number` for consistent tracking across seasons (car numbers may change)

---

### **laps** - Lap Timing Data

**Rows**: 13,701 total
**Valid Laps** (lap_number < 32768): 10,864
**Laps with Timing Data**: 9,549
**Purpose**: Individual lap timing and metadata

**Columns**:
- `lap_id` (integer, PK)
- `session_id` (integer, FK → sessions)
- `vehicle_id` (varchar, FK → vehicles)
- `outing` (integer) - Session outing number
- `lap_number` (integer) - Lap count ⚠️ **32768 = erroneous**
- `lap_start_time` (timestamp)
- `lap_end_time` (timestamp)
- `lap_start_meta_time` (decimal)
- `lap_end_meta_time` (decimal)
- `lap_duration` (decimal) - ⚠️ **UNRELIABLE** (use calculated instead)
- `is_valid_lap` (boolean) - False when lap_number = 32768
- `created_at`, `updated_at` (timestamp)

**NULL Patterns**:
- `lap_start_time`: 305 NULL (2.2%)
- `lap_end_time`: 358 NULL (2.6%)
- `lap_duration`: 1,890 NULL (13.8%) ⚠️ **DO NOT USE - Calculate from timestamps**
- `lap_start_meta_time`: 305 NULL
- `lap_end_meta_time`: 358 NULL

**Critical Data Quality Notes**:
1. **Lap 32768 Issue**: 2,837 laps have `lap_number = 32768` due to ECU overflow
   - Filter: `WHERE lap_number < 32768 AND lap_number > 0`
   - These are marked with `is_valid_lap = false`
2. **lap_duration Unreliable**: Contains garbage values (45, 784369, etc.)
   - **Always calculate**: `EXTRACT(EPOCH FROM (lap_end_time - lap_start_time))`
   - Valid range: 80-200 seconds for most tracks

**Lap Distribution by Track**:
| Track | Valid Laps | % of Total |
|-------|------------|------------|
| Sonoma | 3,451 | 36.1% |
| COTA | 1,871 | 19.6% |
| VIR | 1,675 | 17.5% |
| Sebring | 1,464 | 15.3% |
| Indianapolis | 847 | 8.9% |
| Road America | 807 | 8.5% |
| Barber | 749 | 7.8% |

---

### **telemetry_readings** ⚡ LARGEST TABLE

**Rows**: 23,179,647 (23.1 million)
**Size**: 6.2 GB
**Purpose**: High-frequency sensor data (columnar format)

**Columns** (21 total):
- `telemetry_id` (integer, PK)
- `lap_id` (integer, FK → laps)
- `session_id` (integer, FK → sessions)
- `vehicle_id` (varchar, FK → vehicles)
- `meta_time` (decimal) - Message received time ✅ **Use this for timing**
- `timestamp_ecu` (decimal) - ECU timestamp ⚠️ **Unreliable**
- `speed` (decimal) - km/h
- `gear` (integer)
- `nmot` (decimal) - Engine RPM
- `aps` (decimal) - Throttle pedal position
- `ath` (decimal) - Throttle blade position
- `pbrake_f` (decimal) - Front brake pressure (bar)
- `pbrake_r` (decimal) - Rear brake pressure (bar)
- `accx_can` (decimal) - Longitudinal G-force (accel/brake)
- `accy_can` (decimal) - Lateral G-force (cornering)
- `steering_angle` (decimal) - Steering wheel angle
- `laptrigger_lapdist_dls` (decimal) - Distance from start/finish (m)
- `vbox_lat_min` (decimal) - GPS latitude
- `vbox_long_minutes` (decimal) - GPS longitude
- `created_at`, `updated_at` (timestamp)

**NULL Patterns** (critical for data quality):
- `lap_id`: 3,571,758 NULL (15.4%) - Telemetry without lap assignment
- `vbox_lat_min` (GPS): 16,517,207 NULL (71.2%) ⚠️ **Limited GPS coverage**
- `vbox_long_minutes` (GPS): 16,517,209 NULL (71.2%)
- `speed`: 18,548,799 NULL (80.0%) ⚠️ **Most telemetry missing speed**
- `pbrake_f`: 718,152 NULL (3.1%)
- `steering_angle`: ~5% NULL
- Other metrics: Generally < 5% NULL

**GPS Coverage**: Only 28.7% of telemetry has GPS data (6,662,440 / 23,179,647)

**Performance Notes**:
- Indexed on `lap_id`, `vehicle_id`, `meta_time`
- Queries can be slow on full table - use `WHERE lap_id = X` filters
- GPS-heavy queries benefit from `WHERE vbox_lat_min IS NOT NULL`

---

### **weather_data** - Weather Conditions

**Rows**: 567
**Purpose**: Weather conditions during races
**Columns**:
- `weather_id` (integer, PK)
- `race_id` (integer, FK → races)
- `timestamp` (timestamp)
- `air_temp` (decimal) - °C
- `track_temp` (decimal) - °C
- `humidity` (decimal) - %
- `pressure` (decimal) - hPa
- `wind_speed` (decimal) - m/s
- `wind_direction` (varchar)
- `conditions` (varchar) - Description
- `raw_data` (jsonb) - Original API response
- `created_at`, `updated_at` (timestamp)

**NULL Patterns**: **None** (all fields fully populated)

**Sample**:
```sql
SELECT air_temp, track_temp, humidity, wind_speed
FROM weather_data
LIMIT 3;
```
| air_temp | track_temp | humidity | wind_speed |
|----------|------------|----------|------------|
| 12.07 | 14.90 | 82.91 | 2.52 |
| 12.18 | 14.96 | 82.75 | 2.54 |
| 12.28 | 15.01 | 82.60 | 2.57 |

---

### **Additional Tables** (Reference)

#### **drivers** - 42 rows
Driver information, team affiliations, country

#### **race_results** - 317 rows
Final race positions and results

#### **sector_analysis** - 7,214 rows
Sector timing data (S1, S2, S3)

#### **championship_standings** - 39 rows
Season championship points

---

## Views Reference

### **lap_aggression_metrics**

**Rows**: 3,737
**Purpose**: Lap-level telemetry aggregations with weather data (ML features)
**Source**: Joins laps + telemetry_readings + races + weather_data

**Columns** (33 total):

**Metadata (8)**:
- `lap_id`, `race_id`, `session_id`, `vehicle_id`, `lap_number`
- `lap_time_seconds` - ✅ **Calculated from timestamps** (reliable)
- `track_id`, `race_date`

**Weather Features (5)**:
- `air_temp`, `track_temp`, `humidity`, `wind_speed`
- `temp_delta` - track_temp - air_temp

**Brake Features (4)**:
- `avg_brake_front`, `max_brake_front`
- `avg_brake_rear`, `max_brake_rear`

**G-Force Features (6)**:
- `avg_lateral_g`, `max_lateral_g` - Cornering aggression
- `avg_long_g`, `max_accel_g`, `max_brake_g` - Longitudinal forces

**Steering Features (2)**:
- `steering_variance` - Higher = more jerky (less smooth)
- `avg_steering_angle`

**Throttle Features (3)**:
- `avg_throttle_pos`, `max_throttle_pos`, `throttle_variance`
- `avg_throttle_blade`

**Speed Features (3)**:
- `avg_speed`, `max_speed`, `min_speed`

**Engine Features (2)**:
- `avg_rpm`, `max_rpm`

**Filters Applied**:
- `is_valid_lap = true`
- `lap_number < 32768 AND lap_number > 0`
- `lap_start_time IS NOT NULL AND lap_end_time IS NOT NULL`
- `lap_time_seconds > 0 AND lap_time_seconds < 300` (5 minutes)

**Usage**:
```sql
SELECT * FROM lap_aggression_metrics
WHERE track_id = 1
ORDER BY lap_time_seconds ASC
LIMIT 10;  -- Get 10 fastest laps at this track
```

---

### **stint_degradation**

**Rows**: 3,737 (same as lap_aggression_metrics)
**Purpose**: Extends lap_aggression_metrics with tire degradation indicators
**Primary ML View**: Use this for tire degradation model training

**Additional Columns** (beyond lap_aggression_metrics):

- `lap_in_stint` - Position in current stint (ROW_NUMBER per vehicle/race)
- `lap_time_delta` - Change from **first lap in stint** (seconds)
  - Negative = getting faster (tire warmup)
  - Positive = getting slower (tire degradation)
- `rolling_5lap_degradation` - Rolling 5-lap average delta

**Interpretation**:
- Laps 1-5: Usually **negative** (tires warming up, lap times improving)
- Laps 5-15: Usually **positive** (tires degrading, lap times increasing)
- Target variable for ML: `rolling_5lap_degradation` or `lap_time_delta`

**Usage**:
```sql
-- Get stint progression for a specific vehicle
SELECT lap_number, lap_time_seconds, lap_time_delta, rolling_5lap_degradation
FROM stint_degradation
WHERE vehicle_id = 'GR86-049-88' AND race_id = 1
ORDER BY lap_number;
```

---

### **vehicle_aggression_profile**

**Rows**: 64 (one per vehicle with laps)
**Purpose**: Summary statistics per vehicle (driving style profiling)

**Columns** (8)**:
- `vehicle_id`
- `total_laps` - Count of laps in lap_aggression_metrics
- `avg_brake_front`
- `avg_max_lateral_g`
- `avg_steering_variance`
- `avg_throttle_variance`
- `avg_speed`
- `avg_lap_time`

**Usage**:
```sql
-- Compare driving styles
SELECT vehicle_id, avg_steering_variance, avg_max_lateral_g, avg_lap_time
FROM vehicle_aggression_profile
ORDER BY avg_lap_time ASC
LIMIT 10;  -- Top 10 fastest vehicles
```

---

## Data Quality

### Summary

| Metric | Count | % of Total |
|--------|-------|------------|
| Total laps | 13,701 | 100% |
| Valid lap numbers | 10,864 | 79.3% |
| Laps with timing data | 9,549 | 69.7% |
| ML-ready laps (with telemetry + weather) | 3,737 | 27.3% |
| Telemetry points | 23,179,647 | 100% |
| Telemetry with GPS | 6,662,440 | 28.7% |
| Weather records | 567 | 100% (complete) |

### Known Issues

#### 1. Lap 32768 (ECU Overflow)
- **Affected**: 2,837 laps (20.7%)
- **Cause**: ECU lap counter overflow/reset
- **Handling**: Marked with `is_valid_lap = false`
- **Filter**: `WHERE lap_number < 32768 AND lap_number > 0`

#### 2. Unreliable lap_duration Column
- **Issue**: Contains garbage values (45, 784369 instead of ~100)
- **Solution**: **Never use lap_duration** - Always calculate:
  ```sql
  EXTRACT(EPOCH FROM (lap_end_time - lap_start_time)) as lap_time_seconds
  ```
- **Views**: lap_aggression_metrics and stint_degradation use calculated values

#### 3. Missing GPS Data
- **Coverage**: Only 28.7% of telemetry has GPS
- **Impact**: Limits track visualization to specific sessions
- **Check availability**:
  ```sql
  SELECT
    COUNT(*) as total_laps,
    COUNT(DISTINCT CASE WHEN EXISTS (
      SELECT 1 FROM telemetry_readings tr
      WHERE tr.lap_id = l.lap_id
      AND tr.vbox_lat_min IS NOT NULL
    ) THEN l.lap_id END) as laps_with_gps
  FROM laps l;
  ```

#### 4. Missing Speed Data
- **Coverage**: Only 20% of telemetry has speed values
- **Impact**: Telemetry charts incomplete
- **Workaround**: Other metrics (brake, throttle, RPM) have better coverage (95%+)

#### 5. Missing Lap Timing
- **Affected**: 663 laps (4.8%) missing lap_start_time or lap_end_time
- **Impact**: Cannot calculate lap duration
- **Handling**: Excluded from ML views automatically

### Data Validation Queries

```sql
-- Check for erroneous lap numbers
SELECT COUNT(*) FROM laps WHERE lap_number >= 32768;
-- Expected: 2,837

-- Check laps with missing timing
SELECT COUNT(*) FROM laps
WHERE lap_start_time IS NULL OR lap_end_time IS NULL;
-- Expected: ~663

-- Check GPS coverage by track
SELECT
  t.track_name,
  COUNT(DISTINCT l.lap_id) as total_laps,
  COUNT(DISTINCT CASE WHEN EXISTS (
    SELECT 1 FROM telemetry_readings tr
    WHERE tr.lap_id = l.lap_id
    AND tr.vbox_lat_min IS NOT NULL
  ) THEN l.lap_id END) as laps_with_gps
FROM tracks t
JOIN races r ON t.track_id = r.track_id
JOIN sessions s ON r.race_id = s.race_id
JOIN laps l ON s.session_id = l.session_id
WHERE l.lap_number < 32768
GROUP BY t.track_name;
```

---

## Querying Data for ML

### Quick Start Examples

#### 1. Get ML-Ready Training Data

```python
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine('postgresql://postgres:password@localhost/gr_cup_racing')

# Load features and target
df = pd.read_sql("""
    SELECT * FROM stint_degradation
    WHERE lap_time_seconds > 0
      AND lap_in_stint >= 5  -- Skip warmup laps
      AND lap_in_stint <= 15  -- Focus on degradation phase
""", engine)

# Separate features and target
feature_cols = [
    'air_temp', 'track_temp', 'humidity', 'wind_speed', 'temp_delta',
    'avg_brake_front', 'max_brake_front', 'avg_brake_rear', 'max_brake_rear',
    'avg_lateral_g', 'max_lateral_g', 'avg_long_g', 'max_accel_g', 'max_brake_g',
    'steering_variance', 'avg_steering_angle', 'avg_throttle_blade',
    'avg_speed', 'max_speed', 'min_speed', 'avg_rpm', 'max_rpm', 'lap_in_stint'
]

X = df[feature_cols]
y = df['rolling_5lap_degradation']  # Target: tire degradation rate
```

#### 2. Get Telemetry for Visualization

```python
lap_id = 12345

telemetry = pd.read_sql(f"""
    SELECT
        meta_time,
        laptrigger_lapdist_dls as distance,
        speed,
        aps as throttle,
        pbrake_f as brake_pressure,
        steering_angle,
        accy_can as lateral_g,
        accx_can as long_g
    FROM telemetry_readings
    WHERE lap_id = {lap_id}
    ORDER BY meta_time
""", engine)

# Plot
import matplotlib.pyplot as plt
fig, axes = plt.subplots(3, 1, figsize=(12, 8))
axes[0].plot(telemetry['distance'], telemetry['speed'])
axes[0].set_ylabel('Speed (km/h)')
axes[1].plot(telemetry['distance'], telemetry['brake_pressure'])
axes[1].set_ylabel('Brake Pressure (bar)')
axes[2].plot(telemetry['distance'], telemetry['lateral_g'])
axes[2].set_ylabel('Lateral G')
axes[2].set_xlabel('Distance (m)')
plt.tight_layout()
plt.show()
```

#### 3. Find Representative Laps

```python
# Get best, average, and slow laps per track
representative_laps = pd.read_sql("""
    WITH lap_times AS (
        SELECT
            lap_id,
            track_id,
            lap_time_seconds,
            NTILE(10) OVER (PARTITION BY track_id ORDER BY lap_time_seconds) as decile
        FROM lap_aggression_metrics
    )
    SELECT
        track_id,
        MAX(CASE WHEN decile = 1 THEN lap_id END) as fast_lap_id,
        MAX(CASE WHEN decile = 5 THEN lap_id END) as avg_lap_id,
        MAX(CASE WHEN decile = 9 THEN lap_id END) as slow_lap_id
    FROM lap_times
    GROUP BY track_id
""", engine)
```

### Common Queries

#### Get Fastest Lap Per Track
```sql
SELECT DISTINCT ON (track_id)
    track_id,
    lap_id,
    lap_time_seconds,
    vehicle_id
FROM lap_aggression_metrics
ORDER BY track_id, lap_time_seconds ASC;
```

#### Compare Two Vehicles
```sql
SELECT
    v1.vehicle_id as vehicle_1,
    v2.vehicle_id as vehicle_2,
    v1.avg_lap_time as vehicle_1_avg_time,
    v2.avg_lap_time as vehicle_2_avg_time,
    v1.avg_lap_time - v2.avg_lap_time as time_delta
FROM vehicle_aggression_profile v1
CROSS JOIN vehicle_aggression_profile v2
WHERE v1.vehicle_id = 'GR86-049-88'
  AND v2.vehicle_id = 'GR86-006-7';
```

#### Find Laps with GPS Data
```sql
SELECT
    l.lap_id,
    l.lap_number,
    l.vehicle_id,
    COUNT(tr.telemetry_id) as gps_points
FROM laps l
JOIN telemetry_readings tr ON l.lap_id = tr.lap_id
WHERE tr.vbox_lat_min IS NOT NULL
  AND tr.vbox_long_minutes IS NOT NULL
GROUP BY l.lap_id, l.lap_number, l.vehicle_id
HAVING COUNT(tr.telemetry_id) > 100  -- At least 100 GPS points
ORDER BY l.lap_id;
```

---

## Performance Optimization

### Query Best Practices

**✅ DO:**
- Use pre-computed views (`lap_aggression_metrics`, `stint_degradation`)
- Filter early: `WHERE lap_id = X` before joining
- Limit telemetry queries: `LIMIT 10000` or filter by lap/time range
- Use indexes: Query should show "Index Scan" in `EXPLAIN`

**❌ DON'T:**
- Query full `telemetry_readings` table without filters (23M rows!)
- Use `lap_duration` column (unreliable - calculate from timestamps)
- Use `timestamp_ecu` (use `meta_time` instead)
- Join tables when a view already exists

### Check Query Performance

```sql
EXPLAIN ANALYZE
SELECT * FROM lap_aggression_metrics WHERE track_id = 1;
```

Look for:
- "Index Scan" (good) vs "Seq Scan" (slow)
- Execution time < 1 second for view queries

---

## Troubleshooting

### Connection Issues

```bash
# Check PostgreSQL is running
pg_isready

# Test connection
psql -h localhost -U postgres -d gr_cup_racing

# Use environment variable for password
export PGPASSWORD=password
psql -h localhost -U postgres -d gr_cup_racing -c "SELECT COUNT(*) FROM laps;"
```

### Slow Queries

1. Use pre-computed views
2. Add `LIMIT` to telemetry queries
3. Run `ANALYZE` on tables:
   ```sql
   ANALYZE laps;
   ANALYZE telemetry_readings;
   ```

### Unexpected Results

```sql
-- Always filter erroneous laps
WHERE lap_number < 32768 AND lap_number > 0

-- Always calculate lap time from timestamps
EXTRACT(EPOCH FROM (lap_end_time - lap_start_time)) as lap_time_seconds

-- Check for NULL values
WHERE lap_start_time IS NOT NULL AND lap_end_time IS NOT NULL
```

---

## File References

- **sql/schema/schema.sql** - Database schema with all tables and indexes
- **sql/views/create_preprocessing_views.sql** - ML views (lap_aggression_metrics, stint_degradation, vehicle_aggression_profile)
- **sql/queries/ml_queries.sql** - Example queries for ML workflows
- **src/data_preprocessing.py** - Python preprocessing pipeline (uses views)
- **hackathon_app/utils/data_loader.py** - Streamlit data loading functions

---

## Next Steps

1. ✅ Database loaded and views created
2. ✅ Data quality validated
3. ⏭️ **Query data for ML training** - See [docs/PREPROCESSING.md](PREPROCESSING.md)
4. ⏭️ **Build Streamlit dashboards** - See hackathon_app/
5. ⏭️ **Train models** - See ml_training/

**Ready to race! 🏁**
