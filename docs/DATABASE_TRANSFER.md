# Database Transfer Guide: Mac → Windows

This guide explains how to transfer the Toyota GR Cup PostgreSQL database from your Mac to your Windows machine for GPU-accelerated ML training.

## Overview

**Why transfer?**
- Windows machine has CUDA-enabled GPU for faster ML training
- XGBoost and other ML libraries can leverage GPU acceleration
- Maintain synchronized database across development environments

**Transfer Method**: PostgreSQL backup/restore using `pg_dump` and `pg_restore`

---

## Part 1: Create Backup on Mac

### Step 1: Run Backup Script

From the project root directory on your Mac:

```bash
./backup_database.sh
```

**What this does:**
- Creates a compressed SQL dump of the `gr_cup_racing` database
- Saves to `database_backup/gr_cup_racing_backup_YYYYMMDD_HHMMSS.sql.gz`
- Displays database statistics and verification info

**Expected output:**
```
==================================================
  Toyota GR Cup Database Backup
==================================================

✓ PostgreSQL is running
✓ Backup created successfully!
✓ Backup compressed successfully!

Backup file: ./database_backup/gr_cup_racing_backup_20250101_120000.sql.gz
Compressed size: ~50-100 MB (depending on data)
```

### Step 2: Locate Backup File

The backup is saved in:
```
hack_the_track/database_backup/gr_cup_racing_backup_YYYYMMDD_HHMMSS.sql.gz
```

### Step 3: Transfer to Windows

**Option A: USB Drive**
1. Copy the `.sql.gz` file to a USB drive
2. Transfer to Windows machine

**Option B: Cloud Storage**
1. Upload to Google Drive / Dropbox / OneDrive
2. Download on Windows machine

**Option C: Network Transfer**
1. Use `scp`, `rsync`, or file sharing
2. Transfer directly over network

---

## Part 2: PostgreSQL Setup on Windows

### Step 1: Install PostgreSQL

**Download PostgreSQL 16 (or latest stable)**
- Website: https://www.postgresql.org/download/windows/
- Installer: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads

**Installation options:**
- ✅ PostgreSQL Server (required)
- ✅ pgAdmin 4 (GUI tool - recommended)
- ✅ Command Line Tools (required)
- ❌ Stack Builder (optional)

**Important settings:**
- **Superuser password**: Leave blank (or use same as Mac for consistency)
- **Port**: 5432 (default)
- **Locale**: Default

### Step 2: Verify Installation

Open **Command Prompt** or **PowerShell**:

```powershell
# Check PostgreSQL version
psql --version

# Test connection
psql -U postgres -h localhost
```

If connection works, type `\q` to exit.

**Troubleshooting:**
- If `psql` command not found, add to PATH:
  - Default location: `C:\Program Files\PostgreSQL\16\bin`
  - Add to System Environment Variables → Path

---

## Part 3: Restore Database on Windows

### Step 1: Extract Backup File

**Option A: Using 7-Zip (recommended)**
1. Install 7-Zip: https://www.7-zip.org/
2. Right-click `.sql.gz` file → 7-Zip → Extract Here
3. Result: `gr_cup_racing_backup_YYYYMMDD_HHMMSS.sql`

**Option B: Using Command Line (if gzip installed)**
```powershell
gzip -d gr_cup_racing_backup_YYYYMMDD_HHMMSS.sql.gz
```

### Step 2: Create Database

Open **Command Prompt** or **PowerShell**:

```powershell
# Create empty database
psql -U postgres -h localhost -c "CREATE DATABASE gr_cup_racing;"
```

**Expected output:**
```
CREATE DATABASE
```

### Step 3: Restore Data

```powershell
# Navigate to backup directory
cd C:\path\to\backup\file

# Restore database (replace with your actual filename)
psql -U postgres -h localhost -d gr_cup_racing -f gr_cup_racing_backup_YYYYMMDD_HHMMSS.sql
```

**This will take 2-5 minutes** depending on data size.

**Expected output:**
```
SET
SET
CREATE TABLE
CREATE TABLE
...
COPY 3257  (laps loaded)
COPY 1234567  (telemetry readings loaded)
...
```

### Step 4: Verify Data Integrity

```powershell
psql -U postgres -h localhost -d gr_cup_racing
```

Inside PostgreSQL prompt:

