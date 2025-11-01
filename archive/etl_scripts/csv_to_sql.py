#!/usr/bin/env python3
"""
Toyota GR Cup Racing Data ETL Pipeline
Migrates CSV data to PostgreSQL database

Usage:
    python csv_to_sql.py --config db_config.yaml [--track TRACK_NAME] [--dry-run]
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import re

import pandas as pd
import numpy as np
import yaml
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from tqdm import tqdm


class RacingDataETL:
    """ETL pipeline for racing data migration to PostgreSQL"""

    def __init__(self, config_path: str):
        """Initialize ETL pipeline with configuration"""
        self.config = self._load_config(config_path)
        self.engine = self._create_db_engine()
        self.Session = sessionmaker(bind=self.engine)
        self.logger = self._setup_logging()

        # Track data directory
        self.data_dir = Path(self.config['etl']['data_directory'])

        # Statistics
        self.stats = {
            'tracks': 0,
            'races': 0,
            'vehicles': 0,
            'drivers': 0,
            'sessions': 0,
            'laps': 0,
            'telemetry': 0,
            'results': 0,
            'sectors': 0,
            'weather': 0,
        }

    def _load_config(self, config_path: str) -> dict:
        """Load YAML configuration file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    def _create_db_engine(self):
        """Create SQLAlchemy database engine"""
        db_config = self.config['database']
        conn_string = (
            f"postgresql://{db_config['user']}:{db_config['password']}"
            f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
        )

        engine = create_engine(
            conn_string,
            poolclass=QueuePool,
            pool_size=db_config['pool']['min_connections'],
            max_overflow=db_config['pool']['max_connections'] - db_config['pool']['min_connections'],
            pool_recycle=db_config['pool']['pool_recycle']
        )
        return engine

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        log_config = self.config['etl']['logging']
        log_level = getattr(logging, log_config['level'])

        # Create logs directory if it doesn't exist
        log_file = Path(log_config['log_file'])
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Configure logging
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout) if log_config['console_output'] else logging.NullHandler()
            ]
        )
        return logging.getLogger(__name__)

    def run(self, track_filter: Optional[str] = None, dry_run: bool = False):
        """Execute the complete ETL pipeline"""
        self.logger.info("Starting ETL pipeline...")
        start_time = datetime.now()

        try:
            # Phase 1: Load dimension tables
            self.logger.info("Phase 1: Loading dimension tables...")
            self.load_tracks(track_filter)
            self.load_vehicles()

            # Phase 2: Load race data
            self.logger.info("Phase 2: Loading race data...")
            self.load_races(track_filter)

            # Phase 3: Load fact tables
            self.logger.info("Phase 3: Loading fact tables...")
            self.load_laps(track_filter, dry_run)
            self.load_telemetry(track_filter, dry_run)

            # Phase 4: Load analysis data
            self.logger.info("Phase 4: Loading analysis data...")
            self.load_race_results(track_filter)
            self.load_sector_analysis(track_filter)
            self.load_weather(track_filter)

            # Phase 5: Load championship data
            if not track_filter:  # Only load championship for full migration
                self.logger.info("Phase 5: Loading championship data...")
                self.load_championship()

            # Statistics
            duration = datetime.now() - start_time
            self.logger.info(f"ETL pipeline completed in {duration}")
            self.print_statistics()

        except Exception as e:
            self.logger.error(f"ETL pipeline failed: {str(e)}", exc_info=True)
            raise

    def load_tracks(self, track_filter: Optional[str] = None):
        """Load track dimension data"""
        self.logger.info("Loading tracks...")

        # Clear existing tracks data
        with self.engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE tracks CASCADE;"))
            conn.commit()
            self.logger.info("Cleared existing tracks data")

        track_mapping = self.config['track_mapping']
        track_data = []

        for track_name, track_info in track_mapping.items():
            if track_filter and track_name != track_filter:
                continue

            track_data.append({
                'track_name': track_name,
                'track_full_name': track_info['full_name']
            })

        if track_data:
            df = pd.DataFrame(track_data)
            df.to_sql('tracks', self.engine, if_exists='append', index=False, method='multi')
            self.stats['tracks'] = len(df)
            self.logger.info(f"Loaded {len(df)} tracks")

    def load_vehicles(self):
        """Extract and load unique vehicles from all telemetry/lap files"""
        self.logger.info("Extracting vehicles...")

        # Clear existing vehicles data
        with self.engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE vehicles CASCADE;"))
            conn.commit()
            self.logger.info("Cleared existing vehicles data")

        vehicles = set()

        # Scan all CSV files for vehicle IDs
        all_files = list(self.data_dir.rglob("*.csv"))
        self.logger.info(f"Scanning {len(all_files)} CSV files for vehicle IDs...")

        for csv_file in all_files:
            try:
                # Only process files likely to have vehicle data
                if 'telemetry' in csv_file.name.lower() or 'lap' in csv_file.name.lower():
                    # Check if file has vehicle_id column first
                    if self._has_column(csv_file, 'vehicle_id'):
                        # Read only vehicle_id column for efficiency
                        df = pd.read_csv(csv_file, usecols=['vehicle_id'])
                        new_vehicles = df['vehicle_id'].dropna().unique()
                        vehicles.update(str(v) for v in new_vehicles)
                        self.logger.debug(f"Found {len(new_vehicles)} vehicles in {csv_file.name}")

            except Exception as e:
                self.logger.warning(f"Error reading {csv_file}: {str(e)}")

        # Parse vehicle IDs (format: GR86-XXX-YYY)
        vehicle_data = []
        for vehicle_id in vehicles:
            chassis_number, car_number = self._parse_vehicle_id(vehicle_id)
            vehicle_data.append({
                'vehicle_id': vehicle_id,
                'chassis_number': chassis_number,
                'car_number': car_number
            })

        if vehicle_data:
            df = pd.DataFrame(vehicle_data)
            df.to_sql('vehicles', self.engine, if_exists='append', index=False, method='multi')
            self.stats['vehicles'] = len(df)
            self.logger.info(f"Loaded {len(df)} vehicles")

    def _has_column(self, csv_file: Path, column_name: str) -> bool:
        """Check if a CSV file has a specific column"""
        try:
            df = pd.read_csv(csv_file, nrows=0)
            return column_name in df.columns
        except:
            return False

    def _parse_vehicle_id(self, vehicle_id: str) -> Tuple[str, Optional[int]]:
        """Parse vehicle ID to extract chassis and car number"""
        # Format: GR86-XXX-YYY where XXX is chassis, YYY is car number
        match = re.match(r'GR86-(\d+)-(\d+)', str(vehicle_id))
        if match:
            chassis = match.group(1)
            car_num = int(match.group(2))
            return chassis, car_num if car_num != 0 else None
        return vehicle_id, None

    def load_races(self, track_filter: Optional[str] = None):
        """Load race events from directory structure"""
        self.logger.info("Loading races...")

        # Clear existing races data
        with self.engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE races CASCADE;"))
            conn.commit()
            self.logger.info("Cleared existing races data")

        race_data = []

        for track_dir in self.data_dir.iterdir():
            if not track_dir.is_dir() or track_dir.name.startswith('.'):
                continue

            track_name = track_dir.name
            if track_filter and track_name != track_filter:
                continue

            # Get track_id
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT track_id FROM tracks WHERE track_name = :track"),
                    {"track": track_name}
                )
                row = result.fetchone()
                if not row:
                    self.logger.warning(f"Track {track_name} not found in database")
                    continue
                track_id = row[0]

            # Check for Race subdirectories or flat structure
            race_dirs = [d for d in track_dir.iterdir() if d.is_dir() and d.name.startswith('Race')]

            if race_dirs:
                # Structure: Track/Race X/
                for race_dir in race_dirs:
                    race_num = int(race_dir.name.split()[-1])
                    meta_event, meta_session = self._extract_meta_from_files(race_dir)
                    race_date = self._extract_date_from_meta(meta_event)

                    race_data.append({
                        'track_id': track_id,
                        'race_number': race_num,
                        'meta_event': meta_event,
                        'meta_session': meta_session,
                        'race_date': race_date
                    })
            else:
                # Flat structure: all files in track directory
                # Assume 2 races per track
                for race_num in [1, 2]:
                    meta_event, meta_session = self._extract_meta_from_files(track_dir, race_num)
                    race_date = self._extract_date_from_meta(meta_event)

                    race_data.append({
                        'track_id': track_id,
                        'race_number': race_num,
                        'meta_event': meta_event,
                        'meta_session': meta_session,
                        'race_date': race_date
                    })

        if race_data:
            df = pd.DataFrame(race_data)
            df.to_sql('races', self.engine, if_exists='append', index=False, method='multi')
            self.stats['races'] = len(df)
            self.logger.info(f"Loaded {len(df)} races")

        # Create default sessions for each race
        self._create_sessions()

    def _extract_meta_from_files(self, directory: Path, race_num: Optional[int] = None) -> Tuple[str, str]:
        """Extract meta_event and meta_session from CSV files"""
        # Try to read a sample file to get metadata
        for csv_file in directory.glob("*.csv"):
            if 'telemetry' in csv_file.name.lower() or 'lap' in csv_file.name.lower():
                try:
                    df = pd.read_csv(csv_file, nrows=1)
                    if 'meta_event' in df.columns and 'meta_session' in df.columns:
                        return df['meta_event'].iloc[0], df['meta_session'].iloc[0]
                except:
                    continue

        # Fallback: construct from race number
        if race_num:
            return f"RACE_{race_num}", f"R{race_num}"
        return "UNKNOWN", "R1"

    def _extract_date_from_meta(self, meta_event: str) -> Optional[datetime]:
        """Extract date from meta_event string"""
        # Format: I_R02_2025-04-27
        match = re.search(r'(\d{4}-\d{2}-\d{2})', meta_event)
        if match:
            return datetime.strptime(match.group(1), '%Y-%m-%d').date()
        return None

    def _create_sessions(self):
        """Create default session entries for each race"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                INSERT INTO sessions (race_id, meta_source)
                SELECT race_id, 'kafka:gr-raw'
                FROM races
                WHERE NOT EXISTS (
                    SELECT 1 FROM sessions WHERE sessions.race_id = races.race_id
                )
            """))
            conn.commit()
            self.stats['sessions'] = result.rowcount
            self.logger.info(f"Created {result.rowcount} sessions")

    def load_laps(self, track_filter: Optional[str] = None, dry_run: bool = False):
        """Load lap timing data (merged from start, end, time files)"""
        self.logger.info("Loading laps...")

        total_laps = 0

        for track_dir in self.data_dir.iterdir():
            if not track_dir.is_dir() or track_dir.name.startswith('.'):
                continue

            track_name = track_dir.name
            if track_filter and track_name != track_filter:
                continue

            # Process race directories
            race_dirs = list(track_dir.glob("Race*"))
            if not race_dirs:
                race_dirs = [track_dir]  # Flat structure

            for race_dir in race_dirs:
                lap_files = self._find_lap_files(race_dir)

                if lap_files['start'] and lap_files['end'] and lap_files['time']:
                    laps_df = self._merge_lap_data(
                        lap_files['start'],
                        lap_files['end'],
                        lap_files['time'],
                        track_name,
                        race_dir
                    )

                    if laps_df is not None and not laps_df.empty:
                        if not dry_run:
                            laps_df.to_sql('laps', self.engine, if_exists='append', index=False, method='multi')
                        total_laps += len(laps_df)
                        self.logger.info(f"Loaded {len(laps_df)} laps from {race_dir.name}")

        self.stats['laps'] = total_laps
        self.logger.info(f"Total laps loaded: {total_laps}")

    def _find_lap_files(self, directory: Path) -> Dict[str, Optional[Path]]:
        """Find lap start, end, and time CSV files"""
        files = {'start': None, 'end': None, 'time': None}

        for csv_file in directory.glob("*.csv"):
            name_lower = csv_file.name.lower()
            if 'lap_start' in name_lower or 'lap start' in name_lower:
                files['start'] = csv_file
            elif 'lap_end' in name_lower or 'lap end' in name_lower:
                files['end'] = csv_file
            elif 'lap_time' in name_lower or 'lap time' in name_lower:
                files['time'] = csv_file

        return files

    def _merge_lap_data(self, start_file: Path, end_file: Path, time_file: Path,
                       track_name: str, race_dir: Path) -> Optional[pd.DataFrame]:
        """Merge lap start, end, and time data"""
        try:
            # Read files
            df_start = pd.read_csv(start_file)
            df_end = pd.read_csv(end_file)
            df_time = pd.read_csv(time_file)

            # Get session_id
            session_id = self._get_session_id(track_name, race_dir.name)
            if session_id is None:
                return None

            # Merge dataframes on (vehicle_id, lap, outing)
            merge_cols = ['vehicle_id', 'lap', 'outing']

            df = df_start[merge_cols + ['timestamp', 'meta_time']].rename(
                columns={'timestamp': 'lap_start_timestamp_ecu', 'meta_time': 'lap_start_meta_time'}
            )

            df = df.merge(
                df_end[merge_cols + ['timestamp', 'meta_time']].rename(
                    columns={'timestamp': 'lap_end_timestamp_ecu', 'meta_time': 'lap_end_meta_time'}
                ),
                on=merge_cols,
                how='outer'
            )

            # Add lap duration
            if 'value' in df_time.columns:
                df = df.merge(
                    df_time[merge_cols + ['value']].rename(columns={'value': 'lap_duration'}),
                    on=merge_cols,
                    how='left'
                )

            # Add session_id and other fields
            df['session_id'] = session_id
            df['lap_number'] = df['lap']

            # Convert timestamps
            for col in ['lap_start_timestamp_ecu', 'lap_end_timestamp_ecu',
                       'lap_start_meta_time', 'lap_end_meta_time']:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce')

            # Flag invalid laps
            invalid_lap_nums = self.config['data_quality']['invalid_lap_numbers']
            df['is_valid_lap'] = ~df['lap_number'].isin(invalid_lap_nums)

            # Select final columns
            final_cols = [
                'session_id', 'vehicle_id', 'outing', 'lap_number',
                'lap_start_timestamp_ecu', 'lap_end_timestamp_ecu',
                'lap_duration', 'lap_start_meta_time', 'lap_end_meta_time',
                'is_valid_lap'
            ]

            return df[[col for col in final_cols if col in df.columns]]

        except Exception as e:
            self.logger.error(f"Error merging lap data from {race_dir}: {str(e)}")
            return None

    def _get_session_id(self, track_name: str, race_dir_name: str) -> Optional[int]:
        """Get session_id for a given track and race"""
        # Extract race number from directory name
        race_num_match = re.search(r'Race\s*(\d+)', race_dir_name)
        race_num = int(race_num_match.group(1)) if race_num_match else 1

        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT s.session_id
                FROM sessions s
                JOIN races r ON s.race_id = r.race_id
                JOIN tracks t ON r.track_id = t.track_id
                WHERE t.track_name = :track AND r.race_number = :race_num
                LIMIT 1
            """), {"track": track_name, "race_num": race_num})

            row = result.fetchone()
            return row[0] if row else None

    def load_telemetry(self, track_filter: Optional[str] = None, dry_run: bool = False):
        """Load and pivot telemetry data from EAV to columnar format"""
        self.logger.info("Loading telemetry (this may take a while)...")

        batch_size = self.config['etl']['batch_size']['telemetry']
        total_rows = 0

        for track_dir in self.data_dir.iterdir():
            if not track_dir.is_dir() or track_dir.name.startswith('.'):
                continue

            track_name = track_dir.name
            if track_filter and track_name != track_filter:
                continue

            # Find telemetry files
            telemetry_files = list(track_dir.rglob("*telemetry*.csv"))

            for telemetry_file in telemetry_files:
                self.logger.info(f"Processing {telemetry_file.name}...")

                try:
                    # Read in chunks
                    chunk_iter = pd.read_csv(telemetry_file, chunksize=batch_size)

                    for chunk in tqdm(chunk_iter, desc=f"Processing {telemetry_file.name}"):
                        # Pivot from EAV to columnar
                        pivoted = self._pivot_telemetry(chunk, track_name, telemetry_file.parent.name)

                        if pivoted is not None and not pivoted.empty:
                            if not dry_run:
                                pivoted.to_sql('telemetry_readings', self.engine,
                                             if_exists='append', index=False, method='multi')
                            total_rows += len(pivoted)

                except Exception as e:
                    self.logger.error(f"Error processing {telemetry_file}: {str(e)}")

        self.stats['telemetry'] = total_rows
        self.logger.info(f"Total telemetry rows loaded: {total_rows}")

    def _pivot_telemetry(self, df: pd.DataFrame, track_name: str, race_dir_name: str) -> Optional[pd.DataFrame]:
        """Pivot telemetry from EAV (telemetry_name, telemetry_value) to columnar format"""
        if 'telemetry_name' not in df.columns or 'telemetry_value' not in df.columns:
            return None

        try:
            # Get session_id
            session_id = self._get_session_id(track_name, race_dir_name)
            if session_id is None:
                return None

            # Pivot the data (exclude 'lap' as it's not in the schema)
            pivoted = df.pivot_table(
                index=['vehicle_id', 'timestamp', 'meta_time', 'outing'],
                columns='telemetry_name',
                values='telemetry_value',
                aggfunc='first'
            ).reset_index()

            # Rename columns to match database schema
            column_mapping = {
                'Speed': 'speed',
                'Gear': 'gear',
                'Steering_Angle': 'steering_angle',
                'VBOX_Long_Minutes': 'vbox_long_minutes',
                'VBOX_Lat_Min': 'vbox_lat_min',
                'Laptrigger_lapdist_dls': 'laptrigger_lapdist_dls'
            }

            pivoted.columns = [column_mapping.get(col, col.lower()) for col in pivoted.columns]

            # Add session_id
            pivoted['session_id'] = session_id

            # Rename timestamp columns
            pivoted.rename(columns={
                'timestamp': 'timestamp_ecu',
                'meta_time': 'meta_time'
            }, inplace=True)

            # Convert timestamps
            pivoted['timestamp_ecu'] = pd.to_datetime(pivoted['timestamp_ecu'], errors='coerce')
            pivoted['meta_time'] = pd.to_datetime(pivoted['meta_time'], errors='coerce')

            # TODO: Match to lap_id (requires querying laps table)
            # For now, set to NULL
            pivoted['lap_id'] = None

            return pivoted

        except Exception as e:
            self.logger.error(f"Error pivoting telemetry: {str(e)}")
            return None

    def load_race_results(self, track_filter: Optional[str] = None):
        """Load race results from CSV files"""
        self.logger.info("Loading race results...")
        # TODO: Implement race results loading
        self.logger.warning("Race results loading not yet implemented")

    def load_sector_analysis(self, track_filter: Optional[str] = None):
        """Load sector analysis data"""
        self.logger.info("Loading sector analysis...")
        # TODO: Implement sector analysis loading
        self.logger.warning("Sector analysis loading not yet implemented")

    def load_weather(self, track_filter: Optional[str] = None):
        """Load weather data"""
        self.logger.info("Loading weather data...")
        # TODO: Implement weather loading
        self.logger.warning("Weather loading not yet implemented")

    def load_championship(self):
        """Load championship standings"""
        self.logger.info("Loading championship data...")
        # TODO: Implement championship loading
        self.logger.warning("Championship loading not yet implemented")

    def print_statistics(self):
        """Print ETL statistics"""
        self.logger.info("\n" + "="*50)
        self.logger.info("ETL Statistics:")
        self.logger.info("="*50)
        for key, value in self.stats.items():
            self.logger.info(f"{key.capitalize()}: {value:,}")
        self.logger.info("="*50)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Toyota GR Cup Racing Data ETL')
    parser.add_argument('--config', default='db_config.yaml',
                       help='Path to configuration file')
    parser.add_argument('--track', help='Filter by specific track name')
    parser.add_argument('--dry-run', action='store_true',
                       help='Run without inserting data')
    args = parser.parse_args()

    # Run ETL
    etl = RacingDataETL(args.config)
    etl.run(track_filter=args.track, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
