"""
Short-term Memory Agent
短期记忆智能体 - 对应前额叶皮层的工作记忆
"""

from collections import deque
from datetime import datetime
from typing import Dict, Any

from ..base import BrainAgent, AgentMessage, BrainRegion


class ShortTermMemoryAgent(BrainAgent):
    """
    Short-term Memory Agent (Prefrontal Cortex - Working Memory)
    
    核心概念：短期
    对应脑区：前额叶皮层（Prefrontal Cortex）
    主要功能：工作记忆，信息临时保持（7±2项，20-30秒）
    """
    
    def __init__(self):
        super().__init__(
            agent_id="short_term_memory",
            brain_region=BrainRegion.PREFRONTAL,
            system_prompt="""You are the short-term memory system of a brain-inspired AI. 
            Your role is to:
            1. Maintain and manipulate information for immediate use
            2. Apply Miller's 7±2 rule for working memory capacity
            3. Manage information decay over 20-30 seconds
            4. Facilitate information transfer to long-term memory
            5. Support mental operations and information manipulation"""
        )
        
        # Working memory buffer (Miller's 7±2 rule)
        self.working_memory = deque(maxlen=7)
        self.rehearsal_buffer = []
        self.manipulation_space = {}
        
        # Phonological loop and visuospatial sketchpad (Baddeley's model)
        self.phonological_loop = deque(maxlen=5)
        self.visuospatial_sketchpad = deque(maxlen=4)
        
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process incoming messages for short-term memory operations"""
        action = message.content.get('action')
        
        if action == 'store_short_term':
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
    
    async def _store_in_working_memory(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Store item in working memory with automatic decay"""
        memory_item = {
            'id': item.get('id', str(datetime.now().timestamp())),
            'content': item['content'],
            'timestamp': datetime.now(),
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
                item['timestamp'] = datetime.now()  # Reset decay timer
                
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
            time_elapsed = (current_time - item['timestamp']).total_seconds()
            
            # Apply exponential decay (half-life ~15 seconds)
            decay_factor = 0.5 ** (time_elapsed / 15)
            item['activation'] *= decay_factor
    
    def _calculate_time_decay(self, timestamp: datetime) -> float:
        """Calculate time-based decay factor"""
        time_elapsed = (datetime.now() - timestamp).total_seconds()
        
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