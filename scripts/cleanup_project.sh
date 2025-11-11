#!/bin/bash
# BMAM 项目清理脚本
# 用途: 清理冗余文件、__pycache__、整理文档结构

set -e

echo "🧹 BMAM 项目清理脚本"
echo "===================="
echo ""

# 1. 清理 __pycache__
echo "1️⃣ 清理 __pycache__ 目录..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
echo "   ✅ __pycache__ 已清理"
echo ""

# 2. 清理 .pyc 文件
echo "2️⃣ 清理 .pyc 文件..."
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
echo "   ✅ .pyc 文件已清理"
echo ""

# 3. 整理文档 (可选 - 需要用户确认)
read -p "3️⃣ 是否整理根目录文档到 docs/refactoring_history/? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "   创建文档归档目录..."
    mkdir -p docs/refactoring_history/

    echo "   移动重构历史文档..."
    mv FILE_SPLIT_*.md docs/refactoring_history/ 2>/dev/null || true
    mv MEMORY_RETRIEVAL_*.md docs/refactoring_history/ 2>/dev/null || true
    mv PERSONALITY_*.md docs/refactoring_history/ 2>/dev/null || true
    mv REFLECTION_*.md docs/refactoring_history/ 2>/dev/null || true
    mv REMAINING_FILES_ANALYSIS.md docs/refactoring_history/ 2>/dev/null || true

    echo "   ✅ 文档已整理"
else
    echo "   ⏭️  跳过文档整理"
fi
echo ""

# 4. 清理废弃测试 (可选)
read -p "4️⃣ 是否移动废弃测试到 archived/tests/? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -d "tests/deprecated" ]; then
        echo "   创建归档测试目录..."
        mkdir -p archived/tests/

        echo "   移动废弃测试..."
        mv tests/deprecated/* archived/tests/ 2>/dev/null || true
        rmdir tests/deprecated 2>/dev/null || true

        echo "   ✅ 废弃测试已归档"
    else
        echo "   ℹ️  没有发现 tests/deprecated 目录"
    fi
else
    echo "   ⏭️  跳过废弃测试清理"
fi
echo ""

# 5. 验证系统完整性
echo "5️⃣ 验证系统完整性..."
python3 -c "
from src.agents.core.memory_retrieval import MemoryRetrievalAgent
from src.agents.core.personality import PersonalityAgent
print('   ✅ 核心模块导入正常')
" 2>&1 | tail -1

echo ""
echo "🎉 清理完成!"
echo ""
echo "📊 清理统计:"
echo "   - __pycache__: 已清理"
echo "   - .pyc 文件: 已清理"
echo "   - 文档整理: $([ -d "docs/refactoring_history" ] && echo "已完成" || echo "未执行")"
echo "   - 废弃测试: $([ -d "archived/tests" ] && echo "已归档" || echo "未执行")"
echo ""
echo "✨ 项目结构已优化!"
