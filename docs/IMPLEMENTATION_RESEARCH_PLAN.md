# OneLib to DeviceLib - Implementation Research Plan

## Objective

Create a focused research plan for implementing **PDB file writer** and **ANLZ file generator** to complete the OneLib to DeviceLib converter.

## Current Status

✅ **COMPLETE**: OneLibrary database reader using pyrekordbox `DeviceLibraryPlus`
- Can read 33 tracks, 4 playlists, cues, loops from `exportLibrary.db`
- CLI fully functional with `info`, `validate`, and `convert` commands

⏳ **BLOCKED**: Need to implement:
1. **PDB Writer** - Generate `export.pdb` for legacy Device Library format
2. **ANLZ Generator** - Create `.DAT`, `.EXT`, `.2EX` analysis files

---

## Part 1: PDB File Writer Implementation Research

### Goal
Port PDB generation logic from REX (Go) to Python, using Deep-Symmetry Kaitai Struct definitions.

### Research Tasks

#### Task 1.1: Study REX Project PDB Implementation
**Priority**: HIGHEST - This is the only working open-source PDB generator

**GitHub**: https://github.com/kimtore/rex

**Specific Files to Examine**:
```
1. Main command/entry point:
   - cmd/rex/main.go
   - pkg/rex/export.go

2. PDB-specific packages (search for directories containing):
   - "pdb" or "PDB"
   - "export" or "device"
   - "writer" or "generator"

3. Look for files with these patterns:
   - *pdb*.go
   - *export*.go
   - *device*.go
   - *writer*.go
```

**What to Extract**:
1. **PDB Header Structure**:
   - Magic bytes
   - Version number
   - Page size
   - Table pointers

2. **Page Management Logic**:
   - How pages are allocated
   - Page size constants
   - Row allocation per page

3. **String Table Management**:
   - How strings are stored (UTF-16LE)
   - String deduplication logic
   - String ID allocation

4. **Row Structure**:
   - Track row format
   - Playlist row format
   - Folder row format
   - How variable-length data is handled

5. **File Writing Process**:
   - Order of operations
   - How indexes are built
   - Checksum/hash calculation

**Expected Output**: Code snippets showing PDB structure and writing logic

---

#### Task 1.2: Kaitai Struct Definition Analysis
**Priority**: HIGH - Provides machine-readable format specification

**Resource**: https://github.com/Deep-Symmetry/crate-digger/blob/master/src/main/kaitai/rekordbox_pdb.ksy

**What to Extract**:
```yaml
# Key sections to find:
1. File header structure
2. Page structure definition
3. Row structure (for each table type)
4. String storage format
5. Index structure
```

**Specific Questions**:
- What is the exact byte layout of the PDB header?
- How are rows organized within pages?
- What is the maximum row size?
- How are variable-length fields handled?

**Expected Output**: Complete field-by-field breakdown of PDB format

---

#### Task 1.3: rekordcrate Rust Implementation
**Priority**: MEDIUM - Alternative reference implementation

**GitHub**: https://github.com/Holzhaus/rekordcrate

**Specific Files**:
```
- rekordcrate/src/pdb/mod.rs
- rekordcrate/src/pdb/*.rs (all files in pdb directory)
```

**What to Extract**:
- Rust structs that map to PDB format
- Serialization logic
- Constants for page sizes, limits, etc.

**Expected Output**: Understanding of PDB format from a different language perspective

---

#### Task 1.4: Working PDB File Analysis
**Priority**: MEDIUM - Reverse engineer from actual file

**Task**: Use validation data to analyze working PDB file

**Files**:
```
validation_data/onelib_and_devicelib/PIONEER/rekordbox/export.pdb
```

**Research Steps**:
1. Use hexdump to examine file structure:
   ```bash
   xxd validation_data/onelib_and_devicelib/PIONEER/rekordbox/export.pdb | head -100
   ```

2. Parse with rekordcrate to verify structure:
   - Clone rekordcrate
   - Use it to read the validation PDB file
   - Document the structure

**Expected Output**: Hex dump analysis showing:
- Header bytes and their meaning
- Page boundaries
- Row data examples
- String table examples

---

#### Task 1.5: Python PDB Writer Implementation Strategy
**Priority**: HIGH - Determine implementation approach

**Research Questions**:
1. Should we use Kaitai Struct Python runtime for writing?
2. Or implement from scratch using `struct` module?
3. What's the minimum viable PDB we can generate?

**Options to Evaluate**:

**Option A: Kaitai Struct Python Runtime**
- Pros: Format definition already exists
- Cons: May not support writing, only reading
- Research: `kaitaistruct` Python package capabilities

**Option B: Pure Python Implementation**
- Pros: Full control, no dependencies
- Cons: More work to implement
- Research: Python `struct` module for binary packing

**Option C: Hybrid Approach**
- Use Python `ctypes` to define C-like structures
- Or use `construct` library (not Kaitai)
- Research: Python binary format libraries

**Expected Output**: Recommended implementation approach with justification

---

### Search Queries for Part 1

