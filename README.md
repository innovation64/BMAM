# MA-CMM Clean Version

Multi-Agent Collaborative Conditional Memory Management Framework - Optimized and Restructured

## Project Structure

```
MA-CMM-Clean/ (1.2MB - Highly Optimized)
├── src/                    # Core source code (784KB)
│   ├── agents/            # Multi-agent implementations
│   ├── memory/            # Hierarchical memory management
│   ├── algorithms/        # Core algorithms
│   ├── utils/             # Utility functions
│   ├── core/              # Framework core (including improved ma_cmm_framework.py)
│   └── optimized_answer_extraction_v8.py
├── experiments/           # Evaluation scripts (140KB)
│   ├── v8_complete_locomo_evaluation.py
│   ├── ablation_study.py
│   ├── sota_comparison.py
│   ├── optimized_test.py  # Final optimized test from revisions
│   └── locomo_main_experiment.py  # Main experiment runner
├── config/                # Configuration files
├── data/                  # Minimal sample data
├── scripts/               # Setup and run scripts
├── main.py               # Unified entry point
├── run_main_evaluation.py # Direct evaluation
├── gradio_demo.py        # Interactive demo
└── requirements.txt      # Dependencies
```

## Quick Start

### 1. Setup Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up API keys
export OPENAI_API_KEY="your-api-key-here"
```

### 2. Run Evaluation

```bash
# Run main evaluation
python run_main_evaluation.py

# Run interactive demo
python gradio_demo.py
```

### 3. Run Experiments

```bash
# Run ablation study
python experiments/ablation_study.py

# Run baseline comparison
python experiments/sota_comparison.py

# Run complete LOCOMO evaluation
python experiments/v8_complete_locomo_evaluation.py
```

## Key Components

### Core Framework
- `src/core/advanced_ma_cmm.py` - Advanced multi-agent framework
- `src/core/dma_cmm_system.py` - Distributed memory management
- `src/optimized_answer_extraction_v8.py` - V8 optimized implementation

### Agents
- Condition Extractor - Extracts conditional statements
- Memory Manager - Manages hierarchical memory
- Retriever - Multi-path retrieval system
- Generator - Response generation
- Conflict Resolver - Handles contradictions

### Memory Architecture
- Working Memory (20 items)
- Short-term Memory (100 items)
- Long-term Memory (1000 items)
- Episodic Memory (500 items)

## Configuration

Edit `config/config.yaml` to customize:
- API settings
- Model parameters
- Memory capacities
- Retrieval thresholds

## Notes

This is a cleaned version of the MA-CMM project with:
- Only essential files preserved
- Removed duplicate and temporary files
- Organized structure for better maintainability
- Preserved experiment_revise from .trees directory

## License

MIT License