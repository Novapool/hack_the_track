# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

Toyota Gazoo Racing hackathon project analyzing motorsport telemetry data from the Toyota GR Cup racing series. The project focuses on tire degradation modeling using machine learning.

**Current Status:**
- ✅ Database loaded: PostgreSQL with 3,257 laps across 8 races
- ✅ Data preprocessing pipeline: Hybrid SQL/Python approach
- ✅ ML-ready datasets: Normalized features in `ml_data/`
- ⏭️ Next: Model training and optimization

## Project Structure

```
hack_the_track/
├── README.md                  # Main project documentation
├── requirements.txt           # Python dependencies
├── db_config.yaml            # Database configuration
├── Hackathon 2025.pdf        # Challenge documentation
│
├── docs/                     # Detailed guides
│   ├── DATABASE.md           # Database schema, ETL, querying
│   └── PREPROCESSING.md      # ML preprocessing pipeline
│
├── src/                      # Source code
│   └── data_preprocessing.py # TireDegradationPreprocessor class
│
├── sql/                      # SQL scripts
│   ├── schema/schema.sql     # Database schema
│   ├── views/create_preprocessing_views.sql  # ML views
│   └── queries/ml_queries.sql  # Example queries
│
├── ml_data/                  # Processed ML datasets
│   ├── features_normalized.csv
│   └── target_degradation.csv
│
├── examples/                 # Usage examples
│   └── test_preprocessing.py
│
└── archive/                  # Historical scripts
    ├── etl_scripts/          # CSV to SQL migration
    ├── column_data/          # CSV metadata
    └── logs/                 # ETL logs
```

## Database

**Database Name**: `gr_cup_racing` (PostgreSQL)

**Connection**:
```python
db_config = {
    'host': 'localhost',
    'database': 'gr_cup_racing',
    'user': 'postgres',
    'password': 'password'
}
```

**Command line**:
```bash
psql -h localhost -U postgres -d gr_cup_racing
```

**Key Tables**:
- `telemetry_readings` - High-frequency sensor data (columnar format)
- `laps` - Lap timing and metadata
- `sessions` - Racing sessions
- `races` - Race events
- `tracks` - Circuit information
- `vehicles` - Race cars

**Pre-computed Views** (for fast ML data retrieval):
- `lap_aggression_metrics` - Lap-level telemetry aggregations
- `stint_degradation` - Tire degradation indicators
- `vehicle_aggression_profile` - Vehicle driving style summaries

## Data Architecture

### Telemetry Parameters

**Aggression Metrics:**
- `pbrake_f`, `pbrake_r` - Brake pressure (bar)
- `accy_can` - Lateral G forces (cornering)
- `accx_can` - Longitudinal acceleration/braking
- `Steering_Angle` - Steering wheel angle
- `aps`, `ath` - Throttle pedal & blade position

**Speed & Engine:**
- `Speed` - Vehicle speed (km/h)
- `Gear` - Current gear
- `nmot` - Engine RPM

**Position:**
- `VBOX_Long_Minutes`, `VBOX_Lat_Min` - GPS coordinates
- `Laptrigger_lapdist_dls` - Distance from start/finish (m)

### Data Quality Notes (from Hackathon 2025.pdf)

⚠️ **Known Issues** (handled automatically by preprocessing):
- **Lap #32768**: Erroneous lap count (ECU overflow) - filtered out
- **ECU timestamps**: May be inaccurate - use `meta_time` instead
- **Vehicle IDs**: Format `GR86-<chassis>-<car_number>` - use chassis for consistent tracking

## Common Workflows

### 1. Data Exploration

```bash
# Run example script
python examples/test_preprocessing.py

# Query database
psql -h localhost -U postgres -d gr_cup_racing
```

### 2. ML Preprocessing

```python
from src.data_preprocessing import TireDegradationPreprocessor

db_config = {
    'host': 'localhost',
    'database': 'gr_cup_racing',
    'user': 'postgres',
    'password': ''
}

preprocessor = TireDegradationPreprocessor(db_config)

# Get normalized training data (one line!)
X, y = preprocessor.prepare_training_data(
    normalization_method='standard',
    outlier_threshold=3.0
)
```

### 3. Train ML Model

```python
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
model = RandomForestRegressor()
model.fit(X_train, y_train)

print(f"R² Score: {model.score(X_test, y_test):.3f}")
```

### 4. Recreate SQL Views

```bash
psql -h localhost -U postgres -d gr_cup_racing -f sql/views/create_preprocessing_views.sql
```

### 5. Query Database

```bash
# Example queries in sql/queries/ml_queries.sql
psql -h localhost -U postgres -d gr_cup_racing -f sql/queries/ml_queries.sql
```

