# Toyota GR Cup Racing - Telemetry Analysis Project

> Hackathon project for analyzing motorsport telemetry data from the Toyota Gazoo Racing GR Cup series

## Project Overview

This project analyzes race telemetry data from 7 tracks (Barber, COTA, Indianapolis, Road America, Sebring, Sonoma, VIR) with a focus on tire degradation modeling. The dataset includes high-frequency telemetry, lap timing, and race results stored in PostgreSQL with ML-ready preprocessing pipelines.

**Status**: ✅ Database loaded (3,257 laps) | ✅ ML Model trained (R² = 0.631) | 🎨 Interactive Dashboard

## Quick Start

### Prerequisites
- Python 3.9+
- PostgreSQL 14+
- 100+ GB disk space

### Setup

```bash
# 1. Clone and navigate to project
cd hack_the_track

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Connect to database
psql -h localhost -U postgres -d gr_cup_racing
```

### Usage Example

```python
from src.data_preprocessing import TireDegradationPreprocessor

# Configure database connection
db_config = {
    'host': 'localhost',
    'database': 'gr_cup_racing',
    'user': 'postgres',
    'password': ''
}

# Initialize preprocessor
preprocessor = TireDegradationPreprocessor(db_config)

# Get normalized training data (one line!)
X, y = preprocessor.prepare_training_data(
    normalization_method='standard',  # Z-score normalization
    outlier_threshold=3.0
)

# Train your model
from sklearn.ensemble import RandomForestRegressor
model = RandomForestRegressor()
model.fit(X, y)
```

## 🏁 Interactive Tire Degradation Dashboard

**NEW!** Interactive Streamlit dashboard for visualizing tire degradation predictions in real-time.

### Features
- 🏁 **Live Track Visualization** - Animated racing line with degradation overlay on all 7 tracks
- 🎮 **What-If Analysis** - Interactive sliders to test driving style changes
- 👥 **Driver Comparison** - Side-by-side tire management analysis
- 📊 **ML Predictions** - Real-time tire wear forecasting using Random Forest model

### Quick Start

```bash
# Install dashboard dependencies
pip install -r requirements.txt

# Run the dashboard
streamlit run hackathon_app/app.py

# Open browser to http://localhost:8501
```

### Model Performance
- **R² Score:** 0.631 (63% accuracy)
- **MAE:** 0.375 seconds/lap
- **Training Data:** 2,036 laps, 23 features
- **Features:** Weather conditions, driving aggression, stint position

### Demo Flow
1. **Track Visualization** - Watch animated laps with degradation heatmap
2. **What-If Scenarios** - "What if I brake 20% softer?" → See prediction change
3. **Driver Comparison** - Compare tire management efficiency between drivers

📖 **Full Documentation:** [docs/HACKATHON_DASHBOARD.md](docs/HACKATHON_DASHBOARD.md)

## Project Structure

```
hack_the_track/
├── README.md                  # This file - project overview
├── requirements.txt           # Python dependencies
├── db_config.yaml            # Database configuration
├── Hackathon 2025.pdf        # Challenge documentation
│
├── hackathon_app/            # 🎨 Interactive Dashboard (NEW!)
│   ├── app.py                # Main Streamlit landing page
│   ├── pages/                # Dashboard pages
│   │   ├── 1_🏁_Track_Visualization.py
│   │   ├── 2_🎮_What_If_Analysis.py
│   │   └── 3_👥_Driver_Comparison.py
│   ├── utils/                # Dashboard utilities
│   │   ├── data_loader.py    # Database queries
│   │   ├── model_predictor.py # ML predictions
│   │   └── track_plotter.py  # Visualizations
│   └── assets/               # Track images and branding
│
├── docs/                     # Detailed documentation
│   ├── DATABASE.md           # Database schema, ETL, querying
│   ├── PREPROCESSING.md      # ML preprocessing pipeline
│   └── HACKATHON_DASHBOARD.md # Dashboard documentation (NEW!)
│
├── models/                   # Trained ML models
│   ├── tire_degradation_model_random_forest_with_weather.pkl
│   └── model_metadata_with_weather.json
│
├── src/                      # Source code
│   └── data_preprocessing.py # TireDegradationPreprocessor class
│
├── sql/                      # SQL scripts
│   ├── schema/
│   │   └── schema.sql        # Database schema definition
│   ├── views/
│   │   └── create_preprocessing_views.sql  # ML views
│   └── queries/
│       └── ml_queries.sql    # Example queries
│
├── ml_data/                  # Processed ML datasets
│   ├── features_normalized.csv
│   ├── target_degradation.csv
│   ├── features_with_weather.csv (NEW!)
│   └── target_with_weather.csv   (NEW!)
│
├── track_maps/               # Track circuit maps (PDFs)
│
├── notebooks/                # Jupyter notebooks
│   └── model_training_exploration.ipynb
│
├── scripts/                  # Training scripts
│   └── train_with_weather.py
│
├── examples/                 # Example usage
│   └── test_preprocessing.py # Demo preprocessing pipeline
│
└── archive/                  # Historical scripts
    ├── etl_scripts/          # Data migration scripts
    ├── column_data/          # CSV metadata
    └── logs/                 # ETL logs
```

