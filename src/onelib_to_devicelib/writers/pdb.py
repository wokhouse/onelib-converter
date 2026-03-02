"""
PDB (legacy Device Library) file writer.

Generates export.pdb files for older Pioneer hardware compatibility.

Based on:
- Deep-Symmetry crate-digger analysis
- REX project (kimtore/rex) PDB generation
- Implementation research results
"""

import logging
import struct
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from onelib_to_devicelib.parsers.onelib import Track, Playlist

logger = logging.getLogger(__name__)

# PDB File Constants
PAGE_SIZE = 4096
MAGIC_HEADER = b'\x00\x00\x00\x00'
ROW_SIZE = 200  # Track row size with all fields
MAX_ROWS_PER_PAGE = (PAGE_SIZE - 8) // ROW_SIZE  # Account for page header

# Page types
PAGE_TYPE_TRACKS = 0x01
PAGE_TYPE_PLAYLISTS = 0x02
PAGE_TYPE_ROOT = 0x03


@dataclass
class TrackRow:
    """Track row data for PDB.

    Based on Deep-Symmetry analysis and REX project implementation.
    Contains all fields needed for proper Device Library compatibility.
    """
    # Core fields
    track_id: int
    title: str
    artist: str
    album: str
    genre: str

    # Audio properties
    bpm: int  # BPM * 100
    duration: int  # in milliseconds

    # File information
    file_path: str
    file_size: int  # in bytes
    bit_rate: int  # in kbps
    sample_rate: int  # in Hz
    bit_depth: int = 16  # Default to 16-bit

    # Track metadata
    track_number: int = 0
    disc_number: int = 1
    rating: int = 0  # 0-5 stars
    play_count: int = 0
    artwork_id: Optional[int] = None

    # Dates (Unix timestamps)
    date_added: int = 0
    date_created: int = 0
    date_modified: int = 0

    # Analysis flags
    analyzed: bool = False  # Whether track has been analyzed
    has_waveform: bool = False
    has_beat_grid: bool = False
    has_cues: bool = False

    def __post_init__(self):
        # Convert BPM from float to int if needed
        if isinstance(self.bpm, float):
            self.bpm = int(self.bpm * 100)  # Store as BPM * 100


