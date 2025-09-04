"""
Environment Variable Loader for MA-CMM Framework

This module handles loading environment variables from .env files
and provides secure API key management.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Optional, Any

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    print("Warning: python-dotenv not installed. Install with: pip install python-dotenv")


class EnvLoader:
    """Environment variable loader with .env file support"""
    
    def __init__(self, env_file: str = ".env"):
        """
        Initialize environment loader
        
        Args:
            env_file: Path to .env file (relative to project root)
        """
        self.logger = logging.getLogger(__name__)
        self.project_root = Path(__file__).parent.parent
        self.env_file_path = self.project_root / env_file
        
        # Load .env file if available
        self._load_env_file()
    
    def _load_env_file(self):
        """Load environment variables from .env file"""
        
        if not DOTENV_AVAILABLE:
            self.logger.warning("python-dotenv not available. Using system environment variables only.")
            return
        
        if self.env_file_path.exists():
            load_dotenv(self.env_file_path)
            self.logger.info(f"Loaded environment variables from {self.env_file_path}")
        else:
            self.logger.warning(f"Environment file not found: {self.env_file_path}")
            self.logger.info("Using system environment variables only")
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Get API key for specified provider
        
        Args:
            provider: API provider name (openai, deepseek, claude, chatglm)
            
        Returns:
            API key if found, None otherwise
        """
        
        key_mapping = {
            'openai': 'OPENAI_API_KEY',
            'deepseek': 'DEEPSEEK_API_KEY',
            'claude': 'CLAUDE_API_KEY',
            'chatglm': 'CHATGLM_API_KEY'
        }
        
        env_var = key_mapping.get(provider.lower())
        if not env_var:
            self.logger.error(f"Unknown API provider: {provider}")
            return None
        
        api_key = os.getenv(env_var)
        
        if not api_key:
            self.logger.warning(f"API key not found for {provider} (env var: {env_var})")
            return None
        
        # Don't log the actual key for security
        self.logger.info(f"API key found for {provider}")
        return api_key
    
    def get_env_var(self, var_name: str, default: Any = None) -> Any:
        """
        Get environment variable with optional default value
        
        Args:
            var_name: Environment variable name
            default: Default value if variable not found
            
        Returns:
            Environment variable value or default
        """
        
        value = os.getenv(var_name, default)
        
        if value is None and default is None:
            self.logger.warning(f"Environment variable not found: {var_name}")
        
        return value
    
    def validate_required_keys(self, required_providers: list = None) -> Dict[str, bool]:
        """
        Validate that required API keys are available
        
        Args:
            required_providers: List of required API providers
            
        Returns:
            Dictionary of provider: bool (key available)
        """
        
        if required_providers is None:
            required_providers = ['openai']  # OpenAI required for GPT Score evaluation
        
        validation_results = {}
        
        for provider in required_providers:
            api_key = self.get_api_key(provider)
            validation_results[provider] = api_key is not None
            
            if api_key is None:
                self.logger.error(f"Required API key missing for {provider}")
        
        return validation_results
    
    def get_api_config(self) -> Dict[str, Any]:
        """
        Get complete API configuration from environment
        
        Returns:
            Dictionary with API configuration
        """
        
        config = {
            'openai': {
                'api_key': self.get_api_key('openai'),
                'base_url': self.get_env_var('OPENAI_BASE_URL', 'https://api.openai.com/v1')
            },
            'deepseek': {
                'api_key': self.get_api_key('deepseek')
            },
            'claude': {
                'api_key': self.get_api_key('claude')
            },
            'chatglm': {
                'api_key': self.get_api_key('chatglm')
            },
            'ollama': {
                'base_url': self.get_env_var('OLLAMA_BASE_URL', 'http://localhost:11434'),
                'model': self.get_env_var('OLLAMA_MODEL', 'llama3.1:8b')
            },
            'cost_limits': {
                'max_daily_cost': float(self.get_env_var('MAX_DAILY_COST_USD', 5)),
                'max_total_cost': float(self.get_env_var('MAX_TOTAL_COST_USD', 50))
            }
        }
        
        return config
    
    def create_env_template(self, output_path: str = ".env.example"):
        """
        Create a template .env file with all required variables
        
        Args:
            output_path: Path for the template file
        """
        
        template_content = """# MA-CMM API Configuration
# Copy this file to .env and set your actual API keys

# OpenAI API (Required for GPT Score evaluation)
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1

# DeepSeek API (Optional - for enhanced condition extraction)
DEEPSEEK_API_KEY=your-deepseek-api-key-here

# Other API providers (Optional)
CLAUDE_API_KEY=your-claude-api-key-here
CHATGLM_API_KEY=your-chatglm-api-key-here

# Ollama Configuration (Local models)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# Cost control settings
MAX_DAILY_COST_USD=5
MAX_TOTAL_COST_USD=50
"""
        
        template_path = self.project_root / output_path
        with open(template_path, 'w') as f:
            f.write(template_content)
        
        self.logger.info(f"Created environment template: {template_path}")


# Global instance
env_loader = EnvLoader()


def get_api_key(provider: str) -> Optional[str]:
    """Convenience function to get API key"""
    return env_loader.get_api_key(provider)


def get_env_var(var_name: str, default: Any = None) -> Any:
    """Convenience function to get environment variable"""
    return env_loader.get_env_var(var_name, default)


def validate_api_setup() -> bool:
    """
    Validate that the API setup is correct for running experiments
    
    Returns:
        True if setup is valid, False otherwise
    """
    
    logger = logging.getLogger(__name__)
    
    # Check if OpenAI API key is available (required for GPT Score)
    validation_results = env_loader.validate_required_keys(['openai'])
    
    if not validation_results['openai']:
        logger.error("OpenAI API key is required for GPT Score evaluation")
        logger.error("Please set OPENAI_API_KEY in your .env file or environment")
        return False
    
    logger.info("API setup validation passed")
    return True


def main():
    """Test environment loader"""
    
    # Set up basic logging
    logging.basicConfig(level=logging.INFO)
    
    print("=== MA-CMM Environment Configuration ===")
    
    # Validate API setup
    if validate_api_setup():
        print("✅ API setup is valid")
    else:
        print("❌ API setup has issues")
    
    # Show available API keys (without revealing actual keys)
    print("\n=== Available API Keys ===")
    providers = ['openai', 'deepseek', 'claude', 'chatglm']
    
    for provider in providers:
        key = get_api_key(provider)
        status = "✅ Available" if key else "❌ Missing"
        print(f"{provider.title()}: {status}")
    
    # Show configuration
    print(f"\n=== Configuration ===")
    print(f"Ollama URL: {get_env_var('OLLAMA_BASE_URL', 'http://localhost:11434')}")
    print(f"Ollama Model: {get_env_var('OLLAMA_MODEL', 'llama3.1:8b')}")
    print(f"Daily Cost Limit: ${get_env_var('MAX_DAILY_COST_USD', 5)}")
    print(f"Total Cost Limit: ${get_env_var('MAX_TOTAL_COST_USD', 50)}")


if __name__ == "__main__":
    main()