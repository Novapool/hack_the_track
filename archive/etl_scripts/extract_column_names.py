import csv
from pathlib import Path


def process_csv_file(csv_file, out_f, indent=""):
    """Process a single CSV file and write its columns to the output file."""
    try:
        with open(csv_file, 'r') as csv_f:
            reader = csv.reader(csv_f)
            # Get the first row (header)
            columns = next(reader)

            # Write to output file
            out_f.write(f"{indent}{csv_file.name} = {columns}\n\n")
            print(f"  ✓ Processed {csv_file.name}")
            return True
    except Exception as e:
        error_msg = f"Error processing {csv_file.name}: {str(e)}\n\n"
        out_f.write(f"{indent}{error_msg}")
        print(f"  ✗ {error_msg.strip()}")
        return False


def extract_column_names():
    """
    Extract column names from all CSV files in track_data directory.
    Creates a separate text file for each track containing file names and their columns.
    Handles two structures:
    1. CSV files directly in track directory (e.g., barber, indianapolis)
    2. CSV files in Race subdirectories (e.g., Sebring/Race 1/, Sebring/Race 2/)
    """
    track_data_dir = Path("track_data")
    output_dir = Path("column_data")

    if not track_data_dir.exists():
        print(f"Error: {track_data_dir} directory not found!")
        return

    # Create output directory if it doesn't exist
    output_dir.mkdir(exist_ok=True)

    # Loop through each track directory
    for track_dir in track_data_dir.iterdir():
        # Skip non-directories and hidden files
        if not track_dir.is_dir() or track_dir.name.startswith('.'):
            continue

        track_name = track_dir.name
        output_file = output_dir / f"{track_name}_columns.txt"

        print(f"Processing track: {track_name}")

        # Open output file for this track
        with open(output_file, 'w') as out_f:
            out_f.write(f"Track: {track_name}\n")
            out_f.write("=" * 80 + "\n\n")

            # Check for CSV files directly in track directory
            csv_files = sorted(track_dir.glob("*.csv"))

            # Check for subdirectories (like Race 1, Race 2)
            subdirs = sorted([d for d in track_dir.iterdir() if d.is_dir() and not d.name.startswith('.')])

            if csv_files:
                # Structure 1: CSV files directly in track directory
                for csv_file in csv_files:
                    process_csv_file(csv_file, out_f)

            elif subdirs:
                # Structure 2: CSV files in subdirectories
                for subdir in subdirs:
                    subdir_csv_files = sorted(subdir.glob("*.csv"))

                    if subdir_csv_files:
                        out_f.write(f"{subdir.name}:\n")
                        out_f.write("-" * 40 + "\n")

                        for csv_file in subdir_csv_files:
                            process_csv_file(csv_file, out_f, indent="  ")

                        out_f.write("\n")
            else:
                out_f.write("No CSV files found.\n")
                print(f"  No CSV files found in {track_dir}")

        print(f"Created: {output_file}\n")


if __name__ == "__main__":
    extract_column_names()
    print("Done!")
