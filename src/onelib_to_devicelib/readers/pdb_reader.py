"""
PDB Reader

Read existing PDB files for comparison and validation.
"""

import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from ..writers.rowset import RowSet


@dataclass
class FileHeader:
    """Parsed file header.

    The file header occupies the first page (4096 bytes).
    """
    magic: int
    page_size: int
    num_tables: int
    next_unused_page: int
    unknown1: int
    sequence: int
    gap: int
    table_pointers: List[Dict] = field(default_factory=list)


@dataclass
class ParsedPage:
    """Parsed page with header and rows."""
    header: Dict
    data_header: Dict
    rowsets: List[RowSet]
    rows: List[bytes]


class PDBReader:
    """Read PDB files."""

    def __init__(self, pdb_path: Path):
        """Initialize PDB reader.

        Args:
            pdb_path: Path to PDB file to read
        """
        self.pdb_path = pdb_path
        self.data = pdb_path.read_bytes()

    def parse_file_header(self) -> FileHeader:
        """Parse file header (first page).

        Returns:
            Parsed FileHeader object

        Raises:
            ValueError: If file is too small or invalid
        """
        if len(self.data) < 4096:
            raise ValueError(f"PDB file too small: {len(self.data)} bytes")

        header_data = self.data[:4096]

        # Parse first 28 bytes
        magic, page_size, num_tables = struct.unpack('<III', header_data[:12])
        next_unused, unknown1, sequence, gap = struct.unpack('<IIII', header_data[12:28])

        # Parse table pointers
        table_pointers = []
        offset = 28
        for i in range(num_tables):
            if offset + 16 > 4096:
                raise ValueError(f"Table pointer {i} extends beyond file header")

            table_type, empty_cand, first_page, last_page = struct.unpack('<IIII',
                                                                           header_data[offset:offset + 16])
            table_pointers.append({
                'type': table_type,
                'empty_candidate': empty_cand,
                'first_page': first_page,
                'last_page': last_page
            })
            offset += 16

        return FileHeader(magic, page_size, num_tables, next_unused,
                         unknown1, sequence, gap, table_pointers)

    def parse_page(self, page_index: int) -> ParsedPage:
        """Parse single page.

        Args:
            page_index: Page index to parse

        Returns:
            ParsedPage object

        Raises:
            ValueError: If page index is out of range
        """
        offset = page_index * 4096
        if offset + 4096 > len(self.data):
            raise ValueError(f"Page {page_index} out of range")

        page_data = self.data[offset:offset + 4096]

        # Parse page header (32 bytes)
        magic, pidx, ptype, next_pg = struct.unpack('<IIII', page_data[:16])
        trans, unk2, num_rows, unk3, unk4, flags, free, next_off = struct.unpack('<IIBBBBHH',
                                                                                  page_data[16:32])

        header = {
            'magic': magic,
            'page_index': pidx,
            'page_type': ptype,
            'next_page': next_pg,
            'transaction': trans,
            'num_rows_small': num_rows,
            'unknown3': unk3,
            'page_flags': flags,
            'free_size': free,
            'next_heap_write_offset': next_off
        }

        # Parse data header (8 bytes)
        unk5, num_large, unk6, unk7 = struct.unpack('<HHHH', page_data[40:48])

        data_header = {
            'unknown5': unk5,
            'num_rows_large': num_large,
            'unknown6': unk6,
            'unknown7': unk7
        }

        # Calculate row index start (from end of page)
        num_rowsets = (num_rows // 0x20 + 15) // 16  # Round up
        row_index_size = num_rowsets * 36  # 36 bytes per RowSet
        row_index_offset = 4096 - row_index_size

        # Parse RowSets
        rowsets = []
        for i in range(num_rowsets):
            rs_offset = row_index_offset + (i * 36)
            if rs_offset + 36 > 4096:
                break
            rowset = RowSet.unmarshal_binary(page_data, rs_offset)
            rowsets.append(rowset)

        # Extract row data
        rows = []
        for rowset in rowsets:
            for i, pos in enumerate(rowset.positions):
                if rowset.row_exists(i):
                    # Extract row from heap
                    row_offset = 48 + pos  # After headers
                    if row_offset >= 4096:
                        break
                    # Find row end (next row or end of heap)
                    # For now, just grab remaining data and let parsing handle it
                    rows.append(page_data[row_offset:])

        return ParsedPage(header, data_header, rowsets, rows)

    def analyze_structure(self) -> Dict:
        """Analyze complete PDB structure.

        Returns:
            Dictionary with structure information
        """
        fh = self.parse_file_header()

        structure = {
            'file_size': len(self.data),
            'num_pages': len(self.data) // 4096,
            'tables': {}
        }

        for tp in fh.table_pointers:
            table_type = tp['type']
            structure['tables'][table_type] = {
                'first_page': tp['first_page'],
                'last_page': tp['last_page'],
                'num_pages': tp['last_page'] - tp['first_page'] + 1 if tp['last_page'] >= tp['first_page'] else 0
            }

        return structure

    def get_table_pages(self, table_type: int) -> List[int]:
        """Get page indices for a specific table.

        Args:
            table_type: Table type index (0-19)

        Returns:
            List of page indices
        """
        fh = self.parse_file_header()

        for tp in fh.table_pointers:
            if tp['type'] == table_type:
                if tp['first_page'] == 0 and tp['last_page'] == 0:
                    return []  # Empty table
                return list(range(tp['first_page'], tp['last_page'] + 1))

        return []