```
# REX project structure
"kimtore/rex" PDB writer golang
github.com/kimtore/rex export pdb
"rex" golang rekordbox pdb

# Kaitai Struct
"kaitai struct" rekordbox_pdb.ksy explanation
python kaitaistruct write file
kaitai struct python runtime write

# Python PDB implementations
python rekordbox PDB writer
"export.pdb" python generate
rekordbox PDB binary format python

# rekordcrate
rekordcrate PDB documentation
"rekordcrate" rust PDB format

# General format questions
rekordbox PDB file format specification
"PIONEER" PDB magic bytes
DeviceSQL format rekordbox
```

---

## Part 2: ANLZ File Generator Implementation Research

### Goal
Implement ANLZ file writer (`.DAT`, `.EXT`, `.2EX`) using librosa for audio analysis.

### Research Tasks

#### Task 2.1: ANLZ Format Deep Dive
**Priority**: HIGHEST - Need exact format specifications

**Primary Resource**: https://djl-analysis.deepsymmetry.org/rekordbox-export-analysis/anlz.html

**Kaitai Struct**: https://github.com/Deep-Symmetry/crate-digger/blob/master/src/main/kaitai/rekordbox_anlz.ksy

**What to Extract for Each File Type**:

**ANLZ0000.DAT (Path & Metadata)**:
- PMAI header format
- PPTH tag structure
- Path encoding (UTF-16LE details)
- Other required tags

**ANLZ0000.EXT (Waveform)**:
- PMAI header
- PWV3 tag (mono waveform)
- Waveform data encoding:
  - Sample resolution (bits per sample)
  - Number of samples for full track
  - Compression method (if any)

**ANLZ0000.2EX (Extended)**:
- PMAI header
- PWV5/PWV6 tags (color waveform)
- PPOS tag (beat grid)
- PCOB tag (cue points)
- Data format for each tag

**Expected Output**: Complete byte-level format for all three files

---

#### Task 2.2: pyrekordbox ANLZ Reader Study
**Priority**: HIGH - Understand format by reverse engineering

**Documentation**: https://pyrekordbox.readthedocs.io/en/latest/formats/anlz.html

**Source Code**: Examine pyrekordbox's ANLZ parsing code

**Research Steps**:
1. Check if pyrekordbox can write ANLZ files
2. Study how it reads each tag type
3. Extract data structures used for parsing

**Python Code to Test**:
```python
from pyrekordbox.anlz import read_anlz_file

# Read existing ANLZ files
anlz_dat = read_anlz_file('path/to/ANLZ0000.DAT')
anlz_ext = read_anlz_file('path/to/ANLZ0000.EXT')
anlz_2ex = read_anlz_file('path/to/ANLZ0000.2EX')

# Inspect structure
print(dir(anlz_dat))
# Document attributes and their types
```

**Expected Output**: Python data structures representing ANLZ format

---

#### Task 2.3: Waveform Generation with librosa
**Priority**: HIGH - Core functionality

**Research**: How to generate Rekordbox-compatible waveforms

**Tasks**:
1. **Mono Waveform (PWV3)**:
   - librosa audio loading
   - RMS energy calculation
   - Downsampling to ~400 samples
   - Normalization to 0-255 range

2. **Color Waveform (PWV5/PWV6)**:
   - Spectral analysis for frequency coloring
   - RGB value calculation
   - Higher resolution sampling

**Research Questions**:
- What sampling rate should we use?
- What window size for RMS calculation?
- How to map frequencies to RGB colors?
- What's the exact resolution (samples per pixel)?

**Librosa Documentation**:
- https://librosa.org/doc/main/generated/librosa.load.html
- https://librosa.org/doc/main/generated/librosa.feature.rms.html
- https://librosa.org/doc/main/generated/librosa.stft.html

**Expected Output**: Python functions for generating waveform data

---

#### Task 2.4: Beat Grid and BPM Detection
**Priority**: MEDIUM - Important for sync features

**Research**: Beat detection algorithms that match Rekordbox

**Options**:
1. **librosa.beat.beat_track**:
   - Basic beat tracking
   - Returns BPM and beat frames

2. **madmom** (more advanced):
   - RNN-based beat detection
   - Downbeat detection
   - State-of-the-art accuracy

**Research**:
```python
import librosa

# Load audio
y, sr = librosa.load('track.mp3', sr=44100)

# Get tempo and beats
tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
beat_times = librosa.frames_to_time(beats, sr=sr)

# What format does Rekordbox expect?
# Research: Beat grid entry structure from Deep-Symmetry
```

**Expected Output**: Beat grid generation with proper timing precision

---

#### Task 2.5: Cue Point Conversion
**Priority**: LOW - Straightforward mapping

**Task**: Convert OneLibrary cues to ANLZ PCOB format

**Research**:
- OneLibrary cue format (already have from database)
- PCOB tag structure from Deep-Symmetry
- Hot cue vs memory cue vs loop handling

**Expected Output**: Conversion function for cue points

---

### Search Queries for Part 2

