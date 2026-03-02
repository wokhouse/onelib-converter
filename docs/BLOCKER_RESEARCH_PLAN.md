# OneLib to DeviceLib - Blocker Research Plan

## Critical Blockers Requiring Online Research

This document contains focused research questions and search queries to resolve the three main blockers preventing completion of the OneLib to DeviceLib converter.

---

## Blocker #1: SQLCipher Decryption for Device Library Plus

### Problem
The `exportLibrary.db` file is encrypted with SQLCipher. We need to find the correct decryption key or API to read Device Library Plus exports.

### Current Status
- Database opens with `pyrekordbox.MasterDatabase` but queries fail with "file is not a database"
- Hex dump shows no standard SQLite header (confirms encryption)
- Universal key theory needs verification

### Research Questions

#### Q1.1: Does pyrekordbox have specific Device Library Plus support?
**Goal**: Determine if there's a dedicated API for reading `exportLibrary.db`

**Search Queries**:
```
"pyrekordbox" "Device Library Plus" "exportLibrary.db"
"pyrekordbox" "exportLibrary.db" decryption
pyrekordbox readthedocs exportLibrary.db
"pyrekordbox.device" "DeviceDatabase"
"pyrekordbox" "export db" API
```

**What to Look For**:
- Any mention of `exportLibrary.db` in pyrekordbox docs
- `DeviceDatabase` or `ExportDatabase` classes
- Alternative database connection methods
- Examples of reading exported databases

---

#### Q1.2: What is the SQLCipher key for Device Library Plus?
**Goal**: Find the universal encryption key or key derivation method

**Search Queries**:
```
"exportLibrary.db" SQLCipher key
rekordbox "Device Library Plus" encryption key
"rekordbox" "export library" universal key
pioneer rekordbox database encryption key
"exportLibrary.db" decryption
```

**What to Look For**:
- GitHub issues discussing Device Library Plus decryption
- Reverse engineering projects with working keys
- Documentation from pyrekordbox about keys
- Any mention of "universal key" for exports

**Specific Resources to Check**:
- github.com/dylanljones/pyrekordbox/issues
- github.com/liamcottle/pioneer-rekordbox-database-encryption
- djl-analysis.deepsymmetry.org (look for exportLibrary.db mentions)

---

#### Q1.3: How does exportLibrary.db differ from master.db?
**Goal**: Understand schema and encryption differences

**Search Queries**:
```
"exportLibrary.db" vs "master.db" rekordbox
rekordbox "Device Library Plus" schema
pyrekordbox export database tables
"exportLibrary.db" sqlcipher version
rekordbox 6 device export format
```

**What to Look For**:
- Schema documentation for exportLibrary.db
- Differences in table structure vs master.db
- Whether the same decryption approach works
- Migration/export process documentation

---

#### Q1.4: Are there alternative ways to read the database?
**Goal**: Find workarounds if direct decryption fails

**Search Queries**:
```
rekordbox xml export alternative
pyrekordbox xml to database
rekordbox export format options
"masterPlaylists6.xml" vs exportLibrary.db
```

**What to Look For**:
- XML export capabilities in Rekordbox
- Whether OneLibrary exports include XML files
- Alternative data access methods

---

## Blocker #2: PDB File Generation

### Problem
Need to generate valid `export.pdb` files for legacy Device Library format. Currently have placeholder implementation.

### Current Status
- Basic structure understood from Deep-Symmetry analysis
- REX project demonstrates PDB generation from Mixxx
- Kaitai Struct definitions available
- Need to implement writing logic

### Research Questions

#### Q2.1: How does REX generate PDB files?
**Goal**: Study working PDB generation implementation

**Search Queries**:
```
github.com/kimtore/rex PDB writer
"rekordbox exporter" golang PDB
REX rekordbox PDB generation code
"kimtore/rex" export.pdb write
```

**What to Look For**:
- Source code files that write PDB
- Data structures used for PDB
- Page allocation logic
- String table management
- Commit history for PDB-related changes

**Specific Files to Examine**:
- `pkg/pdb/` or similar directory
- Files with "pdb", "export", "device" in name
- Writer/encoder modules

---

#### Q2.2: What are the exact PDB file format specifications?
**Goal**: Get detailed format documentation

**Search Queries**:
```
rekordbox export.pdb format specification
"PIONEER" PDB file structure
rekordbox DeviceSQL format documentation
"rekordbox_pdb.ksy" kaitai struct
Deep-Symmetry rekordbox export analysis
```

**What to Look For**:
- Detailed byte-level format documentation
- Kaitai Struct `.ksy` file definition
- Page structure and row layout
- String storage format
- Checksum/hash algorithms

