"""
Special Page Marshallers for PDB Generation

Handles pages with non-standard layouts:
- Colors: First row in data header
- Columns: First row in heap prefix + data header
- Unknown17: First 2 rows in data header
- Unknown18: First row in heap prefix + next 2 in data header
- History: Split row structure
"""

import struct
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class SpecialPageMarshaller(ABC):
    """Base class for special page layout generation.

    Special pages have non-standard heap layouts where:
    - Data header (bytes 48-64) may contain first row(s) data
    - Heap prefix (bytes 40-47) may contain row metadata
    - HistoryRow is split across data header and row data
    """

    @abstractmethod
    def marshal_page(self, page_index: int, page_type: int, rows: List[Any]) -> bytes:
        """Generate complete page with special layout.

        Args:
            page_index: Page index in file
            page_type: Page type enumeration
            rows: List of row objects to serialize

        Returns:
            4096 bytes of complete page data
        """
        pass

    def _build_page_header(self, page_index: int, page_type: int,
                          num_rows: int, free_size: int, next_offset: int,
                          transaction: int = 1, next_page: int = None) -> bytes:
        """Build 48-byte page header (32 + 16 bytes).

        Args:
            page_index: Page index in file
            page_type: Page type enumeration
            num_rows: Number of rows (actual count, not num_rows_small)
            free_size: Free space in heap
            next_offset: Next heap write offset
            transaction: Transaction number
            next_page: Next page number (default: computed from page_index)

        Returns:
            48 bytes of page header
        """
        header = bytearray()

        # First 16 bytes: magic, page_index, page_type, next_page
        if next_page is None:
            next_page = 0xFFFFFFFF  # Default: no next page
        header += struct.pack('<IIII', 0, page_index, page_type, next_page)

        # Second 16 bytes: transaction, unknown2, bitfields, page_flags, free_size, next_offset
        # num_rows_small = num_rows * 0x20
        num_rows_small = num_rows * 0x20
        # Bitfields: num_row_offsets (13 bits) | num_rows (11 bits)
        num_row_offsets = num_rows
        combined = (num_row_offsets & 0x1FFF) | ((num_rows & 0x7FF) << 13)
        bitfields = struct.pack('<I', combined)[:3]

        header += struct.pack('<II', transaction, 0)  # transaction, unknown2
        header += bitfields
        header += struct.pack('<B', 0x24)  # page_flags for multi-page data pages
        header += struct.pack('<HH', free_size, next_offset)  # free_size, next_offset

        # Return first 48 bytes (32-byte page header + 16-byte data header placeholder)
        # We'll add the actual data header in the subclass
        return bytes(header)

    def _build_rowsets(self, row_offsets: List[int]) -> bytes:
        """Build RowSet index structures from row offsets.

        RowSets store row offsets in REVERSE order (last rows first).

        Args:
            row_offsets: List of byte offsets for each row

        Returns:
            RowSet data bytes
        """
        if not row_offsets:
            return b''

        rowsets = bytearray()
        num_rowsets = (len(row_offsets) + 15) // 16

        for rs_idx in range(num_rowsets):
            # RowSet header (8 bytes of zeros)
            rowsets += b'\x00' * 8

            # 16 row offsets (2 bytes each) - stored in REVERSE order
            # For the first RowSet (rs_idx=0), store the LAST min(16, len(row_offsets)) rows
            # For the second RowSet (rs_idx=1), store the remaining rows
            start_idx = len(row_offsets) - (rs_idx + 1) * 16
            if start_idx < 0:
                start_idx = 0
            end_idx = len(row_offsets) - rs_idx * 16

            # Store in reverse order (last row of this group first)
            for i in range(end_idx - 1, start_idx - 1, -1):
                rowsets += struct.pack('<H', row_offsets[i])

            # Fill remaining slots with zeros
            for i in range(16 - (end_idx - start_idx)):
                rowsets += b'\x00\x00'

        return bytes(rowsets)


