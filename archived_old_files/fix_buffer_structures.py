#!/usr/bin/env python3
"""
修复所有agent的buffer结构，确保每个agent都有recent_inputs和recent_outputs字段
"""

import json
import os
from pathlib import Path

def fix_agent_buffer_system():
    """修复AgentBufferSystem文件中的结构定义"""
    buffer_file = Path("src/agents/agent_buffer_system.py")
    
    if not buffer_file.exists():
        print("❌ AgentBufferSystem文件不存在")
        return
    
    # 读取当前内容
    with open(buffer_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找每个agent结构的'recent_exchanges': []位置，并添加缺失的字段
    import re
    
    # 匹配模式：'recent_exchanges': [] 但后面没有 recent_inputs/recent_outputs
    pattern = r"(\s*'recent_exchanges': \[\])\s*\n(\s*)\}\s*\n(\s*\}\s*,?)"
    
    def replacement(match):
        recent_exchanges_line = match.group(1)
        indent = match.group(2)
        closing_braces = match.group(3)
        
        # 添加缺失的字段
        return f"{recent_exchanges_line},\n{indent}'recent_inputs': [],\n{indent}'recent_outputs': []\n{closing_braces}"
    
    new_content = re.sub(pattern, replacement, content)
    
    # 写回文件
    with open(buffer_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ 修复了AgentBufferSystem结构定义")

def fix_existing_buffer_files():
    """修复现有的buffer文件，添加缺失的字段"""
    buffer_dir = Path("data/agent_buffers")
    
    if not buffer_dir.exists():
        print("❌ buffer目录不存在")
        return
    
    fixed_count = 0
    for json_file in buffer_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 检查并添加缺失的字段
            buffer_content = data.get('buffer_content', {})
            modified = False
            
            if 'recent_inputs' not in buffer_content:
                buffer_content['recent_inputs'] = []
                modified = True
            
            if 'recent_outputs' not in buffer_content:
                buffer_content['recent_outputs'] = []
                modified = True
            
            if modified:
                data['buffer_content'] = buffer_content
                
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                print(f"✅ 修复了 {json_file.name}")
                fixed_count += 1
        
        except Exception as e:
            print(f"❌ 修复 {json_file.name} 失败: {e}")
    
    print(f"🎉 总共修复了 {fixed_count} 个buffer文件")

if __name__ == "__main__":
    print("🔧 开始修复agent buffer结构...")
    fix_agent_buffer_system()
    fix_existing_buffer_files()
    print("✅ 修复完成！")