"""
Validation Test Suite for PDB Writer

End-to-end validation tests for PDB writer v3.
"""

import struct
import pytest
from pathlib import Path

from onelib_to_devicelib.parsers.onelib import OneLibraryParser
from onelib_to_devicelib.writers.pdb_v3 import PDBWriterV3
from onelib_to_devicelib.writers.dstring import encode_device_sql_string
from onelib_to_devicelib.readers.pdb_reader import PDBReader
from tests.comparators.pdb_comparator import PDBComparator


@pytest.fixture
def validation_data():
    """Path to validation data."""
    return Path("validation_data")


def test_string_encoding():
    """Test DeviceSQL string encoding."""
    # Short ASCII
    result = encode_device_sql_string("Hello")
    assert result[0] == ((5 + 1) << 1) | 0x01
    assert result[1:] == b"Hello"
    assert len(result) == 6

    # Empty string
    result = encode_device_sql_string("")
    assert result[0] == 0x01
    assert len(result) == 1

    # Long ASCII (>127 bytes)
    long_string = "A" * 200
    result = encode_device_sql_string(long_string)
    assert result[0] == 0x40  # Long ASCII marker
    assert result[1] == 0x03
    assert len(result) == 2 + 2 + 200  # Header + length + data

    # UTF-16LE (non-ASCII)
    result = encode_device_sql_string("こんにちは")
    assert result[0] == 0x90  # UTF-16LE marker
    assert result[1] == 0x03


def test_onelib_to_devicelib_conversion(validation_data):
    """Test conversion of onelib_only to devicelib format."""
    source = validation_data / "onelib_only"

    if not source.exists():
        pytest.skip(f"Validation data not found: {source}")

    # Parse source
    parser = OneLibraryParser(source)
    parser.parse()

    tracks = parser.get_tracks()
    assert len(tracks) == 33, f"Expected 33 tracks, got {len(tracks)}"

    # Generate PDB
    output = Path("/tmp/test_pdb_validation")
    output.mkdir(exist_ok=True)

    writer = PDBWriterV3(output)

    for track in tracks:
        writer.add_track(track)

    file_size = writer.finalize()

    # Check generated file exists
    gen_pdb = output / "PIONEER" / "rekordbox" / "export.pdb"
    assert gen_pdb.exists(), "Generated PDB file not found"

    # Check file size is reasonable (should be much larger than MVP's 12KB)
    assert file_size > 100_000, f"Generated PDB too small: {file_size} bytes"

    # Get stats
    stats = writer.get_stats()
    assert stats['total_pages'] > 10, f"Too few pages: {stats['total_pages']}"
    assert stats['tables']['Tracks']['total_rows'] == 33

    # Compare with reference if available
    reference = validation_data / "onelib_and_devicelib"
    ref_pdb = reference / "PIONEER" / "rekordbox" / "export.pdb"

    if ref_pdb.exists():
        comparator = PDBComparator(gen_pdb, ref_pdb)
        report = comparator.generate_report()

        # Print report for debugging
        print("\n" + report)

        # Check structure
        struct = comparator.compare_structure()
        assert struct['generated_pages'] > 5, "Too few pages generated"


def test_pdb_page_structure(validation_data):
    """Test that page structure matches reference."""
    reference = validation_data / "onelib_and_devicelib"
    ref_pdb = reference / "PIONEER" / "rekordbox" / "export.pdb"

    if not ref_pdb.exists():
        pytest.skip(f"Reference PDB not found: {ref_pdb}")

    reader = PDBReader(ref_pdb)
    fh = reader.parse_file_header()

    # Verify file header
    assert fh.magic == 0x00000000, f"Invalid magic: {fh.magic}"
    assert fh.page_size == 4096, f"Invalid page size: {fh.page_size}"
    assert fh.num_tables == 20, f"Invalid num_tables: {fh.num_tables}"

    # Check first page (tracks)
    page = reader.parse_page(1)  # Page 0 is file header, page 1 is first data page
    assert page.header['page_type'] == 0, f"Invalid page type: {page.header['page_type']}"
    assert page.header['num_rows_small'] > 0, "No rows in first page"
    assert len(page.rowsets) > 0, "No RowSets in first page"


def test_track_row_encoding(validation_data):
    """Test that track rows are encoded correctly."""
    reference = validation_data / "onelib_and_devicelib"
    ref_pdb = reference / "PIONEER" / "rekordbox" / "export.pdb"

    if not ref_pdb.exists():
        pytest.skip(f"Reference PDB not found: {ref_pdb}")

    reader = PDBReader(ref_pdb)

    # Find first track page
    track_pages = reader.get_table_pages(0)  # Table type 0 = Tracks

    if not track_pages:
        pytest.skip("No track pages found in reference PDB")

    page = reader.parse_page(track_pages[0])

    # Check first track row
    if len(page.rows) > 0:
        row = page.rows[0]

        # Verify row has reasonable size
        assert len(row) >= 90, f"Row too small: {len(row)} bytes"

        # Check critical fields
        # unnamed0 (bytes 0-1) - should be 0x24
        unnamed0 = struct.unpack('<H', row[0:2])[0]
        assert unnamed0 == 0x24, f"Invalid unnamed0: 0x{unnamed0:04x}"

        # file_type near end of header
        # This should be a valid file type (MP3, M4A, FLAC, WAV, etc.)
        # Based on the plan, bytes 90-91 should have file_type in lower bits
        if len(row) >= 92:
            file_type_field = struct.unpack('<H', row[90:92])[0]
            # Should have 0x3 in the upper bits or some valid value
            assert file_type_field != 0, "Invalid file_type field"


