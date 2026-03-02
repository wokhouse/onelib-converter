"""
Enhanced PDB file writer based on reference file analysis.

This implementation generates PDB files that match the observed format
from rekordbox-generated export.pdb files.
"""

import struct
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from onelib_to_devicelib.parsers.onelib import Track, Playlist

logger = logging.getLogger(__name__)

# Constants
PAGE_SIZE = 4096
MAGIC_HEADER = b'\x00\x00\x00\x00'


@dataclass
class PDBTrack:
    """Track data for PDB row generation."""

    # Core fields
    track_id: int
    file_id: int
    title: str
    artist: str

    # File info
    file_path: str
    anlz_path: str

    # Audio properties
    duration_ms: int
    sample_rate: int

    # Metadata
    date_added: int  # DOS date format


class PDBWriterV2:
    """
    Enhanced PDB writer that generates rekordbox-compatible files.

    Based on analysis of reference export.pdb from rekordbox 6.
    """

    def __init__(self, output_path: Path):
        self.output_path = Path(output_path)
        self.pioneer_path = self.output_path / "PIONEER" / "rekordbox"
        self.pioneer_path.mkdir(parents=True, exist_ok=True)

        self.tracks: List[PDBTrack] = []
        self.playlists: List[Playlist] = []

    def add_track(self, track: Track, file_id: int, anlz_path: str) -> None:
        """Add a track from OneLibrary data."""

        # Convert date to DOS format (used in reference)
        # Format: YYMMDD or similar
        date_added = self._encode_dos_date(getattr(track, 'date_added', None))

        pdb_track = PDBTrack(
            track_id=track.id,
            file_id=file_id,
            title=track.title or "",
            artist=track.artist or "",
            file_path=str(track.file_path),
            anlz_path=anlz_path,
            duration_ms=int(track.duration * 1000) if track.duration else 0,
            sample_rate=track.sample_rate or 44100,
            date_added=date_added
        )

        self.tracks.append(pdb_track)

    def _encode_dos_date(self, timestamp: Optional[int]) -> int:
        """
        Encode Unix timestamp to DOS date format.

        Reference uses format like 0x24012009 for 2026-01-24
        This appears to be: 0xYYMMDD or similar

        For now, use a default value.
        """
        # TODO: Properly convert timestamp to DOS date format
        # For MVP, use a reasonable default
        return 0x24012009  # 2026-01-24

    def _write_file_header(self) -> bytes:
        """Write file header page (page 0)."""

        header = bytearray(PAGE_SIZE)

        # Magic bytes
        header[0:4] = MAGIC_HEADER

        # Page size
        struct.pack_into('<I', header, 4, PAGE_SIZE)

        # Unknown values from reference
        struct.pack_into('<I', header, 8, 0x14)  # 20
        struct.pack_into('<I', header, 12, 0x39)  # 57

        # Table entries (simplified for MVP)
        # These map table IDs to page numbers
        # For MVP, use minimal table structure
        offset = 0x10

        # Track table entry
        struct.pack_into('<I', header, offset, 1)      # Table ID
        struct.pack_into('<I', header, offset + 4, 2)  # Page number (page 2)
        offset += 8

        # Rest of header entries (placeholder pattern from reference)
        # These would be proper table entries in a full implementation
        entries = [
            (56, 1), (55, 1), (48, 3), (4, 2), (47, 5),
            (6, 3), (49, 7), (8, 4), (10, 9), (9, 5)
        ]

        for val1, val2 in entries:
            struct.pack_into('<I', header, offset, val1)
            struct.pack_into('<I', header, offset + 4, val2)
            offset += 8

            if offset >= 0x100:
                break

        return bytes(header)

    def _create_track_row(self, track: PDBTrack) -> bytes:
        """
        Create a track row with fixed fields and embedded strings.

        Based on observed structure from reference file.
        """

        # Fixed-width section (approximately 84 bytes)
        fixed = bytearray(0x54)  # 84 bytes

        # Offset 0x00: Flags
        fixed[0:4] = b'\x00\x00\x00\x00'

        # Offset 0x04: Track ID
        struct.pack_into('<I', fixed, 0x04, track.track_id)

        # Offset 0x08: Unknown (0)
        struct.pack_into('<I', fixed, 0x08, 0)

        # Offset 0x0C: Secondary ID (use file_id for now)
        struct.pack_into('<I', fixed, 0x0C, track.file_id)

        # Offset 0x10: File ID
        struct.pack_into('<I', fixed, 0x10, track.file_id)

        # Offset 0x14: Unknown (0)
        struct.pack_into('<I', fixed, 0x14, 0)

        # Offset 0x18: Date (DOS format)
        struct.pack_into('<I', fixed, 0x18, track.date_added)

        # Offset 0x1C: Unknown (from reference: 0x0ecc00f6)
        struct.pack_into('<I', fixed, 0x1C, 0x0ecc00f6)

        # Offset 0x20: Duration (ms)
        struct.pack_into('<I', fixed, 0x20, track.duration_ms)

        # Offset 0x24: Unknown (0)
        struct.pack_into('<I', fixed, 0x24, 0)

        # Offset 0x28: Unknown (36 in reference)
        struct.pack_into('<I', fixed, 0x28, 36)

        # Offset 0x2C: Unknown (0x000c0700 in reference)
        struct.pack_into('<I', fixed, 0x2C, 0x00070c00)

        # Offset 0x30: Sample rate
        struct.pack_into('<I', fixed, 0x30, track.sample_rate)

        # Offset 0x34+: More unknown fields
        # Use placeholder values from reference
        struct.pack_into('<I', fixed, 0x34, 0x00000002)
        struct.pack_into('<I', fixed, 0x38, 0x28fa5d00)
        struct.pack_into('<I', fixed, 0x3C, 0xe6101b0b)
        struct.pack_into('<I', fixed, 0x40, 0xda63ef52)
        struct.pack_into('<I', fixed, 0x44, 0x00000001)
        struct.pack_into('<I', fixed, 0x48, 0x00000001)
        struct.pack_into('<I', fixed, 0x4C, 0x00000001)
        struct.pack_into('<I', fixed, 0x50, 0xc7071000)

        # Variable-width string section
        strings = self._encode_strings(track)

        # Combine fixed and string sections
        row = bytes(fixed) + strings

        return row

    def _encode_strings(self, track: PDBTrack) -> bytes:
        """
        Encode string section for track row.

        Based on observed pattern from reference.
        """

        strings = bytearray()

        # Prefix data (observed in reference)
        # Use append instead of pack_into for dynamic buffer
        strings += b'\x00\x00\x00\x00'
        strings += struct.pack('<I', 0x000000d2)
        strings += struct.pack('<I', 0x00000001)
        strings += struct.pack('<I', 0x00002563)
        strings += struct.pack('<I', 0x00000001)
        strings += struct.pack('<I', 0x00000001)
        strings += struct.pack('<I', 0x00000001)
        strings += struct.pack('<I', 0x00000001)
        strings += struct.pack('<I', 0x00000001)
        strings += struct.pack('<I', 0x00000000)
        strings += struct.pack('<I', 0xc7071000)
        strings += struct.pack('<I', 0x000029eb)
        strings += struct.pack('<I', 0x00000001)
        strings += struct.pack('<I', 0x00000003)

        # String offset table (observed in reference)
        # These appear to be offsets or indices
        offsets = [0x88, 0x89, 0x8a, 0x8b, 0x8d, 0x8e, 0x8f, 0x90,
                   0x91, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0xc3,
                   0xce, 0xcf, 0xda, 0xdb]

        for offset in offsets:
            strings += struct.pack('<H', offset)

        # String type/length indicators (from reference)
        strings += bytes([0x06, 0x01, 0x03, 0x03, 0x03, 0x05])
        strings += bytes([0x31])  # String prefix
        strings += b'\x03' * 10  # Padding

        # ANLZ path
        anlz_bytes = track.anlz_path.encode('utf-8')
        strings += anlz_bytes

        # Separator (0x59 = 'Y' in ASCII, but used as separator here)
        strings += bytes([0x59])

        # Date string
        date_str = f"{track.date_added:08x}"
        # Convert DOS date to readable format
        # For 0x24012009 → "2026-01-24"
        year = ((track.date_added >> 24) & 0xFF) + 2000
        month = (track.date_added >> 16) & 0xFF
        day = (track.date_added >> 8) & 0xFF
        date_readable = f"{year:04d}-{month:02d}-{day:02d}"

        strings += bytes([0x17])  # Separator
        strings += date_readable.encode('utf-8')
        strings += bytes([0x03])  # Separator

        # Artist/title
        title_artist = f"{track.title}\x03{track.artist}\x03"
        strings += title_artist.encode('utf-8')

        # File path
        strings += bytes([0xbb])  # Separator
        strings += track.file_path.encode('utf-8')
        strings += b'\x00\x00\x00'  # Null termination

        return bytes(strings)

    def write(self) -> None:
        """
        Write the complete PDB file.

        Generates export.pdb with proper page structure.
        """

        output_file = self.pioneer_path / "export.pdb"

        logger.info(f"Writing PDB file: {output_file}")
        logger.info(f"Tracks: {len(self.tracks)}")

        with open(output_file, 'wb') as f:
            # Write file header (page 0)
            f.write(self._write_file_header())

            # Write page 1 (placeholder, empty for now)
            page1 = bytearray(PAGE_SIZE)
            f.write(bytes(page1))

            # Write track data page (page 2)
            track_page = bytearray(PAGE_SIZE)

            offset = 0
            for track in self.tracks:
                row = self._create_track_row(track)

                if offset + len(row) > PAGE_SIZE:
                    # Would need another page, but for MVP assume fits
                    logger.warning("Track data exceeds page size")
                    break

                track_page[offset:offset + len(row)] = row
                offset += len(row)

            # Pad remainder of page with zeros
            if offset < PAGE_SIZE:
                track_page[offset:] = b'\x00' * (PAGE_SIZE - offset)

            f.write(bytes(track_page))

            logger.debug(f"Wrote track page: {offset} bytes")

        logger.info("PDB file written successfully")


def convert_tracks_to_pdb(
    tracks: List[Track],
    output_path: Path,
    anlz_paths: Dict[int, str]
) -> None:
    """
    Convert OneLibrary tracks to PDB file.

    Args:
        tracks: List of tracks from OneLibrary
        output_path: Path to output directory
        anlz_paths: Mapping of track ID to ANLZ path
    """

    writer = PDBWriterV2(output_path)

    # Assign sequential file IDs
    file_id = 1
    for track in tracks:
        anlz_path = anlz_paths.get(track.id, f"/PIONEER/USBANLZ/P001/DEFAULT/ANLZ0000.DAT")
        writer.add_track(track, file_id, anlz_path)
        file_id += 1

    writer.write()
