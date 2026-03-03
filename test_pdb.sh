#!/bin/bash
# Quick test script for PDB development
# Converts onelib_only and compares with onelib_and_devicelib reference

set -e

echo "🔄 Running PDB comparison test..."
echo ""

# Activate venv and run comparison
source .venv/bin/activate
python tests/test_pdb_comparison.py validation_data/onelib_only "$@"

echo ""
echo "✅ Test complete!"