## Key Features

### 🚀 Hybrid SQL/Python Preprocessing
- **10x faster** than pure Python (0.5s vs 15s for 10k laps)
- SQL pre-aggregates telemetry into lap-level features
- Python handles normalization & ML pipelines

### 🏎️ Tire Degradation Analysis
- 21 aggression metrics per lap (brake pressure, lateral G's, steering smoothness)
- Automatic outlier filtering & data quality checks
- Target variable: lap time degradation over stint

### 📊 Pre-computed SQL Views
- `lap_aggression_metrics`: Lap-level telemetry features
- `stint_degradation`: Tire degradation indicators
- `vehicle_aggression_profile`: Driving style summaries

## Data Architecture

### Database

**PostgreSQL**: `gr_cup_racing`
- **Tables**: tracks, races, sessions, laps, telemetry_readings (100M+ rows)
- **Views**: 3 pre-computed views for fast ML data retrieval
- **Indexes**: Optimized for vehicle_id, lap_id, meta_time queries

### Telemetry Parameters

**Aggression Metrics:**
- `pbrake_f`, `pbrake_r` - Front/rear brake pressure (bar)
- `accy_can` - Lateral G forces (cornering aggression)
- `accx_can` - Longitudinal acceleration/braking
- `Steering_Angle` - Steering wheel angle (smoothness)
- `aps`, `ath` - Throttle pedal & blade position

**Speed & Engine:**
- `Speed` - Vehicle speed (km/h)
- `Gear` - Current gear selection
- `nmot` - Engine RPM

**Position:**
- `VBOX_Long_Minutes`, `VBOX_Lat_Min` - GPS coordinates
- `Laptrigger_lapdist_dls` - Distance from start/finish (m)

### Data Quality Notes

⚠️ **Known Issues** (handled automatically):
- Lap #32768: Erroneous lap count (filtered)
- ECU timestamps may be inaccurate (we use `meta_time`)
- Vehicle IDs tracked by chassis number for consistency

See `Hackathon 2025.pdf` for complete data specifications.

## Common Workflows

### Explore Data
```bash
# Run example script
python examples/test_preprocessing.py

# Query database directly
psql -h localhost -U postgres -d gr_cup_racing
```

### Train ML Model
```python
# See examples/test_preprocessing.py for complete example
from src.data_preprocessing import TireDegradationPreprocessor

preprocessor = TireDegradationPreprocessor(db_config)
X, y = preprocessor.prepare_training_data()

# Your model training code here...
```

### Create SQL Views
```bash
# Views are already created, but to recreate:
psql -h localhost -U postgres -d gr_cup_racing -f sql/views/create_preprocessing_views.sql
```

## Documentation

- **[docs/HACKATHON_DASHBOARD.md](docs/HACKATHON_DASHBOARD.md)** - 🎨 Interactive dashboard guide (NEW!)
- **[docs/DATABASE.md](docs/DATABASE.md)** - Database schema, ETL pipeline, SQL queries
- **[docs/PREPROCESSING.md](docs/PREPROCESSING.md)** - ML preprocessing, feature engineering, API reference
- **[Hackathon 2025.pdf](Hackathon%202025.pdf)** - Official challenge documentation

## Dependencies

- **Data Processing**: pandas, numpy
- **Visualization**: matplotlib, seaborn, plotly
- **Database**: sqlalchemy, psycopg2-binary
- **Machine Learning**: scikit-learn
- **Config**: PyYAML, tqdm, tabulate

Install all: `pip install -r requirements.txt`

## Database Connection

**Server Name**: GR Cup Racing

```python
db_config = {
    'host': 'localhost',
    'database': 'gr_cup_racing',
    'user': 'postgres',
    'password': ''  # Update if password-protected
}
```

**Command Line**:
```bash
psql -h localhost -U postgres -d gr_cup_racing
```

## Performance

| Operation | Time | Dataset Size |
|-----------|------|--------------|
| Load lap features (SQL) | ~0.5s | 2,545 laps |
| Normalize features (Python) | ~1s | 21 features |
| **Total preprocessing** | **~1.5s** | ✅ **10x faster** than pandas |

## Next Steps

1. ✅ **Database loaded** - 3,257 laps from 8 races
2. ✅ **Preprocessing ready** - SQL views + Python pipeline
3. ⏭️ **Train models** - RandomForest, XGBoost, Neural Networks
4. ⏭️ **Optimize** - Find optimal aggression level per track
5. ⏭️ **Visualize** - Plot aggression vs degradation curves

## External Resources

- **Series**: SRO Motorsports
- **2025 Season**: Search "TGRNA GR CUP NORTH AMERICA"
- **2024 Season**: Search "Toyota GR Cup"
- **Official Timing**: Available through SRO website

## Project Context

This is hackathon data for analyzing Toyota GR86 Cup racing performance. Common analysis tasks:
- Lap time prediction
- Tire degradation modeling
- Driver style classification
- Optimal racing line analysis
- Telemetry visualization

---

**Good luck with your racing data analysis!** 🏁

For detailed documentation, see:
- [Database Guide](docs/DATABASE.md)
- [Preprocessing Guide](docs/PREPROCESSING.md)
