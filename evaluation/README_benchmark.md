# BMAM vs MemOS Benchmark Comparison

Comprehensive benchmark comparison framework between BMAM and the MemOS baseline system.

## Overview

This framework provides standardized benchmark comparisons using the same datasets and metrics that MemOS uses for evaluation, ensuring fair and comparable results.

### Supported Benchmarks

1. **LongMemEval** - Long-term memory evaluation
2. **LoCoMo** - Long Context Memory benchmark
3. **Needle in Haystack** - Information retrieval in long contexts
4. **MemoryBank** - Comprehensive memory evaluation

## Quick Start

### Setup Datasets
```bash
# Download and prepare all benchmark datasets
python run_benchmark_comparison.py --mode setup
```

### Run Quick Comparison
```bash
# Run core benchmarks (LongMemEval + LoCoMo)
python run_benchmark_comparison.py --mode quick
```

### Run Full Comparison
```bash
# Run all benchmarks including custom ones
python run_benchmark_comparison.py --mode full
```

### List Available Benchmarks
```bash
python run_benchmark_comparison.py --mode list
```

## Detailed Usage

### Specify MemOS Path
```bash
python run_benchmark_comparison.py --memos-path /path/to/MemOS --mode quick
```

### Run Specific Benchmarks
```bash
python run_benchmark_comparison.py --benchmarks longmemeval locomo
```

### Custom Output Directory
```bash
python run_benchmark_comparison.py --output-dir /path/to/results --mode full
```

### Force Dataset Refresh
```bash
python run_benchmark_comparison.py --mode setup --force-refresh
```

## Benchmark Details

### LongMemEval
- **Purpose**: Evaluate long-term memory retention and retrieval
- **Metrics**: LLM judge score, F1, ROUGE, BLEU scores
- **Categories**: Reasoning, factual, conversational
- **MemOS Baseline**: Uses standard LongMemEval evaluation pipeline

### LoCoMo (Long Context Memory)
- **Purpose**: Test memory performance across different reasoning types
- **Categories**:
  - Single-hop: Direct information retrieval
  - Multi-hop: Reasoning across multiple pieces of information
  - Temporal reasoning: Time-based logical inference
  - Open domain: General knowledge questions
- **Metrics**: Accuracy, response time, LLM judge scores
- **MemOS Baseline**: Standard LoCoMo evaluation methodology

### Needle in Haystack
- **Purpose**: Information retrieval in very long contexts
- **Categories**: Short (1K), Medium (5K), Long (15K), Very Long (50K) contexts
- **Metrics**: Retrieval accuracy, position independence
- **Custom Implementation**: Generated test cases for systematic evaluation

### MemoryBank
- **Purpose**: Comprehensive memory type evaluation
- **Categories**: Episodic, semantic, procedural memory
- **Metrics**: Retention rate, accuracy, retrieval speed
- **Custom Implementation**: Synthetic test cases covering different memory types

## Results and Reports

### Output Files

All results saved to `results/benchmark_comparison/`:

- `comprehensive_benchmark_comparison_YYYYMMDD_HHMMSS.json` - Complete results
- `benchmark_summary_YYYYMMDD_HHMMSS.txt` - Human-readable summary
- `latest_comprehensive_comparison.json` - Latest results
- Individual benchmark reports (per benchmark)

### Report Structure

Each comparison includes:

1. **Overall Metrics**: Win/loss counts, improvement percentages
2. **Benchmark-Specific Results**: Detailed performance per benchmark
3. **Category Analysis**: Performance breakdown by test categories
4. **Key Findings**: Automated insights and recommendations

### Example Output

```
==================================================
BMAM vs MemOS COMPREHENSIVE BENCHMARK COMPARISON
==================================================

OVERALL SUMMARY:
Successful Comparisons: 4/4
BMAM Wins: 15
MemOS Wins: 8
Average Improvement: +12.3%

BENCHMARK PERFORMANCE:
longmemeval          | BMAM   | +15.2%
locomo              | BMAM   |  +8.4%
needle_in_haystack  | BMAM   | +18.7%
memorybank          | MemOS  |  -3.1%

KEY FINDINGS:
• BMAM outperforms MemOS overall (15 vs 8 metric wins)
• BMAM shows significant performance improvements
• BMAM performs best on needle_in_haystack (+18.7%)
• BMAM needs improvement on memorybank (-3.1%)
```

