# BMAM Memory Archive: locomo_sample0_full_20251112_161320

**Format Version**: 2.0.0 (Multi-Region)
**Created**: 2025-11-12 08:13:20 UTC

## Description

LoCoMo Sample 0 - Full 419 turns with multi-region consolidation

## Brain Regions Included

- **Temporal Lobe**: 0 items (sqlite)
- **Hippocampus**: 2 items (json)
- **Prefrontal**: 10 items (json)
- **Amygdala**: N/A items (json)
- **Basal Ganglia**: 4 items (json)

## Tags

locomo, sample_0, full, v2.0.0, validated

## Usage

Load this archive into BMAM using:

```python
from src.coordination.brain_coordinator_refactored import BrainInspiredCoordinator

coordinator = BrainInspiredCoordinator()
await coordinator.initialize()

# Load archive
result = coordinator.load_memory_archive(
    archive_path=Path("path/to/this.bma"),
    validate=True
)
```

## Archive Structure

```
archive.bma/
├── manifest.json           # Archive metadata
├── brain_regions/          # Brain region states
│   ├── temporal_lobe.db   # Long-term memory (SQLite)
│   ├── hippocampus.json   # Short-term memory
│   ├── prefrontal.json    # Working memory
│   ├── amygdala.json      # Emotional memory
│   └── basal_ganglia.json # Procedural memory
├── vectors/                # FAISS vector indices
├── checksums.json         # File integrity hashes
└── README.md             # This file
```

---

*Generated with BMAM Memory Archive System v2.0.0*
