#!/usr/bin/env python3
"""
Auto-generate English docstrings for Python files.
Replaces empty docstrings with meaningful descriptions based on naming conventions.
"""
import os
import re
import ast
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Mapping of common terms to descriptions
TERM_MAPPINGS = {
    # Brain regions
    'hippocampus': 'episodic memory storage and retrieval',
    'prefrontal': 'executive control and decision making',
    'amygdala': 'emotional processing and tagging',
    'temporal_lobe': 'semantic knowledge and concept graphs',
    'basal_ganglia': 'habit formation and procedural memory',
    'thalamus': 'attention gating and information routing',
    'anterior_cingulate': 'conflict detection and error monitoring',

    # Memory operations
    'consolidation': 'memory consolidation from short-term to long-term',
    'retrieval': 'memory retrieval and search',
    'storage': 'memory storage operations',
    'forgetting': 'memory decay and forgetting mechanisms',
    'encoding': 'perception and memory encoding',

    # Core concepts
    'agent': 'autonomous processing agent',
    'coordinator': 'multi-agent coordination',
    'memory': 'memory management',
    'reasoning': 'reasoning and inference',
    'reflection': 'self-reflection and meta-cognition',
    'stress': 'stress response handling',
    'emotion': 'emotional processing',
    'personality': 'personality modeling',
    'distortion': 'memory distortion detection',

    # Actions
    'process': 'Process',
    'handle': 'Handle',
    'get': 'Get',
    'set': 'Set',
    'create': 'Create',
    'update': 'Update',
    'delete': 'Delete',
    'search': 'Search for',
    'retrieve': 'Retrieve',
    'store': 'Store',
    'encode': 'Encode',
    'decode': 'Decode',
    'validate': 'Validate',
    'analyze': 'Analyze',
    'extract': 'Extract',
    'compute': 'Compute',
    'calculate': 'Calculate',
    'initialize': 'Initialize',
    'init': 'Initialize',
    'load': 'Load',
    'save': 'Save',
    'build': 'Build',
    'parse': 'Parse',
    'format': 'Format',
    'convert': 'Convert',
    'merge': 'Merge',
    'split': 'Split',
    'filter': 'Filter',
    'sort': 'Sort',
    'rank': 'Rank',
    'score': 'Score',
}

def camel_to_words(name: str) -> str:
    """Convert CamelCase to words."""
    words = re.sub('([A-Z])', r' \1', name).strip()
    return words.lower()

def snake_to_words(name: str) -> str:
    """Convert snake_case to words."""
    return name.replace('_', ' ').lower()

def generate_class_docstring(class_name: str, base_classes: List[str] = None) -> str:
    """Generate docstring for a class."""
    words = camel_to_words(class_name)

    # Check for known terms
    for term, desc in TERM_MAPPINGS.items():
        if term in words.lower():
            if 'agent' in words.lower():
                return f'Brain-inspired agent for {desc}.'
            elif 'manager' in words.lower():
                return f'Manager for {desc}.'
            elif 'handler' in words.lower():
                return f'Handler for {desc}.'
            elif 'config' in words.lower():
                return f'Configuration for {desc}.'
            else:
                return f'{words.title()} - {desc}.'

    # Check base classes
    if base_classes:
        if 'BrainAgent' in base_classes:
            return f'Brain region agent implementing {words}.'
        if 'BaseModel' in base_classes or 'dataclass' in str(base_classes):
            return f'Data model for {words}.'

    # Default
    if 'agent' in words:
        return f'Agent for {words.replace("agent", "").strip()} operations.'
    elif 'manager' in words:
        return f'Manager handling {words.replace("manager", "").strip()}.'
    elif 'config' in words:
        return f'Configuration settings for {words.replace("config", "").strip()}.'
    elif 'result' in words or 'response' in words:
        return f'Data container for {words}.'
    else:
        return f'{words.title().strip()}.'

