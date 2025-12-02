"""
Brain Config Manager
Handles persistence of adaptive parameters (e.g., thresholds, decay rates) to disk.
Ensures that the "soul's" learning is preserved across restarts.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from .config import get_logger
from .paths import BMAMPaths

logger = get_logger(__name__)

class BrainConfigManager:
    """
    Manages persistent brain configuration.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        # Default to unified data dir under BMAM/data, not repo root
        default_path = BMAMPaths.PROJECT_DATA_DIR / "brain_config.json"
        self.config_path = Path(config_path) if config_path else default_path
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config: Dict[str, Any] = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load config from disk or return defaults."""
        if not self.config_path.exists():
            logger.info("📄 No existing brain config found. Using defaults.")
            return {}
            
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"📄 Loaded brain config from {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"❌ Failed to load brain config: {e}")
            return {}
            
    def get_param(self, key: str, default: Any = None) -> Any:
        """Get a parameter value."""
        return self.config.get(key, default)
        
    def update_param(self, key: str, value: Any):
        """Update a parameter and save to disk."""
        self.config[key] = value
        self._save_config()
        logger.info(f"💾 Persisted parameter: {key} = {value}")
        
    def _save_config(self):
        """Save config to disk."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"❌ Failed to save brain config: {e}")
