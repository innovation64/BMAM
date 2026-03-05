#!/usr/bin/env python3
"""
缓存性能监控工具
Cache Performance Monitor
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def print_cache_stats():
    """打印缓存统计信息"""
    print("=" * 60)
    print("BMAM 缓存性能监控")
    print("=" * 60)

    try:
        # 1. Embedding缓存统计
        from src.services.openai_embedding_service import OpenAIEmbeddingService

        print("\n【1】Embedding缓存统计:")
        print("-" * 60)

        embedding_service = OpenAIEmbeddingService()
        if hasattr(embedding_service, 'cache') and embedding_service.cache:
            stats = embedding_service.cache.get_stats()
            print(f"  缓存大小:    {stats['cache_size']}/{stats['max_size']}")
            print(f"  命中次数:    {stats['hit_count']}")
            print(f"  未命中次数:  {stats['miss_count']}")
            print(f"  命中率:      {stats['hit_rate']}")
            print(f"  待写入:      {stats['pending_writes']} 条")
        else:
            print("  ⚠️  Embedding缓存未初始化")

    except Exception as e:
        print(f"  ❌ 获取Embedding缓存统计失败: {e}")

    try:
        # 2. MemoryRetrieval缓存统计
        print("\n【2】Memory Retrieval缓存统计:")
        print("-" * 60)

        # 需要从coordinator获取
        print("  💡 提示: 需要在运行时通过coordinator获取")
        print("  使用方法:")
        print("    coordinator = BrainInspiredCoordinator()")
        print("    stats = coordinator.memory_retrieval.get_cache_stats()")
        print("    print(stats)")

    except Exception as e:
        print(f"  ❌ 获取Retrieval缓存统计失败: {e}")

    print("\n" + "=" * 60)
    print("建议:")
    print("  1. 如果Embedding命中率 < 50%, 考虑增加cache_size")
    print("  2. 如果Retrieval命中率 < 30%, 考虑增加缓存大小")
    print("  3. 定期监控pending_writes,如果过多可能有IO瓶颈")
    print("=" * 60)


def print_cache_recommendations():
    """打印缓存优化建议"""
    print("\n" + "#" * 60)
    print("缓存优化建议")
    print("#" * 60)

    print("\n【Embedding缓存】")
    print("  当前配置:")
    print("    - 大小: 10000")
    print("    - TTL: 24小时")
    print("    - 批量写入阈值: 10条")
    print("    - 强制保存间隔: 5分钟")
    print()
    print("  优化建议:")
    print("    - 如果内存充足,可增加到50000")
    print("    - 如果embedding重复率高,可延长TTL到48小时")
    print("    - 如果IO压力大,可增加批量写入阈值到50条")

    print("\n【MemoryRetrieval缓存】")
    print("  当前配置:")
    print("    - 大小: 200 (已从20优化到200)")
    print("    - LRU策略: OrderedDict")
    print()
    print("  优化建议:")
    print("    - 如果用户查询类型多样,可增加到500")
    print("    - 如果内存紧张,保持200即可")

    print("\n【优化效果预估】")
    print("  Embedding缓存优化:")
    print("    ✅ IO操作减少: 90% (批量写入)")
    print("    ✅ 响应速度提升: 10-30ms/query")
    print()
    print("  MemoryRetrieval缓存优化:")
    print("    ✅ 缓存容量增加: 10倍 (20→200)")
    print("    ✅ 命中率提升: 预计从15%提升到50%+")
    print("    ✅ 向量搜索次数减少: 30-50%")

    print("\n" + "#" * 60)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--recommendations':
        print_cache_recommendations()
    else:
        print_cache_stats()

    print("\n💡 提示: 使用 --recommendations 查看优化建议")


if __name__ == "__main__":
    main()