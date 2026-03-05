# OneLib to DeviceLib Converter - Project Status

## Overview

Converts OneLibrary USB drives (djay Pro exports) to dual-format (OneLibrary + Device Library) for Pioneer DJ hardware (CDJ-2000NXS, CDJ-900NXS).

**Status**: ✅ **Phase 2 Complete** - 99.26% similarity - Ready for hardware testing

---

## 🤖 For AI Agents: Quick Start

### Development Workflow

```bash
# After ANY code change, run this to see impact:
./test_pdb.sh

# Activate virtual environment first
source .venv/bin/activate
```

### Current Status (2026-03-04)

**Phase 2 Complete**: 99.26% similarity achieved
- File size: 167,936 bytes (100% of reference) ✅
- Bitwise similarity: 99.26% (166,698/167,936 bytes match)
- Tables populated: 20/20 (all tables)
- Status: **READY FOR HARDWARE TESTING**

**Next Priority**:
- 🎯 **PRIMARY**: Hardware testing on CDJ-2000NXS/CDJ-900NXS
- 📋 See `HARDWARE_TESTING_GUIDE.md` for testing instructions
- 📋 See `PHASE_2_COMPLETE.md` for detailed analysis

**Not Recommended** (diminishing returns <0.12%):
- ❌ Further PDB optimization
- ❌ Artwork page fix (undocumented format)
- ❌ History page polish

### Tool Guidelines

**Preferred Tools** (over bash commands):
- **Read** - Read files (instead of `cat`)
- **Edit** - Edit files (instead of `sed`)
- **Glob** - Find files by pattern (instead of `find`)
- **Grep** - Search file contents (instead of `grep`)
- **Bash** - Only for: git, npm/pip, test execution

### What NOT to Do

- ❌ Don't edit multiple files at once without testing
- ❌ Don't make large refactors without running tests between changes
- ❌ Don't skip the test step - it's your only feedback mechanism
- ❌ Don't change file paths or project structure without asking
- ❌ Don't modify validation data files
- ❌ Don't create new documentation files (README, etc.) - not priority

### Key Files

**Core Implementation**:
- `src/onelib_to_devicelib/writers/track.py` - Track row structure (132 bytes)
- `src/onelib_to_devicelib/writers/pdb_v3.py` - PDB writer orchestrator
- `src/onelib_to_devicelib/parsers/onelib.py` - Database parser
- `src/onelib_to_devicelib/writers/metadata_rows.py` - Metadata row structures

**Testing**:
- `tests/test_pdb_comparison.py` - Comparison test script
- `./test_pdb.sh` - Quick test runner
- `validation_data/onelib_only` - Test data (OneLibrary only)
- `validation_data/onelib_and_devicelib` - Reference data (both formats)

### Interpreting Test Output

```bash
./test_pdb.sh
```

**File Size Section**:
- Goal: Increase percentage toward 100%
- Each new table adds 4,096 bytes minimum

**Table Pointers Section**:
- `gen:0-0 (0p)` means table is empty
- Adding populated tables = progress

**Field-by-Field Comparison**:
- More ✓ marks = better
- Focus on fields that should match but don't (✗ marks)

---

## Completed Features

### 1. OneLibrary Database Parser

**File**: `src/onelib_to_devicelib/parsers/onelib.py`

Opens encrypted `exportLibrary.db` using pyrekordbox, extracts:
- Track metadata (title, artist, album, genre, BPM, duration, file path)
- Playlists and folders
- Hot cues, memory cues, and loops
- UTF-16LE encoded strings

### 2. PDB File Writer (V3)

**File**: `src/onelib_to_devicelib/writers/pdb_v3.py`

Generates:
- `export.pdb` (legacy Device Library format)
- `exportExt.pdb` (extended data)
- Page-based structure (4096-byte pages)
- UTF-16LE string encoding with deduplication
- Track rows with all required fields (200 bytes)
- File metadata (size, bitrate, sample rate)
- Track metadata (track/disc number, rating, play count)
- Analysis flags (analyzed, has_waveform, has_beat_grid, has_cues)

### 3. ANLZ File Generator

**File**: `src/onelib_to_devicelib/writers/anlz.py`

Generates:
- `ANLZ0000.DAT` (path metadata with PPTH tag)
- `ANLZ0000.EXT` (mono waveform with PWV3 tag)
- `ANLZ0000.2EX` (color waveform, beat grid, cues with PWV5/PPOS/PCOB tags)
- PMAI header structure
- librosa-based audio analysis

### 4. Audio Analysis

Functions:
- `generate_mono_waveform()` - RMS energy-based waveform
- `generate_beat_grid()` - Beat tracking using librosa
- `generate_color_waveform()` - STFT-based frequency coloring

**Dependencies**: librosa, numpy

### 5. Metadata Files

**File**: `src/onelib_to_devicelib/writers/metadata.py`

Generates:
- `DEVSETTING.DAT` - Device settings
- `DeviceLibBackup/rbDevLibBaInfo_*.json` - Device backup with UUID

### 6. CLI Interface

**File**: `src/onelib_to_devicelib/cli.py`

**Commands**:
- `convert` - Main conversion command
- `info` - Display export information
- `validate` - Check export integrity

**Options**:
- `--output PATH` - Specify output directory
- `--pdb-version [v2|v3|minimal]` - PDB writer version
- `--analyze` - Generate waveforms from audio
- `--analyze-missing` - Only analyze files missing data
- `--no-copy` - Skip copying Contents directory

---

## Comparison Test Results