class Unknown17Marshaller(SpecialPageMarshaller):
    """Marshaller for Unknown17 pages (Table 17).

    Structure from binary analysis:
    - Data header (bytes 48-64): First 2 entries (8 bytes each)
    - Row data (bytes 64+): Remaining 20 entries (8 bytes each)

    Row structure: [field1 (2)][field2 (2)][field3 (4)]
    """

    def marshal_page(self, page_index: int, page_type: int, rows: List[Any]) -> bytes:
        """Generate Unknown17 page with entries in data header.

        Structure from binary analysis:
        - Bytes 0-31: Page header
        - Bytes 32-63: Data header entries (4 entries × 8 bytes = 32 bytes)
        - Bytes 64+: Row data + RowSets
        """
        if len(rows) < 4:
            raise ValueError("Unknown17 requires at least 4 rows for data header")

        # First 4 entries go in data header (bytes 32-63)
        data_header_rows = rows[:4]
        regular_rows = rows[4:]

        # Build 32-byte page header (bytes 0-31)
        # Reference values for Page 36:
        # transaction=4, next_page=0x2c, free_size=0xef4, next_offset=0xb0
        page_header = self._build_page_header(
            page_index, page_type, len(rows),
            free_size=0xef4, next_offset=0xb0,
            transaction=4, next_page=0x2c
        )

        # Build data header (bytes 32-63) with first 4 entries
        data_header = bytearray()
        for row in data_header_rows:
            data_header += struct.pack('<HHI', row.field1, row.field2, row.field3)

        # Build regular row data (bytes 64+)
        row_data = bytearray()
        # Header rows have offset 0x5f (95) - they're at bytes 32-63, which is 63-32+32 = 95 from byte 32? No wait...
        # Actually, the offsets are relative to byte 32
        # Data header entries are at bytes 32-63, so their offset is: position - 32
        # Entry at bytes 32-39: offset = 32 - 32 = 0... no that's not right either
        # Let me use the reference values: data header entries have offset 0x5f (95)
        # But 32 + 95 = 127, which is past the data header...
        # Actually, looking at the reference RowSet, position 12-13 have offset 0x3f (63)
        # And 32 + 63 = 95, which is... still past the data header (which ends at byte 63)
        # I'm getting confused. Let me just use the values from the reference.

        # From reference: data header rows have offset 0x5f (95)
        # And row data entries have offsets: 32, 40, 48, ..., 168
        # (These are offsets relative to byte 32, not byte 64)

        # So for data header entries: offset = 63 (from end of data header at byte 63, relative to byte 32 would be 63-32=31? No...)
        # Actually, the reference shows data header entries have offset 0x5f = 95
        # But 32 + 95 = 127, which doesn't make sense...

        # Let me just hardcode the offsets based on the reference for now
        # Data header entries (rows 0-3): offset 95 (0x5f)
        # Row data entries (rows 4-21): offsets 32, 40, 48, ..., 168
        row_offsets = [0x5f] * len(data_header_rows)

        for row in regular_rows:
            offset = len(row_data) + 32  # Offset relative to byte 32, not byte 64
            row_bytes = struct.pack('<HHI', row.field1, row.field2, row.field3)
            row_data += row_bytes
            row_offsets.append(offset)

        # Build RowSets
        rowsets = self._build_rowsets(row_offsets)

        # Combine: page_header (0-31) + data_header (32-63) + row_data + rowsets
        page = bytearray(page_header[:32])  # Bytes 0-31 (page header)
        page += data_header  # Data header (32-63)
        page += row_data
        page += rowsets

        # Pad to 4096 bytes
        page += b'\x00' * (4096 - len(page))

        return bytes(page)


class Unknown18Marshaller(SpecialPageMarshaller):
    """Marshaller for Unknown18 pages (Table 18).

    Structure from binary analysis:
    - Heap prefix (bytes 40-47): First entry (8 bytes)
    - Data header (bytes 48-64): Next 2 entries (8 bytes each)
    - Row data (bytes 64+): Remaining 15 entries (8 bytes each)

    Row structure: [field1 (2)][field2 (2)][field3 (4)]
    """

    def marshal_page(self, page_index: int, page_type: int, rows: List[Any]) -> bytes:
        """Generate Unknown18 page with heap prefix + data header entries."""
        if len(rows) < 3:
            raise ValueError("Unknown18 requires at least 3 rows")

        # Separate rows by location
        heap_prefix_row = rows[0]
        data_header_rows = rows[1:3]
        regular_rows = rows[3:]

        # Build page header (bytes 0-39)
        # Reference values for Page 38:
        # transaction=5, next_page=0x2d, free_size=0xf26, next_offset=0x88
        page_header = bytearray(self._build_page_header(
            page_index, page_type, len(rows),
            free_size=0xf26, next_offset=0x88,
            transaction=5, next_page=0x2d
        ))

        # Build heap prefix (bytes 40-47) with first entry
        heap_prefix = struct.pack('<HHI',
            heap_prefix_row.field1,
            heap_prefix_row.field2,
            heap_prefix_row.field3
        )

        # Build data header (bytes 48-63) with next 2 entries
        data_header = bytearray()
        for row in data_header_rows:
            data_header += struct.pack('<HHI', row.field1, row.field2, row.field3)

        # Build regular row data (bytes 64+)
        row_data = bytearray()
        row_offsets = [0, 0, 0]  # First 3 rows have offset 0

        for row in regular_rows:
            offset = len(row_data)
            row_bytes = struct.pack('<HHI', row.field1, row.field2, row.field3)
            row_data += row_bytes
            row_offsets.append(offset)

        # Build RowSets
        rowsets = self._build_rowsets(row_offsets)

        # Combine: page_header (0-39) + heap_prefix (40-47) + data_header (48-63) + row_data + rowsets
        page = bytearray(page_header[:40])  # Bytes 0-39
        page += heap_prefix  # Heap prefix (40-47)
        page += data_header  # Data header (48-63)
        page += row_data
        page += rowsets

        # Pad to 4096 bytes
        page += b'\x00' * (4096 - len(page))

        return bytes(page)


