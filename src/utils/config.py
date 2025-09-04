import yaml
import os
from typing import Dict, Any, Optional
from pathlib import Path

class ConfigManager:
    """Manages configuration loading and environment variable substitution"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self._config = None
        self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        # Load .env file first
        self._load_env_file()
        
        try:
            # Use UTF-8 encoding to handle Chinese characters
            with open(self.config_path, 'r', encoding='utf-8') as file:
                self._config = yaml.safe_load(file)
                self._substitute_env_vars(self._config)
            return self._config
        except FileNotFoundError:
            print(f"Warning: Config file {self.config_path} not found. Using defaults.")
            self._config = self._get_default_config()
            return self._config
        except Exception as e:
            print(f"Error loading config: {e}. Using defaults.")
            self._config = self._get_default_config()
            return self._config
    
    def _substitute_env_vars(self, config: Any) -> Any:
        """Recursively substitute environment variables in config"""
        if isinstance(config, dict):
            for key, value in config.items():
                config[key] = self._substitute_env_vars(value)
        elif isinstance(config, list):
            for i, item in enumerate(config):
                config[i] = self._substitute_env_vars(item)
        elif isinstance(config, str) and config.startswith("${") and config.endswith("}"):
            env_var_spec = config[2:-1]
            # Handle default values like ${VAR_NAME:-default_value}
            if ":-" in env_var_spec:
                env_var, default_val = env_var_spec.split(":-", 1)
                config = os.getenv(env_var, default_val)
            else:
                env_var = env_var_spec
                config = os.getenv(env_var, config)
        
        return config
    
    def _load_env_file(self):
        """Load .env file manually"""
        env_file = Path('.env')
        if env_file.exists():
            try:
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and '=' in line and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            # Only set if not already in environment
                            if key not in os.environ:
                                os.environ[key] = value
            except Exception as e:
                print(f"Warning: Could not load .env file: {e}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "api": {
                "provider": "ollama",
                "base_url": "http://localhost:11434",
                "timeout": 30,
                "max_retries": 3
            },
            "models": {
                "local": {
                    "orchestrator": "phi3:mini",
                    "memory_manager": "phi3:mini",
                    "base_url": "http://localhost:11434"
                },
                "api": {
                    "condition_extractor": "llama3.1:8b",
                    "generator": "llama3.1:8b",
                    "temperature": 0.1,
                    "max_tokens": 2000
                },
                "embeddings": {
                    "model": "sentence-transformers/all-MiniLM-L6-v2",
                    "dimension": 384
                }
            },
            "agents": {
                "memory": {
                    "memory_threshold": 50,
                    "compression_ratio": 0.5
                },
                "retriever": {
                    "top_k": 10,
                    "condition_weight": 0.3
                },
                "generator": {
                    "max_context_length": 4000,
                    "temperature": 0.7
                }
            },
            "experiment": {
                "batch_size": 10,
                "output_dir": "results/"
            },
            "logging": {
                "level": "INFO"
            }
        }
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'api.timeout')"""
        if not self._config:
            self.load_config()
        
        keys = key_path.split('.')
        value = self._config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_config(self) -> Dict[str, Any]:
        """Get the complete configuration dictionary"""
        if not self._config:
            self.load_config()
        return self._config
    
    def set(self, key_path: str, value: Any):
        """Set configuration value using dot notation"""
        if not self._config:
            self._config = {}
        
        keys = key_path.split('.')
        config = self._config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
    
    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """Get configuration for a specific agent"""
        return self.get(f"agents.{agent_name}", {})
    
    def get_api_config(self) -> Dict[str, Any]:
        """Get API configuration"""
        return self.get("api", {})
    
    def get_model_config(self) -> Dict[str, Any]:
        """Get model configuration"""
        return self.get("models", {})
    
    def save_config(self, output_path: Optional[str] = None):
        """Save current configuration to file"""
        if not output_path:
            output_path = self.config_path
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as file:
            yaml.dump(self._config, file, default_flow_style=False, indent=2, allow_unicode=True)
    
    def validate_config(self) -> Dict[str, list]:
        """Validate configuration and return any issues"""
        issues = {
            "missing": [],
            "invalid": [],
            "warnings": []
        }
        
        # Check required fields
        required_fields = [
            "agents.memory.memory_threshold",
            "agents.retriever.top_k",
            "models.embeddings.model"
        ]
        
        for field in required_fields:
            if self.get(field) is None:
                issues["missing"].append(field)
        
        # Check API provider
        provider = self.get("api.provider")
        if provider == "deepseek":
            api_key = self.get("api.deepseek_api_key")
            if not api_key or api_key.startswith("${"):
                issues["warnings"].append("DeepSeek API key not set - some features may not work")
        elif provider == "ollama":
            base_url = self.get("api.base_url", "http://localhost:11434")
            if not base_url:
                issues["warnings"].append("Ollama base URL not configured")
        
        # Check paths
        data_dir = self.get("storage.data_dir", "ma-cmm/data/")
        if not os.path.exists(data_dir):
            issues["warnings"].append(f"Data directory {data_dir} does not exist")
        
        return issues
    
    @property
    def config(self) -> Dict[str, Any]:
        """Get the full configuration dictionary"""
        if not self._config:
            self.load_config()
        return self._config