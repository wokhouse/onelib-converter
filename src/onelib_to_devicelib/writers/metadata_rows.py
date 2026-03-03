"""
Metadata Row Structures for PDB Tables

Simple row structures for non-track tables (Genres, Artists, Albums, etc.)
Based on REX project (https://github.com/kimtore/rex) implementation.
"""

import struct
from dataclasses import dataclass
from .dstring import encode_device_sql_string


@dataclass
class GenreRow:
    """Genre table row (Table 1).

    Structure:
    - row_offset (2 bytes): Always 0x0A
    - index_shift (2 bytes): Row index shifted by 0x20
    - genre_id (4 bytes): Genre ID
    - name (DeviceSQL string): Genre name
    """

    genre_id: int
    name: str

    def marshal_binary(self, row_index: int) -> bytes:
        """Marshal row to binary format."""
        name_encoded = encode_device_sql_string(self.name)

        # Build row: [row_offset (2)] [index_shift (2)] [genre_id (4)] [name]
        row = bytearray()
        row.extend(struct.pack('<H', 0x0A))  # row_offset
        row.extend(struct.pack('<H', row_index & 0xFFFF))  # index_shift
        row.extend(struct.pack('<I', self.genre_id))  # genre_id
        row.extend(name_encoded)

        return bytes(row)


@dataclass
class ArtistRow:
    """Artist table row (Table 2).

    Structure:
    - row_offset (2 bytes): Always 0x0A
    - index_shift (2 bytes): Row index shifted by 0x20
    - artist_id (4 bytes): Artist ID
    - name (DeviceSQL string): Artist name
    """

    artist_id: int
    name: str

    def marshal_binary(self, row_index: int) -> bytes:
        """Marshal row to binary format."""
        name_encoded = encode_device_sql_string(self.name)

        # Build row: [row_offset (2)] [index_shift (2)] [artist_id (4)] [name]
        row = bytearray()
        row.extend(struct.pack('<H', 0x0A))  # row_offset
        row.extend(struct.pack('<H', row_index & 0xFFFF))  # index_shift
        row.extend(struct.pack('<I', self.artist_id))  # artist_id
        row.extend(name_encoded)

        return bytes(row)


@dataclass
class AlbumRow:
    """Album table row (Table 3).

    Structure:
    - row_offset (2 bytes): Always 0x0E
    - index_shift (2 bytes): Row index shifted by 0x20
    - album_id (4 bytes): Album ID
    - artist_id (4 bytes): Artist ID reference
    - unknown (4 bytes): Unknown field
    - name (DeviceSQL string): Album name
    """

    album_id: int
    name: str
    artist_id: int = 0

    def marshal_binary(self, row_index: int) -> bytes:
        """Marshal row to binary format."""
        name_encoded = encode_device_sql_string(self.name)

        # Build row: [row_offset (2)] [index_shift (2)] [album_id (4)] [artist_id (4)] [unknown (4)] [name]
        row = bytearray()
        row.extend(struct.pack('<H', 0x0E))  # row_offset
        row.extend(struct.pack('<H', row_index & 0xFFFF))  # index_shift
        row.extend(struct.pack('<I', self.album_id))  # album_id
        row.extend(struct.pack('<I', self.artist_id))  # artist_id
        row.extend(struct.pack('<I', 0))  # unknown
        row.extend(name_encoded)

        return bytes(row)


@dataclass
class LabelRow:
    """Label table row (Table 4).

    Structure:
    - row_offset (2 bytes): Always 0x0A
    - index_shift (2 bytes): Row index shifted by 0x20
    - label_id (4 bytes): Label ID
    - name (DeviceSQL string): Label name
    """

    label_id: int
    name: str

    def marshal_binary(self, row_index: int) -> bytes:
        """Marshal row to binary format."""
        name_encoded = encode_device_sql_string(self.name)

        # Build row: [row_offset (2)] [index_shift (2)] [label_id (4)] [name]
        row = bytearray()
        row.extend(struct.pack('<H', 0x0A))  # row_offset
        row.extend(struct.pack('<H', row_index & 0xFFFF))  # index_shift
        row.extend(struct.pack('<I', self.label_id))  # label_id
        row.extend(name_encoded)

        return bytes(row)


@dataclass
class KeyRow:
    """Key table row (Table 5).

    Structure:
    - row_offset (2 bytes): Always 0x0A
    - index_shift (2 bytes): Row index shifted by 0x20
    - key_id (4 bytes): Key ID
    - name (DeviceSQL string): Key name (e.g., "C maj", "A min")
    """

    key_id: int
    name: str

    def marshal_binary(self, row_index: int) -> bytes:
        """Marshal row to binary format."""
        name_encoded = encode_device_sql_string(self.name)

        # Build row: [row_offset (2)] [index_shift (2)] [key_id (4)] [name]
        row = bytearray()
        row.extend(struct.pack('<H', 0x0A))  # row_offset
        row.extend(struct.pack('<H', row_index & 0xFFFF))  # index_shift
        row.extend(struct.pack('<I', self.key_id))  # key_id
        row.extend(name_encoded)

        return bytes(row)