class PDBWriter:
    """
    Writer for legacy Device Library PDB files.

    Generates export.pdb files compatible with CDJ-2000NXS and older hardware.
    """

    def __init__(self, output_path: Path):
        """
        Initialize the PDB writer.

        Args:
            output_path: Path to PIONEER/rekordbox/ directory
        """
        self.output_path = Path(output_path)
        self.pioneer_path = self.output_path / "PIONEER" / "rekordbox"
        self.pioneer_path.mkdir(parents=True, exist_ok=True)

        self.tracks: List[TrackRow] = []
        self.playlists: List[Playlist] = []
        self.folders: List[Playlist] = []

        # String storage for deduplication
        self._strings: Dict[str, int] = {}
        self._string_data = bytearray()

    def add_track(self, track: Track) -> None:
        """
        Add a track to the PDB database.

        Extracts all available fields from Track object for complete PDB row.
        """
        # Determine analysis flags
        analyzed = track.beat_grid is not None
        has_waveform = analyzed  # If we have beat grid, we likely have waveform
        has_beat_grid = analyzed
        has_cues = len(track.hot_cues) > 0 or len(track.cues) > 0

        pdb_track = TrackRow(
            # Core fields
            track_id=track.id,
            title=track.title or "",
            artist=track.artist or "",
            album=track.album or "",
            genre=track.genre or "",

            # Audio properties
            bpm=int(track.bpm * 100) if track.bpm else 0,
            duration=int(track.duration * 1000) if track.duration else 0,

            # File information
            file_path=str(track.file_path),
            file_size=track.file_size,
            bit_rate=track.bit_rate,
            sample_rate=track.sample_rate,
            bit_depth=16,  # Default assumption

            # Track metadata
            track_number=0,  # Not available in OneLibrary
            disc_number=1,   # Default
            rating=0,        # Not available
            play_count=0,    # Not available
            artwork_id=track.artwork_id,

            # Dates (use current time if not available)
            date_added=0,    # Would need file creation time
            date_created=0,
            date_modified=0,

            # Analysis flags
            analyzed=analyzed,
            has_waveform=has_waveform,
            has_beat_grid=has_beat_grid,
            has_cues=has_cues
        )
        self.tracks.append(pdb_track)

    def add_playlist(self, playlist: Playlist) -> None:
        """Add a playlist to the PDB database."""
        if playlist.is_folder:
            self.folders.append(playlist)
        else:
            self.playlists.append(playlist)

    def _encode_string(self, s: str) -> bytes:
        """Encode string as UTF-16LE with null terminator."""
        return s.encode('utf-16-le') + b'\x00\x00'

    def _add_string_to_heap(self, s: str) -> int:
        """
        Add a string to the global string heap and return its offset.

        Strings are deduplicated - same string shares storage.
        """
        if s in self._strings:
            return self._strings[s]

        # Encode string
        encoded = self._encode_string(s)
        offset = len(self._string_data)

        # Add to heap
        self._string_data += encoded
        self._strings[s] = offset

        return offset

    def _write_file_header(self) -> bytes:
        """Write the PDB file header (first page)."""
        header = bytearray(PAGE_SIZE)

        # Magic bytes (4 zeros)
        header[0:4] = MAGIC_HEADER

        # Page size
        struct.pack_into('<I', header, 4, PAGE_SIZE)

        # Unknown (always 1)
        struct.pack_into('<I', header, 8, 1)

        # Sequence number
        struct.pack_into('<I', header, 12, 0)

        # Table pointers will follow
        # For now, reserve space for table pointers
        # Track table starts at page 1
        struct.pack_into('<I', header, 16, 1)

        # Remaining header reserved
        # (table pointers for playlists, folders, etc.)

        return bytes(header)

    def _write_track_row(self, track: TrackRow, string_offsets: Dict[str, int]) -> bytes:
        """
        Create a track row (fixed-size portion).

        Expanded row structure (200 bytes for complete track data):
        - Row header (4 bytes)
        - Track ID (4 bytes)
        - String offsets for title, artist, album, genre, file_path (4 bytes each)
        - BPM (2 bytes)
        - Duration (4 bytes)
        - File size (4 bytes)
        - Bit rate (2 bytes)
        - Sample rate (2 bytes)
        - Track number (2 bytes)
        - Disc number (2 bytes)
        - Rating (1 byte)
        - Play count (4 bytes)
        - Artwork ID (4 bytes)
        - Dates (12 bytes: added, created, modified)
        - Analysis flags (1 byte)
        - Reserved/padding (rest)
        """
        ROW_SIZE = 200  # Expanded to accommodate all fields
        row = bytearray(ROW_SIZE)

        # Row header (from Deep-Symmetry analysis)
        struct.pack_into('<H', row, 0, 0)  # Row header
        struct.pack_into('<H', row, 2, 0)  # Unknown

        # Track ID
        struct.pack_into('<I', row, 4, track.track_id)

        # String offsets (matching Deep-Symmetry field order)
        struct.pack_into('<I', row, 8, string_offsets.get('artist', 0))
        struct.pack_into('<I', row, 12, string_offsets.get('title', 0))
        struct.pack_into('<I', row, 16, string_offsets.get('album', 0))
        struct.pack_into('<I', row, 20, string_offsets.get('genre', 0))
        struct.pack_into('<I', row, 24, string_offsets.get('file_path', 0))

        # BPM (stored as BPM * 100, max 655.35 BPM)
        struct.pack_into('<H', row, 28, min(track.bpm, 65535))

        # Duration in milliseconds
        struct.pack_into('<I', row, 30, track.duration)

        # File information
        struct.pack_into('<I', row, 34, track.file_size)
        struct.pack_into('<H', row, 38, min(track.bit_rate, 65535))
        struct.pack_into('<H', row, 40, min(track.sample_rate, 65535))

        # Track metadata
        struct.pack_into('<H', row, 42, track.track_number)
        struct.pack_into('<H', row, 44, track.disc_number)
        row[46] = track.rating  # 1 byte
        struct.pack_into('<I', row, 47, track.play_count)

        # Artwork ID
        artwork_id_val = track.artwork_id if track.artwork_id else 0
        struct.pack_into('<I', row, 51, artwork_id_val)

        # Dates (Unix timestamps)
        struct.pack_into('<I', row, 55, track.date_added)
        struct.pack_into('<I', row, 59, track.date_created)
        struct.pack_into('<I', row, 63, track.date_modified)

        # Analysis flags (bitfield)
        flags = 0
        if track.analyzed:
            flags |= 0x01
        if track.has_waveform:
            flags |= 0x02
        if track.has_beat_grid:
            flags |= 0x04
        if track.has_cues:
            flags |= 0x08
        row[67] = flags

        # Rest is reserved/padding (already zeroed from bytearray)

        return bytes(row)

    def _write_track_page(self, tracks: List[TrackRow], page_num: int) -> bytes:
        """
        Write a page containing track rows.

        Page structure:
        - Page header (8 bytes)
        - Row data (variable, based on row count and row size)
        - String heap (at end of page if using per-page heaps)
        """
        page = bytearray(PAGE_SIZE)
        ROW_SIZE = 200  # Must match _write_track_row

        # Page header (8 bytes)
        page[0] = PAGE_TYPE_TRACKS  # Page type
        page[1] = 0x00
        struct.pack_into('<H', page, 2, len(tracks))  # Row count
        struct.pack_into('<H', page, 4, 0)  # Unknown
        struct.pack_into('<H', page, 6, 0)  # Heap entries (for now)

        # Row data starts at offset 8
        row_offset = 8

        # Collect strings for this page (using global heap for MVP)
        page_strings = {}

        for track in tracks:
            # Get or create string offsets for all string fields
            if 'artist' not in page_strings:
                page_strings['artist'] = self._add_string_to_heap(track.artist)
            if 'title' not in page_strings:
                page_strings['title'] = self._add_string_to_heap(track.title)
            if 'album' not in page_strings:
                page_strings['album'] = self._add_string_to_heap(track.album)
            if 'genre' not in page_strings:
                page_strings['genre'] = self._add_string_to_heap(track.genre)
            if 'file_path' not in page_strings:
                page_strings['file_path'] = self._add_string_to_heap(track.file_path)

            # Write row
            row = self._write_track_row(track, page_strings)
            page[row_offset:row_offset + len(row)] = row
            row_offset += len(row)

        # Note: For MVP, we use a global string heap written separately
        # In a full implementation, each page would have its own heap
        # String heap would go at end of page (PAGE_SIZE - heap_start)

        return bytes(page)

    def _write_playlist_page(self, playlists: List[Playlist], page_num: int) -> bytes:
        """Write a page containing playlist rows."""
        page = bytearray(PAGE_SIZE)

        # Page header
        page[0] = PAGE_TYPE_PLAYLISTS
        page[1] = 0x00
        struct.pack_into('<H', page, 2, len(playlists))
        struct.pack_into('<H', page, 4, 0)
        struct.pack_into('<H', page, 6, 0)

        # Playlist row structure would go here
        # For MVP, we're creating minimal playlist support

        return bytes(page)

    def write(self) -> None:
        """
        Write the complete PDB file.

        Generates export.pdb with tracks, playlists, and folders.
        Includes global string heap at the end for string storage.
        """
        output_file = self.pioneer_path / "export.pdb"

        logger.info(f"Writing PDB file: {output_file}")
        logger.info(f"Tracks: {len(self.tracks)}, Playlists: {len(self.playlists)}")
        logger.info(f"String heap entries: {len(self._strings)}")

        with open(output_file, 'wb') as f:
            # Write file header page
            f.write(self._write_file_header())

            # Calculate track pages
            num_track_pages = (len(self.tracks) + MAX_ROWS_PER_PAGE - 1) // MAX_ROWS_PER_PAGE

            # Write track pages
            for page_num in range(num_track_pages):
                start_idx = page_num * MAX_ROWS_PER_PAGE
                end_idx = min(start_idx + MAX_ROWS_PER_PAGE, len(self.tracks))
                page_tracks = self.tracks[start_idx:end_idx]

                f.write(self._write_track_page(page_tracks, page_num + 1))
                logger.debug(f"Wrote track page {page_num + 1}: {len(page_tracks)} tracks")

            # Write playlist pages (if any)
            if self.playlists:
                # Group playlists into pages
                # For MVP, write all playlists to one page
                f.write(self._write_playlist_page(self.playlists, num_track_pages + 1))
                logger.debug(f"Wrote playlist page: {len(self.playlists)} playlists")

            # Write global string heap
            if self._string_data:
                string_heap_page = bytearray(PAGE_SIZE)
                string_heap_page[0:4] = b'\x00\x00\x00\x00'  # Heap page marker
                struct.pack_into('<I', string_heap_page, 4, len(self._string_data))
                string_heap_page[8:8+len(self._string_data)] = self._string_data
                f.write(string_heap_page)
                logger.debug(f"Wrote string heap: {len(self._string_data)} bytes")

        logger.info("PDB file written successfully")

    def write_export_ext_pdb(self) -> None:
        """
        Write the exportExt.pdb file (extended data).

        Contains tag-track relationships and additional metadata.
        """
        output_file = self.pioneer_path / "exportExt.pdb"

        logger.info(f"Writing exportExt.pdb file: {output_file}")

        # For MVP, create minimal exportExt.pdb
        # This file contains extended metadata that's not strictly required

        with open(output_file, 'wb') as f:
            # Write minimal header
            header = bytearray(PAGE_SIZE)
            header[0:4] = MAGIC_HEADER
            struct.pack_into('<I', header, 4, PAGE_SIZE)
            struct.pack_into('<I', header, 8, 1)
            f.write(header)

        logger.info("exportExt.pdb written successfully")