def generate_function_docstring(func_name: str, args: List[str], is_async: bool = False) -> str:
    """Generate docstring for a function."""
    words = snake_to_words(func_name)

    # Handle special prefixes
    prefix = ""
    action = words.split()[0] if words.split() else ""

    if action in TERM_MAPPINGS:
        prefix = TERM_MAPPINGS[action]
        remainder = ' '.join(words.split()[1:])
        if remainder:
            desc = f'{prefix} {remainder}.'
        else:
            desc = f'{prefix} operation.'
    else:
        desc = f'{words.title().replace("_", " ")}.'

    # Add async note
    if is_async:
        desc = desc.rstrip('.') + ' (async).'

    # Add args info if present
    if args and len(args) > 1:  # More than just self
        meaningful_args = [a for a in args if a not in ('self', 'cls')]
        if meaningful_args:
            args_str = ', '.join(meaningful_args[:3])
            if len(meaningful_args) > 3:
                args_str += ', ...'
            desc = desc.rstrip('.') + f'\n\n        Args:\n            {args_str}: Input parameters.'

    return desc

def fix_empty_docstrings(content: str) -> str:
    """Fix empty docstrings in Python content."""
    lines = content.split('\n')
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check for class definition
        class_match = re.match(r'^(\s*)class\s+(\w+)(?:\((.*?)\))?:', line)
        if class_match:
            indent = class_match.group(1)
            class_name = class_match.group(2)
            bases = class_match.group(3) if class_match.group(3) else ""
            base_list = [b.strip() for b in bases.split(',')] if bases else []

            result.append(line)
            i += 1

            # Check next line for empty docstring
            if i < len(lines):
                next_line = lines[i]
                if re.match(r'^\s*"""\"\"\"', next_line) or next_line.strip() == '""""""':
                    # Replace with generated docstring
                    doc = generate_class_docstring(class_name, base_list)
                    result.append(f'{indent}    """{doc}"""')
                    i += 1
                    continue
            continue

        # Check for function/method definition
        func_match = re.match(r'^(\s*)(async\s+)?def\s+(\w+)\s*\((.*?)\).*:', line)
        if func_match:
            indent = func_match.group(1)
            is_async = func_match.group(2) is not None
            func_name = func_match.group(3)
            args_str = func_match.group(4)
            args = [a.strip().split(':')[0].split('=')[0].strip() for a in args_str.split(',') if a.strip()]

            result.append(line)
            i += 1

            # Check next line for empty docstring
            if i < len(lines):
                next_line = lines[i]
                if re.match(r'^\s*"""\"\"\"', next_line) or next_line.strip() == '""""""':
                    # Skip trivial methods
                    if func_name.startswith('_') and func_name != '__init__':
                        result.append(next_line)
                        i += 1
                        continue

                    # Replace with generated docstring
                    doc = generate_function_docstring(func_name, args, is_async)
                    if '\n' in doc:
                        # Multi-line docstring
                        result.append(f'{indent}    """')
                        for doc_line in doc.split('\n'):
                            result.append(f'{indent}    {doc_line.strip()}')
                        result.append(f'{indent}    """')
                    else:
                        result.append(f'{indent}    """{doc}"""')
                    i += 1
                    continue
            continue

        result.append(line)
        i += 1

    return '\n'.join(result)

def process_file(file_path: Path) -> bool:
    """Process a single Python file."""
    try:
        content = file_path.read_text(encoding='utf-8')

        # Check if has empty docstrings
        if '""""""' not in content:
            return False

        # Fix empty docstrings
        fixed = fix_empty_docstrings(content)

        # Write back
        file_path.write_text(fixed, encoding='utf-8')
        return True

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    src_dir = Path("/Users/liyang/Desktop/testversion/BMAM_submission_clean/src")

    print("=" * 60)
    print("Generating English Docstrings")
    print("=" * 60)

    fixed_count = 0
    total_count = 0

    for py_file in src_dir.rglob("*.py"):
        total_count += 1
        if process_file(py_file):
            fixed_count += 1
            print(f"Fixed: {py_file.relative_to(src_dir)}")

    print(f"\n{'=' * 60}")
    print(f"Processed {total_count} files, fixed {fixed_count} files")

    # Verify
    remaining = 0
    for py_file in src_dir.rglob("*.py"):
        content = py_file.read_text(encoding='utf-8')
        count = content.count('""""""')
        if count > 0:
            remaining += count

    print(f"Remaining empty docstrings: {remaining}")

if __name__ == "__main__":
    main()
