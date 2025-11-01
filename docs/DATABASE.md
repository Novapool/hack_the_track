# Toyota GR Cup Racing Database Guide

## Table of Contents
1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Database Schema](#database-schema)
4. [ETL Pipeline](#etl-pipeline)
5. [Querying Data for ML](#querying-data-for-ml)
6. [Data Quality](#data-quality)
7. [Performance Optimization](#performance-optimization)
8. [Troubleshooting](#troubleshooting)

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
- **Total Size**: ~1-2 GB (currently loaded data)
- **Telemetry Rows**: Millions (high-frequency sensor readings)
- **Lap Records**: 3,257 (across 8 races)
- **Tracks**: 7 (Barber, COTA, Indianapolis, Road America, Sebring, Sonoma, VIR)
- **Vehicles**: 62

---

## Getting Started

### Prerequisites

1. **PostgreSQL 14+** installed and running
2. **Python 3.9+** with required packages
3. **Sufficient disk space** (100+ GB recommended for full dataset)

### Installation Steps

#### 1. Install PostgreSQL

**macOS (Homebrew):**
```bash
brew install postgresql@14
brew services start postgresql@14
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql-14
sudo systemctl start postgresql
```

**Windows:**
Download from [postgresql.org](https://www.postgresql.org/download/windows/)

#### 2. Create Database

```bash
# Login as postgres user
psql -U postgres

# Create database
CREATE DATABASE gr_cup_racing;

# Create user (optional)
CREATE USER racing_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE gr_cup_racing TO racing_user;

# Exit psql
\q
```

#### 3. Install Python Dependencies

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 4. Configure Database Connection

Edit `db_config.yaml`:

```yaml
database:
  host: localhost
  port: 5432
  database: gr_cup_racing
  user: postgres        # or racing_user
  password: your_password_here  # CHANGE THIS!
```

#### 5. Create Schema

```bash
psql -U postgres -d gr_cup_racing -f sql/schema/schema.sql
```

You should see:
```
CREATE TABLE
CREATE INDEX
...
Schema created successfully!
```

---

## Database Schema

### Entity Relationship Diagram

```
tracks (7 rows)
  ↓
races (14 rows)
  ↓
sessions (14 rows)
  ↓
laps (10K-15K rows) ← vehicles (30-40 rows)
  ↓
telemetry_readings (100M+ rows)
```

### Table Descriptions

#### Dimension Tables (Reference Data)

**1. tracks**
- Stores racing circuit information
- Primary Key: `track_id`
- Example: COTA, Sebring, Sonoma

**2. races**
- Individual race events at specific tracks
- Foreign Key: `track_id` → tracks
- Contains: `race_number` (1 or 2), `meta_event`, `race_date`

**3. vehicles**
- Race cars with chassis and car numbers
- Primary Key: `vehicle_id` (e.g., "GR86-002-2")
- Contains: `chassis_number` (unique identifier), `car_number` (may change)

**4. drivers**
- Driver information and team affiliations
- Contains: Name, country, team, participant number

**5. sessions**
- Racing sessions within a race event
- Foreign Key: `race_id` → races
- Typically one session per race

#### Fact Tables (Transactional Data)

**6. laps**
- Individual lap timing data
- Foreign Keys: `session_id`, `vehicle_id`
- Contains: lap start/end times, duration, validity flag
- **Important**: `is_valid_lap = FALSE` when `lap_number = 32768` (known data issue)

**7. telemetry_readings** ⚡ **LARGEST TABLE**
- High-frequency sensor readings (pivoted from EAV format)
- Foreign Keys: `lap_id`, `session_id`, `vehicle_id`
- Contains 13 telemetry parameters: speed, gear, RPM, throttle, brakes, acceleration, GPS, etc.
- **Optimized** with indexes for fast queries

**8. race_results**
- Final race positions and results
- Foreign Keys: `race_id`, `driver_id`, `vehicle_id`
- Contains: position, status, fastest lap, gaps

**9. sector_analysis**
- Detailed sector and intermediate timing
- Foreign Keys: `race_id`, `vehicle_id`
- Contains: sector times (S1, S2, S3), intermediate markers

**10. weather_data**
- Weather conditions during races
- Foreign Key: `race_id`
- Contains: temperature, humidity, pressure, conditions

**11. championship_standings**
- Season championship points and standings
- Foreign Key: `driver_id`
- Contains: points, position, race-by-race results (JSONB)

### Key Indexes

Fast queries are enabled by indexes on:
- Foreign keys (all tables)
- `vehicle_id`, `lap_number`, `meta_time` (laps, telemetry)
- `track_id`, `race_date` (races)
- `lap_duration` (for fastest lap queries)

---

## ETL Pipeline

### Running the Migration

ETL scripts are located in `archive/etl_scripts/` (historical reference).

#### Full Migration (All Tracks)

```bash
python archive/etl_scripts/csv_to_sql.py --config db_config.yaml
```

#### Single Track Migration

```bash
python archive/etl_scripts/csv_to_sql.py --config db_config.yaml --track COTA
```

#### Dry Run (No Data Insertion)

```bash
python archive/etl_scripts/csv_to_sql.py --config db_config.yaml --dry-run
```

### ETL Process Flow

1. **Phase 1: Dimension Tables**
   - Load tracks from configuration
   - Extract unique vehicles from CSV files
   - Parse vehicle IDs (GR86-XXX-YYY format)

2. **Phase 2: Race Data**
   - Scan directory structure
   - Extract metadata from CSV files
   - Create race and session records

3. **Phase 3: Fact Tables**
   - **Laps**: Merge lap_start, lap_end, lap_time CSVs
   - **Telemetry**: Pivot EAV data to columnar format (SLOW - processes in batches)

4. **Phase 4: Analysis Data**
   - Load race results
   - Load sector analysis
   - Load weather data

5. **Phase 5: Championship**
   - Load championship standings (only in full migration)

### Performance Considerations

**Telemetry Loading Time:**
- Expect **2-4 hours** for full migration
- COTA alone: ~17M rows, ~30-45 minutes
- Uses batch processing (10,000 rows per batch)

**Optimizations:**
- Parallel processing enabled by default (4 workers)
- Batch inserts reduce database round trips
- Indexes created after bulk load (recommended)

### Monitoring Progress

The ETL script provides:
- Progress bars for each file
- Real-time statistics
- Detailed logging to `archive/logs/etl.log`

Example output:
```
INFO - Phase 1: Loading dimension tables...
INFO - Loaded 7 tracks
INFO - Loaded 38 vehicles
INFO - Phase 2: Loading race data...
INFO - Loaded 14 races
INFO - Created 14 sessions
INFO - Phase 3: Loading fact tables...
Processing R1_cota_telemetry_data.csv: 100%|███████| 1775/1775 [12:34<00:00, 2.35it/s]
```

---

## Querying Data for ML

### Quick Start Examples

#### 1. Get Lap Data with Features

```sql
SELECT * FROM stint_degradation
WHERE lap_time_seconds > 0
  AND lap_number < 32768  -- Filter erroneous lap counts
ORDER BY race_id, vehicle_id, lap_number
LIMIT 100;
```

#### 2. Export to Python/Pandas

```python
import pandas as pd
import psycopg2

conn = psycopg2.connect(
    host='localhost',
    database='gr_cup_racing',
    user='postgres',
    password=''
)

# Load training data
df = pd.read_sql("""
    SELECT * FROM stint_degradation
    WHERE lap_time_seconds > 0
""", conn)

# Export to Parquet for fast loading
df.to_parquet('training_data.parquet', compression='snappy')
```

#### 3. Get Telemetry Time Series for Visualization

```python
# Get telemetry for specific lap
lap_telemetry = pd.read_sql(f"""
    SELECT
        meta_time,
        laptrigger_lapdist_dls as distance,
        speed,
        aps as throttle_position,
        pbrake_f as brake_pressure,
        steering_angle
    FROM telemetry_readings
    WHERE lap_id = {lap_id}
    ORDER BY meta_time
""", conn)

# Plot
import matplotlib.pyplot as plt
plt.plot(lap_telemetry['distance'], lap_telemetry['speed'])
plt.xlabel('Distance (m)')
plt.ylabel('Speed (km/h)')
plt.show()
```

### Common ML Workflows

#### Workflow 1: Tire Degradation Prediction

```python
# Use the preprocessing pipeline (recommended)
from src.data_preprocessing import TireDegradationPreprocessor

db_config = {
    'host': 'localhost',
    'database': 'gr_cup_racing',
    'user': 'postgres',
    'password': ''
}

preprocessor = TireDegradationPreprocessor(db_config)
X, y = preprocessor.prepare_training_data()

# Train model
from sklearn.ensemble import RandomForestRegressor
model = RandomForestRegressor()
model.fit(X, y)
```

#### Workflow 2: Anomaly Detection

```sql
-- Get laps with unusual telemetry patterns
SELECT
    lap_id,
    vehicle_id,
    lap_time_seconds,
    avg_speed,
    max_speed,
    max_brake_g
FROM lap_aggression_metrics
WHERE max_speed > 220  -- Unusually high speed
   OR max_brake_g < -2.0  -- Unusually high braking
   OR avg_speed < 80;  -- Unusually slow
```

#### Workflow 3: Driver Style Classification

```sql
-- Extract driving style features
SELECT
    vehicle_id,
    AVG(avg_throttle_pos) as typical_throttle_usage,
    AVG(max_brake_front) as typical_max_braking,
    AVG(avg_lateral_g) as typical_cornering_g,
    STDDEV(lap_time_seconds) as consistency
FROM lap_aggression_metrics
GROUP BY vehicle_id
HAVING COUNT(*) > 20;  -- Sufficient data
```

### Pre-built Views for ML

**lap_aggression_metrics**
- Lap-level telemetry aggregations
- Brake pressure, lateral G's, steering smoothness, throttle usage
- Speed and engine metrics
- Location: `sql/views/create_preprocessing_views.sql`

**stint_degradation**
- Builds on lap_aggression_metrics
- Adds tire degradation indicators (lap_time_delta, rolling averages)
- **Primary view for ML training**

**vehicle_aggression_profile**
- Summary statistics per vehicle
- Useful for driver style comparison

---

## Data Quality

### Validation Checks

Run validation after migration:

```bash
python archive/validate_data.py --config db_config.yaml --detailed
```

### Known Data Issues

#### 1. Invalid Lap Numbers (lap_number = 32768)
- **Cause**: ECU lap counter overflow/reset
- **Solution**: Filter with `lap_number < 32768`
- **Impact**: ~1-5% of laps affected
- **Mitigation**: Time values remain accurate; can derive lap from timestamps

#### 2. ECU Timestamp Drift
- **Cause**: ECU clock may not be synced with actual time
- **Solution**: Use `meta_time` (message received time) as source of truth
- **Impact**: `timestamp_ecu` may be off by minutes to hours
- **Mitigation**: Always use `meta_time` for time-based analysis

#### 3. Telemetry Outliers
- **Examples**: Speed > 250 km/h, RPM > 8000, negative values
- **Detection**: Run validation script for automated detection
- **Handling**:
  ```sql
  -- Filter outliers in queries
  WHERE speed BETWEEN 0 AND 220
    AND nmot BETWEEN 0 AND 7500
    AND pbrake_f >= 0
  ```

#### 4. Missing Data
- Some laps may not have telemetry data
- Some vehicles may have incomplete lap records
- **Recommendation**: Use preprocessing pipeline which handles this automatically

### Data Cleaning for ML

```python
# The TireDegradationPreprocessor handles this automatically
# But for custom queries:

df = df[
    (df['lap_number'] < 32768) &
    (df['lap_time_seconds'] > 0) &
    (df['max_speed'] < 220) &
    (df['avg_speed'] > 50)
]

# Handle missing values
df = df.dropna(subset=['lap_time_seconds', 'avg_speed'])
df = df.fillna(df.median())  # Fill remaining with median

# Remove outliers using Z-score method (handled by preprocessor)
from scipy import stats
z_scores = stats.zscore(df.select_dtypes(include=[np.number]))
df = df[(np.abs(z_scores) < 3).all(axis=1)]
```

---

## Performance Optimization

### Query Optimization Tips

#### 1. Use Indexes

```sql
-- Check if query uses indexes
EXPLAIN ANALYZE
SELECT * FROM laps WHERE vehicle_id = 'GR86-002-2';

-- Should show "Index Scan" not "Seq Scan"
```

#### 2. Limit Telemetry Queries

```sql
-- BAD: Returns millions of rows
SELECT * FROM telemetry_readings;

-- GOOD: Filter by time range or lap
SELECT * FROM telemetry_readings
WHERE lap_id IN (SELECT lap_id FROM laps WHERE vehicle_id = 'GR86-002-2')
LIMIT 10000;
```

#### 3. Use Pre-computed Views

```sql
-- Query the view instead of joining tables
SELECT * FROM stint_degradation
WHERE race_id = 1;
-- Much faster than joining laps + telemetry_readings + sessions + races!
```

#### 4. Connection Pooling

```python
# Use connection pooling for concurrent queries
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    'postgresql://postgres@localhost/gr_cup_racing',
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10
)
```

### Database Maintenance

```sql
-- Analyze tables for query optimization (run after bulk load)
ANALYZE tracks;
ANALYZE races;
ANALYZE sessions;
ANALYZE laps;
ANALYZE telemetry_readings;

-- Vacuum to reclaim space (run periodically)
VACUUM ANALYZE;

-- Reindex if queries are slow
REINDEX TABLE telemetry_readings;
```

---

## Troubleshooting

### Common Issues

#### Issue: "Connection refused" when running queries

**Solution:**
1. Check PostgreSQL is running: `pg_isready`
2. Verify connection settings in `db_config.yaml`
3. Test connection: `psql -U postgres -d gr_cup_racing`

#### Issue: Queries running very slowly

**Solution:**
1. Use pre-computed views (`lap_aggression_metrics`, `stint_degradation`)
2. Ensure indexes exist: Check with `\di` in psql
3. Run `ANALYZE` on tables
4. Use `EXPLAIN ANALYZE` to understand query plan

#### Issue: Out of disk space

**Solution:**
1. Check disk usage: `df -h`
2. Estimate: ~1-2 GB per million telemetry rows
3. Consider filtering tracks or races
4. Run `VACUUM FULL` to reclaim space (requires table lock)

#### Issue: Queries returning unexpected results

**Solution:**
1. Check for invalid laps: `WHERE lap_number < 32768`
2. Verify timestamp usage: Use `meta_time` not `timestamp_ecu`
3. Run validation: `python archive/validate_data.py`
4. Check for NULL values: `WHERE column IS NOT NULL`

#### Issue: Unable to export large datasets

**Solution:**
```python
# Use chunking for large exports
chunksize = 100000
for i, chunk in enumerate(pd.read_sql(query, conn, chunksize=chunksize)):
    # Process chunk
    chunk.to_parquet(f'output_{i}.parquet', compression='snappy')
```

### Getting Help

1. Check logs: `tail -f archive/logs/etl.log`
2. Run validation: `python archive/validate_data.py --detailed`
3. Check PostgreSQL logs: `/var/log/postgresql/postgresql-14-main.log` (Linux)
4. Enable query logging:
   ```sql
   ALTER DATABASE gr_cup_racing SET log_statement = 'all';
   ```

---

## Additional Resources

### Useful SQL Queries

See `sql/queries/ml_queries.sql` for ready-to-use queries including:
- Fastest laps analysis
- Telemetry extraction
- Vehicle performance comparison
- Track characteristics
- Braking zone detection
- Driver consistency analysis

### File References

- `sql/schema/schema.sql` - Database schema with all tables and indexes
- `db_config.yaml` - Configuration file (update passwords!)
- `sql/views/create_preprocessing_views.sql` - ML views creation
- `sql/queries/ml_queries.sql` - Example SQL queries for ML
- `archive/etl_scripts/csv_to_sql.py` - ETL pipeline script (historical)
- `archive/validate_data.py` - Data quality validation

---

## Next Steps

1. ✅ Create PostgreSQL database
2. ✅ Configure `db_config.yaml`
3. ✅ Run `sql/schema/schema.sql` to create tables
4. ✅ ETL completed (data loaded)
5. ✅ SQL views created
6. ⏭️ Start building ML models! See [docs/PREPROCESSING.md](PREPROCESSING.md)

**Good luck with your racing data analysis!** 🏁
