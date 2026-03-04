# Bitwise Comparison Results

**Date**: 2026-03-03
**Generated PDB**: 217,088 bytes (53 pages)
**Reference PDB**: 167,936 bytes (41 pages)
**Difference**: +49,152 bytes (+29% larger)

---

## Executive Summary

### Critical Issues Found

1. **CRITICAL: Index Page Structure Missing** - First page of each table should be an index page (page_flags=0x64), not a data page (page_flags=0x34)
2. **CRITICAL: Track Row Structure Incorrect** - Our generated file has page_flags=0x34 on page 1, but reference has 0x64
3. **Table Pointer Bug** - Table pointers are showing impossible overlapping page ranges (e.g., Genres starting at page 1, Artists also at page 1)

### Good News

- ✅ **unnamed30 = 0x0003** correctly set (CRITICAL for rekordbox compatibility)
- ✅ **row_offset = 0x0024** correctly set
- ✅ **bitmask = 0x0C0700** correctly set
- ✅ **magic = 0x00000000** correctly set
- ✅ **page_size = 4096** correctly set

---

## File-Level Comparison

| Metric | Reference | Generated | Status |
|--------|-----------|-----------|--------|
| File Size | 167,936 bytes | 217,088 bytes | ⚠️ +29% larger |
| Page Count | 41 pages | 53 pages | ⚠️ +12 pages |
| Magic Number | 0x00000000 | 0x00000000 | ✅ |
| Page Size | 4096 | 4096 | ✅ |
| Num Tables | 20 | 20 | ✅ |
| next_unused_page | 54 | 47 | ❌ |
| unknown1 | 1 | 1 | ✅ |
| sequence | 22 | 6 | ❌ |

---

## Page Structure Comparison

### Reference Page Layout

| Table | Pages | Page Range | Structure |
|-------|-------|------------|-----------|
| Tracks | 2 | 1-2 | Index + Data |
| Genres | 2 | 3-4 | Index + Data |
| Artists | 2 | 5-6 | Index + Data |
| Albums | 2 | 7-8 | Index + Data |
| Labels | 1 | 9-9 | Empty (self-pointing) |
| Keys | 2 | 11-12 | Index + Data |
| Colors | 2 | 13-14 | Index + Data |
| PlaylistTree | 2 | 15-16 | Index + Data |
| PlaylistEntries | 2 | 17-18 | Index + Data |
| Unknown9 | 1 | 19-19 | Empty (self-pointing) |

**Pattern**: Non-empty tables have 2 pages (index + data), empty tables have 1 page

**Gap**: Page 10 is skipped (reserved space between Labels and Keys)

### Generated Page Layout (Detected via get_table_pages)

| Table | Ref Pages | Gen Pages (detected) | Issue |
|-------|-----------|---------------------|-------|
| Tracks | 2 | 1 | Missing index page |
| Genres | 2 | 41 | Impossible! Points to wrong pages |
| Artists | 2 | 42 | Impossible! Points to wrong pages |
| Albums | 2 | 43 | Impossible! Points to wrong pages |
| Keys | 2 | 44 | Impossible! Points to wrong pages |

**Root Cause**: The `get_table_pages()` function scans for pages with matching `page_type`, but our pages are being written with incorrect `page_type` values.

---

## Critical Corruption Check

| Field | Reference | Generated | Status |
|-------|-----------|-----------|--------|
| Magic number | 0x00000000 | 0x00000000 | ✅ |
| Page size | 4096 | 4096 | ✅ |
| TrackRow unnamed30 | 0x0003 | 0x0003 | ✅ |
| TrackRow offset | 0x0024 | 0x0024 | ✅ |
| Bitmask | 0x0C0700 | 0x0C0700 | ✅ |
| **Page flags (page 1)** | **0x64** | **0x34** | ❌ **CRITICAL** |

---

## Page Header Analysis

### Page 1 (First Track Page)

**Reference**:
```
magic: 0x00000000
page_index: 1
page_type: 0 (Tracks)
page_flags: 0x64 (INDEX PAGE!)
num_rows_small: 0x00 (0 rows - this is an index page)
```

**Generated**:
```
magic: 0x00000000
page_index: 1
page_type: 0 (Tracks)
page_flags: 0x34 (DATA PAGE)
num_rows_small: 0x02 (2 rows - these are actual track rows)
```

**Issue**: Reference uses an index page as the first page of Tracks table. We're writing data directly to page 1.

### Page 2 (Reference) vs Page 1 (Generated)

**Reference Page 2**:
```
page_index: 2
page_type: 0 (Tracks)
page_flags: 0x34 (DATA PAGE)
num_rows_small: 0x04 (4 rows)
```

This is the first data page with actual track rows.

---

## Root Cause Analysis

### Issue 1: Missing Index Pages

**Problem**: The code comment in `add_track()` says:
```python
# NOTE: Reference doesn't use IndexPages for Tracks
```

**This is WRONG!** The reference DOES use index pages for Tracks (and all other tables).

**Evidence**:
- Reference page 1 has `page_flags=0x64` (index page)
- Reference page 1 has `num_rows_small=0x00` (0 data rows)
- Reference page 2 has `page_flags=0x34` (data page) with actual track rows

**Fix Required**:
1. Create an `IndexPage` as the first page of the Tracks table (page 1)
2. Create a `DataPage` as the second page (page 2) with actual track rows
3. Update the index page to point to the data page

### Issue 2: Page Type Not Being Set Correctly

