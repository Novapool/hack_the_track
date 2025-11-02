# Tire Whisperer - Interactive Tire Degradation Dashboard

AI-Powered tire wear analysis for Toyota GR Cup racing data.

## Quick Start

### Prerequisites
- Python 3.10+ with virtual environment activated
- PostgreSQL database running at localhost:5432
- Database `gr_cup_racing` loaded with racing data

### Run the Dashboard

```bash
# From project root directory
source .venv/bin/activate  # Activate virtual environment

# Start the dashboard
streamlit run hackathon_app/app.py

# Dashboard will open at http://localhost:8501
```

## Dashboard Features

### 🏁 Track Visualization
- Animated racing line on track maps (7 tracks)
- Real-time telemetry charts (speed, brake, G-forces)
- GPS-based degradation heatmap
- AI tire wear predictions

### 🎮 What-If Analysis
- Interactive sliders to adjust driving parameters
- Real-time prediction updates
- AI coaching insights
- Stint projections (15-lap forecasts)

### 👥 Driver Comparison
- Side-by-side driver analysis
- Aggression radar charts
- Efficiency scoring
- Detailed statistics tables

## Architecture

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
│   └── pdf_converter.py            # Track map converter
├── assets/
│   └── track_images/               # PNG track maps (7 tracks)
└── .streamlit/
    └── config.toml                 # Toyota Red theme
```

## Model Performance

- **R² Score**: 0.631 (63% accuracy)
- **MAE**: 0.375 seconds/lap
- **RMSE**: 0.610 seconds/lap
- **Training Data**: 2,036 laps, 23 features
- **Model**: Random Forest Regressor

## Track Coverage

| Track | Total Laps | GPS Laps | Coverage |
|-------|------------|----------|----------|
| Barber | 746 | 530 | 71.0% ✅ |
| COTA | 1,500+ | 0 | 0% |
| Indianapolis | 848 | 526 | 62.0% ⚠️ |
| Road America | 1,800+ | 0 | 0% |
| Sebring | 1,600+ | 0 | 0% |
| Sonoma | 1,700+ | 0 | 0% |
| VIR | 1,600+ | 0 | 0% |

**Note**: Tracks without GPS still show telemetry charts and predictions.

## Troubleshooting

### Dashboard won't start
```bash
# Check virtual environment is activated
which python
# Should show: /path/to/.venv/bin/python

# Verify dependencies installed
pip list | grep streamlit
```

### Database connection error
```bash
# Test database connection
PGPASSWORD=password psql -h localhost -U postgres -d gr_cup_racing -c "SELECT COUNT(*) FROM laps;"

# Expected output: 10864 rows
```

### Track images missing
```bash
# Re-run PDF converter
python -m hackathon_app.utils.pdf_converter

# Verify images exist
ls hackathon_app/assets/track_images/
# Should show: barber.png, cota.png, etc.
```

### Port already in use
```bash
# Kill existing Streamlit
pkill -f streamlit

# Or use different port
streamlit run hackathon_app/app.py --server.port 8502
```

## Demo Flow (10-minute presentation)

### 1. Introduction (1 min)
Show landing page with model stats and track overview.

### 2. Track Visualization (3 min)
- Select Barber Motorsports Park
- Choose a lap with GPS (📍 indicator)
- Show animated racing line
- Point out telemetry charts and degradation prediction

### 3. What-If Analysis (3 min)
- Load same lap as baseline
- Adjust brake pressure slider (-20%)
- Show prediction change and savings
- Highlight coaching insights

### 4. Driver Comparison (2 min)
- Select two different vehicles
- Show radar chart and efficiency scores
- Explain tire management differences

### 5. Q&A (1 min)
Answer technical questions about model, data, and implementation.

## Configuration

### Database Connection
Edit `utils/data_loader.py` to change database settings:
```python
DB_CONFIG = {
    'host': 'localhost',
    'database': 'gr_cup_racing',
    'user': 'postgres',
    'password': 'password',
    'port': 5432
}
```

### Theme Customization
Edit `.streamlit/config.toml` to change colors and styling.

## Tech Stack

- **Frontend**: Streamlit 1.31.0
- **Visualization**: Plotly, Matplotlib
- **ML**: scikit-learn (Random Forest)
- **Database**: PostgreSQL (psycopg2)
- **Data Processing**: pandas, numpy

## Performance Optimization

The dashboard uses Streamlit's caching extensively:

- **`@st.cache_data(ttl=600)`**: Database queries cached for 10 minutes
- **`@st.cache_resource`**: ML model loaded once and reused
- **GPS resampling**: Large GPS datasets downsampled for smooth rendering

## Future Enhancements

- Live data streaming from races
- Mobile app companion
- Multi-lap stint analysis
- SHAP feature importance
- Export features (PDF reports, CSV)

## Support

For issues, see full documentation:
- [docs/HACKATHON_DASHBOARD.md](../docs/HACKATHON_DASHBOARD.md) - Complete implementation guide
- [docs/DATABASE.md](../docs/DATABASE.md) - Database schema and queries
- [docs/PREPROCESSING.md](../docs/PREPROCESSING.md) - ML preprocessing pipeline

---

**Built for the Toyota GR Cup hackathon** | Powered by Streamlit & scikit-learn
