"""
Configuration module for MA-CMM
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables once at module import
_env_loaded = False

def load_environment():
    """Load environment variables from .env file (singleton pattern)"""
    global _env_loaded
    if not _env_loaded:
        # Find project root (where .env should be)
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent
        env_path = project_root / '.env'
        
        # Load from .env file if it exists
        if env_path.exists():
            load_dotenv(env_path)
        else:
            # Try loading from current directory
            load_dotenv()
        
        _env_loaded = True
        return True
    return False

# Load environment on module import
load_environment()

# Export commonly used config values
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DEFAULT_MODEL = os.getenv('DEFAULT_MODEL', 'gpt-4o-mini')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small')
EMBEDDING_DIMENSION = int(os.getenv('EMBEDDING_DIMENSION', '1536'))
MA_CMM_DEBUG = os.getenv('MA_CMM_DEBUG', 'false').lower() == 'true'
MA_CMM_LOG_LEVEL = os.getenv('MA_CMM_LOG_LEVEL', 'INFO')

__all__ = [
    'load_environment',
    'OPENAI_API_KEY',
    'DEFAULT_MODEL',
    'EMBEDDING_MODEL',
    'EMBEDDING_DIMENSION',
    'MA_CMM_DEBUG',
    'MA_CMM_LOG_LEVEL'
]