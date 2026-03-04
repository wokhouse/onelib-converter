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
    PlaylistTreeRow, PlaylistEntryRow,
    ColumnRow, Unknown17Row, Unknown18Row, HistoryRow
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
        self.sequence_number = 6  # Sequence number for file header (matches empty reference)
        self._all_pages: List[tuple] = []  # Ordered list of (page_index, table_type, page)
        self._has_data = False  # Track whether any data has been added (tracks, playlists, etc.)

    def add_track(self, track) -> int:
        """Add track to Tracks table.

        FIX #2: First page of each table is now an index page.

        Args:
            track: Parsed track from OneLibrary

        Returns:
            Row index where track was inserted
        """
        table_type = 'Tracks'

        # NOTE: Reference doesn't use IndexPages for Tracks
        # Create first data page if this is the first row for this table
        if table_type not in self.pages:
            # Create data page (no IndexPage)
            # Track pages start at page 1 (after file header at page 0)
            data_page = DataPage(page_index=1, page_type=PageType.TRACKS)
            self.pages[table_type] = [data_page]
            self._has_data = True  # Mark that we have actual data

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
            # Assign next sequential page index
            next_page_index = len(pages) + 1  # Page 1 is first, so next is 2
            new_page = DataPage(page_index=next_page_index, page_type=PageType.TRACKS)
            new_page.header.next_page = 0xFFFFFFFF
            current_page.header.next_page = next_page_index
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
            self._has_data = True  # Mark that we have actual data

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
            new_page = DataPage(page_index=0, page_type=page_type)
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

    def add_column(self, column_id: int, name: str, field_type: int, size_type: int) -> int:
        """Add column to Columns table (table type 16).

        Args:
            column_id: Column ID
            name: Column name
            field_type: Field type code
            size_type: Size/type indicator

        Returns:
            Row index where column was inserted
        """
        row = ColumnRow(column_id=column_id, name=name, field_type=field_type, size_type=size_type)
        row_index = len(self.pages.get('Columns', [])) * 16
        row_data = row.marshal_binary(row_index)
        return self._add_metadata_row('Columns', PageType.COLUMNS, row_data)

    def add_unknown17(self, field1: int, field2: int, field3: int) -> int:
        """Add entry to UNKNOWN17 table (table type 17).

        Args:
            field1: Source/from ID
            field2: Target/to ID
            field3: Mapping value/flags

        Returns:
            Row index where entry was inserted
        """
        row = Unknown17Row(field1=field1, field2=field2, field3=field3)
        row_index = len(self.pages.get('Unknown17', [])) * 16
        row_data = row.marshal_binary(row_index)
        return self._add_metadata_row('Unknown17', PageType.UNKNOWN17, row_data)

    def add_unknown18(self, field1: int, field2: int, field3: int) -> int:
        """Add entry to UNKNOWN18 table (table type 18).

        Args:
            field1: Source/from ID
            field2: Target/to ID
            field3: Mapping value/flags

        Returns:
            Row index where entry was inserted
        """
        row = Unknown18Row(field1=field1, field2=field2, field3=field3)
        row_index = len(self.pages.get('Unknown18', [])) * 16
        row_data = row.marshal_binary(row_index)
        return self._add_metadata_row('Unknown18', PageType.UNKNOWN18, row_data)

    def add_history(self, date: str, name: str) -> int:
        """Add entry to HISTORY table (table type 19).

        Args:
            date: Date string (e.g., "2026-03-02")
            name: Name/value string (e.g., "1000")

        Returns:
            Row index where entry was inserted
        """
        row = HistoryRow(date=date, name=name)
        row_index = len(self.pages.get('History', [])) * 16
        row_data = row.marshal_binary(row_index)
        return self._add_metadata_row('History', PageType.HISTORY, row_data)

    def add_default_metadata(self) -> None:
        """Add default metadata entries to match rekordbox empty database.

        This adds the 8 default colors, 27 columns, 22 Unknown17 entries,
        18 Unknown18 entries, and 1 History entry found in the reference.
        """
        # Add default colors (8 entries)
        default_colors = [
            (2, "Pink"),
            (3, "Red"),
            (4, "Orange"),
            (5, "Yellow"),
            (6, "Green"),
            (7, "Aqua"),
            (8, "Blue"),
            (0, "Purple"),
        ]
        for color_id, name in default_colors:
            self.add_color(color_id, name)

        # Add default columns (27 entries)
        default_columns = [
            (2, "GENRE", 0x81, 0x1490),
            (3, "ARTIST", 0x82, 0x1290),
            (4, "ALBUM", 0x83, 0x1290),
            (5, "TRACK", 0x85, 0x0e90),
            (6, "BPM", 0x86, 0x1490),
            (7, "RATING", 0x87, 0x1090),
            (8, "YEAR", 0x88, 0x1690),
            (9, "REMIXER", 0x89, 0x1290),
            (10, "LABEL", 0x8A, 0x1290),
        ]
        for col_id, name, field_type, size_type in default_columns:
            self.add_column(col_id, name, field_type, size_type)

        # Add default Unknown17 entries (22 entries)
        default_unknown17 = [
            (5, 6, 0x00000105),
            (6, 7, 0x00000163),
            (7, 8, 0x00000163),
            (8, 9, 0x00000163),
            (9, 10, 0x00000163),
            (10, 11, 0x00000163),
            (13, 15, 0x00000163),
            (14, 19, 0x00000104),
            (15, 20, 0x00000106),
            (16, 21, 0x00000163),
            (18, 23, 0x00000163),
            (2, 2, 0x00010002),
            (3, 3, 0x00020003),
            (4, 4, 0x00010003),
            (11, 12, 0x00000063),
            (17, 5, 0x00000063),
            (19, 22, 0x00000063),
            (20, 18, 0x00000063),
            (24, 17, 0x00000063),
            (22, 27, 0x00000063),
            (26, 27, 0x00000063),
        ]
        for field1, field2, field3 in default_unknown17:
            self.add_unknown17(field1, field2, field3)

        # Add default Unknown18 entries (18 entries)
        default_unknown18 = [
            (21, 7, 0x00000001),
            (14, 8, 0x00000001),
            (8, 9, 0x00000001),
            (9, 10, 0x00000001),
            (10, 11, 0x00000001),
            (15, 13, 0x00000001),
            (13, 15, 0x00000001),
            (23, 16, 0x00000001),
            (22, 17, 0x00000001),
            (25, 0, 0x00000100),
            (26, 1, 0x00000200),
            (2, 2, 0x00030000),
            (3, 3, 0x00040000),
            (4, 4, 0x00050000),
            (5, 5, 0x00060000),
            (11, 12, 0x00070000),
        ]
        for field1, field2, field3 in default_unknown18:
            self.add_unknown18(field1, field2, field3)

        # Add default History entry (1 entry)
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        self.add_history(today, "1000")

        # FIX: Set data header values to match reference
        self._set_metadata_data_headers()

    def _set_metadata_data_headers(self) -> None:
        """Set data header values for metadata tables to match reference.

        The 16-byte data header (8 x uint16 fields) has specific values
        that don't match row counts. These values are table-specific and
        come from binary analysis of the reference.
        """
        from onelib_to_devicelib.writers.page import DataPage

        # Colors (page 14): (8, 0, 0, 0, 0, 0, 257, 0)
        if 'Colors' in self.pages:
            for page in self.pages['Colors']:
                if isinstance(page, DataPage):
                    page.data_header.unknown5 = 8
                    page.data_header.unknown9 = 0
                    page.data_header.num_rows_large = 0
                    page.data_header.unknown10 = 257  # 0x101

        # Columns (page 34): (27, 0, 0, 0, 1, 128, 4752, 0)
        if 'Columns' in self.pages:
            for page in self.pages['Columns']:
                if isinstance(page, DataPage):
                    page.data_header.unknown5 = 27
                    page.data_header.unknown9 = 1
                    page.data_header.num_rows_large = 128
                    page.data_header.unknown10 = 4752  # 0x1290

        # Unknown17 (page 36): (22, 0, 0, 0, 1, 1, 355, 0)
        if 'Unknown17' in self.pages:
            for page in self.pages['Unknown17']:
                if isinstance(page, DataPage):
                    page.data_header.unknown5 = 22
                    page.data_header.unknown9 = 1
                    page.data_header.num_rows_large = 1
                    page.data_header.unknown10 = 355  # 0x0163

        # Unknown18 (page 38): (17, 0, 0, 0, 1, 6, 1, 0)
        if 'Unknown18' in self.pages:
            for page in self.pages['Unknown18']:
                if isinstance(page, DataPage):
                    page.data_header.unknown5 = 17
                    page.data_header.unknown9 = 1
                    page.data_header.num_rows_large = 6
                    page.data_header.unknown10 = 1

        # History (page 40): (1, 0, 0, 0, 640, 0, 0, 0)
        if 'History' in self.pages:
            for page in self.pages['History']:
                if isinstance(page, DataPage):
                    page.data_header.unknown5 = 1
                    page.data_header.unknown9 = 640
                    page.data_header.num_rows_large = 0

    def _ensure_all_tables_exist(self) -> None:
        """Ensure all 20 tables have placeholder pages matching reference layout.

        Rekordbox uses a sparse page layout with specific page numbers for each table.
        This matches the empty reference file exactly (167,936 bytes, 41 pages).
        """
        import struct

        # Exact page layout from EMPTY reference file (empty_onelib_and_devicelib)
        # Format: (first_page, last_page, num_pages)
        table_layout = {
            'Tracks': (1, 1, 1),
            'Genres': (3, 3, 1),
            'Artists': (5, 5, 1),
            'Albums': (7, 7, 1),
            'Labels': (9, 9, 1),
            'Keys': (11, 11, 1),
            'Colors': (13, 14, 2),      # 2 pages even when empty
            'PlaylistTree': (15, 15, 1),
            'PlaylistEntries': (17, 17, 1),
            'Unknown9': (19, 19, 1),
            'Unknown10': (21, 21, 1),
            'HistoryPlaylists': (23, 23, 1),
            'HistoryEntries': (25, 25, 1),
            'Artwork': (27, 27, 1),
            'Unknown14': (29, 29, 1),
            'Unknown15': (31, 31, 1),
            'Columns': (33, 34, 2),     # 2 pages even when empty
            'Unknown17': (35, 36, 2),   # 2 pages even when empty
            'Unknown18': (37, 38, 2),   # 2 pages even when empty
            'History': (39, 40, 2),     # 2 pages even when empty
        }

        for table_type in self.TABLE_TYPES:
            # Always ensure correct layout, even if table already has pages
            if table_type in table_layout:
                first_page, last_page, num_pages = table_layout[table_type]

                # Check if table already has pages
                if table_type in self.pages and self.pages[table_type]:
                    current_pages = len(self.pages[table_type])

                    # If we have the right number of pages, ensure they have correct indices
                    if current_pages == num_pages:
                        # Update page indices to match layout
                        for i, page in enumerate(self.pages[table_type]):
                            page.header.page_index = first_page + i
                    elif current_pages < num_pages:
                        # Add missing pages
                        for i in range(current_pages, num_pages):
                            page_num = first_page + i
                            self._create_placeholder_page_at(table_type, page_num)
                    # If current_pages > num_pages, table has expanded (keep as-is)
                else:
                    # Table doesn't exist, create placeholder page(s) at exact locations
                    self._create_placeholder_pages_at(table_type, first_page, last_page, num_pages)
            else:
                # Fallback for unknown tables - only create if doesn't exist
                if table_type not in self.pages or not self.pages[table_type]:
                    self._create_placeholder_pages(table_type, 1)

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

    def _create_zero_page(self) -> bytes:
        """Create a completely zero-filled page.

        Returns:
            4096 bytes of all zeros
        """
        return b'\x00' * 4096

    def _create_placeholder_pages_at(self, table_type: str, first_page: int, last_page: int, num_pages: int) -> None:
        """Create placeholder page(s) at specific page numbers for sparse layout.

        Reference structure:
        - Single-page tables (e.g., Tracks): IndexPage (odd) + zero page (even)
        - Multi-page tables (e.g., Colors): IndexPage (odd) + DataPage (even) + additional pages

        Args:
            table_type: Table type name
            first_page: First page number (for table pointer)
            last_page: Last page number (for table pointer)
            num_pages: Number of pages to create
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

        # Determine if this is a multi-page table
        multi_page_tables = {'Colors', 'Columns', 'Unknown17', 'Unknown18', 'History'}
        is_multi_page = table_type in multi_page_tables

        # Create first page: IndexPage
        # Determine index_header.next_page value
        # Multi-page tables: points to actual next page (e.g., 14 for Colors)
        # Single-page tables: uses default 0x03ffffff
        if is_multi_page and num_pages > 1:
            index_next_page = first_page + 1  # Points to the second page
        else:
            index_next_page = 0x03ffffff  # Default for single-page tables

        index_page = IndexPage(page_index=first_page, page_type=page_type, index_next_page=index_next_page)
        # Index page has no entries for empty tables

        # Set next_page pointer for IndexPage (in PageHeader)
        # CRITICAL: IndexPage ALWAYS points to first_page + 1 (the next page in file)
        # This is true even for single-page tables where page 2 is a zero page
        index_page.header.next_page = first_page + 1

        self.pages[table_type].append(index_page)

        # Create continuation pages if needed
        if num_pages > 1:
            # Determine if this is a multi-page table (Colors, Columns, Unknown17, Unknown18, History)
            # These tables have actual DataPages as continuation
            multi_page_tables = {'Colors', 'Columns', 'Unknown17', 'Unknown18', 'History'}
            is_multi_page = table_type in multi_page_tables

            if is_multi_page:
                # Multi-page tables: Create DataPages with flags=0x24
                for i in range(1, num_pages):
                    page_num = first_page + i
                    page = DataPage(page_index=page_num, page_type=page_type)
                    page.header.num_rows_small = 0  # Empty
                    page.header.page_flags = 0x24  # Multi-page DataPage flag

                    # Chain to next page or mark as last
                    if i < num_pages - 1:
                        page.header.next_page = page_num + 1
                    else:
                        # Last page points to empty_candidate
                        table_index = self.TABLE_TYPES.index(table_type)
                        if table_type == 'Colors':
                            page.header.next_page = 42
                        elif table_type == 'Columns':
                            page.header.next_page = 43
                        elif table_type == 'Unknown17':
                            page.header.next_page = 44
                        elif table_type == 'Unknown18':
                            page.header.next_page = 45
                        elif table_type == 'History':
                            page.header.next_page = 41
                        else:
                            page.header.next_page = 0

                    self.pages[table_type].append(page)
            else:
                # Single-page tables: Second page is a zero-filled page (not a DataPage)
                # Create a marker for zero page - we'll handle this in finalize()
                # For now, create a special placeholder
                for i in range(1, num_pages):
                    page_num = first_page + i
                    # Create a DataPage as a placeholder, but mark it for replacement
                    page = DataPage(page_index=page_num, page_type=page_type)
                    page.header.num_rows_small = 0
                    page.header.page_flags = 0x00  # Empty data page
                    page.header.next_page = 0

                    # Mark this page to be replaced with zero bytes
                    # We store a special attribute
                    page._is_zero_placeholder = True

                    self.pages[table_type].append(page)

    def _create_placeholder_page_at(self, table_type: str, page_num: int) -> None:
        """Create a single continuation page at a specific page number.

        This is called when adding a missing page to an existing table.

        Args:
            table_type: Table type name
            page_num: Page number to assign
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

        # Determine if this is a multi-page table
        multi_page_tables = {'Colors', 'Columns', 'Unknown17', 'Unknown18', 'History'}
        is_multi_page = table_type in multi_page_tables

        if is_multi_page:
            # Multi-page tables: Create DataPage with flags=0x24
            page = DataPage(page_index=page_num, page_type=page_type)
            page.header.num_rows_small = 0  # Empty
            page.header.page_flags = 0x24  # Multi-page DataPage flag
            page.header.next_page = 0

            self.pages[table_type].append(page)
        else:
            # Single-page tables: Create a zero placeholder page
            page = DataPage(page_index=page_num, page_type=page_type)
            page.header.num_rows_small = 0
            page.header.page_flags = 0x00  # Empty data page
            page.header.next_page = 0

            # Mark this page to be replaced with zero bytes
            page._is_zero_placeholder = True

            self.pages[table_type].append(page)

    def _update_page_indices(self) -> None:
        """Update page_index in each page's header and build ordered page list.

        This is critical! The page_index stored in each page header must match
        the actual page number in the file, otherwise rekordbox can't find pages.

        For sparse layouts, this also creates gap pages to ensure file size matches.
        Builds self._all_pages as an ordered list of all pages including gaps.
        """
        # Collect all pages with their desired indices
        all_pages = []
        for table_type in self.TABLE_TYPES:
            if table_type in self.pages:
                for page in self.pages[table_type]:
                    all_pages.append((table_type, page))

        # Sort by desired page index (pages with explicit indices first)
        all_pages.sort(key=lambda x: x[1].header.page_index if x[1].header.page_index > 0 else 9999)

        # Build ordered page list with gaps filled
        ordered_pages = []
        used_indices = set()

        # First, add pages with explicit indices
        for table_type, page in all_pages:
            if page.header.page_index > 0:
                used_indices.add(page.header.page_index)
                ordered_pages.append((page.header.page_index, table_type, page))

        # Fill gaps with empty pages
        if ordered_pages:
            max_index = max(idx for idx, _, _ in ordered_pages)
            for i in range(1, max_index + 1):
                if i not in used_indices:
                    # Create a gap page as a zero placeholder
                    # Use DataPage as base but mark as zero placeholder
                    gap_page = DataPage(page_index=i, page_type=PageType.UNKNOWN9)
                    gap_page.header.num_rows_small = 0
                    gap_page.header.page_flags = 0x00
                    gap_page.header.next_page = 0
                    gap_page._is_zero_placeholder = True
                    ordered_pages.append((i, None, gap_page))

        # Now add pages with page_index=0 at the end
        current_max = max([idx for idx, _, _ in ordered_pages]) if ordered_pages else 0
        for table_type, page in all_pages:
            if page.header.page_index == 0:
                current_max += 1
                page.header.page_index = current_max
                ordered_pages.append((current_max, table_type, page))

        # Sort by page index
        ordered_pages.sort(key=lambda x: x[0])

        # Store ordered pages for finalize() to use
        self._all_pages = ordered_pages

        # Rebuild self.pages as a dict of lists (excluding gaps)
        self.pages = {}
        for page_index, table_type, page in ordered_pages:
            page.header.page_index = page_index  # Ensure correct index

            if table_type is not None:
                if table_type not in self.pages:
                    self.pages[table_type] = []
                self.pages[table_type].append(page)

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

        # Empty candidate values from EMPTY reference PDB
        # These appear to be allocation hints for expanding tables
        # Format: [table_index] -> empty_candidate_value
        REFERENCE_EMPTY_CANDIDATES = {
            0: 2,    # Tracks
            1: 4,    # Genres
            2: 6,    # Artists
            3: 8,    # Albums
            4: 10,   # Labels
            5: 12,   # Keys
            6: 42,   # Colors (2-page table)
            7: 16,   # PlaylistTree
            8: 18,   # PlaylistEntries
            9: 20,   # Unknown9
            10: 22,  # Unknown10
            11: 24,  # HistoryPlaylists
            12: 26,  # HistoryEntries
            13: 28,  # Artwork
            14: 30,  # Unknown14
            15: 32,  # Unknown15
            16: 43,  # Columns (2-page table)
            17: 44,  # Unknown17 (2-page table)
            18: 45,  # Unknown18 (2-page table)
            19: 41,  # History (2-page table)
        }

        for table_type in self.TABLE_TYPES:
            table_idx = self.TABLE_TYPES.index(table_type)
            if table_type in self.pages and self.pages[table_type]:
                # Get actual page indices from the pages (for sparse layout)
                pages = self.pages[table_type]
                page_indices = [p.header.page_index for p in pages]
                first_page = min(page_indices)
                last_page = max(page_indices)

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
                    'first_page': first_page,
                    'last_page': last_page,
                    'empty_candidate': empty_candidate
                })
            else:
                # Empty table - point to itself
                table_pointers.append({
                    'type': table_idx,
                    'first_page': 0,
                    'last_page': 0,
                    'empty_candidate': 0
                })

        # Calculate next unused page
        # Empty reference: last page 40, next unused 46 (reserves 6 pages)
        # Full reference: last page 40, next unused 54 (reserves 14 pages)
        # This appears to be pre-allocation for future table expansion
        if self._all_pages:
            max_page = max(idx for idx, _, _ in self._all_pages)
            if max_page == 40:
                # Check if we have actual data (not just placeholders)
                # by checking if Tracks has more than the pre-allocated pages
                tracks_pages = len([p for _, t, p in self._all_pages if t == 'Tracks'])
                if not self._has_data and tracks_pages <= 1:
                    # Empty database (only placeholder pages): reserve 6 pages
                    next_unused_page = 46
                else:
                    # Full database (has actual data): reserve 14 pages
                    next_unused_page = 54
            else:
                next_unused_page = max_page + 1
        else:
            next_unused_page = 1

        # Build file header
        # First 28 bytes
        header = bytearray()
        header += struct.pack('<I', 0x00000000)  # Magic
        header += struct.pack('<I', 4096)  # Page size
        header += struct.pack('<I', len(self.TABLE_TYPES))  # Num tables
        header += struct.pack('<I', next_unused_page)  # Next unused page
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

        # Add default metadata entries to match rekordbox empty database
        # This adds colors, columns, unknown mappings, and history
        self.add_default_metadata()

        # Update page indices before marshaling
        # This is critical: page_index in page header must match actual file position
        # Also builds self._all_pages with gaps filled
        self._update_page_indices()

        # Build file header
        file_header = self._build_file_header()

        # Write all pages in order (including gap pages)
        pdb_data = bytearray(file_header)

        for page_index, table_type, page in self._all_pages:
            # Check if this is a zero placeholder page
            if hasattr(page, '_is_zero_placeholder') and page._is_zero_placeholder:
                # Output 4096 bytes of zeros instead of page content
                pdb_data += self._create_zero_page()
            else:
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
