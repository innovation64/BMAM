"""
Tests for Configuration Management
配置管理测试
"""

import pytest
import os
from BMAM.src.core.config import (
    BMAMConfig,
    MemorySystemConfig,
    AgentConfig,
    CoordinatorConfig,
    get_config,
    reset_config
)


class TestMemorySystemConfig:
    """Test suite for MemorySystemConfig"""

    def test_default_values(self):
        """Test default configuration values"""
        config = MemorySystemConfig()

        assert config.embedding_model == "text-embedding-3-small"
        assert config.embedding_dimension == 1536
        assert config.embedding_max_length == 8191
        assert config.enable_cache is True
        assert config.cache_dir == "data/embedding_cache"
        assert config.vector_db_index_path == "data/faiss_index"
        assert config.database_url == "sqlite:///data/memories.db"

    def test_immutability(self):
        """Test config is immutable (frozen dataclass)"""
        config = MemorySystemConfig()

        with pytest.raises(AttributeError):
            config.embedding_model = "new_model"


class TestAgentConfig:
    """Test suite for AgentConfig"""

    def test_default_values(self):
        """Test default configuration values"""
        config = AgentConfig()

        assert config.default_model == "gpt-4o-mini"
        assert config.max_tokens == 1500
        assert config.temperature == 0.7
        assert config.llm_call_timeout == 30.0
        assert config.max_retries == 3
        assert config.retry_delay == 1.0

    def test_immutability(self):
        """Test config is immutable"""
        config = AgentConfig()

        with pytest.raises(AttributeError):
            config.default_model = "new_model"


class TestCoordinatorConfig:
    """Test suite for CoordinatorConfig"""

    def test_default_values(self):
        """Test default configuration values"""
        config = CoordinatorConfig()

        assert config.parallel_phase_timeout == 15.0
        assert config.buffer_exchange_timeout == 5.0
        assert config.memory_storage_timeout == 8.0
        assert config.max_concurrent_agents == 10
        assert config.enable_learning is True
        assert config.enable_background_processes is True
        assert config.consolidation_interval_seconds == 3600
        assert config.default_language == "en"


class TestBMAMConfig:
    """Test suite for BMAMConfig"""

    def test_default_values(self):
        """Test default root configuration"""
        config = BMAMConfig()

        assert isinstance(config.memory, MemorySystemConfig)
        assert isinstance(config.agent, AgentConfig)
        assert isinstance(config.coordinator, CoordinatorConfig)
        assert config.environment == "production"
        assert config.log_level == "INFO"
        assert config.log_file == "bmam.log"

    def test_nested_config_access(self):
        """Test accessing nested configuration"""
        config = BMAMConfig()

        # Access nested values
        assert config.memory.embedding_model == "text-embedding-3-small"
        assert config.agent.default_model == "gpt-4o-mini"
        assert config.coordinator.max_concurrent_agents == 10

    def test_to_dict(self):
        """Test converting config to dictionary"""
        config = BMAMConfig()
        config_dict = config.to_dict()

        assert 'memory' in config_dict
        assert 'agent' in config_dict
        assert 'coordinator' in config_dict
        assert config_dict['environment'] == 'production'
        assert config_dict['log_level'] == 'INFO'

        # Check nested dict
        assert 'embedding_model' in config_dict['memory']
        assert 'default_model' in config_dict['agent']


class TestBMAMConfigFromEnv:
    """Test suite for loading config from environment"""

    def test_from_env_with_defaults(self, monkeypatch):
        """Test loading config with default values"""
        # Clear relevant env vars
        for key in os.environ.copy():
            if key.startswith('BMAM_') or key.startswith('EMBEDDING_'):
                monkeypatch.delenv(key, raising=False)

        config = BMAMConfig.from_env()

        # Should use defaults
        assert config.memory.embedding_model == "text-embedding-3-small"
        assert config.agent.default_model == "gpt-4o-mini"
        assert config.environment == "production"

    def test_from_env_with_custom_values(self, monkeypatch):
        """Test loading config from environment variables"""
        # Set environment variables
        monkeypatch.setenv("EMBEDDING_MODEL", "custom-model")
        monkeypatch.setenv("EMBEDDING_DIMENSION", "768")
        monkeypatch.setenv("DEFAULT_MODEL", "gpt-4")
        monkeypatch.setenv("MAX_TOKENS", "2000")
        monkeypatch.setenv("BMAM_ENV", "development")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")

        config = BMAMConfig.from_env()

        # Should use env values
        assert config.memory.embedding_model == "custom-model"
        assert config.memory.embedding_dimension == 768
        assert config.agent.default_model == "gpt-4"
        assert config.agent.max_tokens == 2000
        assert config.environment == "development"
        assert config.log_level == "DEBUG"

    def test_from_env_boolean_parsing(self, monkeypatch):
        """Test boolean environment variable parsing"""
        monkeypatch.setenv("ENABLE_EMBEDDING_CACHE", "false")
        monkeypatch.setenv("ENABLE_LEARNING", "false")
        monkeypatch.setenv("ENABLE_BACKGROUND_PROCESSES", "false")

        config = BMAMConfig.from_env()

        assert config.memory.enable_cache is False
        assert config.coordinator.enable_learning is False
        assert config.coordinator.enable_background_processes is False

    def test_from_env_numeric_parsing(self, monkeypatch):
        """Test numeric environment variable parsing"""
        monkeypatch.setenv("CACHE_MAX_SIZE", "5000")
        monkeypatch.setenv("TEMPERATURE", "0.5")
        monkeypatch.setenv("LLM_CALL_TIMEOUT", "60.0")
        monkeypatch.setenv("MAX_CONCURRENT_AGENTS", "20")

        config = BMAMConfig.from_env()

        assert config.memory.cache_max_size == 5000
        assert config.agent.temperature == 0.5
        assert config.agent.llm_call_timeout == 60.0
        assert config.coordinator.max_concurrent_agents == 20

    def test_from_env_openai_api_key(self, monkeypatch):
        """Test loading OpenAI API key from environment"""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123")

        config = BMAMConfig.from_env()

        assert config.openai_api_key == "sk-test-key-123"


