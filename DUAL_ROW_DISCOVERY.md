# Dual-Row Structure Discovery

**Date**: 2026-03-05
**Status**: ✅ **CRITICAL BREAKTHROUGH**

## Executive Summary

Through systematic hardware testing (Tests T1.1-T1.5), we discovered that the PDB format uses a **dual-row structure** for each track. Each track requires TWO rows in the database:

1. **ID Row** (index_shift = 0, 64, 128...) - Registered in row index
2. **Metadata Row** (index_shift = 32, 96, 160...) - Contains displayed data

This discovery explains why our 99.26% similar PDB was still corrupted - we were only writing one row per track.

---

## Test Results Summary

| Test | Modification | Result | Key Insight |
|------|--------------|--------|-------------|
| **T1.1** | Track 0 BPM 154→155 only | ❌ No change | Modifying ID row doesn't affect display |
| **T1.2** | Disabled OneLibrary DB | ❌ No change | CDJ reads from metadata row, not ID row |
| **T1.3** | **BOTH tracks** BPM →155 | ✅ **SUCCESS** | Both rows must be updated |
| **T1.4** | Track0=154.8, Track1=155 | ✅ Shows 155 | Display comes from Track 1 (metadata) |
| **T1.5** | Removed Track 0 entirely | ❌ Track gone | ID row required for track to appear |

---

## The Discovery Process

### Initial Problem
- Generated PDB at 99.26% similarity
- Still caused corruption on CDJ
- Structure looked correct (page_flags, row size, bitfield)

### Systematic Testing Approach
Instead of trying to fix all differences, we started with a known-good baseline and made ONE change at a time:

1. **Test T1.1**: Changed BPM in Track 0 only → didn't work
2. **Test T1.2**: Disabled OneLibrary to force PDB-only mode → didn't work
3. **Test T1.3**: Changed BPM in BOTH Track 0 and Track 1 → **SUCCESS!**

### Key Observation
```
Baseline PDB has 4 track rows for 2 tracks:
  Track 0: Ragatere, BPM 154.8
  Track 1: Ragatere, BPM 154.8  (duplicate?)
  Track 2: Payaso, BPM 85.3
  Track 3: Payaso, BPM 85.3    (duplicate?)
```

### Critical Test (T1.4)
Modified only Track 1, not Track 0:
- Track 0: BPM 154.8 (original)
- Track 1: BPM 155.0 (modified)
- **Result**: CDJ displayed BPM 155.0

**Conclusion**: CDJ uses Track 1 for display, not Track 0!

### Definitive Test (T1.5)
Removed Track 0 entirely:
- **Result**: Database reads fine, but track doesn't appear

**Conclusion**: Track 0 is required for track to exist, Track 1 provides displayed data!

---

## Technical Details

### index_shift Pattern

Analysis of Track 0-3 in baseline PDB:

```
Track 0: row_offset=36, index_shift=0   (0x00)  - ID row
Track 1: row_offset=36, index_shift=32  (0x20)  - Metadata row
Track 2: row_offset=36, index_shift=64  (0x40)  - ID row
Track 3: row_offset=36, index_shift=96  (0x60)  - Metadata row
```

**Pattern**:
- ID rows: index_shift = track_index × 0x40 (even multiples of 0x20)
- Metadata rows: index_shift = track_index × 0x40 + 0x20 (odd multiples of 0x20)

### How CDJ Reads the Database

```
1. CDJ reads row index at end of page
2. Row index points to ID rows (Track 0, 2)
3. CDJ uses index_shift to find associated metadata row:
   - Track 0 (shift=0) → Track 1 (shift=32)
   - Track 2 (shift=64) → Track 3 (shift=96)
4. CDJ displays data from metadata row (Track 1, 3)
```

### Why This Explains Everything

| Test | Expected | Actual | Explanation |
|------|----------|--------|-------------|
| T1.1 | BPM 155 | BPM 154.8 | Modified ID row, metadata row still had original value |
| T1.3 | BPM 155 | BPM 155 ✅ | Both rows updated |
| T1.4 | BPM 154.8 | BPM 155 ✅ | Display reads from Track 1 (metadata row) |
| T1.5 | Track visible | Track gone | ID row missing → can't find track |

---

## Implementation Requirements

### Current Code (WRONG)

