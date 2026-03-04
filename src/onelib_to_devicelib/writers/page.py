"""
Page Structure

Build complete pages with 32-byte headers, row data, and row index.
"""

import struct
from dataclasses import dataclass
from typing import List, Optional

from .heap import TwoWayHeap
from .rowset import RowSet


class PageType:
    """Page type enumeration."""
    TRACKS = 0
    GENRES = 1
    ARTISTS = 2
    ALBUMS = 3
    LABELS = 4
    KEYS = 5
    COLORS = 6
    PLAYLIST_TREE = 7
    PLAYLIST_ENTRIES = 8
    UNKNOWN9 = 9
    UNKNOWN10 = 10
    HISTORY_PLAYLISTS = 11
    HISTORY_ENTRIES = 12
    ARTWORK = 13
    UNKNOWN14 = 14
    UNKNOWN15 = 15
    COLUMNS = 16
    UNKNOWN17 = 17
    UNKNOWN18 = 18
    HISTORY = 19


@dataclass
class PageHeader:
    """32-byte page header.

    Format:
    - First 16 bytes: magic, page_index, page_type, next_page
    - Second 16 bytes: transaction, unknown2, bitfields (num_row_offsets+num_rows), page_flags, free_size, next_heap_write_offset

    FIX #1: Bytes 24-26 are bitfields:
    - Bits 0-12: num_row_offsets (13 bits) - offset into row index
    - Bits 13-23: num_rows (11 bits) - actual row count
    - Bits 24-31: page_flags (8 bits) - page type flags (stored separately)
    """
    # First 16 bytes
    magic: int = 0  # Always 0 for data pages
    page_index: int = 0
    page_type: int = 0  # PageType enum
    next_page: int = 0xFFFFFFFF  # 0xFFFFFFFF if last page

    # Second 16 bytes
    transaction: int = 1
    unknown2: int = 0
    num_rows_small: int = 0  # Increments by 0x20 per row (not 1!)
    unknown3: int = 0
    unknown4: int = 0
    page_flags: int = 0x34  # 0x34 for data pages, 0x64 for index pages
    free_size: int = 0
    next_heap_write_offset: int = 0

    def pack_bitfields(self) -> bytes:
        """Pack num_row_offsets, num_rows, and page_flags into bitfields.

        FIX #1: Bytes 24-26 are bitfields, not separate uint8 fields.

        Layout (3 bytes = 24 bits):
        - Bits 0-12: num_row_offsets (13 bits) - offset into row index
        - Bits 13-23: num_rows (11 bits) - actual row count
        - Byte 3: page_flags (8 bits)

        Returns:
            4 bytes (3 bitfield bytes + 1 page_flags byte)
        """
        # Calculate actual values
        # num_rows_small is in units of 0x20, so divide to get actual row count
        num_rows = self.num_rows_small // 0x20  # Actual row count
        num_row_offsets = num_rows  # Offset into row index (same as row count for now)

        # Pack into 24-bit bitfield (little-endian)
        # Lower 13 bits: num_row_offsets
        # Upper 11 bits: num_rows
        combined = (num_row_offsets & 0x1FFF) | ((num_rows & 0x7FF) << 13)

        # Pack as 4 bytes: 3 bytes bitfield + 1 byte page_flags
        # We pack as 32-bit int and take first 3 bytes
        bytes_24_26 = struct.pack('<I', combined)[:3]  # Take first 3 bytes
        bytes_24_26 += struct.pack('<B', self.page_flags & 0xFF)

        return bytes_24_26


@dataclass
class DataPageHeader:
    """16-byte data page header.

    Comes after the 32-byte page header.
    Structure: 8 x uint16 fields
    """
    unknown5: int = 0
    unknown6: int = 0
    unknown7: int = 0
    unknown8: int = 0
    unknown9: int = 0
    num_rows_large: int = 0
    unknown10: int = 0
    unknown11: int = 0


@dataclass
class IndexHeader:
    """8-byte index page header (different from DataPageHeader).

    FIX #2: Index pages have a different header structure than data pages.

    Used by IndexPage (first page of each table).
    """
    unknown1: int = 0x1fff  # Usually 0x1fff
    unknown2: int = 0x1fff  # Usually 0x1fff
    unknown3: int = 0x03ec  # Always 0x03ec
    next_offset: int = 0  # Byte offset for next entry
    page_index: int = 0
    next_page: int = 0
    unknown5: int = 0x03ffffff  # Always 0x03ffffff
    unknown6: int = 0x00000000  # Always 0x00000000
    num_entries: int = 0
    first_empty_entry: int = 0x1fff


