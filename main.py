#!/usr/bin/env python3
"""
MA-CMM Main Entry Point
Unified interface for running experiments and demos
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def main():
    parser = argparse.ArgumentParser(description='MA-CMM Framework')
    parser.add_argument(
        'mode',
        choices=['evaluate', 'demo', 'ablation', 'comparison', 'test'],
        help='Execution mode'
    )
    parser.add_argument(
        '--config',
        default='config/config.yaml',
        help='Configuration file path'
    )
    parser.add_argument(
        '--dataset',
        default='locomo',
        choices=['locomo', 'memorybank', 'custom'],
        help='Dataset to use'
    )
    parser.add_argument(
        '--samples',
        type=int,
        default=100,
        help='Number of samples to evaluate'
    )
    parser.add_argument(
        '--output',
        default='results/',
        help='Output directory for results'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'evaluate':
        # Run main evaluation
        from run_main_evaluation import run_evaluation
        run_evaluation(args.config, args.dataset, args.samples, args.output)
        
    elif args.mode == 'demo':
        # Launch interactive demo
        import gradio_demo
        gradio_demo.launch_demo()
        
    elif args.mode == 'ablation':
        # Run ablation study
        from experiments.ablation_study import run_ablation
        run_ablation(args.config, args.output)
        
    elif args.mode == 'comparison':
        # Run baseline comparison
        from experiments.sota_comparison import run_comparison
        run_comparison(args.config, args.dataset, args.samples, args.output)
        
    elif args.mode == 'test':
        # Run optimized test
        from experiments.optimized_test import final_optimized_test
        import asyncio
        asyncio.run(final_optimized_test())
    
    else:
        print(f"Unknown mode: {args.mode}")
        sys.exit(1)


if __name__ == "__main__":
    main()