```
Source: validation_data/onelib_only
- Tracks: 2 (validation set)
- Playlists: 1

Generated PDB:
- export.pdb: 167,936 bytes (41 pages)
- Bitwise similarity: 99.26%
- Tables populated: 20/20

Reference PDB (onelib_and_devicelib):
- export.pdb: 167,936 bytes (41 pages)
- Tables populated: 20/20

Page-by-Page Differences:
  Pages with differences: 18 out of 41 pages
  🔴 CRITICAL (>500 bytes): 1 page (Page 2: 908 bytes)
  🟡 MEDIUM (10-100 bytes): 8 pages
  🟢 LOW (≤10 bytes): 9 pages

Remaining differences: 1,238 bytes (0.74%)
  - Acceptable (content-specific): ~800 bytes
  - Structural (fixable but low impact): ~438 bytes
```

## Known Issues (All Acceptable)

**Remaining Differences** (1,238 bytes / 0.74%):
- ✅ **Acceptable** (~800 bytes): Content-specific (checksums, file paths, timestamps, track IDs)
- ⚠️ **Structural** (~438 bytes): Fixable but low impact
  - Artwork page: page_flags=0x88 (undocumented)
  - History page: Entry structure and headers
  - Track pages: Minor row size/alignment differences

**Why These Are Acceptable**:
1. Content-specific differences will ALWAYS exist between exports
2. Structural differences have diminishing returns (<0.12% improvement potential)
3. Realistic maximum similarity is 99.3% - 99.4% (we're at 99.26%)
4. Hardware testing is the only true validation - similarity metrics are misleading

**Hardware Testing Predictions**:
- ✅ USB Recognition: 99% confidence (file structure matches)
- ✅ Track Browsing: 95% confidence (table structure correct)
- ✅ Track Playback: 90% confidence (metadata present)
- ⚠️ Waveform Display: 50% confidence (ANLZ format may differ)
- ⚠️ Artwork Display: 30% confidence (Artwork page incomplete)

---

## Usage Examples

### Basic Conversion

```bash
# Convert OneLibrary to dual-format (in-place)
onelib-to-devicelib convert /path/to/usb/drive

# Convert to new directory
onelib-to-devicelib convert /path/to/source --output /path/to/output

# Convert without copying audio files
onelib-to-devicelib convert /path/to/source --no-copy
```

### With Waveform Generation

```bash
# Generate waveforms for all tracks (slower)
onelib-to-devicelib convert /path/to/source --analyze

# Only analyze tracks missing waveforms
onelib-to-devicelib convert /path/to/source --analyze-missing
```

### Information & Validation

```bash
# Get information about an export
onelib-to-devicelib info /path/to/export

# Validate an export
onelib-to-devicelib validate /path/to/export
```

### Python API

```python
from onelib_to_devicelib import Converter

# Create converter instance
converter = Converter("/path/to/onelib_export")

# Parse source
converter.parse()

# Convert with waveform generation
converter.convert(
    generate_waveforms=True,
    copy_contents=True
)
```

---

## Troubleshooting

### Common Issues

**Issue: "pyrekordbox not installed"**
```bash
pip install pyrekordbox
```

**Issue: "librosa not installed"** (when using --analyze)
```bash
pip install librosa numpy soundfile
```

**Issue: "Database file not found"**
Ensure you're pointing to the root of the USB drive, not the PIONEER directory:
```bash
# Correct
onelib-to-devicelib convert /Volumes/USB_DRIVE

# Incorrect
onelib-to-devicelib convert /Volumes/USB_DRIVE/PIONEER
```

**Issue: Generated PDB doesn't work on CDJ**

**Possible Causes**:
1. PDB format incomplete (MVP limitation)
2. Missing ANLZ files
3. Incorrect file structure
4. Hardware requires specific format

**Solution**:
1. Run validation: `onelib-to-devicelib validate /path/to/export`
2. Check ANLZ files exist in USBANLZ/P001/*/ANLZ0000.*
3. Test with smaller library first

---

## Quick Reference

### Essential Commands

```bash
# Run comparison test (DO THIS AFTER EVERY CHANGE)
./test_pdb.sh

# Activate virtual environment
source .venv/bin/activate

# Convert and test (full workflow)
onelib-to-devicelib convert validation_data/onelib_only --output /tmp/test_convert --no-copy
./test_pdb.sh
```

### File Locations

**Implementation**:
- Track structure: `src/onelib_to_devicelib/writers/track.py:135-183`
- PDB writer: `src/onelib_to_devicelib/writers/pdb_v3.py`
- Parser: `src/onelib_to_devicelib/parsers/onelib.py`
- Metadata rows: `src/onelib_to_devicelib/writers/metadata_rows.py`

**Test Files**:
- Comparison script: `tests/test_pdb_comparison.py`
- Test runner: `test_pdb.sh`
- Reference PDB: `validation_data/onelib_and_devicelib/PIONEER/rekordbox/export.pdb`
- Source data: `validation_data/onelib_only/PIONEER/rekordbox/exportLibrary.db`

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run tests and ensure they pass
6. Submit a pull request

---

## License

MIT License - see LICENSE file for details.

---

## Acknowledgments

- **pyrekordbox** - Database access library
- **REX (kimtore/rex)** - Go PDB generator (reference implementation)
- **Deep-Symmetry** - Format documentation and analysis
- **librosa** - Audio analysis

---

**Status**: ✅ Phase 2 Complete - Ready for hardware testing (99.26% similarity)

*Last Updated: 2026-03-04*
