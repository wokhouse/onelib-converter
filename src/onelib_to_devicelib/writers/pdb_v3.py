"""
REX-Compliant PDB Writer (Version 3)

Orchestrates file header, table pointers, and page generation.
"""

import struct
from pathlib import Path
from typing import Dict, List, Optional

from .page import DataPage, PageType
from .track import TrackRow


class PDBWriterV3:
    """REX-compliant PDB writer.

    This writer generates PDB files that follow the complete format
    specification from the REX project and Deep-Symmetry analysis.
    """

    # Table type enumeration (must match order in PDB file)
    TABLE_TYPES = [
        'Tracks',          # 0
        'Genres',          # 1
        'Artists',         # 2
        'Albums',          # 3
        'Labels',          # 4
        'Keys',            # 5
        'Colors',          # 6
        'PlaylistTree',    # 7
        'PlaylistEntries', # 8
        'Unknown9',        # 9
        'Unknown10',       # 10
        'HistoryPlaylists',# 11
        'HistoryEntries',  # 12
        'Artwork',         # 13
        'Unknown14',       # 14
        'Unknown15',       # 15
        'Columns',         # 16
        'Unknown17',       # 17
        'Unknown18',       # 18
        'History'          # 19
    ]

    def __init__(self, output_dir: Path):
        """Initialize PDB writer.

        Args:
            output_dir: Directory to write PDB file to
        """
        self.output_dir = output_dir
        self.pages: Dict[str, List[DataPage]] = {}
        self.table_pointers: Dict[str, Dict] = {}

    def add_track(self, track) -> int:
        """Add track to Tracks table.

        Args:
            track: Parsed track from OneLibrary

        Returns:
            Row index where track was inserted
        """
        table_type = 'Tracks'

        # Create page if needed
        if table_type not in self.pages:
            self.pages[table_type] = [DataPage(page_index=0, page_type=PageType.TRACKS)]

        # Get current page
        pages = self.pages[table_type]
        current_page = pages[-1]

        # Create track row to check size
        track_row = TrackRow(track)
        row_index = current_page.header.num_rows_small // 0x20
        row_data = track_row.marshal_binary(row_index)

        # Estimate row size including alignment and RowSet overhead
        # Row data + 4-byte alignment + potential RowSet (36 bytes per 16 rows)
        estimated_size = len(row_data) + 4 + (36 if (row_index % 16) == 0 else 0)

        # Check if page has space
        # Need space for:
        # - Row data (aligned to 4 bytes)
        # - Row index grows from bottom (36 bytes per RowSet)
        # - We need at least 100 bytes free for safety margin
        if current_page.heap.free_size() < estimated_size + 100:
            # Need new page
            new_page = DataPage(page_index=len(pages), page_type=PageType.TRACKS)
            new_page.header.next_page = 0xFFFFFFFF
            current_page.header.next_page = len(pages)
            pages.append(new_page)
            current_page = new_page
            # Recalculate row index for new page
            row_index = current_page.header.num_rows_small // 0x20
            row_data = track_row.marshal_binary(row_index)

        # Insert row
        return current_page.insert_row(row_data)

    def add_playlist(self, playlist):
        """Add playlist/folder to PlaylistTree table.

        Args:
            playlist: Parsed playlist from OneLibrary

        Returns:
            Row index where playlist was inserted
        """
        table_type = 'PlaylistTree'

        # Create page if needed
        if table_type not in self.pages:
            self.pages[table_type] = [DataPage(page_index=0, page_type=PageType.PLAYLIST_TREE)]

        # TODO: Implement playlist row structure
        # For now, just create an empty page
        return 0

    def _build_file_header(self) -> bytes:
        """Build PDB file header.

        The file header occupies the first page (4096 bytes).
        It contains:
        - Magic and page info (28 bytes)
        - Table pointers (16 bytes × num_tables)
        - Padding to 4096 bytes

        Returns:
            4096-byte file header
        """
        # Build table pointers
        table_pointers = []

        # Track which page index each table starts at
        current_page_index = 1  # Page 0 is the file header

        for table_type in self.TABLE_TYPES:
            if table_type in self.pages:
                pages = self.pages[table_type]
                table_pointers.append({
                    'type': self.TABLE_TYPES.index(table_type),
                    'first_page': current_page_index,
                    'last_page': current_page_index + len(pages) - 1,
                    'empty_candidate': 0
                })
                current_page_index += len(pages)
            else:
                # Empty table - point to itself
                table_pointers.append({
                    'type': self.TABLE_TYPES.index(table_type),
                    'first_page': 0,
                    'last_page': 0,
                    'empty_candidate': 1
                })

        # Build file header
        # First 28 bytes
        header = bytearray()
        header += struct.pack('<I', 0x00000000)  # Magic
        header += struct.pack('<I', 4096)  # Page size
        header += struct.pack('<I', len(self.TABLE_TYPES))  # Num tables
        header += struct.pack('<I', current_page_index)  # Next unused page
        header += struct.pack('<I', 0x5)  # Unknown1
        header += struct.pack('<I', 1)  # Sequence
        header += struct.pack('<I', 0x00000000)  # Gap

        # Table pointers (16 bytes each)
        for tp in table_pointers:
            header += struct.pack('<IIII',
                tp['type'], tp['empty_candidate'],
                tp['first_page'], tp['last_page'])

        # Pad to page size
        header += b'\x00' * (4096 - len(header))

        return bytes(header)

    def finalize(self) -> int:
        """Build file header and write PDB file.

        Returns:
            Size of written PDB file in bytes
        """
        # Build file header
        file_header = self._build_file_header()

        # Write all pages
        pdb_data = bytearray(file_header)

        for table_type in self.TABLE_TYPES:
            if table_type in self.pages:
                for page in self.pages[table_type]:
                    pdb_data += page.marshal_binary()

        # Write file
        output_path = self.output_dir / "PIONEER" / "rekordbox" / "export.pdb"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(pdb_data)

        return len(pdb_data)

    def get_stats(self) -> Dict:
        """Get statistics about the PDB file.

        Returns:
            Dictionary with file statistics
        """
        stats = {
            'tables': {},
            'total_pages': 1  # File header
        }

        for table_type in self.TABLE_TYPES:
            if table_type in self.pages:
                pages = self.pages[table_type]
                total_rows = sum(p.header.num_rows_small // 0x20 for p in pages)
                stats['tables'][table_type] = {
                    'num_pages': len(pages),
                    'total_rows': total_rows
                }
                stats['total_pages'] += len(pages)
            else:
                stats['tables'][table_type] = {
                    'num_pages': 0,
                    'total_rows': 0
                }

        stats['estimated_file_size'] = stats['total_pages'] * 4096

        return stats
