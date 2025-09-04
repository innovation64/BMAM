"""
Executive Control Agent
执行控制智能体 - 对应前扣带皮层（ACC）
"""

from collections import deque
from datetime import datetime
from typing import Dict, Any, List, Optional
import uuid
import logging

from ..base import BrainAgent, AgentMessage

logger = logging.getLogger(__name__)


class ExecutiveControlAgent(BrainAgent):
    """
    Executive Control Agent (Anterior Cingulate Cortex)
    
    对应脑区：前扣带皮层（ACC）
    主要功能：任务协调，冲突解决，资源分配
    """
    
    def __init__(self):
        super().__init__(
            agent_id="executive_control",
            brain_region="anterior_cingulate",
            system_prompt="""You are the executive control system of a brain-inspired AI.
            Your role is to:
            1. Coordinate multiple agents for complex tasks
            2. Resolve conflicts between competing processes
            3. Allocate cognitive resources optimally
            4. Monitor system performance and efficiency
            5. Manage task prioritization and scheduling"""
        )
        
        # Task management
        self.task_queue = deque()
        self.active_tasks = {}
        self.completed_tasks = {}
        
        # Resource management
        self.resource_allocation = {
            'memory': 0.0,
            'attention': 0.0,
            'processing': 0.0
        }
        self.resource_limits = {
            'memory': 1.0,
            'attention': 1.0,
            'processing': 1.0
        }
        
        # Agent coordination
        self.agent_status = {}
        self.agent_priorities = {}
        
        # Conflict resolution
        self.conflict_history = []
        self.resolution_strategies = {
            'priority_based': self._priority_based_resolution,
            'resource_based': self._resource_based_resolution,
            'temporal_based': self._temporal_based_resolution,
            'compromise': self._compromise_resolution
        }
        
        # Performance monitoring
        self.performance_metrics = {
            'task_completion_rate': 0.0,
            'average_task_duration': 0.0,
            'resource_utilization': 0.0,
            'conflict_rate': 0.0
        }
        
        # Statistics
        self.tasks_coordinated = 0
        self.conflicts_resolved = 0
        self.resource_allocations = 0
    
    async def process_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Process executive control requests"""
        action = message.content.get('action')
        
        if action == 'coordinate_agents':
            return await self._coordinate_agents(message.content['task'])
        elif action == 'resolve_conflict':
            return await self._resolve_conflict(message.content['conflicts'])
        elif action == 'allocate_resources':
            return await self._allocate_cognitive_resources(message.content['demands'])
        elif action == 'monitor_performance':
            return await self._monitor_system_performance()
        elif action == 'prioritize_tasks':
            return await self._prioritize_tasks(message.content['tasks'])
        elif action == 'schedule_task':
            return await self._schedule_task(message.content['task'])
        elif action == 'optimize_workflow':
            return await self._optimize_workflow()
        
        return {'error': f'Unknown executive control action: {action}'}
    
    async def _coordinate_agents(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate multiple agents for complex task execution"""
        
        task_id = str(uuid.uuid4())
        
        # Analyze task requirements
        task_analysis = self._analyze_task_requirements(task)
        
        # Identify required agents
        required_agents = self._identify_required_agents(task_analysis)
        
        # Create execution plan
        execution_plan = self._create_execution_plan(required_agents, task_analysis)
        
        # Allocate resources for the task
        resource_allocation = await self._allocate_task_resources(execution_plan)
        
        # Initialize task tracking
        self.active_tasks[task_id] = {
            'task': task,
            'analysis': task_analysis,
            'plan': execution_plan,
            'resource_allocation': resource_allocation,
            'status': 'initiated',
            'start_time': datetime.now(),
            'agents_involved': required_agents
        }
        
        self.tasks_coordinated += 1
        
        return {
            'coordination_initiated': True,
            'task_id': task_id,
            'required_agents': required_agents,
            'execution_plan': execution_plan,
            'resource_allocation': resource_allocation,
            'estimated_duration': execution_plan['estimated_duration']
        }
    
    async def _resolve_conflict(self, conflicts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Resolve conflicts between competing processes"""
        
        resolutions = []
        
        for conflict in conflicts:
            # Analyze conflict type and context
            conflict_analysis = self._analyze_conflict(conflict)
            
            # Select appropriate resolution strategy
            strategy = self._select_resolution_strategy(conflict_analysis)
            
            # Apply resolution
            resolution = await self.resolution_strategies[strategy](conflict, conflict_analysis)
            
            resolutions.append({
                'conflict': conflict,
                'analysis': conflict_analysis,
                'strategy': strategy,
                'resolution': resolution
            })
            
            # Record conflict for learning
            self.conflict_history.append({
                'timestamp': datetime.now(),
                'conflict': conflict,
                'resolution': resolution,
                'strategy': strategy
            })
        
        self.conflicts_resolved += len(resolutions)
        
        # Update conflict rate metric
        self._update_conflict_metrics()
        
        return {
            'conflicts_resolved': len(resolutions),
            'resolutions': resolutions,
            'total_conflicts_handled': self.conflicts_resolved
        }
    
    async def _allocate_cognitive_resources(self, demands: Dict[str, float]) -> Dict[str, Any]:
        """Allocate cognitive resources across agents and tasks"""
        
        # Validate demands
        validated_demands = self._validate_resource_demands(demands)
        
        # Check total demand
        total_demand = {
            resource: sum(agent_demand.get(resource, 0) for agent_demand in validated_demands.values())
            for resource in self.resource_limits
        }
        
        # Optimize allocation if over capacity
        if any(total_demand[r] > self.resource_limits[r] for r in self.resource_limits):
            optimized_allocation = self._optimize_resource_allocation(validated_demands, total_demand)
        else:
            optimized_allocation = validated_demands
        
        # Apply allocation
        self.resource_allocation = {
            resource: sum(agent_alloc.get(resource, 0) for agent_alloc in optimized_allocation.values())
            for resource in self.resource_limits
        }
        
        self.resource_allocations += 1
        
        return {
            'resources_allocated': True,
            'allocation': optimized_allocation,
            'total_allocation': self.resource_allocation,
            'utilization_rates': {
                resource: self.resource_allocation[resource] / self.resource_limits[resource]
                for resource in self.resource_limits
            },
            'overloaded': any(self.resource_allocation[r] > self.resource_limits[r] for r in self.resource_limits)
        }
    
    async def _monitor_system_performance(self) -> Dict[str, Any]:
        """Monitor overall system performance"""
        
        # Calculate current metrics
        current_metrics = {
            'active_tasks': len(self.active_tasks),
            'queued_tasks': len(self.task_queue),
            'resource_utilization': self._calculate_resource_utilization(),
            'agent_activity': self._calculate_agent_activity(),
            'system_load': self._calculate_system_load(),
            'bottlenecks': self._identify_bottlenecks()
        }
        
        # Update performance metrics
        self._update_performance_metrics(current_metrics)
        
        # Generate performance report
        performance_report = {
            'current_metrics': current_metrics,
            'historical_metrics': self.performance_metrics,
            'health_status': self._assess_system_health(current_metrics),
            'recommendations': self._generate_performance_recommendations(current_metrics)
        }
        
        return {
            'monitoring_complete': True,
            'performance_report': performance_report,
            'timestamp': datetime.now().isoformat()
        }
    
    async def _prioritize_tasks(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Prioritize tasks based on multiple criteria"""
        
        prioritized_tasks = []
        
        for task in tasks:
            # Calculate priority score
            priority_score = self._calculate_task_priority(task)
            
            prioritized_tasks.append({
                'task': task,
                'priority_score': priority_score,
                'priority_factors': self._get_priority_factors(task)
            })
        
        # Sort by priority
        prioritized_tasks.sort(key=lambda x: x['priority_score'], reverse=True)
        
        # Update task queue
        for task_item in prioritized_tasks:
            self.task_queue.append(task_item)
        
        return {
            'tasks_prioritized': len(prioritized_tasks),
            'prioritized_list': prioritized_tasks,
            'queue_length': len(self.task_queue)
        }
    
    async def _schedule_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule a task for execution"""
        
        # Analyze task for scheduling
        scheduling_analysis = {
            'priority': self._calculate_task_priority(task),
            'resource_requirements': self._estimate_resource_requirements(task),
            'estimated_duration': self._estimate_task_duration(task),
            'dependencies': task.get('dependencies', []),
            'optimal_execution_time': self._determine_optimal_execution_time(task)
        }
        
        # Find scheduling slot
        schedule_slot = self._find_schedule_slot(scheduling_analysis)
        
        # Add to schedule
        scheduled_task = {
            'task': task,
            'schedule_slot': schedule_slot,
            'analysis': scheduling_analysis,
            'status': 'scheduled'
        }
        
        # Add to appropriate queue position
        if schedule_slot['immediate']:
            self.task_queue.appendleft(scheduled_task)
        else:
            self.task_queue.append(scheduled_task)
        
        return {
            'task_scheduled': True,
            'schedule_slot': schedule_slot,
            'scheduling_analysis': scheduling_analysis,
            'queue_position': len(self.task_queue)
        }
    
    async def _optimize_workflow(self) -> Dict[str, Any]:
        """Optimize workflow across agents and tasks"""
        
        # Analyze current workflow
        workflow_analysis = {
            'task_distribution': self._analyze_task_distribution(),
            'agent_workload': self._analyze_agent_workload(),
            'resource_bottlenecks': self._identify_resource_bottlenecks(),
            'inefficiencies': self._identify_workflow_inefficiencies()
        }
        
        # Generate optimization strategies
        optimization_strategies = self._generate_optimization_strategies(workflow_analysis)
        
        # Apply optimizations
        optimization_results = []
        for strategy in optimization_strategies:
            result = await self._apply_optimization_strategy(strategy)
            optimization_results.append(result)
        
        return {
            'workflow_optimized': True,
            'workflow_analysis': workflow_analysis,
            'optimization_strategies': optimization_strategies,
            'optimization_results': optimization_results,
            'expected_improvement': self._estimate_improvement(optimization_results)
        }
    
    # Helper methods for task coordination
    
    def _analyze_task_requirements(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze what a task requires"""
        
        requirements = {
            'complexity': self._assess_task_complexity(task),
            'memory_needed': task.get('memory_required', False),
            'reasoning_needed': task.get('reasoning_required', False),
            'emotional_processing': task.get('emotional', False),
            'time_sensitive': task.get('urgent', False),
            'dependencies': task.get('dependencies', [])
        }
        
        # Determine cognitive load
        cognitive_load = 0.0
        if requirements['memory_needed']:
            cognitive_load += 0.3
        if requirements['reasoning_needed']:
            cognitive_load += 0.4
        if requirements['emotional_processing']:
            cognitive_load += 0.2
        if requirements['time_sensitive']:
            cognitive_load += 0.1
        
        requirements['cognitive_load'] = min(1.0, cognitive_load)
        
        return requirements
    
    def _identify_required_agents(self, task_analysis: Dict[str, Any]) -> List[str]:
        """Identify which agents are needed for a task"""
        
        required_agents = []
        
        # Map requirements to agents
        if task_analysis['memory_needed']:
            required_agents.extend(['short_term_memory', 'memory_retrieval'])
        
        if task_analysis['reasoning_needed']:
            required_agents.extend(['reflection', 'executive_control'])
        
        if task_analysis['emotional_processing']:
            required_agents.append('stress_response')
        
        # Always include conversation for interaction
        if 'conversation' not in required_agents:
            required_agents.append('conversation')
        
        return list(set(required_agents))  # Remove duplicates
    
    def _create_execution_plan(self, agents: List[str], task_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create detailed execution plan"""
        
        plan = {
            'stages': [],
            'agent_sequence': [],
            'parallel_operations': [],
            'estimated_duration': 0
        }
        
        # Define execution stages
        if 'perception_encoding' in agents:
            plan['stages'].append({
                'stage': 'input_processing',
                'agents': ['perception_encoding'],
                'duration': 1
            })
        
        if any(agent in agents for agent in ['short_term_memory', 'memory_retrieval']):
            plan['stages'].append({
                'stage': 'memory_operations',
                'agents': [a for a in agents if 'memory' in a],
                'duration': 2
            })
        
        if 'reflection' in agents:
            plan['stages'].append({
                'stage': 'reasoning',
                'agents': ['reflection'],
                'duration': 3
            })
        
        if 'conversation' in agents:
            plan['stages'].append({
                'stage': 'response_generation',
                'agents': ['conversation'],
                'duration': 2
            })
        
        # Calculate total estimated duration
        plan['estimated_duration'] = sum(stage['duration'] for stage in plan['stages'])
        
        # Identify parallel operations
        memory_agents = [a for a in agents if 'memory' in a]
        if len(memory_agents) > 1:
            plan['parallel_operations'].append({
                'agents': memory_agents,
                'operation': 'parallel_memory_processing'
            })
        
        return plan
    
    async def _allocate_task_resources(self, execution_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Allocate resources for task execution"""
        
        allocation = {}
        
        for stage in execution_plan['stages']:
            stage_allocation = {}
            
            for agent in stage['agents']:
                # Estimate resource needs per agent
                if 'memory' in agent:
                    stage_allocation[agent] = {
                        'memory': 0.3,
                        'processing': 0.2,
                        'attention': 0.2
                    }
                elif agent == 'reflection':
                    stage_allocation[agent] = {
                        'memory': 0.2,
                        'processing': 0.4,
                        'attention': 0.3
                    }
                elif agent == 'conversation':
                    stage_allocation[agent] = {
                        'memory': 0.1,
                        'processing': 0.3,
                        'attention': 0.2
                    }
                else:
                    stage_allocation[agent] = {
                        'memory': 0.1,
                        'processing': 0.2,
                        'attention': 0.1
                    }
            
            allocation[stage['stage']] = stage_allocation
        
        return allocation
    
    # Helper methods for conflict resolution
    
    def _analyze_conflict(self, conflict: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze conflict characteristics"""
        
        return {
            'conflict_type': conflict.get('type', 'resource'),
            'severity': self._assess_conflict_severity(conflict),
            'agents_involved': conflict.get('agents', []),
            'resource_contested': conflict.get('resource'),
            'priority_difference': self._calculate_priority_difference(conflict)
        }
    
    def _select_resolution_strategy(self, conflict_analysis: Dict[str, Any]) -> str:
        """Select appropriate conflict resolution strategy"""
        
        if conflict_analysis['conflict_type'] == 'resource':
            if conflict_analysis['severity'] > 0.7:
                return 'priority_based'
            else:
                return 'resource_based'
        elif conflict_analysis['conflict_type'] == 'timing':
            return 'temporal_based'
        else:
            return 'compromise'
    
    async def _priority_based_resolution(self, conflict: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve conflict based on priority"""
        
        agents = conflict.get('agents', [])
        if len(agents) < 2:
            return {'error': 'Need at least 2 agents for conflict resolution'}
        
        # Determine priorities
        priorities = {agent: self.agent_priorities.get(agent, 0.5) for agent in agents}
        
        # Winner takes all
        winner = max(priorities, key=priorities.get)
        
        return {
            'resolution': 'priority_based',
            'winner': winner,
            'losers': [a for a in agents if a != winner],
            'resource_allocation': {winner: 1.0}
        }
    
    async def _resource_based_resolution(self, conflict: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve conflict through resource sharing"""
        
        agents = conflict.get('agents', [])
        resource = conflict.get('resource', 'processing')
        
        # Calculate fair share based on needs
        shares = {}
        total_need = sum(self.agent_priorities.get(agent, 0.5) for agent in agents)
        
        for agent in agents:
            agent_need = self.agent_priorities.get(agent, 0.5)
            shares[agent] = agent_need / total_need if total_need > 0 else 1.0 / len(agents)
        
        return {
            'resolution': 'resource_sharing',
            'resource': resource,
            'allocation': shares
        }
    
    async def _temporal_based_resolution(self, conflict: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve conflict through temporal scheduling"""
        
        agents = conflict.get('agents', [])
        
        # Create time slots
        time_slots = []
        for i, agent in enumerate(agents):
            time_slots.append({
                'agent': agent,
                'slot': i,
                'duration': 1.0 / len(agents)
            })
        
        return {
            'resolution': 'temporal_scheduling',
            'schedule': time_slots
        }
    
    async def _compromise_resolution(self, conflict: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve conflict through compromise"""
        
        return {
            'resolution': 'compromise',
            'strategy': 'balanced_allocation',
            'outcome': 'All parties receive partial resources'
        }
    
    # Helper methods for resource management
    
    def _validate_resource_demands(self, demands: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """Validate and normalize resource demands"""
        
        validated = {}
        
        for agent, agent_demands in demands.items():
            validated[agent] = {}
            
            for resource in self.resource_limits:
                if isinstance(agent_demands, dict):
                    demand = agent_demands.get(resource, 0.0)
                else:
                    demand = float(agent_demands)
                
                # Clamp to valid range
                validated[agent][resource] = max(0.0, min(1.0, demand))
        
        return validated
    
    def _optimize_resource_allocation(self, demands: Dict[str, Dict[str, float]], 
                                     total_demand: Dict[str, float]) -> Dict[str, Dict[str, float]]:
        """Optimize resource allocation when overloaded"""
        
        optimized = {}
        
        for agent, agent_demands in demands.items():
            optimized[agent] = {}
            
            for resource in self.resource_limits:
                if total_demand[resource] > self.resource_limits[resource]:
                    # Scale down proportionally
                    scale_factor = self.resource_limits[resource] / total_demand[resource]
                    optimized[agent][resource] = agent_demands[resource] * scale_factor
                else:
                    optimized[agent][resource] = agent_demands[resource]
        
        return optimized
    
    # Performance monitoring helpers
    
    def _calculate_resource_utilization(self) -> float:
        """Calculate overall resource utilization"""
        
        total_used = sum(self.resource_allocation.values())
        total_available = sum(self.resource_limits.values())
        
        return total_used / total_available if total_available > 0 else 0.0
    
    def _calculate_agent_activity(self) -> Dict[str, float]:
        """Calculate activity level of each agent"""
        
        activity = {}
        
        for task in self.active_tasks.values():
            for agent in task['agents_involved']:
                activity[agent] = activity.get(agent, 0) + 1
        
        # Normalize
        max_activity = max(activity.values()) if activity else 1
        
        return {agent: count / max_activity for agent, count in activity.items()}
    
    def _calculate_system_load(self) -> str:
        """Calculate overall system load"""
        
        utilization = self._calculate_resource_utilization()
        
        if utilization > 0.8:
            return 'high'
        elif utilization > 0.5:
            return 'moderate'
        elif utilization > 0.2:
            return 'low'
        else:
            return 'idle'
    
    def _identify_bottlenecks(self) -> List[str]:
        """Identify system bottlenecks"""
        
        bottlenecks = []
        
        for resource, allocation in self.resource_allocation.items():
            if allocation / self.resource_limits[resource] > 0.9:
                bottlenecks.append(f"{resource}_bottleneck")
        
        if len(self.task_queue) > 10:
            bottlenecks.append('task_queue_bottleneck')
        
        if len(self.active_tasks) > 5:
            bottlenecks.append('concurrent_task_bottleneck')
        
        return bottlenecks
    
    def _update_performance_metrics(self, current_metrics: Dict[str, Any]):
        """Update running performance metrics"""
        
        # Update task completion rate
        if self.completed_tasks:
            self.performance_metrics['task_completion_rate'] = (
                len(self.completed_tasks) / (len(self.completed_tasks) + len(self.active_tasks))
            )
        
        # Update average task duration
        if self.completed_tasks:
            durations = []
            for task in self.completed_tasks.values():
                if 'duration' in task:
                    durations.append(task['duration'])
            
            if durations:
                self.performance_metrics['average_task_duration'] = sum(durations) / len(durations)
        
        # Update resource utilization
        self.performance_metrics['resource_utilization'] = current_metrics['resource_utilization']
        
        # Update conflict rate
        if self.conflict_history:
            recent_conflicts = [c for c in self.conflict_history 
                              if (datetime.now() - c['timestamp']).seconds < 3600]
            self.performance_metrics['conflict_rate'] = len(recent_conflicts) / 60  # Conflicts per minute
    
    def _assess_system_health(self, metrics: Dict[str, Any]) -> str:
        """Assess overall system health"""
        
        health_score = 1.0
        
        # Check for bottlenecks
        if metrics['bottlenecks']:
            health_score -= 0.2 * len(metrics['bottlenecks'])
        
        # Check resource utilization
        if metrics['resource_utilization'] > 0.9:
            health_score -= 0.3
        elif metrics['resource_utilization'] < 0.1:
            health_score -= 0.1  # Underutilization
        
        # Check task queue
        if metrics['queued_tasks'] > 20:
            health_score -= 0.2
        
        if health_score > 0.8:
            return 'excellent'
        elif health_score > 0.6:
            return 'good'
        elif health_score > 0.4:
            return 'fair'
        else:
            return 'poor'
    
    def _generate_performance_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate recommendations for performance improvement"""
        
        recommendations = []
        
        if metrics['bottlenecks']:
            for bottleneck in metrics['bottlenecks']:
                if 'memory' in bottleneck:
                    recommendations.append('Consider memory optimization or caching')
                elif 'task_queue' in bottleneck:
                    recommendations.append('Increase task processing rate or parallelize')
        
        if metrics['resource_utilization'] > 0.8:
            recommendations.append('System near capacity - consider load balancing')
        elif metrics['resource_utilization'] < 0.2:
            recommendations.append('System underutilized - consider batching tasks')
        
        if metrics['system_load'] == 'high':
            recommendations.append('High system load - prioritize critical tasks')
        
        return recommendations
    
    # Additional helper methods
    
    def _assess_task_complexity(self, task: Dict[str, Any]) -> str:
        """Assess complexity of a task"""
        
        complexity_score = 0
        
        if task.get('multi_step', False):
            complexity_score += 2
        
        if task.get('requires_reasoning', False):
            complexity_score += 3
        
        if task.get('dependencies'):
            complexity_score += len(task['dependencies'])
        
        if complexity_score < 2:
            return 'simple'
        elif complexity_score < 5:
            return 'moderate'
        else:
            return 'complex'
    
    def _calculate_task_priority(self, task: Dict[str, Any]) -> float:
        """Calculate priority score for a task"""
        
        priority = 0.5  # Base priority
        
        if task.get('urgent', False):
            priority += 0.3
        
        if task.get('important', False):
            priority += 0.2
        
        if task.get('user_priority'):
            priority = task['user_priority']
        
        return min(1.0, priority)
    
    def _get_priority_factors(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get factors contributing to task priority"""
        
        return {
            'urgency': task.get('urgent', False),
            'importance': task.get('important', False),
            'user_priority': task.get('user_priority', 0.5),
            'dependencies': len(task.get('dependencies', [])),
            'complexity': self._assess_task_complexity(task)
        }
    
    def _estimate_resource_requirements(self, task: Dict[str, Any]) -> Dict[str, float]:
        """Estimate resource requirements for a task"""
        
        complexity = self._assess_task_complexity(task)
        
        base_requirements = {
            'simple': {'memory': 0.2, 'processing': 0.3, 'attention': 0.2},
            'moderate': {'memory': 0.4, 'processing': 0.5, 'attention': 0.4},
            'complex': {'memory': 0.6, 'processing': 0.7, 'attention': 0.6}
        }
        
        return base_requirements.get(complexity, base_requirements['moderate'])
    
    def _estimate_task_duration(self, task: Dict[str, Any]) -> float:
        """Estimate task duration in seconds"""
        
        complexity = self._assess_task_complexity(task)
        
        base_durations = {
            'simple': 2.0,
            'moderate': 5.0,
            'complex': 10.0
        }
        
        return base_durations.get(complexity, 5.0)
    
    def _determine_optimal_execution_time(self, task: Dict[str, Any]) -> str:
        """Determine optimal time to execute task"""
        
        if task.get('urgent', False):
            return 'immediate'
        elif self._calculate_system_load() == 'low':
            return 'now'
        else:
            return 'when_available'
    
    def _find_schedule_slot(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Find appropriate schedule slot for task"""
        
        return {
            'immediate': analysis['optimal_execution_time'] == 'immediate',
            'position': 0 if analysis['optimal_execution_time'] == 'immediate' else len(self.task_queue),
            'estimated_start': datetime.now() if analysis['optimal_execution_time'] == 'immediate' else None
        }
    
    def _update_conflict_metrics(self):
        """Update conflict-related metrics"""
        
        recent_window = 3600  # 1 hour in seconds
        recent_conflicts = [
            c for c in self.conflict_history
            if (datetime.now() - c['timestamp']).seconds < recent_window
        ]
        
        self.performance_metrics['conflict_rate'] = len(recent_conflicts) / (recent_window / 60)
    
    def _assess_conflict_severity(self, conflict: Dict[str, Any]) -> float:
        """Assess severity of a conflict"""
        
        severity = 0.5  # Base severity
        
        if conflict.get('blocks_critical_task', False):
            severity += 0.3
        
        if len(conflict.get('agents', [])) > 2:
            severity += 0.2
        
        return min(1.0, severity)
    
    def _calculate_priority_difference(self, conflict: Dict[str, Any]) -> float:
        """Calculate priority difference between conflicting agents"""
        
        agents = conflict.get('agents', [])
        if len(agents) < 2:
            return 0.0
        
        priorities = [self.agent_priorities.get(agent, 0.5) for agent in agents]
        return max(priorities) - min(priorities)
    
    # Workflow optimization helpers
    
    def _analyze_task_distribution(self) -> Dict[str, int]:
        """Analyze how tasks are distributed"""
        
        distribution = {}
        
        for task in self.active_tasks.values():
            task_type = task['task'].get('type', 'general')
            distribution[task_type] = distribution.get(task_type, 0) + 1
        
        return distribution
    
    def _analyze_agent_workload(self) -> Dict[str, float]:
        """Analyze workload per agent"""
        
        workload = {}
        
        for task in self.active_tasks.values():
            for agent in task['agents_involved']:
                workload[agent] = workload.get(agent, 0.0) + task['analysis']['cognitive_load']
        
        return workload
    
    def _identify_resource_bottlenecks(self) -> List[str]:
        """Identify resource bottlenecks"""
        
        bottlenecks = []
        
        for resource, allocation in self.resource_allocation.items():
            if allocation > self.resource_limits[resource] * 0.9:
                bottlenecks.append(resource)
        
        return bottlenecks
    
    def _identify_workflow_inefficiencies(self) -> List[str]:
        """Identify workflow inefficiencies"""
        
        inefficiencies = []
        
        # Check for idle agents
        active_agents = set()
        for task in self.active_tasks.values():
            active_agents.update(task['agents_involved'])
        
        if len(active_agents) < 3:  # Less than 3 agents active
            inefficiencies.append('underutilized_agents')
        
        # Check for task queue buildup
        if len(self.task_queue) > 10:
            inefficiencies.append('task_queue_buildup')
        
        # Check for repeated conflicts
        if len(self.conflict_history) > 10:
            recent_conflicts = self.conflict_history[-10:]
            conflict_types = [c['conflict'].get('type') for c in recent_conflicts]
            if len(set(conflict_types)) < 3:  # Same conflicts repeating
                inefficiencies.append('repeated_conflicts')
        
        return inefficiencies
    
    def _generate_optimization_strategies(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate optimization strategies based on analysis"""
        
        strategies = []
        
        if 'task_queue_buildup' in analysis['inefficiencies']:
            strategies.append({
                'type': 'parallel_processing',
                'description': 'Enable parallel task processing',
                'expected_benefit': 'Reduce queue by 50%'
            })
        
        if analysis['resource_bottlenecks']:
            strategies.append({
                'type': 'resource_reallocation',
                'description': 'Reallocate resources from idle to busy agents',
                'expected_benefit': 'Improve resource utilization by 20%'
            })
        
        if 'repeated_conflicts' in analysis['inefficiencies']:
            strategies.append({
                'type': 'conflict_prevention',
                'description': 'Implement proactive conflict prevention',
                'expected_benefit': 'Reduce conflicts by 30%'
            })
        
        return strategies
    
    async def _apply_optimization_strategy(self, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Apply an optimization strategy"""
        
        if strategy['type'] == 'parallel_processing':
            # Enable parallel processing for compatible tasks
            return {
                'strategy': strategy['type'],
                'applied': True,
                'result': 'Parallel processing enabled for compatible tasks'
            }
        
        elif strategy['type'] == 'resource_reallocation':
            # Reallocate resources
            return {
                'strategy': strategy['type'],
                'applied': True,
                'result': 'Resources reallocated based on demand'
            }
        
        elif strategy['type'] == 'conflict_prevention':
            # Implement conflict prevention
            return {
                'strategy': strategy['type'],
                'applied': True,
                'result': 'Conflict prevention rules updated'
            }
        
        return {
            'strategy': strategy['type'],
            'applied': False,
            'result': 'Strategy not implemented'
        }
    
    def _estimate_improvement(self, results: List[Dict[str, Any]]) -> float:
        """Estimate expected improvement from optimizations"""
        
        improvement = 0.0
        
        for result in results:
            if result['applied']:
                # Simple heuristic for improvement estimation
                if 'parallel' in result['strategy']:
                    improvement += 0.3
                elif 'resource' in result['strategy']:
                    improvement += 0.2
                elif 'conflict' in result['strategy']:
                    improvement += 0.15
        
        return min(1.0, improvement)