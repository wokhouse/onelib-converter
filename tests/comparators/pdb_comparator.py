"""
Page-Level PDB Comparator

Compare two PDB files at page, rowset, and row level.
"""

from pathlib import Path
from typing import Dict, List, Optional

from onelib_to_devicelib.readers.pdb_reader import PDBReader, ParsedPage


class PDBComparator:
    """Compare two PDB files."""

    def __init__(self, generated_path: Path, reference_path: Path):
        """Initialize comparator.

        Args:
            generated_path: Path to generated PDB file
            reference_path: Path to reference PDB file
        """
        self.generated = PDBReader(generated_path)
        self.reference = PDBReader(reference_path)

    def compare_structure(self) -> Dict:
        """Compare file structure.

        Returns:
            Dictionary with structure comparison results
        """
        gen_struct = self.generated.analyze_structure()
        ref_struct = self.reference.analyze_structure()

        return {
            'file_size_match': gen_struct['file_size'] == ref_struct['file_size'],
            'num_pages_match': gen_struct['num_pages'] == ref_struct['num_pages'],
            'generated_size': gen_struct['file_size'],
            'reference_size': ref_struct['file_size'],
            'generated_pages': gen_struct['num_pages'],
            'reference_pages': ref_struct['num_pages'],
        }

    def compare_page_headers(self, page_index: int) -> Dict:
        """Compare page headers.

        Args:
            page_index: Page index to compare

        Returns:
            Dictionary with header comparison results
        """
        gen_page = self.generated.parse_page(page_index)
        ref_page = self.reference.parse_page(page_index)

        differences = []

        for key in ['magic', 'page_index', 'page_type', 'next_page',
                    'transaction', 'num_rows_small', 'page_flags',
                    'free_size', 'next_heap_write_offset']:
            gen_val = gen_page.header.get(key, None)
            ref_val = ref_page.header.get(key, None)

            if gen_val != ref_val:
                differences.append({
                    'field': key,
                    'generated': gen_val,
                    'reference': ref_val
                })

        return {
            'page_index': page_index,
            'differences': differences,
            'match': len(differences) == 0
        }

    def compare_rowsets(self, page_index: int) -> Dict:
        """Compare RowSet structures.

        Args:
            page_index: Page index to compare

        Returns:
            Dictionary with RowSet comparison results
        """
        gen_page = self.generated.parse_page(page_index)
        ref_page = self.reference.parse_page(page_index)

        if len(gen_page.rowsets) != len(ref_page.rowsets):
            return {
                'error': 'RowSet count mismatch',
                'generated_count': len(gen_page.rowsets),
                'reference_count': len(ref_page.rowsets)
            }

        differences = []

        for i, (gen_rs, ref_rs) in enumerate(zip(gen_page.rowsets, ref_page.rowsets)):
            if gen_rs.active_rows != ref_rs.active_rows:
                differences.append({
                    'rowset': i,
                    'field': 'active_rows',
                    'generated': f"0x{gen_rs.active_rows:04x}",
                    'reference': f"0x{ref_rs.active_rows:04x}"
                })

            if gen_rs.positions != ref_rs.positions:
                # Show first 5 positions
                gen_pos = gen_rs.positions[:5]
                ref_pos = ref_rs.positions[:5]
                differences.append({
                    'rowset': i,
                    'field': 'positions',
                    'generated': gen_pos,
                    'reference': ref_pos
                })

        return {
            'page_index': page_index,
            'differences': differences,
            'match': len(differences) == 0
        }

    def compare_track_rows(self, page_index: int, row_index: int) -> Dict:
        """Compare individual track rows.

        Args:
            page_index: Page index
            row_index: Row index within the page

        Returns:
            Dictionary with row comparison results
        """
        gen_page = self.generated.parse_page(page_index)
        ref_page = self.reference.parse_page(page_index)

        if row_index >= len(gen_page.rows) or row_index >= len(ref_page.rows):
            return {
                'error': 'Row index out of bounds',
                'gen_rows': len(gen_page.rows),
                'ref_rows': len(ref_page.rows)
            }

        gen_row = gen_page.rows[row_index]
        ref_row = ref_page.rows[row_index]

        # Compare fixed header (first 90 bytes)
        header_size = min(90, len(gen_row), len(ref_row))
        gen_header = gen_row[:header_size]
        ref_header = ref_row[:header_size]

        header_diffs = []
        for i in range(header_size):
            if gen_header[i] != ref_header[i]:
                header_diffs.append(i)

        # Try to parse struct fields for more meaningful comparison
        field_diffs = []
        if len(gen_row) >= 90 and len(ref_row) >= 90:
            # Parse key fields
            import struct

            # unnamed0 (bytes 0-1)
            gen_unnamed0 = struct.unpack('<H', gen_row[0:2])[0]
            ref_unnamed0 = struct.unpack('<H', ref_row[0:2])[0]
            if gen_unnamed0 != ref_unnamed0:
                field_diffs.append(('unnamed0', gen_unnamed0, ref_unnamed0))

            # index_shift (bytes 2-3)
            gen_shift = struct.unpack('<H', gen_row[2:4])[0]
            ref_shift = struct.unpack('<H', ref_row[2:4])[0]
            if gen_shift != ref_shift:
                field_diffs.append(('index_shift', gen_shift, ref_shift))

            # track_id (bytes 72-75)
            gen_id = struct.unpack('<I', gen_row[72:76])[0]
            ref_id = struct.unpack('<I', ref_row[72:76])[0]
            if gen_id != ref_id:
                field_diffs.append(('track_id', gen_id, ref_id))

        return {
            'page_index': page_index,
            'row_index': row_index,
            'header_differences': header_diffs,
            'field_differences': field_diffs,
            'header_match': len(header_diffs) == 0,
            'generated_size': len(gen_row),
            'reference_size': len(ref_row)
        }

    def generate_report(self) -> str:
        """Generate comprehensive comparison report.

        Returns:
            Multi-line string report
        """
        lines = []
        lines.append("=" * 80)
        lines.append("PDB Comparison Report")
        lines.append("=" * 80)

        # Structure comparison
        struct = self.compare_structure()
        lines.append("\n--- File Structure ---")
        lines.append(f"Generated: {struct['generated_size']:,} bytes, {struct['generated_pages']} pages")
        lines.append(f"Reference: {struct['reference_size']:,} bytes, {struct['reference_pages']} pages")
        lines.append(f"Size match: {'✅' if struct['file_size_match'] else '❌'}")
        lines.append(f"Pages match: {'✅' if struct['num_pages_match'] else '❌'}")

        # Page header comparison (first 5 pages)
        lines.append("\n--- Page Headers (first 5 pages) ---")
        for i in range(min(5, struct['generated_pages'], struct['reference_pages'])):
            try:
                comp = self.compare_page_headers(i)
                if comp['match']:
                    lines.append(f"Page {i}: ✅ Match")
                else:
                    lines.append(f"Page {i}: ❌ {len(comp['differences'])} differences")
                    for diff in comp['differences'][:3]:
                        lines.append(f"  - {diff['field']}: {diff['generated']} vs {diff['reference']}")
            except Exception as e:
                lines.append(f"Page {i}: ⚠️  Error: {e}")

        # RowSet comparison (first track page)
        lines.append("\n--- RowSet Structure (Page 0 - Tracks) ---")
        try:
            rs_comp = self.compare_rowsets(0)
            if 'error' in rs_comp:
                lines.append(f"⚠️  {rs_comp['error']}")
            elif rs_comp.get('match'):
                lines.append("✅ RowSets match")
            else:
                for diff in rs_comp.get('differences', [])[:5]:
                    lines.append(f"❌ RowSet {diff['rowset']}.{diff['field']}: {diff['generated']} vs {diff['reference']}")
        except Exception as e:
            lines.append(f"⚠️  Error: {e}")

        # Track row comparison (first 3 tracks)
        lines.append("\n--- Track Rows (Page 0 - first 3) ---")
        for i in range(min(3, 3)):
            try:
                row_comp = self.compare_track_rows(0, i)
                if 'error' in row_comp:
                    lines.append(f"Row {i}: ⚠️  {row_comp['error']}")
                elif row_comp.get('header_match'):
                    lines.append(f"Row {i}: ✅ Match ({row_comp['generated_size']} bytes)")
                else:
                    lines.append(f"Row {i}: ❌ {len(row_comp['header_differences'])} byte differences")
                    lines.append(f"  Sizes: {row_comp['generated_size']} vs {row_comp['reference_size']} bytes")
                    for field_diff in row_comp['field_differences'][:3]:
                        lines.append(f"  - {field_diff[0]}: {field_diff[1]} vs {field_diff[2]}")
            except Exception as e:
                lines.append(f"Row {i}: ⚠️  Error: {e}")

        lines.append("\n" + "=" * 80)

        return "\n".join(lines)


def main():
    """Command-line entry point for PDB comparison."""
    import sys

    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <generated.pdb> <reference.pdb>")
        sys.exit(1)

    generated = Path(sys.argv[1])
    reference = Path(sys.argv[2])

    if not generated.exists():
        print(f"Error: Generated file not found: {generated}")
        sys.exit(1)

    if not reference.exists():
        print(f"Error: Reference file not found: {reference}")
        sys.exit(1)

    comparator = PDBComparator(generated, reference)
    report = comparator.generate_report()
    print(report)


if __name__ == '__main__':
    main()
