from typing import Dict, Any, List, Optional
from .base import BaseAgent
from .condition_extractor import ConditionExtractorAgent
from .memory_manager import MemoryManagerAgent
from .conflict_resolver import ConflictResolverAgent
from .memory_compressor import MemoryCompressorAgent
from .retriever import RetrieverAgent
from .generator import GeneratorAgent
import asyncio
import time

class OrchestratorAgent(BaseAgent):
    """Main orchestrator that coordinates all agents in the MA-CMM system"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__("Orchestrator", config)
        self.agents = {}
        self.conversation_history = []
        self.session_id = None
        self.performance_metrics = {
            "total_queries": 0,
            "average_response_time": 0,
            "memory_compressions": 0,
            "conflicts_resolved": 0
        }
        
        # Initialize all agents
        self._initialize_agents(config)
    
    def _initialize_agents(self, config: Dict[str, Any]):
        """Initialize all sub-agents"""
        api_client = config.get('api_client')
        agent_configs = config.get('agent_configs', {})
        
        self.agents = {
            'extractor': ConditionExtractorAgent(
                config=config  # Pass full config instead of api_client
            ),
            'memory': MemoryManagerAgent(
                config=agent_configs.get('memory', {})
            ),
            'resolver': ConflictResolverAgent(
                config=config
            ),
            'compressor': MemoryCompressorAgent(
                config=agent_configs.get('compressor', {})
            ),
            'retriever': RetrieverAgent(
                config=agent_configs.get('retriever', {})
            ),
            'generator': GeneratorAgent(
                api_client=api_client,
                config=agent_configs.get('generator', {})
            )
        }
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main processing pipeline for user queries
        
        Args:
            input_data: Should contain:
                - query: User query
                - session_id: Session identifier
                - documents: Available documents (optional)
                - action: 'query', 'initialize', 'reset'
        """
        action = input_data.get('action', 'query')
        
        if action == 'initialize':
            return await self._initialize_session(input_data)
        elif action == 'reset':
            return await self._reset_session()
        elif action == 'query':
            return await self._process_query(input_data)
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}
    
    async def _initialize_session(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize a new session"""
        self.session_id = input_data.get('session_id', f"session_{int(time.time())}")
        documents = input_data.get('documents', [])
        
        # Initialize retriever with documents if provided
        if documents:
            await self.agents['retriever'].process({
                'action': 'index',
                'documents': documents
            })
        
        # Reset conversation history
        self.conversation_history = []
        
        return {
            "status": "success",
            "session_id": self.session_id,
            "documents_indexed": len(documents),
            "message": "Session initialized successfully"
        }
    
    async def _reset_session(self) -> Dict[str, Any]:
        """Reset current session"""
        # Reset all agents
        for agent in self.agents.values():
            agent.reset()
        
        # Clear conversation history
        self.conversation_history = []
        
        return {
            "status": "success",
            "message": "Session reset successfully"
        }
    
    async def _process_query(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a user query through the complete pipeline"""
        start_time = time.time()
        query = input_data.get('query', '')
        
        if not query:
            return {"status": "error", "message": "Empty query provided"}
        
        try:
            # Step 1: Extract conditions from dialogue history + current query
            if self.config.get('use_simple_extraction', False):
                # Use basic extraction for ablation study
                condition_result = await self._extract_conditions_basic(query)
            else:
                condition_result = await self._extract_conditions(query)
            
            # Step 2: Update memory with new conditions
            memory_result = await self._update_memory(condition_result)
            
            # Step 3: Resolve conflicts if any detected and conflict resolution enabled
            if memory_result.get('conflicts_detected') and self.config.get('enable_conflict_resolution', True):
                conflict_result = await self._resolve_conflicts(memory_result)
                self.logger.info(f"Conflict resolution enabled - resolved {conflict_result.get('resolved_conflicts', 0)} conflicts")
            else:
                conflict_result = {"resolved_conflicts": 0}
                if not self.config.get('enable_conflict_resolution', True):
                    self.logger.info("Conflict resolution disabled for ablation study")
            
            # Step 4: Check if memory compression is needed and enabled
            if memory_result.get('needs_compression') and self.config.get('enable_memory_compression', True):
                compression_result = await self._compress_memory()
                self.performance_metrics["memory_compressions"] += 1
                self.logger.info("Memory compression enabled and executed")
            else:
                compression_result = {"compressed": 0}
                if not self.config.get('enable_memory_compression', True):
                    self.logger.info("Memory compression disabled for ablation study")
            
            # Step 5: Retrieve relevant documents if enabled
            if self.config.get('enable_document_retrieval', True):
                retrieval_result = await self._retrieve_documents(query)
                self.logger.info(f"Document retrieval enabled - retrieved {retrieval_result.get('total_retrieved', 0)} documents")
            else:
                retrieval_result = {"retrieved_documents": [], "total_retrieved": 0}
                self.logger.info("Document retrieval disabled for ablation study")
            
            # Step 6: Generate final response
            generation_result = await self._generate_response(
                query, retrieval_result, memory_result
            )
            
            # Update conversation history
            self.conversation_history.append({
                'role': 'user',
                'content': query,
                'timestamp': time.time()
            })
            self.conversation_history.append({
                'role': 'assistant',
                'content': generation_result.get('response', ''),
                'timestamp': time.time()
            })
            
            # Update performance metrics
            end_time = time.time()
            response_time = end_time - start_time
            self.performance_metrics["total_queries"] += 1
            self.performance_metrics["conflicts_resolved"] += conflict_result.get("resolved_conflicts", 0)
            
            # Update average response time
            total_queries = self.performance_metrics["total_queries"]
            current_avg = self.performance_metrics["average_response_time"]
            self.performance_metrics["average_response_time"] = (
                (current_avg * (total_queries - 1) + response_time) / total_queries
            )
            
            return {
                "status": "success",
                "response": generation_result.get('response', ''),
                "pipeline_results": {
                    "conditions_extracted": condition_result.get('total_conditions', 0),
                    "memory_updated": memory_result.get('added_conditions', 0),
                    "conflicts_resolved": conflict_result.get('resolved_conflicts', 0),
                    "memory_compressed": compression_result.get('compressed', 0),
                    "documents_retrieved": retrieval_result.get('total_retrieved', 0),
                    "response_quality": generation_result.get('quality_analysis', {})
                },
                "performance": {
                    "response_time": response_time,
                    "total_queries": self.performance_metrics["total_queries"]
                }
            }
        
        except Exception as e:
            self.logger.error(f"Error in query processing: {e}")
            return {
                "status": "error",
                "message": f"Failed to process query: {str(e)}",
                "error_type": type(e).__name__
            }
    
    async def _extract_conditions(self, query: str) -> Dict[str, Any]:
        """Extract conditions from current query and conversation history"""
        return await self.agents['extractor'].process({
            'dialogue_history': self.conversation_history,
            'current_query': query
        })
    
    async def _extract_conditions_basic(self, query: str) -> Dict[str, Any]:
        """Basic condition extraction for ablation study"""
        # Simple keyword-based extraction
        basic_conditions = []
        
        # Extract some basic patterns
        import re
        
        # Look for simple requirements
        requirement_patterns = [
            r'need (\w+)',
            r'want (\w+)',
            r'prefer (\w+)',
            r'must have (\w+)',
            r'should be (\w+)'
        ]
        
        condition_count = 0
        for pattern in requirement_patterns:
            matches = re.findall(pattern, query.lower())
            for match in matches:
                basic_conditions.append({
                    'id': f'basic_cond_{condition_count}',
                    'text': f'requirement: {match}',
                    'category': 'soft_preferences',
                    'source_turn': len(self.conversation_history),
                    'extraction_method': 'basic'
                })
                condition_count += 1
        
        # Always return at least one condition to simulate some extraction
        if not basic_conditions:
            basic_conditions.append({
                'id': 'basic_cond_default',
                'text': 'general query requirement',
                'category': 'soft_preferences',
                'source_turn': len(self.conversation_history),
                'extraction_method': 'basic'
            })
            condition_count = 1
        
        return {
            'status': 'success',
            'total_conditions': condition_count,
            'conditions': {'soft_preferences': basic_conditions},
            'extraction_method': 'basic'
        }
    
    async def _update_memory(self, condition_result: Dict[str, Any]) -> Dict[str, Any]:
        """Update memory with extracted conditions"""
        conditions = condition_result.get('conditions', {})
        turn_id = len(self.conversation_history)
        
        return await self.agents['memory'].process({
            'action': 'add',
            'conditions': conditions,
            'turn_id': turn_id
        })
    
    async def _resolve_conflicts(self, memory_result: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve detected conflicts"""
        conflicts = memory_result.get('conflicts', [])
        memory_state = self.agents['memory'].get_memory_state()
        
        return await self.agents['resolver'].process({
            'conflicts': conflicts,
            'memory_state': memory_state,
            'use_reasoning': True
        })
    
    async def _compress_memory(self) -> Dict[str, Any]:
        """Compress memory when it gets too large"""
        # Get all conditions from memory
        all_conditions = self.agents['memory'].memory.get_all_conditions()
        
        compression_result = await self.agents['compressor'].process({
            'conditions': all_conditions,
            'target_reduction': 0.3,  # Remove 30% of conditions
            'strategy': 'hybrid',
            'preserve_categories': ['hard_constraints']
        })
        
        # Apply compression results to memory
        if compression_result.get('status') == 'success':
            removed_ids = compression_result.get('removed_conditions', [])
            for condition_id in removed_ids:
                self.agents['memory'].memory.remove_condition(condition_id)
        
        return compression_result
    
    async def _retrieve_documents(self, query: str) -> Dict[str, Any]:
        """Retrieve relevant documents"""
        memory_state = self.agents['memory'].get_memory_state()
        return await self.agents['retriever'].process({
            'action': 'retrieve',
            'query': query,
            'memory_state': memory_state,
            'top_k': 10
        })
    
    async def _generate_response(self, query: str, retrieval_result: Dict[str, Any], 
                               memory_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate final response"""
        documents = retrieval_result.get('retrieved_documents', [])
        
        # Get both memory statistics and actual conditions
        memory_stats = self.agents['memory'].get_memory_state()
        all_conditions = self.agents['memory'].memory.get_all_conditions()
        
        # Prepare comprehensive memory state for generator
        memory_state = {
            'stats': memory_stats,
            'conditions': all_conditions,
            'total_conditions': len(all_conditions)
        }
        
        return await self.agents['generator'].process({
            'query': query,
            'retrieved_documents': documents,
            'memory_state': memory_state,
            'conversation_history': self.conversation_history[-10:]  # Last 10 turns
        })
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        agent_statuses = {}
        for name, agent in self.agents.items():
            agent_statuses[name] = agent.get_status()
        
        memory_stats = self.agents['memory'].get_memory_state()
        retrieval_stats = self.agents['retriever'].get_index_stats()
        
        return {
            "session_id": self.session_id,
            "conversation_length": len(self.conversation_history),
            "agent_statuses": agent_statuses,
            "memory_statistics": memory_stats,
            "retrieval_statistics": retrieval_stats,
            "performance_metrics": self.performance_metrics
        }
    
    async def export_session_data(self) -> Dict[str, Any]:
        """Export current session data for analysis"""
        memory_data = self.agents['memory'].memory.serialize()
        
        return {
            "session_id": self.session_id,
            "conversation_history": self.conversation_history,
            "memory_data": memory_data,
            "performance_metrics": self.performance_metrics,
            "export_timestamp": time.time()
        }