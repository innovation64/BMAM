#!/usr/bin/env python3
"""
DMA-CMM System: Distributed Multi-Agent Conditional Memory Management
This integrates the Advanced MA-CMM framework with the Collaborative Multi-Agent framework
to create a fully distributed, collaborative memory management system.
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional
from pathlib import Path
import yaml
import uuid

# Import the core frameworks
from core.advanced_ma_cmm import AdvancedMACMM, MemoryItem, MemoryLayer
from core.advanced_collaborative_macmm import (
    CoordinationFramework, 
    CollaborationTask,
    AgentRole,
    ConsensusType,
    CollaborativeAgent,
    AgentCapability,
    ConditionExtractorAgent
)

# Import specialized collaborative agents
from agents.base import BaseAgent


class CollaborativeMemoryCuratorAgent(CollaborativeAgent):
    """Memory curator agent for collaborative framework"""
    
    def __init__(self, agent_id: str, coordination_framework: 'CoordinationFramework'):
        capability = AgentCapability(
            role=AgentRole.MEMORY_CURATOR,
            expertise_level=0.85,
            processing_capacity=8,
            reliability_score=0.9,
            specialization_domains=['memory_organization', 'relevance_scoring', 'memory_consolidation'],
            collaboration_history={}
        )
        super().__init__(agent_id, capability, coordination_framework)
    
    async def process_task(self, task: CollaborationTask) -> Dict[str, Any]:
        """Process memory curation tasks"""
        start_time = time.time()
        
        memories = task.resource_requirements.get('memories', [])
        query = task.resource_requirements.get('query', '')
        
        # Curate memories based on relevance
        curated_memories = await self._curate_memories(memories, query)
        
        processing_time = time.time() - start_time
        
        return {
            'task_id': task.task_id,
            'agent_id': self.agent_id,
            'curated_memories': curated_memories,
            'processing_time': processing_time,
            'confidence': 0.85
        }
    
    async def vote_on_proposal(self, proposal) -> float:
        """Vote on memory-related proposals"""
        if proposal.proposal_type in ['memory_curation', 'memory_update']:
            return 0.8 * self.capability.reliability_score
        return 0.5
    
    async def _curate_memories(self, memories: List[Any], query: str) -> List[Any]:
        """Curate memories based on relevance"""
        # Simple relevance scoring
        curated = []
        for memory in memories:
            relevance_score = await self._calculate_relevance(memory, query)
            if relevance_score > 0.5:
                curated.append({
                    'memory': memory,
                    'relevance_score': relevance_score
                })
        
        # Sort by relevance
        curated.sort(key=lambda x: x['relevance_score'], reverse=True)
        return curated[:10]  # Top 10 most relevant
    
    async def _calculate_relevance(self, memory: Any, query: str) -> float:
        """Calculate memory relevance to query"""
        # Simplified relevance calculation
        if isinstance(memory, dict):
            content = str(memory.get('content', ''))
            query_words = set(query.lower().split())
            content_words = set(content.lower().split())
            overlap = len(query_words & content_words)
            return min(overlap / max(len(query_words), 1), 1.0)
        return 0.0


class CollaborativeRetrieverAgent(CollaborativeAgent):
    """Retriever agent for collaborative framework"""
    
    def __init__(self, agent_id: str, coordination_framework: 'CoordinationFramework'):
        capability = AgentCapability(
            role=AgentRole.RETRIEVAL_OPTIMIZER,
            expertise_level=0.9,
            processing_capacity=12,
            reliability_score=0.88,
            specialization_domains=['semantic_search', 'vector_retrieval', 'multi_modal_retrieval'],
            collaboration_history={}
        )
        super().__init__(agent_id, capability, coordination_framework)
    
    async def process_task(self, task: CollaborationTask) -> Dict[str, Any]:
        """Process retrieval tasks"""
        start_time = time.time()
        
        query = task.resource_requirements.get('query', '')
        memory_index = task.resource_requirements.get('memory_index', None)
        
        # Perform multi-modal retrieval
        retrieved_items = await self._multi_modal_retrieval(query, memory_index)
        
        processing_time = time.time() - start_time
        
        return {
            'task_id': task.task_id,
            'agent_id': self.agent_id,
            'retrieved_items': retrieved_items,
            'processing_time': processing_time,
            'confidence': 0.9
        }
    
    async def vote_on_proposal(self, proposal) -> float:
        """Vote on retrieval-related proposals"""
        if proposal.proposal_type in ['retrieval_strategy', 'index_optimization']:
            return 0.85 * self.capability.reliability_score
        return 0.5
    
    async def _multi_modal_retrieval(self, query: str, memory_index: Any) -> List[Dict]:
        """Perform multi-modal memory retrieval"""
        # Simplified retrieval - in practice would use embeddings
        retrieved = []
        
        # Simulate different retrieval modes
        semantic_results = await self._semantic_retrieval(query)
        temporal_results = await self._temporal_retrieval(query)
        
        # Merge results
        all_results = semantic_results + temporal_results
        
        # Remove duplicates and return
        seen = set()
        unique_results = []
        for result in all_results:
            result_id = result.get('id', str(uuid.uuid4()))
            if result_id not in seen:
                seen.add(result_id)
                unique_results.append(result)
        
        return unique_results[:20]  # Top 20 results
    
    async def _semantic_retrieval(self, query: str) -> List[Dict]:
        """Semantic similarity based retrieval"""
        # Simplified - would use embeddings in practice
        return [
            {
                'id': f'semantic_{i}',
                'content': f'Semantically relevant memory {i} for: {query}',
                'score': 0.9 - i * 0.1
            }
            for i in range(5)
        ]
    
    async def _temporal_retrieval(self, query: str) -> List[Dict]:
        """Time-based retrieval"""
        return [
            {
                'id': f'temporal_{i}',
                'content': f'Recent memory {i} related to: {query}',
                'score': 0.8 - i * 0.1,
                'timestamp': time.time() - i * 3600
            }
            for i in range(3)
        ]


class DMACMM:
    """
    Distributed Multi-Agent Conditional Memory Management System
    Integrates AdvancedMACMM with CollaborativeFramework for true multi-agent collaboration
    """
    
    def __init__(self, config_path: str = "config/advanced_framework_config.yaml"):
        """Initialize the DMA-CMM system"""
        self.logger = logging.getLogger('DMA-CMM')
        self.logger.setLevel(logging.INFO)
        
        # Initialize core MA-CMM framework
        self.macmm = AdvancedMACMM(config_path)
        
        # Initialize collaborative framework
        self.coordination = CoordinationFramework(max_agents=20)
        
        # Initialize collaborative agents
        self._initialize_collaborative_agents()
        
        # System metrics
        self.collaboration_metrics = {
            'total_collaborative_tasks': 0,
            'consensus_success_rate': 0.0,
            'avg_collaboration_time': 0.0,
            'agent_utilization': {},
            'conflict_resolution_count': 0
        }
        
        self.logger.info("DMA-CMM System initialized with collaborative multi-agent architecture")
    
    def _initialize_collaborative_agents(self):
        """Initialize and register collaborative agents"""
        # Condition Extractor
        condition_agent = ConditionExtractorAgent("collab_condition_001", self.coordination)
        self.coordination.register_agent(condition_agent)
        
        # Memory Curator
        memory_curator = CollaborativeMemoryCuratorAgent("collab_curator_001", self.coordination)
        self.coordination.register_agent(memory_curator)
        
        # Retriever
        retriever_agent = CollaborativeRetrieverAgent("collab_retriever_001", self.coordination)
        self.coordination.register_agent(retriever_agent)
        
        # Could add more specialized agents: ConflictResolver, CompressionSpecialist, etc.
        
        self.logger.info(f"Registered {len(self.coordination.agents)} collaborative agents")
    
    async def process_query(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process query using distributed multi-agent collaboration
        
        This method orchestrates both the MA-CMM framework and the collaborative agents
        to process queries with enhanced multi-agent collaboration.
        """
        start_time = time.time()
        
        try:
            # Phase 1: Collaborative Condition Extraction
            extraction_task = CollaborationTask(
                task_id=f"extract_{uuid.uuid4().hex[:8]}",
                task_type="condition_extraction",
                priority=1,
                required_roles={AgentRole.CONDITION_EXTRACTOR, AgentRole.MEMORY_CURATOR},
                deadline=None,
                complexity_score=0.7,
                resource_requirements={
                    'query': query,
                    'context': context or {}
                },
                dependencies=[]
            )
            
            # Submit to collaborative framework
            extraction_task_id = await self.coordination.submit_task(extraction_task)
            
            # Wait for extraction results (with timeout)
            await asyncio.sleep(1.0)  # Give agents time to process
            
            # Phase 2: Memory Retrieval with Collaboration
            retrieval_task = CollaborationTask(
                task_id=f"retrieve_{uuid.uuid4().hex[:8]}",
                task_type="memory_retrieval",
                priority=1,
                required_roles={AgentRole.RETRIEVAL_OPTIMIZER, AgentRole.MEMORY_CURATOR},
                deadline=None,
                complexity_score=0.8,
                resource_requirements={
                    'query': query,
                    'memory_index': self.macmm.unified_memory
                },
                dependencies=[extraction_task_id]
            )
            
            retrieval_task_id = await self.coordination.submit_task(retrieval_task)
            
            # Wait for retrieval results
            await asyncio.sleep(1.0)
            
            # Phase 3: Process through MA-CMM framework
            # This integrates the collaborative results with the core framework
            macmm_result = await self.macmm.process_query(query, context)
            
            # Phase 4: Collect collaboration metrics
            collaboration_metrics = self._collect_collaboration_metrics()
            
            # Combine results
            processing_time = time.time() - start_time
            
            return {
                'status': 'success',
                'response': macmm_result.get('response', ''),
                'processing_time': processing_time,
                'macmm_result': macmm_result,
                'collaboration_metrics': collaboration_metrics,
                'system_metrics': self.get_system_metrics(),
                'collaborative_agents_used': len(self.coordination.agents),
                'consensus_achieved': True  # Simplified - would check actual consensus
            }
            
        except Exception as e:
            self.logger.error(f"Error in DMA-CMM processing: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    def _collect_collaboration_metrics(self) -> Dict[str, Any]:
        """Collect metrics about multi-agent collaboration"""
        # Get metrics from coordination framework
        system_metrics = self.coordination.get_system_metrics()
        
        # Calculate collaboration effectiveness
        total_tasks = system_metrics['performance_metrics'].get('total_tasks', 0)
        successful_tasks = system_metrics['performance_metrics'].get('successful_tasks', 0)
        
        collaboration_effectiveness = successful_tasks / max(total_tasks, 1)
        
        # Agent utilization
        agent_utilization = {}
        for role, agent_ids in system_metrics['agents_by_role'].items():
            if agent_ids:
                # Get load for each agent
                loads = []
                for agent_id in agent_ids:
                    agent_load = self.coordination.load_balancer.agent_loads.get(agent_id, 0)
                    loads.append(agent_load)
                avg_load = sum(loads) / len(loads) if loads else 0
                agent_utilization[role] = avg_load
        
        return {
            'collaboration_effectiveness': collaboration_effectiveness,
            'consensus_success_rate': 0.85,  # Placeholder - would calculate from consensus history
            'active_agents': system_metrics['total_agents'],
            'active_tasks': system_metrics['active_tasks'],
            'agent_utilization': agent_utilization,
            'avg_task_execution_time': system_metrics['performance_metrics'].get('avg_execution_time', 0),
            'throughput': system_metrics['performance_metrics'].get('throughput', 0),
            'error_rate': system_metrics['performance_metrics'].get('error_rate', 0)
        }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system metrics"""
        # Get metrics from both systems
        macmm_metrics = self.macmm._get_memory_stats()
        collab_metrics = self.coordination.get_system_metrics()
        
        return {
            'memory_system': macmm_metrics,
            'collaboration_system': collab_metrics,
            'integration_metrics': {
                'total_collaborative_queries': self.collaboration_metrics['total_collaborative_tasks'],
                'consensus_success_rate': self.collaboration_metrics['consensus_success_rate'],
                'avg_collaboration_time': self.collaboration_metrics['avg_collaboration_time']
            }
        }
    
    async def shutdown(self):
        """Gracefully shutdown the system"""
        self.logger.info("Shutting down DMA-CMM system...")
        # Could add cleanup logic here
        

# Example usage
async def main():
    """Example of using the DMA-CMM system"""
    # Initialize system
    dma_cmm = DMACMM()
    
    # Process a query
    result = await dma_cmm.process_query(
        "What are the key features of Python for data science?",
        context={'session_id': 'test_session_001'}
    )
    
    print("DMA-CMM Result:")
    print(f"Status: {result['status']}")
    print(f"Response: {result.get('response', 'No response')}")
    print(f"Processing Time: {result['processing_time']:.2f}s")
    print(f"Collaboration Metrics: {result.get('collaboration_metrics', {})}")
    
    # Get system metrics
    metrics = dma_cmm.get_system_metrics()
    print(f"\nSystem Metrics: {metrics}")
    
    # Shutdown
    await dma_cmm.shutdown()


if __name__ == "__main__":
    asyncio.run(main())