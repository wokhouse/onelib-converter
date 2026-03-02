# OneLib to DeviceLib Converter - Online Research Guide

## Project Overview

**Goal**: Create a CLI tool to convert onelibrary exported libraries from DJ software (djay Pro) into onelib + devicelib format for compatibility with hardware that doesn't support onelib (e.g., CDJ-2000NXS, CDJ-900NXS).

**Problem**: Currently, djay users must import their library into Rekordbox and re-export to play on non-onelib compatible hardware. This is slow and tedious.

---

## Validation Data Analysis Summary

### Data Sets Compared
- `onelib_only/` - Contains only the onelib format export
- `onelib_and_devicelib/` - Contains both onelib AND devicelib format export

### Key Differences Tally

| Category | Count | Details |
|----------|-------|---------|
| Total unique files/dirs in combined | 245 | vs 186 in onelib_only |
| DeviceLibBackup directory | 1 | New directory containing device library backup |
| DEVSETTING.DAT | 1 | Device settings file |
| djprofile.nxs | 1 | DJ performance profile |
| extracted directory | 1 | Contains gcred.dat |
| Additional PDB files | 2 | export.pdb, exportExt.pdb |
| Additional artwork | ~57 | Thumbnail variants (_m.jpg files) |
| Modified ANLZ files | ~28 | Waveform/analysis data differs |

---

## File-By-File Analysis & Research Questions

### 1. `PIONEER/rekordbox/exportLibrary.db`
**Type**: Encrypted database (SQLCipher)
**Size**: ~151KB
**Purpose**: Main track library database containing metadata, playlists, cues, loops, etc.
**Status**: Present in both onelib_only and onelib_and_devicelib

**Research Topics**:
- [ ] SQLCipher encryption key extraction/derivation
- [ ] Database schema and table structure
- [ ] Existing tools that can read/write this format
- [ ] pyrekordbox library capabilities (already installed in .venv)

**Open Source References**:
- `pyrekordbox` (Python library, v0.4.5.dev5 installed)
- Look for: rekordbox database reverse engineering projects
- Search terms: "rekordbox exportLibrary.db decryption", "sqlcipher rekordbox key"

---

### 2. `PIONEER/rekordbox/export.pdb` (NEW in combined)
**Type**: Unknown binary format
**Size**: Unknown
**Purpose**: Likely contains additional playlist/database information for device compatibility

**Research Topics**:
- [ ] File format specification
- [ ] Relationship to exportLibrary.db
- [ ] Tools to read/write this format
- [ ] Is this required for device library or just for Rekordbox software?

**Open Source References**:
- Search: "rekordbox export.pdb format", "pdb file rekordbox", "pioneer pdb specification"

---

### 3. `PIONEER/rekordbox/exportExt.pdb` (NEW in combined)
**Type**: Unknown binary format
**Purpose**: Extended data - possibly track analysis, waveforms, or device-specific metadata

**Research Topics**:
- [ ] File format specification
- [ ] Difference between export.pdb and exportExt.pdb
- [ ] What data does this contain that exportLibrary.db doesn't?

**Open Source References**:
- Search: "rekordbox exportExt.pdb", "rekordbox extended database format"

---

### 4. `PIONEER/DeviceLibBackup/rbDevLibBaInfo_1391420378.json` (NEW in combined)
**Type**: JSON
**Content**:
```json
{
  "uuid": "292d308378264db180e8742ed81244e9",
  "info": []
}
```
**Purpose**: Device library backup information - UUID likely identifies the device/export

**Research Topics**:
- [ ] UUID generation algorithm
- [ ] What gets populated in the "info" array?
- [ ] Is this file format documented anywhere?
- [ ] Relationship to device pairing/registration

**Open Source References**:
- Search: "rbDevLibBaInfo format", "rekordbox device library backup json"
- Pioneer's XML/XSD specifications for device metadata

---

### 5. `PIONEER/DEVSETTING.DAT` (NEW in combined)
**Type**: Binary configuration file
**Hex header**: `PIONEER DJ...rekordbox...7.2.9...`
**Purpose**: Device-specific settings for rekordbox export

**Research Topics**:
- [ ] Full file format specification
- [ ] What settings are stored?
- [ ] Is this device-specific or universal?
- [ ] How to generate/modify programmatically?

