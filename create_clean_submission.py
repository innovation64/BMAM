#!/usr/bin/env python3
"""
Create a clean submission package by removing Chinese comments.
"""
import os
import re
import shutil
from pathlib import Path

# Source and destination
SRC_DIR = Path("/Users/liyang/Desktop/testversion/BMAM/src")
DEST_DIR = Path("/Users/liyang/Desktop/testversion/BMAM_submission_clean/src")

# Core directories to include (essential algorithm components)
CORE_DIRS = [
    "agents/brain_regions",
    "agents/core",
    "agents/environment",
    "memory",
    "coordination",
    "reasoning",
    "brain",
    "core",
    "services",
    "utils",
]

# Files to include from root
ROOT_FILES = [
    "__init__.py",
    "agents/__init__.py",
    "agents/base.py",
    "agents/llm_service.py",
    "agents/memory_interface.py",
]

# Directories to exclude
EXCLUDE_DIRS = {"__pycache__", ".git", "ui", "monitoring", "evaluation", "optimization", "learning", "systems", "config"}

# Chinese character pattern
CHINESE_PATTERN = re.compile(r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]+')

def contains_chinese(text: str) -> bool:
    """Check if text contains Chinese characters."""
    return bool(CHINESE_PATTERN.search(text))

def remove_chinese_from_line(line: str) -> str:
    """Remove Chinese from a single line, preserving code structure."""
    # Skip if no Chinese
    if not contains_chinese(line):
        return line

    stripped = line.strip()
    indent = line[:len(line) - len(line.lstrip())]

    # Case 1: Pure Chinese comment line (# 中文...)
    if stripped.startswith('#') and contains_chinese(stripped):
        # Check if it's ONLY Chinese after #
        comment_content = stripped[1:].strip()
        if CHINESE_PATTERN.sub('', comment_content).strip() in ['', ':', '-', '!', '?', '.']:
            return ""  # Remove entire line
        else:
            # Mixed content - remove only Chinese parts
            cleaned = CHINESE_PATTERN.sub('', stripped)
            if cleaned.strip() == '#':
                return ""
            return indent + cleaned + "\n"

    # Case 2: Docstring with Chinese
    if '"""' in stripped or "'''" in stripped:
        # Replace Chinese with [...]
        return indent + CHINESE_PATTERN.sub('', stripped) + "\n"

    # Case 3: Inline comment with Chinese (code # Chinese comment)
    if '#' in line and contains_chinese(line.split('#', 1)[1] if '#' in line else ''):
        code_part = line.split('#', 1)[0]
        comment_part = line.split('#', 1)[1]
        # Remove Chinese from comment
        cleaned_comment = CHINESE_PATTERN.sub('', comment_part).strip()
        if cleaned_comment:
            return code_part + "# " + cleaned_comment + "\n"
        else:
            return code_part.rstrip() + "\n"

    # Case 4: Other Chinese (in strings, etc.)
    return CHINESE_PATTERN.sub('', line)

def clean_python_file(content: str) -> str:
    """Remove Chinese comments from Python file content."""
    lines = content.split('\n')
    cleaned_lines = []
    in_docstring = False
    docstring_char = None

    for line in lines:
        # Track docstrings
        stripped = line.strip()
        if not in_docstring:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                docstring_char = stripped[:3]
                if stripped.count(docstring_char) >= 2:
                    # Single line docstring
                    cleaned = remove_chinese_from_line(line + '\n')
                    if cleaned:
                        cleaned_lines.append(cleaned.rstrip('\n'))
                    continue
                else:
                    in_docstring = True
        else:
            if docstring_char in stripped:
                in_docstring = False

        cleaned = remove_chinese_from_line(line + '\n')
        if cleaned:
            cleaned_lines.append(cleaned.rstrip('\n'))

    # Remove consecutive empty lines (more than 2)
    result = []
    empty_count = 0
    for line in cleaned_lines:
        if line.strip() == '':
            empty_count += 1
            if empty_count <= 2:
                result.append(line)
        else:
            empty_count = 0
            result.append(line)

    return '\n'.join(result)

def copy_and_clean_file(src_path: Path, dest_path: Path):
    """Copy a Python file and remove Chinese comments."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    if src_path.suffix == '.py':
        try:
            content = src_path.read_text(encoding='utf-8')
            cleaned = clean_python_file(content)
            dest_path.write_text(cleaned, encoding='utf-8')

            # Verify no Chinese remains
            if contains_chinese(cleaned):
                print(f"  WARNING: Still has Chinese: {dest_path}")
        except Exception as e:
            print(f"  ERROR processing {src_path}: {e}")
    else:
        shutil.copy2(src_path, dest_path)

def should_include_dir(path: Path) -> bool:
    """Check if directory should be included."""
    return path.name not in EXCLUDE_DIRS

def process_directory(src_dir: Path, dest_dir: Path):
    """Recursively process a directory."""
    if not src_dir.exists():
        return

    for item in src_dir.iterdir():
        if item.is_dir():
            if should_include_dir(item):
                process_directory(item, dest_dir / item.name)
        elif item.suffix == '.py':
            copy_and_clean_file(item, dest_dir / item.name)

def main():
    print("=" * 60)
    print("Creating Clean Submission Package")
    print("=" * 60)

    # Clean destination
    if DEST_DIR.exists():
        shutil.rmtree(DEST_DIR)
    DEST_DIR.mkdir(parents=True)

    # Copy root __init__.py
    for root_file in ROOT_FILES:
        src_file = SRC_DIR / root_file
        if src_file.exists():
            copy_and_clean_file(src_file, DEST_DIR / root_file)
            print(f"Copied: {root_file}")

    # Process core directories
    for core_dir in CORE_DIRS:
        src_path = SRC_DIR / core_dir
        dest_path = DEST_DIR / core_dir
        if src_path.exists():
            print(f"\nProcessing: {core_dir}")
            process_directory(src_path, dest_path)

    # Count files
    py_files = list(DEST_DIR.rglob("*.py"))
    print(f"\n{'=' * 60}")
    print(f"Done! Created {len(py_files)} Python files")
    print(f"Location: {DEST_DIR}")

    # Verify no Chinese
    print("\nVerifying no Chinese remains...")
    chinese_files = []
    for py_file in py_files:
        content = py_file.read_text(encoding='utf-8')
        if contains_chinese(content):
            chinese_files.append(py_file)

    if chinese_files:
        print(f"WARNING: {len(chinese_files)} files still contain Chinese:")
        for f in chinese_files[:10]:
            print(f"  - {f.relative_to(DEST_DIR)}")
    else:
        print("SUCCESS: No Chinese characters found!")

if __name__ == "__main__":
    main()
