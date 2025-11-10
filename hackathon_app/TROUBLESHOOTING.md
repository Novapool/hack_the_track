# Troubleshooting Guide - Tire Whisperer Dashboard

## Current Status: ✅ WORKING

Your application is running correctly! The warnings you see are **expected** and do not indicate errors.

## Common "Warnings" That Are Actually Normal

### 1. ✅ **`avg_throttle_blade` NaN Values**
**Status:** Expected behavior

**What you see:**
```
DEBUG | Expected NaN in avg_throttle_blade column, filling with 0
```

**Why this happens:**
- Some racing telemetry systems don't include throttle blade sensors
- The code automatically fills missing values with 0
- Predictions work correctly without this sensor

**Action needed:** None - this is handled automatically

---

### 2. ✅ **No GPS Data for Certain Laps**
**Status:** Expected behavior

**What you see:**
```
WARNING | No GPS data available for lap_id=XXXXX
```

**Why this happens:**
- GPS coverage varies by track:
  - ✅ Barber: 530 laps with GPS
  - ✅ Indianapolis: 527 laps with GPS
  - ❌ COTA: 0 laps with GPS
  - ❌ Road America: 0 laps with GPS
  - ❌ Sebring: 0 laps with GPS
  - ❌ Sonoma: 0 laps with GPS
  - ❌ VIR: 0 laps with GPS

**Action needed:** None - Track visualization shows the track image without GPS overlay

---

## How to Check If Something Is Actually Wrong

### ✅ Good Signs (App is working):
- Lap data loads successfully
- Predictions are generated (numbers like -0.858 sec/lap)
- Track visualizations appear
- What-If Analysis sliders work
- No Python exceptions or tracebacks

### ❌ Real Errors to Watch For:
- **Database connection failures**
  - Error: `could not connect to server`
  - Fix: Ensure PostgreSQL is running (`brew services start postgresql`)

- **Missing model file**
  - Error: `FileNotFoundError: Model file not found`
  - Fix: Ensure `models/tire_degradation_model_random_forest_with_weather.pkl` exists

- **Empty lap lists**
  - Check logs: `INFO | Loaded 0 laps for track`
  - Already fixed - you should see non-zero lap counts now

---

## Viewing Logs

### Real-Time Monitoring
```bash
# Watch logs as they happen
tail -f hackathon_app/logs/tire_whisperer_$(date +%Y%m%d).log
```

### Search for Errors
```bash
# Only show ERROR messages
grep "ERROR" hackathon_app/logs/tire_whisperer_*.log

# Show WARNING messages (may include expected warnings)
grep "WARNING" hackathon_app/logs/tire_whisperer_*.log
```

### Debug Specific Lap
```bash
# Find all logs for a specific lap_id
grep "lap_id=31786" hackathon_app/logs/tire_whisperer_*.log
```

---

## Log Levels Explained

| Level | Meaning | Action |
|-------|---------|--------|
| **DEBUG** | Detailed information for debugging | Ignore unless actively debugging |
| **INFO** | Normal operations | Everything is working |
| **WARNING** | Something unexpected but handled | Check if it's expected (see above) |
| **ERROR** | Something failed | Needs investigation |

---

## Data Quality Issues (Already Handled)

### Known Issues from Dataset:
1. ✅ **Lap #32768** - Filtered out (ECU overflow error)
2. ✅ **NULL lap_duration** - Handled with COALESCE
3. ✅ **NULL avg_throttle_blade** - Filled with 0
4. ✅ **numpy.int64 type issues** - Converted to Python int
5. ✅ **Missing GPS on some tracks** - Gracefully handled

All these issues are automatically handled by the application.

---

## Performance Stats

From your logs, here's what's working:

### ✅ Successful Operations:
- **Lap Loading:** ~50-100ms per track query
- **Feature Loading:** ~200-300ms per lap
- **GPS Loading:** ~500ms for 100K GPS points
- **Predictions:** ~50ms per prediction
- **Model Loading:** ~500ms (cached after first load)

### Track Coverage:
```
Track              | Total Laps | GPS Laps | Coverage
-------------------|------------|----------|----------
Barber             |        749 |      530 | 70.8%
Indianapolis       |        847 |      527 | 62.2%
COTA               |      1,871 |        0 | 0.0%
Road America       |        807 |        0 | 0.0%
Sebring            |      1,464 |        0 | 0.0%
Sonoma             |      3,451 |        0 | 0.0%
VIR                |      1,675 |        0 | 0.0%
```

---

## Quick Health Check

Run this to verify everything is working:

```bash
source .venv/bin/activate
python -c "
from hackathon_app.utils.data_loader import get_available_tracks, get_available_laps, get_lap_features
from hackathon_app.utils.model_predictor import predict_lap_degradation

# Check database
tracks = get_available_tracks()
print(f'✓ Database: {len(tracks)} tracks available')

# Check laps
laps = get_available_laps('indianapolis', limit=5)
print(f'✓ Laps: {len(laps)} laps loaded')

# Check features & prediction
if not laps.empty:
    features = get_lap_features(laps.iloc[0]['lap_id'])
    if features is not None:
        pred = predict_lap_degradation(features)
        print(f'✓ Prediction: {pred:.3f} sec/lap')
        print('\n✅ All systems operational!')
    else:
        print('✗ Could not load features')
else:
    print('✗ No laps available')
"
```

Expected output:
```
✓ Database: 7 tracks available
✓ Laps: 5 laps loaded
✓ Prediction: -0.858 sec/lap

✅ All systems operational!
```

---

## Contact & Support

If you see actual ERROR messages (not warnings), check:
1. This troubleshooting guide
2. The detailed logs at `hackathon_app/logs/tire_whisperer_*.log`
3. The main documentation in `CLAUDE.md`

The logging system will show you exactly where any real errors occur with full context and tracebacks.
