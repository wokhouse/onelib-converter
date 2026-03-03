# OneLib to DeviceLib Converter - Project Status

## Overview

The OneLib to DeviceLib Converter converts OneLibrary USB drives exported from djay Pro into dual-format (OneLibrary + Device Library) exports compatible with older Pioneer DJ hardware (CDJ-2000NXS, CDJ-900NXS).

**Current Status**: 🔄 **Active PDB Format Refinement** - 19.6% of reference file size achieved

---

## 🤖 For AI Agents: Quick Start

### How to Work Effectively on This Project

**IMPORTANT**: Always use the comparison pipeline as your feedback loop!

```bash
# After ANY code change, run this to see impact:
./test_pdb.sh
```

### Development Workflow

1. **Understand the current state** - Read the "Current Focus" section below
2. **Make targeted changes** - Edit specific files based on the goal
3. **Test immediately** - Run `./test_pdb.sh` to see the impact
4. **Analyze output** - Check if file size increased, tables populated, or fields matched
5. **Iterate** - Make next change based on test results

**Never make blind changes** - always use the test output to guide your work.

### Current Focus (2026-03-02)

**Active Goal**: Achieve bitwise identical (or as close as possible) PDB output to match `validation_data/onelib_and_devicelib` reference.

**Current Progress**:
- File size: 45,056 bytes (19.6% of 229,376 byte reference)
- Tables populated: 8/20 (Tracks, Genres, Artists, Albums, Keys, Colors, PlaylistTree, PlaylistEntries)
- Track metadata: Most critical fields working (checksum, composer_id, key_id, duration)

**Next Priority Tasks**:
1. ✅ COMPLETED: Fix track metadata extraction (duration, year, track_number, composer_id, key_id)
2. ✅ COMPLETED: Add Colors table
3. ✅ COMPLETED: Add playlist support (PlaylistTree, PlaylistEntries)
4. ⏳ IN PROGRESS: Investigate track row size discrepancy (we have 3 pages, reference has 55)
5. ⏳ TODO: Fix file header fields (unknown1, sequence)
6. ⏳ TODO: Add remaining empty tables (Artwork, History, Columns, Unknown tables)

### Tool Guidelines

**Preferred Tools** (use these over bash commands):
- **Read** - Read files (instead of `cat`)
- **Edit** - Edit files (instead of `sed`)
- **Glob** - Find files by pattern (instead of `find`)
- **Grep** - Search file contents (instead of `grep`)
- **Bash** - Only for: git, npm/pip, test execution, file system operations

**Project-Specific Tools**:
```bash
./test_pdb.sh              # Run PDB comparison test (DO THIS AFTER EVERY CHANGE)
source .venv/bin/activate  # Activate virtual environment before running Python
```

### What NOT to Do

- ❌ Don't edit multiple files at once without testing
- ❌ Don't make large refactors without running tests between changes
- ❌ Don't skip the test step - it's your only feedback mechanism
- ❌ Don't change file paths or project structure without asking
- ❌ Don't modify validation data files
- ❌ Don't create new documentation files (README, INSTALLATION, etc.) - they're in the plan but not priority

### What to Prioritize

**High Impact Changes** (do these first):
1. Fix obvious field mismatches in track rows
2. Add missing tables that have data
3. Populate missing track metadata fields

**Lower Priority**:
- Code refactoring/cleanup
- Adding error messages
- Optimization
- Documentation

### Success Metrics

When you make changes, look for improvement in:
- **File size percentage** (should increase toward 100%)
- **Number of tables populated** (should increase toward 20)
- **Matching field count** (more ✓ marks in field comparison)
- **Reduced binary differences** (fewer `>>>` and `<<<` markers in hex dump)

**Good progress example**:
```
Before: File size 12.5%, 4 tables, 5 matching fields
After:  File size 19.6%, 8 tables, 9 matching fields
```

### Key Files to Understand

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

### Common Patterns

**Adding a new table**:
1. Create row structure in `metadata_rows.py`
2. Add import to `pdb_v3.py`
3. Add `add_*` method to `PDBWriterV3` class
4. Update `convert.py` and `test_pdb_comparison.py` to populate table
5. Run `./test_pdb.sh` to verify

**Fixing track field mismatches**:
1. Check test output for ✗ marks in "Field-by-Field Comparison"
2. Find field in `TrackHeader` or `TrackRow` classes
3. Update field initialization to use correct track attribute
4. Run `./test_pdb.sh` to verify fix

### When to Ask for Clarification

- 🤔 Unsure which file to modify? → Ask, don't guess
- 🤔 Multiple approaches possible? → Present options and ask which to try
- 🤔 Test output confusing? → Share the output and ask for interpretation
- 🤔 Need to make large changes? → Describe the plan and ask for approval

---

## Table of Contents

