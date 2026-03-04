#!/bin/bash
# Master test runner for PDB comparison
# Runs all comparison phases in sequence

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "PDB Bitwise Comparison Test Suite"
echo "========================================"

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo -e "${YELLOW}Warning: Virtual environment not activated${NC}"
    echo "Run: source .venv/bin/activate"
fi

# Paths
REFERENCE_PDB="validation_data/onelib_and_devicelib/PIONEER/rekordbox/export.pdb"
GENERATED_DIR="/tmp/pdb_comparison_test"

# Check if reference exists
if [[ ! -f "$REFERENCE_PDB" ]]; then
    echo -e "${RED}Error: Reference PDB not found: $REFERENCE_PDB${NC}"
    exit 1
fi

# Phase 0: Generate fresh PDB
echo ""
echo "========================================"
echo "Phase 0: Generating fresh PDB"
echo "========================================"

# Clean previous output
rm -rf "$GENERATED_DIR"

# Generate new PDB
onelib-to-devicelib convert \
    validation_data/onelib_only \
    --output "$GENERATED_DIR" \
    --no-copy

GENERATED_PDB="$GENERATED_DIR/PIONEER/rekordbox/export.pdb"

if [[ ! -f "$GENERATED_PDB" ]]; then
    echo -e "${RED}Error: Generated PDB not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ PDB generated successfully${NC}"

# Phase 1: Corruption Check
echo ""
echo "========================================"
echo "Phase 1: Critical Corruption Check"
echo "========================================"

python tests/check_corruption.py "$GENERATED_PDB"
GEN_CORRUPTION=$?

python tests/check_corruption.py "$REFERENCE_PDB"
REF_CORRUPTION=$?

if [[ $GEN_CORRUPTION -eq 0 ]]; then
    echo -e "${GREEN}✓ Generated file passes corruption check${NC}"
else
    echo -e "${RED}✗ Generated file has corruption issues${NC}"
fi

# Phase 2: File-Level Comparison
echo ""
echo "========================================"
echo "Phase 2: File-Level Structure Comparison"
echo "========================================"

python tests/compare_pdb_structure.py "$REFERENCE_PDB" "$GENERATED_PDB"

# Phase 3: Page-Level Comparison
echo ""
echo "========================================"
echo "Phase 3: Page-Level Comparison"
echo "========================================"

python tests/compare_pdb_pages.py "$REFERENCE_PDB" "$GENERATED_PDB"

# Phase 4: Track Row Comparison
echo ""
echo "========================================"
echo "Phase 4: Track Row Field Comparison"
echo "========================================"

python tests/compare_pdb_tracks.py "$REFERENCE_PDB" "$GENERATED_PDB" 5

# Summary
echo ""
echo "========================================"
echo "Test Suite Complete"
echo "========================================"
echo ""
echo "Generated PDB: $GENERATED_PDB"
echo "Reference PDB: $REFERENCE_PDB"
echo ""
echo "To run individual phases:"
echo "  python tests/check_corruption.py <pdb>"
echo "  python tests/compare_pdb_structure.py <ref> <gen>"
echo "  python tests/compare_pdb_pages.py <ref> <gen>"
echo "  python tests/compare_pdb_tracks.py <ref> <gen> [count]"
