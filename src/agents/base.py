from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
import logging

class BaseAgent(ABC):
    """Base class for all agents in the MA-CMM system"""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.logger = logging.getLogger(f"ma-cmm.{name}")
        self._initialize()
    
    def _initialize(self):
        """Initialize agent-specific components"""
        pass
    
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input data and return results
        
        Args:
            input_data: Input data dictionary
            
        Returns:
            Dict containing processing results
        """
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        return {
            "name": self.name,
            "status": "active",
            "config": self.config
        }
    
    def reset(self):
        """Reset agent state"""
        self.logger.info(f"Resetting agent: {self.name}")
        self._initialize()