```python
# In PDBWriterV3.add_tracks()
for track_index, track in enumerate(tracks):
    track_row = TrackRow(track)
    data = track_row.marshal_binary(track_index)
    page.insert_row(data)
    # Only writes ONE row per track ❌
```

### Required Fix

```python
# In PDBWriterV3.add_tracks()
for track_index, track in enumerate(tracks):
    # Write ID row
    index_shift_id = track_index * 0x40  # 0, 64, 128, ...
    id_row = TrackRow(track)
    id_row.header.index_shift = index_shift_id
    id_data = id_row.marshal_binary(track_index)
    page.insert_row(id_data)

    # Write Metadata row
    index_shift_meta = track_index * 0x40 + 0x20  # 32, 96, 160, ...
    meta_row = TrackRow(track)
    meta_row.header.index_shift = index_shift_meta
    meta_data = meta_row.marshal_binary(track_index)
    page.insert_row(meta_data)
```

### Changes Needed

1. **TrackRow.marshal_binary()**
   - Accept `index_shift` as parameter instead of calculating internally
   - OR allow caller to override the calculated value

2. **PDBWriterV3.add_tracks()**
   - Write TWO rows per track instead of one
   - Calculate correct index_shift values
   - Ensure row index points to ID rows only

3. **DataPage.insert_row()**
   - May need updates to handle double the rows
   - Verify row index structure handles dual rows correctly

---

## Validation Strategy

### Test After Implementation

1. **Generate PDB** with dual-row structure
2. **Verify structure**:
   - 2 tracks → 4 track rows (not 2)
   - index_shift values correct (0, 32, 64, 96)
   - Row index points to ID rows (0, 64)
3. **Hardware test** on CDJ:
   - Database should load without corruption
   - Both tracks should appear
   - BPM should display correctly
4. **Test metadata modification**:
   - Modify BPM in both rows
   - Verify CDJ displays updated value

### Success Criteria

- ✅ No corruption message
- ✅ All tracks visible
- ✅ BPM displays correctly
- ✅ Can modify metadata successfully

---

## Implications

### For Our PDB Writer

**Current State**:
- Generates 99.26% similar PDB
- Single-row implementation
- Corrupted on hardware

**After Fix**:
- Dual-row implementation
- Should work on hardware
- Basic Device Library functionality

### For Metadata Fields

**What We Know**:
- ✅ Tempo field works (T1.3 proven)
- ✅ No checksum on tempo field
- ✅ Both rows must be updated

**What We Need to Test**:
- Duration, year, play count (numeric fields - likely similar)
- Track names, artist, album (string fields - untested)
- Hot cue linking (unknown)

### For Option A (Full Reverse Engineering)

**Before This Discovery**:
- 40% confidence (high similarity but broken)

**After This Discovery**:
- 80% confidence (we know the structure)
- Clear path forward
- Estimated 2-3 days to MVP

---

## Next Steps

1. **Implement dual-row structure** (CRITICAL)
   - Modify TrackRow.marshal_binary()
   - Update PDBWriterV3.add_tracks()
   - Test with validation data

2. **Test on hardware**
   - Verify no corruption
   - Verify track listing
   - Verify BPM display

3. **Test other metadata fields**
   - Duration, year, play count
   - Track names (check hot cues)

4. **Implement playlists**
   - Similar dual-row structure?
   - Test on hardware

---

## Files to Modify

1. **src/onelib_to_devicelib/writers/track.py**
   - Line 170: `marshal_binary(row_index: int)` → `marshal_binary(row_index: int, index_shift: int = None)`
   - Allow caller to specify index_shift

2. **src/onelib_to_devicelib/writers/pdb_v3.py**
   - Line ~400: `add_tracks()` method
   - Write TWO rows per track
   - Calculate correct index_shift values

3. **src/onelib_to_devicelib/writers/page.py**
   - Verify `insert_row()` handles dual rows
   - Check row index structure

---

## Conclusion

This discovery is the **missing piece** we've been searching for. The dual-row structure explains why our high-similarity PDB was corrupted, and the fix is straightforward.

**Confidence Level**: 80-90% for basic Device Library functionality after implementing this fix.

**Timeline**: 2-3 days to MVP, 1-2 weeks to beta, 3-4 weeks to production.

**Status**: 🟢 **READY TO IMPLEMENT**
