#!/usr/bin/env python3
"""
Test Special Page Marshallers

Tests each special page marshaller individually against the reference PDB file.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from onelib_to_devicelib.writers.special_pages import (
    Unknown17Marshaller, Unknown18Marshaller,
    ColorsMarshaller, ColumnsMarshaller, HistoryMarshaller
)
from onelib_to_devicelib.writers.metadata_rows import (
    Unknown17Row, Unknown18Row, ColorRow,
    ColumnRow, HistoryRow
)


def test_unknown17_page():
    """Test Unknown17 page (Page 36)."""
    print("\n=== Testing Unknown17 Page (36) ===")

    # Create default rows (22 total)
    rows = []

    # First 4 entries go in data header (bytes 32-63)
    rows.append(Unknown17Row(22, 0, 0x00000000))  # Entry at bytes 32-39
    rows.append(Unknown17Row(1, 1, 0x00000163))   # Entry at bytes 40-47
    rows.append(Unknown17Row(5, 6, 0x00000105))   # Entry at bytes 48-55
    rows.append(Unknown17Row(6, 7, 0x00000163))   # Entry at bytes 56-63

    # Remaining 18 entries (from binary analysis of reference)
    # Reference has 22 regular rows (19 valid + 3 null)
    default_unknown17 = [
        (7, 8, 0x00000163),
        (8, 9, 0x00000163),
        (9, 10, 0x00000163),
        (10, 11, 0x00000163),
        (13, 15, 0x00000163),
        (14, 19, 0x00000104),
        (15, 20, 0x00000106),
        (16, 21, 0x00000163),
        (18, 23, 0x00000163),
        (2, 2, 0x00010002),
        (3, 3, 0x00020003),
        (4, 4, 0x00030001),
        (11, 12, 0x00040063),
        (17, 5, 0x00050063),
        (19, 22, 0x00060063),
        (20, 18, 0x00070063),
        (27, 26, 0x00080263),
        (24, 17, 0x00090063),
        (22, 27, 0x000a0063),
        (0, 0, 0x00000000),  # Row 19 - null
        (0, 0, 0x00000000),  # Row 20 - null
        (0, 0, 0x00000000),  # Row 21 - null
    ]
    for field1, field2, field3 in default_unknown17:
        rows.append(Unknown17Row(field1, field2, field3))

    # Generate page
    marshaller = Unknown17Marshaller()
    page_data = marshaller.marshal_page(36, 17, rows)

    # Compare with reference
    ref_path = Path('validation_data/empty_onelib_and_devicelib/PIONEER/rekordbox/export.pdb')
    if not ref_path.exists():
        print("⚠️  Reference file not found - skipping comparison")
        return None

    ref_data = ref_path.read_bytes()
    ref_page = ref_data[36*4096:(36+1)*4096]

    # Verify match
    if page_data == ref_page:
        print('✅ Unknown17 page matches 100%')
        return True
    else:
        diff = sum(1 for a, b in zip(page_data, ref_page) if a != b)
        print(f'❌ Unknown17 page has {diff} byte differences')

        # Show first difference
        for i, (a, b) in enumerate(zip(page_data, ref_page)):
            if a != b:
                print(f'  First diff at byte {i} (offset 0x{i:04x}): gen=0x{a:02x} ref=0x{b:02x}')
                break

        return False


def test_unknown18_page():
    """Test Unknown18 page (Page 38)."""
    print("\n=== Testing Unknown18 Page (38) ===")

    # Create default rows (18 total)
    rows = []

    # Structure from binary analysis of reference:
    # - Bytes 32-39: Heap prefix (field1=17, field2=0, field3=0)
    # - Bytes 40-47: Extra entry (field1=1, field2=6, field3=1)
    # - Bytes 48-55: Data header entry 1 (field1=21, field2=7, field3=1)
    # - Bytes 56-63: Data header entry 2 (field1=14, field2=8, field3=1)

    # Heap prefix entry (bytes 32-39)
    rows.append(Unknown18Row(17, 0, 0x00000000))

    # Extra entry (bytes 40-47)
    rows.append(Unknown18Row(1, 6, 0x00000001))

    # Data header entries (bytes 48-63)
    rows.append(Unknown18Row(21, 7, 0x00000001))
    rows.append(Unknown18Row(14, 8, 0x00000001))

    # Remaining 17 entries (13 indexed + 4 unindexed)
    default_unknown18 = [
        # First 13 are indexed by RowSets
        (8, 9, 0x00000001),
        (9, 10, 0x00000001),
        (10, 11, 0x00000001),
        (15, 13, 0x00000001),
        (13, 15, 0x00000001),
        (23, 16, 0x00000001),
        (22, 17, 0x00000001),
        (25, 0, 0x00000100),
        (26, 1, 0x00000200),
        (2, 2, 0x00000300),
        (3, 3, 0x00000400),
        (5, 4, 0x00000500),
        (6, 5, 0x00000600),
        # Last 4 are NOT indexed (added after row_offsets)
        (11, 12, 0x00000700),
        (0, 0, 0x00000000),
        (0, 0, 0x00000000),
        (0, 0, 0x00000000),
    ]
    for field1, field2, field3 in default_unknown18:
        rows.append(Unknown18Row(field1, field2, field3))

    # Generate page
    marshaller = Unknown18Marshaller()
    page_data = marshaller.marshal_page(38, 18, rows)

    # Compare with reference
    ref_path = Path('validation_data/empty_onelib_and_devicelib/PIONEER/rekordbox/export.pdb')
    if not ref_path.exists():
        print("⚠️  Reference file not found - skipping comparison")
        return None

    ref_data = ref_path.read_bytes()
    ref_page = ref_data[38*4096:(38+1)*4096]

    # Verify match
    if page_data == ref_page:
        print('✅ Unknown18 page matches 100%')
        return True
    else:
        diff = sum(1 for a, b in zip(page_data, ref_page) if a != b)
        print(f'❌ Unknown18 page has {diff} byte differences')

        # Show first difference
        for i, (a, b) in enumerate(zip(page_data, ref_page)):
            if a != b:
                print(f'  First diff at byte {i} (offset 0x{i:04x}): gen=0x{a:02x} ref=0x{b:02x}')
                break

        return False


def test_colors_page():
    """Test Colors page (Page 14)."""
    print("\n=== Testing Colors Page (14) ===")

    # Create default rows (8 total)
    rows = []

    # First color (Pink) goes in data header
    rows.append(ColorRow(color_id=2, name="Pink"))

    # Remaining 7 colors
    default_colors = [
        (3, "Red"),
        (4, "Orange"),
        (5, "Yellow"),
        (6, "Green"),
        (7, "Aqua"),
        (8, "Blue"),
        (0, "Purple"),
    ]
    for color_id, name in default_colors:
        rows.append(ColorRow(color_id=color_id, name=name))

    # Generate page
    marshaller = ColorsMarshaller()
    page_data = marshaller.marshal_page(14, 6, rows)

    # Compare with reference
    ref_path = Path('validation_data/empty_onelib_and_devicelib/PIONEER/rekordbox/export.pdb')
    if not ref_path.exists():
        print("⚠️  Reference file not found - skipping comparison")
        return None

    ref_data = ref_path.read_bytes()
    ref_page = ref_data[14*4096:(14+1)*4096]

    # Verify match
    if page_data == ref_page:
        print('✅ Colors page matches 100%')
        return True
    else:
        diff = sum(1 for a, b in zip(page_data, ref_page) if a != b)
        print(f'❌ Colors page has {diff} byte differences')

        # Show first difference
        for i, (a, b) in enumerate(zip(page_data, ref_page)):
            if a != b:
                print(f'  First diff at byte {i} (offset 0x{i:04x}): gen=0x{a:02x} ref=0x{b:02x}')
                break

        return False


def test_columns_page():
    """Test Columns page (Page 34)."""
    print("\n=== Testing Columns Page (34) ===")

    # Create default rows (27 total)
    rows = []

    # First column (GENRE) split between heap prefix and data header
    rows.append(ColumnRow(column_id=1, name="GENRE", field_type=0x0080, size_type=0x00001290))

    # Remaining 26 columns
    default_columns = [
        (2, "ARTIST", 0x0081, 0x00001490),
        (3, "ALBUM", 0x0082, 0x00001290),
        (4, "TRACK", 0x0083, 0x00001290),
        (5, "BPM", 0x0085, 0x00000e90),
        (6, "RATING", 0x0086, 0x00001490),
        (7, "YEAR", 0x0087, 0x00001090),
        (8, "REMIXER", 0x0088, 0x00001690),
        (9, "LABEL", 0x0089, 0x00001290),
        (10, "ORIGINAL ARTIST", 0x008a, 0x00002690),
        (11, "KEY", 0x008b, 0x00000e90),
        (12, "CUE", 0x008d, 0x00000e90),
        (13, "COLOR", 0x008e, 0x00001290),
        (14, "TIME", 0x0092, 0x00001090),
        (15, "BITRATE", 0x0093, 0x00001690),
        (16, "FILE NAME", 0x0094, 0x00001a90),
        (17, "PLAYLIST", 0x0084, 0x00001890),
        (18, "HOT CUE BANK", 0x0098, 0x00002090),
        (19, "HISTORY", 0x0095, 0x00001690),
        (20, "SEARCH", 0x0091, 0x00001490),
        (21, "COMMENTS", 0x0096, 0x00001890),
        (22, "DATE ADDED", 0x008c, 0x00001c90),
        (23, "DJ PLAY COUNT", 0x0097, 0x00002290),
        (24, "FOLDER", 0x0090, 0x00001490),
        (25, "DEFAULT", 0x00a1, 0x00001690),
        (26, "ALPHABET", 0x00a2, 0x00001890),
        (27, "MATCHING", 0x00aa, 0x00001890),
    ]
    for col_id, name, field_type, size_type in default_columns:
        rows.append(ColumnRow(column_id=col_id, name=name, field_type=field_type, size_type=size_type))

    # Generate page
    marshaller = ColumnsMarshaller()
    page_data = marshaller.marshal_page(34, 16, rows)

    # Compare with reference
    ref_path = Path('validation_data/empty_onelib_and_devicelib/PIONEER/rekordbox/export.pdb')
    if not ref_path.exists():
        print("⚠️  Reference file not found - skipping comparison")
        return None

    ref_data = ref_path.read_bytes()
    ref_page = ref_data[34*4096:(34+1)*4096]

    # Verify match
    if page_data == ref_page:
        print('✅ Columns page matches 100%')
        return True
    else:
        diff = sum(1 for a, b in zip(page_data, ref_page) if a != b)
        print(f'❌ Columns page has {diff} byte differences')

        # Show first difference
        for i, (a, b) in enumerate(zip(page_data, ref_page)):
            if a != b:
                print(f'  First diff at byte {i} (offset 0x{i:04x}): gen=0x{a:02x} ref=0x{b:02x}')
                break

        return False


def test_history_page():
    """Test History page (Page 40)."""
    print("\n=== Testing History Page (40) ===")

    # Create default row (1 entry)
    rows = [HistoryRow(date="2026-03-02", name="1000")]

    # Generate page
    marshaller = HistoryMarshaller()
    page_data = marshaller.marshal_page(40, 19, rows)

    # Compare with reference
    ref_path = Path('validation_data/empty_onelib_and_devicelib/PIONEER/rekordbox/export.pdb')
    if not ref_path.exists():
        print("⚠️  Reference file not found - skipping comparison")
        return None

    ref_data = ref_path.read_bytes()
    ref_page = ref_data[40*4096:(40+1)*4096]

    # Verify match
    if page_data == ref_page:
        print('✅ History page matches 100%')
        return True
    else:
        diff = sum(1 for a, b in zip(page_data, ref_page) if a != b)
        print(f'❌ History page has {diff} byte differences')

        # Show first difference
        for i, (a, b) in enumerate(zip(page_data, ref_page)):
            if a != b:
                print(f'  First diff at byte {i} (offset 0x{i:04x}): gen=0x{a:02x} ref=0x{b:02x}')
                break

        return False


def main():
    """Run all special page tests."""
    print("=" * 60)
    print("Special Page Marshallers - Individual Tests")
    print("=" * 60)

    results = {
        'Unknown17': test_unknown17_page(),
        'Unknown18': test_unknown18_page(),
        'Colors': test_colors_page(),
        'Columns': test_columns_page(),
        'History': test_history_page(),
    }

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for r in results.values() if r is True)
    failed = sum(1 for r in results.values() if r is False)
    skipped = sum(1 for r in results.values() if r is None)

    for name, result in results.items():
        if result is True:
            print(f"✅ {name}: PASS")
        elif result is False:
            print(f"❌ {name}: FAIL")
        else:
            print(f"⚠️  {name}: SKIP")

    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped")

    if failed == 0 and skipped == 0:
        print("\n🎉 All special pages match 100%!")
        return 0
    elif failed > 0:
        print(f"\n⚠️  {failed} page(s) have differences - need fixes")
        return 1
    else:
        print("\n⚠️  Some tests were skipped - check reference file")
        return 2


if __name__ == "__main__":
    sys.exit(main())
