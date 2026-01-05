#!/usr/bin/env python3
"""Fix remaining empty docstrings with a more aggressive approach."""
import re
from pathlib import Path

def fix_file(file_path: Path) -> int:
    content = file_path.read_text(encoding='utf-8')
    original = content
    
    # Pattern 1: class Name: followed by """"""
    content = re.sub(
        r'(class\s+(\w+).*?:\s*\n\s*)""""""',
        lambda m: m.group(1) + f'"""{m.group(2).replace("_", " ").title()} class."""',
        content
    )
    
    # Pattern 2: def name(...): followed by """"""  
    content = re.sub(
        r'(def\s+(\w+)\s*\([^)]*\).*?:\s*\n\s*)""""""',
        lambda m: m.group(1) + f'"""{m.group(2).replace("_", " ").title().strip()}."""',
        content
    )
    
    # Pattern 3: async def name(...): followed by """"""
    content = re.sub(
        r'(async\s+def\s+(\w+)\s*\([^)]*\).*?:\s*\n\s*)""""""',
        lambda m: m.group(1) + f'"""{m.group(2).replace("_", " ").title().strip()} (async)."""',
        content
    )
    
    if content != original:
        file_path.write_text(content, encoding='utf-8')
        return content.count('"""') - original.count('"""')
    return 0

src_dir = Path("/Users/liyang/Desktop/testversion/BMAM_submission_clean/src")
total_fixed = 0

for py_file in src_dir.rglob("*.py"):
    fixed = fix_file(py_file)
    if fixed:
        print(f"Fixed: {py_file.relative_to(src_dir)}")
        
# Count remaining
remaining = 0
for py_file in src_dir.rglob("*.py"):
    content = py_file.read_text()
    remaining += content.count('""""""')
    
print(f"\nRemaining empty docstrings: {remaining}")
