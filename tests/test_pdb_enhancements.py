#!/usr/bin/env python3
"""Test PDB writer enhancements."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from onelib_to_devicelib.writers.pdb import PDBWriter, TrackRow


def test_track_row_structure():
    """Test that TrackRow has all required fields."""
    print("Testing TrackRow structure...")

    # Create a track row with all fields
    track = TrackRow(
        track_id=12345,
        title="Test Track",
        artist="Test Artist",
        album="Test Album",
        genre="Test Genre",
        bpm=12800,  # 128.00 BPM * 100
        duration=180000,  # 3 minutes in ms
        file_path="/Music/test.mp3",
        file_size=10485760,  # 10 MB
        bit_rate=320,
        sample_rate=44100,
        bit_depth=16,
        track_number=5,
        disc_number=1,
        rating=4,
        play_count=10,
        artwork_id=999,
        date_added=1640000000,
        date_created=1640000000,
        date_modified=1640000000,
        analyzed=True,
        has_waveform=True,
        has_beat_grid=True,
        has_cues=True
    )

    print(f"✓ Created TrackRow with {len(track.__dict__)} fields")

    # Verify fields are set correctly
    assert track.track_id == 12345
    assert track.bpm == 12800
    assert track.duration == 180000
    assert track.file_path == "/Music/test.mp3"
    assert track.file_size == 10485760
    assert track.bit_rate == 320
    assert track.sample_rate == 44100
    assert track.rating == 4
    assert track.play_count == 10
    assert track.artwork_id == 999
    assert track.analyzed == True
    assert track.has_waveform == True

    print("✓ All fields correctly set")


def test_pdb_writer_with_enhanced_rows():
    """Test PDBWriter with enhanced TrackRow structure."""
    print("\nTesting PDBWriter with enhanced rows...")

    import tempfile
    import shutil

    # Create temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        writer = PDBWriter(Path(tmpdir))

        # Add test tracks with all fields
        for i in range(5):
            track = TrackRow(
                track_id=1000 + i,
                title=f"Track {i}",
                artist=f"Artist {i}",
                album=f"Album {i}",
                genre=f"Genre {i}",
                bpm=12000 + (i * 100),
                duration=180000 + (i * 10000),
                file_path=f"/Music/track{i}.mp3",
                file_size=10000000 + (i * 1000000),
                bit_rate=320,
                sample_rate=44100,
                rating=i % 6,
                play_count=i * 5,
                artwork_id=100 + i if i > 0 else None,
                analyzed=True,
                has_waveform=True
            )
            writer.tracks.append(track)

        print(f"✓ Added {len(writer.tracks)} test tracks")

        # Write PDB file
        writer.write()

        # Check that PDB file was created
        pdb_file = Path(tmpdir) / "PIONEER" / "rekordbox" / "export.pdb"
        assert pdb_file.exists(), "PDB file not created"
        print(f"✓ PDB file created: {pdb_file}")

        # Check file size (should be larger than before due to expanded rows)
        file_size = pdb_file.stat().st_size
        print(f"✓ PDB file size: {file_size} bytes")

        # With 200-byte rows vs 88-byte rows, file should be significantly larger
        # 5 tracks * 200 bytes = 1000 bytes of row data + headers
        assert file_size > 5000, f"PDB file too small: {file_size} bytes"
        print("✓ PDB file size looks reasonable for expanded rows")


def test_row_serialization():
    """Test that rows are serialized correctly."""
    print("\nTesting row serialization...")

    writer = PDBWriter(Path("/tmp/test"))

    # Create a test track
    track = TrackRow(
        track_id=1,
        title="Test Title",
        artist="Test Artist",
        album="Test Album",
        genre="Test Genre",
        bpm=12800,
        duration=180000,
        file_path="/Music/test.mp3",
        file_size=10000000,
        bit_rate=320,
        sample_rate=44100
    )

    # Add strings to heap in the correct order (matching Deep-Symmetry spec)
    artist_offset = writer._add_string_to_heap(track.artist)
    title_offset = writer._add_string_to_heap(track.title)
    album_offset = writer._add_string_to_heap(track.album)
    genre_offset = writer._add_string_to_heap(track.genre)
    path_offset = writer._add_string_to_heap(track.file_path)

    print(f"  String offsets: title={title_offset}, artist={artist_offset}, album={album_offset}, genre={genre_offset}, path={path_offset}")

    string_offsets = {
        'artist': artist_offset,
        'title': title_offset,
        'album': album_offset,
        'genre': genre_offset,
        'file_path': path_offset
    }

    # Write row
    row_data = writer._write_track_row(track, string_offsets)

    # Verify row size (should be 200 bytes now)
    assert len(row_data) == 200, f"Row size incorrect: {len(row_data)} (expected 200)"
    print(f"✓ Row size: {len(row_data)} bytes")

    # Verify key fields are in the row
    import struct
    track_id = struct.unpack('<I', row_data[4:8])[0]
    assert track_id == 1, f"Track ID incorrect: {track_id}"
    print(f"✓ Track ID correctly serialized: {track_id}")

    # Check string offsets (at their correct positions in the row)
    # Offsets per the row structure:
    # 8: artist, 12: title, 16: album, 20: genre, 24: file_path
    artist_off = struct.unpack('<I', row_data[8:12])[0]
    title_off = struct.unpack('<I', row_data[12:16])[0]
    album_off = struct.unpack('<I', row_data[16:20])[0]
    genre_off = struct.unpack('<I', row_data[20:24])[0]
    path_off = struct.unpack('<I', row_data[24:28])[0]

    print(f"  Serialized offsets:")
    print(f"    Artist: {artist_off} (expected {artist_offset})")
    print(f"    Title: {title_off} (expected {title_offset})")
    print(f"    Album: {album_off} (expected {album_offset})")
    print(f"    Genre: {genre_off} (expected {genre_offset})")
    print(f"    Path: {path_off} (expected {path_offset})")

    assert artist_off == artist_offset, f"Artist offset mismatch: {artist_off} != {artist_offset}"
    assert title_off == title_offset, f"Title offset mismatch: {title_off} != {title_offset}"
    assert album_off == album_offset, f"Album offset mismatch: {album_off} != {album_offset}"
    assert genre_off == genre_offset, f"Genre offset mismatch: {genre_off} != {genre_offset}"
    assert path_off == path_offset, f"Path offset mismatch: {path_off} != {path_offset}"

    print(f"✓ String offsets correctly serialized")

    # Check file metadata
    bpm = struct.unpack('<H', row_data[28:30])[0]
    duration = struct.unpack('<I', row_data[30:34])[0]
    file_size = struct.unpack('<I', row_data[34:38])[0]
    bit_rate = struct.unpack('<H', row_data[38:40])[0]
    sample_rate = struct.unpack('<H', row_data[40:42])[0]

    assert bpm == 12800, f"BPM incorrect: {bpm}"
    assert duration == 180000, f"Duration incorrect: {duration}"
    assert file_size == 10000000, f"File size incorrect: {file_size}"
    assert bit_rate == 320, f"Bit rate incorrect: {bit_rate}"
    assert sample_rate == 44100, f"Sample rate incorrect: {sample_rate}"

    print(f"✓ File metadata correctly serialized:")
    print(f"  BPM: {bpm / 100:.2f}")
    print(f"  Duration: {duration / 1000:.1f}s")
    print(f"  File size: {file_size} bytes")
    print(f"  Bit rate: {bit_rate} kbps")
    print(f"  Sample rate: {sample_rate} Hz")


def main():
    """Run all tests."""
    print("=" * 60)
    print("PDB Writer Enhancement Tests")
    print("=" * 60)

    try:
        test_track_row_structure()
        test_pdb_writer_with_enhanced_rows()
        test_row_serialization()

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