class IndexPage:
    """Index page for B-tree-like structure.

    FIX #2: First page of each table should be an index page, not a data page.

    Index page characteristics:
    - PageFlags = 0x64 (not 0x34 like data pages)
    - Different header structure (IndexHeader instead of DataPageHeader)
    - Filled with 0x1ffffff8 entries pointing to data pages
    - No row data, just page pointers

    The index page contains pointers to data pages, forming a B-tree-like
    structure where the index page is the root.
    """

    def __init__(self, page_index: int, page_type: int, index_next_page: int = 0x03ffffff):
        """Initialize a new index page.

        Args:
            page_index: Page index in the file
            page_type: Page type (PageType enum)
            index_next_page: Next page for index_header (default 0x03ffffff for single-page tables)
        """
        self.header = PageHeader(page_index=page_index, page_type=page_type)
        self.header.page_flags = 0x64  # CRITICAL: Index page flag (FIX #2)
        self.index_header = IndexHeader()
        # CRITICAL: Set index_header.page_index to match the page
        self.index_header.page_index = page_index
        # CRITICAL: Set index_header.next_page (points to next data page)
        # Default is 0x03ffffff for single-page tables, but multi-page tables use actual page number
        self.index_header.next_page = index_next_page
        # Index entries point to data pages
        self.index_entries: List[int] = []

    def add_entry(self, page_index: int) -> None:
        """Add a data page pointer to the index.

        Args:
            page_index: Page index of the data page to point to
        """
        self.index_entries.append(page_index)
        self.index_header.num_entries = len(self.index_entries)

    def marshal_binary(self) -> bytes:
        """Serialize index page to bytes.

        Returns:
            4096 bytes of complete index page data
        """
        page = bytearray()

        # 32-byte page header (same as data pages)
        page += struct.pack('<IIII',
            self.header.magic, self.header.page_index,
            self.header.page_type, self.header.next_page)

        # Second 16 bytes
        page += struct.pack('<II', self.header.transaction, self.header.unknown2)
        # FIX #2: Index pages use bitfields too, but page_flags is 0x64
        page += self.header.pack_bitfields()
        page += struct.pack('<HH',
            self.header.free_size, self.header.next_heap_write_offset)

        # 8-byte index header (replaces DataPageHeader)
        # FIX #2: Different structure than DataPageHeader
        page += struct.pack('<HHHH',
            self.index_header.unknown1, self.index_header.unknown2,
            self.index_header.unknown3, self.index_header.next_offset)
        page += struct.pack('<II',
            self.index_header.page_index, self.index_header.next_page)
        page += struct.pack('<II',
            self.index_header.unknown5, self.index_header.unknown6)
        page += struct.pack('<HH',
            self.index_header.num_entries, self.index_header.first_empty_entry)

        # Fill remaining space with 0x1ffffff8 (empty index marker)
        # FIX #2: Empty index entries are marked as 0x1ffffff8
        # Reference stops at offset 4075 (leaving 20 bytes of zeros at end)
        # This gives 1004 entries of 4 bytes each = 4016 bytes
        # Header is 60 bytes, so entries from byte 60 to 4075
        max_entry_offset = 4076  # Stop before this byte
        entries_written = 0
        while len(page) < max_entry_offset:
            if entries_written < len(self.index_entries):
                page += struct.pack('<I', self.index_entries[entries_written])
            else:
                page += struct.pack('<I', 0x1ffffff8)  # Empty entry
            entries_written += 1

        # Pad to 4096 bytes (leave remaining bytes as zeros)
        page += b'\x00' * (4096 - len(page))

        return bytes(page)

    def __repr__(self) -> str:
        """String representation of index page state."""
        return (f"IndexPage(index={self.header.page_index}, "
                f"type={self.header.page_type}, "
                f"entries={len(self.index_entries)}, "
                f"flags=0x{self.header.page_flags:02x})")


