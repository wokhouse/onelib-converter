#!/usr/bin/env python3
"""
Test PDB Format Fixes

Tests for the critical PDB format fixes to achieve REX compliance.
"""

import sys
import struct
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from onelib_to_devicelib.writers.page import PageHeader, IndexPage
from onelib_to_devicelib.writers.rowset import RowSet


def test_page_header_bitfields():
    """Test page header bitfield packing (FIX #1)."""
    print("\n=== Test Page Header Bitfields (FIX #1) ===")

    header = PageHeader(page_index=1, page_type=0)
    header.num_rows_small = 0x20 * 5  # 5 rows (increments by 0x20 per row)

    # Pack bitfields
    bitfield_bytes = header.pack_bitfields()

    print(f"  num_rows_small: 0x{header.num_rows_small:x} (5 rows)")
    print(f"  Bitfield bytes: {bitfield_bytes.hex()}")

    # Verify: should have num_rows = 5
    combined = struct.unpack('<I', bitfield_bytes[0:4])[0]
    num_rows = (combined >> 13) & 0x7FF
    num_row_offsets = combined & 0x1FFF

    print(f"  Extracted num_rows: {num_rows}")
    print(f"  Extracted num_row_offsets: {num_row_offsets}")
    print(f"  Page flags: 0x{bitfield_bytes[3]:02x}")

    assert num_rows == 5, f"Expected 5 rows, got {num_rows}"
    assert num_row_offsets == 5, f"Expected 5 row_offsets, got {num_row_offsets}"
    assert bitfield_bytes[3] == 0x34, f"Expected page_flags=0x34, got 0x{bitfield_bytes[3]:02x}"

    print("  ✅ Page header bitfields working correctly")
    return True


def test_index_page_creation():
    """Test index page creation (FIX #2)."""
    print("\n=== Test Index Page Creation (FIX #2) ===")

    index_page = IndexPage(page_index=1, page_type=0)
    index_page.add_entry(2)  # Point to data page 2
    index_page.add_entry(3)  # Point to data page 3

    print(f"  Created IndexPage with {len(index_page.index_entries)} entries")

    page_data = index_page.marshal_binary()

    print(f"  Page size: {len(page_data)} bytes")

    # Verify page flags (byte 27 in page header, after bitfields)
    # Page header structure:
    # Bytes 0-15: First 16 bytes (magic, page_index, page_type, next_page)
    # Bytes 16-23: Second 8 bytes (transaction, unknown2)
    # Bytes 24-27: Bitfields (3 bytes) + page_flags (1 byte) = 4 bytes
    # So page_flags is at byte 27 (16 + 8 + 3)
    page_flags = page_data[27]
    print(f"  Page flags (byte 27): 0x{page_flags:02x}")

    assert len(page_data) == 4096, f"Expected 4096 bytes, got {len(page_data)}"
    assert page_flags == 0x64, f"Expected page_flags=0x64, got 0x{page_flags:02x}"

    print("  ✅ Index page creation working correctly")
    return True


def test_rowset_reverse_order():
    """Test RowSet reverse order marshaling (FIX #3)."""
    print("\n=== Test RowSet Reverse Order (FIX #3) ===")

    rowset = RowSet()
    rowset.set_row(0, 100)  # Position 100 for row 0
    rowset.set_row(15, 200)  # Position 200 for row 15

    print(f"  Created RowSet with positions[0]=100, positions[15]=200")

    data = rowset.marshal_binary()

    print(f"  Marshaled size: {len(data)} bytes")

    # First 2 bytes should be position[15] (reversed order)
    pos_15 = struct.unpack('<H', data[0:2])[0]
    print(f"  First uint16 (position[15]): {pos_15}")

    # Last position (before flags) should be position[0]
    pos_0 = struct.unpack('<H', data[30:32])[0]
    print(f"  Last uint16 (position[0]): {pos_0}")

    assert pos_15 == 200, f"Expected position[15]=200, got {pos_15}"
    assert pos_0 == 100, f"Expected position[0]=100, got {pos_0}"

    print("  ✅ RowSet reverse order working correctly")
    return True


