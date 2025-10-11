import re

file_path = "src/agents/core/reasoning_validator.py"

with open(file_path, 'r') as f:
    content = f.read()

# 为_identity_reasoning, _research_reasoning, _multi_hop_reasoning添加memories_by_region参数
replacements = [
    (
        r'(async def _identity_reasoning\(\s*self,\s*query: str,\s*memories: List\[Dict\],\s*hippocampus: Optional\[Any\] = None)\)',
        r'\1, memories_by_region: Optional[Dict] = None)'
    ),
    (
        r'(async def _research_reasoning\(\s*self,\s*query: str,\s*memories: List\[Dict\],\s*hippocampus: Optional\[Any\] = None)\)',
        r'\1, memories_by_region: Optional[Dict] = None)'
    ),
    (
        r'(async def _multi_hop_reasoning\(\s*self,\s*query: str,\s*memories: List\[Dict\],\s*hippocampus: Optional\[Any\] = None)\)',
        r'\1, memories_by_region: Optional[Dict] = None)'
    ),
]

for pattern, replacement in replacements:
    content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

with open(file_path, 'w') as f:
    f.write(content)

print("✅ Updated reasoning method signatures")
