"""
Metadata Row Structures for PDB Tables

Simple row structures for non-track tables (Genres, Artists, Albums, etc.)
Based on REX project (https://github.com/kimtore/rex) implementation.
"""

import struct
from dataclasses import dataclass
from .dstring import encode_device_sql_string


def encode_pdb_string(s: str) -> bytes:
    """
    Encode string for PDB format (for COLORS, HISTORY tables).

    Format: [length_marker][ascii_string][padding]
    length_marker = strlen(s) * 2 + 3

    Args:
        s: String to encode (ASCII only)

    Returns:
        Encoded bytes
    """
    name_bytes = s.encode('ascii')
    length_marker = len(name_bytes) * 2 + 3
    padding_len = length_marker - len(name_bytes) - 1
    return bytes([length_marker]) + name_bytes + b'\x00' * padding_len


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

    CORRECTED STRUCTURE (from reference Page 12 analysis):
    - str_marker (1 byte): Always 0x07 for 2-char keys
    - char1 (1 byte): First character (e.g., 'C' for "Cm")
    - char2 (1 byte): Second character (e.g., 'm' for "Cm")
    - null (1 byte): 0x00 terminator
    - key_id (4 bytes): Key ID
    - key_id_dup (4 bytes): DUPLICATE of key_id (unknown purpose)

    Total: EXACTLY 12 bytes (fixed length)
    """

    key_id: int
    name: str  # Will be converted to 2-character format

    def _convert_to_2char_format(self, name: str) -> tuple:
        """Convert key name to 2-character format.

        Converts from:
        - "C maj" -> "C" + " " (note + space for major)
        - "C min" -> "C" + "m" (note + 'm' for minor)
        - "C# maj" -> "C" + "#" (note + '#' for sharp major)
        - "C# min" -> "#" + "m" (sharp '#' + 'm' for sharp minor)

        Reference format uses 2 chars: note (or sharp) + modifier.
        """
        if not isinstance(name, str):
            return ' ', ' '

        # Handle major keys
        if 'maj' in name:
            # Extract note (handles C, C#, Db, etc.)
            name = name.strip()
            if '#' in name:
                # Sharp major: "C# maj" -> "#" + " "
                return '#', ' '
            elif 'b' in name:
                # Flat major: "Db maj" -> "Db" but we only have 2 chars...
                # Reference uses "b" for flats? Let's use first 2 chars
                return name[0], name[1] if len(name) > 1 else ' '
            else:
                # Natural major: "C maj" -> "C" + " "
                return name[0], ' '

        # Handle minor keys
        elif 'min' in name:
            name = name.strip()
            if '#' in name:
                # Sharp minor: "C# min" -> "#" + "m"
                return '#', 'm'
            elif 'b' in name:
                # Flat minor: "Db min" -> first 2 chars
                return name[0], name[1] if len(name) > 1 else 'm'
            else:
                # Natural minor: "C min" -> "C" + "m"
                return name[0], 'm'

        # Fallback: take first 2 chars
        return name[0] if len(name) > 0 else ' ', name[1] if len(name) > 1 else ' '

    def marshal_binary(self, row_index: int) -> bytes:
        """Marshal key as 12-byte fixed entry."""
        # Convert to 2-character format
        char1, char2 = self._convert_to_2char_format(self.name)

        # Build 12-byte entry in CORRECT ORDER:
        # [str_marker (1)] [char1 (1)] [char2 (1)] [null (1)] [key_id (4)] [key_id_dup (4)]
        row = struct.pack('<B', 0x07)  # str_marker for 2-char string
        row += char1.encode('ascii')
        row += char2.encode('ascii')
        row += b'\x00'  # null terminator
        row += struct.pack('<II', self.key_id, self.key_id)  # key_id + dup

        assert len(row) == 12, f"KeyRow must be exactly 12 bytes, got {len(row)}"
        return row


@dataclass
class ColorRow:
    """Color table row (Table 6).

    SIMPLE STRUCTURE (from reference Page 14 analysis):
    - length_marker (1 byte): Total entry length (1 + strlen + 1 + padding + 4)
    - name (N bytes): ASCII string + null terminator
    - padding (P bytes): Zeros to align
    - color_id (1 byte): Color ID
    - color_id_dup (1 byte): Duplicate color_id
    - zero_padding (2 bytes): Always 0x0000

    Total row size = variable (12-16 bytes)
    Entries are packed tightly (not 16-byte aligned!)
    """

    color_id: int
    name: str
    color_rgb: int = 0  # Not stored in actual row structure!

    def marshal_binary(self, row_index: int) -> bytes:
        """Marshal color as variable-length entry (tightly packed)."""
        row = bytearray()

        # Encode name as ASCII + null terminator
        name_bytes = self.name.encode('ascii')
        name_with_null = name_bytes + b'\x00'

        # Calculate length_marker using formula from reference:
        # length_marker = 2 * strlen(name) + 3
        strlen = len(name_bytes)
        length_marker = 2 * strlen + 3

        # Calculate total length based on name length
        # Short names (<=3 letters) get 12 bytes total
        # Longer names (>=4 letters) get 16 bytes total
        if strlen <= 3:
            total_len = 12
        else:
            total_len = 16

        # Calculate padding needed
        # Structure: [length_marker (1)] + [name+null (N)] + [padding (P)] + [color_id (1)] + [color_id_dup (1)] + [0x0000 (2)]
        name_len = len(name_with_null)
        fixed_fields_len = 4  # color_id + color_id_dup + 0x0000
        padding = total_len - 1 - name_len - fixed_fields_len

        # Build entry
        row.extend(bytes([length_marker]))  # Length marker
        row.extend(name_with_null)          # Name + null
        row.extend(b'\x00' * padding)       # Padding
        row.extend(struct.pack('<B', self.color_id))  # color_id
        row.extend(struct.pack('<B', self.color_id))  # color_id_dup
        row.extend(struct.pack('<H', 0))    # 0x0000

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


# ============================================================================
# DEFAULT METADATA ROW TYPES (from binary analysis)
# ============================================================================

@dataclass
class ColumnRow:
    """Column table row (Table 16 - COLUMNS).

    Structure from binary analysis:
    - start_marker (2 bytes): 0xFFFA
    - name (N*2 bytes): UTF-16LE encoded column name
    - end_marker (2 bytes): 0xFFFB
    - column_id (2 bytes): Sequential ID (2, 3, 4...)
    - field_type (2 bytes): Field type code (0x81, 0x82...)
    - size_type (2 bytes): Data size/type indicator
    - padding (2 bytes): Always 0x0000

    Row size = 12 + (name_length * 2) bytes
    """

    column_id: int
    name: str
    field_type: int
    size_type: int

    def marshal_binary(self, row_index: int) -> bytes:
        """Marshal row to binary format."""
        row = bytearray()

        # Start marker
        row.extend(struct.pack('<H', 0xFFFA))

        # Name in UTF-16LE
        name_utf16 = self.name.encode('utf-16-le')
        row.extend(name_utf16)

        # End marker
        row.extend(struct.pack('<H', 0xFFFB))

        # Metadata
        row.extend(struct.pack('<H', self.column_id))
        row.extend(struct.pack('<H', self.field_type))
        row.extend(struct.pack('<H', self.size_type))
        row.extend(struct.pack('<H', 0))

        return bytes(row)


@dataclass
class Unknown17Row:
    """UNKNOWN17 table row (Table 17).

    Structure from binary analysis:
    - field1 (2 bytes): uint16 - source_id / from_id
    - field2 (2 bytes): uint16 - target_id / to_id
    - field3 (4 bytes): uint32 - mapping value / flags

    Fixed row size = 8 bytes
    """

    field1: int
    field2: int
    field3: int

    def marshal_binary(self, row_index: int) -> bytes:
        """Marshal row to binary format."""
        row = bytearray()
        row.extend(struct.pack('<H', self.field1))
        row.extend(struct.pack('<H', self.field2))
        row.extend(struct.pack('<I', self.field3))
        return bytes(row)


@dataclass
class Unknown18Row:
    """UNKNOWN18 table row (Table 18).

    Structure from binary analysis (IDENTICAL to UNKNOWN17):
    - field1 (2 bytes): uint16 - source_id / from_id
    - field2 (2 bytes): uint16 - target_id / to_id
    - field3 (4 bytes): uint32 - mapping value / flags

    Fixed row size = 8 bytes
    """

    field1: int
    field2: int
    field3: int

    def marshal_binary(self, row_index: int) -> bytes:
        """Marshal row to binary format (same as Unknown17Row)."""
        row = bytearray()
        row.extend(struct.pack('<H', self.field1))
        row.extend(struct.pack('<H', self.field2))
        row.extend(struct.pack('<I', self.field3))
        return bytes(row)


@dataclass
class HistoryRow:
    """HISTORY table row (Table 19/40 - Page 40).

    Structure from binary analysis:
    - header (4 bytes): Always 0x00000000
    - date_length_marker (1 byte): strlen(date) * 2 + 3
    - date (N bytes): ASCII date string (e.g., "2026-03-02")
    - padding (P bytes): Pads to length_marker total
    - unknown1 (1 byte): Observed 0x19 (25)
    - unknown2 (1 byte): Observed 0x1e (30)
    - name_length_marker (1 byte): strlen(name) * 2 + 3
    - name (M bytes): ASCII name string (e.g., "1000")
    - padding (Q bytes): Pads to length_marker total
    - unknown3 (1 byte): Observed 0x03 (3)
    - padding (rest): Null bytes to fill page
    """

    date: str
    name: str
    unknown1: int = 0x19
    unknown2: int = 0x1e
    unknown3: int = 0x03

    def marshal_binary(self, row_index: int) -> bytes:
        """Marshal row to binary format."""
        row = bytearray()

        # Header (4 zero bytes)
        row.extend(b'\x00' * 4)

        # Date field
        row.extend(encode_pdb_string(self.date))

        # Unknown bytes
        row.extend(struct.pack('<B', self.unknown1))
        row.extend(struct.pack('<B', self.unknown2))

        # Name field
        row.extend(encode_pdb_string(self.name))

        # Final unknown byte
        row.extend(struct.pack('<B', self.unknown3))

        return bytes(row)