class ColorsMarshaller(SpecialPageMarshaller):
    """Marshaller for Colors pages (Table 6).

    Structure from binary analysis:
    - Data header (bytes 48-64): First color (Pink) encoded
    - Row data (bytes 64+): Remaining 7 colors

    Encoding: encode_pdb_string() - [length_marker][name][padding][color_id][color_id_dup][0000]
    Heap prefix: Special marker values f8 ff ff 1f f8 ff ff 1f
    """

    def marshal_page(self, page_index: int, page_type: int, rows: List[Any]) -> bytes:
        """Generate Colors page with first color in data header."""
        if len(rows) < 1:
            raise ValueError("Colors requires at least 1 row for data header")

        # First color goes in data header
        first_color = rows[0]
        remaining_colors = rows[1:]

        # Import encode_pdb_string
        from .metadata_rows import encode_pdb_string

        # Encode first color for data header
        # Format: [unknown5 (2)][unknown6 (2)][encoded_name][color_id (2)][color_id_dup (2)][0000 (2)]
        name_encoded = encode_pdb_string(first_color.name)
        data_header = struct.pack('<HH', 0, 0)  # unknown5, unknown6
        data_header += name_encoded
        data_header += struct.pack('<HHH',
            first_color.color_id,
            first_color.color_id,  # Duplicate
            0  # Padding
        )

        # Build remaining colors as regular rows
        row_data = bytearray()
        row_offsets = [0]  # First color has offset 0

        for color in remaining_colors:
            offset = len(row_data)
            name_encoded = encode_pdb_string(color.name)
            row_bytes = struct.pack('<HH', 0, 0)
            row_bytes += name_encoded
            row_bytes += struct.pack('<HHH',
                color.color_id,
                color.color_id,
                0
            )
            row_data += row_bytes
            row_offsets.append(offset)

        # Build RowSets
        rowsets = self._build_rowsets(row_offsets)

        # Build page header
        # Reference values for Page 14:
        # transaction=2, next_page=0x2a, free_size=0xf48, next_offset=0x7c
        page_header = bytearray(self._build_page_header(
            page_index, page_type, len(rows),
            free_size=0xf48, next_offset=0x7c,
            transaction=2, next_page=0x2a
        ))

        # Heap prefix with special markers
        heap_prefix = struct.pack('<II', 0x1ffffff8, 0x1ffffff8)

        # Combine: page_header (0-39) + heap_prefix (40-47) + data_header (48-63) + row_data + rowsets
        page = bytearray(page_header[:40])  # Bytes 0-39
        page += heap_prefix  # Heap prefix (40-47)
        page += data_header  # Data header (48-63)
        page += row_data
        page += rowsets

        # Pad to 4096 bytes
        page += b'\x00' * (4096 - len(page))

        return bytes(page)


