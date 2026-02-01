#!/bin/bash
# Example: Run a SWMM simulation from GitHub benchmarks

# Set your API token (or use: python ../wrapi.py config --token YOUR_TOKEN)
# export WRAPI_TOKEN="your-token-here"

# Navigate to project root
cd "$(dirname "$0")/.."

echo "=== Running SWMM Benchmark Example ==="

# Run a simple SWMM model from GitHub (no external dependencies)
python wrapi.py run \
    "https://raw.githubusercontent.com/SWMMEnablement/1729-SWMM5-Models/main/Hydraulics/10000FootSurchargeDepth.inp" \
    --type swmm \
    --label "SWMM Benchmark - 10000FootSurchargeDepth" \
    --wait \
    --show-files

echo ""
echo "=== Done! ==="
