#!/usr/bin/env python3
"""
Compare PDB file structure between generated and reference.
Focus on file-level metrics and table structure.
"""

import sys
sys.path.insert(0, 'src')

from pathlib import Path
from onelib_to_devicelib.readers.pdb_reader import PDBReader


def compare_structure(reference_path: Path, generated_path: Path):
    """Compare file structure."""

    print("=" * 70)
    print("PDB File Structure Comparison")
    print("=" * 70)

    # Read both files
    ref_reader = PDBReader(reference_path)
    gen_reader = PDBReader(generated_path)

    # Parse file headers
    ref_header = ref_reader.parse_file_header()
    gen_header = gen_reader.parse_file_header()

    # File-level comparison
    print("\n[File Level]")
    ref_size = len(ref_reader.data)
    gen_size = len(gen_reader.data)
    ref_pages = ref_size // 4096
    gen_pages = gen_size // 4096

    print(f"Reference: {ref_size:,} bytes ({ref_pages} pages)")
    print(f"Generated: {gen_size:,} bytes ({gen_pages} pages)")

    if ref_size == gen_size:
        print("✅ File size matches")
    else:
        diff = gen_size - ref_size
        pct = (gen_size / ref_size * 100) if ref_size > 0 else 0
        if diff > 0:
            print(f"⚠️  Generated is {diff:,} bytes LARGER (+{pct:.1f}%)")
        else:
            print(f"⚠️  Generated is {abs(diff):,} bytes SMALLER ({pct:.1f}%)")

    if ref_pages == gen_pages:
        print("✅ Page count matches")
    else:
        page_diff = gen_pages - ref_pages
        if page_diff > 0:
            print(f"⚠️  Generated has {page_diff} more pages")
        else:
            print(f"⚠️  Generated has {abs(page_diff)} fewer pages")

    # Header field comparison
    print("\n[Header Fields]")
    header_fields = ['magic', 'page_size', 'num_tables', 'next_unused_page',
                     'unknown1', 'sequence']

    for field in header_fields:
        ref_val = getattr(ref_header, field)
        gen_val = getattr(gen_header, field)
        match = "✅" if ref_val == gen_val else "❌"
        print(f"  {match} {field:20s}: ref={ref_val:10}  gen={gen_val:10}")

    # Table pointer comparison
    print("\n[Table Pointers]")
    table_names = [
        'Tracks', 'Genres', 'Artists', 'Albums', 'Labels', 'Keys', 'Colors',
        'PlaylistTree', 'PlaylistEntries', 'Unknown9', 'Unknown10',
        'HistoryPlaylists', 'HistoryEntries', 'Artwork', 'Unknown14',
        'Unknown15', 'Columns', 'Unknown17', 'Unknown18', 'History'
    ]

    for i, (ref_tp, gen_tp) in enumerate(zip(ref_header.table_pointers, gen_header.table_pointers)):
        name = table_names[i] if i < len(table_names) else f"Table{i}"

        ref_first = ref_tp['first_page']
        ref_last = ref_tp['last_page']
        gen_first = gen_tp['first_page']
        gen_last = gen_tp['last_page']

        ref_pages = ref_last - ref_first + 1 if ref_last >= ref_first else 0
        gen_pages = gen_last - gen_first + 1 if gen_last >= gen_first else 0

        if ref_pages == 0 and gen_pages == 0:
            print(f"  ✓ [{i:2d}] {name:20s} Both empty")
        elif ref_pages == gen_pages and ref_first == gen_first:
            print(f"  ✓ [{i:2d}] {name:20s} ref:{ref_first}-{ref_last} ({ref_pages}p)")
        else:
            print(f"  ✗ [{i:2d}] {name:20s} ref:{ref_first}-{ref_last} ({ref_pages}p)  "
                  f"gen:{gen_first}-{gen_last} ({gen_pages}p)")

    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    if ref_size == gen_size and ref_pages == gen_pages:
        print("✅ File structure matches reference")
    else:
        print("⚠️  File structure differs from reference")
        print("\nPossible causes:")
        if gen_size > ref_size:
            print("  - Generated file is larger - inefficient storage or extra data")
            print("  - Track rows might be larger than reference")
            print("  - String heap might not be optimized")
            print("  - Extra pages allocated for some tables")
        if gen_pages > ref_pages:
            print(f"  - {gen_pages - ref_pages} extra pages allocated")
        print("\nNext steps:")
        print("  - Run page-level comparison to identify which tables differ")
        print("  - Run track row comparison to check row structure")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python tests/compare_pdb_structure.py <reference.pdb> <generated.pdb>")
        sys.exit(1)

    reference = Path(sys.argv[1])
    generated = Path(sys.argv[2])

    if not reference.exists():
        print(f"❌ Reference file not found: {reference}")
        sys.exit(1)

    if not generated.exists():
        print(f"❌ Generated file not found: {generated}")
        sys.exit(1)

    compare_structure(reference, generated)
