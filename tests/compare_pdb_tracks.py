#!/usr/bin/env python3
"""
Compare track rows between generated and reference PDB.
Does field-by-field comparison of first few tracks.
"""

import sys
sys.path.insert(0, 'src')

from pathlib import Path
import struct
from onelib_to_devicelib.readers.pdb_reader import PDBReader


def parse_track_header(row_data: bytes) -> dict:
    """Parse track row header fields.

    Returns dict of field values for comparison.
    """
    if len(row_data) < 94:
        return {'error': f'Row too short: {len(row_data)} bytes'}

    fields = {}

    # Parse critical fields (bytes 0-93)
    fields['row_offset'] = struct.unpack('<H', row_data[0:2])[0]
    fields['index_shift'] = struct.unpack('<H', row_data[2:4])[0]
    fields['bitmask'] = struct.unpack('<I', row_data[4:8])[0]
    fields['sample_rate'] = struct.unpack('<I', row_data[8:12])[0]
    fields['composer_id'] = struct.unpack('<I', row_data[12:16])[0]
    fields['file_size'] = struct.unpack('<I', row_data[16:20])[0]
    fields['checksum'] = struct.unpack('<I', row_data[20:24])[0]
    fields['unnamed7'] = struct.unpack('<H', row_data[24:26])[0]
    fields['unnamed8'] = struct.unpack('<H', row_data[26:28])[0]
    fields['artwork_id'] = struct.unpack('<I', row_data[28:32])[0]
    fields['key_id'] = struct.unpack('<I', row_data[32:36])[0]
    fields['original_artist_id'] = struct.unpack('<I', row_data[36:40])[0]
    fields['label_id'] = struct.unpack('<I', row_data[40:44])[0]
    fields['remixer_id'] = struct.unpack('<I', row_data[44:48])[0]
    fields['bitrate'] = struct.unpack('<I', row_data[48:52])[0]
    fields['track_number'] = struct.unpack('<I', row_data[52:56])[0]
    fields['tempo'] = struct.unpack('<I', row_data[56:60])[0]
    fields['genre_id'] = struct.unpack('<I', row_data[60:64])[0]
    fields['album_id'] = struct.unpack('<I', row_data[64:68])[0]
    fields['artist_id'] = struct.unpack('<I', row_data[68:72])[0]
    fields['id'] = struct.unpack('<I', row_data[72:76])[0]
    fields['disc_number'] = struct.unpack('<H', row_data[76:78])[0]
    fields['play_count'] = struct.unpack('<H', row_data[78:80])[0]
    fields['year'] = struct.unpack('<H', row_data[80:82])[0]
    fields['sample_depth'] = struct.unpack('<H', row_data[82:84])[0]
    fields['duration'] = struct.unpack('<H', row_data[84:86])[0]
    fields['unnamed26'] = struct.unpack('<H', row_data[86:88])[0]
    fields['color_id'] = row_data[88]
    fields['rating'] = row_data[89]
    fields['file_type'] = struct.unpack('<H', row_data[90:92])[0]
    fields['unnamed30'] = struct.unpack('<H', row_data[92:94])[0]

    return fields


