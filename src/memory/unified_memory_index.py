"""
Unified Memory Index - Bridges ConditionalMemory storage with semantic retrieval

This module solves the core architectural problem where conditions are stored
in ConditionalMemory but not indexed for semantic retrieval, causing the
"automatic retrieval returns 0 results" issue.
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json
import uuid
from dataclasses import dataclass

# Import existing memory components
from .condition_memory import ConditionalMemory

# Optional FAISS for semantic search
try:
    import faiss
    from sentence_transformers import SentenceTransformer
    import numpy as np
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

@dataclass
class MemoryItem:
    """Unified memory item that can be stored and retrieved"""
    id: str
    text: str
    category: str
    importance_score: float
    source_turn: int
    confidence: str
    timestamp: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None

class UnifiedMemoryIndex:
    """Unified memory system that bridges storage and retrieval"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Initialize the existing conditional memory
        self.conditional_memory = ConditionalMemory()
        
        # Initialize semantic search components
        self.embedding_model = None
        self.embedding_dim = 384
        self.faiss_index = None
        self.indexed_items = []  # List of MemoryItem objects
        self.text_index = {}  # Fallback text-based index
        
        # Initialize embedding model
        if FAISS_AVAILABLE:
            self._init_embedding_model()
        
        # Memory layers for cross-layer search
        self.memory_layers = {
            'working_memory': [],
            'short_term_memory': [],
            'long_term_memory': [],
            'episodic_memory': []
        }
        
    def _init_embedding_model(self):
        """Initialize embedding model with fallbacks"""
        models_to_try = [
            'Qwen/Qwen3-Embedding-0.6B',
            'sentence-transformers/all-MiniLM-L6-v2',
            'all-MiniLM-L6-v2'
        ]
        
        for model_name in models_to_try:
            try:
                self.embedding_model = SentenceTransformer(model_name)
                self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
                print(f"✅ Loaded embedding model: {model_name}")
                return
            except Exception as e:
                print(f"Failed to load {model_name}: {e}")
                continue
                
        print("❌ No embedding model available - using text fallback")
    
    def add_memory_item(self, text: str, category: str, importance_score: float = 0.5,
                       source_turn: int = -1, confidence: str = "medium",
                       metadata: Optional[Dict[str, Any]] = None,
                       memory_layer: str = "short_term_memory", session_id: str = None) -> str:
        """Add a memory item to both storage and index
        
        This is the key function that solves the storage-retrieval disconnect
        """
        # Create unified memory item
        item_id = str(uuid.uuid4())
        
        # Ensure metadata includes session_id for isolation
        final_metadata = metadata or {}
        if session_id:
            final_metadata['session_id'] = session_id
            
        memory_item = MemoryItem(
            id=item_id,
            text=text,
            category=category,
            importance_score=importance_score,
            source_turn=source_turn,
            confidence=confidence,
            timestamp=datetime.now().isoformat(),
            metadata=final_metadata
        )
        
        # Store in conditional memory (existing system)
        condition_data = {
            'text': text,
            'source_turn': source_turn,
            'confidence': confidence,
            'category': category
        }
        self.conditional_memory.add_condition(condition_data, category, importance_score)
        
        # Store in appropriate memory layer
        if memory_layer in self.memory_layers:
            self.memory_layers[memory_layer].append(memory_item)
        
        # Index for semantic retrieval
        self._index_memory_item(memory_item)
        
        # Add to text index (fallback)
        self.text_index[item_id] = memory_item
        
        return item_id
    
    def _index_memory_item(self, memory_item: MemoryItem):
        """Index a memory item for semantic retrieval"""
        if self.embedding_model is None:
            print(f"❌ No embedding model - cannot index: {memory_item.text}")
            return
            
        try:
            # Generate embedding
            embedding = self.embedding_model.encode([memory_item.text])
            memory_item.embedding = embedding[0].tolist()
            
            # Add to FAISS index
            if self.faiss_index is None:
                self.faiss_index = faiss.IndexFlatIP(self.embedding_dim)  # Inner product
            
            self.faiss_index.add(embedding.astype('float32'))
            self.indexed_items.append(memory_item)
            
        except Exception as e:
            print(f"❌ Failed to index memory item: {e}")
            import traceback
            traceback.print_exc()
    
    def retrieve_memories(self, query: str, top_k: int = 10, 
                         memory_layers: Optional[List[str]] = None,
                         categories: Optional[List[str]] = None,
                         session_id: Optional[str] = None) -> List[MemoryItem]:
        """Unified memory retrieval across all layers and storage systems
        
        This solves the core problem of fragmented memory search
        """
        results = []
        
        # Search semantic index first
        if self.embedding_model and self.faiss_index and len(self.indexed_items) > 0:
            semantic_results = self._semantic_search(query, top_k)
            results.extend(semantic_results)
        
        # Search text index as fallback
        text_results = self._text_search(query, top_k)
        results.extend(text_results)
        
        # Search memory layers
        if memory_layers is None:
            memory_layers = list(self.memory_layers.keys())
            
        for layer_name in memory_layers:
            layer_results = self._search_memory_layer(query, layer_name, categories)
            results.extend(layer_results)
        
        # Filter by session_id if provided
        if session_id:
            results = [item for item in results 
                      if item.metadata.get('session_id') == session_id]
        
        # Deduplicate and rank by importance/relevance
        unique_results = self._deduplicate_and_rank(results, query)
        
        return unique_results[:top_k]
    
    def _semantic_search(self, query: str, top_k: int) -> List[MemoryItem]:
        """Semantic search using FAISS"""
        if not self.embedding_model or not self.faiss_index:
            return []
            
        try:
            # Encode query
            query_embedding = self.embedding_model.encode([query])
            
            # Search FAISS index
            scores, indices = self.faiss_index.search(
                query_embedding.astype('float32'), 
                min(top_k, len(self.indexed_items))
            )
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(self.indexed_items):
                    item = self.indexed_items[idx]
                    item.metadata['semantic_score'] = float(score)
                    results.append(item)
            
            return results
            
        except Exception as e:
            print(f"Semantic search failed: {e}")
            return []
    
    def _text_search(self, query: str, top_k: int) -> List[MemoryItem]:
        """Text-based search fallback"""
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        results = []
        for item in self.text_index.values():
            text_lower = item.text.lower()
            text_words = set(text_lower.split())
            
            # Calculate word overlap score
            overlap = len(query_words.intersection(text_words))
            if overlap > 0:
                item.metadata['text_score'] = overlap / len(query_words)
                results.append(item)
        
        return sorted(results, key=lambda x: x.metadata.get('text_score', 0), reverse=True)[:top_k]
    
    def _search_memory_layer(self, query: str, layer_name: str, 
                           categories: Optional[List[str]] = None) -> List[MemoryItem]:
        """Search specific memory layer"""
        if layer_name not in self.memory_layers:
            return []
            
        layer_items = self.memory_layers[layer_name]
        if categories:
            layer_items = [item for item in layer_items if item.category in categories]
        
        # Simple text matching for now
        query_lower = query.lower()
        results = []
        
        for item in layer_items:
            if query_lower in item.text.lower():
                item.metadata['layer_match'] = layer_name
                results.append(item)
        
        return results
    
    def _deduplicate_and_rank(self, results: List[MemoryItem], query: str) -> List[MemoryItem]:
        """Remove duplicates and rank by combined score"""
        seen_ids = set()
        unique_results = []
        
        for item in results:
            if item.id not in seen_ids:
                seen_ids.add(item.id)
                
                # Calculate combined score
                semantic_score = item.metadata.get('semantic_score', 0)
                text_score = item.metadata.get('text_score', 0)
                importance_score = item.importance_score
                
                combined_score = (semantic_score * 0.4 + 
                                text_score * 0.3 + 
                                importance_score * 0.3)
                
                item.metadata['combined_score'] = combined_score
                unique_results.append(item)
        
        return sorted(unique_results, key=lambda x: x.metadata.get('combined_score', 0), reverse=True)
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics"""
        stats = {
            'conditional_memory': self.conditional_memory.get_memory_stats(),
            'indexed_items': len(self.indexed_items),
            'text_index_size': len(self.text_index),
            'faiss_index_size': self.faiss_index.ntotal if self.faiss_index else 0,
            'memory_layers': {
                layer: len(items) for layer, items in self.memory_layers.items()
            },
            'total_items': sum(len(items) for items in self.memory_layers.values())
        }
        
        return stats
    
    def add_biographical_fact(self, fact_text: str, importance_score: float = 0.8) -> str:
        """Add biographical facts with high importance
        
        This addresses the importance scoring problem for basic facts
        """
        return self.add_memory_item(
            text=fact_text,
            category="biographical_facts",
            importance_score=importance_score,
            confidence="high",
            memory_layer="long_term_memory"
        )
    
    def bulk_add_facts(self, facts: List[Tuple[str, str, float]]) -> List[str]:
        """Bulk add facts (text, category, importance)"""
        ids = []
        for text, category, importance in facts:
            item_id = self.add_memory_item(text, category, importance)
            ids.append(item_id)
        return ids