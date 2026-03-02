"""
Tests for the converter functionality.
"""

import pytest
from pathlib import Path

from onelib_to_devicelib.convert import Converter
from onelib_to_devicelib.utils.paths import get_anlz_path_hash


def test_get_pioneer_path():
    """Test Pioneer path resolution."""
    from onelib_to_devicelib.utils.paths import get_pioneer_path

    base = Path("/test/usb")
    pioneer_path = get_pioneer_path(base)

    assert pioneer_path == Path("/test/usb/PIONEER")


def test_anlz_path_hash():
    """Test ANLZ path hash generation."""
    path = Path("/Contents/Artist/Album/track.mp3")
    hash_val = get_anlz_path_hash(path)

    assert len(hash_val) == 8
    assert hash_val.isupper()
    assert all(c in "0123456789ABCDEF" for c in hash_val)


def test_anlz_path_hash_consistent():
    """Test that hash is consistent for same path."""
    path = Path("/Contents/Artist/Album/track.mp3")
    hash1 = get_anlz_path_hash(path)
    hash2 = get_anlz_path_hash(path)

    assert hash1 == hash2


@pytest.mark.skipif(
    not Path("validation_data/onelib_only").exists(),
    reason="Validation data not available"
)
def test_converter_initialization():
    """Test converter initialization with validation data."""
    source = Path("validation_data/onelib_only")

    converter = Converter(source)

    assert converter.source_path == source
    assert converter.output_path == source
    assert converter.pioneer_path.exists()


@pytest.mark.skipif(
    not Path("validation_data/onelib_only").exists(),
    reason="Validation data not available"
)
def test_parse_onelib():
    """Test parsing OneLibrary database."""
    source = Path("validation_data/onelib_only")

    converter = Converter(source)

    # Parse should succeed
    parser = converter.parse()

    # Should have tracks
    tracks = parser.get_tracks()
    assert len(tracks) > 0

    # Should have playlists
    playlists = parser.get_playlists()
    assert len(playlists) >= 0  # May be empty


@pytest.mark.skipif(
    not Path("validation_data/onelib_only").exists(),
    reason="Validation data not available"
)
def test_converter_dry_run():
    """Test converter without actual file writing."""
    source = Path("validation_data/onelib_only")
    output = Path("/tmp/test_output")

    converter = Converter(source, output)
    converter.parse()

    # Just verify parsing works - don't actually convert
    parser = converter.parser
    assert len(parser.get_tracks()) > 0
