# Remaining Work for 100% Bitwise Compatibility

## Current Status
- **Similarity**: 99.08% (166,398 / 167,936 bytes)
- **Differing bytes**: 1,538 across 18 pages
- **Status**: GOOD - File loads in rekordbox but minor differences remain

---

## Category 1: Row Structure Issues (HIGH PRIORITY - ~428 bytes)

### Issue: KeyRow Structure is Incorrect
**Impact**: 152 bytes in Page 12, likely similar issues in other metadata tables

**Current Implementation** (`src/onelib_to_devicelib/writers/metadata_rows.py:150`):
```python
class KeyRow:
    # Documented structure:
    # - row_offset (2 bytes): Always 0x0A
    # - index_shift (2 bytes): Row index shifted by 0x20
    # - key_id (4 bytes): Key ID
    # - name (DeviceSQL string): Key name
```

**Actual Reference Structure** (from binary analysis):
```python
# Each entry is 12 bytes:
# - key_id (4 bytes): Key ID (little-endian uint32)
# - key_id_dup (4 bytes): DUPLICATE of key_id (why?!)
# - str_marker (1 byte): 0x07 for 2-char ASCII string
# - char1 (1 byte): First character
# - char2 (1 byte): Second character
# - null (1 byte): 0x00 terminator
```

**Evidence**:
```
Reference Page 12 (Keys):
  Entry 0: 01 00 00 00 01 00 00 00 07 45 6d 00
           key_id=1  dup=1    m=0x07 'E'  'm'  \0

Generated Page 12 (Keys):
  Entry 0: 0a 00 20 00 01 00 00 00 0d 43 20 6d 61 6a 00 ...
           offset   idx      id     str="C maj" (wrong!)
```

**Fix Required**:
1. Update `KeyRow.marshal_binary()` to use correct 12-byte fixed structure
2. Remove row_offset and index_shift fields
3. Add duplicate key_id field
4. Use DeviceSQL encoding for short 2-char key names

**Similar Issues May Exist In**:
- GenreRow
- ArtistRow
- AlbumRow
- LabelRow
- Other metadata rows

Each needs binary analysis against reference to determine correct structure.

---

## Category 2: Page Header Field Calculations (MEDIUM PRIORITY - ~50 bytes)

### Issue: Transaction, free_size, next_offset Calculations
**Impact**: 5-10 bytes per differing page (18 pages = ~90-180 bytes)

**Current Implementation** (`src/onelib_to_devicelib/writers/page.py`):
```python
# Transaction: Simple increment
self.header.transaction += 1  # After each row insert

# free_size: Calculated from heap
self.header.free_size = self.heap.free_size()

# next_offset: Heap top cursor
self.header.next_heap_write_offset = self.heap.top_cursor
```

**Reference Values** (Page 2 - Tracks Data):
```
Generated: transaction=3, free_size=3540, next_offset=516
Reference: transaction=20, free_size=2644, next_offset=1400
```

**Analysis**:
- `transaction`: Not a simple increment. May be calculated as:
  - `num_rows * some_factor + base_value`
  - Or a cumulative counter across all pages
  - Reference Page 2 has 2 rows and transaction=20, suggesting 10 per row?

- `free_size`: Difference of 896 bytes between gen/ref
  - Generated: 3540 (more free space)
  - Reference: 2644 (less free space)
  - Suggests generated rows are smaller or laid out differently

- `next_offset`: Difference of 884 bytes
  - Generated: 516 (row data ends earlier)
  - Reference: 1400 (row data extends further)
  - Consistent with row structure differences

**Fix Required**:
1. Analyze reference file to derive transaction formula
2. Ensure row sizes match reference exactly (fixes free_size and next_offset)
3. May need to adjust heap layout or row padding

---

## Category 3: Track Row Metadata Differences (LOW PRIORITY - ~200 bytes)

### Issue: Track Metadata Content Differs
**Impact**: 156 bytes in Page 2 (Tracks Data)

**Analysis**:
These differences are in track metadata fields:
- Offset 56-63: checksum values (will differ per track)
- Offset 64-67: file path hashes (will differ)
- Offset 88-124: timestamps, IDs, file metadata

**Example** (Page 2, bytes 56-63):
```
Reference: 90 1f aa 00 7d e9 60 0d
Generated: a1 fd 9d 00 00 00 00 00
```

**Verdict**: ✅ **ACCEPTABLE** - These are content differences, not structure issues

- Track checksums are calculated from file content (will differ)
- File paths are different between OneLibrary export and reference
- Timestamps and IDs are export-specific

**No Fix Required** - These differences are expected and acceptable.

---

## Category 4: Index Page Structure (MEDIUM PRIORITY - ~50 bytes)

### Issue: Index Pages May Have Incorrect Structure
**Impact**: 12 bytes in Page 1 (Tracks Index)

**Current Implementation** (`src/onelib_to_devicelib/writers/page.py:150`):
```python
class IndexPage:
    # Structure:
    # - 32-byte page header
    # - 20-byte index header
    # - Index entries (4 bytes each, pointing to data pages)
    # - Padding with 0x1ffffff8
```

