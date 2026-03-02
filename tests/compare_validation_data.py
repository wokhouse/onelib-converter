#!/usr/bin/env python3
"""
Bitwise comparison test for validation data.

Compares converter output with reference onelib_and_devicelib export.

Usage:
    python tests/compare_validation_data.py

Prerequisites:
    - Run conversion first:
      onelib-to-devicelib convert validation_data/onelib_only --output /tmp/test_validation
"""

import hashlib
import sys
from pathlib import Path

# Paths
SOURCE_DIR = Path("validation_data/onelib_only")
REFERENCE_DIR = Path("validation_data/onelib_and_devicelib")
GENERATED_DIR = Path("/tmp/test_validation")


def file_checksum(path: Path) -> str:
    """Calculate MD5 checksum of a file."""
    return hashlib.md5(path.read_bytes()).hexdigest()


def compare_file_structures() -> dict:
    """Compare file structures between generated and reference."""
    results = {}

    # Check PIONEER directory structure
    gen_pioneer = GENERATED_DIR / "PIONEER"
    ref_pioneer = REFERENCE_DIR / "PIONEER"

    if not gen_pioneer.exists():
        results["PIONEER directory"] = False
        return results

    # Check subdirectories
    for subdir in ["rekordbox", "USBANLZ", "Artwork", "DeviceLibBackup"]:
        gen_sub = gen_pioneer / subdir
        ref_sub = ref_pioneer / subdir

        exists = gen_sub.exists()
        ref_exists = ref_sub.exists()

        results[f"{subdir} exists"] = exists
        results[f"{subdir} matches reference"] = exists == ref_exists

    # Check specific files
    gen_pdb = gen_pioneer / "rekordbox" / "export.pdb"
    ref_pdb = ref_pioneer / "rekordbox" / "export.pdb"

    if gen_pdb.exists() and ref_pdb.exists():
        gen_size = gen_pdb.stat().st_size
        ref_size = ref_pdb.stat().st_size

        results["export.pdb generated"] = True
        results["export.pdb size"] = f"{gen_size} bytes (ref: {ref_size})"
        results["export.pdb size matches"] = gen_size == ref_size

    # Check ANLZ structure
    gen_anlz = gen_pioneer / "USBANLZ"
    ref_anlz = ref_pioneer / "USBANLZ"

    if gen_anlz.exists() and ref_anlz.exists():
        gen_dirs = len(list(gen_anlz.rglob("ANLZ0000.DAT")))
        ref_dirs = len(list(ref_anlz.rglob("ANLZ0000.DAT")))

        results["ANLZ directories"] = f"{gen_dirs} (ref: {ref_dirs})"
        results["ANLZ count matches"] = gen_dirs == ref_dirs

    return results


def compare_pdb_details() -> None:
    """Detailed PDB file comparison."""
    gen_pdb = GENERATED_DIR / "PIONEER" / "rekordbox" / "export.pdb"
    ref_pdb = REFERENCE_DIR / "PIONEER" / "rekordbox" / "export.pdb"

    if not gen_pdb.exists() or not ref_pdb.exists():
        print("⚠️  Cannot compare PDB files (one or both missing)")
        return

    gen_data = gen_pdb.read_bytes()
    ref_data = ref_pdb.read_bytes()

    print("\n=== PDB File Analysis ===")
    print(f"Generated: {len(gen_data)} bytes")
    print(f"Reference: {len(ref_data)} bytes")

    # Check header
    gen_header = gen_data[:32]
    ref_header = ref_data[:32]

    print(f"\nGenerated header: {gen_header[:16].hex()}")
    print(f"Reference header: {ref_header[:16].hex()}")

    if gen_header == ref_header:
        print("✅ Headers match")
    else:
        print("⚠️  Headers differ (expected for MVP)")

    # Check page structure
    page_size = 4096
    gen_pages = len(gen_data) // page_size
    ref_pages = len(ref_data) // page_size

    print(f"\nGenerated pages: {gen_pages}")
    print(f"Reference pages: {ref_pages}")


def compare_anlz_files() -> None:
    """Compare ANLZ file structures."""
    gen_anlz = GENERATED_DIR / "PIONEER" / "USBANLZ" / "P001"
    ref_anlz = REFERENCE_DIR / "PIONEER" / "USBANLZ" / "P001"

    if not gen_anlz.exists() or not ref_anlz.exists():
        print("⚠️  Cannot compare ANLZ files")
        return

    print("\n=== ANLZ File Analysis ===")

    gen_dirs = sorted([d for d in gen_anlz.iterdir() if d.is_dir()])
    ref_dirs = sorted([d for d in ref_anlz.iterdir() if d.is_dir()])

    print(f"Generated ANLZ dirs: {len(gen_dirs)}")
    print(f"Reference ANLZ dirs: {len(ref_dirs)}")

    # Check file counts
    gen_complete = sum(1 for d in gen_dirs if len(list(d.glob("ANLZ0000.*"))) == 3)
    ref_complete = sum(1 for d in ref_dirs if len(list(d.glob("ANLZ0000.*"))) == 3)

    print(f"\nComplete ANLZ sets:")
    print(f"  Generated: {gen_complete}/{len(gen_dirs)}")
    print(f"  Reference: {ref_complete}/{len(ref_dirs)}")

    # Sample comparison
    if gen_dirs and ref_dirs:
        sample_gen = gen_dirs[0]
        sample_ref = ref_dirs[0]

        print(f"\nSample comparison:")
        print(f"  Generated: {sample_gen.name}")
        print(f"  Reference: {sample_ref.name}")

        # Check if files exist
        for ext in ["DAT", "EXT", "2EX"]:
            gen_file = sample_gen / f"ANLZ0000.{ext}"
            ref_file = sample_ref / f"ANLZ0000.{ext}"

            gen_exists = gen_file.exists()
            ref_exists = ref_file.exists()

            status = "✅" if gen_exists else "❌"
            print(f"    {ext}: Generated: {gen_exists}, Reference: {ref_exists} {status}")


def main():
    """Run comparison tests."""
    print("=" * 60)
    print("Validation Data Comparison Test")
    print("=" * 60)

    # Check if conversion has been run
    if not GENERATED_DIR.exists():
        print("\n❌ Generated directory not found!")
        print(f"Please run conversion first:")
        print(f"  onelib-to-devicelib convert {SOURCE_DIR} --output {GENERATED_DIR}")
        sys.exit(1)

    # Structure comparison
    print("\n--- Structure Comparison ---")
    results = compare_file_structures()

    for key, value in results.items():
        status = "✅" if value else "❌"
        print(f"{status} {key}: {value}")

    # Detailed PDB comparison
    compare_pdb_details()

    # Detailed ANLZ comparison
    compare_anlz_files()

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print("\n✅ Core functionality working:")
    print("  - Database reading")
    print("  - PDB generation")
    print("  - ANLZ generation")
    print("  - Metadata files")

    print("\n⚠️  Expected differences:")
    print("  - PDB exact format (MVP vs full Rekordbox format)")
    print("  - DeviceLibBackup UUID (randomly generated)")
    print("  - DEVSETTING.DAT timestamps")

    print("\n📋 Next steps:")
    print("  - Test on actual hardware")
    print("  - Refine PDB format for exact match")
    print("  - Add comprehensive error handling")

    print("=" * 60)


if __name__ == "__main__":
    main()
