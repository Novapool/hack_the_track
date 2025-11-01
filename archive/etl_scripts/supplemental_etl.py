#!/usr/bin/env python3
"""
Supplemental ETL Script for Toyota GR Cup Racing Database

Loads data that was not implemented in the initial ETL:
- Drivers
- Race Results
- Sector Analysis
- Weather Data
- Championship Standings

Usage:
    python supplemental_etl.py --config db_config.yaml [--dry-run]
"""

import argparse
import yaml
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
import pandas as pd
from sqlalchemy import create_engine, text
from tqdm import tqdm
import re


class SupplementalETL:
    """Loads supplemental racing data not covered by initial ETL"""

    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.engine = self._create_db_engine()
        self.data_dir = Path(self.config['etl']['data_directory'])
        self.stats = {
            'drivers': 0,
            'race_results': 0,
            'sector_analysis': 0,
            'weather': 0,
            'championship': 0
        }
        self._setup_logging()

    def _load_config(self, config_path: str) -> dict:
        """Load YAML configuration"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    def _create_db_engine(self):
        """Create database connection"""
        db = self.config['database']
        return create_engine(
            f"postgresql://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['database']}"
        )

    def _setup_logging(self):
        """Configure logging"""
        log_config = self.config['etl']['logging']
        log_level = getattr(logging, log_config['level'])

        # Create logs directory if it doesn't exist
        log_file = Path(log_config['log_file'])
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Configure logger
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler() if log_config['console_output'] else logging.NullHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def run(self, dry_run: bool = False):
        """Execute supplemental ETL pipeline"""
        start_time = datetime.now()
        self.logger.info("="*70)
        self.logger.info("Starting Supplemental ETL Pipeline...")
        self.logger.info("="*70)

        try:
            # Phase 1: Load drivers
            self.logger.info("\nPhase 1: Loading drivers...")
            self.load_drivers(dry_run=dry_run)

            # Phase 2: Load race results
            self.logger.info("\nPhase 2: Loading race results...")
            self.load_race_results(dry_run=dry_run)

            # Phase 3: Load sector analysis
            self.logger.info("\nPhase 3: Loading sector analysis...")
            self.load_sector_analysis(dry_run=dry_run)

            # Phase 4: Load weather data
            self.logger.info("\nPhase 4: Loading weather data...")
            self.load_weather(dry_run=dry_run)

            # Phase 5: Load championship standings
            self.logger.info("\nPhase 5: Loading championship standings...")
            self.load_championship(dry_run=dry_run)

            # Summary
            elapsed = datetime.now() - start_time
            self.logger.info(f"\nSupplemental ETL completed in {elapsed}")
            self.print_statistics()

        except Exception as e:
            self.logger.error(f"ETL pipeline failed: {str(e)}", exc_info=True)
            raise

    def load_drivers(self, dry_run: bool = False):
        """Extract unique drivers from race results files"""
        self.logger.info("Extracting drivers from race results...")

        # Find all results files
        results_files = list(self.data_dir.rglob("*Results*.CSV"))

        drivers_data = []
        seen_drivers = set()

        for results_file in tqdm(results_files, desc="Processing results files"):
            try:
                df = pd.read_csv(results_file, sep=';', encoding='utf-8-sig')

                # Check if this file has driver information
                if 'DRIVER_FIRSTNAME' not in df.columns or 'DRIVER_SECONDNAME' not in df.columns:
                    continue

                for _, row in df.iterrows():
                    first_name = str(row.get('DRIVER_FIRSTNAME', '')).strip()
                    last_name = str(row.get('DRIVER_SECONDNAME', '')).strip()
                    country = str(row.get('DRIVER_COUNTRY', '')).strip()
                    team = str(row.get('TEAM', '')).strip()
                    car_number = row.get('NUMBER', None)

                    # Skip empty entries
                    if not first_name or not last_name or first_name == 'nan' or last_name == 'nan':
                        continue

                    # Create unique key
                    driver_key = (first_name, last_name, car_number)
                    if driver_key in seen_drivers:
                        continue

                    seen_drivers.add(driver_key)

                    drivers_data.append({
                        'first_name': first_name,
                        'last_name': last_name,
                        'full_name': f"{first_name} {last_name}",
                        'country': country if country and country != 'nan' else None,
                        'team': team if team and team != 'nan' else None,
                        'participant_number': car_number if pd.notna(car_number) else None
                    })

            except Exception as e:
                self.logger.warning(f"Error processing {results_file.name}: {str(e)}")
                continue

        if drivers_data:
            df_drivers = pd.DataFrame(drivers_data).drop_duplicates(subset=['first_name', 'last_name', 'participant_number'])

            if not dry_run:
                # Clear existing data
                with self.engine.connect() as conn:
                    conn.execute(text("TRUNCATE TABLE drivers RESTART IDENTITY CASCADE"))
                    conn.commit()

                # Insert new data
                df_drivers.to_sql('drivers', self.engine, if_exists='append', index=False, method='multi')

            self.stats['drivers'] = len(df_drivers)
            self.logger.info(f"Loaded {len(df_drivers)} drivers")
        else:
            self.logger.warning("No driver data found in results files")

    def load_race_results(self, dry_run: bool = False):
        """Load race results from official results files"""
        self.logger.info("Loading race results...")

        # Find official results files (prefer official over provisional)
        results_files = list(self.data_dir.rglob("*Official*.CSV"))
        if not results_files:
            results_files = list(self.data_dir.rglob("*Results*.CSV"))

        results_data = []

        for results_file in tqdm(results_files, desc="Processing results files"):
            try:
                # Skip analysis and weather files
                if 'Analysis' in results_file.name or 'Weather' in results_file.name or 'Championship' in results_file.name:
                    continue

                df = pd.read_csv(results_file, sep=';', encoding='utf-8-sig')

                # Get race_id from file path
                race_id = self._get_race_id_from_path(results_file)
                if race_id is None:
                    self.logger.warning(f"Could not determine race_id for {results_file}")
                    continue

                for _, row in df.iterrows():
                    # Get driver_id if driver exists
                    driver_id = None
                    first_name = str(row.get('DRIVER_FIRSTNAME', '')).strip()
                    last_name = str(row.get('DRIVER_SECONDNAME', '')).strip()
                    car_number = row.get('NUMBER', None)

                    if first_name and last_name and first_name != 'nan' and last_name != 'nan':
                        driver_id = self._get_driver_id(first_name, last_name, car_number)

                    # Parse time fields (they might be formatted as mm:ss.sss)
                    fastest_lap_time = self._parse_lap_time(row.get('FL_TIME', None))

                    results_data.append({
                        'race_id': race_id,
                        'driver_id': driver_id,
                        'vehicle_id': None,  # Will update later if we can match
                        'position': row.get('POSITION', None),
                        'car_number': car_number,
                        'status': row.get('STATUS', None),
                        'laps_completed': row.get('LAPS', None),
                        'total_time': row.get('TOTAL_TIME', None),
                        'gap_to_first': row.get('GAP_FIRST', None),
                        'gap_to_previous': row.get('GAP_PREVIOUS', None),
                        'fastest_lap_number': row.get('FL_LAPNUM', None),
                        'fastest_lap_time': fastest_lap_time,
                        'fastest_lap_kph': row.get('FL_KPH', None),
                        'class': row.get('CLASS', None),
                        'division': row.get('DIVISION', None),
                        'vehicle_type': row.get('VEHICLE', None)
                    })

            except Exception as e:
                self.logger.warning(f"Error processing {results_file.name}: {str(e)}")
                continue

        if results_data:
            df_results = pd.DataFrame(results_data)

            if not dry_run:
                # Clear existing data
                with self.engine.connect() as conn:
                    conn.execute(text("TRUNCATE TABLE race_results RESTART IDENTITY CASCADE"))
                    conn.commit()

                # Insert new data
                df_results.to_sql('race_results', self.engine, if_exists='append', index=False, method='multi')

            self.stats['race_results'] = len(df_results)
            self.logger.info(f"Loaded {len(df_results)} race results")
        else:
            self.logger.warning("No race results data found")

    def load_sector_analysis(self, dry_run: bool = False):
        """Load sector timing analysis from AnalysisEnduranceWithSections files"""
        self.logger.info("Loading sector analysis...")

        sector_files = list(self.data_dir.rglob("*AnalysisEndurance*.CSV"))

        sector_data = []

        for sector_file in tqdm(sector_files, desc="Processing sector files"):
            try:
                df = pd.read_csv(sector_file, sep=';', encoding='utf-8-sig')

                # Get race_id
                race_id = self._get_race_id_from_path(sector_file)
                if race_id is None:
                    continue

                for _, row in df.iterrows():
                    # Parse lap time
                    lap_time_seconds = self._parse_lap_time(row.get('LAP_TIME', None))

                    sector_data.append({
                        'race_id': race_id,
                        'vehicle_id': None,  # Will need to match from driver number
                        'driver_number': row.get('DRIVER_NUMBER', None),
                        'car_number': row.get('NUMBER', None),
                        'lap_number': row.get('LAP_NUMBER', None),
                        'lap_time': row.get('LAP_TIME', None),
                        'lap_time_seconds': lap_time_seconds,
                        'crossing_finish_in_pit': row.get('CROSSING_FINISH_LINE_IN_PIT', None) == 'True',
                        # Sector times
                        's1_time': row.get('S1', None),
                        's1_seconds': row.get('S1_SECONDS', None),
                        's1_improvement': row.get('S1_IMPROVEMENT', None),
                        's2_time': row.get('S2', None),
                        's2_seconds': row.get('S2_SECONDS', None),
                        's2_improvement': row.get('S2_IMPROVEMENT', None),
                        's3_time': row.get('S3', None),
                        's3_seconds': row.get('S3_SECONDS', None),
                        's3_improvement': row.get('S3_IMPROVEMENT', None),
                        # Intermediate times - parse to decimal
                        'im1a_time': self._parse_lap_time(row.get('IM1a_time', None)),
                        'im1a_elapsed': self._parse_lap_time(row.get('IM1a_elapsed', None)),
                        'im1_time': self._parse_lap_time(row.get('IM1_time', None)),
                        'im1_elapsed': self._parse_lap_time(row.get('IM1_elapsed', None)),
                        'im2a_time': self._parse_lap_time(row.get('IM2a_time', None)),
                        'im2a_elapsed': self._parse_lap_time(row.get('IM2a_elapsed', None)),
                        'im2_time': self._parse_lap_time(row.get('IM2_time', None)),
                        'im2_elapsed': self._parse_lap_time(row.get('IM2_elapsed', None)),
                        'im3a_time': self._parse_lap_time(row.get('IM3a_time', None)),
                        'im3a_elapsed': self._parse_lap_time(row.get('IM3a_elapsed', None)),
                        'fl_time': self._parse_lap_time(row.get('FL_time', None)),
                        'fl_elapsed': self._parse_lap_time(row.get('FL_elapsed', None)),
                        # Additional data
                        'top_speed': row.get('TOP_SPEED', None),
                        'average_kph': row.get('KPH', None),
                        'elapsed_time': row.get('ELAPSED', None),
                        'elapsed_seconds': self._parse_lap_time(row.get('ELAPSED', None)),
                        'flag_at_finish': row.get('FLAG_AT_FL', None)
                    })

            except Exception as e:
                self.logger.warning(f"Error processing {sector_file.name}: {str(e)}")
                continue

        if sector_data:
            df_sectors = pd.DataFrame(sector_data)

            if not dry_run:
                # Clear existing data
                with self.engine.connect() as conn:
                    conn.execute(text("TRUNCATE TABLE sector_analysis RESTART IDENTITY CASCADE"))
                    conn.commit()

                # Insert new data
                df_sectors.to_sql('sector_analysis', self.engine, if_exists='append', index=False, method='multi')

            self.stats['sector_analysis'] = len(df_sectors)
            self.logger.info(f"Loaded {len(df_sectors)} sector analysis records")
        else:
            self.logger.warning("No sector analysis data found")

    def load_weather(self, dry_run: bool = False):
        """Load weather data from Weather CSV files"""
        self.logger.info("Loading weather data...")

        weather_files = list(self.data_dir.rglob("*Weather*.CSV"))

        weather_data = []

        for weather_file in tqdm(weather_files, desc="Processing weather files"):
            try:
                df = pd.read_csv(weather_file, sep=';', encoding='utf-8-sig')

                # Get race_id
                race_id = self._get_race_id_from_path(weather_file)
                if race_id is None:
                    continue

                for _, row in df.iterrows():
                    # Parse timestamp
                    timestamp = None
                    if 'TIME_UTC_SECONDS' in row:
                        try:
                            timestamp = pd.to_datetime(row['TIME_UTC_SECONDS'], unit='s')
                        except:
                            pass

                    if timestamp is None and 'TIME_UTC_STR' in row:
                        try:
                            timestamp = pd.to_datetime(row['TIME_UTC_STR'])
                        except:
                            pass

                    weather_data.append({
                        'race_id': race_id,
                        'timestamp': timestamp,
                        'air_temp': row.get('AIR_TEMP', None),
                        'track_temp': row.get('TRACK_TEMP', None),
                        'humidity': row.get('HUMIDITY', None),
                        'pressure': row.get('PRESSURE', None),
                        'wind_speed': row.get('WIND_SPEED', None),
                        'wind_direction': str(row.get('WIND_DIRECTION', None)) if pd.notna(row.get('WIND_DIRECTION')) else None,
                        'conditions': 'Rainy' if row.get('RAIN', 0) > 0 else 'Dry',
                        'raw_data': None  # Could store full row as JSON if needed
                    })

            except Exception as e:
                self.logger.warning(f"Error processing {weather_file.name}: {str(e)}")
                continue

        if weather_data:
            df_weather = pd.DataFrame(weather_data)

            if not dry_run:
                # Clear existing data
                with self.engine.connect() as conn:
                    conn.execute(text("TRUNCATE TABLE weather_data RESTART IDENTITY CASCADE"))
                    conn.commit()

                # Insert new data
                df_weather.to_sql('weather_data', self.engine, if_exists='append', index=False, method='multi')

            self.stats['weather'] = len(df_weather)
            self.logger.info(f"Loaded {len(df_weather)} weather records")
        else:
            self.logger.warning("No weather data found")

    def load_championship(self, dry_run: bool = False):
        """Load championship standings"""
        self.logger.info("Loading championship standings...")

        # Find championship file
        champ_files = list(self.data_dir.rglob("*Championship*.csv"))

        if not champ_files:
            self.logger.warning("No championship file found")
            return

        try:
            champ_file = champ_files[0]
            df = pd.read_csv(champ_file, sep=';', encoding='utf-8-sig')

            standings_data = []

            for _, row in df.iterrows():
                # Get driver_id
                first_name = str(row.get('NAME', '')).strip()
                last_name = str(row.get('SURNAME', '')).strip()
                car_number = row.get('Number', None)

                driver_id = None
                if first_name and last_name and first_name != 'nan' and last_name != 'nan':
                    driver_id = self._get_driver_id(first_name, last_name, car_number)

                if driver_id is None:
                    self.logger.warning(f"Could not find driver_id for {first_name} {last_name}")
                    continue

                standings_data.append({
                    'driver_id': driver_id,
                    'season_year': 2025,  # Adjust as needed
                    'position': row.get('Pos', None),
                    'total_points': row.get('Points', None),
                    'participant_number': car_number,
                    'race_results': None  # Could parse individual race results from columns if needed
                })

            if standings_data:
                df_standings = pd.DataFrame(standings_data)

                if not dry_run:
                    # Clear existing data
                    with self.engine.connect() as conn:
                        conn.execute(text("TRUNCATE TABLE championship_standings RESTART IDENTITY CASCADE"))
                        conn.commit()

                    # Insert new data
                    df_standings.to_sql('championship_standings', self.engine, if_exists='append', index=False, method='multi')

                self.stats['championship'] = len(df_standings)
                self.logger.info(f"Loaded {len(df_standings)} championship standings")

        except Exception as e:
            self.logger.error(f"Error loading championship data: {str(e)}")

    def _get_race_id_from_path(self, file_path: Path) -> Optional[int]:
        """Extract race_id from file path"""
        # Extract track name and race number from path
        path_parts = file_path.parts

        # Try to find track directory
        track_name = None
        for part in path_parts:
            if part in ['COTA', 'Sebring', 'Sonoma', 'VIR', 'Road America', 'barber', 'indianapolis']:
                track_name = part
                break

        if track_name is None:
            return None

        # Normalize track name
        track_name_normalized = track_name

        # Extract race number from filename or directory
        race_num = 1  # default

        # Check filename first
        if 'Race 2' in file_path.name or 'Race_2' in file_path.name or 'R2' in file_path.name:
            race_num = 2
        elif 'Race 1' in file_path.name or 'Race_1' in file_path.name or 'R1' in file_path.name:
            race_num = 1
        else:
            # Check parent directory
            for part in path_parts:
                if 'Race 2' in part:
                    race_num = 2
                    break
                elif 'Race 1' in part:
                    race_num = 1
                    break

        # Query database for race_id
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT r.race_id
                FROM races r
                JOIN tracks t ON r.track_id = t.track_id
                WHERE t.track_name = :track AND r.race_number = :race_num
                LIMIT 1
            """), {"track": track_name_normalized, "race_num": race_num})

            row = result.fetchone()
            return row[0] if row else None

    def _get_driver_id(self, first_name: str, last_name: str, car_number: Optional[int]) -> Optional[int]:
        """Get driver_id from database"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT driver_id FROM drivers
                WHERE first_name = :first AND last_name = :last
                AND (participant_number = :num OR participant_number IS NULL OR :num IS NULL)
                LIMIT 1
            """), {"first": first_name, "last": last_name, "num": car_number})

            row = result.fetchone()
            return row[0] if row else None

    def _parse_lap_time(self, time_str) -> Optional[float]:
        """Parse lap time string (mm:ss.sss) to seconds"""
        if pd.isna(time_str) or not time_str:
            return None

        try:
            # If already a number, return it
            return float(time_str)
        except (ValueError, TypeError):
            pass

        try:
            # Try parsing mm:ss.sss format
            time_str = str(time_str).strip()
            if ':' in time_str:
                parts = time_str.split(':')
                if len(parts) == 2:
                    minutes = int(parts[0])
                    seconds = float(parts[1])
                    return minutes * 60 + seconds
        except:
            pass

        return None

    def print_statistics(self):
        """Print ETL statistics"""
        self.logger.info("\n" + "="*70)
        self.logger.info("Supplemental ETL Statistics:")
        self.logger.info("="*70)
        self.logger.info(f"Drivers: {self.stats['drivers']:,}")
        self.logger.info(f"Race Results: {self.stats['race_results']:,}")
        self.logger.info(f"Sector Analysis: {self.stats['sector_analysis']:,}")
        self.logger.info(f"Weather Records: {self.stats['weather']:,}")
        self.logger.info(f"Championship Standings: {self.stats['championship']:,}")
        self.logger.info("="*70)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Toyota GR Cup Supplemental ETL')
    parser.add_argument('--config', default='db_config.yaml',
                       help='Path to configuration file')
    parser.add_argument('--dry-run', action='store_true',
                       help='Run without inserting data')
    args = parser.parse_args()

    # Run ETL
    etl = SupplementalETL(args.config)
    etl.run(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
