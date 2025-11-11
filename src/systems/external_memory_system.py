"""
External Memory System - 外部记忆系统

理论依据:
- Clark & Chalmers (1998) - The Extended Mind
- Hutchins (1995) - Cognition in the Wild (Distributed Cognition)
- Risko & Gilbert (2016) - Cognitive Offloading

⚠️ 重要: 这不是人脑的一部分,而是外部辅助工具!
人类认知系统 = 大脑 + 外部工具 (笔记本、书籍、搜索引擎)
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class ExternalDocument:
    """外部文档"""
    id: str
    title: str
    content: str
    source: str  # 'notebook' | 'document' | 'web'
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunks: Optional[List[Dict]] = None  # 文档分块 (用于大文档)
    embedding: Optional[List[float]] = None


class NotebookStore:
    """
    笔记本存储 - 模拟人类使用笔记本记录信息

    特点:
    - 用户主动添加的笔记
    - 结构化程度较高
    - 可靠性较高

    理论依据:
    - External Memory (Clark & Chalmers, 1998)
    - Offloading cognitive work to external aids
    """

    def __init__(self):
        self.notes: Dict[str, ExternalDocument] = {}

    async def add_note(self, title: str, content: str, metadata: Dict = None) -> str:
        """添加笔记"""
        note_id = uuid.uuid4().hex

        note = ExternalDocument(
            id=note_id,
            title=title,
            content=content,
            source='notebook',
            timestamp=datetime.now(),
            metadata=metadata or {}
        )

        self.notes[note_id] = note

        return note_id

    async def search_notes(self, query: str, k: int = 5) -> List[ExternalDocument]:
        """搜索笔记 (分词关键词匹配)"""
        # 🔧 修复: 分词搜索而不是完整字符串匹配
        query_terms = [term.lower() for term in query.split() if len(term) > 2]
        results = []

        for note in self.notes.values():
            relevance = 0
            title_lower = note.title.lower()
            content_lower = note.content.lower()

            # 对每个关键词分别匹配
            for term in query_terms:
                if term in title_lower:
                    relevance += 2  # 标题匹配权重高
                if term in content_lower:
                    relevance += 1  # 内容匹配权重低

            if relevance > 0:
                results.append((note, relevance))

        # 按相关性排序
        results.sort(key=lambda x: x[1], reverse=True)

        return [note for note, _ in results[:k]]

    def get_note(self, note_id: str) -> Optional[ExternalDocument]:
        """获取笔记"""
        return self.notes.get(note_id)

    def list_notes(self) -> List[ExternalDocument]:
        """列出所有笔记"""
        return list(self.notes.values())


class DocumentStore:
    """
    文档库 - 存储外部文档 (论文、书籍等)

    特点:
    - 大规模文本 (10篇论文, 8本书)
    - 需要分块处理
    - 需要实体关系提取

    理论依据:
    - Distributed Cognition (Hutchins, 1995)
    - Information stored externally, accessed when needed
    """

    def __init__(self, embedding_service=None):
        self.documents: Dict[str, ExternalDocument] = {}
        self.embedding_service = embedding_service
        self.chunk_size = 1000  # 每块1000字符

    async def add_document(
        self,
        title: str,
        content: str,
        metadata: Dict = None
    ) -> str:
        """添加文档"""
        doc_id = uuid.uuid4().hex

        # 分块处理大文档
        chunks = self._chunk_document(content)

        # 为每个chunk生成embedding (如果有embedding service)
        if self.embedding_service:
            for chunk in chunks:
                chunk['embedding'] = await self.embedding_service.encode_text(chunk['text'])

        document = ExternalDocument(
            id=doc_id,
            title=title,
            content=content,
            source='document',
            timestamp=datetime.now(),
            metadata=metadata or {},
            chunks=chunks
        )

        self.documents[doc_id] = document

        return doc_id

    def _chunk_document(self, content: str) -> List[Dict]:
        """将文档分块"""
        chunks = []
        words = content.split()

        for i in range(0, len(content), self.chunk_size):
            chunk_text = content[i:i + self.chunk_size]
            if chunk_text.strip():
                chunks.append({
                    'text': chunk_text,
                    'start_pos': i,
                    'end_pos': min(i + self.chunk_size, len(content))
                })

        return chunks

    async def search_documents(
        self,
        query: str,
        k: int = 10,
        use_embedding: bool = True
    ) -> List[Dict]:
        """
        搜索文档

        Returns:
            List of {
                'document': ExternalDocument,
                'chunk': Dict (如果是chunk-level搜索),
                'relevance': float
            }
        """
        if use_embedding and self.embedding_service:
            return await self._search_with_embedding(query, k)
        else:
            return await self._search_with_keywords(query, k)

    async def _search_with_embedding(self, query: str, k: int) -> List[Dict]:
        """使用embedding搜索"""
        query_embedding = await self.embedding_service.encode_text(query)

        results = []
        for doc in self.documents.values():
            if not doc.chunks:
                continue

            for chunk in doc.chunks:
                if 'embedding' not in chunk:
                    continue

                # 计算相似度 (简化版: 余弦相似度)
                similarity = self._cosine_similarity(
                    query_embedding,
                    chunk['embedding']
                )

                if similarity > 0.3:  # 阈值
                    results.append({
                        'document': doc,
                        'chunk': chunk,
                        'relevance': similarity
                    })

        # 按相关性排序
        results.sort(key=lambda x: x['relevance'], reverse=True)

        return results[:k]

    async def _search_with_keywords(self, query: str, k: int) -> List[Dict]:
        """使用关键词搜索 (分词匹配)"""
        # 🔧 修复: 分词搜索而不是完整字符串匹配
        query_terms = [term.lower() for term in query.split() if len(term) > 2]
        results = []

        for doc in self.documents.values():
            relevance = 0
            title_lower = doc.title.lower()
            content_lower = doc.content.lower()

            # 对每个关键词分别匹配
            for term in query_terms:
                if term in title_lower:
                    relevance += 2  # 标题匹配权重高
                if term in content_lower:
                    relevance += 1  # 内容匹配权重低

            if relevance > 0:
                results.append({
                    'document': doc,
                    'chunk': None,
                    'relevance': relevance
                })

        results.sort(key=lambda x: x['relevance'], reverse=True)

        return results[:k]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        import math

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def get_document(self, doc_id: str) -> Optional[ExternalDocument]:
        """获取文档"""
        return self.documents.get(doc_id)

    def list_documents(self) -> List[ExternalDocument]:
        """列出所有文档"""
        return list(self.documents.values())


class ExternalMemorySystem:
    """
    外部记忆系统 - 整合笔记本、文档库、知识图谱

    设计理念:
    - 模拟人类使用外部工具的认知卸载 (Cognitive Offloading)
    - 不是人脑的一部分,而是外部辅助工具
    - 当内部记忆不足时,主动查询外部系统

    组件:
    1. NotebookStore - 笔记本
    2. DocumentStore - 文档库
    3. KnowledgeGraph - 知识图谱 (通过KGBuilder构建)

    理论依据:
    - Extended Mind Theory (Clark & Chalmers, 1998)
    - Distributed Cognition (Hutchins, 1995)
    - Cognitive Offloading (Risko & Gilbert, 2016)
    """

    def __init__(
        self,
        embedding_service=None,
        kg_builder=None,
        search_api_key: Optional[str] = None
    ):
        """
        初始化外部记忆系统

        Args:
            embedding_service: 嵌入服务 (用于语义搜索)
            kg_builder: 知识图谱构建器
            search_api_key: 搜索API密钥 (如果需要联网搜索)
        """
        self.notebook = NotebookStore()
        self.documents = DocumentStore(embedding_service=embedding_service)
        self.kg_builder = kg_builder
        self.search_api_key = search_api_key


    async def add_note(self, title: str, content: str, metadata: Dict = None) -> str:
        """添加笔记 (外部记录)"""
        return await self.notebook.add_note(title, content, metadata)

    async def ingest_document(
        self,
        title: str,
        content: str,
        metadata: Dict = None,
        extract_kg: bool = True
    ) -> str:
        """
        摄入外部文档 (用于场景2: 10篇论文/8本书)

        Args:
            title: 文档标题
            content: 文档内容
            metadata: 元数据
            extract_kg: 是否提取知识图谱

        Returns:
            document_id
        """

        # 存储文档
        doc_id = await self.documents.add_document(title, content, metadata)

        # 提取实体和关系 (如果有KG Builder)
        if extract_kg and self.kg_builder:
            try:
                entities, relations = await self.kg_builder.extract_from_text(content)

                # 更新文档metadata
                doc = self.documents.get_document(doc_id)
                if doc:
                    doc.metadata['entities'] = entities
                    doc.metadata['relations'] = relations

            except (asyncio.CancelledError, asyncio.TimeoutError) as e:
                logger.warning(f"   ⚠️  KG extraction failed: {e}")

        return doc_id

    async def search(
        self,
        query: str,
        sources: List[str] = None,
        k: int = 10
    ) -> Dict[str, List]:
        """
        统一搜索接口 - 搜索所有外部记忆源

        Args:
            query: 查询文本
            sources: 搜索源 ['notebook', 'documents', 'kg', 'web']
            k: 返回数量

        Returns:
            {
                'notebook': [...],
                'documents': [...],
                'kg': [...],
                'web': [...]
            }
        """
        if sources is None:
            sources = ['notebook', 'documents']

        results = {}

        # 并行搜索
        tasks = []

        if 'notebook' in sources:
            tasks.append(('notebook', self.notebook.search_notes(query, k)))

        if 'documents' in sources:
            tasks.append(('documents', self.documents.search_documents(query, k)))

        if 'kg' in sources and self.kg_builder:
            tasks.append(('kg', self._search_kg(query, k)))

        if 'web' in sources and self.search_api_key:
            tasks.append(('web', self._search_web(query, k)))

        # 执行并行搜索
        if tasks:
            task_names = [name for name, _ in tasks]
            task_coros = [coro for _, coro in tasks]

            all_results = await asyncio.gather(*task_coros, return_exceptions=True)

            for i, task_name in enumerate(task_names):
                if isinstance(all_results[i], Exception):
                    logger.error(f"Search {task_name} failed: {all_results[i]}")
                    results[task_name] = []
                else:
                    results[task_name] = all_results[i]


        return results

    async def _search_kg(self, query: str, k: int) -> List[Dict]:
        """搜索知识图谱"""
        if not self.kg_builder:
            return []

        # 从query中提取实体
        entities = await self.kg_builder.extract_entities(query)

        # 查询KG中的relations
        results = []
        for entity in entities[:3]:  # 限制查询数量
            relations = await self.kg_builder.query_relations(entity)
            results.extend(relations)

        return results[:k]

    async def _search_web(self, query: str, k: int) -> List[Dict]:
        """联网搜索 (如果需要)"""
        # 预留接口: 可以集成Google Search API, Bing Search等
        return []

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'notebook_notes': len(self.notebook.notes),
            'documents': len(self.documents.documents),
            'total_chunks': sum(
                len(doc.chunks) if doc.chunks else 0
                for doc in self.documents.documents.values()
            ),
            'kg_available': self.kg_builder is not None,
            'web_search_available': self.search_api_key is not None
        }

    # ============================================================
    # 🔥 Phase 4: 大规模文档处理 (Large-scale Document Processing)
    # ============================================================

    async def hierarchical_process_documents(
        self,
        documents: List[Dict[str, str]],
        target_summaries: int = 7,
        prefrontal_agent = None
    ) -> Dict[str, Any]:
        """
        分层处理大规模文档 (Phase 4.2)

        策略 (根据ROADMAP):
        10篇论文 (500K tokens)
            ↓
        分块 (100个chunks × 5K tokens)
            ↓
        每个chunk提取key points (100 → 30 key points)
            ↓
        聚类key points (30 → 7 clusters)
            ↓
        工作记忆 (7 slots)

        Args:
            documents: 大量文档 [{'title': ..., 'content': ...}, ...]
            target_summaries: 最终压缩到几个摘要 (默认7)
            prefrontal_agent: 用于最终压缩

        Returns:
            {
                'summaries': List[Dict],           # target_summaries个高层摘要
                'key_points': List[Dict],          # 所有key points
                'total_chunks': int,               # 总chunk数
                'compression_ratio': float,        # 压缩比
                'processing_time_ms': float
            }
        """
        start_time = datetime.now()

        # Step 1: 分块所有文档
        all_chunks = []
        for doc in documents:
            # 使用DocumentStore的分块方法
            chunks = self.documents._chunk_document(doc['content'])
            for chunk in chunks:
                chunk['source_doc'] = doc.get('title', 'unknown')
            all_chunks.extend(chunks)


        # Step 2: 从每个chunk提取key points (简化版: 每个chunk取1个key point)
        key_points = []
        for chunk in all_chunks[:100]:  # 限制最多100个chunks避免过慢
            key_point = await self._extract_key_point(chunk)
            key_points.append(key_point)


        # Step 3: 使用PrefrontalAgent压缩key points → 7 slots
        if prefrontal_agent:
            compression_result = await prefrontal_agent.compress_working_memory(
                information=key_points,
                target_slots=target_summaries,
                use_llm=True
            )
            summaries = compression_result['compressed_info']
        else:
            # Fallback: 简单聚类
            summaries = key_points[:target_summaries]

        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(
            f"✅ Hierarchical processing: {len(documents)} docs → {len(all_chunks)} chunks "
            f"→ {len(key_points)} key points → {len(summaries)} summaries in {elapsed_ms:.0f}ms"
        )

        return {
            'summaries': summaries,
            'key_points': key_points,
            'total_chunks': len(all_chunks),
            'compression_ratio': len(all_chunks) / len(summaries) if summaries else 0,
            'processing_time_ms': elapsed_ms
        }

    async def _extract_key_point(self, chunk: Dict) -> Dict[str, Any]:
        """从chunk中提取key point (简化版: 取前100字符作为摘要)"""
        content = chunk.get('content', '')

        # 简化实现: 取前100字符 + 统计词频
        summary = content[:100] + '...' if len(content) > 100 else content

        # 提取关键词
        words = content.lower().split()
        from collections import Counter
        word_freq = Counter([w for w in words if len(w) > 4])
        keywords = [word for word, _ in word_freq.most_common(3)]

        return {
            'content': summary,
            'keywords': keywords,
            'source_chunk': chunk.get('chunk_id'),
            'source_doc': chunk.get('source_doc'),
            'word_count': len(words)
        }

    async def ingest_documents_incrementally(
        self,
        document_list: List[Dict[str, str]],
        batch_size: int = 3,
        delay_between_batches: float = 0.1
    ) -> Dict[str, Any]:
        """
        增量摄入文档 (Phase 4.3)

        不一次性加载10篇论文,而是分批加载,减少内存压力

        Args:
            document_list: 文档列表 [{'title': ..., 'content': ...}, ...]
            batch_size: 每批处理几篇 (默认3)
            delay_between_batches: 批次间延迟(秒)

        Returns:
            {
                'ingested_count': int,
                'failed_count': int,
                'batch_count': int,
                'total_time_ms': float
            }
        """
        start_time = datetime.now()
        ingested_ids = []
        failed = []

        # 分批处理
        for i in range(0, len(document_list), batch_size):
            batch = document_list[i:i+batch_size]
            batch_num = i // batch_size + 1


            # 并行ingest当前batch
            tasks = []
            for doc in batch:
                task = self.ingest_document(
                    title=doc['title'],
                    content=doc['content'],
                    metadata=doc.get('metadata', {})
                )
                tasks.append(task)

            # 等待当前batch完成
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for j, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to ingest {batch[j]['title']}: {result}")
                    failed.append(batch[j]['title'])
                else:
                    ingested_ids.append(result)

            # 批次间延迟 (模拟按需加载)
            if i + batch_size < len(document_list):
                await asyncio.sleep(delay_between_batches)

        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(
            f"✅ Incremental ingestion: {len(ingested_ids)}/{len(document_list)} documents "
            f"ingested in {elapsed_ms:.0f}ms ({len(failed)} failed)"
        )

        return {
            'ingested_count': len(ingested_ids),
            'failed_count': len(failed),
            'batch_count': (len(document_list) + batch_size - 1) // batch_size,
            'total_time_ms': elapsed_ms,
            'ingested_ids': ingested_ids,
            'failed_docs': failed
        }

    async def lazy_load_document(
        self,
        document_id: str,
        query_relevance: float = 0.0
    ) -> Optional[ExternalDocument]:
        """
        按需懒加载文档 (Phase 4.3)

        只有当query相关性足够高时才加载完整文档

        Args:
            document_id: 文档ID
            query_relevance: 查询相关性 (0-1)

        Returns:
            完整文档 (如果相关性足够) 或 None
        """
        # 简化实现: 如果相关性 > 0.5 才加载
        if query_relevance < 0.5:
            return None

        # 加载文档
        if document_id in self.documents.documents:
            doc = self.documents.documents[document_id]
            return doc
        else:
            logger.warning(f"Document {document_id} not found")
            return None
