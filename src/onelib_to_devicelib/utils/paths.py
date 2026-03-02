"""
Path utilities for OneLibrary and Device Library structures.
"""

import hashlib
from pathlib import Path


def get_pioneer_path(base_path: Path) -> Path:
    """
    Get the PIONEER directory path.

    Args:
        base_path: Base path of the USB drive

    Returns:
        Path to PIONEER directory
    """
    return Path(base_path) / "PIONEER"


def get_anlz_path_hash(file_path: Path) -> str:
    """
    Generate the 8-character hash used in ANLZ directory names.

    The hash is derived from the track's file path.

    Args:
        file_path: Path to the audio file

    Returns:
        8-character hexadecimal string

    Example:
        >>> get_anlz_path_hash(Path("/Contents/Artist/Album/track.mp3"))
        'a1b2c3d4'
    """
    path_str = str(file_path).encode("utf-8")

    # The exact hashing algorithm is not fully documented
    # This is a placeholder using a simple hash
    hash_val = hashlib.md5(path_str).hexdigest()[:8].upper()

    return hash_val


def get_artwork_path(artwork_id: int, pioneer_path: Path) -> Path:
    """
    Get the path to an artwork file.

    Args:
        artwork_id: Artwork ID from database
        pioneer_path: Path to PIONEER directory

    Returns:
        Path to artwork file
    """
    # Artwork is organized in numbered directories
    dir_num = (artwork_id // 100) + 1
    artwork_dir = pioneer_path / "Artwork" / f"{dir_num:05d}"

    return artwork_dir / f"b{artwork_id % 100}.jpg"


def get_thumbnail_path(artwork_path: Path) -> Path:
    """
    Get the thumbnail path for an artwork file.

    Args:
        artwork_path: Path to original artwork

    Returns:
        Path to thumbnail file
    """
    stem = artwork_path.stem
    return artwork_path.parent / f"{stem}_m.jpg"