def compare_tracks(reference_path: Path, generated_path: Path, max_tracks: int = 5):
    """Compare track row structure."""

    print("=" * 70)
    print("PDB Track Row Comparison")
    print("=" * 70)

    # Read both files
    ref_reader = PDBReader(reference_path)
    gen_reader = PDBReader(generated_path)

    # Get track pages (Table 0)
    ref_track_pages = ref_reader.get_table_pages(0)
    gen_track_pages = gen_reader.get_table_pages(0)

    if not ref_track_pages or not gen_track_pages:
        print("❌ No track pages found in one or both files")
        return

    print(f"\nReference track pages: {len(ref_track_pages)}")
    print(f"Generated track pages: {len(gen_track_pages)}")

    # Compare first N tracks
    track_count = 0
    total_matches = 0
    total_diffs = 0

    # Track which fields differ
    field_diff_counts = {}

    for ref_page_idx in ref_track_pages[:1]:  # Just first page for now
        print(f"\n[Page {ref_page_idx}]")

        # Get page data
        ref_page_offset = ref_page_idx * 4096
        gen_page_offset = gen_track_pages[0] * 4096 if gen_track_pages else 0

        ref_page_data = ref_reader.data[ref_page_offset:ref_page_offset + 4096]
        gen_page_data = gen_reader.data[gen_page_offset:gen_page_offset + 4096]

        # Parse page headers to get row info
        ref_num_rows = struct.unpack('<B', ref_page_data[22:23])[0]

        # Track rows start at offset 48
        track_row_offset = 48

        # Compare each track row
        for row_idx in range(min(ref_num_rows, max_tracks)):
            print(f"\n  Track {row_idx + 1}:")

            # Extract track rows (estimate 200 bytes per row)
            ref_row_start = ref_page_offset + track_row_offset + (row_idx * 200)
            gen_row_start = gen_page_offset + track_row_offset + (row_idx * 200)

            if ref_row_start + 94 > len(ref_reader.data) or gen_row_start + 94 > len(gen_reader.data):
                print(f"    ⚠️  Row data out of bounds")
                break

            ref_row = ref_reader.data[ref_row_start:ref_row_start + 200]
            gen_row = gen_reader.data[gen_row_start:gen_row_start + 200]

            # Parse headers
            ref_fields = parse_track_header(ref_row)
            gen_fields = parse_track_header(gen_row)

            if 'error' in ref_fields or 'error' in gen_fields:
                print(f"    ⚠️  Error parsing row: {ref_fields.get('error', gen_fields.get('error'))}")
                continue

            # Compare critical fields first
            critical_matches = True
            critical_fields = ['row_offset', 'bitmask', 'unnamed30']

            for field in critical_fields:
                if ref_fields[field] != gen_fields[field]:
                    print(f"    ❌ CRITICAL {field}: ref=0x{ref_fields[field]:04x} "
                          f"gen=0x{gen_fields[field]:04x}")
                    critical_matches = False
                    field_diff_counts[field] = field_diff_counts.get(field, 0) + 1

            if critical_matches:
                print(f"    ✅ All critical fields match")

            # Compare all fields
            field_diffs = []
            for field in ref_fields:
                if field == 'error':
                    continue
                if ref_fields[field] != gen_fields[field]:
                    field_diffs.append(field)
                    field_diff_counts[field] = field_diff_counts.get(field, 0) + 1

            if field_diffs:
                total_diffs += 1
                print(f"    ⚠️  {len(field_diffs)} fields differ:")

                # Show first 5 differences
                for field in field_diffs[:5]:
                    ref_val = ref_fields[field]
                    gen_val = gen_fields[field]
                    print(f"      - {field:20s}: ref={ref_val:10}  gen={gen_val:10}")

                if len(field_diffs) > 5:
                    print(f"      ... and {len(field_diffs) - 5} more")
            else:
                total_matches += 1
                print(f"    ✅ All fields match (row size: {len(ref_row)} bytes)")

            track_count += 1
            if track_count >= max_tracks:
                break

        if track_count >= max_tracks:
            break

    # Summary
    print("\n" + "=" * 70)
    print("Analysis Summary")
    print("=" * 70)
    print(f"Compared {track_count} tracks")
    print(f"  ✅ Full matches: {total_matches}")
    print(f"  ⚠️  Partial matches: {total_diffs}")

    if field_diff_counts:
        print(f"\nMost common field differences:")
        sorted_diffs = sorted(field_diff_counts.items(), key=lambda x: x[1], reverse=True)
        for field, count in sorted_diffs[:10]:
            print(f"  - {field:20s}: {count} tracks")

    print("\nRecommendations:")
    if total_diffs > 0:
        print("  1. Check if non-critical field differences matter")
        print("  2. Verify our row size matches reference")
        print("  3. Check string encoding if string fields differ")
    else:
        print("  ✅ Track rows look good - focus on other aspects")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python tests/compare_pdb_tracks.py <reference.pdb> <generated.pdb> [max_tracks]")
        sys.exit(1)

    reference = Path(sys.argv[1])
    generated = Path(sys.argv[2])
    max_tracks = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    if not reference.exists():
        print(f"❌ Reference file not found: {reference}")
        sys.exit(1)

    if not generated.exists():
        print(f"❌ Generated file not found: {generated}")
        sys.exit(1)

    compare_tracks(reference, generated, max_tracks)
