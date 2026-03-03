"""
Command-line interface for OneLib to DeviceLib converter.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import click

from onelib_to_devicelib import __version__
from onelib_to_devicelib.convert import Converter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version=__version__)
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output")
@click.option("-q", "--quiet", is_flag=True, help="Suppress non-error output")
def main(verbose: bool = False, quiet: bool = False):
    """
    OneLib to DeviceLib Converter

    Convert OneLibrary USB drives to dual-format (OneLibrary + Device Library)
    for compatibility with older Pioneer DJ hardware.

    \b
    Example:
        onelib-to-devicelib convert /path/to/usb/drive
    """
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    elif quiet:
        logging.getLogger().setLevel(logging.ERROR)


@main.command()
@click.argument("source", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o", "--output",
    type=click.Path(path_type=Path),
    help="Output directory (default: in-place conversion)"
)
@click.option(
    "--pdb-version",
    type=click.Choice(['v2', 'v3', 'minimal'], case_sensitive=False),
    default='v3',
    help="PDB writer version: v3 (with metadata), minimal (tracks only), v2 (legacy)"
)
@click.option(
    "--analyze",
    is_flag=True,
    help="Generate waveforms by analyzing audio files"
)
@click.option(
    "--analyze-missing",
    is_flag=True,
    help="Only analyze audio files missing analysis data"
)
@click.option(
    "--no-copy",
    is_flag=True,
    help="Don't copy Contents directory to output"
)
def convert(
    source: Path,
    output: Optional[Path],
    pdb_version: str,
    analyze: bool,
    analyze_missing: bool,
    no_copy: bool,
):
    """
    Convert OneLibrary export to Device Library format.

    SOURCE is the path to the OneLibrary USB drive root directory.

    If OUTPUT is not specified, performs in-place conversion.
    """
    try:
        click.echo(f"🎵 Converting OneLibrary export...")
        click.echo(f"   Source: {source}")
        if output:
            click.echo(f"   Output: {output}")
        click.echo(f"   PDB Version: {pdb_version}")

        # Initialize converter
        converter = Converter(source, output, pdb_version=pdb_version)

        # Parse source
        click.echo(f"\n📖 Parsing OneLibrary database...")
        converter.parse()

        parser = converter.parser
        click.echo(f"   Found {len(parser.tracks)} tracks")
        click.echo(f"   Found {len(parser.playlists)} playlists")

        # Perform conversion
        click.echo(f"\n🔄 Converting to Device Library format...")
        converter.convert(
            generate_waveforms=analyze,
            analyze_missing=analyze_missing,
            copy_contents=not no_copy,
        )

        click.echo(f"\n✅ Conversion complete!")

    except FileNotFoundError as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        if logger.isEnabledFor(logging.DEBUG):
            import traceback
            traceback.print_exc()
        sys.exit(1)


@main.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
def info(path: Path):
    """
    Display information about a OneLibrary or Device Library export.

    PATH is the path to the USB drive root directory.
    """
    try:
        converter = Converter(path)

        click.echo(f"📊 Analyzing: {path}\n")

        # Parse database
        converter.parse()
        parser = converter.parser

        # Display track count
        tracks = parser.get_tracks()
        click.echo(f"Tracks: {len(tracks)}")

        # Display playlist count
        playlists = parser.get_playlists()
        click.echo(f"Playlists: {len(playlists)}")

        # Display format info
        pioneer_path = converter.pioneer_path

        # Check for OneLibrary (exportLibrary.db)
        export_db = pioneer_path / "rekordbox" / "exportLibrary.db"
        if export_db.exists():
            click.echo(f"Format: OneLibrary (Device Library Plus)")

        # Check for Device Library (export.pdb)
        export_pdb = pioneer_path / "rekordbox" / "export.pdb"
        if export_pdb.exists():
            click.echo(f"Format: Device Library (legacy)")

        # Check for ANLZ files
        usbanlz_path = pioneer_path / "USBANLZ"
        if usbanlz_path.exists():
            anlz_count = len(list(usbanlz_path.glob("P*/*/ANLZ0000.DAT")))
            click.echo(f"Analysis Files: {anlz_count} tracks")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
def validate(path: Path):
    """
    Validate a OneLibrary or Device Library export.

    Checks for missing files, corrupt data, and compatibility issues.

    PATH is the path to the USB drive root directory.
    """
    try:
        click.echo(f"🔍 Validating: {path}\n")

        issues = []
        warnings = []

        converter = Converter(path)
        pioneer_path = converter.pioneer_path

        # Check required directories
        required_dirs = ["rekordbox", "USBANLZ", "Artwork"]
        for dir_name in required_dirs:
            dir_path = pioneer_path / dir_name
            if not dir_path.exists():
                issues.append(f"Missing required directory: PIONEER/{dir_name}")

        # Check database files
        export_db = pioneer_path / "rekordbox" / "exportLibrary.db"
        if not export_db.exists():
            issues.append("Missing exportLibrary.db (OneLibrary format)")
        else:
            try:
                converter.parse()
                parser = converter.parser
                tracks = parser.get_tracks()

                # Check for tracks without analysis
                without_analysis = [t for t in tracks if not t.has_analysis()]
                if without_analysis:
                    warnings.append(
                        f"{len(without_analysis)} tracks missing waveform analysis"
                    )

            except Exception as e:
                issues.append(f"Cannot read exportLibrary.db: {e}")

        # Check for export.pdb (legacy format)
        export_pdb = pioneer_path / "rekordbox" / "export.pdb"
        if not export_pdb.exists():
            warnings.append(
                "Missing export.pdb (Device Library format) - "
                "not compatible with CDJ-2000NXS/CDJ-900NXS"
            )

        # Display results
        if not issues and not warnings:
            click.echo("✅ No issues found!\n")
        else:
            if warnings:
                click.echo("⚠️  Warnings:")
                for warning in warnings:
                    click.echo(f"   - {warning}")
                click.echo()

            if issues:
                click.echo("❌ Issues:")
                for issue in issues:
                    click.echo(f"   - {issue}")
                click.echo()

        # Summary
        click.echo(f"Issues: {len(issues)}")
        click.echo(f"Warnings: {len(warnings)}")

        if issues:
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