**Open Source References**:
- Search: "DEVSETTING.DAT format", "rekordbox device settings file", "pioneer devsetting specification"

---

### 6. `PIONEER/djprofile.nxs` (NEW in combined)
**Type**: Binary format
**Purpose**: DJ performance profile settings (likely for CDJ/DJM settings)

**Research Topics**:
- [ ] NXS file format specification
- [ ] What DJ settings are stored?
- [ ] Is this required for playback or just preferences?

**Open Source References**:
- Search: "nxs file format pioneer", "djprofile.nxs specification", "NXS format reverse engineering"

---

### 7. `PIONEER/extracted/gcred.dat` (NEW in combined)
**Type**: Binary file
**Size**: 66 bytes
**Purpose**: Unknown - possibly credentials or authentication data

**Research Topics**:
- [ ] File format and purpose
- [ ] Is this required for device operation?
- [ ] Security/encryption implications

**Open Source References**:
- Search: "gcred.dat rekordbox", "rekordbox extracted credentials"

---

### 8. `PIONEER/Artwork/*.jpg` and `PIONEER/Artwork/*_m.jpg`
**Type**: JPEG images
**Naming**: `b##.jpg` and `a##.jpg` (album art), with `_m` variants (thumbnails)
**Purpose**: Album artwork display on CDJ screens
**Difference**: onelib_and_devicelib has additional `_m.jpg` thumbnail variants