class DataPage:
    """Data page with row heap and row index.

    A DataPage contains:
    - 32-byte page header
    - 8-byte data page header
    - Row data (grows from top)
    - Padding
    - Row index/RowSets (grows from bottom)
    """

    def __init__(self, page_index: int, page_type: int):
        """Initialize a new data page.

        Args:
            page_index: Page index in the file
            page_type: Page type (PageType enum)
        """
        self.header = PageHeader(page_index=page_index, page_type=page_type)
        self.data_header = DataPageHeader()
        # Reserve 40 bytes for page + data headers, plus 8 bytes of space for data header
        # This ensures heap data starts at byte 48 (40 headers + 8 data header space)
        self.heap = TwoWayHeap(page_size=4096, data_header_size=48)  # 32-byte header + 16-byte data header
        self.rowsets: List[RowSet] = []

    def insert_row(self, row_data: bytes) -> int:
        """Insert row and return row index.

        Args:
            row_data: Serialized row bytes to insert

        Returns:
            Row index (increments by 0x20 per row, not 1)
        """
        # Write to top of heap
        position = self.heap.write_top(row_data)

        # Align to 4-byte boundary
        self.heap.align_top(4)

        # Calculate row index
        # num_rows_small is in units of 0x20, so divide to get actual row count
        actual_row_count = self.header.num_rows_small // 0x20
        row_index = self.header.num_rows_small  # Return value
        rowset_index = actual_row_count // 16
        row_in_rowset = actual_row_count % 16

        # Create new RowSet if needed
        if row_in_rowset == 0:
            self.rowsets.append(RowSet())

        # Set row position
        self.rowsets[rowset_index].set_row(row_in_rowset, position)

        # Update header
        # NOTE: num_rows_small increments by 0x20, not 1!
        # This is a critical detail from the REX implementation
        self.header.num_rows_small += 0x20
        self.header.transaction += 1
        self.header.free_size = self.heap.free_size()
        self.header.next_heap_write_offset = self.heap.top_cursor

        # Update data header
        self.data_header.num_rows_large = self.header.num_rows_small // 0x20

        return row_index

    def marshal_binary(self) -> bytes:
        """Serialize complete page.

        Builds:
        1. 32-byte page header
        2. 8-byte data page header
        3. Row data from heap
        4. Padding
        5. Row index (RowSets)

        Returns:
            4096 bytes of complete page data
        """
        # Build row index at bottom of heap
        # Write RowSets in reverse order
        for rowset in reversed(self.rowsets):
            self.heap.write_bottom(rowset.marshal_binary())

        # Assemble page
        page = bytearray()

        # 32-byte page header
        # First 16 bytes
        page += struct.pack('<IIII',
            self.header.magic, self.header.page_index,
            self.header.page_type, self.header.next_page)

        # Second 16 bytes
        # - transaction: uint32 (4 bytes)
        # - unknown2: uint32 (4 bytes)
        # - FIX #1: Bitfields (3 bytes) + page_flags (1 byte) = 4 bytes total
        #   * num_row_offsets (13 bits)
        #   * num_rows (11 bits)
        #   * page_flags (8 bits)
        # - free_size: uint16 (2 bytes)
        # - next_heap_write_offset: uint16 (2 bytes)
        # Total: 4+4+4+2+2 = 16 bytes ✓
        page += struct.pack('<II', self.header.transaction, self.header.unknown2)
        page += self.header.pack_bitfields()  # FIX #1: Use bitfield packing
        page += struct.pack('<HH',
            self.header.free_size, self.header.next_heap_write_offset)

        # 16-byte data header (8 x uint16)
        page += struct.pack('<HHHHHHHH',
            self.data_header.unknown5, self.data_header.unknown6,
            self.data_header.unknown7, self.data_header.unknown8,
            self.data_header.unknown9, self.data_header.num_rows_large,
            self.data_header.unknown10, self.data_header.unknown11)

        # Add heap data
        page += self.heap.to_bytes()

        # Pad to page size
        assert len(page) <= 4096, f"Page too large: {len(page)} bytes"
        return bytes(page + b'\x00' * (4096 - len(page)))

    @classmethod
    def unmarshal_binary(cls, data: bytes, offset: int = 0) -> 'DataPage':
        """Deserialize page from bytes.

        Args:
            data: Bytes containing page data
            offset: Offset to start reading from

        Returns:
            DataPage instance

        Raises:
            ValueError: If data is too short
        """
        if offset + 4096 > len(data):
            raise ValueError(f"Need 4096 bytes for page, got {len(data) - offset}")

        page_data = data[offset:offset + 4096]

        # Parse 32-byte page header
        magic, pidx, ptype, next_pg = struct.unpack('<IIII', page_data[:16])
        trans, unk2, num_rows, unk3, unk4, flags, free, next_off = struct.unpack('<IIBBBBHH', page_data[16:32])

        header = PageHeader(
            magic=magic,
            page_index=pidx,
            page_type=ptype,
            next_page=next_pg,
            transaction=trans,
            unknown2=unk2,
            num_rows_small=num_rows,
            unknown3=unk3,
            unknown4=unk4,
            page_flags=flags,
            free_size=free,
            next_heap_write_offset=next_off
        )

        # Parse 8-byte data header
        unk5, num_large, unk6, unk7 = struct.unpack('<HHHH', page_data[40:48])

        data_header = DataPageHeader(
            unknown5=unk5,
            num_rows_large=num_large,
            unknown6=unk6,
            unknown7=unk7
        )

        # Create page
        page = cls(page_index=pidx, page_type=ptype)
        page.header = header
        page.data_header = data_header

        # Parse RowSets from bottom of page
        # Calculate number of RowSets
        num_rowsets = (num_rows // 0x20 + 15) // 16  # Round up
        row_index_size = num_rowsets * 36  # 36 bytes per RowSet
        row_index_offset = 4096 - row_index_size

        page.rowsets = []
        for i in range(num_rowsets):
            rs_offset = row_index_offset + (i * 36)
            rowset = RowSet.unmarshal_binary(page_data, rs_offset)
            page.rowsets.append(rowset)

        return page

    def __repr__(self) -> str:
        """String representation of page state."""
        num_rows = self.header.num_rows_small // 0x20
        return (f"DataPage(index={self.header.page_index}, "
                f"type={self.header.page_type}, "
                f"rows={num_rows}, "
                f"free={self.header.free_size})")
