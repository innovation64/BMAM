"""
Short-term Memory Agent
短期记忆智能体 - 对应前额叶皮层的工作记忆
"""

from collections import deque
from datetime import datetime
from typing import Dict, Any, Optional
import hashlib
import sqlite3
import json
import os
from pathlib import Path

from ..base import BrainAgent, AgentMessage, BrainRegion


class ShortTermMemoryAgent(BrainAgent):
    """
    Short-term Memory Agent (Prefrontal Cortex - Working Memory)
    
    核心概念：短期
    对应脑区：前额叶皮层（Prefrontal Cortex）
    主要功能：工作记忆，信息临时保持（7±2项，20-30秒）
    """
    
    def __init__(self, client=None, persist_path: Optional[str] = None):
        super().__init__(
            agent_id="short_term_memory",
            brain_region=BrainRegion.PREFRONTAL,
            system_prompt="""You hold information temporarily for immediate use (7±2 items, ~30s).
            Prioritize by relevance and transfer important items to long-term storage when needed.""",
            client=client  # 支持外部注入客户端
        )

        # ✅ P1-1: 持久化配置 - 使用 BMAMPaths 统一路径管理
        from ...utils.paths import BMAMPaths
        self.persist_path = persist_path or str(BMAMPaths.WORKING_MEMORY_DB)
        self._init_persistence()

        # Working memory buffer (扩大容量以提高AI系统性能)
        # 注: Miller's 7±2规则适用于人脑，AI系统可以更大
        self.working_memory = deque(maxlen=20)  # ✅ 7→20 提高容量
        self.rehearsal_buffer = []
        self.manipulation_space = {}

        # Phonological loop and visuospatial sketchpad (Baddeley's model)
        self.phonological_loop = deque(maxlen=15)  # ✅ 5→15 扩大
        self.visuospatial_sketchpad = deque(maxlen=10)  # ✅ 4→10 扩大

        # Fast query cache (for working memory hit optimization)
        self.query_cache = {}  # {query_hash: result}
        self.recent_queries = deque(maxlen=50)  # ✅ 10→50 扩大查询缓存

        # ✅ P1-1: 从持久化存储加载query_cache
        self._load_query_cache()

        # Activation decay tracking
        self.activation_decay_rate = 0.1  # 10% per second
        self.last_update_time = datetime.now()

    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process incoming messages for short-term memory operations"""
        action = message.content.get('action')

        if action == 'fast_query':
            # Fast query for working memory hit (no LLM call)
            return await self._fast_query(message.content['query'])
        elif action == 'store_short_term':
            return await self._store_in_working_memory(message.content['item'])
        elif action == 'retrieve_working':
            return await self._retrieve_from_working_memory(message.content.get('query', ''))
        elif action == 'manipulate':
            return await self._manipulate_information(message.content['operation'])
        elif action == 'rehearse':
            return await self._rehearse_information(message.content.get('item_id'))
        elif action == 'clear_buffer':
            return await self._clear_working_memory()

        return {'error': f'Unknown action: {action}'}

    async def _fast_query(self, query: str) -> Dict[str, Any]:
        """
        Fast query for working memory (no LLM call, <50ms)

        Strategy:
        1. Exact match (hash lookup) - ~1ms
        2. Keyword match (substring) - ~5ms
        3. Return confidence based on activation level

        Returns:
            {
                'found': bool,
                'items': List[Dict],
                'confidence': float,
                'match_type': 'exact'|'keyword'|'none',
                'latency_ms': float
            }
        """
        start_time = datetime.now()

        # Update activation levels (time decay)
        self._update_activation_levels()

        # Step 1: Exact match via cache
        query_hash = hashlib.md5(query.encode()).hexdigest()
        if query_hash in self.query_cache:
            cached = self.query_cache[query_hash]
            latency = (datetime.now() - start_time).total_seconds() * 1000

            return {
                'found': True,
                'items': cached['items'],
                'confidence': cached['confidence'] * 0.95,  # slight decay
                'match_type': 'exact',
                'latency_ms': latency,
                'source': 'query_cache'
            }

        # Step 2: 智能关键词匹配（去除停用词，提取核心实体）
        # 停用词列表
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '他', '她', '它',
                      '什么', '怎么', '哪里', '可以', '这个', '那个', '时候', '？', '。', '，', '！', '你', '我们'}

        # 提取查询中的关键词（去除停用词）
        query_keywords = set()
        for word in query.lower().split():
            if len(word) > 1 and word not in stop_words:
                query_keywords.add(word)

        matched_items = []

        for item in self.working_memory:
            if item['activation'] < 0.10:  # 进一步降低阈值以提高召回率
                continue

            item_content_lower = item['content'].lower()

            # 计算关键词重叠
            item_keywords = set()
            for word in item_content_lower.split():
                if len(word) > 1 and word not in stop_words:
                    item_keywords.add(word)

            overlap = query_keywords & item_keywords

            if overlap or (query_keywords and any(kw in item_content_lower for kw in query_keywords)):
                # 计算匹配得分（多因素加权）
                overlap_ratio = len(overlap) / len(query_keywords) if query_keywords else 0

                # 子串匹配加成（处理"喝茶"vs"绿茶"这种情况）
                substring_matches = sum(1 for kw in query_keywords if kw in item_content_lower)
                substring_bonus = substring_matches * 0.15

                # 综合得分：重叠率 + 子串匹配 + 激活水平
                score = min(1.0, (overlap_ratio * 1.3 + substring_bonus) * item['activation'] + 0.15)

                matched_items.append({
                    'item': item,
                    'score': score,
                    'match_type': 'keyword',
                    'overlap_count': len(overlap)
                })

        if matched_items:
            # Sort by score
            matched_items.sort(key=lambda x: x['score'], reverse=True)
            best_match = matched_items[0]

            latency = (datetime.now() - start_time).total_seconds() * 1000

            result = {
                'found': True,
                'items': [best_match['item']],
                'confidence': best_match['score'],
                'match_type': 'keyword',
                'latency_ms': latency,
                'source': 'working_memory'
            }

            # ✅ P1-1: Update cache (memory + persistence)
            self.query_cache[query_hash] = result
            self.recent_queries.append(query)
            self._save_to_cache(query_hash, query, result, best_match['score'], 'keyword')

            # Limit cache size (keep top 1000 in DB, top 100 in memory)
            if len(self.query_cache) > 100:
                oldest_queries = list(self.query_cache.keys())[:20]
                for q in oldest_queries:
                    del self.query_cache[q]

            return result

        # Step 3: No match
        latency = (datetime.now() - start_time).total_seconds() * 1000
        return {
            'found': False,
            'items': [],
            'confidence': 0.0,
            'match_type': 'none',
            'latency_ms': latency,
            'source': 'working_memory'
        }

    async def _store_in_working_memory(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Store item in working memory with automatic decay"""
        memory_item = {
            'id': item.get('id', str(datetime.now().timestamp())),
            'content': item['content'],
            'timestamp': datetime.now().isoformat(),
            'activation': 1.0,  # Initial activation level
            'rehearsals': 0,
            'modality': item.get('modality', 'verbal'),  # verbal or visual
            'chunk_size': self._calculate_chunk_size(item['content'])
        }
        
        # Route to appropriate subsystem
        if memory_item['modality'] == 'verbal':
            self.phonological_loop.append(memory_item)
        elif memory_item['modality'] == 'visual':
            self.visuospatial_sketchpad.append(memory_item)
        
        # Add to main working memory (automatically removes oldest if full)
        self.working_memory.append(memory_item)
        
        # Update activation levels
        self._update_activation_levels()
        
        return {
            'stored': True,
            'item_id': memory_item['id'],
            'working_memory_size': len(self.working_memory),
            'capacity_used': len(self.working_memory) / 7,
            'activation_level': memory_item['activation']
        }
    
    async def _retrieve_from_working_memory(self, query: str) -> Dict[str, Any]:
        """Retrieve from working memory with activation boost"""
        results = []
        
        for item in self.working_memory:
            # Check for query match
            if not query or query.lower() in item['content'].lower():
                # Boost activation through retrieval (testing effect)
                item['activation'] = min(1.0, item['activation'] + 0.2)
                item['rehearsals'] += 1
                
                # Calculate retrieval confidence
                time_decay = self._calculate_time_decay(item['timestamp'])
                retrieval_confidence = item['activation'] * time_decay
                
                results.append({
                    'item': item,
                    'retrieval_confidence': retrieval_confidence
                })
        
        # Sort by retrieval confidence
        results.sort(key=lambda x: x['retrieval_confidence'], reverse=True)
        
        return {
            'results': results,
            'count': len(results),
            'working_memory_state': self._get_memory_state()
        }
    
    async def _manipulate_information(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Perform mental operations on working memory contents"""
        operation_type = operation.get('type', 'combine')
        
        result = {}
        
        if operation_type == 'combine':
            # Combine multiple working memory items
            combined_content = []
            for item in self.working_memory:
                if item['activation'] > 0.3:  # Only use sufficiently active items
                    combined_content.append(item['content'])
            
            result = {
                'operation': 'combine',
                'result': ' '.join(combined_content),
                'items_used': len(combined_content)
            }
            
        elif operation_type == 'chunk':
            # Chunk information for better retention
            items_to_chunk = [item for item in self.working_memory if item['activation'] > 0.4]
            chunked = self._create_chunk(items_to_chunk)
            
            result = {
                'operation': 'chunk',
                'result': chunked,
                'original_items': len(items_to_chunk)
            }
            
        elif operation_type == 'reorder':
            # Reorder items based on importance or recency
            reordered = sorted(self.working_memory, 
                             key=lambda x: x['activation'], 
                             reverse=True)
            self.working_memory = deque(reordered, maxlen=7)
            
            result = {
                'operation': 'reorder',
                'result': 'Items reordered by activation level'
            }
        
        else:
            result = {'operation': operation_type, 'result': 'Operation completed'}
        
        return result
    
    async def _rehearse_information(self, item_id: str = None) -> Dict[str, Any]:
        """Rehearse information to prevent decay"""
        rehearsed_items = []
        
        for item in self.working_memory:
            if item_id is None or item['id'] == item_id:
                # Rehearsal boosts activation and resets decay
                item['activation'] = min(1.0, item['activation'] + 0.3)
                item['rehearsals'] += 1
                item['timestamp'] = datetime.now().isoformat()  # Reset decay timer
                
                rehearsed_items.append(item['id'])
                
                # Move to rehearsal buffer for consolidation
                if item['rehearsals'] >= 3:
                    self.rehearsal_buffer.append(item)
        
        return {
            'rehearsed': True,
            'items_rehearsed': rehearsed_items,
            'ready_for_consolidation': len(self.rehearsal_buffer)
        }
    
    async def _clear_working_memory(self) -> Dict[str, Any]:
        """Clear working memory buffer"""
        items_cleared = len(self.working_memory)
        
        self.working_memory.clear()
        self.phonological_loop.clear()
        self.visuospatial_sketchpad.clear()
        
        return {
            'cleared': True,
            'items_cleared': items_cleared
        }
    
    def _update_activation_levels(self):
        """Update activation levels based on time decay"""
        current_time = datetime.now()
        
        for item in self.working_memory:
            item_timestamp = datetime.fromisoformat(item['timestamp']) if isinstance(item['timestamp'], str) else item['timestamp']
            time_elapsed = (current_time - item_timestamp).total_seconds()
            
            # Apply exponential decay (half-life ~15 seconds)
            decay_factor = 0.5 ** (time_elapsed / 15)
            item['activation'] *= decay_factor
    
    def _calculate_time_decay(self, timestamp: str) -> float:
        """Calculate time-based decay factor"""
        timestamp_dt = datetime.fromisoformat(timestamp) if isinstance(timestamp, str) else timestamp
        time_elapsed = (datetime.now() - timestamp_dt).total_seconds()
        
        # Exponential decay with 20-30 second window
        if time_elapsed < 20:
            return 1.0 - (time_elapsed / 40)
        elif time_elapsed < 30:
            return 0.5 - (time_elapsed - 20) / 20
        else:
            return 0.1  # Minimal retention after 30 seconds
    
    def _calculate_chunk_size(self, content: str) -> int:
        """Calculate chunk size based on content"""
        # Simple heuristic: words or meaningful units
        words = content.split()
        
        if len(words) <= 3:
            return 1  # Single chunk
        elif len(words) <= 7:
            return 2  # Two chunks
        else:
            return 3  # Three or more chunks
    
    def _create_chunk(self, items: list) -> str:
        """Create a meaningful chunk from multiple items"""
        if not items:
            return ""
        
        # Combine related items into a single chunk
        contents = [item['content'] for item in items]
        
        # Simple chunking strategy
        if len(contents) == 1:
            return contents[0]
        elif len(contents) == 2:
            return f"{contents[0]} and {contents[1]}"
        else:
            return f"{', '.join(contents[:-1])}, and {contents[-1]}"
    
    def _get_memory_state(self) -> Dict[str, Any]:
        """Get current state of working memory"""
        return {
            'total_items': len(self.working_memory),
            'phonological_items': len(self.phonological_loop),
            'visuospatial_items': len(self.visuospatial_sketchpad),
            'average_activation': sum(item['activation'] for item in self.working_memory) / len(self.working_memory) if self.working_memory else 0,
            'rehearsal_buffer_size': len(self.rehearsal_buffer)
        }
    
    def get_items_for_consolidation(self) -> list:
        """Get items ready for long-term consolidation"""
        # Items that have been rehearsed multiple times
        consolidation_candidates = [
            item for item in self.rehearsal_buffer
            if item['rehearsals'] >= 3 and item['activation'] > 0.5
        ]

        # Clear rehearsal buffer after extraction
        self.rehearsal_buffer = [
            item for item in self.rehearsal_buffer
            if item not in consolidation_candidates
        ]

        return consolidation_candidates

    # ========================================
    # ✅ P1-1: 持久化功能 (SQLite)
    # ========================================

    def _init_persistence(self):
        """初始化SQLite持久化存储"""
        # 确保data目录存在
        Path(self.persist_path).parent.mkdir(parents=True, exist_ok=True)

        # 创建数据库连接
        self.db_conn = sqlite3.connect(self.persist_path, check_same_thread=False)
        cursor = self.db_conn.cursor()

        # 创建query_cache表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS query_cache (
                query_hash TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                result TEXT NOT NULL,
                confidence REAL,
                match_type TEXT,
                created_at TEXT,
                last_accessed TEXT,
                access_count INTEGER DEFAULT 1
            )
        ''')

        self.db_conn.commit()

    def _load_query_cache(self):
        """从SQLite加载query_cache到内存"""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('SELECT query_hash, result, confidence, match_type FROM query_cache')
            rows = cursor.fetchall()

            for query_hash, result_json, confidence, match_type in rows:
                # ✅ 修复: 直接解析result，不再嵌套一层
                result = json.loads(result_json)
                self.query_cache[query_hash] = result

            if rows:
                print(f"✅ Loaded {len(rows)} query cache entries from persistence")
        except Exception as e:
            print(f"⚠️  Failed to load query cache: {e}")

    def _save_to_cache(self, query_hash: str, query: str, result: Dict, confidence: float, match_type: str):
        """保存查询结果到持久化缓存"""
        try:
            cursor = self.db_conn.cursor()
            now = datetime.now().isoformat()

            # 尝试插入或更新
            cursor.execute('''
                INSERT INTO query_cache (query_hash, query, result, confidence, match_type, created_at, last_accessed, access_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT(query_hash) DO UPDATE SET
                    last_accessed = ?,
                    access_count = access_count + 1
            ''', (query_hash, query, json.dumps(result), confidence, match_type, now, now, now))

            self.db_conn.commit()
        except Exception as e:
            print(f"⚠️  Failed to save to cache: {e}")

    def clear_persistent_cache(self):
        """清空持久化缓存"""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('DELETE FROM query_cache')
            self.db_conn.commit()
            self.query_cache.clear()
            print("✅ Cleared persistent query cache")
        except Exception as e:
            print(f"⚠️  Failed to clear cache: {e}")

    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('SELECT COUNT(*), SUM(access_count) FROM query_cache')
            total_entries, total_accesses = cursor.fetchone()

            return {
                'total_entries': total_entries or 0,
                'total_accesses': total_accesses or 0,
                'memory_entries': len(self.query_cache),
                'persistence_enabled': True
            }
        except Exception as e:
            return {
                'error': str(e),
                'persistence_enabled': False
            }

    def __del__(self):
        """关闭数据库连接"""
        if hasattr(self, 'db_conn'):
            self.db_conn.close()