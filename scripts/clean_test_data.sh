#!/bin/bash
# Clean test data and corrupted buffers before running LoCoMo tests
# Usage: bash scripts/clean_test_data.sh

echo "🧹 Cleaning test data..."

# Clean agent buffers (can grow very large during long tests)
if [ -d "data/agent_buffers" ]; then
    echo "  Removing agent buffers..."
    rm -f data/agent_buffers/*.json
    echo "  ✓ Agent buffers cleaned"
fi

# Optional: Clean embedding cache (uncomment if needed)
# if [ -f "data/embedding_cache/embeddings.json" ]; then
#     echo "  Cleaning embedding cache..."
#     rm -f data/embedding_cache/embeddings.json
#     echo "  ✓ Embedding cache cleaned"
# fi

# Optional: Clean old test metrics (uncomment if needed)
# echo "  Cleaning old test metrics..."
# find metrics -name "*.json" -mtime +7 -delete
# echo "  ✓ Old metrics cleaned"

echo "✅ Test data cleaned successfully!"
echo ""
echo "You can now run LoCoMo tests:"
echo "  python3 tests/test_locomo_bmam_full.py --samples 1 --questions 5 --verbose"
