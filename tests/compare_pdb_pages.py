#!/usr/bin/env python3
"""
Compare PDB pages between generated and reference.
Identifies which pages have different headers, row counts, or structure.
"""

import sys
sys.path.insert(0, 'src')

from pathlib import Path
from onelib_to_devicelib.readers.pdb_reader import PDBReader


def compare_pages(reference_path: Path, generated_path: Path):
    """Compare page-level structure."""

    print("=" * 70)
    print("PDB Page-Level Comparison")
    print("=" * 70)

    # Read both files
    ref_reader = PDBReader(reference_path)
    gen_reader = PDBReader(generated_path)

    # Parse file headers
    ref_header = ref_reader.parse_file_header()
    gen_header = gen_reader.parse_file_header()

    # Table names
    table_names = [
        'Tracks', 'Genres', 'Artists', 'Albums', 'Labels', 'Keys', 'Colors',
        'PlaylistTree', 'PlaylistEntries', 'Unknown9', 'Unknown10',
        'HistoryPlaylists', 'HistoryEntries', 'Artwork', 'Unknown14',
        'Unknown15', 'Columns', 'Unknown17', 'Unknown18', 'History'
    ]

    # Track page differences by table
    page_diffs = []

    print("\n[Table Page Comparison]")
    for table_id, (ref_tp, gen_tp) in enumerate(zip(ref_header.table_pointers, gen_header.table_pointers)):
        name = table_names[table_id] if table_id < len(table_names) else f"Table{table_id}"

        ref_first = ref_tp['first_page']
        ref_last = ref_tp['last_page']
        gen_first = gen_tp['first_page']
        gen_last = gen_tp['last_page']

        ref_pages = ref_last - ref_first + 1 if ref_last >= ref_first else 0
        gen_pages = gen_last - gen_first + 1 if gen_last >= gen_first else 0

        if ref_pages == 0 and gen_pages == 0:
            status = "✓"
        elif ref_pages == gen_pages:
            status = "✓"
        else:
            status = "✗"
            page_diffs.append({
                'table_id': table_id,
                'name': name,
                'ref_pages': ref_pages,
                'gen_pages': gen_pages,
                'diff': gen_pages - ref_pages
            })

        print(f"  {status} [{table_id:2d}] {name:20s} ref:{ref_pages:2d}p  gen:{gen_pages:2d}p")

    # Detailed comparison for tables with differences
    if page_diffs:
        print("\n[Detailed Page Analysis for Tables with Differences]")
        for diff in page_diffs[:5]:  # Limit to first 5
            table_id = diff['table_id']
            name = diff['name']

            print(f"\n{name} (Table {table_id}):")
            print(f"  Reference: {diff['ref_pages']} pages")
            print(f"  Generated: {diff['gen_pages']} pages")
            print(f"  Difference: {diff['diff']:+d} pages")

            # Compare first page header
            ref_pages = ref_reader.get_table_pages(table_id)
            gen_pages = gen_reader.get_table_pages(table_id)

            if ref_pages and gen_pages:
                ref_page = ref_reader.parse_page(ref_pages[0])
                gen_page = gen_reader.parse_page(gen_pages[0])

                # Compare header fields
                header_fields = ['magic', 'page_type', 'page_flags', 'num_rows_small']
                header_diffs = []

                for field in header_fields:
                    ref_val = ref_page.header.get(field)
                    gen_val = gen_page.header.get(field)
                    if ref_val != gen_val:
                        header_diffs.append((field, ref_val, gen_val))

                if header_diffs:
                    print(f"  First page header differences:")
                    for field, ref_val, gen_val in header_diffs[:3]:
                        print(f"    - {field}: ref={ref_val} gen={gen_val}")
                else:
                    print(f"  ✓ First page header matches")

                # Compare row counts
                ref_rows = ref_page.header.get('num_rows_small', 0)
                gen_rows = gen_page.header.get('num_rows_small', 0)
                print(f"  Row counts: ref={ref_rows} gen={gen_rows}")

    # Check for track row size differences
    print("\n[Track Row Size Analysis]")
    track_pages = ref_reader.get_table_pages(0)  # Table 0 = Tracks
    gen_track_pages = gen_reader.get_table_pages(0)

    if track_pages and gen_track_pages:
        ref_page = ref_reader.parse_page(track_pages[0])
        gen_page = gen_reader.parse_page(gen_track_pages[0])

        # Calculate average row size
        if ref_page.rowsets and gen_page.rowsets:
            ref_rs = ref_page.rowsets[0]
            gen_rs = gen_page.rowsets[0]

            # RowSets contain positions, we can estimate row sizes
            print(f"  Reference RowSet[0]: {ref_rs.active_rows} active rows")
            print(f"  Generated RowSet[0]: {gen_rs.active_rows} active rows")

            # Check if positions differ significantly
            if len(ref_rs.positions) > 1 and len(gen_rs.positions) > 1:
                ref_avg = (ref_rs.positions[1] - ref_rs.positions[0]) if ref_rs.positions[1] > ref_rs.positions[0] else 0
                gen_avg = (gen_rs.positions[1] - gen_rs.positions[0]) if gen_rs.positions[1] > gen_rs.positions[0] else 0

                if ref_avg > 0 and gen_avg > 0:
                    print(f"  Estimated row sizes: ref={ref_avg} bytes, gen={gen_avg} bytes")
                    if ref_avg != gen_avg:
                        print(f"  ⚠️  Row size difference: {gen_avg - ref_avg:+d} bytes")

    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    if page_diffs:
        print(f"Found {len(page_diffs)} tables with page count differences")
        print("\nPriority tables to investigate:")
        for diff in sorted(page_diffs, key=lambda x: abs(x['diff']), reverse=True)[:5]:
            print(f"  - {diff['name']}: {diff['diff']:+d} pages")
        print("\nNext steps:")
        print("  1. Run track row comparison for detailed field analysis")
        print("  2. Check if our row structure is larger than reference")
        print("  3. Verify string heap storage efficiency")
    else:
        print("✅ All table page counts match reference")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python tests/compare_pdb_pages.py <reference.pdb> <generated.pdb>")
        sys.exit(1)

    reference = Path(sys.argv[1])
    generated = Path(sys.argv[2])

    if not reference.exists():
        print(f"❌ Reference file not found: {reference}")
        sys.exit(1)

    if not generated.exists():
        print(f"❌ Generated file not found: {generated}")
        sys.exit(1)

    compare_pages(reference, generated)