**Specific Resources**:
- djl-analysis.deepsymmetry.org/rekordbox-export-analysis
- github.com/Deep-Symmetry/crate-digger (Kaitai definitions)
- github.com/Holzhaus/rekordcrate (Rust implementation)

---

#### Q2.3: How do rekordcrate/crate-digger read PDB files?
**Goal**: Understand PDB format by studying parsers

**Search Queries**:
```
github.com/Holzhaus/rekordcrate PDB parsing
rekordcrate "pdb" module documentation
github.com/Deep-Symmetry/crate-digger PDB parser Java
rekordbox PDB file reader implementation
```

**What to Look For**:
- PDB file parsing logic (reverse to understand writing)
- Data structures that map to PDB format
- Field types and sizes
- Handling of special cases

**Specific Files to Examine**:
- `rekordcrate/src/pdb/` directory
- `crate-digger/src/main/kaitai/rekordbox_pdb.ksy`
- Parser implementation files

---

#### Q2.4: What's the minimum viable PDB file structure?
**Goal**: Create simplest working PDB for testing

**Search Queries**:
```
rekordbox export.pdb minimal structure
"CDJ-2000NXS" PDB requirements
Pioneer CDJ device library minimum files
rekordbox PDB essential tables
```

**What to Look For**:
- Which tables are absolutely required
- Minimum data needed for basic playback
- Can we skip artwork/history temporarily?
- Hardware tolerance for incomplete PDBs

---

#### Q2.5: Are there Python PDB writer implementations?
**Goal**: Find existing Python code to adapt

**Search Queries**:
```
python rekordbox PDB writer
"pyrekordbox" write PDB
python export.pdb generator
rekordbox PDB "write" github python
```

**What to Look For**:
- Existing Python implementations
- Code we can adapt or reference
- Libraries that handle PDB writing

---

## Blocker #3: ANLZ File Generation

### Problem
Need to generate complete ANLZ0000.DAT, .EXT, and .2EX files with waveforms and beat grids.

### Current Status
- Basic PMAI header structure understood
- Tag definitions documented (PPTH, PWV3-6, PCOB, PPOS, etc.)
- Placeholder implementations exist
- Need complete binary format specs

### Research Questions

#### Q3.1: What are the complete ANLZ file binary specifications?
**Goal**: Get detailed format documentation for all three file types

**Search Queries**:
```
rekordbox ANLZ0000.DAT format specification
rekordbox ANLZ0000.EXT waveform format
rekordbox ANLZ0000.2EX extended format
PMAI tag format documentation
"pyrekordbox" ANLZ file format
```

**What to Look For**:
- Byte-level structure for each ANLZ file type
- All tag types and their data structures
- Waveform data encoding (compression, resolution)
- Beat grid storage format
- Cue/loop point format

**Specific Resources**:
- pyrekordbox.readthedocs.io/en/latest/formats/anlz.html
- djl-analysis.deepsymmetry.org/rekordbox-export-analysis/anlz.html
- deepsymmetry.org/cratedigger/Analysis.pdf

---

#### Q3.2: How does pyrekordbox read/write ANLZ files?
**Goal**: Leverage pyrekordbox's ANLZ handling

**Search Queries**:
```
pyrekordbox read_anlz_file documentation
pyrekordbox ANLZ writer
"pyrekordbox.anlz" module
pyrekordbox get_anlz_path
```

**What to Look For**:
- `read_anlz_file()` method documentation
- Data structures returned by ANLZ parsing
- Whether pyrekordbox can write ANLZ files
- ANLZ path generation logic

---

#### Q3.3: What are the waveform data encoding details?
**Goal**: Understand how to encode waveform data properly

**Search Queries**:
```
rekordbox waveform data encoding
ANLZ0000.EXT waveform format details
rekordbox color waveform PWV5 PWV6
beat grid encoding ANLZ
"rekordbox" waveform compression
```

**What to Look For**:
- Sample resolution (bits per sample)
- Downsampling factor
- Color waveform RGB encoding
- Beat grid time precision
- Cue point storage (milliseconds vs samples)

---

#### Q3.4: How to generate ANLZ from audio analysis?
**Goal**: Integrate librosa/madmom with ANLZ format

**Search Queries**:
```
generate rekordbox ANLZ files programmatically
librosa to rekordbox waveform
beat detection rekordbox format
"rekordbox analysis" python
generate ANLZ from audio python
```

**What to Look For**:
- Tools that already generate ANLZ from audio
- Audio analysis settings that match Rekordbox
- Waveform downsampling algorithms
- Beat grid conversion from audio analysis

---

