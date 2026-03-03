"""
REX-Compliant PDB Writer (Version 3)

Orchestrates file header, table pointers, and page generation.
"""

import struct
from pathlib import Path
from typing import Dict, List, Optional

from .page import DataPage, IndexPage, PageType
from .track import TrackRow
from .metadata_rows import (
    GenreRow, ArtistRow, AlbumRow,
    LabelRow, KeyRow, ColorRow,
    PlaylistTreeRow, PlaylistEntryRow
)


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
        self.sequence_number = 1  # Sequence number for file header (FIX #5)

    def add_track(self, track) -> int:
        """Add track to Tracks table.

        FIX #2: First page of each table is now an index page.

        Args:
            track: Parsed track from OneLibrary

        Returns:
            Row index where track was inserted
        """
        table_type = 'Tracks'

        # FIX #2: Create index page if this is the first row for this table
        if table_type not in self.pages:
            # Create index page as first page
            index_page = IndexPage(page_index=0, page_type=PageType.TRACKS)
            self.pages[table_type] = [index_page]

        # Get or create data page (starts from index 1, not 0)
        pages = self.pages[table_type]

        # FIX #2: If we only have index page, create first data page
        if len(pages) == 1:
            data_page = DataPage(page_index=1, page_type=PageType.TRACKS)
            pages.append(data_page)
            # Add this data page to index
            index_page = pages[0]
            index_page.add_entry(1)  # Point to data page 1

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
            # FIX #2: Add new data page to index
            index_page = pages[0]
            index_page.add_entry(len(pages) - 1)  # Point to new data page
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

        # Create playlist tree row
        row = PlaylistTreeRow(
            playlist_id=playlist.id,
            name=playlist.name,
            parent_id=playlist.parent_id or 0,
            is_folder=playlist.is_folder,
            track_count=len(playlist.track_ids) if not playlist.is_folder else 0,
            sequence_no=playlist.id  # Use ID as sequence for now
        )
        row_index = len(self.pages.get('PlaylistTree', [])) * 16
        row_data = row.marshal_binary(row_index)

        return self._add_metadata_row('PlaylistTree', PageType.PLAYLIST_TREE, row_data)

    def add_playlist_entry(self, track_id: int, playlist_id: int, sequence_no: int = 0) -> int:
        """Add track to playlist in PlaylistEntries table.

        Args:
            track_id: Track ID
            playlist_id: Playlist ID
            sequence_no: Track order within playlist

        Returns:
            Row index where entry was inserted
        """
        table_type = 'PlaylistEntries'

        # Create page if needed
        if table_type not in self.pages:
            self.pages[table_type] = [DataPage(page_index=0, page_type=PageType.PLAYLIST_ENTRIES)]

        # Create playlist entry row
        row = PlaylistEntryRow(
            track_id=track_id,
            playlist_id=playlist_id,
            sequence_no=sequence_no
        )
        row_index = len(self.pages.get('PlaylistEntries', [])) * 16
        row_data = row.marshal_binary(row_index)

        return self._add_metadata_row('PlaylistEntries', PageType.PLAYLIST_ENTRIES, row_data)

    def _add_metadata_row(self, table_type: str, page_type: int, row_data: bytes) -> int:
        """Add a metadata row to a metadata table.

        FIX #2: First page of each table is now an index page.

        Args:
            table_type: Table name (e.g., 'Genres', 'Artists')
            page_type: PageType enum value
            row_data: Serialized row bytes

        Returns:
            Row index where row was inserted
        """
        # FIX #2: Create index page if this is the first row for this table
        if table_type not in self.pages:
            # Create index page as first page
            index_page = IndexPage(page_index=0, page_type=page_type)
            self.pages[table_type] = [index_page]

        # Get or create data page (starts from index 1, not 0)
        pages = self.pages[table_type]

        # FIX #2: If we only have index page, create first data page
        if len(pages) == 1:
            data_page = DataPage(page_index=1, page_type=page_type)
            pages.append(data_page)
            # Add this data page to index
            index_page = pages[0]
            index_page.add_entry(1)  # Point to data page 1

        # Get current page
        current_page = pages[-1]

        # Estimate row size including alignment and RowSet overhead
        row_index = current_page.header.num_rows_small // 0x20
        estimated_size = len(row_data) + 4 + (36 if (row_index % 16) == 0 else 0)

        # Check if page has space
        if current_page.heap.free_size() < estimated_size + 100:
            # Need new page
            new_page = DataPage(page_index=len(pages), page_type=page_type)
            new_page.header.next_page = 0xFFFFFFFF
            current_page.header.next_page = len(pages)
            pages.append(new_page)
            # FIX #2: Add new data page to index
            index_page = pages[0]
            index_page.add_entry(len(pages) - 1)  # Point to new data page
            current_page = new_page

        # Insert row
        return current_page.insert_row(row_data)

    def add_genre(self, genre_id: int, name: str) -> int:
        """Add genre to Genres table (table type 1).

        Args:
            genre_id: Genre ID
            name: Genre name

        Returns:
            Row index where genre was inserted
        """
        row = GenreRow(genre_id=genre_id, name=name)
        row_index = len(self.pages.get('Genres', [])) * 16  # Approximate
        row_data = row.marshal_binary(row_index)
        return self._add_metadata_row('Genres', PageType.GENRES, row_data)

    def add_artist(self, artist_id: int, name: str) -> int:
        """Add artist to Artists table (table type 2).

        Args:
            artist_id: Artist ID
            name: Artist name

        Returns:
            Row index where artist was inserted
        """
        row = ArtistRow(artist_id=artist_id, name=name)
        row_index = len(self.pages.get('Artists', [])) * 16
        row_data = row.marshal_binary(row_index)
        return self._add_metadata_row('Artists', PageType.ARTISTS, row_data)

    def add_album(self, album_id: int, name: str, artist_id: int = 0) -> int:
        """Add album to Albums table (table type 3).

        Args:
            album_id: Album ID
            name: Album name
            artist_id: Artist ID reference

        Returns:
            Row index where album was inserted
        """
        row = AlbumRow(album_id=album_id, name=name, artist_id=artist_id)
        row_index = len(self.pages.get('Albums', [])) * 16
        row_data = row.marshal_binary(row_index)
        return self._add_metadata_row('Albums', PageType.ALBUMS, row_data)

    def add_label(self, label_id: int, name: str) -> int:
        """Add label to Labels table (table type 4).

        Args:
            label_id: Label ID
            name: Label name

        Returns:
            Row index where label was inserted
        """
        row = LabelRow(label_id=label_id, name=name)
        row_index = len(self.pages.get('Labels', [])) * 16
        row_data = row.marshal_binary(row_index)
        return self._add_metadata_row('Labels', PageType.LABELS, row_data)

    def add_key(self, key_id: int, name: str) -> int:
        """Add key to Keys table (table type 5).

        Args:
            key_id: Key ID
            name: Key name (e.g., "C maj", "A min")

        Returns:
            Row index where key was inserted
        """
        row = KeyRow(key_id=key_id, name=name)
        row_index = len(self.pages.get('Keys', [])) * 16
        row_data = row.marshal_binary(row_index)
        return self._add_metadata_row('Keys', PageType.KEYS, row_data)

    def add_color(self, color_id: int, name: str, color_rgb: int = 0) -> int:
        """Add color to Colors table (table type 6).

        Args:
            color_id: Color ID
            name: Color name
            color_rgb: RGB color value

        Returns:
            Row index where color was inserted
        """
        row = ColorRow(color_id=color_id, name=name, color_rgb=color_rgb)
        row_index = len(self.pages.get('Colors', [])) * 16
        row_data = row.marshal_binary(row_index)
        return self._add_metadata_row('Colors', PageType.COLORS, row_data)

    def _ensure_all_tables_exist(self) -> None:
        """Ensure all 20 tables have at least placeholder pages.

        Rekordbox creates pages for all tables even when empty.
        Most tables have 2 pages (first + continuation), some have 1.
        """
        import struct

        # Tables that typically have 2 pages even when empty
        two_page_tables = {
            'Tracks', 'Genres', 'Artists', 'Albums', 'Keys', 'Colors',
            'PlaylistTree', 'PlaylistEntries', 'Artwork', 'Columns',
            'Unknown17', 'Unknown18', 'History'
        }

        # Tables that typically have 1 page
        one_page_tables = {
            'Labels', 'Unknown9', 'Unknown10', 'HistoryPlaylists',
            'HistoryEntries', 'Unknown14', 'Unknown15'
        }

        for table_type in self.TABLE_TYPES:
            if table_type not in self.pages or not self.pages[table_type]:
                # Table is missing, create placeholder page(s)
                if table_type in two_page_tables:
                    # Create 2 placeholder pages
                    self._create_placeholder_pages(table_type, 2)
                elif table_type in one_page_tables:
                    # Create 1 placeholder page
                    self._create_placeholder_pages(table_type, 1)
                else:
                    # Default to 1 page
                    self._create_placeholder_pages(table_type, 1)
            else:
                # Table exists, ensure it has enough pages
                current_pages = len(self.pages[table_type])
                min_pages = 2 if table_type in two_page_tables else 1

                if current_pages < min_pages:
                    # Add continuation page(s)
                    for _ in range(min_pages - current_pages):
                        self._create_placeholder_pages(table_type, 1, is_continuation=True)

    def _create_placeholder_pages(self, table_type: str, count: int, is_continuation: bool = False) -> None:
        """Create placeholder page(s) for an empty table.

        FIX #2: First page is now an IndexPage, subsequent pages are DataPages.

        Args:
            table_type: Table type name
            count: Number of placeholder pages to create
            is_continuation: True if this is a continuation page
        """
        # Map table type to PageType
        page_type_map = {
            'Tracks': PageType.TRACKS,
            'Genres': PageType.GENRES,
            'Artists': PageType.ARTISTS,
            'Albums': PageType.ALBUMS,
            'Labels': PageType.LABELS,
            'Keys': PageType.KEYS,
            'Colors': PageType.COLORS,
            'PlaylistTree': PageType.PLAYLIST_TREE,
            'PlaylistEntries': PageType.PLAYLIST_ENTRIES,
            'Unknown9': PageType.UNKNOWN9,
            'Unknown10': PageType.UNKNOWN10,
            'HistoryPlaylists': PageType.HISTORY_PLAYLISTS,
            'HistoryEntries': PageType.HISTORY_ENTRIES,
            'Artwork': PageType.ARTWORK,
            'Unknown14': PageType.UNKNOWN14,
            'Unknown15': PageType.UNKNOWN15,
            'Columns': PageType.COLUMNS,
            'Unknown17': PageType.UNKNOWN17,
            'Unknown18': PageType.UNKNOWN18,
            'History': PageType.HISTORY,
        }

        page_type = page_type_map.get(table_type, PageType.UNKNOWN9)

        # Add to table's page list if needed
        if table_type not in self.pages:
            self.pages[table_type] = []

        for i in range(count):
            # FIX #2: First page should be an IndexPage
            if i == 0 and not is_continuation:
                # Create index page as first page
                page = IndexPage(page_index=0, page_type=page_type)
                # Index page has no entries for empty tables
            else:
                # Continuation data pages
                # Determine page flags
                table_index = self.TABLE_TYPES.index(table_type)
                flags = 0x90 if table_index % 2 == 1 else 0x01

                # Create empty DataPage
                page = DataPage(page_index=0, page_type=page_type)
                page.header.num_rows_small = 0  # Empty
                page.header.page_flags = flags
                page.header.next_page = 0  # No next page for placeholder

            self.pages[table_type].append(page)

    def _update_page_indices(self) -> None:
        """Update page_index in each page's header to match actual file position.

        This is critical! The page_index stored in each page header must match
        the actual page number in the file, otherwise rekordbox can't find pages.
        """
        current_page_index = 1  # Page 0 is the file header

        for table_type in self.TABLE_TYPES:
            if table_type in self.pages:
                for page in self.pages[table_type]:
                    page.header.page_index = current_page_index
                    current_page_index += 1

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

        # Empty candidate values from reference PDB
        # These appear to be allocation hints for expanding tables
        # Format: [table_index] -> empty_candidate_value
        REFERENCE_EMPTY_CANDIDATES = {
            0: 50,   # Tracks
            1: 53,   # Genres
            2: 47,   # Artists
            3: 48,   # Albums
            4: None, # Labels (single-page: use last+1)
            5: 49,   # Keys
            6: 42,   # Colors
            7: 46,   # PlaylistTree
            8: 52,   # PlaylistEntries
            9: None, # Unknown9 (single-page)
            10: None, # Unknown10 (single-page)
            11: None, # HistoryPlaylists (single-page)
            12: None, # HistoryEntries (single-page)
            13: 51,   # Artwork
            14: None, # Unknown14 (single-page)
            15: None, # Unknown15 (single-page)
            16: 43,   # Columns
            17: 44,   # Unknown17
            18: 45,   # Unknown18
            19: 41,   # History
        }

        for table_type in self.TABLE_TYPES:
            table_idx = self.TABLE_TYPES.index(table_type)
            if table_type in self.pages:
                pages = self.pages[table_type]
                last_page = current_page_index + len(pages) - 1

                # Calculate empty_candidate
                ref_empty = REFERENCE_EMPTY_CANDIDATES.get(table_idx)
                if ref_empty is not None:
                    # Use reference value for multi-page tables
                    empty_candidate = ref_empty
                else:
                    # For single-page tables: empty_candidate = last_page + 1
                    empty_candidate = last_page + 1

                table_pointers.append({
                    'type': table_idx,
                    'first_page': current_page_index,
                    'last_page': last_page,
                    'empty_candidate': empty_candidate
                })
                current_page_index += len(pages)
            else:
                # Empty table - point to itself
                table_pointers.append({
                    'type': table_idx,
                    'first_page': 0,
                    'last_page': 0,
                    'empty_candidate': 0
                })

        # Build file header
        # First 28 bytes
        header = bytearray()
        header += struct.pack('<I', 0x00000000)  # Magic
        header += struct.pack('<I', 4096)  # Page size
        header += struct.pack('<I', len(self.TABLE_TYPES))  # Num tables
        header += struct.pack('<I', current_page_index)  # Next unused page
        header += struct.pack('<I', 0x1)  # Unknown1 - FIXED: was 0x5, reference uses 0x1
        header += struct.pack('<I', self.sequence_number)  # Unknown2/Build - FIX #5: Use incrementing sequence
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
        # Ensure all 20 tables exist (add placeholder pages for missing tables)
        # This matches rekordbox behavior where all tables are allocated
        self._ensure_all_tables_exist()

        # Update page indices before marshaling
        # This is critical: page_index in page header must match actual file position
        self._update_page_indices()

        # Build file header
        file_header = self._build_file_header()

        # Write all pages
        pdb_data = bytearray(file_header)

        for table_type in self.TABLE_TYPES:
            if table_type in self.pages:
                for page in self.pages[table_type]:
                    # FIX #2: Both IndexPage and DataPage have marshal_binary()
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
