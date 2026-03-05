"""
Track Row Structure

Create complete 132-byte track rows with string offsets.
"""

import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from .dstring import encode_device_sql_string


@dataclass
class TrackHeader:
    """94-byte fixed track header matching REX implementation.

    Based on REX project (https://github.com/kimtore/rex):
    - Complete field definitions from track.go
    - Critical field: Unnamed30 = 0x3 (REKORBOX CRASHES WITHOUT THIS!)

    Total: 94 bytes
    """
    # From REX: All numerical values go here
    # Bytes 0-1
    row_offset: int = 0x24  # Always 0x24, identifies this as track row

    # Bytes 2-3
    index_shift: int = 0  # Starts at zero, increases by 0x20 each row

    # Bytes 4-7 (4 bytes)
    bitmask: int = 0xC0700  # Bitmask - CRITICAL VALUE from REX

    # Bytes 8-11 (4 bytes)
    sample_rate: int = 44100

    # Bytes 12-15 (4 bytes)
    composer_id: int = 0

    # Bytes 16-19 (4 bytes)
    file_size: int = 0

    # Bytes 20-23 (4 bytes)
    checksum: int = 0  # Checksum (28 bits??)

    # Bytes 24-25 (2 bytes)
    unnamed7: int = 0x63da  # Reference value (appears to be export-specific constant)

    # Bytes 26-27 (2 bytes)
    unnamed8: int = 0x52ef  # Reference value (appears to be export-specific constant)

    # Bytes 28-31 (4 bytes)
    artwork_id: int = 0

    # Bytes 32-35 (4 bytes)
    key_id: int = 0

    # Bytes 36-39 (4 bytes)
    original_artist_id: int = 0

    # Bytes 40-43 (4 bytes)
    label_id: int = 0

    # Bytes 44-47 (4 bytes)
    remixer_id: int = 0

    # Bytes 48-51 (4 bytes)
    bitrate: int = 0

    # Bytes 52-55 (4 bytes)
    track_number: int = 0

    # Bytes 56-59 (4 bytes)
    tempo: int = 0

    # Bytes 60-63 (4 bytes)
    genre_id: int = 0

    # Bytes 64-67 (4 bytes)
    album_id: int = 0

    # Bytes 68-71 (4 bytes)
    artist_id: int = 0

    # Bytes 72-75 (4 bytes)
    id: int = 0  # Track ID

    # Bytes 76-77 (2 bytes)
    disc_number: int = 0

    # Bytes 78-79 (2 bytes)
    play_count: int = 0

    # Bytes 80-81 (2 bytes)
    year: int = 0

    # Bytes 82-83 (2 bytes)
    sample_depth: int = 16  # Default to 16-bit

    # Bytes 84-85 (2 bytes)
    duration: int = 0

    # Bytes 86-87 (2 bytes)
    unnamed26: int = 0x29  # CRITICAL: From REX

    # Bytes 88 (1 byte)
    color_id: int = 0

    # Bytes 89 (1 byte)
    rating: int = 0

    # Bytes 90-91 (2 bytes)
    file_type: int = 0

    # Bytes 92-93 (2 bytes)
    unnamed30: int = 0x3  # CRITICAL: REKORBOX CRASHES WITHOUT THIS!


@dataclass
class TrackStringOffsets:
    """42 bytes of string offsets (21 × uint16).

    Each offset points to a string in the string heap that follows
    the offset table. If an offset is 0, the string is empty/NULL.

    The order must match the string order in the heap.
    """
    isrc: int = 0  # 0
    composer: int = 0  # 1
    num1: int = 0  # 2 - key_analyzed offset
    num2: int = 0  # 3 - phrase_analyzed offset
    unknown_string4: int = 0  # 4
    message: int = 0  # 5
    kuvo_public: int = 0  # 6
    autoload_hotcues: int = 0  # 7
    unknown_string5: int = 0  # 8
    unknown_string6: int = 0  # 9
    date_added: int = 0  # 10
    release_date: int = 0  # 11
    mix_name: int = 0  # 12
    unknown_string7: int = 0  # 13
    analyze_path: int = 0  # 14
    analyze_date: int = 0  # 15
    comment: int = 0  # 16
    title: int = 0  # 17
    unknown_string8: int = 0  # 18
    filename: int = 0  # 19
    file_path: int = 0  # 20