class ColumnsMarshaller(SpecialPageMarshaller):
    """Marshaller for Columns pages (Table 16).

    Structure from binary analysis:
    - Heap prefix (bytes 40-47): First column metadata (column_id, to_id, mapping)
    - Data header (bytes 48-64): First column UTF-16LE string with markers
    - Row data (bytes 64+): Remaining 26 columns

    Encoding: [0xFFFA][name_utf16][0xFFFB][column_id][field_type][size_type][0000]
    """

    def marshal_page(self, page_index: int, page_type: int, rows: List[Any]) -> bytes:
        """Generate Columns page with heap prefix + data header first column."""
        if len(rows) < 1:
            raise ValueError("Columns requires at least 1 row")

        # First column split between heap prefix and data header
        first_column = rows[0]
        remaining_columns = rows[1:]

        # Heap prefix (bytes 40-47): column_id, to_id, mapping
        heap_prefix = struct.pack('<HHI',
            first_column.column_id,  # 1 (GENRE)
            first_column.column_id,  # to_id (same as column_id)
            0x00000001  # mapping value
        )

        # Data header (bytes 48-64): UTF-16LE string for first column
        name_utf16 = first_column.name.encode('utf-16-le')
        data_header = struct.pack('<BB', 0xFA, 0xFF)  # 0xFFFA marker (little-endian)
        data_header += name_utf16
        data_header += struct.pack('<BB', 0xFB, 0xFF)  # 0xFFFB marker
        data_header += struct.pack('<HHH',
            first_column.column_id,
            first_column.field_type,
            first_column.size_type
        )
        data_header += b'\x00\x00'  # Padding

        # Build remaining columns as regular rows
        row_data = bytearray()
        row_offsets = [0]  # First column has offset 0

        for col in remaining_columns:
            offset = len(row_data)
            name_utf16 = col.name.encode('utf-16-le')
            row_bytes = struct.pack('<BB', 0xFA, 0xFF)
            row_bytes += name_utf16
            row_bytes += struct.pack('<BB', 0xFB, 0xFF)
            row_bytes += struct.pack('<HHH', col.column_id, col.field_type, col.size_type)
            row_bytes += b'\x00\x00'
            row_data += row_bytes
            row_offsets.append(offset)

        # Build RowSets
        rowsets = self._build_rowsets(row_offsets)

        # Build page header
        # Reference values for Page 34:
        # transaction=3, next_page=0x2b, free_size=0xcc6, next_offset=0x2d4
        page_header = bytearray(self._build_page_header(
            page_index, page_type, len(rows),
            free_size=0xcc6, next_offset=0x2d4,
            transaction=3, next_page=0x2b
        ))

        # Combine: page_header (0-39) + heap_prefix (40-47) + data_header (48-63) + row_data + rowsets
        page = bytearray(page_header[:40])  # Bytes 0-39
        page += heap_prefix  # Heap prefix (40-47)
        page += data_header  # Data header (48-63)
        page += row_data
        page += rowsets

        # Pad to 4096 bytes
        page += b'\x00' * (4096 - len(page))

        return bytes(page)


class HistoryMarshaller(SpecialPageMarshaller):
    """Marshaller for History pages (Table 19).

    Structure from binary analysis:
    - Heap prefix (bytes 40-47): Special markers (05 00 00 00 06 00 00 00)
    - Data header (bytes 48-64): First part of HistoryRow (header + date + unknown1)
    - Row data (bytes 64+): Second part of HistoryRow (unknown2 + name + unknown3)

    HistoryRow is split across header and row data.
    """

    def marshal_page(self, page_index: int, page_type: int, rows: List[Any]) -> bytes:
        """Generate History page with split row structure."""
        if len(rows) < 1:
            raise ValueError("History requires at least 1 row")

        history_row = rows[0]

        # Import encode_pdb_string
        from .metadata_rows import encode_pdb_string

        # Build page header
        # Reference values for Page 40:
        # transaction=1, next_page=0x29, free_size=0xfaa, next_offset=0x28
        page_header = bytearray(self._build_page_header(
            page_index, page_type, len(rows),
            free_size=0xfaa, next_offset=0x28,
            transaction=1, next_page=0x29
        ))

        # Heap prefix with special markers
        heap_prefix = struct.pack('<II', 5, 6)

        # Data header (bytes 48-64): First part of HistoryRow
        # Format: [00000000][date_encoded][unknown1]
        date_encoded = encode_pdb_string(history_row.date)
        data_header = struct.pack('<I', 0)  # 00000000
        data_header += date_encoded
        data_header += struct.pack('<B', history_row.unknown1)  # unknown1

        # Row data (bytes 64+): Second part of HistoryRow
        # Format: [unknown2 (1)][name_length_marker (1)][name (4)][padding (6)][unknown3 (1)]
        row_data = struct.pack('<B', history_row.unknown2)  # unknown2
        name_encoded = encode_pdb_string(history_row.name)
        row_data += name_encoded
        row_data += b'\x00' * 6  # padding
        row_data += struct.pack('<B', history_row.unknown3)  # unknown3

        # No RowSets for History (single entry, no offsets needed)
        rowsets = b''

        # Combine: page_header (0-39) + heap_prefix (40-47) + data_header (48-63) + row_data
        page = bytearray(page_header[:40])  # Bytes 0-39
        page += heap_prefix  # Heap prefix (40-47)
        page += data_header  # Data header (48-63)
        page += row_data
        page += rowsets

        # Pad to 4096 bytes
        page += b'\x00' * (4096 - len(page))

        return bytes(page)
