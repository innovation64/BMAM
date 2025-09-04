from .config import ConfigManager
from .prompts import PromptTemplates
from .logging_config import setup_logging

__all__ = ['ConfigManager', 'PromptTemplates', 'setup_logging']

# Optional imports (require dependencies)
try:
    from .api_client import APIClient, MockAPIClient
    __all__.extend(['APIClient', 'MockAPIClient'])
except ImportError:
    pass

try:
    from .ollama_client import OllamaClient
    __all__.append('OllamaClient')
except ImportError:
    pass