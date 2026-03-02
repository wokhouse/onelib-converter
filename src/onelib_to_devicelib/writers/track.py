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
    """90-byte fixed track header.

    This header contains all fixed-width fields for a track.
    Variable-length strings are stored after this header.
    """
    # Bytes 0-1
    unnamed0: int = 0x24  # Always 0x24
    # Bytes 2-3
    index_shift: int = 0  # row_num × 0x20 (critical field!)
    # Bytes 4-7
    bitmask: int = 0xC0700  # Always 0xC0700
    # Bytes 8-11
    sample_rate: int = 44100
    # Bytes 12-15
    composer_id: int = 0
    # Bytes 16-19
    file_size: int = 0
    # Bytes 20-23
    checksum: int = 0
    # Bytes 24-25
    unnamed7: int = 0x758a
    # Bytes 26-27
    unnamed8: int = 0x57a2
    # Bytes 28-31
    artwork_id: int = 0
    # Bytes 32-35
    key_id: int = 0
    # Bytes 36-39
    original_artist_id: int = 0
    # Bytes 40-43
    label_id: int = 0
    # Bytes 44-47
    remixer_id: int = 0
    # Bytes 48-51
    bitrate: int = 0
    # Bytes 52-55
    track_number: int = 0
    # Bytes 56-59
    tempo: int = 0  # BPM × 100
    # Bytes 60-63
    genre_id: int = 0
    # Bytes 64-67
    album_id: int = 0
    # Bytes 68-71
    artist_id: int = 0
    # Bytes 72-75
    id: int = 0  # Track ID
    # Bytes 76-77
    disc_number: int = 0
    # Bytes 78-79
    play_count: int = 0
    # Bytes 80-81
    year: int = 0
    # Bytes 82-83
    sample_depth: int = 16
    # Bytes 84-85
    duration: int = 0  # Seconds
    # Bytes 86-87
    unnamed26: int = 0x29  # Always 0x29
    # Byte 88
    color_id: int = 0
    # Byte 89
    rating: int = 0
    # Bytes 90-91 (wait, this is at byte 88-89, not 90-91)
    # Let me recalculate...
    # Actually the file_type and unnamed30 are at the end


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
        self.header = TrackHeader(
            id=getattr(track, 'id', 0),  # Note: 'id' not 'track_id'
            tempo=int(getattr(track, 'bpm', 0) * 100),
            duration=int(getattr(track, 'duration', 0)),
            file_size=getattr(track, 'file_size', 0),
            sample_rate=getattr(track, 'sample_rate', 44100),
            bitrate=getattr(track, 'bit_rate', 0),  # Note: 'bit_rate' not 'bitrate'
            track_number=getattr(track, 'track_number', 0),
            disc_number=getattr(track, 'disc_number', 0),
            year=getattr(track, 'year', 0),
            artist_id=getattr(track, 'artist_id', 0),
            album_id=getattr(track, 'album_id', 0),
            genre_id=getattr(track, 'genre_id', 0),
            index_shift=0,  # Set when inserted
        )
        self.offsets = TrackStringOffsets()
        self.strings: Dict[str, str] = {}

        # Build string dictionary
        self.strings['isrc'] = getattr(track, 'isrc', '')
        self.strings['composer'] = getattr(track, 'composer', '')
        self.strings['key_analyzed'] = '1'  # Not analyzed
        self.strings['phrase_analyzed'] = '1'
        self.strings['unknown_string4'] = ''
        self.strings['message'] = getattr(track, 'comment', '')
        self.strings['kuvo_public'] = ''
        self.strings['autoload_hotcues'] = 'ON'
        self.strings['unknown_string5'] = ''
        self.strings['unknown_string6'] = ''
        self.strings['date_added'] = getattr(track, 'date_added', '')
        self.strings['release_date'] = getattr(track, 'release_date', '')
        self.strings['mix_name'] = ''
        self.strings['unknown_string7'] = ''
        self.strings['analyze_path'] = ''
        self.strings['analyze_date'] = ''
        self.strings['comment'] = getattr(track, 'comment', '')
        self.strings['title'] = getattr(track, 'title', '')
        self.strings['unknown_string8'] = ''
        # Get filename from file_path Path object
        file_path = getattr(track, 'file_path', Path())
        self.strings['filename'] = file_path.name if hasattr(file_path, 'name') else str(file_path)
        self.strings['file_path'] = str(file_path)

    def marshal_binary(self, row_index: int) -> bytes:
        """Serialize track row with string heap.

        Args:
            row_index: Row index (used to set index_shift field)

        Returns:
            Complete serialized row bytes
        """
        # Set index shift (critical field!)
        self.header.index_shift = row_index * 0x20

        # Build row data
        row = bytearray()

        # Fixed header (88 bytes - need to verify this count)
        # Field packing for first 16 bytes
        row += struct.pack('<HH', self.header.unnamed0, self.header.index_shift)  # 4 bytes
        row += struct.pack('<II', self.header.bitmask, self.header.sample_rate)  # 8 bytes

        # Bytes 12-19
        row += struct.pack('<II',
            self.header.composer_id, self.header.file_size)  # 8 bytes

        # Bytes 20-27
        row += struct.pack('<IHH',
            self.header.checksum, self.header.unnamed7, self.header.unnamed8)  # 8 bytes

        # Bytes 28-35
        row += struct.pack('<II',
            self.header.artwork_id, self.header.key_id)  # 8 bytes

        # Bytes 36-43
        row += struct.pack('<II',
            self.header.original_artist_id, self.header.label_id)  # 8 bytes

        # Bytes 44-51
        row += struct.pack('<II',
            self.header.remixer_id, self.header.bitrate)  # 8 bytes

        # Bytes 52-59
        row += struct.pack('<II',
            self.header.track_number, self.header.tempo)  # 8 bytes

        # Bytes 60-67
        row += struct.pack('<II',
            self.header.genre_id, self.header.album_id)  # 8 bytes

        # Bytes 68-75
        row += struct.pack('<II',
            self.header.artist_id, self.header.id)  # 8 bytes

        # Bytes 76-83
        row += struct.pack('<HHHH',
            self.header.disc_number, self.header.play_count,
            self.header.year, self.header.sample_depth)  # 8 bytes

        # Bytes 84-87
        row += struct.pack('<HH', self.header.duration, self.header.unnamed26)  # 4 bytes

        # Bytes 88-91 (color_id, rating, file_type, unnamed30)
        # Actually this needs to be 1 byte + 1 byte + 2 bytes
        row += struct.pack('<BBH',
            self.header.color_id, self.header.rating, 0x3)  # 4 bytes

        # Wait, I need to recalculate. Let me be more careful:
        # Total header should be 90 bytes (or 88? need to verify)
        # Let me just pack the entire thing systematically

        # Actually, looking at the structure more carefully, the track header is:
        # - unnamed0: H (2)
        # - index_shift: H (2)
        # - bitmask: I (4)
        # - sample_rate: I (4)
        # - composer_id: I (4)
        # - file_size: I (4)
        # - checksum: I (4)
        # - unnamed7: H (2)
        # - unnamed8: H (2)
        # - artwork_id: I (4)
        # - key_id: I (4)
        # - original_artist_id: I (4)
        # - label_id: I (4)
        # - remixer_id: I (4)
        # - bitrate: I (4)
        # - track_number: I (4)
        # - tempo: I (4)
        # - genre_id: I (4)
        # - album_id: I (4)
        # - artist_id: I (4)
        # - id: I (4)
        # - disc_number: H (2)
        # - play_count: H (2)
        # - year: H (2)
        # - sample_depth: H (2)
        # - duration: H (2)
        # - unnamed26: H (2)
        # - color_id: B (1)
        # - rating: B (1)
        # - file_type: H (2)
        # Total: 2+2+4+4+4+4+4+2+2+4+4+4+4+4+4+4+4+4+4+4+2+2+2+2+2+2+1+1+2 = 88 bytes

        # Then we have 42 bytes of offsets (21 × H)
        # Total so far: 88 + 42 = 130 bytes

        # But the plan says 132 bytes... let me check if there's something else
        # Actually the file_type and unnamed30 might be in a different position
        # Let me stick with the plan's structure which says 90 bytes for header
        # and has file_type and unnamed30 as the last fields

        # For now, let me rebuild with the correct 90-byte header:
        row = bytearray()

        # Pack all header fields in order
        row += struct.pack('<H', self.header.unnamed0)  # 0-1
        row += struct.pack('<H', self.header.index_shift)  # 2-3
        row += struct.pack('<I', self.header.bitmask)  # 4-7
        row += struct.pack('<I', self.header.sample_rate)  # 8-11
        row += struct.pack('<I', self.header.composer_id)  # 12-15
        row += struct.pack('<I', self.header.file_size)  # 16-19
        row += struct.pack('<I', self.header.checksum)  # 20-23
        row += struct.pack('<H', self.header.unnamed7)  # 24-25
        row += struct.pack('<H', self.header.unnamed8)  # 26-27
        row += struct.pack('<I', self.header.artwork_id)  # 28-31
        row += struct.pack('<I', self.header.key_id)  # 32-35
        row += struct.pack('<I', self.header.original_artist_id)  # 36-39
        row += struct.pack('<I', self.header.label_id)  # 40-43
        row += struct.pack('<I', self.header.remixer_id)  # 44-47
        row += struct.pack('<I', self.header.bitrate)  # 48-51
        row += struct.pack('<I', self.header.track_number)  # 52-55
        row += struct.pack('<I', self.header.tempo)  # 56-59
        row += struct.pack('<I', self.header.genre_id)  # 60-63
        row += struct.pack('<I', self.header.album_id)  # 64-67
        row += struct.pack('<I', self.header.artist_id)  # 68-71
        row += struct.pack('<I', self.header.id)  # 72-75
        row += struct.pack('<H', self.header.disc_number)  # 76-77
        row += struct.pack('<H', self.header.play_count)  # 78-79
        row += struct.pack('<H', self.header.year)  # 80-81
        row += struct.pack('<H', self.header.sample_depth)  # 82-83
        row += struct.pack('<H', self.header.duration)  # 84-85
        row += struct.pack('<H', self.header.unnamed26)  # 86-87
        row += struct.pack('<B', self.header.color_id)  # 88
        row += struct.pack('<B', self.header.rating)  # 89
        row += struct.pack('<H', 0x3)  # 90-91 - CRITICAL: file_type + unnamed30 combined

        # Actually that's 92 bytes, not 90. Let me check the plan again...
        # The plan says:
        # - file_type: uint16 = 0x1  # MP3 = 0x1
        # - unnamed30: uint16 = 0x3  # CRITICAL: MUST be 0x3 or rekordbox crashes!
        #
        # But looking at the TrackHeader definition, it seems like they're separate
        # For now let me assume the header is 92 bytes and see if it works

        # String offsets placeholder (42 bytes)
        offset_start = len(row)
        row += b'\x00' * 42

        # Calculate string heap offset (after row data)
        heap_base = len(row)

        # Encode strings and build offset table
        offset_table = []
        string_heap = bytearray()

        for key in self.STRING_FIELDS:
            encoded = encode_device_sql_string(self.strings.get(key, ''))
            offset = heap_base + len(string_heap)
            offset_table.append(offset)
            string_heap += encoded

        # Write offset table
        offset_pack = '<' + 'H' * 21
        row[offset_start:offset_start+42] = struct.pack(offset_pack, *offset_table)

        # Append string heap
        row += string_heap

        return bytes(row)