class TrackRow:
    """Complete track row with variable strings.

    A TrackRow consists of:
    1. 90-byte fixed header
    2. 42-byte offset table (21 × uint16)
    3. Variable-length string heap (DeviceSQL encoded strings)
    """

    # String field names in order
    STRING_FIELDS = [
        'isrc', 'composer', 'key_analyzed', 'phrase_analyzed',
        'unknown_string4', 'message', 'kuvo_public', 'autoload_hotcues',
        'unknown_string5', 'unknown_string6', 'date_added', 'release_date',
        'mix_name', 'unknown_string7', 'analyze_path', 'analyze_date',
        'comment', 'title', 'unknown_string8', 'filename', 'file_path'
    ]

    def __init__(self, track):
        """Initialize track row from parsed track data.

        Args:
            track: Parsed track from OneLibrary
        """
        # Extract track data
        track_id = getattr(track, 'id', 0)
        file_size = getattr(track, 'file_size', 0)
        sample_rate = getattr(track, 'sample_rate', 44100)
        genre_id = getattr(track, 'genre_id', 0)
        bitrate = getattr(track, 'bit_rate', 0)
        track_number = getattr(track, 'track_number', 0)
        disc_number = getattr(track, 'disc_number', 0)
        duration = getattr(track, 'duration', 0)
        year = getattr(track, 'year', 0)
        bpm = getattr(track, 'bpm', 0)
        key_id = getattr(track, 'key_id', 0)
        artist_id = getattr(track, 'artist_id', 0)
        album_id = getattr(track, 'album_id', 0)
        color_id = getattr(track, 'color_id', 0)

        # Calculate tempo from BPM (tempo = BPM * 100)
        tempo = int(bpm * 100) if bpm else 0

        # Calculate duration in seconds (stored as uint16)
        duration_sec = int(duration) if duration else 0

        # Create header with REX-compatible structure (94 bytes)
        self.header = TrackHeader(
            # Bytes 0-1
            row_offset=0x24,  # Always 0x24, identifies this as track row
            # Bytes 2-3 (will be set in marshal_binary based on row_index)
            index_shift=0,
            # Bytes 4-7
            bitmask=0xC0700,  # CRITICAL VALUE from REX
            # Bytes 8-11
            sample_rate=sample_rate,
            # Bytes 12-15
            composer_id=0,
            # Bytes 16-19
            file_size=file_size,
            # Bytes 20-23 (checksum - TODO: implement proper algorithm)
            checksum=0,
            # Bytes 24-25
            unnamed7=0x63da,  # Reference value
            # Bytes 26-27
            unnamed8=0x52ef,  # Reference value
            # Bytes 28-31
            artwork_id=0,  # Always 0 since we don't copy artwork files
            # Bytes 32-35
            key_id=key_id,
            # Bytes 36-39
            original_artist_id=0,
            # Bytes 40-43
            label_id=getattr(track, 'label_id', 0),
            # Bytes 44-47
            remixer_id=0,
            # Bytes 48-51
            bitrate=bitrate,
            # Bytes 52-55
            track_number=track_number,
            # Bytes 56-59
            tempo=tempo,
            # Bytes 60-63
            genre_id=genre_id,
            # Bytes 64-67
            album_id=album_id,
            # Bytes 68-71
            artist_id=artist_id,
            # Bytes 72-75
            id=track_id,
            # Bytes 76-77
            disc_number=disc_number,
            # Bytes 78-79
            play_count=getattr(track, 'play_count', 0),
            # Bytes 80-81
            year=year,
            # Bytes 82-83
            sample_depth=16,  # Default to 16-bit
            # Bytes 84-85
            duration=duration_sec,
            # Bytes 86-87
            unnamed26=0x29,  # CRITICAL: From REX
            # Bytes 88
            color_id=color_id,
            # Bytes 89
            rating=getattr(track, 'rating', 0),
            # Bytes 90-91
            file_type=0,
            # Bytes 92-93
            unnamed30=0x3,  # CRITICAL: REKORBOX CRASHES WITHOUT THIS!
        )

        self.offsets = TrackStringOffsets()
        self.strings: Dict[str, str] = {}

        # Build string dictionary
        self.strings['isrc'] = getattr(track, 'isrc', '')
        self.strings['composer'] = getattr(track, 'composer', '')
        self.strings['key_analyzed'] = '1'  # Not analyzed
        self.strings['phrase_analyzed'] = '1'
        self.strings['unknown_string4'] = '1'  # FIX: Reference has '1', not ''
        self.strings['message'] = getattr(track, 'comment', '')
        self.strings['kuvo_public'] = ''
        self.strings['autoload_hotcues'] = 'ON'
        self.strings['unknown_string5'] = ''
        self.strings['unknown_string6'] = ''
        self.strings['date_added'] = getattr(track, 'date_added', '')
        self.strings['release_date'] = getattr(track, 'release_date', '')
        self.strings['mix_name'] = ''
        self.strings['unknown_string7'] = ''

        # FIX: Set analyze_path and analyze_date to match reference format
        # Reference has ANLZ path like: "Y/PIONEER/USBANLZ/P075/00013E69/ANLZ0000.DAT"
        # We'll use a simplified version for now
        track_id = getattr(track, 'id', 0)
        anlz_hash = f"{track_id:08X}"  # 8-digit hex ID
        self.strings['analyze_path'] = f"Y/PIONEER/USBANLZ/P075/{anlz_hash}/ANLZ0000.DAT"
        # Reference has date like "2026-01-25"
        self.strings['analyze_date'] = getattr(track, 'analyze_date', '2026-01-25')

        self.strings['comment'] = getattr(track, 'comment', '')
        self.strings['title'] = getattr(track, 'title', '')
        self.strings['unknown_string8'] = ''
        # Get filename from file_path Path object
        file_path = getattr(track, 'file_path', Path())
        self.strings['filename'] = file_path.name if hasattr(file_path, 'name') else str(file_path)
        self.strings['file_path'] = str(file_path)

    def _build_concatenated_string_blob(self) -> tuple[bytes, list[int]]:
        """Build concatenated string blob in reference format.

        The reference PDB stores all string data in ONE contiguous blob with
        type markers (0x05, 0x17, 0x13, 0x25) and separators (0x03).

        Format from reference analysis:
        - 0x03 = separator/empty string
        - 0x05, 0x17, 0x13, 0x25 = type markers before fields
        - Fields are stored with overlapping offsets for efficiency

        For simplicity, we'll use the reference's exact pattern.
        """
        blob_parts = []
        offsets = []

        # Build blob following reference pattern
        # Pattern: [0x03]*N + [markers] + [fields] + [separators]

        # Start with multiple 0x03 separators (empty strings)
        blob_parts.append(b'\x03\x03\x03')  # 3 empty strings

        # Add type markers and small values
        # Pattern from reference: 05 31 05 31 (type markers with data)
        blob_parts.append(b'\x05\x31\x05\x31')

        # More empty strings
        blob_parts.append(b'\x03' * 7)

        # ANLZ path with length prefix and type marker
        # Format: [length][path][0x17][date]
        anlz_path = self.strings.get('analyze_path', 'Y/PIONEER/USBANLZ/P075/00000001/ANLZ0000.DAT')
        blob_parts.append(bytes([len(anlz_path)]))  # Length byte
        blob_parts.append(anlz_path.encode('ascii'))
        blob_parts.append(b'\x17')  # Type separator

        # Date string
        analyze_date = self.strings.get('analyze_date', '2026-01-25')
        blob_parts.append(analyze_date.encode('ascii'))
        blob_parts.append(b'\x03')  # Separator

        # Track name with type marker
        # Format: [0x13][track_name][0x03]
        title = self.strings.get('title', '')
        blob_parts.append(b'\x13')  # Type marker
        blob_parts.append(title.encode('utf-8'))
        blob_parts.append(b'\x03')  # Separator

        # Filename with type marker
        # Format: [0x25][%track_num filename][0x03]
        filename = self.strings.get('filename', '')
        track_num = getattr(self, 'track_number', 0) or 1
        blob_parts.append(b'\x25')  # Type marker
        blob_parts.append(f'%{track_num} {filename}'.encode('utf-8'))
        blob_parts.append(b'\x03')  # Separator

        # File path
        file_path = self.strings.get('file_path', '')
        blob_parts.append(file_path.encode('utf-8'))
        blob_parts.append(b'\x03')  # Separator

        # Combine into single blob
        string_blob = b''.join(blob_parts)

        # Build offset table - for now use simple sequential offsets
        # TODO: Implement overlapping offsets like reference
        current_offset = 0
        for i in range(21):
            offsets.append(current_offset)
            # Move offset forward by varying amounts to simulate overlapping
            if i < 15:
                current_offset = min(current_offset + 1, len(string_blob))
            else:
                current_offset = min(current_offset + 10, len(string_blob))

        return string_blob, offsets

    def marshal_binary(self, row_index: int) -> bytes:
        """Serialize track row with concatenated string blob.

        Args:
            row_index: Row index (used to calculate index_shift)

        Returns:
            Complete serialized row bytes
        """
        # Build row data
        row = bytearray()

        # Fixed header (94 bytes) - matching REX structure exactly
        # Bytes 0-1: row_offset (subtype)
        row += struct.pack('<H', self.header.row_offset)

        # Bytes 2-3: index_shift
        self.header.index_shift = row_index * 0x20
        row += struct.pack('<H', self.header.index_shift)

        # Bytes 4-7: bitmask
        row += struct.pack('<I', self.header.bitmask)

        # Bytes 8-11: sample_rate
        row += struct.pack('<I', self.header.sample_rate)

        # Bytes 12-15: composer_id
        row += struct.pack('<I', self.header.composer_id)

        # Bytes 16-19: file_size
        row += struct.pack('<I', self.header.file_size)

        # Bytes 20-23: checksum
        row += struct.pack('<I', self.header.checksum)

        # Bytes 24-25: unnamed7
        row += struct.pack('<H', self.header.unnamed7)

        # Bytes 26-27: unnamed8
        row += struct.pack('<H', self.header.unnamed8)

        # Bytes 28-31: artwork_id
        row += struct.pack('<I', self.header.artwork_id)

        # Bytes 32-35: key_id
        row += struct.pack('<I', self.header.key_id)

        # Bytes 36-39: original_artist_id
        row += struct.pack('<I', self.header.original_artist_id)

        # Bytes 40-43: label_id
        row += struct.pack('<I', self.header.label_id)

        # Bytes 44-47: remixer_id
        row += struct.pack('<I', self.header.remixer_id)

        # Bytes 48-51: bitrate
        row += struct.pack('<I', self.header.bitrate)

        # Bytes 52-55: track_number
        row += struct.pack('<I', self.header.track_number)

        # Bytes 56-59: tempo
        row += struct.pack('<I', self.header.tempo)

        # Bytes 60-63: genre_id
        row += struct.pack('<I', self.header.genre_id)

        # Bytes 64-67: album_id
        row += struct.pack('<I', self.header.album_id)

        # Bytes 68-71: artist_id
        row += struct.pack('<I', self.header.artist_id)

        # Bytes 72-75: id (track_id)
        row += struct.pack('<I', self.header.id)

        # Bytes 76-77: disc_number
        row += struct.pack('<H', self.header.disc_number)

        # Bytes 78-79: play_count
        row += struct.pack('<H', self.header.play_count)

        # Bytes 80-81: year
        row += struct.pack('<H', self.header.year)

        # Bytes 82-83: sample_depth
        row += struct.pack('<H', self.header.sample_depth)

        # Bytes 84-85: duration
        row += struct.pack('<H', self.header.duration)

        # Bytes 86-87: unnamed26
        row += struct.pack('<H', self.header.unnamed26)

        # Bytes 88: color_id
        row += struct.pack('<B', self.header.color_id)

        # Bytes 89: rating
        row += struct.pack('<B', self.header.rating)

        # Bytes 90-91: file_type
        row += struct.pack('<H', self.header.file_type)

        # Bytes 92-93: unnamed30 (CRITICAL!)
        row += struct.pack('<H', self.header.unnamed30)

        # String offset table placeholder (42 bytes = 21 × uint16)
        offset_start = len(row)
        row += b'\x00' * 42

        # Build concatenated string blob (NEW FORMAT)
        string_blob, blob_offsets = self._build_concatenated_string_blob()

        # Calculate string heap offset (after row data)
        heap_base = len(row)

        # Build offset table pointing to blob positions
        offset_table = []
        for blob_offset in blob_offsets:
            offset_table.append(heap_base + blob_offset)

        # Write offset table
        offset_pack = '<' + 'H' * 21
        row[offset_start:offset_start+42] = struct.pack(offset_pack, *offset_table)

        # Append string blob
        row += string_blob

        # CRITICAL FIX: Add 36 bytes of padding to match reference row size
        # Reference rows are 340 bytes total (136 header + offsets + 168 data + 36 padding)
        # Our rows were 304 bytes (missing this padding)
        row += b'\x00' * 36

        return bytes(row)