## Architecture

### Comparison Framework (`benchmark_comparison.py`)
- Coordinates evaluation runs for both systems
- Implements metric calculation and comparison logic
- Generates standardized reports

### Dataset Management (`benchmark_datasets.py`)
- Downloads and caches benchmark datasets
- Provides unified data loading interface
- Generates synthetic test data when needed

### Evaluation Integration
- Integrates with existing BMAM evaluation system
- Loads MemOS baseline results from standard locations
- Ensures comparable evaluation conditions

## Metrics and Scoring

### Standard Metrics (from MemOS)
- **LLM Judge Score**: GPT-based quality assessment
- **Lexical Metrics**: F1, ROUGE-1/2/L, BLEU-1/2/3/4
- **Semantic Metrics**: Embedding-based similarity
- **Performance Metrics**: Response time, throughput

### BMAM-Specific Metrics
- **Memory Utilization**: Effectiveness of retrieved context
- **Agent Coordination**: Multi-agent task success rate
- **Personality Consistency**: Persona coherence scores
- **Context Retention**: Long-term context maintenance

### Comparison Methodology
- **Direct Comparison**: Same datasets, same metrics
- **Improvement Calculation**: (BMAM - MemOS) / MemOS × 100%
- **Statistical Significance**: Multiple runs with variance analysis
- **Category-wise Analysis**: Performance breakdown by test type

## Configuration

### Dataset Sources
- LongMemEval: Based on standard evaluation protocol
- LoCoMo: Uses official benchmark structure
- Custom datasets: Generated with controlled parameters
- Baseline results: Loaded from MemOS evaluation outputs

### Evaluation Parameters
- Consistent timeout values across systems
- Standardized input preprocessing
- Unified output format normalization
- Fair resource allocation

## Extending the Framework

### Adding New Benchmarks

1. **Define Dataset Structure**:
```python
"new_benchmark": {
    "name": "New Benchmark",
    "description": "Description of benchmark",
    "url": "https://dataset-url.com",
    "data_files": ["test_data.json"],
    "categories": ["cat1", "cat2"]
}
```

2. **Implement Evaluation Logic**:
```python
async def _run_bmam_new_benchmark(self, coordinator):
    # Implement BMAM evaluation for new benchmark
    pass

def _load_memos_new_benchmark(self):
    # Load MemOS baseline results
    pass
```

3. **Add Comparison Metrics**:
```python
def _compare_new_benchmark_metrics(self, bmam, memos):
    # Define comparison logic
    pass
```

### Custom Metrics

Add domain-specific metrics by extending the comparison framework:

```python
def calculate_custom_metric(self, responses, ground_truth):
    # Implement custom evaluation metric
    return score
```

## Troubleshooting

### Common Issues

1. **Dataset Download Failures**
   - Check internet connection
   - Verify dataset URLs are accessible
   - Use `--force-refresh` to re-download

2. **MemOS Baseline Missing**
   - Ensure MemOS path is correct
   - Check if MemOS evaluation results exist
   - Framework will use mock baselines if unavailable

3. **BMAM Evaluation Errors**
   - Verify BMAM system initializes correctly
   - Check for import/dependency issues
   - Review BMAM configuration

4. **Memory Issues**
   - Reduce dataset size for testing
   - Monitor system resources during evaluation
   - Use smaller batch sizes for large benchmarks

### Debug Mode

Enable verbose logging for detailed execution information:

```bash
python run_benchmark_comparison.py --verbose --mode quick
```

## Performance Considerations

- **Dataset Caching**: Datasets cached locally after first download
- **Parallel Evaluation**: Multiple benchmarks can run concurrently
- **Resource Management**: Memory usage monitored during evaluation
- **Result Persistence**: All results saved for future reference

## Contributing

When adding new benchmarks or metrics:

1. Follow existing code patterns and documentation
2. Include test cases for new functionality
3. Update this README with new features
4. Ensure backward compatibility with existing results
5. Add appropriate error handling and logging

## Citation

If using this comparison framework in research:

```bibtex
@misc{bmam_benchmark_comparison,
  title={BMAM vs MemOS Benchmark Comparison Framework},
  year={2024},
  url={https://github.com/your-repo/bmam-evaluation}
}
```