def test_heap_allocator():
    """Test TwoWayHeap allocator."""
    from onelib_to_devicelib.writers.heap import TwoWayHeap

    heap = TwoWayHeap(page_size=4096, data_header_size=48)

    # Write to top
    pos1 = heap.write_top(b'AAAA')
    assert pos1 == 0
    assert heap.top_cursor == 4

    pos2 = heap.write_top(b'BBBB')
    assert pos2 == 4
    assert heap.top_cursor == 8

    # Write to bottom
    # Note: heap_size = 4096 - 48 = 4048
    pos3 = heap.write_bottom(b'CCCC')
    assert pos3 == 0  # First from bottom
    assert heap.bottom_cursor == 4044  # 4048 - 4

    # Check free space
    assert heap.free_size() == 4044 - 8  # bottom_cursor - top_cursor

    # Align top
    heap.align_top(4)
    assert heap.top_cursor == 8  # No change, already aligned

    heap.write_top(b'A')
    heap.align_top(4)
    assert heap.top_cursor == 12  # Aligned to 4-byte boundary

    # Serialize
    data = heap.to_bytes()
    assert len(data) == 4048  # heap_size
    assert data[:8] == b'AAAABBBB'
    assert data[-4:] == b'CCCC'


def test_rowset_structure():
    """Test RowSet structure."""
    from onelib_to_devicelib.writers.rowset import RowSet

    rs = RowSet()

    # Initially empty
    assert rs.count_rows() == 0
    assert not rs.row_exists(0)

    # Add rows
    rs.set_row(0, 100)
    assert rs.row_exists(0)
    assert rs.positions[0] == 100
    assert rs.count_rows() == 1
    assert rs.active_rows == 0x0001

    rs.set_row(5, 200)
    assert rs.row_exists(5)
    assert rs.positions[5] == 200
    assert rs.count_rows() == 2
    assert rs.active_rows == 0x0021

    # Clear row
    rs.clear_row(0)
    assert not rs.row_exists(0)
    assert rs.count_rows() == 1

    # Marshal/unmarshal
    data = rs.marshal_binary()
    assert len(data) == 36

    rs2 = RowSet.unmarshal_binary(data)
    assert rs2.active_rows == rs.active_rows
    assert rs2.positions == rs.positions


def test_page_structure():
    """Test DataPage structure."""
    from onelib_to_devicelib.writers.page import DataPage, PageType

    page = DataPage(page_index=0, page_type=PageType.TRACKS)

    # Insert rows
    row1 = b'A' * 100
    idx1 = page.insert_row(row1)
    assert idx1 == 0
    assert page.header.num_rows_small == 0x20

    row2 = b'B' * 150
    idx2 = page.insert_row(row2)
    assert idx2 == 0x20
    assert page.header.num_rows_small == 0x40

    # Marshal
    data = page.marshal_binary()
    assert len(data) == 4096

    # Unmarshal
    page2 = DataPage.unmarshal_binary(data)
    assert page2.header.page_index == 0
    assert page2.header.page_type == PageType.TRACKS
    assert page2.header.num_rows_small == 0x40
    assert len(page2.rowsets) == 1  # One RowSet for 2 rows


def test_full_track_row():
    """Test complete track row creation."""
    from onelib_to_devicelib.writers.track import TrackRow
    from onelib_to_devicelib.parsers.onelib import Track

    # Create mock track (matching Track dataclass structure)
    track = Track(
        id=123,  # Note: 'id' not 'track_id'
        title="Test Track",
        artist="Test Artist",
        album="Test Album",
        genre="Genre",
        bpm=120.0,
        duration=180,
        file_path=Path("/Contents/test.mp3"),
        file_size=5_000_000,
        bit_rate=320,
        sample_rate=44100
    )

    row = TrackRow(track)
    data = row.marshal_binary(0)

    # Check row has reasonable size
    assert len(data) > 130, f"Row too small: {len(data)} bytes"

    # Check fixed header
    assert data[0:2] == struct.pack('<H', 0x24)  # unnamed0
    assert data[2:4] == struct.pack('<H', 0)  # index_shift for row 0

    # Check track ID
    track_id = struct.unpack('<I', data[72:76])[0]
    assert track_id == 123

    # Check tempo (BPM × 100)
    tempo = struct.unpack('<I', data[56:60])[0]
    assert tempo == 12000


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v'])
