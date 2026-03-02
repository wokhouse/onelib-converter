# OneLib to DeviceLib Converter

Convert OneLibrary USB drives exported from djay Pro into dual-format (OneLibrary + Device Library) exports compatible with older Pioneer DJ hardware.

## Problem

OneLibrary is only supported on newer Pioneer DJ hardware:
- ✅ CDJ-3000, CDJ-3000X
- ✅ OPUS-QUAD, XDJ-AZ, OMNIS-DUO

Older hardware requires the traditional Device Library format:
- ❌ CDJ-2000NXS, CDJ-900NXS

Currently, djay users must import their library into Rekordbox and re-export, which is slow and tedious.

## Solution

This CLI tool converts OneLibrary exports to include both formats:
1. Preserves existing OneLibrary format
2. Adds legacy Device Library format (export.pdb + ANLZ files)
3. Generates required analysis data (waveforms, beat grids, cues)

## Installation

```bash
# Install from source
pip install -e .

# Or install with audio analysis dependencies
pip install -e ".[analysis]"
```

## Usage

```bash
# Basic conversion
onelib-to-devicelib convert /path/to/usb/drive

# Specify output directory
onelib-to-devicelib convert /path/to/source --output /path/to/output

# Generate waveforms for missing analysis
onelib-to-devicelib convert /path/to/source --analyze

# Validate an existing export
onelib-to-devicelib validate /path/to/export

# Show detailed information
onelib-to-devicelib info /path/to/export
```

## Features

- ✅ Reads OneLibrary format (exportLibrary.db)
- ✅ Generates legacy Device Library format (export.pdb)
- ✅ Creates ANLZ analysis files (DAT, EXT, 2EX)
- ✅ Preserves metadata, cues, loops, playlists
- ✅ Optional audio analysis for missing waveforms
- ✅ Generates artwork thumbnails
- ✅ Creates supporting files (DEVSETTING.DAT, etc.)

## Project Structure

```
src/onelib_to_devicelib/
├── cli.py              # Main CLI interface
├── parsers/
│   ├── onelib.py       # OneLibrary database reader
│   └── anlz.py         # ANLZ file parser
├── writers/
│   ├── pdb.py          # PDB file writer
│   └── anlz.py         # ANLZ file generator
├── analyzers/
│   └── audio.py        # Audio analysis module
└── utils/
    ├── paths.py        # Path utilities
    └── crypto.py       # Encryption helpers
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev,analysis]"

# Run tests
pytest

# Format code
black src tests

# Type checking
mypy src
```

## References

- [pyrekordbox documentation](https://pyrekordbox.readthedocs.io)
- [Deep-Symmetry Rekordbox Analysis](https://djl-analysis.deepsymmetry.org)
- [REX Rekordbox Exporter](https://github.com/kimtore/rex)

## License

CC-BY-SA
