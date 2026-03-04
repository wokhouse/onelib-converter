#!/usr/bin/env python3
"""
Quick corruption check for PDB files.
Checks only fields known to cause rekordbox to crash/reject the file.

CRITICAL FIELDS (from REX project research):
- unnamed30 = 0x3 (bytes 92-93 in TrackRow) - CRITICAL
- Page flags: 0x64 for index pages, 0x34 for data pages
- Magic number: 0x00000000 (bytes 0-3)
- Track row offset: 0x24 (bytes 0-1)
"""

import sys
sys.path.insert(0, 'src')

from pathlib import Path
import struct


def check_critical_fields(pdb_path: Path) -> bool:
    """Check CRITICAL corruption-causing fields.

    Returns:
        True if all critical fields are correct, False otherwise
    """
    print(f"Checking {pdb_path} for corruption issues...")
    print("=" * 70)

    issues = []

    # Read file
    data = pdb_path.read_bytes()

    # Check 1: Magic number (bytes 0-3)
    magic = struct.unpack('<I', data[0:4])[0]
    if magic != 0x00000000:
        issues.append(f"❌ Magic number: 0x{magic:08x} (expected 0x00000000)")
    else:
        print("✅ Magic number: 0x00000000")

    # Check 2: Page size (bytes 4-7)
    page_size = struct.unpack('<I', data[4:8])[0]
    if page_size != 4096:
        issues.append(f"❌ Page size: {page_size} (expected 4096)")
    else:
        print(f"✅ Page size: {page_size}")

    # Check 3: Number of pages
    num_pages = len(data) // page_size
    print(f"✅ Total pages: {num_pages}")

    # Check 4: First track page (page 1, since page 0 is file header)
    if num_pages > 1:
        page_offset = 1 * 4096

        # Parse page header
        page_magic, page_idx, page_type, next_pg = struct.unpack('<IIII', data[page_offset:page_offset + 16])
        trans, unk2, num_rows, unk3, unk4, flags, free, next_off = struct.unpack(
            '<IIBBBBHH', data[page_offset + 16:page_offset + 32])

        # Check page flags (first track page should be index page: 0x64)
        if flags != 0x64:
            issues.append(f"❌ Page flags: 0x{flags:02x} (expected 0x64 for index page)")
        else:
            print(f"✅ Page flags: 0x{flags:02x} (index page)")

        # Check 5: Track row unnamed30 (bytes 92-93 in each track row)
        # Track rows start after page header (48 bytes offset)
        # First track row at: page_offset + 48
        if num_rows > 0:
            track_row_offset = page_offset + 48
            # unnamed30 is at bytes 92-93 of track row
            unnamed30_offset = track_row_offset + 92

            if unnamed30_offset + 2 <= len(data):
                unnamed30 = struct.unpack('<H', data[unnamed30_offset:unnamed30_offset + 2])[0]
                if unnamed30 != 0x3:
                    issues.append(
                        f"❌ TrackRow unnamed30: 0x{unnamed30:04x} (expected 0x0003) - CRITICAL!")
                else:
                    print(f"✅ TrackRow unnamed30: 0x{unnamed30:04x}")

            # Check 6: Track row offset (bytes 0-1 of track row)
            row_offset = struct.unpack('<H', data[track_row_offset:track_row_offset + 2])[0]
            if row_offset != 0x24:
                issues.append(f"❌ TrackRow offset: 0x{row_offset:04x} (expected 0x0024)")
            else:
                print(f"✅ TrackRow offset: 0x{row_offset:04x}")

            # Check 7: Bitmask (bytes 4-7 of track row)
            bitmask = struct.unpack('<I', data[track_row_offset + 4:track_row_offset + 8])[0]
            if bitmask != 0xC0700:
                issues.append(f"❌ Bitmask: 0x{bitmask:06x} (expected 0x0C0700)")
            else:
                print(f"✅ Bitmask: 0x{bitmask:06x}")

    # Summary
    print("=" * 70)
    if issues:
        print("\n❌ CORRUPTION ISSUES FOUND:\n")
        for issue in issues:
            print(f"  {issue}")
        print("\n⚠️  This file may be REJECTED by rekordbox!")
        return False
    else:
        print("\n✅ No corruption issues found - file should be accepted by rekordbox")
        return True


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python tests/check_corruption.py <path_to_export.pdb>")
        sys.exit(1)

    pdb_path = Path(sys.argv[1])
    if not pdb_path.exists():
        print(f"❌ File not found: {pdb_path}")
        sys.exit(1)

    success = check_critical_fields(pdb_path)
    sys.exit(0 if success else 1)
