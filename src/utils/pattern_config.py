"""
Pattern Configuration Loader

Centralized configuration management for all hardcoded patterns in BMAM.
Supports multi-language patterns with fallback mechanisms.

Usage:
    from src.utils.pattern_config import pattern_config

    # Get temporal keywords for English
    keywords = pattern_config.get_patterns('query_patterns.json', 'temporal_keywords', 'en')

    # Get KG predicates with automatic language detection
    predicates = pattern_config.get_patterns('kg_query_patterns.json', 'location_predicates')
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger(__name__)


class PatternConfigLoader:
    """
    Centralized configuration loader for all hardcoded patterns.

    Features:
    - Multi-language support with fallback
    - Configuration caching for performance
    - Validation and error handling
    - Hot-reload support (optional)
    """

    def __init__(self, config_dir: str = "config", default_language: str = "en"):
        """
        Initialize the pattern config loader.

        Args:
            config_dir: Directory containing configuration JSON files
            default_language: Default language code (e.g., 'en', 'zh')
        """
        self.config_dir = Path(config_dir)
        self.default_language = default_language
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._file_timestamps: Dict[str, float] = {}

        # Ensure config directory exists
        if not self.config_dir.exists():
            logger.warning(f"Config directory not found: {self.config_dir}")
            logger.warning("Creating config directory...")
            self.config_dir.mkdir(parents=True, exist_ok=True)

    def load(self, config_file: str, force_reload: bool = False) -> Dict[str, Any]:
        """
        Load configuration file with caching.

        Args:
            config_file: Name of the config file (e.g., 'query_patterns.json')
            force_reload: Force reload even if cached

        Returns:
            Dictionary containing configuration data

        Raises:
            FileNotFoundError: If config file doesn't exist
            json.JSONDecodeError: If config file is invalid JSON
        """
        if not force_reload and config_file in self._cache:
            # Check if file has been modified
            file_path = self.config_dir / config_file
            if file_path.exists():
                current_mtime = file_path.stat().st_mtime
                cached_mtime = self._file_timestamps.get(config_file, 0)
                if current_mtime <= cached_mtime:
                    return self._cache[config_file]

        # Load configuration
        file_path = self.config_dir / config_file
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # Cache the config
            self._cache[config_file] = config
            self._file_timestamps[config_file] = file_path.stat().st_mtime

            return config

        except (json.JSONDecodeError) as e:
            logger.error(f"❌ Invalid JSON in {config_file}: {e}")
            raise

    def get_patterns(
        self,
        config_file: str,
        pattern_key: str,
        language: Optional[str] = None,
        fallback_to_default: bool = True
    ) -> List[str]:
        """
        Get language-specific patterns.

        Args:
            config_file: Name of the config file
            pattern_key: Key in the config file (e.g., 'temporal_keywords')
            language: Language code (e.g., 'en', 'zh'). If None, uses default.
            fallback_to_default: If True, fallback to default language if not found

        Returns:
            List of pattern strings

        Examples:
            # Get English temporal keywords
            keywords = loader.get_patterns('query_patterns.json', 'temporal_keywords', 'en')

            # Get default language patterns
            keywords = loader.get_patterns('query_patterns.json', 'temporal_keywords')
        """
        if language is None:
            language = self.default_language

        try:
            config = self.load(config_file)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"❌ Failed to load config {config_file}: {e}")
            return []

        patterns = config.get(pattern_key, {})

        # Support both flat lists and language-nested structures
        if isinstance(patterns, list):
            # Flat list (no language nesting)
            return patterns

        if isinstance(patterns, dict):
            # Language-nested structure
            if language in patterns:
                return patterns[language]

            # Fallback to default language
            if fallback_to_default and self.default_language in patterns:
                logger.warning(
                    f"⚠️ Pattern '{pattern_key}' not found for language '{language}', "
                    f"using default '{self.default_language}'"
                )
                return patterns[self.default_language]

        logger.warning(f"⚠️ Pattern '{pattern_key}' not found in {config_file}")
        return []

    def get_dict(
        self,
        config_file: str,
        dict_key: str,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get a dictionary value from config.

        Useful for mappings like month names to numbers.

        Args:
            config_file: Name of the config file
            dict_key: Key in the config file
            language: Language code (e.g., 'en', 'zh'). If None, uses default.

        Returns:
            Dictionary value
        """
        if language is None:
            language = self.default_language

        try:
            config = self.load(config_file)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

        data = config.get(dict_key, {})

        # Support both flat dicts and language-nested structures
        if isinstance(data, dict):
            if language in data:
                return data[language]
            return data

        return {}

    def get_regex_patterns(
        self,
        config_file: str,
        pattern_key: str
    ) -> List[str]:
        """
        Get regex patterns from config.

        Args:
            config_file: Name of the config file
            pattern_key: Key in the config file

        Returns:
            List of regex pattern strings
        """
        try:
            config = self.load(config_file)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

        patterns = config.get(pattern_key, [])

        # Handle both list of strings and list of dicts with 'pattern' key
        if isinstance(patterns, list):
            result = []
            for p in patterns:
                if isinstance(p, str):
                    result.append(p)
                elif isinstance(p, dict) and 'pattern' in p:
                    result.append(p['pattern'])
            return result

        return []

    def set_default_language(self, language: str):
        """
        Set the default language for pattern retrieval.

        Args:
            language: Language code (e.g., 'en', 'zh')
        """
        self.default_language = language

    def reload_all(self):
        """
        Reload all cached configurations.
        Useful for hot-reloading in development.
        """
        for config_file in list(self._cache.keys()):
            try:
                self.load(config_file, force_reload=True)
            except (Exception) as e:
                logger.error(f"❌ Failed to reload {config_file}: {e}")

    def clear_cache(self):
        """Clear the configuration cache."""
        self._cache.clear()
        self._file_timestamps.clear()


