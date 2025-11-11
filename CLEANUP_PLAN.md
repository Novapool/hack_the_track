# Hack the Track - Cleanup & Reorganization Plan

**Date**: November 11, 2025
**Status**: ✅ In Progress
**Goal**: Clean codebase, improve documentation, simplify Streamlit UX

---

## Summary of Changes

### ✅ Phase 1: Codebase Cleanup (COMPLETED)

1. **Deleted `archive/` directory** (11MB freed)
   - Removed historical ETL scripts (one-time use)
   - Removed CSV column metadata files
   - Removed 11MB of migration logs
   - **Rationale**: Data is in PostgreSQL, ETL completed, logs no longer needed

2. **Reorganized project structure**
   - Created `ml_training/` folder for training scripts
   - Moved `scripts/train_with_weather.py` → `ml_training/train_with_weather.py`
   - Removed empty `scripts/` directory
   - **Rationale**: Better separation between data prep, training, and deployment

### ✅ Phase 2: Database Documentation (COMPLETED)

1. **Updated `docs/DATABASE.md`** with:
   - **Accurate statistics**: 13,701 total laps, 9,549 valid, 3,737 ML-ready
   - **Table schemas**: All key tables with columns and data types
   - **NULL patterns**: Documented missing data for all tables
   - **View documentation**: Detailed column lists for ML views
   - **Data quality notes**: Known issues (lap 32768, unreliable lap_duration, GPS coverage)
   - **Common queries**: Python examples for ML workflows
   - **Removed references** to deleted `archive/` directory

---

## Project Structure (Current)

```
hack_the_track/
├── README.md
├── CLAUDE.md
├── CLEANUP_PLAN.md (THIS FILE)
├── requirements.txt
├── db_config.yaml
│
├── docs/
│   ├── DATABASE.md (✅ UPDATED - comprehensive schema reference)
│   ├── PREPROCESSING.md
│   └── HACKATHON_DASHBOARD.md
│
├── src/
│   └── data_preprocessing.py
│
├── sql/
│   ├── schema/schema.sql
│   ├── views/create_preprocessing_views.sql
│   └── queries/ml_queries.sql
│
├── ml_data/ (1.7MB)
│   ├── features_normalized.csv
│   ├── features_with_weather.csv
│   ├── target_degradation.csv
│   └── target_with_weather.csv
│
├── ml_training/ (✅ NEW - consolidated training scripts)
│   └── train_with_weather.py
│
├── models/ (4.5MB)
│   ├── tire_degradation_model_random_forest_with_weather.pkl
│   ├── model_metadata_with_weather.json
│   └── model_metadata.json
│
├── examples/
│   ├── test_preprocessing.py
│   └── test_model_sensitivity.py
│
└── hackathon_app/ (Streamlit app)
    ├── app.py
    ├── pages/
    │   ├── 1_🏁_Track_Visualization.py
    │   ├── 2_🎮_What_If_Analysis.py
    │   └── 3_👥_Driver_Comparison.py
    └── utils/
        ├── data_loader.py
        ├── error_display.py
        ├── logger.py
        ├── model_predictor.py
        ├── pdf_converter.py
        └── track_plotter.py
```

---

## Database Quick Reference

### Connection Info
```bash
# Command line
psql -h localhost -U postgres -d gr_cup_racing

# With password
PGPASSWORD=password psql -h localhost -U postgres -d gr_cup_racing

# Python
import psycopg2
conn = psycopg2.connect(
    host='localhost',
    database='gr_cup_racing',
    user='postgres',
    password='password'
)
```

### Database Statistics

| Metric | Count |
|--------|-------|
| Database Size | 6.2 GB |
| Telemetry Rows | 23,179,647 (23.1M) |
| Total Laps | 13,701 |
| Valid Laps | 9,549 (lap_number < 32768) |
| ML-Ready Laps | 3,737 (with telemetry + weather) |
| Tracks | 7 |
| Vehicles | 65 |
| Races | 14 (2 per track) |
| Weather Records | 567 |

### Key Tables

| Table | Rows | Purpose |
|-------|------|---------|
| **tracks** | 7 | Circuit information |
| **races** | 14 | Race events (2 per track) |
| **sessions** | 14 | Racing sessions |
| **laps** | 13,701 | Lap timing data |
| **vehicles** | 65 | Race cars (Toyota GR86s) |
| **telemetry_readings** | 23.1M | High-frequency sensor data (6.2 GB) |
| **weather_data** | 567 | Weather conditions (fully populated) |

### ML Views