class TestBMAMConfigForTesting:
    """Test suite for testing configuration preset"""

    def test_for_testing_defaults(self):
        """Test testing configuration has appropriate defaults"""
        config = BMAMConfig.for_testing()

        # Memory optimizations for testing
        assert config.memory.enable_cache is False
        assert config.memory.cache_dir == "test_data/cache"
        assert config.memory.max_vectors == 100
        assert config.memory.database_url == "sqlite:///:memory:"
        assert config.memory.connection_pool_size == 1

        # Agent optimizations for testing
        assert config.agent.llm_call_timeout == 5.0
        assert config.agent.max_retries == 0
        assert config.agent.fallback_cache_size == 10
        assert config.agent.enable_activation_logging is False

        # Coordinator optimizations for testing
        assert config.coordinator.parallel_phase_timeout == 5.0
        assert config.coordinator.enable_learning is False
        assert config.coordinator.enable_background_processes is False

        # Environment
        assert config.environment == "test"
        assert config.log_level == "DEBUG"
        assert config.log_file is None

    def test_for_testing_immutable(self):
        """Test testing config is also immutable"""
        config = BMAMConfig.for_testing()

        with pytest.raises(AttributeError):
            config.environment = "production"


class TestGlobalConfigFunctions:
    """Test suite for global config functions"""

    def test_get_config_returns_instance(self):
        """Test get_config returns config instance"""
        reset_config()  # Ensure clean state

        config = get_config()

        assert isinstance(config, BMAMConfig)

    def test_get_config_caches(self):
        """Test get_config caches the instance"""
        reset_config()

        config1 = get_config()
        config2 = get_config()

        # Should return same instance
        assert config1 is config2

    def test_reset_config_clears_cache(self):
        """Test reset_config clears cached instance"""
        reset_config()

        config1 = get_config()

        reset_config()

        config2 = get_config()

        # Should create new instance
        assert config1 is not config2

    def test_get_config_loads_from_env(self, monkeypatch):
        """Test get_config loads from environment"""
        reset_config()

        monkeypatch.setenv("BMAM_ENV", "development")
        monkeypatch.setenv("LOG_LEVEL", "WARNING")

        config = get_config()

        assert config.environment == "development"
        assert config.log_level == "WARNING"


class TestConfigurationUsage:
    """Test realistic configuration usage patterns"""

    def test_access_nested_config_values(self):
        """Test accessing configuration in application code"""
        config = BMAMConfig.for_testing()

        # Typical usage pattern
        embedding_model = config.memory.embedding_model
        llm_timeout = config.agent.llm_call_timeout
        enable_learning = config.coordinator.enable_learning

        assert embedding_model == "text-embedding-3-small"
        assert llm_timeout == 5.0
        assert enable_learning is False

    def test_config_in_dependency_injection(self):
        """Test using config with dependency injection"""
        from BMAM.src.core.container import Container

        config = BMAMConfig.for_testing()
        container = Container()

        # Register config
        container.register_instance(BMAMConfig, config)

        # Resolve it
        resolved_config = container.resolve(BMAMConfig)

        assert resolved_config is config
        assert resolved_config.environment == "test"

    def test_multiple_config_presets(self):
        """Test creating different config presets"""
        # Production config
        prod_config = BMAMConfig.from_env()

        # Test config
        test_config = BMAMConfig.for_testing()

        # They should have different settings
        assert prod_config.memory.enable_cache is True
        assert test_config.memory.enable_cache is False

        assert prod_config.coordinator.enable_learning is True
        assert test_config.coordinator.enable_learning is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
