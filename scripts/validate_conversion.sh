#!/bin/bash

# Validation script for PDB conversion
# Compares generated PDB with reference PDB

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "PDB Conversion Validation Script"
echo "========================================="
echo ""

# Check if validation data exists
if [ ! -d "validation_data/onelib_only" ]; then
    echo -e "${RED}Error: validation_data/onelib_only not found${NC}"
    echo "Please run this script from the project root directory"
    exit 1
fi

# Output directory
OUTPUT_DIR="/tmp/test_pdb_conversion_$(date +%s)"

# Step 1: Convert onelib_only
echo -e "${YELLOW}Step 1: Converting onelib_only...${NC}"
onelib-to-devicelib convert validation_data/onelib_only \
    --output "$OUTPUT_DIR" \
    --pdb-version v3 \
    --no-copy

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Conversion successful${NC}"
else
    echo -e "${RED}✗ Conversion failed${NC}"
    exit 1
fi

echo ""

# Step 2: Check if reference PDB exists
REFERENCE_PDB="validation_data/onelib_and_devicelib/PIONEER/rekordbox/export.pdb"
GENERATED_PDB="$OUTPUT_DIR/PIONEER/rekordbox/export.pdb"

if [ ! -f "$REFERENCE_PDB" ]; then
    echo -e "${YELLOW}Warning: Reference PDB not found at $REFERENCE_PDB${NC}"
    echo "Skipping comparison..."
    echo ""
    echo -e "${GREEN}Generated PDB: $GENERATED_PDB${NC}"
    echo "File size: $(stat -f%z "$GENERATED_PDB" 2>/dev/null || stat -c%s "$GENERATED_PDB") bytes"
    exit 0
fi

# Step 3: Compare file sizes
echo -e "${YELLOW}Step 2: Comparing file sizes...${NC}"

if command -v stat &> /dev/null; then
    # macOS uses different stat syntax
    if [[ "$(uname)" == "Darwin" ]]; then
        REF_SIZE=$(stat -f%z "$REFERENCE_PDB")
        GEN_SIZE=$(stat -f%z "$GENERATED_PDB")
    else
        REF_SIZE=$(stat -c%s "$REFERENCE_PDB")
        GEN_SIZE=$(stat -c%s "$GENERATED_PDB")
    fi

    echo "Reference: $(numfmt --to=iec-i --suffix=B $REF_SIZE 2>/dev/null || echo ${REF_SIZE} bytes)"
    echo "Generated: $(numfmt --to=iec-i --suffix=B $GEN_SIZE 2>/dev/null || echo ${GEN_SIZE} bytes)"

    # Calculate percentage
    if [ "$REF_SIZE" -gt 0 ]; then
        PERCENT=$((GEN_SIZE * 100 / REF_SIZE))
        echo "Size ratio: ${PERCENT}%"
    fi
else
    echo "stat command not available, skipping size comparison"
fi

echo ""

# Step 4: Run PDB comparison
echo -e "${YELLOW}Step 3: Running detailed PDB comparison...${NC}"
python3 -m tests.comparators.pdb_comparator "$GENERATED_PDB" "$REFERENCE_PDB"

echo ""

# Step 5: Summary
echo "========================================="
echo "Validation Summary"
echo "========================================="
echo ""
echo "Output directory: $OUTPUT_DIR"
echo ""
echo -e "${GREEN}To inspect the generated files:${NC}"
echo "  ls -la $OUTPUT_DIR/PIONEER/rekordbox/"
echo ""
echo -e "${GREEN}To run pytest tests:${NC}"
echo "  pytest tests/test_pdb_validation.py -v"
echo ""