**Research Topics**:
- [ ] Artwork file naming scheme (how are a## and b## assigned?)
- [ ] Thumbnail generation requirements (_m files - dimensions, quality)
- [ ] Maximum artwork size/count supported by devices
- [ ] How to link artwork to tracks in the database

**Open Source References**:
- Search: "rekordbox artwork format", "pioneer cdj artwork specification", "exportLibrary.xml artwork"

---

### 9. `PIONEER/USBANLZ/P###/XXXXXXXX/ANLZ0000.*` (3 files per track)
**Files**:
- `ANLZ0000.DAT` - Path and metadata
- `ANLZ0000.2EX` - Extended waveform data (color waveform)
- `ANLZ0000.EXT` - Waveform data

**Magic header**: `PMAI....PPTH`
**Path example**: `/Contents/A Tribe Called Quest/The Low End Theory/06 - A Tribe Called Quest - Show Business.mp3`

**Difference**: ANLZ files differ between onelib_only and onelib_and_devicelib (likely different analysis results)

**Research Topics**:
- [ ] Complete PMAI file format specification
- [ ] ANLZ0000.DAT structure (path encoding, metadata fields)
- [ ] ANLZ0000.2EX format (high-res color waveform - seems to contain waveform data like beat grid, BPM info)
- [ ] ANLZ0000.EXT format (detailed waveform - appears to contain raw waveform samples)
- [ ] Directory naming scheme (P###, XXXXXXXX)
- [ ] How to generate these from audio files
- [ ] Are there open source tools to analyze audio and generate these formats?

**Open Source References**:
- Search: "PMAI format specification", "ANLZ0000 format rekordbox", "rekordbox waveform format", "pioneer analysis file format"
- Look for: audio analysis libraries that can generate beatgrids, BPM, waveforms
- Keywords: "librosa", "madmom", "beat detection", "waveform generation"

---

### 10. `Contents/` Directory Structure
**Type**: Filesystem hierarchy
**Structure**: `Contents/Artist/Album/filename.ext`
**Status**: Identical in both versions (same audio files)

**Purpose**: Actual audio files in standard filesystem hierarchy

**Research Topics**:
- [ ] File naming conventions
- [ ] Supported audio formats
- [ ] File path encoding in database/ANLZ files (UTF-16LE observed)

---

## Critical Open Source Projects to Investigate

### 1. pyrekordbox
**URL**: https://github.com/Dracon ateau/pyrekordbox (verify exact URL)
**Purpose**: Python library for reading/writing Rekordbox databases
**Version**: 0.4.5.dev5 (already installed in project)
**Capabilities to Research**:
- [ ] Can it read/exportLibrary.db?
- [ ] Can it write/create new databases?
- [ ] Does it support device library export?
- [ ] What about export.pdb and exportExt.pdb?
- [ ] ANLZ file support?

### 2. Similar Conversion Tools
**Search Terms**:
- "rekordbox export library format converter"
- "djay to rekordbox converter"
- "rekordbox xml to database"
- "onelib to rekordbox"

**Potential Projects**:
- Any existing djay → Rekordbox converters
- Rekordbox library manipulation tools
- XML based Rekordbox export/import tools

### 3. Audio Analysis Libraries
**For ANLZ Generation**:
- **librosa** (Python) - Audio analysis, beat detection, tempo estimation
- **madmom** (Python) - Beat tracking, downbeat detection
- **Essentia** - Music audio analysis
- **aubio** - Onset detection, pitch tracking

### 4. Database/Encryption Libraries
- **SQLCipher** - For reading/writing encrypted SQLite databases
- **pysqlcipher3** - Python bindings for SQLCipher

---

## Technical Implementation Questions

### Database Questions
1. What is the SQLCipher key for exportLibrary.db?
2. What is the exact schema/structure of the database?
3. Can we use pyrekordbox to read/write, or do we need to implement from scratch?
4. How are tracks linked to ANLZ files?
5. How are playlists stored and structured?

### ANLZ File Questions
1. What is the complete binary format specification for PMAI files?
2. How do we generate waveform data (ANLZ0000.EXT)?
3. How do we generate color waveform data (ANLZ0000.2EX)?
4. What analysis data is required (BPM, beat grid, hot cues, loops)?
5. What audio analysis settings match Rekordbox's output?

### Device Library Questions
1. Is DeviceLibBackup/rbDevLibBaInfo required for device playback?
2. What is the purpose of DEVSETTING.DAT?
3. Is djprofile.nxs required or optional?
4. What do export.pdb and exportExt.pdb contain?
5. Can we generate valid device libraries from onelib data alone?

### Compatibility Questions
1. Which Pioneer CDJ models support which formats?
2. What are the limitations of onelib-only exports?
3. What minimum data is required for basic playback?
4. What additional data is needed for advanced features (waveforms, beat sync, etc.)?

---

## Development Strategy Research

### Phase 1: Format Understanding
- [ ] Document all file formats completely
- [ ] Identify existing libraries/tools we can leverage
- [ ] Determine minimum viable data required

### Phase 2: Proof of Concept
- [ ] Read onelib database
- [ ] Generate basic device library files
- [ ] Test on actual hardware

### Phase 3: Feature Complete
- [ ] Generate all ANLZ files
- [ ] Create artwork
- [ ] Generate all PDB files

---

## Search Queries for Online Research

### Database & Encryption
- "pyrekordbox documentation examples"
- "rekordbox exportLibrary.db SQLCipher key"
- "rekordbox database schema documentation"
- "pyrekordbox read exportLibrary.db"

### ANLZ File Formats
- "PMAI file format specification"
- "rekordbox ANLZ0000.DAT format"
- "rekordbox waveform format reverse engineering"
- "Pioneer CDJ analysis file format"

### PDB Files
- "rekordbox export.pdb file format"
- "rekordbox exportExt.pdb specification"
- "Pioneer PDB file format documentation"

### Device Configuration
- "rekordbox DEVSETTING.DAT format"
- "djprofile.nxs file specification"
- "rekordbox device library backup format"

### Conversion Tools
- "djay pro to rekordbox converter open source"
- "rekordbox library export format"
- "convert music library to rekordbox format"

### Audio Analysis
- "generate rekordbox waveforms programmatically"
- "beat detection python library"
- "audio waveform analysis library Python"

---

## Additional Resources to Investigate

1. **Pioneer DJ SDK** - If available, check for official documentation
2. **Rekordbox XML Export** - May provide insights into the data structure
3. **Existing reverse engineering efforts** on GitHub/forums
4. **DJ software forums** - DJ Tech Tools, Reddit r/DJs, etc.
5. **ISO/IEC standards** for audio metadata if relevant

---

## Success Criteria

The CLI tool should be able to:
1. Read onelibrary exported data
2. Generate all required device library files
3. Create a working export that CDJ-2000NXS can read
4. Preserve metadata (track info, cues, loops, playlists)
5. Optionally generate waveforms/analysis data

---

## Next Steps After Research

1. **Prototype database reader** using pyrekordbox
2. **Prototype ANLZ file generator** using audio analysis libraries
3. **Test on hardware** to validate output
4. **Build CLI interface** with click/typer
