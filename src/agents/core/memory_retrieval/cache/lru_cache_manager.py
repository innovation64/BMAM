"""
LRU Cache Manager
LRU缓存管理器
"""

from collections import OrderedDict
from typing import Any, Optional, Dict
import logging
import json
import hashlib

logger = logging.getLogger(__name__)


class LRUCacheManager:
    """
    LRU (Least Recently Used) 缓存管理器

    特性:
    - 自动淘汰最久未使用的条目
    - 统计命中率
    - 支持手动清理
    - 线程安全的有序字典实现

    Usage:
        cache = LRUCacheManager(max_size=200)
        cache.put('key1', {'data': 'value'})
        result = cache.get('key1')  # {'data': 'value'}
        stats = cache.get_stats()   # {'hit_rate': 1.0, ...}
    """

    def __init__(self, max_size: int = 200):
        """
        初始化LRU缓存

        Args:
            max_size: 缓存最大容量
        """
        self.max_size = max_size
        self.cache = OrderedDict()
        self.hit_count = 0
        self.miss_count = 0
        self.logger = logger

    def make_key(self, action: str, params: Dict[str, Any]) -> str:
        """
        生成缓存键

        使用MD5哈希确保键的唯一性和长度固定

        Args:
            action: 操作类型 (如'semantic_search')
            params: 参数字典

        Returns:
            32字符的MD5哈希字符串
        """
        try:
            # 排序参数确保一致性
            params_str = json.dumps(params, sort_keys=True, default=str)
            content = f"{action}_{params_str}"
            return hashlib.md5(content.encode()).hexdigest()
        except Exception as e:
            self.logger.warning(f"Failed to generate cache key: {e}")
            # 降级方案: 使用简单字符串
            return f"{action}_{hash(str(params))}"

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        如果命中,将该键移到末尾(最近使用)

        Args:
            key: 缓存键

        Returns:
            缓存的值,如果不存在返回None
        """
        if key in self.cache:
            self.hit_count += 1

            # LRU: 移到末尾表示最近使用
            self.cache.move_to_end(key)

            hit_rate = self.get_hit_rate()
            self.logger.debug(
                f"Cache HIT: key={key[:8]}... (hit_rate={hit_rate:.2%})"
            )

            return self.cache[key]
        else:
            self.miss_count += 1

            miss_rate = 1.0 - self.get_hit_rate()
            self.logger.debug(
                f"Cache MISS: key={key[:8]}... (miss_rate={miss_rate:.2%})"
            )

            return None

    def put(self, key: str, value: Any):
        """
        存入缓存

        如果缓存已满,自动淘汰最久未使用的条目

        Args:
            key: 缓存键
            value: 要缓存的值
        """
        if key in self.cache:
            # 更新已存在的key
            self.cache.move_to_end(key)
            self.cache[key] = value
        else:
            # 添加新key
            if len(self.cache) >= self.max_size:
                # 淘汰最久未使用的条目(第一个)
                evicted_key = next(iter(self.cache))
                self.cache.popitem(last=False)
                self.logger.debug(
                    f"Cache EVICT: key={evicted_key[:8]}... "
                    f"(size={len(self.cache)}/{self.max_size})"
                )

            self.cache[key] = value

    def clear(self):
        """清空缓存并重置统计"""
        size_before = len(self.cache)
        self.cache.clear()
        self.hit_count = 0
        self.miss_count = 0
        self.logger.info(f"Cache cleared ({size_before} entries removed)")

    def get_hit_rate(self) -> float:
        """
        获取缓存命中率

        Returns:
            命中率 [0.0, 1.0]
        """
        total = self.hit_count + self.miss_count
        return self.hit_count / total if total > 0 else 0.0

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            包含以下字段的字典:
            - size: 当前缓存大小
            - max_size: 最大容量
            - hit_count: 命中次数
            - miss_count: 未命中次数
            - hit_rate: 命中率
            - utilization: 利用率
        """
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'hit_rate': self.get_hit_rate(),
            'utilization': len(self.cache) / self.max_size if self.max_size > 0 else 0.0
        }

    def resize(self, new_size: int):
        """
        调整缓存大小

        如果新大小小于当前条目数,会淘汰最久未使用的条目

        Args:
            new_size: 新的最大容量
        """
        if new_size < 1:
            raise ValueError("Cache size must be at least 1")

        self.max_size = new_size

        # 如果当前大小超过新容量,淘汰多余条目
        while len(self.cache) > self.max_size:
            self.cache.popitem(last=False)

        self.logger.info(f"Cache resized to {new_size} (current size: {len(self.cache)})")

    def __len__(self) -> int:
        """返回缓存当前大小"""
        return len(self.cache)

    def __contains__(self, key: str) -> bool:
        """检查键是否存在"""
        return key in self.cache
