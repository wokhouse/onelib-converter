#!/usr/bin/env python3
"""
Bitwise PDB Comparison Test

Compares generated PDB file against reference to measure bitwise similarity.
This is the main feedback loop for PDB format refinement.

Usage:
    python tests/test_pdb_comparison.py <source_dir> [options]

Example:
    python tests/test_pdb_comparison.py validation_data/onelib_only
    python tests/test_pdb_comparison.py validation_data/onelib_only --verbose
"""

import argparse
import os
import struct
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from onelib_to_devicelib.convert import Converter


def compare_pdb_files(generated_path: Path, reference_path: Path, verbose: bool = False) -> dict:
    """Compare two PDB files byte-by-byte.

    Args:
        generated_path: Path to generated PDB file
        reference_path: Path to reference PDB file
        verbose: Show detailed hex dump of differences

    Returns:
        Dictionary with comparison results
    """
    if not generated_path.exists():
        return {
            'error': f'Generated file not found: {generated_path}',
            'success': False
        }

    if not reference_path.exists():
        return {
            'error': f'Reference file not found: {reference_path}',
            'success': False
        }

    gen_data = generated_path.read_bytes()
    ref_data = reference_path.read_bytes()

    # Basic stats
    gen_size = len(gen_data)
    ref_size = len(ref_data)

    # Calculate page-level differences
    page_size = 4096
    gen_pages = gen_size // page_size
    ref_pages = ref_size // page_size

    page_differences = []

    # Compare each page
    min_pages = min(gen_pages, ref_pages)
    for page_idx in range(min_pages):
        gen_page = gen_data[page_idx * page_size:(page_idx + 1) * page_size]
        ref_page = ref_data[page_idx * page_size:(page_idx + 1) * page_size]

        if gen_page != ref_page:
            # Count differing bytes in this page
            diff_count = sum(1 for a, b in zip(gen_page, ref_page) if a != b)
            page_differences.append({
                'page_index': page_idx,
                'diff_count': diff_count,
                'match_count': page_size - diff_count
            })

    # Extra pages in generated
    extra_gen_pages = []
    for page_idx in range(min_pages, gen_pages):
        extra_gen_pages.append(page_idx)

    # Extra pages in reference
    extra_ref_pages = []
    for page_idx in range(min_pages, ref_pages):
        extra_ref_pages.append(page_idx)

    # Calculate overall similarity
    total_diff_bytes = sum(p['diff_count'] for p in page_differences)
    # Matching bytes = all bytes in matching pages + matching bytes in differing pages
    matching_pages = min_pages - len(page_differences)
    total_match_bytes = (matching_pages * page_size) + sum(p['match_count'] for p in page_differences)
    total_compared = min(gen_size, ref_size)

    similarity_percent = (total_match_bytes / total_compared * 100) if total_compared > 0 else 0

    result = {
        'success': True,
        'generated_size': gen_size,
        'reference_size': ref_size,
        'generated_pages': gen_pages,
        'reference_pages': ref_pages,
        'page_differences': page_differences,
        'extra_gen_pages': extra_gen_pages,
        'extra_ref_pages': extra_ref_pages,
        'total_diff_bytes': total_diff_bytes,
        'total_match_bytes': total_match_bytes,
        'similarity_percent': similarity_percent,
        'size_match': gen_size == ref_size
    }

    # Add verbose hex dump if requested
    if verbose and page_differences:
        result['hex_dump'] = []
        for page_diff in page_differences[:5]:  # First 5 pages only
            page_idx = page_diff['page_index']
            gen_page = gen_data[page_idx * page_size:(page_idx + 1) * page_size]
            ref_page = ref_data[page_idx * page_size:(page_idx + 1) * page_size]

            hex_lines = []
            for offset in range(0, min(256, page_size), 16):  # First 256 bytes only
                gen_chunk = gen_page[offset:offset + 16]
                ref_chunk = ref_page[offset:offset + 16]

                if gen_chunk != ref_chunk:
                    gen_hex = ' '.join(f'{b:02x}' for b in gen_chunk)
                    ref_hex = ' '.join(f'{b:02x}' for b in ref_chunk)
                    hex_lines.append({
                        'offset': offset,
                        'generated': gen_hex,
                        'reference': ref_hex
                    })

            result['hex_dump'].append({
                'page_index': page_idx,
                'lines': hex_lines
            })

    return result