```sql
-- Check tables exist
\dt

-- Verify row counts
SELECT 'laps' as table_name, COUNT(*) as rows FROM laps
UNION ALL
SELECT 'telemetry_readings', COUNT(*) FROM telemetry_readings
UNION ALL
SELECT 'sessions', COUNT(*) FROM sessions
UNION ALL
SELECT 'races', COUNT(*) FROM races;

-- Check views exist
\dv

-- Test preprocessing view
SELECT COUNT(*) FROM lap_aggression_metrics;

-- Exit
\q
```

**Expected row counts** (should match Mac):
- `laps`: 3,257
- `telemetry_readings`: ~1-2 million (varies by track data)
- `sessions`: 10-20
- `races`: 8
- `lap_aggression_metrics` (view): 2,545

---

## Part 4: Python Environment Setup on Windows

### Step 1: Install Python (if not already installed)

- Download Python 3.11+ from https://www.python.org/downloads/
- ✅ Check "Add Python to PATH" during installation

### Step 2: Create Virtual Environment

```powershell
# Navigate to project directory
cd C:\path\to\hack_the_track

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\activate
```

### Step 3: Install Dependencies

```powershell
# Install standard requirements
pip install -r requirements.txt

# Install GPU-enabled requirements
pip install -r requirements-gpu.txt
```

**Note**: `requirements-gpu.txt` includes:
- XGBoost with CUDA support
- CuPy (CUDA-accelerated NumPy)
- GPU-specific configurations

---

## Part 5: CUDA Setup for GPU Training

### Step 1: Check GPU Compatibility

```powershell
# Check NVIDIA GPU
nvidia-smi
```

