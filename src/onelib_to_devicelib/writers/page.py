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
    - Second 16 bytes: transaction, unknown2, num_rows_small, unknown3, unknown4, page_flags, free_size, next_heap_write_offset
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
    page_flags: int = 0x34  # 0x34 for data pages
    free_size: int = 0
    next_heap_write_offset: int = 0


@dataclass
class DataPageHeader:
    """8-byte data page header.

    Comes after the 32-byte page header.
    """
    unknown5: int = 1
    num_rows_large: int = 0
    unknown6: int = 0
    unknown7: int = 0


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
        self.heap = TwoWayHeap(page_size=4096, data_header_size=40)  # 32-byte header + 8-byte data header
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
        # - num_rows_small: uint8 (1 byte)
        # - unknown3: uint8 (1 byte)
        # - unknown4: uint8 (1 byte)
        # - page_flags: uint8 (1 byte)
        # - free_size: uint16 (2 bytes)
        # - next_heap_write_offset: uint16 (2 bytes)
        # Total: 4+4+1+1+1+1+2+2 = 16 bytes ✓
        # Format: I(4) + I(4) + B(1) + B(1) + B(1) + B(1) + H(2) + H(2) = 16 bytes, 8 items
        page += struct.pack('<IIBBBBHH',
            self.header.transaction, self.header.unknown2,
            self.header.num_rows_small & 0xFF, self.header.unknown3 & 0xFF,
            self.header.unknown4 & 0xFF, self.header.page_flags & 0xFF,
            self.header.free_size, self.header.next_heap_write_offset)

        # 8-byte data header
        page += struct.pack('<HHHH',
            self.data_header.unknown5, self.data_header.num_rows_large,
            self.data_header.unknown6, self.data_header.unknown7)

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