@dataclass
class ColorRow:
    """Color table row (Table 6).

    Structure:
    - row_offset (2 bytes): Always 0x12
    - index_shift (2 bytes): Row index shifted by 0x20
    - color_id (4 bytes): Color ID
    - color_rgb (4 bytes): RGB color value
    - unknown (4 bytes): Unknown field
    - name (DeviceSQL string): Color name
    """

    color_id: int
    name: str
    color_rgb: int = 0

    def marshal_binary(self, row_index: int) -> bytes:
        """Marshal row to binary format."""
        name_encoded = encode_device_sql_string(self.name)

        # Build row: [row_offset (2)] [index_shift (2)] [color_id (4)] [color_rgb (4)] [unknown (4)] [name]
        row = bytearray()
        row.extend(struct.pack('<H', 0x12))  # row_offset
        row.extend(struct.pack('<H', row_index & 0xFFFF))  # index_shift
        row.extend(struct.pack('<I', self.color_id))  # color_id
        row.extend(struct.pack('<I', self.color_rgb))  # color_rgb
        row.extend(struct.pack('<I', 0))  # unknown
        row.extend(name_encoded)

        return bytes(row)


@dataclass
class PlaylistTreeRow:
    """Playlist tree row (Table 7).

    Structure for folders and playlists in the playlist tree.

    Args:
        playlist_id: Playlist/folder ID
        name: Playlist/folder name
        parent_id: Parent folder ID (0 for root level)
        is_folder: True if this is a folder, False if playlist
        attribute: Additional attribute flags
        sequence_no: Sequence number for sorting
        image_id: Image ID for playlist artwork
        track_count: Number of tracks (for playlists only)
    """

    playlist_id: int
    name: str
    parent_id: int = 0
    is_folder: bool = False
    attribute: int = 0
    sequence_no: int = 0
    image_id: int = 0
    track_count: int = 0

    def marshal_binary(self, row_index: int) -> bytes:
        """Marshal row to binary format."""
        name_encoded = encode_device_sql_string(self.name)

        # Calculate attribute based on is_folder
        # From REX: folder = 0x100, playlist = 0x200
        if self.is_folder:
            attribute = self.attribute or 0x100
        else:
            attribute = self.attribute or 0x200

        # Build row based on REX playlist structure
        # [row_offset (2)] [index_shift (2)] [playlist_id (4)] [parent_id (4)]
        # [attribute (4)] [sequence_no (4)] [image_id (4)] [track_count (4)]
        # [unknown (4)] [name]
        row = bytearray()
        row.extend(struct.pack('<H', 0x26))  # row_offset (matches REX)
        row.extend(struct.pack('<H', row_index & 0xFFFF))  # index_shift
        row.extend(struct.pack('<I', self.playlist_id))  # playlist_id
        row.extend(struct.pack('<I', self.parent_id))  # parent_id
        row.extend(struct.pack('<I', attribute))  # attribute
        row.extend(struct.pack('<I', self.sequence_no))  # sequence_no
        row.extend(struct.pack('<I', self.image_id))  # image_id
        row.extend(struct.pack('<I', self.track_count))  # track_count
        row.extend(struct.pack('<I', 0))  # unknown
        row.extend(name_encoded)

        return bytes(row)


@dataclass
class PlaylistEntryRow:
    """Playlist entry row (Table 8).

    Structure linking tracks to playlists.

    Args:
        track_id: Track ID
        playlist_id: Playlist ID
        sequence_no: Sequence number within playlist (for sorting)
    """

    track_id: int
    playlist_id: int
    sequence_no: int

    def marshal_binary(self, row_index: int) -> bytes:
        """Marshal row to binary format."""
        # Build row based on REX playlist entry structure
        # [row_offset (2)] [index_shift (2)] [track_id (4)] [playlist_id (4)]
        # [sequence_no (4)] [unknown (4)] [unknown2 (4)]
        row = bytearray()
        row.extend(struct.pack('<H', 0x16))  # row_offset (matches REX)
        row.extend(struct.pack('<H', row_index & 0xFFFF))  # index_shift
        row.extend(struct.pack('<I', self.track_id))  # track_id
        row.extend(struct.pack('<I', self.playlist_id))  # playlist_id
        row.extend(struct.pack('<I', self.sequence_no))  # sequence_no
        row.extend(struct.pack('<I', 0))  # unknown
        row.extend(struct.pack('<I', 0))  # unknown2

        return bytes(row)