**Requirements:**
- NVIDIA GPU (GTX 1060 or better recommended)
- CUDA Compute Capability 3.5+ (check: https://developer.nvidia.com/cuda-gpus)

### Step 2: Install NVIDIA Drivers

- Latest drivers: https://www.nvidia.com/Download/index.aspx
- Or use GeForce Experience for automatic updates

### Step 3: Install CUDA Toolkit

**XGBoost 2.0+ includes CUDA runtime** - you don't need to install CUDA Toolkit separately!

However, for optimal performance (optional):
- Download CUDA 12.x: https://developer.nvidia.com/cuda-downloads
- Follow Windows installation instructions

### Step 4: Verify GPU in Python

```python
import xgboost as xgb

# Check XGBoost GPU support
print(xgb.build_info())
print(f"GPU available: {xgb.build_info()['USE_CUDA']}")
```

**Expected output:**
```python
{'USE_CUDA': True, 'CUDA_VERSION': '12.x', ...}
GPU available: True
```

---

## Part 6: Test ML Training on Windows

### Step 1: Open Jupyter Notebook

```powershell
# Activate virtual environment
.venv\Scripts\activate

# Launch Jupyter
jupyter notebook
```

### Step 2: Open Training Notebook

Navigate to: `notebooks/model_training_exploration.ipynb`

### Step 3: Enable GPU in XGBoost

In the notebook, find the XGBoost model configuration and change:

```python
'XGBoost': xgb.XGBRegressor(
    n_estimators=100,
    learning_rate=0.1,
    max_depth=5,
    random_state=42,
    tree_method='gpu_hist',  # ← Change from 'auto' to 'gpu_hist'
    predictor='gpu_predictor',  # ← Add this line
    n_jobs=1  # ← Change from -1 to 1 (GPU handles parallelization)
)
```

### Step 4: Run Training

Execute all cells in the notebook. You should see:
- **Faster training times** for XGBoost (2-10x speedup)
- GPU memory usage in `nvidia-smi`
- Model performance metrics

**Benchmark comparison:**
- Mac (CPU): ~5-10 seconds for XGBoost training
- Windows (GPU): ~1-2 seconds for XGBoost training

---

## Part 7: Keep Databases in Sync

### Option A: Re-run Backup/Restore

When data changes on Mac:
1. Run `./backup_database.sh` on Mac
2. Transfer new backup to Windows
3. Drop and recreate database on Windows:
   ```powershell
   psql -U postgres -h localhost -c "DROP DATABASE gr_cup_racing;"
   psql -U postgres -h localhost -c "CREATE DATABASE gr_cup_racing;"
   psql -U postgres -h localhost -d gr_cup_racing -f new_backup.sql
   ```

### Option B: Use ML Data CSVs Only

For ML training, you don't need the full database on Windows!

**Simplified approach:**
1. On Mac: Generate preprocessed CSVs (already done)
2. Transfer only `ml_data/` folder to Windows
3. Load CSVs directly in notebook (no database required)

**In notebook:**
```python
# No database connection needed!
X = pd.read_csv('../ml_data/features_normalized.csv')
y = pd.read_csv('../ml_data/target_degradation.csv')['tire_degradation_rate']
```

This is the **fastest approach** for ML training.

---

## Troubleshooting

### Issue: "psql: command not found" on Windows

**Solution**: Add PostgreSQL to PATH
1. Search "Environment Variables" in Windows
2. Edit "Path" under System Variables
3. Add: `C:\Program Files\PostgreSQL\16\bin`
4. Restart terminal

### Issue: "permission denied for database"

**Solution**: Use superuser account
```powershell
psql -U postgres -h localhost
```

### Issue: "database already exists"

**Solution**: Drop existing database first
```powershell
psql -U postgres -h localhost -c "DROP DATABASE gr_cup_racing;"
```

### Issue: XGBoost not using GPU

**Check 1**: Verify CUDA availability
```python
import xgboost as xgb
print(xgb.build_info())
```

**Check 2**: Ensure correct tree_method
```python
model = xgb.XGBRegressor(tree_method='gpu_hist')
```

**Check 3**: Monitor GPU usage
```powershell
nvidia-smi -l 1  # Update every 1 second
```

### Issue: Out of memory on GPU

**Solution**: Reduce batch size or use CPU fallback
```python
# Reduce n_estimators or max_depth
model = xgb.XGBRegressor(
    n_estimators=50,  # Reduced from 100
    max_depth=3,      # Reduced from 5
    tree_method='gpu_hist'
)
```

---

## Quick Reference

### Mac: Create Backup
```bash
cd ~/Documents/Programs/hack_the_track
./backup_database.sh
```

### Windows: Restore Database
```powershell
# Extract backup
7z e gr_cup_racing_backup_YYYYMMDD_HHMMSS.sql.gz

# Create database
psql -U postgres -h localhost -c "CREATE DATABASE gr_cup_racing;"

# Restore data
psql -U postgres -h localhost -d gr_cup_racing -f gr_cup_racing_backup_YYYYMMDD_HHMMSS.sql

# Verify
psql -U postgres -h localhost -d gr_cup_racing -c "SELECT COUNT(*) FROM laps;"
```

### Windows: Test GPU
```powershell
# Activate environment
.venv\Scripts\activate

# Check GPU
python -c "import xgboost as xgb; print(xgb.build_info()['USE_CUDA'])"

# Monitor GPU
nvidia-smi -l 1
```

---

## Performance Tips

1. **Use GPU for large datasets** (>10k samples)
   - XGBoost GPU speedup: 2-10x
   - Training time: 5 seconds → 0.5 seconds

2. **Use CPU for small datasets** (<5k samples)
   - Overhead of GPU initialization not worth it
   - CPU may be faster for 2,545 samples

3. **Optimize GPU memory**
   - Close unnecessary applications
   - Monitor with `nvidia-smi`
   - Reduce model complexity if OOM errors occur

4. **Experiment with tree_method**
   - `gpu_hist`: GPU histogram-based (fastest)
   - `auto`: XGBoost chooses automatically
   - `hist`: CPU histogram-based (fallback)

---

## Additional Resources

- **PostgreSQL Documentation**: https://www.postgresql.org/docs/
- **XGBoost GPU Support**: https://xgboost.readthedocs.io/en/stable/gpu/index.html
- **CUDA Installation Guide**: https://docs.nvidia.com/cuda/cuda-installation-guide-microsoft-windows/
- **Project README**: `../README.md`
- **Database Documentation**: `DATABASE.md`
- **Preprocessing Guide**: `PREPROCESSING.md`

---

## Summary Checklist

### Mac (Source)
- [ ] Run `./backup_database.sh`
- [ ] Verify backup file created
- [ ] Transfer backup to Windows

### Windows (Target)
- [ ] Install PostgreSQL
- [ ] Extract backup file
- [ ] Create database
- [ ] Restore data
- [ ] Verify row counts
- [ ] Install Python dependencies
- [ ] Install GPU requirements
- [ ] Verify CUDA/GPU support
- [ ] Test ML training with GPU

### Validation
- [ ] Database row counts match
- [ ] Preprocessing views exist
- [ ] Jupyter notebook runs
- [ ] GPU training works (if applicable)
- [ ] Model metrics comparable to Mac

---

**Need Help?**
- Check PostgreSQL logs: `C:\Program Files\PostgreSQL\16\data\log\`
- Check Python errors in Jupyter notebook
- Verify CUDA installation: `nvidia-smi`
- Consult project documentation in `docs/`
