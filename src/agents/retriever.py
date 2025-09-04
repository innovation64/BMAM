from typing import Dict, Any, List, Optional, Tuple
from .base import BaseAgent
import random
# Optional dependencies for production use
try:
    import faiss
    from sentence_transformers import SentenceTransformer
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
import json

class RetrieverAgent(BaseAgent):
    """Agent for retrieving relevant documents based on query and conditional memory"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("Retriever", config)
        
        # Ensure config is not None
        if config is None:
            config = {}
            
        self.embedding_model_name = config.get('embedding_model', 'sentence-transformers/all-MiniLM-L6-v2')
        self.top_k = config.get('top_k', 10)
        self.condition_weight = config.get('condition_weight', 0.3)
        self.similarity_metric = config.get('similarity_metric', 'cosine')
        
        # Initialize embedding model with multiple fallback options
        self.embedding_model = None
        self.embedding_dim = 384  # Default dimension
        self.use_simcse = False
        
        if FAISS_AVAILABLE:
            # List of fallback models to try (from most preferred to basic)
            models_to_try = [
                self.embedding_model_name,  # Primary model from config
                'sentence-transformers/all-MiniLM-L6-v2',  # Small, fast model
                'all-MiniLM-L6-v2',  # Even simpler name
            ]
            
            for model_name in models_to_try:
                try:
                    self.logger.info(f"Attempting to load embedding model: {model_name}")
                    self.embedding_model = SentenceTransformer(model_name)
                    self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
                    
                    # Check if this is a SimCSE model
                    if 'simcse' in model_name.lower():
                        self.logger.info(f"✅ Using SimCSE model for semantic retrieval: {model_name}")
                        self.use_simcse = True
                    else:
                        self.logger.info(f"✅ Using embedding model: {model_name}")
                        self.use_simcse = False
                    
                    # If we get here, the model loaded successfully
                    break
                    
                except Exception as e:
                    self.logger.warning(f"Failed to load embedding model {model_name}: {e}")
                    continue
            
            # If all models failed, set up for text-only retrieval
            if self.embedding_model is None:
                self.logger.error("❌ All embedding models failed - switching to text-based retrieval mode")
                self.logger.info("📝 Retrieval will use keyword matching instead of semantic similarity")
                self.use_text_fallback = True
            else:
                self.use_text_fallback = False
        else:
            self.logger.warning("FAISS not available - using text-based retrieval")
            self.embedding_model = None
            self.embedding_dim = 384
            self.use_simcse = False
            self.use_text_fallback = True
            
        # FAISS index for document embeddings
        self.document_index = None
        self.documents = []
        self.document_metadata = []
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process retrieval requests
        
        Args:
            input_data: Should contain:
                - query: User query
                - memory_state: Current conditional memory
                - documents: Available documents (if not pre-indexed)
                - action: 'retrieve', 'index', or 'update_index'
        """
        action = input_data.get('action', 'retrieve')
        
        if action == 'index':
            return await self._index_documents(input_data)
        elif action == 'retrieve':
            return await self._retrieve_documents(input_data)
        elif action == 'update_index':
            return await self._update_index(input_data)
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}
    
    async def _index_documents(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Index documents for retrieval"""
        documents = input_data.get('documents', [])
        
        if not documents:
            return {
                "status": "error",
                "message": "No documents provided for indexing"
            }
        
        self.documents = documents
        self.document_metadata = []
        
        # Extract text and metadata
        texts = []
        for i, doc in enumerate(documents):
            if isinstance(doc, dict):
                text = doc.get('text', doc.get('content', ''))
                metadata = {
                    'id': doc.get('id', f'doc_{i}'),
                    'title': doc.get('title', ''),
                    'source': doc.get('source', ''),
                    'metadata': doc.get('metadata', {})
                }
            else:
                text = str(doc)
                metadata = {'id': f'doc_{i}', 'title': '', 'source': '', 'metadata': {}}
            
            texts.append(text)
            self.document_metadata.append(metadata)
        
        # Create embeddings if model is available
        if self.embedding_model:
            try:
                embeddings = self.embedding_model.encode(texts)
                self.logger.info(f"✅ Created embeddings for {len(texts)} documents")
            except Exception as e:
                self.logger.error(f"Failed to create embeddings: {e}")
                embeddings = None
        else:
            self.logger.info("📝 No embedding model available - using text-only indexing")
            embeddings = None
        
        # Create FAISS index if available
        if FAISS_AVAILABLE and embeddings is not None:
            self.document_index = faiss.IndexFlatIP(self.embedding_dim)
            
            # Normalize embeddings for cosine similarity
            if len(embeddings) > 0:
                if isinstance(embeddings, list):
                    import numpy as np
                    embeddings = np.array(embeddings, dtype='float32')
                
                # Store document embeddings for SimCSE
                self.document_embeddings = embeddings.copy()
                
                faiss.normalize_L2(embeddings)
                self.document_index.add(embeddings.astype('float32'))
                self.logger.info(f"✅ Created FAISS index with {len(embeddings)} documents")
        else:
            # Simple storage for testing without FAISS or embeddings
            self.simple_embeddings = embeddings if embeddings else []
            if not embeddings:
                self.logger.warning("No embeddings created - retrieval will be limited")
        
        return {
            "status": "success",
            "indexed_documents": len(documents),
            "embedding_dimension": self.embedding_dim
        }
    
    async def _retrieve_documents(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve relevant documents based on query and conditions"""
        query = input_data.get('query', '')
        memory_state = input_data.get('memory_state', {})
        top_k = input_data.get('top_k', self.top_k)
        
        # Check if we have any indexing (FAISS, simple embeddings, or text-only)
        has_index = (FAISS_AVAILABLE and self.document_index is not None) or \
                   (not FAISS_AVAILABLE and hasattr(self, 'simple_embeddings')) or \
                   (hasattr(self, 'use_text_fallback') and self.use_text_fallback and len(self.documents) > 0)
        
        if not has_index or not query:
            return {
                "status": "error", 
                "message": f"No index available (FAISS: {FAISS_AVAILABLE}, docs: {len(self.documents)}, text_fallback: {getattr(self, 'use_text_fallback', False)}) or empty query",
                "total_retrieved": 0,
                "retrieved_documents": []
            }
        
        # Create enhanced query incorporating conditions
        enhanced_query = self._enhance_query_with_conditions(query, memory_state)
        
        # Search using appropriate method
        if hasattr(self, 'use_text_fallback') and self.use_text_fallback:
            # Use text-based retrieval without embeddings
            self.logger.info("📝 Using text-based keyword retrieval")
            scores, indices = self._text_based_search(enhanced_query, top_k)
        else:
            # Use embedding-based retrieval
            if self.embedding_model:
                try:
                    query_embedding = self.embedding_model.encode([enhanced_query])
                except Exception as e:
                    self.logger.error(f"Failed to create query embedding: {e}")
                    # Fallback to text-based search
                    self.logger.info("📝 Falling back to text-based retrieval")
                    scores, indices = self._text_based_search(enhanced_query, top_k)
                    query_embedding = None
            else:
                self.logger.info("📝 No embedding model available - using text-based retrieval")
                scores, indices = self._text_based_search(enhanced_query, top_k)
                query_embedding = None
            
            # If we have embeddings and index, use semantic search
            if query_embedding is not None and FAISS_AVAILABLE and self.document_index is not None:
                if self.use_simcse and self.similarity_metric == 'cosine':
                    # 使用SimCSE + 余弦相似度（与原论文对齐）
                    scores, indices = self._simcse_cosine_search(query_embedding, top_k)
                else:
                    # 标准FAISS搜索
                    if isinstance(query_embedding, list):
                        import numpy as np
                        query_embedding = np.array(query_embedding, dtype='float32')
                    faiss.normalize_L2(query_embedding)
                    scores, indices = self.document_index.search(query_embedding.astype('float32'), top_k)
        
        # Retrieve documents with metadata
        retrieved_docs = []
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx >= 0 and idx < len(self.documents):
                doc_data = {
                    'rank': i + 1,
                    'score': float(score),
                    'document': self.documents[idx],
                    'metadata': self.document_metadata[idx],
                    'relevance_factors': self._analyze_relevance(
                        self.documents[idx], query, memory_state
                    )
                }
                retrieved_docs.append(doc_data)
        
        # Re-rank based on conditions
        reranked_docs = self._rerank_with_conditions(retrieved_docs, memory_state)
        
        return {
            "status": "success",
            "query": query,
            "enhanced_query": enhanced_query,
            "retrieved_documents": reranked_docs,
            "total_retrieved": len(reranked_docs),
            "conditions_applied": len(memory_state.get('conditions', []))
        }
    
    async def _update_index(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update index with new documents"""
        new_documents = input_data.get('new_documents', [])
        
        if not new_documents:
            return {"status": "success", "message": "No new documents to add"}
        
        # Add to existing documents
        start_idx = len(self.documents)
        self.documents.extend(new_documents)
        
        # Create embeddings for new documents
        texts = []
        for i, doc in enumerate(new_documents):
            if isinstance(doc, dict):
                text = doc.get('text', doc.get('content', ''))
                metadata = {
                    'id': doc.get('id', f'doc_{start_idx + i}'),
                    'title': doc.get('title', ''),
                    'source': doc.get('source', ''),
                    'metadata': doc.get('metadata', {})
                }
            else:
                text = str(doc)
                metadata = {'id': f'doc_{start_idx + i}', 'title': '', 'source': '', 'metadata': {}}
            
            texts.append(text)
            self.document_metadata.append(metadata)
        
        if self.embedding_model:
            new_embeddings = self.embedding_model.encode(texts)
        else:
            new_embeddings = [[random.random() for _ in range(self.embedding_dim)] for _ in range(len(texts))]
        
        # Add to index if FAISS is available
        if FAISS_AVAILABLE and self.document_index is not None:
            if isinstance(new_embeddings, list):
                import numpy as np
                new_embeddings = np.array(new_embeddings, dtype='float32')
            faiss.normalize_L2(new_embeddings)
            self.document_index.add(new_embeddings.astype('float32'))
        else:
            # Extend simple storage
            if hasattr(self, 'simple_embeddings'):
                self.simple_embeddings.extend(new_embeddings)
            else:
                self.simple_embeddings = new_embeddings
        
        return {
            "status": "success",
            "added_documents": len(new_documents),
            "total_documents": len(self.documents)
        }
    
    def _enhance_query_with_conditions(self, query: str, memory_state: Dict[str, Any]) -> str:
        """Enhance query with conditional information"""
        conditions = memory_state.get('conditions', [])
        if not conditions:
            return query
        
        # Extract relevant conditions
        relevant_conditions = []
        query_lower = query.lower()
        
        for condition in conditions:
            condition_text = condition.get('text', '').lower()
            category = condition.get('category', '')
            
            # Check relevance
            if any(word in condition_text for word in query_lower.split()):
                relevant_conditions.append(condition)
            elif category == 'hard_constraints':
                relevant_conditions.append(condition)  # Always include hard constraints
        
        if not relevant_conditions:
            return query
        
        # Build enhanced query
        enhanced_parts = [query]
        
        # Add hard constraints
        hard_constraints = [c for c in relevant_conditions if c.get('category') == 'hard_constraints']
        if hard_constraints:
            constraint_texts = [c.get('text', '') for c in hard_constraints]
            enhanced_parts.append("MUST: " + " AND ".join(constraint_texts))
        
        # Add preferences
        preferences = [c for c in relevant_conditions if c.get('category') == 'soft_preferences']
        if preferences:
            pref_texts = [c.get('text', '') for c in preferences[:3]]  # Limit to top 3
            enhanced_parts.append("PREFER: " + " OR ".join(pref_texts))
        
        # Add temporal conditions
        temporal = [c for c in relevant_conditions if c.get('category') == 'temporal_conditions']
        if temporal:
            temp_texts = [c.get('text', '') for c in temporal]
            enhanced_parts.append("TIME: " + " ".join(temp_texts))
        
        # Add negations
        negations = [c for c in relevant_conditions if c.get('category') == 'negations']
        if negations:
            neg_texts = [c.get('text', '') for c in negations]
            enhanced_parts.append("NOT: " + " OR ".join(neg_texts))
        
        return " | ".join(enhanced_parts)
    
    def _analyze_relevance(self, document: Any, query: str, memory_state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze why a document is relevant"""
        doc_text = self._extract_text(document).lower()
        query_lower = query.lower()
        
        factors = {
            'query_match': 0,
            'condition_match': 0,
            'hard_constraint_satisfaction': 0,
            'preference_alignment': 0,
            'temporal_relevance': 0,
            'negation_compliance': 1  # Start with 1, reduce if violations found
        }
        
        # Query matching
        query_words = set(query_lower.split())
        doc_words = set(doc_text.split())
        query_overlap = len(query_words & doc_words)
        factors['query_match'] = query_overlap / len(query_words) if query_words else 0
        
        # Condition matching
        conditions = memory_state.get('conditions', [])
        
        for condition in conditions:
            condition_text = condition.get('text', '').lower()
            category = condition.get('category', '')
            
            if condition_text in doc_text:
                if category == 'hard_constraints':
                    factors['hard_constraint_satisfaction'] += 1
                elif category == 'soft_preferences':
                    factors['preference_alignment'] += 0.5
                elif category == 'temporal_conditions':
                    factors['temporal_relevance'] += 0.3
                elif category == 'negations':
                    factors['negation_compliance'] -= 0.5  # Penalty for containing negated content
        
        return factors
    
    def _rerank_with_conditions(self, documents: List[Dict[str, Any]], 
                               memory_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Re-rank documents based on condition satisfaction"""
        conditions = memory_state.get('conditions', [])
        
        if not conditions:
            return documents
        
        # Calculate condition-based scores
        for doc in documents:
            relevance = doc.get('relevance_factors', {})
            
            # Calculate condition score
            condition_score = 0
            
            # Hard constraints (highest weight)
            condition_score += relevance.get('hard_constraint_satisfaction', 0) * 10
            
            # Preferences (medium weight)
            condition_score += relevance.get('preference_alignment', 0) * 5
            
            # Temporal relevance (medium weight)
            condition_score += relevance.get('temporal_relevance', 0) * 3
            
            # Negation compliance (penalty for violations)
            condition_score *= relevance.get('negation_compliance', 1)
            
            # Combine with original retrieval score
            original_score = doc.get('score', 0)
            combined_score = (1 - self.condition_weight) * original_score + self.condition_weight * condition_score
            
            doc['condition_score'] = condition_score
            doc['combined_score'] = combined_score
        
        # Sort by combined score
        documents.sort(key=lambda x: x.get('combined_score', 0), reverse=True)
        
        # Update ranks
        for i, doc in enumerate(documents):
            doc['final_rank'] = i + 1
        
        return documents
    
    def _simcse_cosine_search(self, query_embedding, top_k: int):
        """SimCSE模型的余弦相似度搜索 - 与原论文对齐"""
        import numpy as np
        
        if self.document_index is None or not hasattr(self, 'document_embeddings'):
            # Fallback to FAISS search
            if isinstance(query_embedding, list):
                query_embedding = np.array(query_embedding, dtype='float32')
            faiss.normalize_L2(query_embedding)
            return self.document_index.search(query_embedding.astype('float32'), top_k)
        
        # 计算余弦相似度
        if isinstance(query_embedding, list):
            query_embedding = np.array(query_embedding, dtype='float32')
        
        # 归一化查询向量
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        
        # 获取文档嵌入（需要在索引时保存）
        doc_embeddings = self.document_embeddings
        doc_norms = doc_embeddings / np.linalg.norm(doc_embeddings, axis=1, keepdims=True)
        
        # 计算余弦相似度
        similarities = np.dot(doc_norms, query_norm.T).flatten()
        
        # 获取top_k结果
        top_indices = np.argsort(similarities)[::-1][:top_k]
        top_scores = similarities[top_indices]
        
        # 返回与FAISS相同的格式
        scores = [top_scores.tolist()]
        indices = [top_indices.tolist()]
        
        return scores, indices
    
    def _extract_text(self, document: Any) -> str:
        """Extract text from document"""
        if isinstance(document, dict):
            return document.get('text', document.get('content', ''))
        else:
            return str(document)
    
    def _text_based_search(self, query: str, top_k: int) -> Tuple[List[List[float]], List[List[int]]]:
        """
        Text-based search using keyword matching when embeddings are not available
        Returns scores and indices in the same format as FAISS search
        """
        query_words = set(query.lower().split())
        
        # Calculate simple keyword-based scores for each document
        doc_scores = []
        for i, doc in enumerate(self.documents):
            doc_text = self._extract_text(doc).lower()
            doc_words = set(doc_text.split())
            
            # Calculate overlap score
            overlap = len(query_words & doc_words)
            total_words = len(query_words)
            score = overlap / total_words if total_words > 0 else 0
            
            # MAJOR BOOST for exact function/identifier matches
            for query_word in query_words:
                if len(query_word) > 3 and ('_' in query_word or query_word.isidentifier()):
                    # This looks like a function/variable name
                    if query_word in doc_text:
                        score += 2.0  # Very high boost for exact identifier match
                        break
            
            # Boost score for exact phrase matches
            if query.lower() in doc_text:
                score += 0.5
            
            # Boost score for title matches (if available)
            if isinstance(doc, dict):
                title = doc.get('title', '').lower()
                if any(word in title for word in query_words):
                    score += 0.3
            
            doc_scores.append((score, i))
        
        # Sort by score (descending) and get top_k
        doc_scores.sort(key=lambda x: x[0], reverse=True)
        top_results = doc_scores[:top_k]
        
        # Extract scores and indices
        scores = [result[0] for result in top_results]
        indices = [result[1] for result in top_results]
        
        # Return in FAISS format (list of lists)
        return [scores], [indices]

    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the current index"""
        index_type = "Text-based" if getattr(self, 'use_text_fallback', False) else "FAISS IndexFlatIP"
        embedding_model = self.embedding_model_name if self.embedding_model else "None (text-only)"
        
        return {
            "total_documents": len(self.documents),
            "embedding_dimension": self.embedding_dim,
            "index_type": index_type,
            "embedding_model": embedding_model,
            "has_index": self.document_index is not None or getattr(self, 'use_text_fallback', False),
            "retrieval_mode": "semantic" if self.embedding_model else "keyword-based"
        }