# Global singleton instance
pattern_config = PatternConfigLoader()


# Convenience functions for common use cases
def get_temporal_keywords(language: Optional[str] = None) -> List[str]:
    """Get temporal query keywords."""
    return pattern_config.get_patterns('query_patterns.json', 'temporal_keywords', language)


def get_intent_keywords(intent_type: str, language: Optional[str] = None) -> List[str]:
    """
    Get intent-specific keywords.

    Args:
        intent_type: Type of intent (e.g., 'memory', 'search', 'reasoning')
        language: Language code

    Returns:
        List of keywords for the intent type
    """
    # This would load from intent_patterns.json once created
    return pattern_config.get_patterns('query_patterns.json', f'{intent_type}_keywords', language)


def get_kg_predicates(predicate_type: str, language: Optional[str] = None) -> List[str]:
    """
    Get KG predicate keywords.

    Args:
        predicate_type: Type of predicate (e.g., 'movement', 'location', 'activity')
        language: Language code

    Returns:
        List of predicate keywords
    """
    return pattern_config.get_patterns(
        'kg_query_patterns.json',
        f'{predicate_type}_predicates',
        language
    )


# Migration helper function
def migrate_hardcoded_list(
    hardcoded_list: List[str],
    config_file: str,
    pattern_key: str,
    use_config: bool = True
) -> List[str]:
    """
    Helper function to migrate from hardcoded lists to configuration.

    During migration, you can use this to gradually switch over:

    Before:
        temporal_keywords = ['when', 'date', 'time', ...]

    After:
        temporal_keywords = migrate_hardcoded_list(
            ['when', 'date', 'time', ...],  # fallback
            'query_patterns.json',
            'temporal_keywords',
            use_config=True  # set to False to use hardcoded during transition
        )

    Args:
        hardcoded_list: Original hardcoded list (used as fallback)
        config_file: Config file to load from
        pattern_key: Key in the config file
        use_config: If True, try to load from config; if False, use hardcoded

    Returns:
        List from config or hardcoded fallback
    """
    if not use_config:
        return hardcoded_list

    try:
        patterns = pattern_config.get_patterns(config_file, pattern_key)
        if patterns:
            return patterns
        logger.warning(f"⚠️ No patterns found in config, using hardcoded fallback")
        return hardcoded_list
    except (Exception) as e:
        logger.warning(f"⚠️ Config load failed: {e}, using hardcoded fallback")
        return hardcoded_list
