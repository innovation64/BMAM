# Contributing to BMAM

Thank you for your interest in contributing to the Brain-inspired Multi-Agent Memory Framework (BMAM)!

## Development Setup

### Prerequisites

- Python 3.10+
- OpenAI API key

### Installation

```bash
# Clone the repository
git clone https://github.com/brain-inspired-ai/bmam.git
cd bmam

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Set up environment
cp .env.example .env
# Edit .env with your OpenAI API key
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_hippocampus.py

# Run with coverage
pytest --cov=src
```

## Code Style

- Use `black` for code formatting
- Use `isort` for import sorting
- Use type hints for function signatures
- Follow PEP 8 guidelines

```bash
# Format code
black src tests
isort src tests

# Type checking
mypy src
```

## Project Structure

```
BMAM/
├── src/
│   ├── agents/           # Brain region agents
│   │   └── brain_regions/
│   │       ├── hippocampus_agent/  # Episodic memory
│   │       ├── amygdala_agent.py   # Emotional processing
│   │       ├── prefrontal_agent/   # Working memory
│   │       └── ...
│   ├── coordination/     # Multi-agent coordination
│   ├── memory/           # Memory systems
│   ├── services/         # External services (OpenAI, etc.)
│   └── utils/            # Utilities
├── tests/                # Test files
├── experiments/          # Benchmark experiments
├── scripts/              # Utility scripts
└── data/                 # Runtime data (not in git)
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Format code (`black . && isort .`)
6. Commit changes (`git commit -m 'Add amazing feature'`)
7. Push to branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## Commit Message Guidelines

Use clear, descriptive commit messages:

- `feat: Add new memory consolidation strategy`
- `fix: Resolve race condition in background processes`
- `docs: Update API documentation`
- `test: Add tests for temporal reasoning`
- `refactor: Simplify hippocampus storage logic`

## Reporting Issues

When reporting issues, please include:

1. Python version
2. OS and version
3. Steps to reproduce
4. Expected vs actual behavior
5. Relevant logs or error messages

## Questions?

Feel free to open an issue for questions or discussions.