## Key Features

### Tire Degradation Model

**Features (X)**: 21 aggression metrics per lap
- Brake pressure (avg/max front, avg/max rear)
- Lateral G forces (cornering aggression)
- Longitudinal acceleration/braking
- Steering smoothness (variance)
- Throttle usage patterns
- Speed metrics
- Engine RPM
- Lap position in stint

**Target (y)**: `tire_degradation_rate`
- Lap time increase over stint (seconds)
- Rolling 5-lap average
- Higher = faster tire degradation

**Goal**: Predict how driving aggression affects tire wear

### Hybrid SQL/Python Preprocessing

**Why hybrid?**
- SQL aggregates millions of telemetry rows → thousands of lap features (fast)
- Python normalizes features for ML (flexible)
- **Result**: 10x faster than pure Python pandas

**Performance**:
- Load 2,545 laps: ~0.5 seconds (SQL)
- Normalize features: ~1 second (Python)
- Total: ~1.5 seconds ✅

## File Locations

### Documentation
- **README.md** - Project overview and quick start
- **docs/DATABASE.md** - Database schema, ETL, querying guide
- **docs/PREPROCESSING.md** - ML preprocessing, feature engineering, API reference
- **Hackathon 2025.pdf** - Official challenge documentation

### Code
- **src/data_preprocessing.py** - TireDegradationPreprocessor class (main preprocessing pipeline)
- **examples/test_preprocessing.py** - Usage example and demo

### SQL
- **sql/schema/schema.sql** - Database schema definition
- **sql/views/create_preprocessing_views.sql** - ML views creation
- **sql/queries/ml_queries.sql** - Example queries

### Data
- **ml_data/features_normalized.csv** - Normalized ML features (2,545 rows × 21 features)
- **ml_data/target_degradation.csv** - Target variable (tire degradation rate)

### Configuration
- **db_config.yaml** - Database connection settings
- **requirements.txt** - Python dependencies

### Historical (Archive)
- **archive/etl_scripts/** - CSV to SQL migration scripts
- **archive/column_data/** - Extracted CSV metadata
- **archive/logs/** - ETL process logs

## Development Environment

### Setup

```bash
# 1. Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Test connection
psql -h localhost -U postgres -d gr_cup_racing
```

### Dependencies

- **Data**: pandas, numpy
- **Visualization**: matplotlib, seaborn, plotly
- **Database**: sqlalchemy, psycopg2-binary
- **ML**: scikit-learn
- **Config**: PyYAML, tqdm, tabulate

## Track Information

**Tracks** (7 total):
- Barber Motorsports Park
- Circuit of the Americas (COTA)
- Indianapolis Motor Speedway
- Road America
- Sebring International Raceway
- Sonoma Raceway
- Virginia International Raceway (VIR)

**Data Organization**:
- Raw CSV files in `track_data/` (not in git)
- Loaded into PostgreSQL database
- Pre-aggregated in SQL views for ML

## External Resources

- **Series**: SRO Motorsports
- **2025 Season**: Search "TGRNA GR CUP NORTH AMERICA"
- **2024 Season**: Search "Toyota GR Cup"
- **Official Timing**: SRO website

## Tips for Claude Code

### When adding features:
1. Modify SQL view in `sql/views/create_preprocessing_views.sql`
2. Recreate view: `psql -h localhost -U postgres -d gr_cup_racing -f sql/views/create_preprocessing_views.sql`
3. Test with `python examples/test_preprocessing.py`

### When querying data:
- Use pre-computed views (`lap_aggression_metrics`, `stint_degradation`) for speed
- Filter erroneous laps: `WHERE lap_number < 32768`
- Use `meta_time` instead of `timestamp_ecu` for time-based queries

### When training models:
- Use `src/data_preprocessing.py` for data loading (handles quality issues automatically)
- Features are already normalized (StandardScaler with mean=0, std=1)
- Target variable is `tire_degradation_rate` (seconds per lap)

### File paths:
- Always use relative paths from project root
- Python modules: `from src.data_preprocessing import ...`
- SQL scripts: `sql/views/create_preprocessing_views.sql`
- Data: `ml_data/features_normalized.csv`

## Common Analysis Tasks

- Lap time prediction
- Tire degradation modeling
- Driver style classification
- Optimal racing line analysis
- Telemetry visualization
- Feature importance analysis
- Aggression vs performance tradeoffs

---

For detailed information:
- Database: See [docs/DATABASE.md](docs/DATABASE.md)
- Preprocessing: See [docs/PREPROCESSING.md](docs/PREPROCESSING.md)
- Quick start: See [README.md](README.md)