| View | Rows | Purpose |
|------|------|---------|
| **lap_aggression_metrics** | 3,737 | Lap-level telemetry aggregations (33 features) |
| **stint_degradation** | 3,737 | Tire degradation indicators (36 features) |
| **vehicle_aggression_profile** | 64 | Driving style summaries per vehicle |

---

## Data Quality Notes

### Critical Known Issues

#### 1. ⚠️ Lap 32768 (ECU Overflow)
- **Affected**: 2,837 laps (20.7%)
- **Cause**: ECU lap counter overflow
- **Solution**: Filter `WHERE lap_number < 32768 AND lap_number > 0`
- **Handled by**: Views already filter this out

#### 2. ⚠️ Unreliable `lap_duration` Column
- **Issue**: Contains garbage values (45, 784369 instead of ~100)
- **Solution**: **NEVER use lap_duration** - Always calculate:
  ```sql
  EXTRACT(EPOCH FROM (lap_end_time - lap_start_time)) as lap_time_seconds
  ```
- **Views**: lap_aggression_metrics and stint_degradation already use calculated values

#### 3. ⚠️ Limited GPS Coverage
- **Coverage**: Only 28.7% of telemetry has GPS (6.6M / 23.1M)
- **Impact**: Limits track visualization to specific sessions
- **Check before use**:
  ```sql
  SELECT COUNT(*) FROM telemetry_readings
  WHERE lap_id = X AND vbox_lat_min IS NOT NULL;
  ```

#### 4. ⚠️ Missing Speed Data
- **Coverage**: Only 20% of telemetry has speed values (80% NULL)
- **Impact**: Telemetry charts may be incomplete
- **Workaround**: Other metrics (brake, throttle, RPM) have 95%+ coverage

#### 5. Missing Lap Timing
- **Affected**: 663 laps (4.8%) missing lap_start_time or lap_end_time
- **Impact**: Cannot calculate lap duration
- **Handled by**: Views automatically exclude these

### NULL Pattern Summary

| Table | Column | NULL Count | % NULL | Impact |
|-------|--------|------------|--------|--------|
| laps | lap_start_time | 305 | 2.2% | Excludes from ML |
| laps | lap_end_time | 358 | 2.6% | Excludes from ML |
| laps | lap_duration | 1,890 | 13.8% | ⚠️ **DO NOT USE** |
| telemetry_readings | vbox_lat_min (GPS) | 16.5M | 71.2% | Limits track viz |
| telemetry_readings | speed | 18.5M | 80.0% | Charts incomplete |
| telemetry_readings | pbrake_f | 718K | 3.1% | Minor |
| weather_data | ALL | 0 | 0% | ✅ Complete |

### Track Distribution

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

## ⏭️ Phase 3: Streamlit App Simplification (PENDING)

### Current Issues

1. **What-If Analysis Page**
   - Shows 30 random laps per track (overwhelming)
   - No context on which lap to choose
   - User doesn't know if lap is representative

2. **Track Visualization Page**
   - Shows 50 arbitrary laps
   - GPS availability not clear upfront
   - No filtering by vehicle/date/lap time

3. **Driver Comparison Page**
   - Compares ALL laps across ALL tracks (not apples-to-apples)
   - Efficiency scores are hardcoded placeholders (0.4, 0.45)
   - 65 vehicles × 64 = 4,160 combinations (too many)

### Planned Solutions

#### 3.1 What-If Analysis (Priority 1)

**Change**: Representative lap selection
- Show **3 options per track**:
  1. "Fast Lap" - Best lap time (top 10% median)
  2. "Average Lap" - Median lap time
  3. "Slow Lap" - Slower representative (bottom 10% median)
- Add "Advanced Mode" toggle: Show all laps with filters

**Implementation**:
- Add `get_representative_laps(track_name)` to `data_loader.py`
- Update `2_🎮_What_If_Analysis.py` dropdown logic

#### 3.2 Track Visualization (Priority 2)

**Change**: GPS-focused filtering
- Show GPS availability upfront: "X laps with GPS / Y total"
- Default to "Best Laps with GPS" (top 10)
- Add filters:
  - ✓ Show only laps with GPS
  - Vehicle filter (optional)
  - Sort by: Fastest | Slowest | Most Recent
- Remove 50-lap limit

**Implementation**:
- Add GPS summary query
- Update `1_🏁_Track_Visualization.py` with filters
- Modify `get_available_laps()` to accept filter parameters

#### 3.3 Driver Comparison (Priority 3)

**Change**: Track-specific comparison
- Add **Track Filter** dropdown (default: "All Tracks" with warning)
- Show comparison options:
  - Best Lap Comparison (fastest lap each)
  - Average Performance (avg across laps)
  - Track-Specific (same track only)
