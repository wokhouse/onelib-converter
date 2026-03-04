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
        # RowSets excludes offsets 0 and 8, but includes 16-168 with markers
        # Pattern: [16, 24, 32, 40, 48, 56, 64, 72, 80, 88, 96, 104, 112, 120, 63, 63, 128, 136, 144, 152, 160, 168]
        # NO explicit page/data header addition here - done below with explicit list


        # Add row data entries at offsets 64+
        # Build row_offsets for RowSets (23 total to match reference)
        # Pattern: [8, 16, 24, 32, 40, 48, 56, 64, 72, 80, 88, 96, 104, 112, 120, 63, 63, 128, 136, 144, 152, 160, 168]

        # Add row data (for all rows, regardless of RowSets inclusion)
        for i, row in enumerate(regular_rows):
            row_bytes = struct.pack('<HHI', row.field1, row.field2, row.field3)
            row_data += row_bytes

        # Build row_offsets list explicitly (not during the loop)
        # Page/data headers: [8, 16, 24, 32, 40, 48, 56]
        row_offsets.extend([8, 16, 24, 32, 40, 48, 56])

        # Row data offsets: [64, 72, 80, 88, 96, 104, 112, 120]
        row_offsets.extend([64, 72, 80, 88, 96, 104, 112, 120])

        # Markers
        row_offsets.extend([0x3f, 0x3f])

        # Remaining row data offsets: [128, 136, 144, 152, 160, 168]
        row_offsets.extend([128, 136, 144, 152, 160, 168])





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
        - Bytes 0-11: 12 zeros
        - Bytes 12-55: 22 offsets in little-endian (in FORWARD order from row_offsets)
        - Bytes 56-57: 2 zeros
        - Bytes 58-61: 0xffffffff (terminator)

        Total: 64 bytes
        """
        if len(row_offsets) != 23:
            raise ValueError(f"Unknown17 expects 23 offsets, got {len(row_offsets)}")

        rowsets = bytearray()

        # 12 zeros
        rowsets += b'\x00' * 12

        # 22 offsets in REVERSE order (matches reference)
        for offset in reversed(row_offsets):
            rowsets.extend(struct.pack('<H', offset))

        # 2 zeros
        rowsets += b'\x00' * 2

        # Terminator: 0xffffffff
        rowsets += struct.pack('<I', 0xFFFFFFFF)

        return bytes(rowsets)


class Unknown18Marshaller(SpecialPageMarshaller):
    """Marshaller for Unknown18 pages (Table 18).

    Structure from binary analysis:
    - Page header (bytes 0-31): 32-byte page header
    - Heap prefix (bytes 32-39): First entry (8 bytes)
    - Extra entry (bytes 40-47): Second entry (8 bytes)
    - Data header (bytes 48-64): Next 2 entries (8 bytes each)
    - Row data (bytes 64+): Remaining entries (8 bytes each)

    Row structure: [field1 (2)][field2 (2)][field3 (4)]
    """

    def marshal_page(self, page_index: int, page_type: int, rows: List[Any]) -> bytes:
        """Generate Unknown18 page with heap prefix + extra entry + data header entries."""
        if len(rows) < 4:
            raise ValueError("Unknown18 requires at least 4 rows")

        # Separate rows by location
        heap_prefix_and_extra = rows[0:2]  # 2 entries at bytes 32-47
        data_header_rows = rows[2:4]  # 2 entries at bytes 48-63
        regular_rows = rows[4:]  # Remaining entries at bytes 64+

        # Build page header (bytes 0-31)
        # Reference values for Page 38:
        # transaction=5, next_page=0x2d, free_size=0xf26, next_offset=0x88
        # IMPORTANT: num_rows should be 17 (indexed rows), even if total rows > 17
        num_indexed_rows = 17  # First 17 rows are indexed by RowSets
        page_header = bytearray(self._build_page_header(
            page_index, page_type, num_indexed_rows,
            free_size=0xf26, next_offset=0x88,
            transaction=5, next_page=0x2d
        ))

        # Build heap prefix + extra entry (bytes 32-47)
        heap_prefix = bytearray()
        for row in heap_prefix_and_extra:
            heap_prefix += struct.pack('<HHI', row.field1, row.field2, row.field3)

        # Build data header (bytes 48-63) with next 2 entries
        data_header = bytearray()
        for row in data_header_rows:
            data_header += struct.pack('<HHI', row.field1, row.field2, row.field3)

        # Build regular row data (bytes 64+)
        row_data = bytearray()
        # First 4 rows offsets: heap prefix (32), extra entry (40), data header 1 (48), data header 2 (56)
        row_offsets = [32, 40, 48, 56]

        # Only first 13 regular rows are indexed (total 4 + 13 = 17 indexed rows)
        indexed_regular_count = 13
        row_data_start = 64  # Row data starts at byte 64 of the page

        for i, row in enumerate(regular_rows):
            offset = row_data_start + len(row_data)  # Absolute offset from page start
            row_bytes = struct.pack('<HHI', row.field1, row.field2, row.field3)
            row_data += row_bytes
            if i < indexed_regular_count:
                row_offsets.append(offset)

        # Build RowSets (only for indexed rows)
        # Unknown18 has custom RowSets structure (48 bytes, not 80)
        rowsets = self._build_unknown18_rowsets(row_offsets)

        # Combine: page_header (0-31) + heap_prefix (32-47) + data_header (48-63) + row_data + padding + rowsets
        page = bytearray(page_header[:32])  # Bytes 0-31
        page += heap_prefix  # Bytes 32-47
        page += data_header  # Bytes 48-63
        page += row_data

        # RowSets are stored at the END of the page, starting at offset 0xfd4 (4084)
        rowsets_start = 0xfd4
        current_size = len(page)

        # Add padding between row_data and rowsets
        if current_size < rowsets_start:
            page += b'\x00' * (rowsets_start - current_size)

        # Add RowSets at the end
        page += rowsets

        # Pad to exactly 4096 bytes
        page += b'\x00' * (4096 - len(page))

        return bytes(page)

    def _build_unknown18_rowsets(self, row_offsets: List[int]) -> bytes:
        """Build custom RowSet structure for Unknown18 page.

        Reference structure (48 bytes total):
        - 8 bytes header: [0x00008000][0x00010001]
        - 40 bytes of offset entries (10 entries * 4 bytes each)
        - Each entry is 2 offsets packed together

        Offsets are stored in descending order.
        """
        if len(row_offsets) != 17:
            raise ValueError(f"Unknown18 expects 17 offsets, got {len(row_offsets)}")

        rowsets = bytearray()

        # Header (8 bytes) - uses big-endian byte order!
        rowsets += struct.pack('>II', 0x00008000, 0x01000100)

        # Offset entries (10 entries * 4 bytes = 40 bytes)
        # Each entry packs 2 offsets together
        # Reference pattern: [0x78,0x70], [0x68,0x60], [0x58,0x50], ...

        entries = [
            (row_offsets[11], row_offsets[10]),  # (120, 112)
            (row_offsets[9], row_offsets[8]),    # (104, 96)
            (row_offsets[7], row_offsets[6]),    # (88, 80)
            (row_offsets[5], row_offsets[4]),    # (72, 64)
            (row_offsets[3], row_offsets[2]),    # (56, 48)
            (row_offsets[1], row_offsets[0]),    # (40, 32)
            (24, 16),                            # Extra entry
            (8, 0),                              # Extra entry
        ]

        for offset1, offset2 in entries:
            rowsets += struct.pack('<HH', offset1, offset2)

        # End marker (4 bytes)
        rowsets += struct.pack('<I', 0xffffffff)

        return bytes(rowsets)


class ColorsMarshaller(SpecialPageMarshaller):
    """Marshaller for Colors pages (Table 6).

    Structure from binary analysis of reference Page 14:
    - Page header (bytes 0-31): Standard 32-byte page header
    - Heap prefix (bytes 32-47): Special structure (not f8 ff ff 1f!)
      - 0x20-0x23: 08 00 00 00
      - 0x24-0x27: 00 00 00 00
      - 0x28-0x2B: 00 00 00 00
      - 0x2C-0x2F: 01 01 00 00
    - Color data (bytes 48-175): 8 variable-length color entries (tightly packed)
    - RowSets (bytes 4064-4095): Offsets in REVERSE order
    """

    def marshal_page(self, page_index: int, page_type: int, rows: List[Any]) -> bytes:
        """Generate Colors page with correct heap prefix structure."""
        if len(rows) < 1:
            raise ValueError("Colors requires at least 1 row")

        # Build page header (32 bytes only)
        page_header = bytearray(self._build_page_header(
            page_index, page_type, len(rows),
            free_size=0xf48, next_offset=0x7c,
            transaction=2, next_page=0x2a
        ))

        # Take only first 32 bytes
        page = bytearray(page_header[:32])

        # Heap prefix (bytes 32-47): Special structure from reference
        page += struct.pack('<I', 8)  # 0x20-0x23: 08 00 00 00
        page += b'\x00' * 8  # 0x24-0x2B: 8 bytes of zeros
        page += struct.pack('<I', 0x0101)  # 0x2C-0x2F: 01 01 00 00

        # Build all color entries (tightly packed, variable length)
        row_data = bytearray()
        row_offsets = []

        for color in rows:
            offset = len(row_data)
            # Use ColorRow.marshal_binary() for simple variable-length encoding
            color_bytes = color.marshal_binary(0)
            row_data += color_bytes
            row_offsets.append(offset)

        # Add color data (starts at byte 48, which is offset 16 relative to heap)
        page += row_data

        # Build RowSets at END of page (starting at byte 4064)
        # Reference structure:
        # - Bytes 0-11: 12 zeros
        # - Bytes 12-25: 7 offsets (in reverse order, excluding first offset which is always 0)
        # - Bytes 26-27: 2 zeros
        # - Bytes 28-31: ff00ff00 terminator
        rowsets_start = 4064
        current_size = len(page)

        # Pad to RowSets start
        if current_size < rowsets_start:
            page += b'\x00' * (rowsets_start - current_size)

        # Build RowSets with correct structure
        rowsets = bytearray()

        # 12 zeros
        rowsets += b'\x00' * 12

        # Add offsets in REVERSE order, excluding the first one (offset 0 is implicit)
        for offset in reversed(row_offsets[1:]):  # Skip first offset (0)
            rowsets.extend(struct.pack('<H', offset))

        # 2 zeros
        rowsets += b'\x00' * 2

        # Terminator: ff00ff00
        rowsets += b'\xff\x00\xff\x00'

        # Add rowsets at the end
        page += rowsets

        # Pad to exactly 4096 bytes
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

    Structure from binary analysis of reference Page 40:
    - Page header (bytes 0-31): Standard 32-byte page header
    - Special structure (bytes 32-63):
      - 0x20-0x23: 01 00 00 00 (row count marker)
      - 0x24-0x27: 00 00 00 00 (padding)
      - 0x28-0x2B: 80 02 00 00 (special marker)
      - 0x2C-0x33: 00 00 00 00 00 00 00 00 (padding, 8 bytes)
    - Date field (bytes 64-79): Length marker + date string + padding + unknown1
    - Name field (bytes 80+): unknown2 + length marker + name + padding + unknown3
    """

    def marshal_page(self, page_index: int, page_type: int, rows: List[Any]) -> bytes:
        """Generate History page with correct structure."""
        if len(rows) < 1:
            raise ValueError("History requires at least 1 row")

        history_row = rows[0]

        # Import encode_pdb_string
        from .metadata_rows import encode_pdb_string

        # Build page header (32 bytes only, not 40!)
        page_header = bytearray(self._build_page_header(
            page_index, page_type, len(rows),
            free_size=0xfaa, next_offset=0x28,
            transaction=1, next_page=0x29
        ))

        # Take only first 32 bytes (page header)
        page = bytearray(page_header[:32])

        # Special structure (bytes 32-63)
        page += struct.pack('<I', 1)  # 0x20-0x23: Row count marker
        page += struct.pack('<I', 0)  # 0x24-0x27: Padding
        page += struct.pack('<I', 0x0280)  # 0x28-0x2B: Special marker
        page += b'\x00' * 8  # 0x2C-0x33: Padding (8 bytes)

        # Date field (bytes 64-75)
        # Format: [length_marker (1)][date (10)][unknown1 (1)]
        # NOTE: No padding between date and unknown1!
        page += struct.pack('<B', 0x17)  # Length marker
        page += history_row.date.encode('ascii')  # Date string (10 bytes)
        page += struct.pack('<B', history_row.unknown1)  # unknown1 (immediately after date)

        # Name field (bytes 76-87)
        # Format: [unknown2 (1)][length_marker (1)][name (4)][unknown3 (1)][padding (7)]
        page += struct.pack('<B', history_row.unknown2)  # unknown2 (0x1e)
        name_len = len(history_row.name)
        page += struct.pack('<B', name_len * 2 + 3)  # Length marker (0x0b for "1000")
        page += history_row.name.encode('ascii')  # Name string (4 bytes)
        page += struct.pack('<B', history_row.unknown3)  # unknown3 (0x03) - immediately after name!
        page += b'\x00' * 7  # Padding (7 bytes)

        # Pad to position 0xffc (4092 bytes)
        page += b'\x00' * (0xffc - len(page))

        # Add 4-byte marker at end (bytes 0xffc-0xfff)
        # Format: 01 00 01 00 (appears to be a count or end marker)
        page += struct.pack('<HH', 1, 1)  # Two 16-bit values of 1

        # Now page should be exactly 4096 bytes
        if len(page) != 4096:
            page += b'\x00' * (4096 - len(page))

        return bytes(page)
