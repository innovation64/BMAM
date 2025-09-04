"""
Agent工厂类
用于动态创建和配置Agent实例
"""

import importlib
import logging
from typing import Dict, Any, Optional, Type
from pathlib import Path
import yaml

from ..base import BrainAgent
from .base_adapter import AgentAdapter

logger = logging.getLogger(__name__)


class AgentFactory:
    """
    Agent工厂类
    负责创建、配置和管理Agent实例
    """
    
    # 默认Agent注册表
    _registry: Dict[str, Type[BrainAgent]] = {}
    
    # 适配器注册表
    _adapters: Dict[str, Type[AgentAdapter]] = {}
    
    # 配置缓存
    _config_cache: Optional[Dict] = None
    
    @classmethod
    def register_agent(cls, name: str, agent_class: Type[BrainAgent]):
        """
        注册Agent类
        
        Args:
            name: Agent名称
            agent_class: Agent类
        """
        cls._registry[name] = agent_class
        logger.info(f"Registered agent: {name} -> {agent_class.__name__}")
    
    @classmethod
    def register_adapter(cls, name: str, adapter_class: Type[AgentAdapter]):
        """
        注册适配器类
        
        Args:
            name: 适配器名称
            adapter_class: 适配器类
        """
        cls._adapters[name] = adapter_class
        logger.info(f"Registered adapter: {name} -> {adapter_class.__name__}")
    
    @classmethod
    def create_agent(cls, 
                    agent_type: str,
                    config: Optional[Dict[str, Any]] = None,
                    use_adapter: Optional[str] = None,
                    **kwargs) -> BrainAgent:
        """
        创建Agent实例
        
        Args:
            agent_type: Agent类型名称
            config: 配置字典
            use_adapter: 适配器名称
            **kwargs: 额外参数
            
        Returns:
            Agent实例
        """
        # 合并配置
        final_config = {}
        if config:
            final_config.update(config)
        final_config.update(kwargs)
        
        # 获取Agent类
        agent_class = cls._get_agent_class(agent_type)
        if not agent_class:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        # 创建Agent实例
        try:
            agent = agent_class(**final_config)
            logger.info(f"Created agent: {agent_type}")
        except Exception as e:
            logger.error(f"Failed to create agent {agent_type}: {e}")
            # 尝试使用默认配置
            agent = agent_class()
            logger.warning(f"Created agent {agent_type} with default config")
        
        # 应用适配器
        if use_adapter:
            adapter_class = cls._adapters.get(use_adapter)
            if adapter_class:
                agent = adapter_class(agent, config=final_config)
                logger.info(f"Applied adapter {use_adapter} to agent {agent_type}")
            else:
                logger.warning(f"Unknown adapter: {use_adapter}")
        
        return agent
    
    @classmethod
    def create_from_config(cls, config_path: str) -> Dict[str, BrainAgent]:
        """
        从配置文件创建所有Agent
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            Agent字典
        """
        config = cls._load_config(config_path)
        agents = {}
        
        for agent_name, agent_config in config.get('agents', {}).items():
            agent_type = agent_config.get('type', agent_name)
            params = agent_config.get('params', {})
            adapter = agent_config.get('adapter')
            
            try:
                agent = cls.create_agent(
                    agent_type=agent_type,
                    config=params,
                    use_adapter=adapter
                )
                agents[agent_name] = agent
            except Exception as e:
                logger.error(f"Failed to create agent {agent_name}: {e}")
                
                # 尝试使用后备方案
                fallback = agent_config.get('fallback')
                if fallback:
                    try:
                        agent = cls.create_agent(agent_type=fallback)
                        agents[agent_name] = agent
                        logger.info(f"Used fallback {fallback} for {agent_name}")
                    except:
                        logger.error(f"Fallback also failed for {agent_name}")
        
        return agents
    
    @classmethod
    def _get_agent_class(cls, agent_type: str) -> Optional[Type[BrainAgent]]:
        """
        获取Agent类
        
        Args:
            agent_type: Agent类型
            
        Returns:
            Agent类或None
        """
        # 首先检查注册表
        if agent_type in cls._registry:
            return cls._registry[agent_type]
        
        # 尝试动态导入
        try:
            return cls._dynamic_import(agent_type)
        except Exception as e:
            logger.error(f"Failed to import {agent_type}: {e}")
            return None
    
    @classmethod
    def _dynamic_import(cls, agent_type: str) -> Type[BrainAgent]:
        """
        动态导入Agent类
        
        Args:
            agent_type: Agent类型 (格式: module.ClassName)
            
        Returns:
            Agent类
        """
        if '.' not in agent_type:
            # 尝试从默认位置导入
            module_map = {
                'ShortTermMemoryAgent': 'src.agents.core.short_term_memory',
                'LongTermMemoryAgent': 'src.agents.core.long_term_memory',
                'MemoryRetrievalAgent': 'src.agents.core.memory_retrieval',
                'ConsolidationAgent': 'src.agents.core.consolidation',
                'MemoryDistortionAgent': 'src.agents.core.memory_distortion',
                'ReflectionAgent': 'src.agents.core.reflection',
                'ForgettingAgent': 'src.agents.core.forgetting',
                'StressResponseAgent': 'src.agents.core.stress_response',
                'ConversationAgent': 'src.agents.auxiliary.conversation',
                'ExecutiveControlAgent': 'src.agents.auxiliary.executive_control',
                'PerceptionEncodingAgent': 'src.agents.auxiliary.perception_encoding',
                'ActionExecutionAgent': 'src.agents.auxiliary.action_execution',
            }
            
            if agent_type in module_map:
                module_path = module_map[agent_type]
                class_name = agent_type
            else:
                raise ValueError(f"Unknown agent type: {agent_type}")
        else:
            # 直接使用提供的路径
            parts = agent_type.rsplit('.', 1)
            module_path = parts[0]
            class_name = parts[1] if len(parts) > 1 else agent_type
        
        # 导入模块
        module = importlib.import_module(module_path)
        
        # 获取类
        agent_class = getattr(module, class_name)
        
        # 注册到缓存
        cls._registry[agent_type] = agent_class
        
        return agent_class
    
    @classmethod
    def _load_config(cls, config_path: str) -> Dict:
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            配置字典
        """
        if cls._config_cache:
            return cls._config_cache
        
        path = Path(config_path)
        if not path.exists():
            logger.warning(f"Config file not found: {config_path}")
            return {}
        
        with open(path, 'r', encoding='utf-8') as f:
            if path.suffix == '.yaml' or path.suffix == '.yml':
                config = yaml.safe_load(f)
            else:
                import json
                config = json.load(f)
        
        cls._config_cache = config
        return config
    
    @classmethod
    def list_available_agents(cls) -> list:
        """
        列出所有可用的Agent
        
        Returns:
            Agent名称列表
        """
        # 默认Agent列表
        default_agents = [
            'ShortTermMemoryAgent',
            'LongTermMemoryAgent',
            'MemoryRetrievalAgent',
            'ConsolidationAgent',
            'MemoryDistortionAgent',
            'ReflectionAgent',
            'ForgettingAgent',
            'StressResponseAgent',
            'ConversationAgent',
            'ExecutiveControlAgent',
            'PerceptionEncodingAgent',
            'ActionExecutionAgent',
        ]
        
        # 合并注册的Agent
        all_agents = list(set(default_agents + list(cls._registry.keys())))
        return sorted(all_agents)
    
    @classmethod
    def list_available_adapters(cls) -> list:
        """
        列出所有可用的适配器
        
        Returns:
            适配器名称列表
        """
        return sorted(list(cls._adapters.keys()))


# 预注册常用适配器
def _register_default_adapters():
    """注册默认适配器"""
    from .base_adapter import (
        FeatureToggleAdapter,
        LoggingAdapter,
        CachingAdapter
    )
    
    AgentFactory.register_adapter('feature_toggle', FeatureToggleAdapter)
    AgentFactory.register_adapter('logging', LoggingAdapter)
    AgentFactory.register_adapter('caching', CachingAdapter)


# 模块加载时自动注册
_register_default_adapters()