```
# ANLZ format
rekordbox ANLZ0000.DAT format
rekordbox ANLZ0000.EXT waveform
rekordbox ANLZ0000.2EX extended
PMAI tag format rekordbox

# Waveform generation
librosa RMS energy waveform
librosa waveform downsampling
audio waveform visualization python
rekordbox waveform algorithm

# Beat detection
librosa beat tracking BPM
madmom beat detection python
rekordbox beat grid format
beat detection milliseconds precision

# pyrekordbox ANLZ
pyrekordbox read_anlz_file example
pyrekordbox ANLZ write
```

---

## Part 3: Integration and Testing Research

### Goal
Ensure generated files work with actual hardware.

### Research Tasks

#### Task 3.1: Hardware Compatibility Testing
**Priority**: MEDIUM - Validation approach

**Research**: How to test without CDJ hardware

**Options**:
1. Use rekordcrate to validate generated files
2. Check for PDB/ANLZ validation tools
3. Document what needs hardware testing

**Expected Output**: Testing strategy and validation approach

---

#### Task 3.2: Minimum Viable Product Definition
**Priority**: HIGH - Focus implementation

**Research**: What's the minimum needed for basic playback?

**Questions**:
- Can we skip color waveforms initially?
- Are beat grids required?
- What subset of PDB tables is essential?

**Expected Output**: MVP feature list and implementation order

---

#### Task 3.3: Error Handling and Edge Cases
**Priority**: LOW - Can address during implementation

**Research**:
- Large file handling
- Corrupt data handling
- Unicode path handling
- File size limits

**Expected Output**: Edge case documentation

---

## Deliverables Expected from Research Agent

### For PDB Writer (Part 1):

1. **REX Code Analysis**:
   - Relevant code snippets from REX showing PDB generation
   - Explanation of Go code logic
   - Key functions and their purposes

2. **Format Specification**:
   - Byte-by-byte breakdown of PDB header
   - Page structure details
   - Row structure for tracks/playlists
   - String table format

3. **Implementation Guide**:
   - Recommended Python approach
   - Required Python libraries
   - Step-by-step implementation plan
   - Code skeleton/template

### For ANLZ Generator (Part 2):

1. **Format Specifications**:
   - ANLZ0000.DAT byte format
   - ANLZ0000.EXT byte format
   - ANLZ0000.2EX byte format
   - All tag structures (PPTH, PWV3-6, PCOB, PPOS)

2. **Audio Analysis Code**:
   - librosa code for waveform generation
   - Beat detection implementation
   - RGB color calculation for waveforms

3. **Implementation Guide**:
   - Python functions for each file type
   - Integration with existing parser
   - Testing approach

### For Integration (Part 3):

1. **MVP Definition**:
   - What to implement first
   - What can be skipped initially
   - Testing strategy

2. **Code Examples**:
   - Working Python snippets where possible
   - Integration points with existing code

---

## Research Execution Instructions

### Phase 1: Code Analysis (60 minutes)
1. Clone and search REX repository for PDB-related code
2. Read rekordbox_pdb.ksy Kaitai Struct definition
3. Examine ANLZ format documentation from Deep-Symmetry
4. Test pyrekordbox ANLZ reading on validation data

### Phase 2: Format Documentation (30 minutes)
1. Document PDB header structure from hex dump
2. Document ANLZ tag structures from validation files
3. Create field-by-field specification documents

### Phase 3: Implementation Planning (30 minutes)
1. Determine best Python implementation approach
2. Create skeleton code structures
3. Define MVP feature set

### Phase 4: Code Examples (60 minutes)
1. Extract and adapt REX Go code to Python pseudocode
2. Create librosa examples for waveform generation
3. Write example beat detection code

---

## Success Criteria

Research is complete when we have:

✅ **PDB Writer**:
- Complete PDB format specification
- Understanding of page allocation and row structure
- Python implementation approach selected
- Code skeleton/structure defined

✅ **ANLZ Generator**:
- Complete ANLZ format for all three file types
- Waveform generation algorithm documented
- Beat detection approach selected
- Python functions for audio analysis

✅ **Integration**:
- Clear MVP feature list
- Implementation order defined
- Testing strategy documented

---

## Quick Copy-Paste Search Terms

For immediate use in research agents:

```
github.com/kimtore/rex golang PDB export
Deep-Symmetry rekordbox_pdb.ksy format
rekordbox ANLZ0000 tag structure PPTH PWV3 PWV5 PCOB PPOS
librosa beat tracking BPM milliseconds
python struct module binary file write
kaitaistruct python write capability
rekordbox waveform RGB color frequency
DeviceSQL PDB format specification
```

---

## Notes for Research Agent

1. **Focus on working code**: REX project is gold standard - extract heavily from it
2. **Validation data is available**: Can analyze actual working PDB/ANLZ files
3. **Python-first**: We need Python implementations, not just format specs
4. **MVP mindset**: Prioritize core functionality over edge cases
5. **Code examples are better than descriptions**: Provide actual code snippets

---

**Research Goal**: Provide enough information to implement PDB writer and ANLZ generator in Python, with working code examples and clear specifications.
