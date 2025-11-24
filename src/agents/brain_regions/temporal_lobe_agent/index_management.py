"""
Index management for Temporal Lobe Agent
索引管理模块
"""

import logging
import string
import json
from datetime import datetime
from typing import Dict, Any

from .data_models import SemanticMemory
from ....utils.config import get_settings
from ....utils.model_selector import select_model_for_task  # 🔥 消除硬编码

logger = logging.getLogger(__name__)


class IndexManagementMixin:
    """Index management mixin for TemporalLobeAgent"""

    def _update_bm25_index(self, memory: SemanticMemory):
        """更新BM25倒排索引"""
        # 🔥 Remove punctuation before tokenization (consistent with search_memories)
        content_clean = memory.content.translate(str.maketrans('', '', string.punctuation))
        words = content_clean.lower().split()

        # 去除停用词 (简化版)
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '他', '她', '它'}
        words = [w for w in words if w not in stop_words and len(w) > 1]

        for word in set(words):  # 去重
            self.inverted_index[word].append(memory.id)

    async def _trigger_forgetting(self):
        """
        Phase 2增强: 自适应遗忘 (LLM动态决策)

        理论依据:
        - Ebbinghaus (1885) - 遗忘曲线理论
        - Anderson & Schooler (1991) - 需求驱动记忆 (Need Probability)

        Phase 2改进:
        - 旧策略: 固定10%遗忘
        - 新策略: LLM评估记忆重要性,动态决定遗忘率 (5%-15%)

        算法:
        1. 按consolidation_level, importance, access_count排序
        2. 对底部20%候选记忆使用LLM评估
        3. LLM判断每个记忆的保留价值 (0-1)
        4. 遗忘价值<0.3的记忆
        """

        # Step 1: 排序 (保留高价值记忆在前)
        self.memories.sort(
            key=lambda m: (m.consolidation_level, m.importance, m.access_count, m.timestamp),
            reverse=True
        )

        # Step 2: 确定遗忘候选 (底部20%)
        candidate_count = max(1, len(self.memories) // 5)
        candidates = self.memories[-candidate_count:]

        # Step 3: LLM评估遗忘 (如果有client)
        if self.client is not None:
            try:
                # 构建评估prompt
                candidate_summaries = []
                for i, mem in enumerate(candidates[:10]):  # 限制10条避免token过多
                    summary = f"{i+1}. [{mem.memory_subtype}] {mem.content[:100]} (importance={mem.importance:.2f}, access={mem.access_count}, consolidation={mem.consolidation_level})"
                    candidate_summaries.append(summary)

                prompt = f"""You are evaluating which semantic memories to forget.

Candidate memories for potential forgetting:
{chr(10).join(candidate_summaries)}

For each memory, assess its retention value (0-1):
- 1.0 = critical knowledge, must keep
- 0.5 = moderately useful
- 0.0 = outdated/redundant, can forget

Respond in JSON format:
{{"retention_values": [0.8, 0.3, 0.5, ...]}}
"""

                # 🔥 消除硬编码：使用智能模型选择
                forgetting_model = select_model_for_task('forgetting')

                response = await self.client.chat.completions.create(
                    model=forgetting_model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    max_tokens=200
                )

                result = json.loads(response.choices[0].message.content)
                retention_values = result.get('retention_values', [])

                # 标记遗忘 (retention_value < 0.3)
                to_forget = []
                for i, value in enumerate(retention_values):
                    if i < len(candidates) and value < 0.3:
                        to_forget.append(candidates[i])

            except (json.JSONDecodeError) as e:
                logger.warning(f"⚠️ LLM forgetting failed: {e}, fallback to algorithm")
                to_forget = None

        else:
            to_forget = None

        # Fallback: 固定比例遗忘 (如果LLM失败)
        if to_forget is None:
            forget_count = len(self.memories) // 10
            to_forget = self.memories[-forget_count:]

        # Step 4: 执行遗忘
        forgotten_ids = {mem.id for mem in to_forget}
        self.memories = [m for m in self.memories if m.id not in forgotten_ids]

        # 更新memory_dict
        for mem in to_forget:
            if mem.id in self.memory_dict:
                del self.memory_dict[mem.id]

        # 重建索引
        self._rebuild_index()

        self.total_forgotten += len(to_forget)

    def _rebuild_index(self):
        """重建BM25索引"""
        self.inverted_index.clear()

        for mem in self.memories:
            self._update_bm25_index(mem)

    def _get_capacity_status(self) -> Dict[str, Any]:
        """获取容量状态"""
        current = len(self.memories)
        return {
            'current': current,
            'max': self.capacity,
            'usage_percent': (current / self.capacity) * 100 if self.capacity > 0 else 0
        }
