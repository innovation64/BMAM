#!/usr/bin/env python3
"""
FAISS Index Cleanup Utility
清理被污染的FAISS向量索引

用于清理包含fallback向量的FAISS索引，并从数据库重建干净的索引
"""

import os
import sys
import asyncio
from pathlib import Path

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # 如果没有python-dotenv，手动加载.env
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#') and '=' in line:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value.strip('"')

from src.memory.memory_system import AdvancedMemorySystem
from src.utils.config import get_logger

logger = get_logger(__name__)


async def clean_and_rebuild_faiss_index():
    """清理并重建FAISS索引"""
    
    print("🧹 FAISS索引清理工具")
    print("=" * 50)
    
    try:
        # 初始化记忆系统
        print("📚 初始化记忆系统...")
        memory_system = AdvancedMemorySystem()
        
        # 检查当前索引状态
        stats = memory_system.get_system_stats()
        print(f"📊 当前索引状态:")
        print(f"   - 向量数量: {stats.get('vector_count', 0)}")
        print(f"   - 记忆数量: {stats.get('memory_count', 0)}")
        
        # 询问用户确认
        response = input("\n⚠️  确定要清理并重建FAISS索引吗? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            print("❌ 取消操作")
            return
        
        print("\n🔧 开始清理FAISS索引...")
        
        # 清理corrupted索引
        memory_system.vector_db.clean_corrupted_index()
        print("✅ 清理完成")
        
        print("\n🔄 从数据库重建索引...")
        
        # 重建索引
        memory_system.vector_db.rebuild_index_from_database(memory_system.db_manager)
        print("✅ 重建完成")
        
        # 显示新的统计信息
        new_stats = memory_system.get_system_stats()
        print(f"\n📊 重建后状态:")
        print(f"   - 向量数量: {new_stats.get('vector_count', 0)}")
        print(f"   - 记忆数量: {new_stats.get('memory_count', 0)}")
        
        print("\n🎉 FAISS索引清理和重建完成！")
        
    except Exception as e:
        print(f"\n❌ 清理过程出错: {e}")
        logger.error(f"FAISS索引清理失败: {e}", exc_info=True)


def manual_cleanup():
    """手动删除索引文件（紧急情况下使用）"""
    
    print("🚨 手动删除FAISS索引文件")
    print("=" * 50)
    
    index_files = [
        "data/memory_vectors.index",
        "data/memory_vectors_mappings.json"
    ]
    
    response = input("⚠️  确定要手动删除所有FAISS文件吗? (y/N): ")
    if response.lower() not in ['y', 'yes']:
        print("❌ 取消操作")
        return
    
    for file_path in index_files:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"✅ 删除: {file_path}")
            else:
                print(f"⚠️  文件不存在: {file_path}")
        except Exception as e:
            print(f"❌ 删除失败 {file_path}: {e}")
    
    print("\n🎉 手动清理完成！")
    print("💡 建议重启系统以重新初始化索引")


def main():
    """主函数"""
    
    print("选择操作模式:")
    print("1. 🧹 清理并重建索引（推荐）")
    print("2. 🚨 手动删除索引文件（紧急）")
    print("3. ❌ 退出")
    
    choice = input("\n请选择 (1-3): ").strip()
    
    if choice == "1":
        # 检查API密钥
        if not os.getenv('OPENAI_API_KEY'):
            print("❌ 未设置 OPENAI_API_KEY 环境变量")
            print("请设置: export OPENAI_API_KEY='your-api-key'")
            return
        
        asyncio.run(clean_and_rebuild_faiss_index())
        
    elif choice == "2":
        manual_cleanup()
        
    elif choice == "3":
        print("👋 退出")
        
    else:
        print("❌ 无效选择")


if __name__ == "__main__":
    main()