**Problem**: When pages are marshaled to bytes, the `page_type` field in the page header might not match the table type.

**Evidence**:
- The `get_table_pages()` function finds pages by scanning for `page_type`
- It's finding impossible overlapping page ranges
- This suggests pages are being written with incorrect `page_type` values

**Investigation Needed**:
1. Check if `IndexPage` is being created with the correct `page_type`
2. Check if `DataPage` is being created with the correct `page_type`
3. Verify that `marshal_binary()` preserves the `page_type` field

### Issue 3: Page Index Assignment

**Problem**: Pages are being created with local indices (0, 1, 2...) that don't match their actual file positions.

**Current Behavior**:
```python
# In _add_metadata_row:
index_page = IndexPage(page_index=0, page_type=page_type)  # Wrong!
data_page = DataPage(page_index=1, page_type=page_type)   # Wrong!
```

**Expected Behavior**:
Each table should start at a unique global page index:
- Tracks: pages 1-2
- Genres: pages 3-4
- Artists: pages 5-6
- etc.

**Fix Required**:
The `_update_page_indices()` method needs to assign global page indices correctly, OR pages need to be created with their correct global indices from the start.

---

## Action Items (Priority Order)

### Priority 1: Fix Index Page Structure (CRITICAL)

**Files to modify**:
- `src/onelib_to_devicelib/writers/pdb_v3.py` - `add_track()` and `_add_metadata_row()`

**Changes**:
1. Remove the incorrect comment about Tracks not using IndexPages
2. Update `add_track()` to create an IndexPage as the first page
3. Ensure IndexPage has `page_flags=0x64` (not 0x34)

**Expected impact**:
- File will be accepted by rekordbox (no corruption)
- Page structure will match reference

**Test**:
```bash
python tests/check_corruption.py /tmp/test_conversion/PIONEER/rekordbox/export.pdb
# Should show: ✅ Page flags: 0x64 (index page)
```

### Priority 2: Fix Page Index Assignment

**Files to modify**:
- `src/onelib_to_devicelib/writers/pdb_v3.py` - `_update_page_indices()`

**Changes**:
1. Assign global page indices to pages as they're created
2. Ensure non-overlapping page ranges for each table
3. Match reference layout (Tracks=1-2, Genres=3-4, etc.)

**Expected impact**:
- Table pointers will show correct page ranges
- File size will decrease (currently 53 pages, should be ~41)

**Test**:
```bash
python tests/compare_pdb_structure.py reference.pdb generated.pdb
# Should show matching page ranges
```

### Priority 3: Verify Page Type Preservation

**Files to check**:
- `src/onelib_to_devicelib/writers/page.py` - `marshal_binary()` methods
- `src/onelib_to_devicelib/writers/pdb_v3.py` - page creation

**Verification**:
1. Confirm `IndexPage` marshals with correct `page_type`
2. Confirm `DataPage` marshals with correct `page_type`
3. Add debug output to show page_type values during write

### Priority 4: Optimize File Size

**Current size**: 217,088 bytes (53 pages)
**Target size**: ~167,936 bytes (41 pages)

**Opportunities**:
- Remove unnecessary placeholder pages (currently 53 vs 41)
- Optimize string heap storage
- Verify we're not creating extra index/data pages

---

## Test Tools Available

### 1. Corruption Check
```bash
python tests/check_corruption.py <pdb_path>
```
Checks only critical corruption-causing fields.

### 2. Structure Comparison
```bash
python tests/compare_pdb_structure.py <reference.pdb> <generated.pdb>
```
Compares file-level metrics and table pointers.

### 3. Page-Level Comparison
```bash
python tests/compare_pdb_pages.py <reference.pdb> <generated.pdb>
```
Identifies which pages differ and why.

### 4. Track Row Comparison
```bash
python tests/compare_pdb_tracks.py <reference.pdb> <generated.pdb> [count]
```
Field-by-field track row comparison.

### 5. Full Comparison Suite
```bash
./tests/run_full_comparison.sh
```
Runs all comparison phases in sequence.

---

## Next Steps

1. **Fix Priority 1** (Index Page Structure)
   - Modify `add_track()` to create IndexPage first
   - Run corruption check to verify fix
   - Expected: Page flags change from 0x34 to 0x64

2. **Fix Priority 2** (Page Index Assignment)
   - Modify `_update_page_indices()` to assign correct global indices
   - Run structure comparison to verify fix
   - Expected: Table pointers show non-overlapping ranges

3. **Verify Priority 3** (Page Type Preservation)
   - Add debug logging to track page_type values
   - Run page-level comparison
   - Expected: get_table_pages() finds correct pages

4. **Address Priority 4** (File Size Optimization)
   - After fixes above, file size should naturally decrease
   - Target: <180KB (within 10% of reference)

---

## Conclusion

The generated PDB files have **all critical track row fields correct** (unnamed30, row_offset, bitmask), but the **page structure is wrong**:

1. Missing index pages (first page of each table should be index, not data)
2. Incorrect page index assignment (causing table pointer confusion)
3. File is 29% larger than reference due to extra/incorrectly placed pages

**Good news**: These are structural issues that can be fixed without changing the track row format. The track rows themselves are correctly formatted.

**Bad news**: The current file will likely be rejected by rekordbox due to the incorrect page flags on page 1.

**Recommended approach**: Fix Priority 1 (Index Page Structure) first, then test on actual hardware if available.