- Fix efficiency scores: Replace hardcoded 0.4/0.45 with:
  ```python
  efficiency = avg_speed / (avg_brake_front + avg_throttle_variance + 1)
  ```

**Implementation**:
- Add track filter dropdown
- Add `get_vehicle_stats_by_track(vehicle_id, track_id)` to `data_loader.py`
- Calculate real efficiency metrics

---

## Common Queries for Development

### Get Representative Laps
```sql
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
GROUP BY track_id;
```

### Check GPS Availability
```sql
SELECT
    t.track_name,
    COUNT(DISTINCT l.lap_id) as total_laps,
    COUNT(DISTINCT CASE WHEN EXISTS (
        SELECT 1 FROM telemetry_readings tr
        WHERE tr.lap_id = l.lap_id
        AND tr.vbox_lat_min IS NOT NULL
    ) THEN l.lap_id END) as laps_with_gps,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN EXISTS (
        SELECT 1 FROM telemetry_readings tr
        WHERE tr.lap_id = l.lap_id
        AND tr.vbox_lat_min IS NOT NULL
    ) THEN l.lap_id END) / COUNT(DISTINCT l.lap_id), 1) as gps_coverage_pct
FROM tracks t
JOIN races r ON t.track_id = r.track_id
JOIN sessions s ON r.race_id = s.race_id
JOIN laps l ON s.session_id = l.session_id
WHERE l.lap_number < 32768
GROUP BY t.track_name
ORDER BY t.track_name;
```

### Get Fastest Lap Per Track
```sql
SELECT DISTINCT ON (track_id)
    track_id,
    lap_id,
    lap_time_seconds,
    vehicle_id
FROM lap_aggression_metrics
ORDER BY track_id, lap_time_seconds ASC;
```

---

## Next Steps

### Immediate (This Session)
- [ ] Simplify What-If Analysis page (representative laps)
- [ ] Simplify Track Visualization page (GPS filtering)
- [ ] Simplify Driver Comparison page (track filtering)

### Future Enhancements (Later)
- [ ] Retrain model with corrected lap times (from fixed SQL views)
- [ ] Add data quality dashboard to Streamlit app
- [ ] Optimize telemetry queries (pre-aggregate common patterns)
- [ ] Add caching to reduce database load
- [ ] Investigate missing GPS data (can it be recovered?)
- [ ] Add lap search by lap_id to all pages

---

## File References

### Documentation
- **CLAUDE.md** - Project overview and Claude Code instructions
- **README.md** - Main project documentation
- **docs/DATABASE.md** - ✅ Database schema, tables, views, data quality
- **docs/PREPROCESSING.md** - ML preprocessing pipeline
- **CLEANUP_PLAN.md** - This file (reference for next session)

### Code
- **src/data_preprocessing.py** - TireDegradationPreprocessor class
- **hackathon_app/utils/data_loader.py** - Streamlit data loading functions
- **ml_training/train_with_weather.py** - Model training script

### SQL
- **sql/schema/schema.sql** - Database schema
- **sql/views/create_preprocessing_views.sql** - ML views
- **sql/queries/ml_queries.sql** - Example queries

### Data
- **ml_data/** - Processed CSV files for ML
- **models/** - Trained model files (PKL + JSON metadata)

---

## Important Reminders

### When Working with Database:
✅ **DO:**
- Use pre-computed views (lap_aggression_metrics, stint_degradation)
- Calculate lap times from timestamps: `EXTRACT(EPOCH FROM (lap_end_time - lap_start_time))`
- Filter erroneous laps: `WHERE lap_number < 32768 AND lap_number > 0`
- Use `meta_time` for timing (not `timestamp_ecu`)

❌ **DON'T:**
- Use `lap_duration` column (unreliable - has garbage values)
- Query full `telemetry_readings` without filters (23M rows!)
- Forget to check GPS availability before track visualization
- Use `timestamp_ecu` (ECU clock drift issues)

### When Modifying Streamlit App:
- Use `@st.cache_data(ttl=600)` for data loading functions
- Always handle None/NULL values gracefully
- Add error handling with try/except blocks
- Test with multiple tracks to ensure queries work
- Check logs in `hackathon_app/logs/` for debugging

---

**Status**: ✅ Phases 1-2 complete | ⏭️ Phase 3 pending
**Next**: Simplify Streamlit app UX (representative laps, GPS filtering, track-specific comparisons)
**Time Estimate**: 1-2 hours for Phase 3

**Ready to continue! 🏁**
