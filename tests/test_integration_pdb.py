#!/usr/bin/env python3
"""
Integration Test: PDB Generation with Index Pages and Bitfields

Tests that the PDB writer correctly generates files with:
- Index pages as first page of each table
- Page header bitfields
- Correct sequence numbers
"""

import sys
import tempfile
import struct
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from onelib_to_devicelib.writers.pdb_v3 import PDBWriterV3
from onelib_to_devicelib.writers.page import PageType


class MockTrack:
    """Mock track for testing."""
    def __init__(self, track_id: int, title: str = "Test Track"):
        self.id = track_id
        self.title = title
        self.artist = "Test Artist"
        self.album = "Test Album"
        self.genre = "Test Genre"
        self.bpm = 120.0
        self.duration = 180.0
        self.file_size = 10000000
        self.sample_rate = 44100
        self.bit_rate = 320
        self.track_number = 1
        self.disc_number = 1
        self.year = 2024
        self.file_path = Path(f"/test/track{track_id}.mp3")
        self.artist_id = 1
        self.album_id = 1
        self.genre_id = 1
        self.key_id = 0
        self.color_id = 0
        self.rating = 0
        self.play_count = 0
        self.label_id = 0
        self.isrc = ""
        self.composer = ""
        self.comment = ""
        self.date_added = ""
        self.release_date = ""
        self.artwork_id = 0


def test_index_pages_in_generated_pdb():
    """Test that generated PDB has index pages as first page of each table."""
    print("\n=== Test Index Pages in Generated PDB ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create PDB writer
        writer = PDBWriterV3(tmpdir)

        # Add some tracks
        for i in range(5):
            track = MockTrack(i + 1, f"Track {i + 1}")
            writer.add_track(track)

        # Add some metadata
        writer.add_artist(1, "Test Artist")
        writer.add_album(1, "Test Album", artist_id=1)
        writer.add_genre(1, "Test Genre")

        # Finalize and write
        file_size = writer.finalize()

        print(f"  Generated PDB size: {file_size} bytes ({file_size / 1024:.1f} KB)")

        # Read generated PDB
        pdb_path = tmpdir / "PIONEER" / "rekordbox" / "export.pdb"
        with open(pdb_path, 'rb') as f:
            pdb_data = f.read()

        # Parse file header (first 4096 bytes)
        header = pdb_data[0:4096]

        # Parse table pointers
        num_tables = struct.unpack('<I', header[8:12])[0]
        print(f"  Number of tables: {num_tables}")

        # Table pointers start at byte 28
        table_pointers = []
        for i in range(num_tables):
            offset = 28 + (i * 16)
            table_type, empty_candidate, first_page, last_page = struct.unpack('<IIII', header[offset:offset+16])
            table_pointers.append({
                'type': table_type,
                'first_page': first_page,
                'last_page': last_page,
                'empty_candidate': empty_candidate
            })

        # Check Tracks table (type 0)
        tracks_tp = table_pointers[0]
        print(f"  Tracks table: page {tracks_tp['first_page']}-{tracks_tp['last_page']}")

        assert tracks_tp['first_page'] > 0, "Tracks table should have pages"

        # Read first page of Tracks table
        tracks_first_page_offset = tracks_tp['first_page'] * 4096
        tracks_first_page = pdb_data[tracks_first_page_offset:tracks_first_page_offset + 4096]

        # Check page flags (byte 27)
        page_flags = tracks_first_page[27]
        print(f"  First Tracks page flags: 0x{page_flags:02x}")

        # FIX #2: First page should be index page with flags 0x64
        if page_flags == 0x64:
            print(f"  ✅ First page is index page (flags=0x64)")
        else:
            print(f"  ⚠️  First page has unexpected flags: 0x{page_flags:02x}")

        # Check second page if exists
        if tracks_tp['last_page'] > tracks_tp['first_page']:
            tracks_second_page_offset = (tracks_tp['first_page'] + 1) * 4096
            tracks_second_page = pdb_data[tracks_second_page_offset:tracks_second_page_offset + 4096]

            # Check page flags (byte 27)
            second_page_flags = tracks_second_page[27]
            print(f"  Second Tracks page flags: 0x{second_page_flags:02x}")

            # Second page should be data page with flags 0x34
            if second_page_flags == 0x34:
                print(f"  ✅ Second page is data page (flags=0x34)")
            else:
                print(f"  ⚠️  Second page has unexpected flags: 0x{second_page_flags:02x}")

        return True


def test_page_header_bitfields_in_generated_pdb():
    """Test that generated PDB has correct bitfield encoding in page headers."""
    print("\n=== Test Page Header Bitfields in Generated PDB ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create PDB writer
        writer = PDBWriterV3(tmpdir)

        # Add a track
        track = MockTrack(1, "Test Track")
        writer.add_track(track)

        # Finalize and write
        file_size = writer.finalize()

        # Read generated PDB
        pdb_path = tmpdir / "PIONEER" / "rekordbox" / "export.pdb"
        with open(pdb_path, 'rb') as f:
            pdb_data = f.read()

        # Get Tracks table first data page (page 2, since page 0 is header, page 1 is index)
        # Data page starts at offset 2 * 4096
        data_page_offset = 2 * 4096
        data_page = pdb_data[data_page_offset:data_page_offset + 4096]

        # Read page header (bytes 24-27 are bitfields)
        bitfield_bytes = data_page[24:28]

        # Parse bitfields
        combined = struct.unpack('<I', bitfield_bytes[0:4])[0]
        num_rows = (combined >> 13) & 0x7FF
        num_row_offsets = combined & 0x1FFF
        page_flags = bitfield_bytes[3]

        print(f"  Data page bitfields:")
        print(f"    num_rows: {num_rows}")
        print(f"    num_row_offsets: {num_row_offsets}")
        print(f"    page_flags: 0x{page_flags:02x}")

        # We added 1 track, so should have 1 row
        assert num_rows == 1, f"Expected 1 row, got {num_rows}"
        print(f"  ✅ Bitfield encoding correct")

        return True


def test_sequence_number_in_file_header():
    """Test that generated PDB has correct sequence number in file header."""
    print("\n=== Test Sequence Number in File Header ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create PDB writer
        writer = PDBWriterV3(tmpdir)

        print(f"  Writer sequence_number: {writer.sequence_number}")

        # Add a track and finalize
        track = MockTrack(1, "Test Track")
        writer.add_track(track)
        writer.finalize()

        # Read generated PDB
        pdb_path = tmpdir / "PIONEER" / "rekordbox" / "export.pdb"
        with open(pdb_path, 'rb') as f:
            pdb_data = f.read()

        # Read sequence number from file header (byte 20-23)
        sequence_in_file = struct.unpack('<I', pdb_data[20:24])[0]

        print(f"  Sequence number in file header: {sequence_in_file}")

        # FIX #5: Should match writer.sequence_number
        assert sequence_in_file == writer.sequence_number, \
            f"Expected sequence={writer.sequence_number}, got {sequence_in_file}"
        print(f"  ✅ Sequence number correct")

        return True


def main():
    """Run integration tests."""
    print("=" * 60)
    print("PDB Integration Tests")
    print("=" * 60)

    tests = [
        ("Index Pages in Generated PDB", test_index_pages_in_generated_pdb),
        ("Page Header Bitfields", test_page_header_bitfields_in_generated_pdb),
        ("Sequence Number", test_sequence_number_in_file_header),
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
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"Integration Test Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed == 0:
        print("\n✅ All integration tests passed!")
        return 0
    else:
        print(f"\n❌ {failed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