**Reference Analysis Needed**:
- Are index entries correct?
- Is padding pattern correct?
- Are index header fields correct?

**Fix Required**:
1. Binary analysis of reference index pages
2. Update IndexPage structure if needed
3. Ensure index entries point to correct data pages

---

## Category 5: Data Header Values for Remaining Pages (LOW PRIORITY - ~30 bytes)

### Issue: Some Data Pages Still Have Incorrect Data Headers
**Impact**: 1-2 bytes per page across ~15 pages

**Current Implementation** (`src/onelib_to_devicelib/writers/pdb_v3.py`):
```python
DATA_HEADER_VALUES = {
    'Tracks': (2, 2, 0, 0),
    'Genres': (2, 2, 0, 0),
    'Artists': (1, 0, 0, 0),
    # ... etc
}
```

**Fix Required**:
1. Analyze reference PDB to extract data header values for ALL page types
2. Add missing table types to DATA_HEADER_VALUES
3. Handle per-page vs per-table variations

---

## Category 6: Special Page Marshallers (MEDIUM PRIORITY - ~100 bytes)

### Issue: Special Pages May Not Match Exactly
**Impact**: Differences in Colors, Columns, Unknown17, Unknown18, History pages

**Current Status**:
- Special page marshallers exist (`special_pages.py`)
- They generate `raw_page_bytes` override
- May not match reference exactly

**Fix Required**:
1. Compare each special page against reference byte-by-byte
2. Update marshaller logic to match exactly
3. Ensure heap prefixes and data headers are correct

---

## Implementation Priority

### Phase 1: Fix Row Structures (HIGH PRIORITY)
**Expected Impact**: +200-300 bytes similarity (99.08% → ~99.25%)

1. Fix KeyRow structure (12-byte fixed format)
2. Analyze and fix GenreRow, ArtistRow, AlbumRow, LabelRow
3. Test each row type individually

**Files to Modify**:
- `src/onelib_to_devicelib/writers/metadata_rows.py`
- `src/onelib_to_devicelib/writers/pdb_v3.py` (row insertion logic)

### Phase 2: Fix Page Header Calculations (MEDIUM PRIORITY)
**Expected Impact**: +50-100 bytes similarity (99.25% → ~99.32%)

1. Derive transaction field formula from reference
2. Ensure heap layout matches reference
3. Fix free_size and next_offset calculations

**Files to Modify**:
- `src/onelib_to_devicelib/writers/page.py`
- `src/onelib_to_devicelib/writers/heap.py`

### Phase 3: Fix Index Pages (MEDIUM PRIORITY)
**Expected Impact**: +30-50 bytes similarity (99.32% → ~99.35%)

1. Analyze reference index page structure
2. Update IndexPage class
3. Verify index entries

**Files to Modify**:
- `src/onelib_to_devicelib/writers/page.py`

### Phase 4: Polish and Validate (LOW PRIORITY)
**Expected Impact**: +20-30 bytes similarity (99.35% → ~99.37%)

1. Fix remaining data header values
2. Fix special page marshallers
3. Comprehensive validation

---

## Realistic Expectations

### Achievable 100% Match?
**Answer**: ❌ **NO**, and here's why:

1. **Track Metadata Differences** (~200 bytes)
   - Checksums are calculated from file content
   - File paths differ between exports
   - Timestamps are export-specific
   - These differences are **inherent and acceptable**

2. **Export-Specific Data** (~100 bytes)
   - UUIDs, timestamps, sequence numbers
   - These will always differ between exports

### Realistic Target
**Answer**: ✅ **99.5% - 99.7% similarity is achievable**

- Fix row structures: +300 bytes
- Fix page headers: +100 bytes
- Fix index pages: +50 bytes
- Polish: +30 bytes

**Expected Result**: 167,436 / 167,936 bytes = 99.70% similarity

**Remaining ~500 bytes** would be:
- Track metadata content (acceptable)
- Export-specific data (acceptable)
- Minor structural quirks (tolerable)

---

## Testing Strategy

### For Each Fix:
1. Run `./test_pdb.sh` to measure impact
2. Check if specific page differences decrease
3. Verify no regressions in other pages
4. Test on actual hardware if available

### Success Criteria:
- ✅ Page-level differences < 10 bytes for non-content pages
- ✅ Overall similarity > 99.5%
- ✅ File loads in rekordbox without errors
- ✅ Tracks are browseable and playable

---

## Summary of Work

| Category | Impact | Effort | Priority |
|----------|--------|--------|----------|
| Fix KeyRow structure | +152 bytes | Medium | HIGH |
| Fix other row structures | +200 bytes | High | HIGH |
| Fix page header calculations | +100 bytes | Medium | MEDIUM |
| Fix index pages | +50 bytes | Low | MEDIUM |
| Polish data headers | +30 bytes | Low | LOW |
| Fix special pages | +100 bytes | Medium | MEDIUM |

**Total Potential Improvement**: +632 bytes (99.08% → 99.46%)

**Note**: 200+ bytes of differences are content-related and will never match.
