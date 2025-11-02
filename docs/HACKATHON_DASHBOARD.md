# 🏁 Tire Whisperer - Interactive Tire Degradation Dashboard

> AI-Powered tire wear analysis for Toyota GR Cup racing data

---

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Setup Instructions](#setup-instructions)
- [Implementation Plan](#implementation-plan)
- [Demo Script](#demo-script)
- [Technical Details](#technical-details)
- [Troubleshooting](#troubleshooting)

---

## Project Overview

### Goal
Build a **simple but impressive** Streamlit dashboard that visualizes tire degradation using our trained Random Forest ML model across all 7 Toyota GR Cup tracks.

### Key Features
- 🏁 **Live Track Visualization** - Animated racing line with real-time degradation overlay
- 🎮 **What-If Analysis** - Interactive sliders to test driving style changes
- 👥 **Driver Comparison** - Side-by-side analysis of tire management efficiency
- 📊 **ML Predictions** - Real-time tire degradation forecasting

### Model Performance
- **R² Score:** 0.631 (63% variance explained)
- **MAE:** 0.375 seconds/lap
- **RMSE:** 0.610 seconds/lap
- **Training Data:** 2,036 laps across 7 tracks
- **Features:** 23 engineered features including weather, driving aggression, stint position

### Tracks Supported
All 7 Toyota GR Cup tracks with PDF maps:
1. **Barber Motorsports Park** (71% laps have GPS ✅)
2. **Circuit of the Americas (COTA)**
3. **Indianapolis Motor Speedway** (62% laps have GPS ⚠️ coordinate issues)
4. **Road America**
5. **Sebring International Raceway**
6. **Sonoma Raceway**
7. **Virginia International Raceway (VIR)**

---

## Architecture

### System Flow
```
┌─────────────────┐
│  PostgreSQL DB  │ (gr_cup_racing)
│  10,864 laps    │
│  23M telemetry  │
└────────┬────────┘
         │
         ↓
┌─────────────────┐      ┌──────────────────┐
│  Data Loader    │ ───→ │  ML Model        │
│  SQL Queries    │      │  Random Forest   │
└────────┬────────┘      │  (23 features)   │
         │               └────────┬─────────┘
         │                        │
         ↓                        ↓
┌─────────────────────────────────────┐
│      Streamlit Dashboard            │
│  ┌───────────┬───────────┬────────┐ │
│  │  Track    │  What-If  │ Driver │ │
│  │  Viz      │  Analysis │  Comp  │ │
│  └───────────┴───────────┴────────┘ │
└─────────────────────────────────────┘
```

### Project Structure
```
hackathon_app/
├── app.py                          # Landing page
├── pages/
│   ├── 1_🏁_Track_Visualization.py  # Animated track view
│   ├── 2_🎮_What_If_Analysis.py     # Interactive analysis
│   └── 3_👥_Driver_Comparison.py    # Driver comparison
├── utils/
│   ├── data_loader.py              # Database queries
│   ├── model_predictor.py          # ML predictions
│   ├── track_plotter.py            # Visualizations
│   └── pdf_converter.py            # Map conversion
├── assets/
│   ├── track_images/               # PNG track maps
│   └── logo/                       # Branding
└── .streamlit/
    └── config.toml                 # Theme config
```

### Tech Stack
- **Frontend:** Streamlit 1.31.0
- **Visualization:** Plotly, Matplotlib
- **ML:** scikit-learn, Random Forest
- **Database:** PostgreSQL (psycopg2)
- **Data:** pandas, numpy
- **Image Processing:** pdf2image, Pillow

---

## Setup Instructions

### Prerequisites
- Python 3.10+
- PostgreSQL database running (localhost:5432)
- Virtual environment activated

### Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Convert track maps (one-time setup):**
```bash
python -m hackathon_app.utils.pdf_converter
```

This converts PDFs in `track_maps/` to PNGs in `hackathon_app/assets/track_images/`

3. **Verify database connection:**
```bash
# Test connection
psql -h localhost -U postgres -d gr_cup_racing -c "SELECT COUNT(*) FROM laps;"
```

### Running the Dashboard

```bash
# Start Streamlit app
streamlit run hackathon_app/app.py

# App will open at http://localhost:8501
```

### Database Configuration
- **Host:** localhost
- **Port:** 5432
- **Database:** gr_cup_racing
- **User:** postgres
- **Password:** password

---

## Implementation Plan

### Phase 0: Documentation ✅ (15 min)
- [x] Create this documentation file
- [ ] Update main README.md
- [ ] Create demo script

### Phase 1: Setup & Infrastructure (30 min)
- [ ] Update requirements.txt with Streamlit dependencies
- [ ] Create hackathon_app/ directory structure
- [ ] Convert PDF track maps to PNG (pdf2image)
- [ ] Configure Streamlit theme (.streamlit/config.toml)

**Dependencies to add:**
```txt
streamlit==1.31.0
streamlit-plotly-events==0.0.6
pdf2image==1.16.3
Pillow==10.2.0
```

### Phase 2: Core Components (2-3 hours)

#### 2.1 Data Loader (`utils/data_loader.py`)
**Functions:**
- `get_available_tracks()` - List tracks with lap counts
- `get_available_laps(track_name)` - Get laps for track
- `load_lap_telemetry(lap_id)` - Full telemetry data
- `load_lap_gps(lap_id)` - GPS coordinates
- `get_vehicle_stats(vehicle_id)` - Driver profile
- `get_lap_features(lap_id)` - ML feature vector

**Caching:** Use `@st.cache_data(ttl=300)` for queries

#### 2.2 Model Predictor (`utils/model_predictor.py`)
**Functions:**
- `load_model()` - Load Random Forest model (cached)
- `predict_degradation(features_df)` - Get predictions
- `predict_lap_degradation(lap_id)` - Predict for lap
- `what_if_prediction(base, adjustments)` - Scenario analysis
- `get_feature_importance()` - Feature rankings

**Model:** `models/tire_degradation_model_random_forest_with_weather.pkl`

#### 2.3 Track Plotter (`utils/track_plotter.py`)
**Functions:**
- `load_track_image(track_name)` - Get PNG background
- `plot_track_with_overlay(track, gps, colors)` - Main viz
- `animate_lap(lap_data, predictions)` - Animation
- `create_degradation_heatmap(gps, values)` - Heat map

**Approaches:**
- **With GPS:** Plot coordinates on track image
- **Without GPS:** Sector-based zones on track image

#### 2.4 PDF Converter (`utils/pdf_converter.py`)
**One-time conversion:**
```python
from pdf2image import convert_from_path

def pdf_to_png(pdf_path, output_path, dpi=300):
    images = convert_from_path(pdf_path, dpi=dpi)
    images[0].save(output_path, 'PNG')
```

### Phase 3: Dashboard Pages (3-4 hours)

#### Landing Page (`app.py`)
**Sections:**
1. Hero with title and branding
2. Quick stats (3 columns):
   - Model R² = 0.631
   - 7 tracks, 10,864 laps
   - 23M telemetry readings
3. How it works (flow diagram)
4. Navigation cards to 3 pages

#### Page 1: Track Visualization
**Features:**
- Track selector (all 7 tracks)
- Lap selector with GPS indicator
- Animated racing line on track map
- Real-time telemetry charts (speed, brake, G-forces)
- Degradation meter with predictions
- Play/pause/speed controls

**Layout:**
```python
col1, col2 = st.columns([3, 1])
with col1:
    # Track map with animation
    # Telemetry charts (4 columns)
with col2:
    # Lap stats
    # Degradation meter
```

#### Page 2: What-If Analysis
**Features:**
- Base lap selector
- Interactive sliders:
  - Brake pressure (-30% to +30%)
  - Cornering speed (-20% to +20%)
  - Steering smoothness (-40% to +40%)
  - Throttle (-20% to +20%)
- Side-by-side track comparison
- Delta metrics table
- AI coaching recommendations

**Key interaction:**
```python
brake_adj = st.slider("Brake Pressure", -30, 30, 0)
modified_features = base_features.copy()
modified_features['avg_brake_front'] *= (1 + brake_adj/100)
new_prediction = predict(modified_features)
```

#### Page 3: Driver Comparison
**Features:**
- Select 2 drivers/vehicles
- Radar chart of aggression profile (6 axes)
- Overlaid track maps
- Statistics table with efficiency scores
- Insights panel with recommendations

**Efficiency Metric:**
```
Efficiency = Lap Time / Tire Degradation Rate
```
Higher = better tire management

### Phase 4: Polish & Hackathon Prep (1-2 hours)

#### Visual Design
**Theme (`.streamlit/config.toml`):**
```toml
[theme]
primaryColor = "#E50000"      # Toyota Red
backgroundColor = "#0E1117"   # Dark
textColor = "#FAFAFA"
font = "sans serif"
```

**Branding:**
- Toyota GR Cup logo
- Red/White/Black color palette
- Professional typography

#### Demo Optimization
- Pre-load best sample lap (Barber 33075)
- Add loading spinners
- Error handling with friendly messages
- Tooltips on all inputs

#### Documentation
- Complete demo script (see below)
- Troubleshooting guide
- Update README.md

### Phase 5: Advanced Features (Optional)
- GPS calibration for accurate overlay
- CSV upload for new data
- Export features (PDF reports, screenshots)
- SHAP feature importance visualization

---

## Demo Script

### Setup (Before Demo)
1. Start Streamlit: `streamlit run hackathon_app/app.py`
2. Open in browser: http://localhost:8501
3. Pre-load Barber Motorsports Park, Lap 33075
4. Test all 3 pages work smoothly

### Presentation Flow (10 minutes)

#### 1. Introduction (1 min)
**What to say:**
> "We built an AI-powered tire degradation analyzer for the Toyota GR Cup racing series. Using machine learning on 23 million telemetry data points, we can predict tire wear and provide real-time coaching to drivers."

**Show:** Landing page with stats

#### 2. Track Visualization (3 min)
**What to say:**
> "Here's Barber Motorsports Park with a real lap. Watch the racing line change color as tire degradation increases. Green is fresh tires, yellow is moderate wear, red is high degradation."

**Demo steps:**
1. Select Barber from dropdown
2. Choose lap 33075 (or best available)
3. Click play to show animation
4. Point out:
   - GPS trace following actual racing line
   - Color changes through corners
   - Telemetry charts updating in real-time
   - Prediction: "0.45 seconds/lap degradation"

**What to say:**
> "Our model predicted this lap would have 0.45 seconds per lap of tire degradation based on the driver's aggression - brake pressure, cornering G-forces, steering inputs."

#### 3. What-If Analysis (3 min)
**What to say:**
> "Now the cool part - what if the driver changed their style? Let's reduce brake pressure by 20%."

**Demo steps:**
1. Switch to What-If Analysis page
2. Load same lap as baseline
3. Move brake pressure slider to -20%
4. Show prediction update in real-time
5. Highlight delta: "Saves 0.12 seconds/lap in wear"

**What to say:**
> "By braking softer, we predict saving 0.12 seconds per lap in tire degradation. Over a 15-lap stint, that's 1.8 seconds of extra tire life - potentially an extra lap before pitting."

#### 4. Driver Comparison (2 min)
**What to say:**
> "We can also compare drivers to see who manages tires better."

**Demo steps:**
1. Switch to Driver Comparison page
2. Select two different vehicles
3. Show radar chart: "Driver A is more aggressive in braking"
4. Show efficiency score: "Driver B is 12% more efficient"

**What to say:**
> "The radar chart shows Driver A brakes harder and corners faster, but Driver B is 12% more efficient - getting similar lap times with less tire wear."

#### 5. Technical Highlights (1 min)
**What to say:**
> "Technically, we:
> - Trained a Random Forest model on 2,036 laps with 23 engineered features
> - Achieved 63% R² accuracy by integrating weather data
> - Built a hybrid SQL/Python pipeline processing 23 million telemetry readings
> - Created an interactive Streamlit dashboard for real-time predictions"

**Show:** Can switch between pages to highlight features

#### 6. Q&A (2-3 min)
**Anticipated questions:**

**Q:** "How accurate is your model?"
**A:** "63% R² score, meaning we explain 63% of tire degradation variance. The remaining 37% is likely tire compound differences, fuel load, and measurement noise not in our dataset."

**Q:** "What data did you use?"
**A:** "Real Toyota GR Cup telemetry from 7 race tracks - 10,864 laps, 23 million data points. Features include brake pressure, G-forces, speed, weather conditions, and driving patterns."

**Q:** "Can this be used in real racing?"
**A:** "Absolutely. Teams could use this for pit strategy optimization, driver coaching, and real-time tire management during races."

**Q:** "What's next?"
**A:** "We'd like to add live data streaming, integrate with team radios for real-time coaching, and expand to other racing series."

---

## Technical Details

### Database Schema
**Key Tables:**
- `laps` - Lap timing and metadata (10,864 rows)
- `telemetry_readings` - High-frequency sensor data (23M rows)
- `weather_data` - Track conditions (567 rows)
- `tracks` - Circuit information (7 tracks)
- `vehicles` - Race cars (59 unique vehicles)

**Useful Queries:**
```sql
-- Get laps with GPS data for Barber
SELECT lap_id, lap_number, lap_duration
FROM laps l
JOIN sessions s ON l.session_id = s.session_id
JOIN races r ON s.race_id = r.race_id
JOIN tracks t ON r.track_id = t.track_id
WHERE t.track_name = 'barber'
  AND l.lap_number < 32768
  AND EXISTS (
    SELECT 1 FROM telemetry_readings tr
    WHERE tr.lap_id = l.lap_id
    AND tr.vbox_lat_min IS NOT NULL
  );
```

### ML Model Details

**Model Type:** Random Forest Regressor

**Hyperparameters:**
- n_estimators: 100
- max_depth: 15
- min_samples_split: 5
- random_state: 42

**Input Features (23):**
1. `air_temp` - Air temperature (°C)
2. `track_temp` - Track surface temp (°C)
3. `humidity` - Relative humidity (%)
4. `wind_speed` - Wind speed (km/h)
5. `temp_delta` - Track - Air temp delta
6. `avg_brake_front` - Average front brake pressure (bar)
7. `max_brake_front` - Max front brake pressure
8. `avg_brake_rear` - Average rear brake pressure
9. `max_brake_rear` - Max rear brake pressure
10. `avg_lateral_g` - Average cornering G-force
11. `max_lateral_g` - Max cornering G-force
12. `avg_long_g` - Average longitudinal G-force
13. `max_accel_g` - Max acceleration G-force
14. `max_brake_g` - Max braking G-force (negative)
15. `steering_variance` - Steering smoothness
16. `avg_steering_angle` - Average steering input
17. `avg_throttle_blade` - Throttle position
18. `avg_speed` - Average lap speed (km/h)
19. `max_speed` - Top speed
20. `min_speed` - Slowest corner
21. `avg_rpm` - Engine RPM
22. `max_rpm` - Peak RPM
23. `lap_in_stint` - Lap number in current stint

**Target Variable:**
- `tire_degradation_rate` - Lap time increase over rolling 5-lap window (seconds)

**Performance Metrics:**
- **R² Score:** 0.6308
- **MAE:** 0.3751 seconds
- **RMSE:** 0.6098 seconds
- **Cross-Validation (5-fold):** 0.6339 ± 0.0309

**Feature Importance (Top 5):**
1. avg_lateral_g: 24.3%
2. lap_in_stint: 16.4%
3. air_temp: 9.2%
4. track_temp: 8.7%
5. avg_rpm: 4.1%

### GPS Data Coverage

**Barber Motorsports Park (BEST):**
- 530 laps with GPS (71% coverage)
- 96.67% of telemetry has coordinates
- Latitude: 33.5290 to 33.5359 (770m span)
- Longitude: -86.6244 to -86.6144 (890m span)
- ~7,256 GPS points per lap
- Clean, continuous traces

**Indianapolis Motor Speedway:**
- 526 laps with GPS (62% coverage)
- 96.37% of telemetry has coordinates
- ⚠️ Coordinate format issues (spans Indiana to Caribbean)
- Needs investigation/calibration

**Other Tracks:**
- No GPS data available
- Fallback: Use track images with sector-based analysis

### Color Scales

**Degradation Heatmap:**
- **Green (0.0-0.2 sec):** Fresh tires, minimal wear
- **Yellow (0.2-0.5 sec):** Moderate degradation
- **Orange (0.5-0.8 sec):** High wear
- **Red (0.8+ sec):** Critical degradation

**Plotly Colorscale:** `'RdYlGn_r'` (Red-Yellow-Green reversed)

### File Paths

**Track Maps:**
- Source PDFs: `/home/laith/Projects/hack_the_track/track_maps/*.pdf`
- Generated PNGs: `/home/laith/Projects/hack_the_track/hackathon_app/assets/track_images/*.png`

**Model:**
- Trained model: `/home/laith/Projects/hack_the_track/models/tire_degradation_model_random_forest_with_weather.pkl`
- Metadata: `/home/laith/Projects/hack_the_track/models/model_metadata_with_weather.json`

**Data:**
- Features CSV: `/home/laith/Projects/hack_the_track/ml_data/features_with_weather.csv`
- Targets CSV: `/home/laith/Projects/hack_the_track/ml_data/target_with_weather.csv`

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Failed
**Error:** `psycopg2.OperationalError: connection to server failed`

**Solution:**
```bash
# Check PostgreSQL is running
sudo service postgresql status

# Test connection
psql -h localhost -U postgres -d gr_cup_racing

# If password error, verify password is "password"
```

#### 2. Model File Not Found
**Error:** `FileNotFoundError: tire_degradation_model_random_forest_with_weather.pkl`

**Solution:**
```bash
# Verify model exists
ls models/tire_degradation_model_random_forest_with_weather.pkl

# If missing, retrain model
python scripts/train_with_weather.py
```

#### 3. Track Images Missing
**Error:** `FileNotFoundError: track image not found`

**Solution:**
```bash
# Convert PDFs to PNGs
python -m hackathon_app.utils.pdf_converter

# Verify images generated
ls hackathon_app/assets/track_images/
```

#### 4. No GPS Data for Lap
**Warning:** "This lap doesn't have GPS data"

**Solution:**
- Expected behavior for non-Barber tracks
- Dashboard falls back to telemetry-only view
- Use sector-based visualization with track image

#### 5. Streamlit Port Already in Use
**Error:** `OSError: [Errno 98] Address already in use`

**Solution:**
```bash
# Kill existing Streamlit processes
pkill -f streamlit

# Or use different port
streamlit run hackathon_app/app.py --server.port 8502
```

#### 6. Slow Loading
**Issue:** Dashboard takes 10+ seconds to load

**Solution:**
- Add `@st.cache_data` to database queries
- Reduce animation frame count (resample GPS data)
- Pre-load frequently accessed laps
- Use `@st.cache_resource` for model loading

### Performance Tips

**Database Queries:**
```python
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_lap_data(lap_id):
    # Query here
    return df
```

**Model Loading:**
```python
@st.cache_resource
def load_ml_model():
    return joblib.load('models/tire_degradation_model_random_forest_with_weather.pkl')
```

**Animation Optimization:**
```python
# Resample GPS data for smoother playback
if len(gps_data) > 1000:
    gps_data = gps_data.iloc[::len(gps_data)//1000]
```

### Debug Mode

**Enable Streamlit debug info:**
```bash
streamlit run hackathon_app/app.py --logger.level=debug
```

**Add debug panel in app:**
```python
if st.checkbox("Show Debug Info"):
    st.write("Session State:", st.session_state)
    st.write("Selected Lap:", selected_lap)
```

---

## Development Roadmap

### Current Phase (Week 1)
- [x] Phase 0: Documentation
- [ ] Phase 1: Setup
- [ ] Phase 2: Core utilities
- [ ] Phase 3: Dashboard pages
- [ ] Phase 4: Polish

### Future Enhancements
- **Live Data Integration:** Stream telemetry from races in real-time
- **Team Radio Integration:** Push predictions to driver/team
- **Multi-Series Support:** Expand to other racing series
- **Mobile App:** iOS/Android companion app
- **Cloud Deployment:** Host on AWS/Azure for remote access
- **API Access:** REST API for third-party integrations

### Research Directions
- **Deep Learning:** LSTM models for time-series prediction
- **Computer Vision:** Analyze onboard camera for racing line optimization
- **Reinforcement Learning:** Optimal driving policy learning
- **Causal Inference:** Identify causal relationships in tire degradation

---

## Contributing

This is a hackathon project, but improvements are welcome!

**Areas for contribution:**
- GPS calibration for non-Barber tracks
- Additional visualization modes
- Performance optimizations
- UI/UX improvements
- Documentation enhancements

---

## License

This project is part of the Toyota Gazoo Racing hackathon.

---

## Acknowledgments

- **Toyota Gazoo Racing** for providing the dataset
- **SRO Motorsports** for the GR Cup racing series
- **Streamlit** for the amazing dashboard framework
- **Plotly** for interactive visualizations

---

**Built with ❤️ for the Toyota GR Cup hackathon**
