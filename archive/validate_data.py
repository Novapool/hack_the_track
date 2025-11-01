#!/usr/bin/env python3
"""
Data Validation Script for Toyota GR Cup Racing Database

Validates data quality and integrity after ETL migration

Usage:
    python validate_data.py --config db_config.yaml [--detailed]
"""

import argparse
import yaml
from datetime import datetime
from sqlalchemy import create_engine, text
from tabulate import tabulate
import pandas as pd


class DataValidator:
    """Validates racing database data quality"""

    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.engine = self._create_db_engine()
        self.issues = []

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

    def run_all_checks(self, detailed: bool = False):
        """Run all validation checks"""
        print("="*70)
        print("Data Validation Report")
        print("="*70)
        print(f"Timestamp: {datetime.now()}")
        print()

        # 1. Table row counts
        print("\n1. Table Row Counts")
        print("-"*70)
        self.check_row_counts()

        # 2. Referential integrity
        print("\n2. Referential Integrity")
        print("-"*70)
        self.check_foreign_keys()

        # 3. Data quality
        print("\n3. Data Quality Checks")
        print("-"*70)
        self.check_data_quality()

        # 4. Invalid laps
        print("\n4. Invalid Lap Detection")
        print("-"*70)
        self.check_invalid_laps()

        # 5. Timestamp consistency
        print("\n5. Timestamp Validation")
        print("-"*70)
        self.check_timestamps()

        # 6. Telemetry outliers
        print("\n6. Telemetry Outlier Detection")
        print("-"*70)
        self.check_telemetry_outliers()

        # 7. Missing data
        print("\n7. Missing Data Analysis")
        print("-"*70)
        self.check_missing_data()

        if detailed:
            # 8. Detailed statistics
            print("\n8. Detailed Statistics")
            print("-"*70)
            self.print_detailed_stats()

        # Summary
        self.print_summary()

    def check_row_counts(self):
        """Check row counts for all tables"""
        tables = [
            'tracks', 'races', 'vehicles', 'drivers', 'sessions',
            'laps', 'telemetry_readings', 'race_results',
            'sector_analysis', 'weather_data', 'championship_standings'
        ]

        counts = []
        with self.engine.connect() as conn:
            for table in tables:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.fetchone()[0]
                counts.append([table, f"{count:,}"])

        print(tabulate(counts, headers=['Table', 'Row Count'], tablefmt='grid'))

    def check_foreign_keys(self):
        """Check for foreign key violations"""
        checks = [
            {
                'name': 'Races → Tracks',
                'query': """
                    SELECT COUNT(*) FROM races r
                    LEFT JOIN tracks t ON r.track_id = t.track_id
                    WHERE t.track_id IS NULL
                """
            },
            {
                'name': 'Sessions → Races',
                'query': """
                    SELECT COUNT(*) FROM sessions s
                    LEFT JOIN races r ON s.race_id = r.race_id
                    WHERE r.race_id IS NULL
                """
            },
            {
                'name': 'Laps → Sessions',
                'query': """
                    SELECT COUNT(*) FROM laps l
                    LEFT JOIN sessions s ON l.session_id = s.session_id
                    WHERE s.session_id IS NULL
                """
            },
            {
                'name': 'Laps → Vehicles',
                'query': """
                    SELECT COUNT(*) FROM laps l
                    LEFT JOIN vehicles v ON l.vehicle_id = v.vehicle_id
                    WHERE v.vehicle_id IS NULL
                """
            },
            {
                'name': 'Telemetry → Vehicles',
                'query': """
                    SELECT COUNT(*) FROM telemetry_readings tr
                    LEFT JOIN vehicles v ON tr.vehicle_id = v.vehicle_id
                    WHERE v.vehicle_id IS NULL
                    LIMIT 1000
                """
            }
        ]

        results = []
        with self.engine.connect() as conn:
            for check in checks:
                result = conn.execute(text(check['query']))
                violations = result.fetchone()[0]
                status = "✓ PASS" if violations == 0 else f"✗ FAIL ({violations} violations)"
                results.append([check['name'], status])

                if violations > 0:
                    self.issues.append(f"{check['name']}: {violations} violations")

        print(tabulate(results, headers=['Check', 'Status'], tablefmt='grid'))

    def check_data_quality(self):
        """Check for data quality issues"""
        checks = []

        with self.engine.connect() as conn:
            # Duplicate vehicles
            result = conn.execute(text("""
                SELECT COUNT(*) FROM (
                    SELECT vehicle_id, COUNT(*) as cnt
                    FROM vehicles
                    GROUP BY vehicle_id
                    HAVING COUNT(*) > 1
                ) duplicates
            """))
            duplicates = result.fetchone()[0]
            checks.append(['Duplicate Vehicles', "✓ PASS" if duplicates == 0 else f"✗ FAIL ({duplicates})"])

            # Negative lap durations
            result = conn.execute(text("""
                SELECT COUNT(*) FROM laps
                WHERE lap_duration < 0
            """))
            negative_laps = result.fetchone()[0]
            checks.append(['Negative Lap Durations', "✓ PASS" if negative_laps == 0 else f"✗ FAIL ({negative_laps})"])

            # NULL vehicle IDs in laps
            result = conn.execute(text("""
                SELECT COUNT(*) FROM laps
                WHERE vehicle_id IS NULL
            """))
            null_vehicles = result.fetchone()[0]
            checks.append(['NULL Vehicle IDs', "✓ PASS" if null_vehicles == 0 else f"✗ FAIL ({null_vehicles})"])

        print(tabulate(checks, headers=['Check', 'Status'], tablefmt='grid'))

    def check_invalid_laps(self):
        """Check for invalid laps (lap number 32768)"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT
                    COUNT(*) as total_laps,
                    SUM(CASE WHEN is_valid_lap = FALSE THEN 1 ELSE 0 END) as invalid_laps,
                    ROUND(100.0 * SUM(CASE WHEN is_valid_lap = FALSE THEN 1 ELSE 0 END) / COUNT(*), 2) as invalid_pct
                FROM laps
            """))

            row = result.fetchone()
            data = [
                ['Total Laps', f"{row[0]:,}"],
                ['Invalid Laps', f"{row[1]:,}"],
                ['Invalid %', f"{row[2]}%"]
            ]

            print(tabulate(data, headers=['Metric', 'Value'], tablefmt='grid'))

            if row[1] > 0:
                self.issues.append(f"{row[1]:,} invalid laps detected (lap_number = 32768)")

    def check_timestamps(self):
        """Check timestamp consistency"""
        with self.engine.connect() as conn:
            # Check for future timestamps
            result = conn.execute(text("""
                SELECT COUNT(*) FROM laps
                WHERE lap_start_meta_time > CURRENT_TIMESTAMP
                   OR lap_end_meta_time > CURRENT_TIMESTAMP
            """))
            future_timestamps = result.fetchone()[0]

            # Check for lap end before lap start
            result = conn.execute(text("""
                SELECT COUNT(*) FROM laps
                WHERE lap_end_time < lap_start_time
                  AND lap_end_time IS NOT NULL
                  AND lap_start_time IS NOT NULL
            """))
            inverted_times = result.fetchone()[0]

            checks = [
                ['Future Timestamps', "✓ PASS" if future_timestamps == 0 else f"✗ FAIL ({future_timestamps})"],
                ['Lap End < Lap Start', "✓ PASS" if inverted_times == 0 else f"✗ FAIL ({inverted_times})"]
            ]

            print(tabulate(checks, headers=['Check', 'Status'], tablefmt='grid'))

    def check_telemetry_outliers(self):
        """Check for telemetry outliers"""
        thresholds = self.config['data_quality']['outliers']

        with self.engine.connect() as conn:
            # Speed outliers
            result = conn.execute(text(f"""
                SELECT COUNT(*) FROM telemetry_readings
                WHERE speed > {thresholds['speed_max']}
                   OR speed < {thresholds['speed_min']}
            """))
            speed_outliers = result.fetchone()[0]

            # RPM outliers
            result = conn.execute(text(f"""
                SELECT COUNT(*) FROM telemetry_readings
                WHERE nmot > {thresholds['rpm_max']}
                   OR nmot < {thresholds['rpm_min']}
            """))
            rpm_outliers = result.fetchone()[0]

            checks = [
                ['Speed Outliers', f"{speed_outliers:,}"],
                ['RPM Outliers', f"{rpm_outliers:,}"]
            ]

            print(tabulate(checks, headers=['Type', 'Count'], tablefmt='grid'))

            if speed_outliers > 0 or rpm_outliers > 0:
                self.issues.append(f"Telemetry outliers detected: {speed_outliers} speed, {rpm_outliers} RPM")

    def check_missing_data(self):
        """Analyze missing data patterns"""
        with self.engine.connect() as conn:
            # Laps without telemetry
            result = conn.execute(text("""
                SELECT COUNT(*) FROM laps l
                LEFT JOIN telemetry_readings tr ON l.lap_id = tr.lap_id
                WHERE tr.telemetry_id IS NULL
                  AND l.lap_id IS NOT NULL
            """))
            laps_no_telemetry = result.fetchone()[0]

            # Vehicles without laps
            result = conn.execute(text("""
                SELECT COUNT(*) FROM vehicles v
                LEFT JOIN laps l ON v.vehicle_id = l.vehicle_id
                WHERE l.lap_id IS NULL
            """))
            vehicles_no_laps = result.fetchone()[0]

            data = [
                ['Laps without Telemetry', f"{laps_no_telemetry:,}"],
                ['Vehicles without Laps', f"{vehicles_no_laps:,}"]
            ]

            print(tabulate(data, headers=['Type', 'Count'], tablefmt='grid'))

    def print_detailed_stats(self):
        """Print detailed statistics"""
        with self.engine.connect() as conn:
            # Lap statistics by track
            print("\nLap Statistics by Track:")
            query = """
                SELECT
                    t.track_name,
                    COUNT(l.lap_id) as total_laps,
                    ROUND(AVG(l.lap_duration), 2) as avg_lap_time,
                    ROUND(MIN(l.lap_duration), 2) as fastest_lap,
                    ROUND(MAX(l.lap_duration), 2) as slowest_lap
                FROM tracks t
                JOIN races r ON t.track_id = r.track_id
                JOIN sessions s ON r.race_id = s.race_id
                JOIN laps l ON s.session_id = l.session_id
                WHERE l.is_valid_lap = TRUE
                  AND l.lap_duration IS NOT NULL
                GROUP BY t.track_name
                ORDER BY t.track_name
            """
            df = pd.read_sql(query, conn)
            print(tabulate(df, headers='keys', tablefmt='grid', showindex=False))

            # Telemetry coverage
            print("\nTelemetry Coverage:")
            query = """
                SELECT
                    t.track_name,
                    COUNT(DISTINCT tr.vehicle_id) as vehicles_with_telemetry,
                    COUNT(tr.telemetry_id) as telemetry_points
                FROM tracks t
                JOIN races r ON t.track_id = r.track_id
                JOIN sessions s ON r.race_id = s.race_id
                LEFT JOIN telemetry_readings tr ON s.session_id = tr.session_id
                GROUP BY t.track_name
                ORDER BY t.track_name
            """
            df = pd.read_sql(query, conn)
            print(tabulate(df, headers='keys', tablefmt='grid', showindex=False))

    def print_summary(self):
        """Print validation summary"""
        print("\n" + "="*70)
        print("VALIDATION SUMMARY")
        print("="*70)

        if not self.issues:
            print("✓ All validation checks passed!")
        else:
            print(f"✗ Found {len(self.issues)} issue(s):")
            for i, issue in enumerate(self.issues, 1):
                print(f"  {i}. {issue}")

        print("="*70)


def main():
    parser = argparse.ArgumentParser(description='Validate racing database')
    parser.add_argument('--config', default='db_config.yaml',
                       help='Path to configuration file')
    parser.add_argument('--detailed', action='store_true',
                       help='Show detailed statistics')
    args = parser.parse_args()

    validator = DataValidator(args.config)
    validator.run_all_checks(detailed=args.detailed)


if __name__ == '__main__':
    main()