#### Q3.5: What's the ANLZ directory naming scheme?
**Goal**: Understand P###/XXXXXXXX/ directory generation

**Search Queries**:
```
rekordbox USBANLZ directory naming
ANLZ path hash algorithm
P### XXXXXXXX rekordbox
get_anlz_path_hash rekordbox
"rekordbox" ANLZ folder structure
```

**What to Look For**:
- How playlist ID (P###) is determined
- Hash algorithm for 8-character directory name
- Whether it's consistent across exports

---

## Priority Order for Research

### Phase 1: Database Access (Blocker #1)
**Must Solve First** - Nothing works without reading source data

1. Search pyrekordbox docs for Device Library Plus support (Q1.1)
2. Search for SQLCipher key (Q1.2)
3. Check for alternative access methods (Q1.4)

**Success Criteria**: Can successfully query `exportLibrary.db` and retrieve track/playlist data

---

### Phase 2: Basic PDB Generation (Blocker #2)
**Critical** - Needed for any hardware compatibility

1. Study REX project PDB writer (Q2.1)
2. Review Kaitai Struct definition (Q2.2)
3. Study rekordcrate parser (Q2.3)

**Success Criteria**: Can generate a valid `export.pdb` that CDJ-2000NXS can read

---

### Phase 3: ANLZ Generation (Blocker #3)
**Important** - Needed for waveforms and advanced features

1. Study pyrekordbox ANLZ docs (Q3.1, Q3.2)
2. Research waveform encoding (Q3.3)
3. Investigate audio-to-ANLZ tools (Q3.4)

**Success Criteria**: Can generate ANLZ files with waveforms and beat grids

---

## Research Execution Plan

### Step 1: Document Scavenging (30 minutes)
Search official documentation first:
- pyrekordbox.readthedocs.io - full site search for "exportLibrary", "Device Library Plus", "ANLZ", "PDB"
- Deep-Symmetry analysis site - complete review of export format docs
- Research report references - check all cited URLs

### Step 2: GitHub Code Search (45 minutes)
Search for working implementations:
- Search all code on GitHub for "exportLibrary.db"
- Search for "ANLZ" language:python
- Search for "write.*pdb" rekordbox
- Look at issues/discussions in pyrekordbox, rekordcrate, crate-digger

### Step 3: Issue/Forum Research (30 minutes)
Search for discussions about these problems:
- GitHub issues in relevant repos
- Stack Overflow questions
- DJ/producer forums (DJTechTools, Reddit r/DJs)
- Gitter/Discord channels for projects

### Step 4: Test Alternative Approaches (if needed)
If direct decryption fails:
- Test with different Rekordbox versions
- Export XML from Rekordbox and compare
- Try reading exportLibrary.db with different tools

---

## Expected Outcomes

### Best Case (Full Research Success)
- Find complete documentation for all formats
- Locate working Python implementations
- Have clear path to completion
- **Timeline**: 2-3 days to complete implementation

### Medium Case (Partial Success)
- Find enough info to proceed with trial-and-error
- Need to reverse engineer some details
- Test on actual hardware to validate
- **Timeline**: 1-2 weeks to complete

### Worst Case (Limited Information)
- Need to do original reverse engineering
- Study binary files extensively
- May need to implement from scratch
- **Timeline**: 3-4 weeks to complete

---

## Quick Reference: Key Resources

### Documentation
- pyrekordbox.readthedocs.io
- djl-analysis.deepsymmetry.org
- Rekordbox USB Export Guide (PDF)

### Open Source Projects
- github.com/dylanljones/pyrekordbox
- github.com/kimtore/rex (Go)
- github.com/Holzhaus/rekordcrate (Rust)
- github.com/Deep-Symmetry/crate-digger (Java)

### Search Terms for Quick Copy-Paste
```
"exportLibrary.db" SQLCipher
pyrekordbox Device Library Plus
rekordbox PDB format
ANLZ0000 format specification
rekordbox waveform encoding
Pioneer CDJ export format
```

---

## Notes for Online Research Agent

When executing research:

1. **Prioritize GitHub code searches** - actual working code is most valuable
2. **Look for recent activity** - projects updated in 2023-2025 are most relevant
3. **Check issues before PRs** - problems discussed there often have solutions
4. **Save specific code examples** - we'll need to adapt them to Python
5. **Document version requirements** - which Rekordbox/pyrekordbox versions work
6. **Note any workarounds** - even if we can't do it "properly", hacks are OK for MVP

---

**Research Goal**: Uncover enough information to:
1. Read `exportLibrary.db` successfully
2. Generate working `export.pdb` files
3. Create valid ANLZ files with waveforms

This will enable completion of the OneLib to DeviceLib converter tool.
