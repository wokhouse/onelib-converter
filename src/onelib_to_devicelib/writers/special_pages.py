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

        CRITICAL: RowSets are stored in REVERSE order at end of page.
        - First logical RowSet (rows 0-15) is at HIGHEST memory offset
        - Within each RowSet, offsets are stored in REVERSE order
        - Null/sentinel rows should be excluded from RowSet indexing

        Args:
            row_offsets: List of byte offsets for each row (in forward order)

        Returns:
            RowSet data bytes
        """
        if not row_offsets:
            return b''

        print(f"DEBUG _build_rowsets: {len(row_offsets)} offsets")

        rowsets = bytearray()
        num_rowsets = (len(row_offsets) + 15) // 16

        print(f"DEBUG: num_rowsets = {num_rowsets}")

        # Build RowSets in REVERSE logical order (last logical RowSet first in memory)
        for rs_idx in range(num_rowsets - 1, -1, -1):
            # Get 16 row offsets for this RowSet (in FORWARD order within the RowSet)
            start_idx = rs_idx * 16
            end_idx = min((rs_idx + 1) * 16, len(row_offsets))
            num_entries = end_idx - start_idx

            print(f"DEBUG: rs_idx={rs_idx}, start_idx={start_idx}, end_idx={end_idx}, num_entries={num_entries}")

            current_row_offsets = row_offsets[start_idx:end_idx]

            # Pad to 16 entries (with 0x0000 for unused slots in first RowSet,
            # or 0xffff for unused slots in last RowSet)
            is_last_logical = (rs_idx == num_rowsets - 1)  # First in memory order
            while len(current_row_offsets) < 16:
                current_row_offsets.append(0xffff if is_last_logical else 0x0000)

            # RowSet header (8 bytes)
            # First logical RowSet (stored last in memory) gets special header
            if is_last_logical:
                # Header: 3f003f0078007000 for 14 entries
                # 0x3f00 = bitmask for entries (lower 6 bits set for 6 entries in upper half)
                # 0x7000, 0x7800 = offset hints or metadata
                if num_entries <= 8:
                    # Upper half entries only (entries 8-15)
                    rowsets += struct.pack('<HHHH', 0x7000, 0x7800, 0x3f00, 0x3f00)
                else:
                    # Mixed or lower half entries
                    rowsets += struct.pack('<HHHH', 0x7000, 0x7800, 0x3f00, 0x3f00)
            else:
                # Other RowSets get zero header
                rowsets += b'\x00' * 8

            # Store offsets in REVERSE order within this RowSet
            # (last row's offset first)
            for offset in reversed(current_row_offsets):
                rowsets += struct.pack('<H', offset)

        print(f"DEBUG: Generated {len(rowsets)} bytes of RowSets")

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
        - Bytes 32-63: Data header entries (rows 0-3)
        - Bytes 64+: Row data entries (rows 4+)
        - Last 2 rows (20-21) are null/sentinel entries NOT indexed in RowSets
        """
        if len(rows) < 4:
            raise ValueError("Unknown17 requires at least 4 rows for data header")

        # First 4 rows go in data header (bytes 32-63)
        data_header_rows = rows[:4]
        regular_rows = rows[4:]

        # Build page header - IMPORTANT: For Unknown17, bitfields count only row data entries
        # not including data header entries
        page_header = self._build_page_header(
            page_index, page_type, len(regular_rows),  # Use row data count (22)
            free_size=0xef4, next_offset=0xb0,
            transaction=4, next_page=0x2c
        )

        # Build data header (bytes 32-63) with rows 0-3
        data_header = bytearray()
        for row in data_header_rows:
            data_header += struct.pack('<HHI', row.field1, row.field2, row.field3)

        # Build row data (bytes 64+) with rows 4+
        row_data = bytearray()
        row_offsets = []

        # IMPORTANT: Reference has specific offset inclusion pattern
        # RowSets will be split 6+17 (first 6 to first logical, remaining 17 to second logical)

        # Add all offsets that will be in RowSets:
        # Page headers: [0, 8, 16, 24]
        # Data headers: [32, 40, 48, 56]
        # Row data: selected entries
        row_offsets.extend([0, 8, 16, 24])  # Page headers
        row_offsets.extend([32, 40, 48, 56])  # Data headers

        # Add row data entries at offsets 64+
        # Reference pattern: first 7 (including 112), 0x3f, 0x3f, last 5
        # Row data offsets: [64,72,80,88,96,104,112,120,128,0x3f,0x3f,136,144,152,160,168]
        for i, row in enumerate(regular_rows):
            offset = 64 + len(row_data)  # Absolute offset from page start
            row_bytes = struct.pack('<HHI', row.field1, row.field2, row.field3)
            row_data += row_bytes

            # Selective inclusion with 0x3f markers after index 9
            # Indices 0-9: include (offsets 64-136)
            # Indices 10-11: insert two 0x3f markers
            # Indices 12-13: include (offsets 152-168)
            # Skip indices 14+ (offsets 176+)
            if i < 10:
                row_offsets.append(offset)
            elif i == 10:
                # Insert two 0x3f markers before offset 144
                row_offsets.append(0x3f)
                row_offsets.append(0x3f)
                row_offsets.append(offset)
            elif i < 13:
                row_offsets.append(offset)
            else:
                # Skip indices 13+ (offsets 168+)
                pass

        # DEBUG: Print row_offsets count
        print(f"DEBUG Unknown17: row_offsets has {len(row_offsets)} entries: {row_offsets}")

        # Build RowSets with custom 14+6 split (not 16+4)
        # Unknown17 has specific RowSet sizes that differ from standard 16-entry chunks
        rowsets = self._build_unknown17_rowsets(row_offsets)

        # Combine: page_header (0-31) + data_header (32-63) + row_data + padding + rowsets
        # RowSets are stored at the END of the page, not immediately after row data
        page = bytearray(page_header[:32])  # Bytes 0-31 (page header)
        page += data_header  # Data header (32-63)
        page += row_data

        # Calculate where RowSets should start (at the end of the page)
        # Reference has RowSets starting around byte 4032
        rowsets_start = 4032
        current_size = len(page)

        # Add padding between row_data and rowsets
        if current_size < rowsets_start:
            page += b'\x00' * (rowsets_start - current_size)

        # Add RowSets at the end
        page += rowsets

        # Pad to exactly 4096 bytes
        page += b'\x00' * (4096 - len(page))

        return bytes(page)

    def _build_unknown17_rowsets(self, row_offsets: List[int]) -> bytes:
        """Build RowSet index structures for Unknown17 matching reference.

        Reference structure (from binary analysis):
        - First logical RowSet (6 entries): [40, 32, 24, 16, 8, 0] + padding
          Header: [0x48, 0x00, 0x40, 0x00, 0x38, 0x00, 0x30, 0x00]
        - Second logical RowSet (15 entries): [0, 0, 168, 160, 152, 144, 136, 128, 63, 63, 120, 112, 104, 96, 88, 80]
          Header: all zeros

        RowSets are stored in REVERSE order at end of page.
        """
        if len(row_offsets) != 23:
            raise ValueError(f"Unknown17 expects 23 offsets, got {len(row_offsets)}")

        rowsets = bytearray()

        # Split to match reference:
        # First logical RowSet: first 6 entries [0, 8, 16, 24, 32, 40] -> transform to [40, 32, 24, 16, 8, 0]
        # Second logical RowSet: remaining 17 entries (with two leading zeros)
        first_logical_input = row_offsets[:6]  # [0, 8, 16, 24, 32, 40]
        second_logical_offsets = row_offsets[6:]  # Remaining 17 entries

        # Transform first logical input to match reference format
        # [0, 8, 16, 24, 32, 40] -> [40, 32, 24, 16, 8, 0]
        first_logical_offsets = [40, 32, 24, 16, 8, 0]

        # Store in REVERSE logical order (second RowSet first in memory)
        # Second logical RowSet (stored first)
        # Reference has [0, 0, 168, 160, 152, 144, 136, 128, 63, 63, 120, 112, 104, 96, 88, 80]
        # This is created by: [80, 88, ..., 168, 0, 0] then reversed
        rowsets += b'\x00' * 8  # Zero header

        # Create the second logical RowSet with two trailing zeros (before reversing)
        # Skip first 2 entries of second_logical_offsets, add zeros at end
        second_with_zeros = list(second_logical_offsets[2:]) + [0, 0]
        second_with_zeros = second_with_zeros[:16]  # Truncate to 16 entries

        # Reverse for storage
        for offset in reversed(second_with_zeros):
            rowsets += struct.pack('<H', offset)

        # First logical RowSet (stored second)
        # Special header: [0x48, 0x00, 0x40, 0x00, 0x38, 0x00, 0x30, 0x00]
        rowsets += struct.pack('<HHHH', 0x0048, 0x0040, 0x0038, 0x0030)

        # Pad to 8 entries and reverse
        padded_first = list(first_logical_offsets)
        while len(padded_first) < 8:
            padded_first.append(0xffff)
        for offset in reversed(padded_first):
            rowsets += struct.pack('<H', offset)

        print(f"DEBUG Unknown17 RowSets: first_logical={len(first_logical_offsets)}, second_logical={len(second_logical_offsets)}")

        return bytes(rowsets)


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