def print_comparison_results(result: dict, verbose: bool = False):
    """Print comparison results in a formatted way.

    Args:
        result: Result dictionary from compare_pdb_files
        verbose: Show detailed hex dump
    """
    if not result.get('success'):
        print(f"❌ Error: {result.get('error')}")
        return

    print("=" * 70)
    print("PDB Bitwise Comparison Results")
    print("=" * 70)

    # File size comparison
    print("\nFile Size Comparison:")
    print(f"  Reference: {result['reference_size']:,} bytes ({result['reference_pages']} pages)")
    print(f"  Generated: {result['generated_size']:,} bytes ({result['generated_pages']} pages)")

    if result['size_match']:
        print(f"  ✅ Size matches exactly!")
    else:
        size_diff = result['reference_size'] - result['generated_size']
        size_pct = (result['generated_size'] / result['reference_size'] * 100) if result['reference_size'] > 0 else 0
        print(f"  ✗ Size differs by {size_diff:,} bytes ({size_pct:.1f}% of reference)")

    # Overall similarity
    print("\nOverall Bitwise Similarity:")
    print(f"  Matching bytes: {result['total_match_bytes']:,} / {result['total_match_bytes'] + result['total_diff_bytes']:,}")
    print(f"  Differing bytes: {result['total_diff_bytes']:,}")
    print(f"  Similarity: {result['similarity_percent']:.2f}%")

    # Page-by-page breakdown
    print("\nPage-by-Page Differences:")
    if not result['page_differences']:
        print("  ✅ All pages match perfectly!")
    else:
        print(f"  Pages with differences: {len(result['page_differences'])}")

        # Group by severity
        critical = [p for p in result['page_differences'] if p['diff_count'] > 500]
        high = [p for p in result['page_differences'] if 100 < p['diff_count'] <= 500]
        medium = [p for p in result['page_differences'] if 10 < p['diff_count'] <= 100]
        low = [p for p in result['page_differences'] if p['diff_count'] <= 10]

        if critical:
            print(f"\n  🔴 CRITICAL (>500 bytes): {len(critical)} pages")
            for p in critical[:5]:
                print(f"      Page {p['page_index']}: {p['diff_count']} bytes differ")
            if len(critical) > 5:
                print(f"      ... and {len(critical) - 5} more")

        if high:
            print(f"\n  🟠 HIGH (100-500 bytes): {len(high)} pages")
            for p in high[:5]:
                print(f"      Page {p['page_index']}: {p['diff_count']} bytes differ")
            if len(high) > 5:
                print(f"      ... and {len(high) - 5} more")

        if medium:
            print(f"\n  🟡 MEDIUM (10-100 bytes): {len(medium)} pages")

        if low:
            print(f"\n  🟢 LOW (≤10 bytes): {len(low)} pages")

    # Extra pages
    if result['extra_gen_pages']:
        print(f"\n  Extra pages in generated: {result['extra_gen_pages']}")
    if result['extra_ref_pages']:
        print(f"\n  Extra pages in reference: {result['extra_ref_pages']}")

    # Verbose hex dump
    if verbose and 'hex_dump' in result:
        print("\n" + "=" * 70)
        print("Detailed Hex Dump (First 256 bytes of differing pages)")
        print("=" * 70)

        for page_dump in result['hex_dump']:
            page_idx = page_dump['page_index']
            print(f"\n--- Page {page_idx} ---")
            for line in page_dump['lines']:
                print(f"  Offset {line['offset']:04x}:")
                print(f"    Generated: {line['generated']}")
                print(f"    Reference: {line['reference']}")
                if line['generated'] != line['reference']:
                    # Show diff markers
                    gen_bytes = [bytes.fromhex(b) for b in line['generated'].split()]
                    ref_bytes = [bytes.fromhex(b) for b in line['reference'].split()]
                    diff = ' >>> ' if gen_bytes != ref_bytes else '     '
                    print(f"    {diff}")

    print("\n" + "=" * 70)

    # Verdict
    if result['similarity_percent'] >= 99.9:
        print("✅ EXCELLENT: File is >99.9% identical to reference!")
    elif result['similarity_percent'] >= 99.0:
        print("✅ GOOD: File is >99% identical to reference.")
    elif result['similarity_percent'] >= 95.0:
        print("⚠️  FAIR: File is >95% identical, but needs improvement.")
    else:
        print("❌ POOR: File is <95% identical, major issues detected.")

    print("=" * 70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Compare generated PDB against reference')
    parser.add_argument('source_dir', type=str, help='Source directory with OneLibrary export')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed hex dump')
    parser.add_argument('--output', '-o', type=str, default='/tmp/pdb_comparison_test',
                       help='Output directory for generated files')

    args = parser.parse_args()

    source_path = Path(args.source_dir)
    output_path = Path(args.output)

    # Check source directory
    if not source_path.exists():
        print(f"❌ Source directory not found: {source_path}")
        sys.exit(1)

    # Reference PDB path
    reference_pdb = source_path / "PIONEER" / "rekordbox" / "export.pdb"

    # For comparison, we need to compare against the reference dual-format export
    # If source is onelib_only, compare against onelib_and_devicelib
    if "onelib_only" in str(source_path):
        reference_dir = source_path.parent / "onelib_and_devicelib"
        reference_pdb = reference_dir / "PIONEER" / "rekordbox" / "export.pdb"

    if not reference_pdb.exists():
        print(f"❌ Reference PDB not found: {reference_pdb}")
        sys.exit(1)

    # Parse source and generate PDB
    print(f"📂 Source: {source_path}")
    print(f"📄 Reference PDB: {reference_pdb}")
    print(f"📤 Output: {output_path}")
    print()

    # Check for database
    db_path = source_path / "PIONEER" / "rekordbox" / "exportLibrary.db"
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        sys.exit(1)

    # Generate PDB using converter
    print("🔄 Converting OneLibrary to dual-format...")
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        converter = Converter(str(source_path), str(output_path))
        converter.parse()
        converter.convert(copy_contents=False, generate_waveforms=False)
    except Exception as e:
        print(f"❌ Error during conversion: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Path to generated PDB
    generated_pdb = output_path / "PIONEER" / "rekordbox" / "export.pdb"

    if not generated_pdb.exists():
        print(f"❌ Generated PDB not found: {generated_pdb}")
        sys.exit(1)

    # Compare files
    print("🔄 Comparing files...")
    result = compare_pdb_files(generated_pdb, reference_pdb, verbose=args.verbose)

    # Print results
    print()
    print_comparison_results(result, verbose=args.verbose)

    # Exit with appropriate code
    if result['similarity_percent'] >= 99.0:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
