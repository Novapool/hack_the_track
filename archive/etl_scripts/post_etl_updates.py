#!/usr/bin/env python3
"""
Post-ETL Updates for Toyota GR Cup Racing Database

Fixes and populates fields that were left NULL during initial ETL:
- Links telemetry_readings to laps via lap_id
- Populates lap_start_time and lap_end_time
- Populates session_start_time
- Extracts vehicle_class from race results

Usage:
    python post_etl_updates.py --config db_config.yaml [--skip-telemetry]
"""

import argparse
import yaml
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, text
from tqdm import tqdm


class PostETLUpdates:
    """Performs post-ETL data fixes and enhancements"""

    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.engine = self._create_db_engine()
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

    def run(self, skip_telemetry: bool = False):
        """Execute all post-ETL updates"""
        start_time = datetime.now()
        self.logger.info("="*70)
        self.logger.info("Starting Post-ETL Updates...")
        self.logger.info("="*70)

        try:
            # Step 1: Update lap timestamps
            self.logger.info("\nStep 1: Populating lap start/end times...")
            self.update_lap_timestamps()

            # Step 2: Update session start times
            self.logger.info("\nStep 2: Populating session start times...")
            self.update_session_timestamps()

            # Step 3: Extract vehicle class
            self.logger.info("\nStep 3: Extracting vehicle classes...")
            self.update_vehicle_class()

            # Step 4: Link telemetry to laps (HEAVY)
            if not skip_telemetry:
                self.logger.info("\nStep 4: Linking telemetry to laps (this will take a while)...")
                self.link_telemetry_to_laps()
            else:
                self.logger.info("\nStep 4: Skipping telemetry linking (--skip-telemetry flag)")

            # Summary
            elapsed = datetime.now() - start_time
            self.logger.info(f"\nPost-ETL updates completed in {elapsed}")
            self.print_summary()

        except Exception as e:
            self.logger.error(f"Post-ETL updates failed: {str(e)}", exc_info=True)
            raise

    def update_lap_timestamps(self):
        """Copy lap_start_meta_time and lap_end_meta_time to lap_start_time and lap_end_time"""
        self.logger.info("Updating lap timestamps...")

        with self.engine.connect() as conn:
            # Update lap_start_time
            result = conn.execute(text("""
                UPDATE laps
                SET lap_start_time = lap_start_meta_time
                WHERE lap_start_time IS NULL
                  AND lap_start_meta_time IS NOT NULL
            """))
            start_updated = result.rowcount
            conn.commit()

            self.logger.info(f"Updated {start_updated:,} lap_start_time values")

            # Update lap_end_time
            result = conn.execute(text("""
                UPDATE laps
                SET lap_end_time = lap_end_meta_time
                WHERE lap_end_time IS NULL
                  AND lap_end_meta_time IS NOT NULL
            """))
            end_updated = result.rowcount
            conn.commit()

            self.logger.info(f"Updated {end_updated:,} lap_end_time values")

    def update_session_timestamps(self):
        """Calculate and populate session_start_time from lap data"""
        self.logger.info("Updating session start times...")

        with self.engine.connect() as conn:
            result = conn.execute(text("""
                UPDATE sessions s
                SET session_start_time = subq.min_start_time
                FROM (
                    SELECT session_id, MIN(lap_start_meta_time) as min_start_time
                    FROM laps
                    WHERE lap_start_meta_time IS NOT NULL
                    GROUP BY session_id
                ) subq
                WHERE s.session_id = subq.session_id
                  AND s.session_start_time IS NULL
            """))
            updated = result.rowcount
            conn.commit()

            self.logger.info(f"Updated {updated:,} session_start_time values")

    def update_vehicle_class(self):
        """Extract vehicle_class from race_results table"""
        self.logger.info("Extracting vehicle classes from race results...")

        with self.engine.connect() as conn:
            # First, check if race_results has data
            result = conn.execute(text("SELECT COUNT(*) FROM race_results"))
            count = result.fetchone()[0]

            if count == 0:
                self.logger.warning("No race results found - run supplemental_etl.py first")
                return

            # Update vehicle_class based on race results
            result = conn.execute(text("""
                UPDATE vehicles v
                SET vehicle_class = subq.class
                FROM (
                    SELECT car_number, class
                    FROM race_results
                    WHERE car_number IS NOT NULL
                      AND class IS NOT NULL
                    GROUP BY car_number, class
                ) subq
                WHERE v.car_number = subq.car_number
                  AND v.vehicle_class IS NULL
            """))
            updated = result.rowcount
            conn.commit()

            self.logger.info(f"Updated {updated:,} vehicle_class values")

    def link_telemetry_to_laps(self):
        """Link telemetry readings to laps (HEAVY OPERATION - processes 23M+ rows)"""
        self.logger.info("Linking telemetry to laps...")
        self.logger.info("This operation will process 23M+ rows and may take 30-60 minutes")

        # Get total count
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM telemetry_readings WHERE lap_id IS NULL"))
            total_rows = result.fetchone()[0]

            if total_rows == 0:
                self.logger.info("All telemetry already linked to laps")
                return

            self.logger.info(f"Found {total_rows:,} telemetry rows to link")

        # Create temporary index to speed up the join
        self.logger.info("Creating temporary indexes for faster processing...")
        with self.engine.connect() as conn:
            try:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS tmp_idx_laps_lookup
                    ON laps(session_id, vehicle_id, outing, lap_start_meta_time, lap_end_meta_time)
                """))
                conn.commit()
                self.logger.info("Temporary index created")
            except Exception as e:
                self.logger.warning(f"Could not create temporary index: {e}")

        # Strategy: Update by session to avoid massive joins
        # Get all session_ids that need updating
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT session_id
                FROM telemetry_readings
                WHERE lap_id IS NULL
                ORDER BY session_id
            """))
            session_ids = [row[0] for row in result.fetchall()]

        self.logger.info(f"Processing {len(session_ids)} sessions...")

        updated_total = 0
        for session_id in tqdm(session_ids, desc="Processing sessions"):
            with self.engine.connect() as conn:
                try:
                    # Update telemetry for this session
                    # Use a correlated subquery to find matching lap
                    result = conn.execute(text("""
                        UPDATE telemetry_readings tr
                        SET lap_id = (
                            SELECT l.lap_id
                            FROM laps l
                            WHERE l.session_id = tr.session_id
                              AND l.vehicle_id = tr.vehicle_id
                              AND l.outing = tr.outing
                              AND tr.meta_time >= l.lap_start_meta_time
                              AND tr.meta_time <= l.lap_end_meta_time
                            ORDER BY l.lap_start_meta_time
                            LIMIT 1
                        )
                        WHERE tr.session_id = :session_id
                          AND tr.lap_id IS NULL
                    """), {"session_id": session_id})

                    updated = result.rowcount
                    updated_total += updated
                    conn.commit()

                except Exception as e:
                    self.logger.error(f"Error processing session {session_id}: {e}")
                    conn.rollback()
                    continue

        self.logger.info(f"Linked {updated_total:,} telemetry readings to laps")

        # Clean up temporary index
        self.logger.info("Cleaning up temporary indexes...")
        with self.engine.connect() as conn:
            try:
                conn.execute(text("DROP INDEX IF EXISTS tmp_idx_laps_lookup"))
                conn.commit()
                self.logger.info("Temporary index dropped")
            except Exception as e:
                self.logger.warning(f"Could not drop temporary index: {e}")

        # Report on telemetry that couldn't be linked
        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM telemetry_readings WHERE lap_id IS NULL"))
            unlinked = result.fetchone()[0]

            if unlinked > 0:
                self.logger.warning(f"{unlinked:,} telemetry readings could not be linked to laps")
                self.logger.warning("This may be due to telemetry outside of lap boundaries")

    def print_summary(self):
        """Print summary of updates"""
        self.logger.info("\n" + "="*70)
        self.logger.info("Post-ETL Update Summary")
        self.logger.info("="*70)

        with self.engine.connect() as conn:
            # Laps with timestamps
            result = conn.execute(text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(lap_start_time) as has_start,
                    COUNT(lap_end_time) as has_end
                FROM laps
            """))
            row = result.fetchone()
            self.logger.info(f"Laps: {row[0]:,} total")
            self.logger.info(f"  - With lap_start_time: {row[1]:,} ({100*row[1]/row[0]:.1f}%)")
            self.logger.info(f"  - With lap_end_time: {row[2]:,} ({100*row[2]/row[0]:.1f}%)")

            # Sessions with start time
            result = conn.execute(text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(session_start_time) as has_start
                FROM sessions
            """))
            row = result.fetchone()
            self.logger.info(f"\nSessions: {row[0]:,} total")
            self.logger.info(f"  - With session_start_time: {row[1]:,} ({100*row[1]/row[0]:.1f}%)")

            # Vehicles with class
            result = conn.execute(text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(vehicle_class) as has_class
                FROM vehicles
            """))
            row = result.fetchone()
            self.logger.info(f"\nVehicles: {row[0]:,} total")
            self.logger.info(f"  - With vehicle_class: {row[1]:,} ({100*row[1]/row[0] if row[0] > 0 else 0:.1f}%)")

            # Telemetry linked to laps
            result = conn.execute(text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(lap_id) as linked
                FROM telemetry_readings
            """))
            row = result.fetchone()
            self.logger.info(f"\nTelemetry: {row[0]:,} total")
            self.logger.info(f"  - Linked to laps: {row[1]:,} ({100*row[1]/row[0]:.1f}%)")

        self.logger.info("="*70)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Post-ETL Updates for GR Cup Racing Database')
    parser.add_argument('--config', default='db_config.yaml',
                       help='Path to configuration file')
    parser.add_argument('--skip-telemetry', action='store_true',
                       help='Skip the heavy telemetry linking operation')
    args = parser.parse_args()

    # Run updates
    updater = PostETLUpdates(args.config)
    updater.run(skip_telemetry=args.skip_telemetry)


if __name__ == '__main__':
    main()