def test_sequence_number_incrementing():
    """Test sequence number incrementing (FIX #5)."""
    print("\n=== Test Sequence Number Incrementing (FIX #5) ===")

    from onelib_to_devicelib.writers.pdb_v3 import PDBWriterV3
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        writer = PDBWriterV3(Path(tmpdir))

        print(f"  Initial sequence_number: {writer.sequence_number}")

        # Sequence number should start at 1
        assert writer.sequence_number == 1, f"Expected sequence_number=1, got {writer.sequence_number}"

        # Add a track to test
        from onelib_to_devicelib.parsers.onelib import OneLibraryParser

        # Create minimal track object
        class MockTrack:
            def __init__(self):
                self.id = 1
                self.title = "Test Track"
                self.artist = "Test Artist"
                self.album = "Test Album"
                self.genre = "Test Genre"
                self.bpm = 120
                self.duration = 180
                self.file_size = 10000000
                self.sample_rate = 44100
                self.bit_rate = 320
                self.track_number = 1
                self.disc_number = 1
                self.year = 2024
                self.file_path = Path("/test/path.mp3")

        track = MockTrack()
        writer.add_track(track)

        # Finalize to build file header
        writer.finalize()

        print(f"  Final sequence_number: {writer.sequence_number}")
        print("  ✅ Sequence number incrementing working correctly")

    return True


def test_critical_constants():
    """Test critical constants (FIX #6)."""
    print("\n=== Test Critical Constants (FIX #6) ===")

    from onelib_to_devicelib.writers.track import TrackHeader, TrackRow

    # Create TrackHeader and verify critical constants
    header = TrackHeader()

    print(f"  unnamed0 (row_offset): 0x{header.row_offset:04x}")
    print(f"  unnamed26: 0x{header.unnamed26:04x}")
    print(f"  unnamed30: 0x{header.unnamed30:04x}")
    print(f"  bitmask: 0x{header.bitmask:x}")

    # Verify critical constants
    assert header.row_offset == 0x24, f"Expected row_offset=0x24, got 0x{header.row_offset:04x}"
    assert header.unnamed26 == 0x29, f"Expected unnamed26=0x29, got 0x{header.unnamed26:04x}"
    assert header.unnamed30 == 0x3, f"Expected unnamed30=0x3, got 0x{header.unnamed30:04x}"
    assert header.bitmask == 0xC0700, f"Expected bitmask=0xC0700, got 0x{header.bitmask:x}"

    print("  ✅ All critical constants verified")
    return True


def test_string_encoding():
    """Test DeviceSQL string encoding (FIX #4)."""
    print("\n=== Test DeviceSQL String Encoding (FIX #4) ===")

    from onelib_to_devicelib.writers.dstring import encode_device_sql_string

    # Test short ASCII
    encoded = encode_device_sql_string("Hello")
    print(f"  Short ASCII 'Hello': {encoded.hex()}")
    assert encoded[0] & 0x01, "Short ASCII should have bit 0 set"

    # Test long ASCII
    long_string = "x" * 200
    encoded = encode_device_sql_string(long_string)
    print(f"  Long ASCII (200 chars): {encoded[:4].hex()}...")
    assert encoded[0] == 0x40, "Long ASCII should start with 0x40"

    # Test UTF-16LE
    encoded = encode_device_sql_string("Hello 世界")
    print(f"  UTF-16LE 'Hello 世界': {encoded[:4].hex()}...")
    assert encoded[0] == 0x90, "UTF-16LE should start with 0x90"

    # Test empty string
    encoded = encode_device_sql_string("")
    print(f"  Empty string: {encoded.hex()}")
    assert encoded == b'\x01', "Empty string should be 0x01"

    print("  ✅ DeviceSQL string encoding working correctly")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("PDB Format Fixes Test Suite")
    print("=" * 60)

    tests = [
        ("Page Header Bitfields", test_page_header_bitfields),
        ("Index Page Creation", test_index_page_creation),
        ("RowSet Reverse Order", test_rowset_reverse_order),
        ("Sequence Number Incrementing", test_sequence_number_incrementing),
        ("Critical Constants", test_critical_constants),
        ("String Encoding", test_string_encoding),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"  ❌ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed == 0:
        print("\n✅ All tests passed!")
        return 0
    else:
        print(f"\n❌ {failed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
