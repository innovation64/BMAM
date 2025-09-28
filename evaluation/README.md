# BMAM Evaluation System

Comprehensive evaluation framework for the Brain-inspired Memory and Attention Model (BMAM).

## Overview

This evaluation system provides multiple specialized modules to test different aspects of the BMAM system:

- **Framework Evaluation**: General system tests and integration tests
- **Memory Evaluation**: Memory storage, retrieval, consolidation, and forgetting
- **Agent Evaluation**: Agent coordination, performance, and error recovery
- **Persona Evaluation**: Personality consistency and emotional appropriateness

## Quick Start

### Run Complete Evaluation
```bash
python run_evaluation.py
```

### Run Specific Modules
```bash
# Memory only
python run_evaluation.py --modules memory

# Multiple modules
python run_evaluation.py --modules memory agent persona

# With verbose output
python run_evaluation.py --verbose
```

### Run Individual Modules
```bash
# Framework evaluation
python evaluation/evaluation_framework.py

# Memory evaluation
python evaluation/memory_evaluation.py

# Agent evaluation
python evaluation/agent_evaluation.py

# Persona evaluation
python evaluation/persona_evaluation.py
```

## Evaluation Modules

### 1. Framework Evaluation (`evaluation_framework.py`)

Core system evaluation with predefined test cases:

**Test Categories:**
- Memory operations (store, retrieve, consolidate)
- Persona consistency tests
- Agent coordination scenarios
- Conversation context tests
- Stress and performance tests

**Metrics:**
- Response time
- Memory retrieval accuracy
- Context relevance
- Task completion rate
- Overall system stability

### 2. Memory Evaluation (`memory_evaluation.py`)

Specialized memory system testing:

**Tests:**
- Storage performance (speed, success rate)
- Retrieval accuracy and relevance
- Memory consolidation effectiveness
- Forgetting curve implementation
- Association strength analysis

**Metrics:**
- Storage/retrieval success rates
- Average response times
- Memory reduction ratios
- Association strengths
- Overall memory score

### 3. Agent Evaluation (`agent_evaluation.py`)

Multi-agent system performance:

**Tests:**
- Individual agent response times
- Multi-agent coordination
- Resource usage analysis
- Error recovery capabilities
- Load handling under stress

**Metrics:**
- Coordination success rate
- Error recovery rate
- Throughput under load
- Resource efficiency
- Agent participation tracking

### 4. Persona Evaluation (`persona_evaluation.py`)

Personality and character consistency:

**Tests:**
- Personality trait consistency
- Emotional response appropriateness
- Character coherence over time
- Context awareness and adaptation

**Metrics:**
- Personality consistency scores
- Emotional appropriateness rate
- Character drift measurement
- Context retention rate

## Results and Reporting

### Output Files

All results are saved to `results/evaluation/`:

- `comprehensive_evaluation_YYYYMMDD_HHMMSS.json` - Complete results
- `evaluation_summary_YYYYMMDD_HHMMSS.json` - Summary metrics
- `latest_comprehensive_evaluation.json` - Latest results (symlink)

Individual module results:
- `memory_evaluation.json`
- `agent_evaluation.json`
- `persona_evaluation.json`

### Report Format

Each evaluation generates:
1. **Console Report**: Human-readable summary printed to terminal
2. **JSON Results**: Detailed machine-readable results
3. **Summary Metrics**: Key performance indicators

Example console output:
```
==================================================
BMAM COMPREHENSIVE EVALUATION REPORT
==================================================
Overall System Score: 87.5%
Total Tests: 45
Passed: 39
Failed: 6

MODULE SCORES
----------------------------------------
Framework: 85.2%
Memory: 91.3%
Agent: 83.7%
Persona: 89.8%
```

## Configuration

### Custom Test Cases

Create custom test cases by modifying the test generation methods in each evaluator:

```python
# In evaluation_framework.py
def _generate_default_test_cases(self):
    # Add your custom test cases here
    pass
```

### Output Directory

Specify custom output directory:
```bash
python run_evaluation.py --output /path/to/results
```

### Logging

Enable verbose logging:
```bash
python run_evaluation.py --verbose
```

## Integration with CI/CD

### Automated Testing

Add to your CI pipeline:

```yaml
# .github/workflows/evaluation.yml
name: BMAM Evaluation
on: [push, pull_request]
jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run evaluation
        run: python run_evaluation.py
```

### Performance Monitoring

Set up regular evaluation runs to monitor system performance over time:

```bash
# Daily evaluation cron job
0 2 * * * cd /path/to/bmam && python run_evaluation.py
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure BMAM is properly installed and in Python path
2. **Memory Issues**: Reduce test data size for systems with limited RAM
3. **Timeout Errors**: Increase timeout values in test configurations
4. **Permission Errors**: Ensure write access to results directory

### Mock Mode

If BMAM system fails to initialize, evaluations run in mock mode with simulated results for testing the evaluation framework itself.

### Debug Mode

Enable debug logging for detailed execution information:

```python
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

## Extending the Evaluation System

### Adding New Test Categories

1. Create test cases in the appropriate evaluator
2. Implement test execution logic
3. Add result analysis and metrics
4. Update report generation

### Custom Evaluators

Create new evaluation modules following the pattern:

```python
class CustomEvaluator:
    def __init__(self):
        pass

    async def run_comprehensive_evaluation(self, coordinator):
        # Your evaluation logic
        return results

    def generate_report(self, results):
        # Generate human-readable report
        return report_string
```

### Integration with External Tools

The evaluation system can be extended to integrate with:
- Performance monitoring tools (Grafana, DataDog)
- Test management systems (TestRail, Zephyr)
- Continuous integration platforms
- Machine learning experiment tracking (MLflow, Weights & Biases)

## Performance Considerations

- Memory evaluations may take longer for large datasets
- Agent evaluations scale with the number of concurrent requests
- Use `--modules` to run only necessary evaluations
- Consider running evaluations on dedicated hardware for consistent results

## Contributing

When adding new evaluation capabilities:

1. Follow the existing module structure
2. Include comprehensive docstrings
3. Add appropriate error handling
4. Update this README with new features
5. Add example usage and expected output