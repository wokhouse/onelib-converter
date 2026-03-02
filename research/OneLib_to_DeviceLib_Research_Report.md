# OneLib to DeviceLib Converter - Online Research Report

**Technical Analysis for DJ Library Format Conversion**

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Key Findings Summary](#2-key-findings-summary)
3. [Database Format Research](#3-database-format-research)
4. [ANLZ Analysis Files Research](#4-anlz-analysis-files-research)
5. [Open Source Projects Analysis](#5-open-source-projects-analysis)
6. [Audio Analysis for Waveform Generation](#6-audio-analysis-for-waveform-generation)
7. [Additional Files Analysis](#7-additional-files-analysis)
8. [Implementation Strategy](#8-implementation-strategy)
9. [Conclusions and Next Steps](#9-conclusions-and-next-steps)
10. [References](#10-references)

---

## 1. Executive Summary

This research report provides comprehensive technical findings for developing a CLI tool to convert OneLibrary exported libraries from djay Pro into the legacy Device Library format compatible with Pioneer DJ hardware that does not support OneLibrary (e.g., CDJ-2000NXS, CDJ-900NXS). The research covers file format specifications, encryption mechanisms, existing open-source tools, and implementation strategies derived from extensive online research.

**A critical finding from this research is that OneLibrary is only compatible with CDJ-3000, CDJ-3000X, OPUS-QUAD, XDJ-AZ, and OMNIS-DUO devices.** Older hardware like CDJ-2000NXS and CDJ-900NXS require the traditional Device Library format, which includes `export.pdb` and ANLZ analysis files. This confirms the necessity of the proposed converter tool.

---

## 2. Key Findings Summary

### 2.1 Hardware Compatibility Matrix

| Device Model | OneLibrary | Device Library |
|-------------|:----------:|:--------------:|
| CDJ-3000X | ✅ Yes | ✅ Yes |
| CDJ-3000 | ✅ Yes | ✅ Yes |
| OPUS-QUAD | ✅ Yes | ✅ Yes |
| XDJ-AZ | ✅ Yes | ✅ Yes |
| OMNIS-DUO | ✅ Yes | ✅ Yes |
| **CDJ-2000NXS** | ❌ **No** | ✅ **Required** |
| **CDJ-900NXS** | ❌ **No** | ✅ **Required** |

> **Source**: [Pioneer DJ Support](https://support.pioneerdj.com/hc/en-us/articles/51298635657881-What-hardware-supports-OneLibrary)

### 2.2 Critical Technical Discoveries

- **Universal Encryption Key**: The Device Library Plus (`exportLibrary.db`) uses SQLCipher encryption with a **UNIVERSAL KEY** that is the same across all devices and exports. This means we can read any Device Library Plus file once we obtain this key.

- **pyrekordbox Support**: The pyrekordbox library (v0.4.5.dev5) already has built-in support for reading encrypted Rekordbox databases and can handle both `master.db` and `exportLibrary.db` files.

- **PDB Format Reverse-Engineered**: The legacy `export.pdb` file format has been fully reverse-engineered by the Deep-Symmetry project and documented with Kaitai Struct definitions, making it possible to write PDB files programmatically.

- **ANLZ Files Documented**: The ANLZ analysis files (`.DAT`, `.EXT`, `.2EX`) have been extensively documented, including beat grids, waveforms, cue points, and song structure information.

- **REX Project Proof**: The REX project (kimtore/rex) demonstrates that it is possible to generate valid PDB files from other DJ software libraries (Mixxx), providing a reference implementation for PDB generation.

---

## 3. Database Format Research

### 3.1 exportLibrary.db (Device Library Plus)

The `exportLibrary.db` file is the newer Device Library Plus format introduced with Rekordbox 6.8.1. It is a SQLite database encrypted using SQLCipher version 4. Unlike the main Rekordbox `master.db` which uses machine-specific keys, the Device Library Plus encryption key appears to be universal across all exports, making it significantly easier to work with.

#### Key Technical Details

| Property | Value |
|----------|-------|
| Encryption | SQLCipher 4 with universal key (not machine-dependent) |
| Schema | Similar to main Rekordbox database with subset of tables |
| Location | `PIONEER/rekordbox/exportLibrary.db` |
| Typical Size | ~151KB |

#### Resources for Working with Device Library Plus

- **pyrekordbox Documentation**: [pyrekordbox.readthedocs.io/en/latest/formats/devicelib_plus.html](https://pyrekordbox.readthedocs.io/en/latest/formats/devicelib_plus.html)
- **Encryption Key Research**: [github.com/liamcottle/pioneer-rekordbox-database-encryption](https://github.com/liamcottle/pioneer-rekordbox-database-encryption)
- **Lexicon DJ Analysis**: [lexicondj.com/blog/everything-you-need-to-know-about-device-library-plus](https://www.lexicondj.com/blog/everything-you-need-to-know-about-device-library-plus-and-more)

### 3.2 export.pdb and exportExt.pdb (Legacy Device Library)

The `export.pdb` file is the core database for the legacy Device Library format used by older Pioneer hardware. This binary file format has been extensively reverse-engineered by the community. The `exportExt.pdb` file contains extended data including tag-track relationships and additional metadata not found in the main PDB file.

#### PDB File Structure

- Contains tables for tracks, playlists, folders, artwork references, and history
- Uses DeviceSQL format with specific row and page structures
- String data stored separately from row data with index references
- File has been fully documented using Kaitai Struct definitions

#### Key Resources

- **Deep-Symmetry PDB Analysis**: [djl-analysis.deepsymmetry.org/rekordbox-export-analysis/exports.html](https://djl-analysis.deepsymmetry.org/rekordbox-export-analysis/exports.html)
- **Henry Betts Decoding**: [github.com/henrybetts/Rekordbox-Decoding](https://github.com/henrybetts/Rekordbox-Decoding)
- **rekordcrate Rust Library**: [github.com/Holzhaus/rekordcrate](https://github.com/Holzhaus/rekordcrate)
- **crate-digger Java Library**: [github.com/Deep-Symmetry/crate-digger](https://github.com/Deep-Symmetry/crate-digger)

---

## 4. ANLZ Analysis Files Research

### 4.1 File Overview

The ANLZ files contain all analysis data for each track including waveforms, beat grids, cue points, loops, and song structure information. Each track has three associated files with the same base name (`ANLZ0000`) but different extensions.

### 4.2 File Format Specifications

| Extension | Content Type | Description |
|:---------:|--------------|-------------|
| `.DAT` | Path & Metadata | Track path, file info, basic metadata |
| `.EXT` | Waveform Data | Raw waveform samples, mono waveform display |
| `.2EX` | Extended Waveform | Color waveform, high-res data, beat grid, cues |

### 4.3 Directory Structure

```
PIONEER/USBANLZ/P###/XXXXXXXX/ANLZ0000.DAT
PIONEER/USBANLZ/P###/XXXXXXXX/ANLZ0000.EXT
PIONEER/USBANLZ/P###/XXXXXXXX/ANLZ0000.2EX
```

- `P###` - Playlist/device identifier (e.g., P001, P002)
- `XXXXXXXX` - 8-character hash derived from track path

### 4.4 Data Structures Within ANLZ Files

The ANLZ files use a **PMAI** header structure and contain various tagged sections:

| Tag | Name | Description |
|-----|------|-------------|
| PPTH | Path Information | Track file path (UTF-16LE encoded) |
| PWV3 | Mono Waveform | Standard waveform display data |
| PWV4 | Color Waveform Preview | Compact color waveform |
| PWV5 | Extended Color Waveform | Full color waveform data |
| PWV6 | High-Res Color Waveform | CDJ-3000 specific high-resolution waveform |
| PCOB | Cue Points | Hot cues, memory cues, loops |
| PPOS | Beat Grid Positions | Beat timing information |
| PSSI | Song Structure Info | Phrase/mood analysis |

### 4.5 Key Resources for ANLZ Files

- **pyrekordbox ANLZ Format**: [pyrekordbox.readthedocs.io/en/latest/formats/anlz.html](https://pyrekordbox.readthedocs.io/en/latest/formats/anlz.html)
- **Deep-Symmetry Analysis**: [djl-analysis.deepsymmetry.org/rekordbox-export-analysis/anlz.html](https://djl-analysis.deepsymmetry.org/rekordbox-export-analysis/anlz.html)
- **Analysis PDF**: [deepsymmetry.org/cratedigger/Analysis.pdf](https://deepsymmetry.org/cratedigger/Analysis.pdf)

---

## 5. Open Source Projects Analysis

### 5.1 pyrekordbox (Python)

**GitHub**: [github.com/dylanljones/pyrekordbox](https://github.com/dylanljones/pyrekordbox)

Pyrekordbox is the most comprehensive Python library for working with Rekordbox data. Version 0.4.5.dev5 is already installed in the project environment.

#### Capabilities

- ✅ Read encrypted `master.db` and `exportLibrary.db` databases
- ✅ Parse and create ANLZ analysis files
- ✅ Handle Rekordbox XML format
- ✅ Access My-Setting files
- ✅ Device Library Plus support

#### Installation

```bash
pip install pyrekordbox
# or for development version
pip install pyrekordbox==0.4.5.dev5
```

### 5.2 crate-digger (Java)

**GitHub**: [github.com/Deep-Symmetry/crate-digger](https://github.com/Deep-Symmetry/crate-digger)

Crate-digger is a Java library developed by Deep-Symmetry that provides comprehensive parsing capabilities for Rekordbox exports. It includes Kaitai Struct definitions for both PDB and ANLZ files.

#### Key Features

- Complete PDB file parsing with Kaitai Struct
- ANLZ file parsing (all three extensions)
- Well-documented with extensive Javadoc
- Tested with Rekordbox 5.x and 6.x formats

### 5.3 rekordcrate (Rust)

**GitHub**: [github.com/Holzhaus/rekordcrate](https://github.com/Holzhaus/rekordcrate)

Rekordcrate is a Rust library for parsing Pioneer device exports with a clean API for reading PDB files.

#### Documentation

- [rekordcrate PDB Documentation](https://holzhaus.github.io/rekordcrate/rekordcrate/pdb/index.html)
- [rekordcrate ANLZ Documentation](https://holzhaus.github.io/rekordcrate/rekordcrate/anlz/index.html)

### 5.4 REX - Rekordbox Exporter (Go)

**GitHub**: [github.com/kimtore/rex](https://github.com/kimtore/rex)

REX is particularly significant as it demonstrates **actual PDB file generation** from another DJ software (Mixxx). This proves that generating valid Device Library files programmatically is achievable.

#### What REX Does

```
Mixxx Library → REX → export.pdb (valid Rekordbox format)
```

This is the most relevant reference for our converter project!

### 5.5 rbox (Rust)

**crates.io**: [crates.io/crates/rbox](https://crates.io/crates/rbox)

Rbox is a newer Rust library that supports both `master.db` and OneLibrary formats with SQLCipher support.

### 5.6 rekordbox-parser (JavaScript/TypeScript)

**GitHub**: [github.com/evanpurkhiser/rekordbox-parser](https://github.com/evanpurkhiser/rekordbox-parser)

A JavaScript/TypeScript library that provides a simple API for parsing Pioneer Rekordbox PDB and ANLZ files. Wraps around Kaitai Struct definitions.

---

## 6. Audio Analysis for Waveform Generation

To generate ANLZ analysis files from audio, several audio analysis libraries can be used for beat detection, tempo estimation, and waveform generation.

### 6.1 Recommended Libraries

#### librosa (Python)

**Documentation**: [librosa.org/doc](https://librosa.org/doc)

- Comprehensive audio analysis library for music information retrieval
- Beat tracking with time-varying tempo support
- Waveform generation and spectral analysis
- Well-documented with extensive examples

```python
import librosa

# Load audio file
y, sr = librosa.load('track.mp3')

# Get BPM
tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)

# Get beat times
beat_times = librosa.frames_to_time(beat_frames, sr=sr)
```

#### madmom (Python)

**GitHub**: [github.com/CPJKU/madmom](https://github.com/CPJKU/madmom)

- State-of-the-art algorithms for beat and downbeat detection
- Uses RNN-based approaches for high accuracy
- Superior tempo estimation compared to basic methods
- Published academic research backing the algorithms

```python
from madmom.features.beats import RNNBeatProcessor
from madmom.features.tempo import TempoEstimationProcessor

# Beat detection
beat_processor = RNNBeatProcessor()
beats = beat_processor('track.mp3')

# Tempo estimation
tempo_processor = TempoEstimationProcessor(fps=100)
tempo = tempo_processor(beats)
```

#### BeatNet (Python)

**GitHub**: [github.com/mjhydri/BeatNet](https://github.com/mjhydri/BeatNet)

- Real-time and offline joint beat, downbeat, tempo tracking
- Uses deep learning models for high accuracy
- Built on top of librosa and madmom

### 6.2 Comparison of Beat Detection Accuracy

Based on research from [biff.ai](https://biff.ai/a-rundown-of-open-source-beat-detection-models):

| Library | Accuracy | Speed | Best For |
|---------|----------|-------|----------|
| librosa | Good | Fast | Quick analysis, prototyping |
| madmom | Excellent | Medium | Production quality |
| BeatNet | Excellent | Slow | Maximum accuracy |

---

## 7. Additional Files Analysis

### 7.1 DEVSETTING.DAT

**Type**: Binary configuration file

**Hex Header**: `PIONEER DJ...rekordbox...7.2.9...`

**Purpose**: Device-specific settings for Rekordbox export including configuration for how the export should be interpreted by CDJ hardware.

**Research Status**: Partially documented; appears to contain version information and export settings.

### 7.2 djprofile.nxs

**Type**: Binary format

**Purpose**: DJ performance profile settings for CDJ/DJM settings. Stores user preferences that can be loaded onto compatible hardware.

**Research Status**: Format not fully documented but appears optional for basic playback.

### 7.3 DeviceLibBackup/rbDevLibBaInfo JSON

**Example Structure**:
```json
{
  "uuid": "292d308378264db180e8742ed81244e9",
  "info": []
}
```

**Purpose**: Device library backup information - UUID identifies the specific export.

**Reference**: [Rekordbox Device Library Backup Guide](https://cdn.rekordbox.com/files/20230711173001/rekordbox6.7.4_device_library_backup_guide_EN.pdf)

### 7.4 gcred.dat

**Type**: Binary file (66 bytes)

**Location**: `PIONEER/extracted/gcred.dat`

**Purpose**: Unknown - possibly credentials or authentication data. Further investigation needed.

### 7.5 Artwork Files

**Location**: `PIONEER/Artwork/`

**Naming Convention**:
- `a##.jpg` - Album artwork (full size)
- `b##.jpg` - Artwork variant (full size)
- `*_m.jpg` - Thumbnail variants (80x80 pixels)

**Requirements**:
- Format: JPEG only
- Maximum resolution: 800x800 pixels
- Thumbnails: 80x80 pixels for CDJ screen display

**Reference**: [Pioneer CDJ Album Art](https://www.blisshq.com/music-library-management-blog/2020/03/03/pioneer-cdj-album-art)

---

## 8. Implementation Strategy

### 8.1 Phase 1: Database Reader Implementation

The first phase should focus on reading the OneLibrary export data using pyrekordbox.

**Tasks**:
1. Implement OneLibrary reader using pyrekordbox
2. Extract track metadata, playlists, cues, and beat grids
3. Map OneLibrary data structures to Device Library equivalents
4. Validate data integrity and completeness

**Example Code**:
```python
from pyrekordbox import Rekordbox6Database

# Open OneLibrary export
db = Rekordbox6Database('/path/to/exportLibrary.db')

# Extract tracks
for track in db.get_content():
    print(f"Title: {track.Title}")
    print(f"Artist: {track.ArtistName}")
    print(f"BPM: {track.BPM}")
```

### 8.2 Phase 2: PDB File Generation

Generate the legacy `export.pdb` file using patterns from REX and rekordcrate.

**Tasks**:
1. Study REX project's PDB generation implementation
2. Implement PDB writer based on reverse-engineered format
3. Generate `export.pdb` with tracks, playlists, and folders
4. Test PDB validity with existing parsers

**Reference Implementation**:
- REX PDB Writer: [github.com/kimtore/rex](https://github.com/kimtore/rex)
- Kaitai Struct Definition: [github.com/Deep-Symmetry/crate-digger/blob/master/src/main/kaitai/rekordbox_pdb.ksy](https://github.com/Deep-Symmetry/crate-digger/blob/master/src/main/kaitai/rekordbox_pdb.ksy)

### 8.3 Phase 3: ANLZ File Generation

Create ANLZ analysis files from extracted or computed analysis data.

**Tasks**:
1. Implement ANLZ file writer based on documented format
2. Transform OneLibrary analysis data to ANLZ format
3. Optionally implement audio analysis for missing data
4. Generate proper directory structure (`P###/XXXXXXXX/`)

**Directory Structure**:
```
PIONEER/
└── USBANLZ/
    └── P001/
        └── abcd1234/
            ├── ANLZ0000.DAT
            ├── ANLZ0000.EXT
            └── ANLZ0000.2EX
```

### 8.4 Phase 4: Hardware Testing

Test on actual CDJ-2000NXS or CDJ-900NXS hardware.

**Tasks**:
1. Generate test exports with various track types
2. Test on actual hardware for compatibility
3. Verify all features (playback, waveforms, cues, beat sync)
4. Document any edge cases or issues

### 8.5 Development Workflow

```
┌─────────────────────┐
│   OneLibrary Export │
│  (exportLibrary.db) │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   pyrekordbox       │
│   Reader Module     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Data Transformer  │
│ (OneLib → DeviceLib)│
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
┌─────────┐ ┌─────────┐
│PDB Gen  │ │ANLZ Gen │
│ Module  │ │ Module  │
└────┬────┘ └────┬────┘
     │           │
     └─────┬─────┘
           ▼
┌─────────────────────┐
│   Device Library    │
│  (export.pdb + ANLZ)│
└─────────────────────┘
```

---

## 9. Conclusions and Next Steps

### 9.1 Feasibility Assessment

This research confirms that developing a OneLib to DeviceLib converter is **technically feasible**:

- ✅ Key file formats have been reverse-engineered and documented
- ✅ Working implementations exist for related functionality (REX, pyrekordbox)
- ✅ Audio analysis libraries available for waveform generation
- ✅ Community has successfully created similar tools

### 9.2 Immediate Action Items

1. **Set up development environment** with pyrekordbox and required audio analysis libraries
2. **Create proof-of-concept OneLibrary reader** to validate data extraction
3. **Study REX project implementation** in detail for PDB generation patterns
4. **Establish test corpus** with known-good exports for validation

### 9.3 Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Incomplete format documentation | Study multiple reference implementations |
| Undocumented hardware requirements | Extensive hardware testing |
| Edge cases in data conversion | Community beta testing |
| Legal considerations | Use clean-room implementation from specs |

### 9.4 Success Criteria

The CLI tool should be able to:

1. ✅ Read OneLibrary exported data
2. ✅ Generate all required Device Library files
3. ✅ Create a working export that CDJ-2000NXS can read
4. ✅ Preserve metadata (track info, cues, loops, playlists)
5. ⏳ Optionally generate waveforms/analysis data

---

## 10. References

### Primary Resources

1. **pyrekordbox Documentation** - [pyrekordbox.readthedocs.io](https://pyrekordbox.readthedocs.io)

2. **Deep-Symmetry Rekordbox Analysis** - [djl-analysis.deepsymmetry.org](https://djl-analysis.deepsymmetry.org)

3. **Pioneer Rekordbox Database Encryption** - [github.com/liamcottle/pioneer-rekordbox-database-encryption](https://github.com/liamcottle/pioneer-rekordbox-database-encryption)

4. **REX Rekordbox Exporter** - [github.com/kimtore/rex](https://github.com/kimtore/rex)

5. **rekordcrate Rust Library** - [github.com/Holzhaus/rekordcrate](https://github.com/Holzhaus/rekordcrate)

6. **crate-digger Java Library** - [github.com/Deep-Symmetry/crate-digger](https://github.com/Deep-Symmetry/crate-digger)

### Official Documentation

7. **Pioneer DJ OneLibrary Support** - [support.pioneerdj.com](https://support.pioneerdj.com/hc/en-us/articles/51298635657881-What-hardware-supports-OneLibrary)

8. **Rekordbox USB Export Guide** - [cdn.rekordbox.com/files/USB_export_guide_en.pdf](https://cdn.rekordbox.com/files/20251021171528/USB_export_guide_en_251007.pdf)

9. **Device Library Plus Guide** - [cdn.rekordbox.com/files/Device_Library_Plus_guide_EN.pdf](https://cdn.rekordbox.com/files/20231208144230/rekordbox6.8.1_Device_Library_Plus_guide_EN.pdf)

### Audio Analysis

10. **librosa Documentation** - [librosa.org/doc](https://librosa.org/doc)

11. **madmom GitHub** - [github.com/CPJKU/madmom](https://github.com/CPJKU/madmom)

12. **madmom Paper (arXiv)** - [arxiv.org/pdf/1605.07008](https://arxiv.org/pdf/1605.07008)

13. **BeatNet GitHub** - [github.com/mjhydri/BeatNet](https://github.com/mjhydri/BeatNet)

### Additional References

14. **Lexicon DJ Device Library Plus Guide** - [lexicondj.com](https://www.lexicondj.com/blog/everything-you-need-to-know-about-device-library-plus-and-more)

15. **Pioneer CDJ Album Art** - [blisshq.com](https://www.blisshq.com/music-library-management-blog/2020/03/03/pioneer-cdj-album-art)

16. **Henry Betts Rekordbox Decoding** - [github.com/henrybetts/Rekordbox-Decoding](https://github.com/henrybetts/Rekordbox-Decoding)

17. **rekordbox-parser (JavaScript)** - [github.com/evanpurkhiser/rekordbox-parser](https://github.com/evanpurkhiser/rekordbox-parser)

18. **rbox (Rust crate)** - [crates.io/crates/rbox](https://crates.io/crates/rbox)

---

*Report generated from online research conducted for the OneLib to DeviceLib Converter project.*
