"""
PDF to PNG Converter for Track Maps

Converts track circuit PDF maps to PNG images for use in the Streamlit dashboard.
This is a one-time conversion utility that should be run during setup.

Usage:
    python -m hackathon_app.utils.pdf_converter
"""

import os
from pathlib import Path
from pdf2image import convert_from_path
from PIL import Image


def pdf_to_png(pdf_path: str, output_path: str, dpi: int = 300) -> bool:
    """
    Convert a PDF file to PNG image.

    Args:
        pdf_path: Path to input PDF file
        output_path: Path to save output PNG file
        dpi: Resolution in dots per inch (default: 300 for high quality)

    Returns:
        bool: True if conversion successful, False otherwise
    """
    try:
        print(f"Converting {os.path.basename(pdf_path)}...", end=" ")

        # Convert PDF to images (typically single-page track maps)
        images = convert_from_path(pdf_path, dpi=dpi)

        # Save the first page as PNG
        if images:
            images[0].save(output_path, 'PNG')
            file_size = os.path.getsize(output_path) / 1024  # KB
            print(f"✓ ({file_size:.1f} KB)")
            return True
        else:
            print("✗ No pages found in PDF")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def convert_all_track_maps():
    """
    Convert all track map PDFs to PNG images.

    Searches for PDFs in /track_maps/ and saves PNGs to /hackathon_app/assets/track_images/
    """
    # Define paths
    project_root = Path(__file__).parent.parent.parent
    pdf_dir = project_root / "track_maps"
    output_dir = project_root / "hackathon_app" / "assets" / "track_images"

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Track name mapping (PDF filename → clean track name)
    track_name_mapping = {
        "Barber_Circuit_Map.pdf": "barber.png",
        "COTA_Circuit_Map.pdf": "cota.png",
        "Indy_Circuit_Map.pdf": "indianapolis.png",
        "Road_America_Map.pdf": "road_america.png",
        "Sebring_Track_Sector_Map.pdf": "sebring.png",
        "Sonoma_Map.pdf": "sonoma.png",
        "VIR_map.pdf": "vir.png"
    }

    print("=" * 60)
    print("Converting Track Maps: PDF → PNG")
    print("=" * 60)
    print(f"Source:      {pdf_dir}")
    print(f"Destination: {output_dir}")
    print(f"DPI:         300 (high quality)")
    print("=" * 60)

    # Convert each track map
    success_count = 0
    total_count = len(track_name_mapping)

    for pdf_filename, png_filename in track_name_mapping.items():
        pdf_path = pdf_dir / pdf_filename
        png_path = output_dir / png_filename

        if not pdf_path.exists():
            print(f"⚠ {pdf_filename} not found, skipping...")
            continue

        if pdf_to_png(str(pdf_path), str(png_path), dpi=300):
            success_count += 1

    print("=" * 60)
    print(f"Conversion Complete: {success_count}/{total_count} tracks converted")
    print("=" * 60)

    # List generated files
    if success_count > 0:
        print("\nGenerated files:")
        for png_file in sorted(output_dir.glob("*.png")):
            size_kb = os.path.getsize(png_file) / 1024
            print(f"  - {png_file.name} ({size_kb:.1f} KB)")

    return success_count == total_count


if __name__ == "__main__":
    success = convert_all_track_maps()
    exit(0 if success else 1)