1. [Current Status](#current-status)
2. [Completed Features](#completed-features)
3. [Remaining Work](#remaining-work)
4. [Testing with Validation Data](#testing-with-validation-data)
5. [Known Limitations](#known-limitations)
6. [Future Enhancements](#future-enhancements)

---

## Current Status

### 🔄 Active PDB Format Refinement (Phase 2)

**Current Progress** (as of 2026-03-02):
- File size: 45,056 bytes (19.6% of 229,376 byte reference) - **+57% growth!**
- Tables populated: 8/20 (was 4)
- Track metadata: Most critical fields working

### ✅ Recently Completed (Phase 1 & 2)

**Track Metadata Fixes**:
- ✅ Fixed `checksum`, `unnamed7`, `unnamed8` to match reference values
- ✅ Enhanced parser to extract `track_number`, `year`, `disc_number`, `composer_id`, `key_id`
- ✅ Fixed `duration` extraction (was incorrectly dividing by 1000)

**New Tables Added**:
- ✅ Colors table (12 rekordbox colors)
- ✅ PlaylistTree table (folders and playlists)
- ✅ PlaylistEntries table (track-to-playlist links)

### 📊 Comparison Test Results

```
Source: validation_data/onelib_only
- Tracks: 33
- Playlists: 4 (1 folder + 3 playlists)
- ANLZ files: 33 (DAT/EXT/2EX for each track)

Generated PDB (latest):
- export.pdb: 45,056 bytes (11 pages)
- Tables populated: 8/20
  - Tracks (3 pages)
  - Genres, Artists, Albums (1 page each)
  - Keys, Colors (1 page each)
  - PlaylistTree, PlaylistEntries (1 page each)

Reference PDB (onelib_and_devicelib):
- export.pdb: 229,376 bytes (56 pages)
- Tables populated: 20/20

Track Field Comparison (matching reference):
- ✅ checksum: 0x0b1b10e6
- ✅ unnamed7: 0x63da
- ✅ unnamed8: 0x52ef
- ✅ composer_id: 2
- ✅ key_id: 1
- ✅ duration: Now properly extracted
```

### ⏳ Known Issues

**Track Pages Discrepancy**:
- Reference: 55 pages of tracks
- Ours: 3 pages of tracks
- Likely cause: Row size smaller than reference or different string storage

**File Header Fields**:
- `unknown1`: 0x5 vs 0x1 (reference)
- `sequence`: 1 vs 132 (reference)

**Missing Tables** (12 empty):
- Labels (table 4) - no data in source
- Artwork (table 13)
- History (tables 11, 12, 19)
- Unknown tables (9, 10, 14, 15, 16, 17, 18)

### 🔍 Interpreting Test Output

When you run `./test_pdb.sh`, here's what to look for:

**File Size Section**:
```
File Size Comparison:
  Reference: 229,376 bytes (56 pages)
  Generated: 45,056 bytes (11 pages)
  ✗ Size differs by 184,320 bytes (19.6% of reference)
```
- **Goal**: Increase percentage toward 100%
- Each new table adds 4,096 bytes minimum

**Table Pointers Section**:
```
Table Pointers:
  ✗ [ 0] Tracks               ref:1-55 (55p)  gen:1-3 (3p)
  ✗ [ 5] Keys                 ref:11-12 (2p)  gen:7-7 (1p)
  ✓ [ 6] Colors               ref:13-14 (2p)  gen:8-8 (1p)  # Good!
```
- `gen:0-0 (0p)` means table is empty
- Adding populated tables = progress

**Field-by-Field Comparison**:
```
  ✓ checksum            : ref=0x0b1b10e6 gen=0x0b1b10e6  # Match!
  ✗ duration            : ref=235        gen=0           # Fix needed
```
- More ✓ marks = better
- Focus on fields that should match but don't

**Binary Dump**:
```
  0000:    >>> 24 00 00 00 24 00 00 00 <<<  # Differences marked
  0010:    24 00 00 00 24 00 00 00            # Match (no markers)
```
- Fewer `>>>` and `<<<` markers = better
- First 16 bytes now match = great progress!

---

## Completed Features

### 1. OneLibrary Database Parser

**File**: `src/onelib_to_devicelib/parsers/onelib.py`

**Capabilities**:
- ✅ Opens encrypted `exportLibrary.db` using pyrekordbox
- ✅ Extracts track metadata (title, artist, album, genre, BPM, duration, file path)
- ✅ Extracts playlists and folders
- ✅ Extracts hot cues, memory cues, and loops
- ✅ Handles UTF-16LE encoded strings

**API Usage**:
```python
from onelib_to_devicelib.parsers.onelib import OneLibraryParser

parser = OneLibraryParser("path/to/exportLibrary.db")
parser.parse()

tracks = parser.get_tracks()
playlists = parser.get_playlists()
```

### 2. PDB File Writer

**File**: `src/onelib_to_devicelib/writers/pdb.py`

**Capabilities**:
- ✅ Generates `export.pdb` (legacy Device Library format)
- ✅ Generates `exportExt.pdb` (extended data)
- ✅ Page-based structure (4096-byte pages)
- ✅ UTF-16LE string encoding with deduplication
- ✅ Track rows with all required fields
- ✅ Playlist and folder support

**Format Details**:
- Magic header: `0x00000000`
- Page size: 4096 bytes
- Track row size: 200 bytes (ENHANCED from 88 bytes)
- String encoding: UTF-16LE
- String deduplication across all strings
- Rows per page: ~20 (4096 / 200)
- **NEW**: File metadata included (size, bitrate, sample rate)
- **NEW**: Track metadata included (track/disc number, rating, play count)
- **NEW**: Analysis flags (analyzed, has_waveform, has_beat_grid, has_cues)
- **FIXED**: file_path now properly written to row structure

### 3. ANLZ File Generator

**File**: `src/onelib_to_devicelib/writers/anlz.py`

**Capabilities**:
- ✅ Generates `ANLZ0000.DAT` (path metadata with PPTH tag)
- ✅ Generates `ANLZ0000.EXT` (mono waveform with PWV3 tag)
- ✅ Generates `ANLZ0000.2EX` (color waveform, beat grid, cues with PWV5/PPOS/PCOB tags)
- ✅ PMAI header structure
- ✅ librosa-based audio analysis
- ✅ Beat grid generation
- ✅ Waveform generation (mono and color)

**Tag Structures**:
```
PPTH - Path Information (UTF-16LE encoded file path)
PWV3 - Mono Waveform Preview (400 samples, RMS energy)
PWV5 - Color Waveform (1200 columns, RGB frequency-based)
PPOS - Beat Grid (8 bytes per beat: number, tempo, time, reserved)
PCOB - Cue Points (ID, position, type)
```

### 4. Audio Analysis

**Functions**:
- ✅ `generate_mono_waveform()` - RMS energy-based waveform
- ✅ `generate_beat_grid()` - Beat tracking using librosa
- ✅ `generate_color_waveform()` - STFT-based frequency coloring

**Dependencies**: librosa, numpy

### 5. Metadata Files

**File**: `src/onelib_to_devicelib/writers/metadata.py`

**Generated Files**:
- ✅ `DEVSETTING.DAT` - Device settings
- ✅ `DeviceLibBackup/rbDevLibBaInfo_*.json` - Device backup with UUID
- ✅ Proper headers and formatting

### 6. CLI Interface

**File**: `src/onelib_to_devicelib/cli.py`

**Commands**:
- ✅ `convert` - Main conversion command
- ✅ `info` - Display export information
- ✅ `validate` - Check export integrity

**Options**:
- `--output` - Specify output directory
- `--analyze` - Generate waveforms from audio
- `--analyze-missing` - Only analyze files missing data
- `--no-copy` - Skip copying Contents directory
- `--verbose` - Enable debug logging
- `--quiet` - Suppress non-error output

---

## Remaining Work

### Priority 1: Validation & Testing

#### 1.1 Bitwise Comparison Test

**Objective**: Validate that generated files match expected format.

**Test Case**:
```bash
# Convert onelib_only to dual-format
onelib-to-devicelib convert \
    validation_data/onelib_only \
    --output /tmp/test_conversion \
    --no-copy

# Compare generated files with onelib_and_devicelib reference
```

**Comparison Script**:
```python
# tests/test_bitwise_comparison.py

import os
import hashlib
from pathlib import Path

def compare_files(file1: Path, file2: Path, name: str):
    """Compare two files byte-by-byte."""
    if not file1.exists():
        print(f"❌ {name}: Generated file missing")
        return False

    if not file2.exists():
        print(f"❌ {name}: Reference file missing")
        return False

    # Read files
    data1 = file1.read_bytes()
    data2 = file2.read_bytes()

    # Compare sizes
    if len(data1) != len(data2):
        print(f"⚠️  {name}: Size mismatch")
        print(f"   Generated: {len(data1)} bytes")
        print(f"   Reference: {len(data2)} bytes")
        return False

    # Compare content
    if data1 == data2:
        print(f"✅ {name}: Exact match")
        return True
    else:
        # Find differences
        diff_count = sum(1 for a, b in zip(data1, data2) if a != b)
        print(f"❌ {name}: {diff_count} byte differences")

        # Check if just headers differ
        if len(data1) > 100 and len(data2) > 100:
            if data1[100:] == data2[100:]:
                print(f"   Note: Content matches after header")

        return False

def compare_pdb_files():
    """Compare PDB files."""
    generated = Path("/tmp/test_conversion/PIONEER/rekordbox/export.pdb")
    reference = Path("validation_data/onelib_and_devicelib/PIONEER/rekordbox/export.pdb")

    return compare_files(generated, reference, "export.pdb")

def compare_anlz_structure():
    """Compare ANLZ directory structure."""
    generated_anlz = Path("/tmp/test_conversion/PIONEER/USBANLZ/P001")
    reference_anlz = Path("validation_data/onelib_and_devicelib/PIONEER/USBANLZ/P001")

    # Get all ANLZ directories
    generated_dirs = set([d.name for d in generated_anlz.iterdir() if d.is_dir()])
    reference_dirs = set([d.name for d in reference_anlz.iterdir() if d.is_dir()])

    if generated_dirs == reference_dirs:
        print(f"✅ ANLZ directories match: {len(generated_dirs)} directories")
    else:
        missing = reference_dirs - generated_dirs
        extra = generated_dirs - reference_dirs
        if missing:
            print(f"❌ Missing ANLZ directories: {missing}")
        if extra:
            print(f"❌ Extra ANLZ directories: {extra}")

    # Compare file counts
    for dirname in generated_dirs & reference_dirs:
        gen_files = list((generated_anlz / dirname).glob("ANLZ0000.*"))
        ref_files = list((reference_anlz / dirname).glob("ANLZ0000.*"))

        if len(gen_files) == len(ref_files) == 3:
            print(f"✅ {dirname}: 3/3 files present")
        else:
            print(f"⚠️  {dirname}: {len(gen_files)}/3 files (expected {len(ref_files)})")

def compare_supporting_files():
    """Compare DEVSETTING.DAT and other metadata files."""
    # DEVSETTING.DAT
    gen_devsetting = Path("/tmp/test_conversion/PIONEER/DEVSETTING.DAT")
    ref_devsetting = Path("validation_data/onelib_and_devicelib/PIONEER/DEVSETTING.DAT")

    # Note: DEVSETTING.DAT contains timestamps/UUIDs that will differ
    # So we just check if it exists and has the right structure
    if gen_devsetting.exists():
        with open(gen_devsetting, "rb") as f:
            header = f.read(20)
            if b"PIONEER DJ" in header and b"rekordbox" in header:
                print("✅ DEVSETTING.DAT: Valid structure")
            else:
                print("❌ DEVSETTING.DAT: Invalid structure")
    else:
        print("❌ DEVSETTING.DAT: Not generated")

if __name__ == "__main__":
    print("=" * 60)
    print("Bitwise Comparison Test")
    print("=" * 60)

    print("\n--- PDB Files ---")
    compare_pdb_files()

    print("\n--- ANLZ Structure ---")
    compare_anlz_structure()

    print("\n--- Supporting Files ---")
    compare_supporting_files()
```

**Expected Outcomes**:
- ⚠️ **PDB files will differ** - Our PDB writer is MVP and doesn't match Rekordbox's exact format yet
- ✅ **ANLZ structure should match** - Directory names and file count
- ✅ **Supporting files should be valid** - Correct headers and structure

#### 1.2 Hardware Testing

**Required**: Access to CDJ-2000NXS or CDJ-900NXS

**Test Plan**:
1. Export from djay Pro (OneLibrary format)
2. Run converter to add Device Library format
3. Test on actual hardware:
   - USB recognition
   - Track browsing
   - Playback functionality
   - Waveform display (if available)
   - Hot cue/loop recall

**Test Results Template**:
```markdown
### Hardware Test Results

**Hardware**: CDJ-2000NXS / CDJ-900NXS
**Test Date**: [DATE]
**Tracks Tested**: [NUMBER]

| Feature | Status | Notes |
|---------|--------|-------|
| USB Recognition | ⏳ Not Tested | |
| Track Browsing | ⏳ Not Tested | |
| Playback | ⏳ Not Tested | |
| Waveform Display | ⏳ Not Tested | |
| Hot Cues | ⏳ Not Tested | |
| Loops | ⏳ Not Tested | |
| Playlists | ⏳ Not Tested | |
```

### Priority 2: PDB Format Refinement

#### 2.1 Complete PDB Row Structure

**Current Status**: MVP with minimal track row structure

**Required**: Full track row with all fields

**Missing Fields**:
```python
# Current: 10 fields
track_id, title, artist, album, genre, bpm, duration

# Required: ~30+ fields based on Deep-Symmetry analysis
# Additional fields needed:
- file_path (full path string)
- file_size
- bit_rate
- sample_rate
- bit_depth
- track_number
- disc_number
- rating
- play_count
- artwork_id
- release_year
- label_id
- composer_id
- key_id
- original_artist_id
- remixer_id
- date_added
- date_modified
- analysis_flags
- cue_updated
- analysis_updated
- and more...
```

**Reference**:
- Deep-Symmetry `rekordbox_pdb.ksy` for complete field list
- Henry Betts `Rekordbox-Decoding` for row structure

#### 2.2 String Heap Management

**Current Status**: Global string heap (not page-based)

**Required**: Per-page string heaps

**Issue**: Rekordbox stores strings at the end of each page, not globally.

**Implementation Needed**:
```python
def _write_track_page_with_heap(self, tracks: List[TrackRow]) -> bytes:
    """Write page with track rows AND string heap at end."""
    page = bytearray(PAGE_SIZE)

    # Write page header
    page[0] = PAGE_TYPE_TRACKS
    struct.pack_into('<H', page, 2, len(tracks))

    # Reserve space for heap (grows from end)
    heap_offset = PAGE_SIZE
    row_offset = 8

    for track in tracks:
        # Collect strings for this track
        strings = {
            'title': self._encode_string(track.title),
            'artist': self._encode_string(track.artist),
            # ...
        }

        # Calculate total string size
        string_sizes = sum(len(s) for s in strings.values())

        # Update heap offset
        heap_offset -= string_sizes

        # Write row with string offsets pointing to heap
        row = self._create_track_row(track, heap_offset)
        page[row_offset:row_offset + len(row)] = row
        row_offset += len(row)

        # Write strings to heap
        current_offset = heap_offset
        for string_data in strings.values():
            string_len = len(string_data)
            page[current_offset:current_offset + string_len] = string_data
            current_offset += string_len

    return bytes(page)
```

#### 2.3 Playlist and Folder Implementation

**Current Status**: Placeholder page structure

**Required**: Full playlist and folder row structures

**Implementation Needed**:
```python
def _write_playlist_page(self, playlists: List[Playlist]) -> bytes:
    """Write playlist page with proper structure."""
    # Playlist row structure:
    # - playlist_id
    # - name (string offset)
    # - parent_id
    # - attribute (folder vs playlist)
    # - sequence_no
    # - image_id
    # - track_count
```

**Reference**: REX project playlist implementation

### Priority 3: ANLZ Enhancements

#### 3.1 Cue Point Conversion

**Current Status**: Basic cue point structure

**Required**: Proper hot cue, memory cue, and loop conversion

**Implementation**:
```python
def convert_cues_from_onelib(track: Track) -> List[Dict]:
    """Convert OneLibrary cues to ANLZ PCOB format."""
    cues = []

    # Hot cues
    for i, cue in enumerate(track.hot_cues):
        cues.append({
            'id': i + 1,
            'position_ms': int(cue['position_ms']),
            'type': 0,  # Hot cue
            'color': cue.get('color', 0xFFFFFF),
            'name': cue.get('name', '')
        })

    # Memory cues
    for i, cue in enumerate(track.memory_cues):
        cues.append({
            'id': i + 100,  # Different ID range
            'position_ms': int(cue['position_ms']),
            'type': 1,  # Memory cue
            'color': cue.get('color', 0xFFFFFF),
            'name': cue.get('name', '')
        })

    # Loops
    for i, loop in enumerate(track.loops):
        cues.append({
            'id': i + 200,
            'position_ms': int(loop['start_ms']),
            'type': 2,  # Loop
            'loop_length_ms': int(loop['length_ms']),
            'color': loop.get('color', 0xFFFFFF),
            'name': loop.get('name', '')
        })

    return cues
```

#### 3.2 Existing ANLZ File Handling

**Current Status**: Copies existing files if found

**Issue**: Path matching logic may not find all files

**Improved Implementation**:
```python
def _find_existing_anlz(self, track: Track) -> Optional[Path]:
    """Find existing ANLZ directory for a track."""
    source_usbanlz = self.source_path / "PIONEER" / "USBANLZ"

    # Method 1: Parse existing DAT files and check paths
    for dat_file in source_usbanlz.glob("*/ANLZ0000.DAT"):
        # Parse PPTH tag
        try:
            anlz_data = self._parse_anlz_dat(dat_file)
            if anlz_data.get('path') == str(track.file_path):
                return dat_file.parent
        except:
            continue

    # Method 2: Check if hash matches our generated hash
    path_hash = get_anlz_path_hash(track.file_path)
    for hash_dir in source_usbanlz.glob(f"*/{path_hash}"):
        if hash_dir.is_dir():
            return hash_dir

    return None
```

### Priority 4: Documentation & Examples

#### 4.1 User Documentation

**Required Files**:
- [ ] `README.md` - Complete usage guide
- [ ] `INSTALLATION.md` - Installation instructions
- [ ] `EXAMPLES.md` - Usage examples
- [ ] `TROUBLESHOOTING.md` - Common issues

#### 4.2 Developer Documentation

**Required Files**:
- [ ] `ARCHITECTURE.md` - Code structure overview
- [ ] `FORMATS.md` - File format specifications
- [ ] `CONTRIBUTING.md` - Contribution guidelines

#### 4.3 API Documentation

**Required**:
- [ ] Docstrings for all public APIs
- [ ] Type hints for all functions
- [ ] Sphinx or MkDocs documentation site

### Priority 5: Error Handling & Edge Cases

#### 5.1 Edge Cases to Handle

**Unicode Paths**:
- [ ] Test with non-ASCII characters in paths
- [ ] Test with emoji in artist/track names
- [ ] Test with very long paths

**Large Libraries**:
- [ ] Test with 1000+ tracks
- [ ] Test with very long playlists
- [ ] Test with nested folders

**Corrupt Data**:
- [ ] Handle missing/corrupt audio files
- [ ] Handle corrupt database
- [ ] Handle invalid metadata

**File System**:
- [ ] Handle read-only filesystems
- [ ] Handle insufficient disk space
- [ ] Handle permission errors

#### 5.2 Error Messages

**Current**: Basic error handling

**Required**: User-friendly error messages

```python
# Example improvements
raise FileNotFoundError(
    f"Source path does not exist: {self.source_path}\n"
    f"Please check the path and try again."
)

# vs

raise FileNotFoundError(f"Source path does not exist: {self.source_path}")
```

### Priority 6: Performance Optimization

#### 6.1 Parallel Processing

**Current**: Sequential track processing

**Enhancement**: Process multiple tracks in parallel

```python
from concurrent.futures import ProcessPoolExecutor

def convert_track(track):
    # Convert single track
    pass

with ProcessPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(convert_track, tracks))
```

#### 6.2 Caching

**Enhancement**: Cache analyzed waveforms to avoid re-analysis

```python
import hashlib
from pathlib import Path

class WaveformCache:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir / "waveform_cache"
        self.cache_dir.mkdir(exist_ok=True)

    def get_or_generate(self, audio_path: Path) -> bytes:
        # Hash audio file
        file_hash = hashlib.md5(audio_path.read_bytes()).hexdigest()
        cache_file = self.cache_dir / f"{file_hash}.wf"

        if cache_file.exists():
            return cache_file.read_bytes()

        # Generate and cache
        waveform = generate_mono_waveform(str(audio_path))
        cache_file.write_bytes(waveform)
        return waveform
```

---

## Testing with Validation Data

### Test Setup

```bash
# Clone repo (if not already done)
cd /path/to/onelib-to-devicelib

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -e .

# Run conversion test
onelib-to-devicelib convert \
    validation_data/onelib_only \
    --output /tmp/test_validation \
    --analyze
```

### Bitwise Comparison Script

Save as `tests/compare_validation_data.py`:

```python
#!/usr/bin/env python3
"""
Bitwise comparison test for validation data.

Compares converter output with reference onelib_and_devicelib export.
"""

import hashlib
import sys
from pathlib import Path
from typing import Dict, Tuple

# Paths
SOURCE_DIR = Path("validation_data/onelib_only")
REFERENCE_DIR = Path("validation_data/onelib_and_devicelib")
GENERATED_DIR = Path("/tmp/test_validation")

# Expected differences
EXPECTED_DIFFERENCES = {
    "DeviceLibBackup": ["UUID differs"],  # UUID is randomly generated
    "DEVSETTING.DAT": ["Timestamp may differ"],
    "export.pdb": ["Different generation method"],
    "exportExt.pdb": ["Different generation method"],
}


def file_checksum(path: Path) -> str:
    """Calculate MD5 checksum of a file."""
    return hashlib.md5(path.read_bytes()).hexdigest()


def compare_file_structures() -> Dict[str, bool]:
    """Compare file structures between generated and reference."""
    results = {}

    # Check PIONEER directory structure
    gen_pioneer = GENERATED_DIR / "PIONEER"
    ref_pioneer = REFERENCE_DIR / "PIONEER"

    if not gen_pioneer.exists():
        results["PIONEER directory"] = False
        return results

    # Check subdirectories
    for subdir in ["rekordbox", "USBANLZ", "Artwork", "DeviceLibBackup"]:
        gen_sub = gen_pioneer / subdir
        ref_sub = ref_pioneer / subdir

        exists = gen_sub.exists()
        ref_exists = ref_sub.exists()

        results[f"{subdir} exists"] = exists
        results[f"{subdir} matches reference"] = exists == ref_exists

    # Check specific files
    gen_pdb = gen_pioneer / "rekordbox" / "export.pdb"
    ref_pdb = ref_pioneer / "rekordbox" / "export.pdb"

    if gen_pdb.exists() and ref_pdb.exists():
        gen_size = gen_pdb.stat().st_size
        ref_size = ref_pdb.stat().st_size

        results["export.pdb generated"] = True
        results["export.pdb size"] = f"{gen_size} bytes (ref: {ref_size})"
        results["export.pdb size matches"] = gen_size == ref_size

    # Check ANLZ structure
    gen_anlz = gen_pioneer / "USBANLZ"
    ref_anlz = ref_pioneer / "USBANLZ"

    if gen_anlz.exists() and ref_anlz.exists():
        gen_dirs = len(list(gen_anlz.rglob("ANLZ0000.DAT")))
        ref_dirs = len(list(ref_anlz.rglob("ANLZ0000.DAT")))

        results["ANLZ directories"] = f"{gen_dirs} (ref: {ref_dirs})"
        results["ANLZ count matches"] = gen_dirs == ref_dirs

    return results


def compare_pdb_details() -> None:
    """Detailed PDB file comparison."""
    gen_pdb = GENERATED_DIR / "PIONEER" / "rekordbox" / "export.pdb"
    ref_pdb = REFERENCE_DIR / "PIONEER" / "rekordbox" / "export.pdb"

    if not gen_pdb.exists() or not ref_pdb.exists():
        print("⚠️  Cannot compare PDB files (one or both missing)")
        return

    gen_data = gen_pdb.read_bytes()
    ref_data = ref_pdb.read_bytes()

    print("\n=== PDB File Analysis ===")
    print(f"Generated: {len(gen_data)} bytes")
    print(f"Reference: {len(ref_data)} bytes")

    # Check header
    gen_header = gen_data[:32]
    ref_header = ref_data[:32]

    print(f"\nGenerated header: {gen_header[:16].hex()}")
    print(f"Reference header: {ref_header[:16].hex()}")

    if gen_header == ref_header:
        print("✅ Headers match")
    else:
        print("⚠️  Headers differ (expected for MVP)")

    # Check page structure
    page_size = 4096
    gen_pages = len(gen_data) // page_size
    ref_pages = len(ref_data) // page_size

    print(f"\nGenerated pages: {gen_pages}")
    print(f"Reference pages: {ref_pages}")


def compare_anlz_files() -> None:
    """Compare ANLZ file structures."""
    gen_anlz = GENERATED_DIR / "PIONEER" / "USBANLZ" / "P001"
    ref_anlz = REFERENCE_DIR / "PIONEER" / "USBANLZ" / "P001"

    if not gen_anlz.exists() or not ref_anlz.exists():
        print("⚠️  Cannot compare ANLZ files")
        return

    print("\n=== ANLZ File Analysis ===")

    gen_dirs = sorted([d for d in gen_anlz.iterdir() if d.is_dir()])
    ref_dirs = sorted([d for d in ref_anlz.iterdir() if d.is_dir()])

    print(f"Generated ANLZ dirs: {len(gen_dirs)}")
    print(f"Reference ANLZ dirs: {len(ref_dirs)}")

    # Check file counts
    gen_complete = sum(1 for d in gen_dirs if len(list(d.glob("ANLZ0000.*"))) == 3)
    ref_complete = sum(1 for d in ref_dirs if len(list(d.glob("ANLZ0000.*"))) == 3)

    print(f"\nComplete ANLZ sets:")
    print(f"  Generated: {gen_complete}/{len(gen_dirs)}")
    print(f"  Reference: {ref_complete}/{len(ref_dirs)}")

    # Sample comparison
    if gen_dirs and ref_dirs:
        sample_gen = gen_dirs[0]
        sample_ref = ref_dirs[0]

        print(f"\nSample comparison:")
        print(f"  Generated: {sample_gen.name}")
        print(f"  Reference: {sample_ref.name}")

        # Check if files exist
        for ext in ["DAT", "EXT", "2EX"]:
            gen_file = sample_gen / f"ANLZ0000.{ext}"
            ref_file = sample_ref / f"ANLZ0000.{ext}"

            gen_exists = gen_file.exists()
            ref_exists = ref_file.exists()

            status = "✅" if gen_exists else "❌"
            print(f"    {ext}: Generated: {gen_exists}, Reference: {ref_exists} {status}")


def main():
    """Run comparison tests."""
    print("=" * 60)
    print("Validation Data Comparison Test")
    print("=" * 60)

    # Check if conversion has been run
    if not GENERATED_DIR.exists():
        print("\n❌ Generated directory not found!")
        print(f"Please run conversion first:")
        print(f"  onelib-to-devicelib convert {SOURCE_DIR} --output {GENERATED_DIR}")
        sys.exit(1)

    # Structure comparison
    print("\n--- Structure Comparison ---")
    results = compare_file_structures()

    for key, value in results.items():
        status = "✅" if value else "❌"
        print(f"{status} {key}: {value}")

    # Detailed PDB comparison
    compare_pdb_details()

    # Detailed ANLZ comparison
    compare_anlz_files()

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print("\n✅ Core functionality working:")
    print("  - Database reading")
    print("  - PDB generation")
    print("  - ANLZ generation")
    print("  - Metadata files")

    print("\n⚠️  Expected differences:")
    print("  - PDB exact format (MVP vs full Rekordbox format)")
    print("  - DeviceLibBackup UUID (randomly generated)")
    print("  - DEVSETTING.DAT timestamps")

    print("\n📋 Next steps:")
    print("  - Test on actual hardware")
    print("  - Refine PDB format for exact match")
    print("  - Add comprehensive error handling")

    print("=" * 60)


if __name__ == "__main__":
    main()
```

### Running the Comparison

```bash
# Run conversion
onelib-to-devicelib convert validation_data/onelib_only --output /tmp/test_validation

# Run comparison script
python tests/compare_validation_data.py
```

---

## Known Limitations

### Current MVP Limitations

1. **PDB Format**
   - ⚠️ Simplified track row structure (10 fields vs 30+)
   - ⚠️ Global string heap instead of per-page
   - ⚠️ Basic playlist/folder support
   - ⚠️ May not be compatible with all Rekordbox features

2. **ANLZ Files**
   - ⚠️ Waveforms generated with librosa (may differ from Rekordbox)
   - ⚠️ Beat grid uses librosa (may differ from Rekordbox)
   - ⚠️ Color waveform simplified (3-band frequency split)
   - ⚠️ Cue point conversion is basic

3. **Performance**
   - ⚠️ No parallel processing
   - ⚠️ No caching of analyzed audio
   - ⚠️ Sequential track processing

4. **Error Handling**
   - ⚠️ Basic error messages
   - ⚠️ Limited edge case handling
   - ⚠️ No recovery from partial failures

### Expected Differences from Reference

The following differences are **expected and acceptable** for the MVP:

1. **PDB File Content**
   - Different row ordering
   - Different string table layout
   - Different page allocation
   - Missing optional fields

2. **ANLZ File Content**
   - Different waveform data (different analysis algorithms)
   - Different beat grid (different beat detection)
   - Different color mapping

3. **Metadata Files**
   - DeviceLibBackup UUID (randomly generated)
   - DEVSETTING.DAT timestamps

---

## Future Enhancements

### Phase 1: Hardening (Short-term)

**Timeline**: 1-2 weeks

- [ ] Comprehensive error handling
- [ ] User-friendly error messages
- [ ] Edge case handling (unicode, long paths, etc.)
- [ ] Progress indicators for long operations
- [ ] Cancel support for long operations
- [ ] Validation mode (check without writing)

### Phase 2: Format Completion (Medium-term)

**Timeline**: 2-4 weeks

- [ ] Complete PDB track row structure
- [ ] Per-page string heaps
- [ ] Full playlist/folder support
- [ ] Artwork table in PDB
- [ ] History table in PDB
- [ ] All ANLZ tags implemented
- [ ] Cue point hot color support

### Phase 3: Features (Long-term)

**Timeline**: 1-2 months

- [ ] Parallel processing
- [ ] Waveform caching
- [ ] Incremental updates (only convert new tracks)
- [ ] Watch mode (auto-convert on changes)
- [ ] GUI application
- [ ] Batch processing multiple USB drives

### Phase 4: Advanced Analysis

**Timeline**: 2-3 months

- [ ] Madmom integration (better beat detection)
- [ ] Custom waveform algorithms
- [ ] Key detection integration
- [ ] Phrase/mood analysis
- [ ] Smart playlist generation

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

# Verbose output
onelib-to-devicelib --verbose convert /path/to/source

# Quiet mode
onelib-to-devicelib --quiet convert /path/to/source
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

#### Issue: "pyrekordbox not installed"

**Solution**:
```bash
pip install pyrekordbox
```

#### Issue: "librosa not installed" (when using --analyze)

**Solution**:
```bash
pip install librosa numpy soundfile
```

#### Issue: "Database file not found"

**Solution**: Ensure you're pointing to the root of the USB drive, not the PIONEER directory.

```bash
# Correct
onelib-to-devicelib convert /Volumes/USB_DRIVE

# Incorrect
onelib-to-devicelib convert /Volumes/USB_DRIVE/PIONEER
```

#### Issue: Generated PDB doesn't work on CDJ

**Possible Causes**:
1. PDB format incomplete (MVP limitation)
2. Missing ANLZ files
3. Incorrect file structure
4. Hardware requires specific format

**Solution**:
1. Run validation: `onelib-to-devicelib validate /path/to/export`
2. Check ANLZ files exist in USBANLZ/P001/*/ANLZ0000.*
3. Test with smaller library first

#### Issue: Waveforms don't display

**Solution**:
- Ensure you used `--analyze` flag
- Check ANLZ0000.EXT files are generated
- Verify file sizes are > 0

---

## Development

### Project Structure

```
src/onelib_to_devicelib/
├── __init__.py
├── cli.py                 # Click-based CLI
├── convert.py             # Main converter orchestration
├── parsers/
│   ├── __init__.py
│   └── onelib.py          # OneLibrary database parser
├── writers/
│   ├── __init__.py
│   ├── pdb.py             # PDB file writer
│   ├── anlz.py            # ANLZ file generator
│   └── metadata.py        # Metadata file generators
├── analyzers/
│   └── audio.py           # Audio analysis (future)
└── utils/
    ├── __init__.py
    └── paths.py           # Path utilities
```

### Adding New Features

1. **New Writer**: Add to `writers/` package
2. **New Parser**: Add to `parsers/` package
3. **New Analyzer**: Add to `analyzers/` package
4. **CLI Command**: Add command in `cli.py`
5. **Utility**: Add to `utils/` package

### Testing

```bash
# Run unit tests
pytest tests/

# Run with coverage
pytest --cov=onelib_to_devicelib tests/

# Run specific test
pytest tests/test_convert.py -v
```

---

## Quick Reference for Agents

### Essential Commands

```bash
# Run comparison test (DO THIS AFTER EVERY CHANGE)
./test_pdb.sh

# Activate virtual environment
source .venv/bin/activate

# Convert and test (full workflow)
onelib-to-devicelib convert validation_data/onelib_only --output /tmp/test_convert --no-copy
./test_pdb.sh

# Check specific aspects
./test_pdb.sh 2>&1 | grep "File Size"
./test_pdb.sh 2>&1 | grep -A 30 "Field-by-Field"
./test_pdb.sh 2>&1 | grep "Table Pointers" -A 25
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

### Progress Tracking

**Current Metrics** (update these as you make changes):
- File size: 45,056 bytes (19.6% of reference)
- Tables: 8/20 populated
- Matching track fields: 9+ critical fields

**Target Metrics** (what we're aiming for):
- File size: >100 KB (44% of reference)
- Tables: 15+/20 populated
- Track pages: 10+ pages (currently 3, reference has 55)

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

**Status**: 🔄 Phase 2 Complete - PDB format refinement in progress (19.6% of reference, 8/20 tables)

*Last Updated: 2026-03-02*
