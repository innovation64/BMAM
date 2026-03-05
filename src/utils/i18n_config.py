#!/usr/bin/env python3
"""
i18n Configuration Loader
Phase 3A - Person D: Config Schema Design

Provides centralized access to language patterns, temporal expressions,
and knowledge graph configurations from YAML files.
"""

import yaml
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class I18nConfig:
    """Centralized configuration loader for i18n patterns

    Usage:
        config = I18nConfig.get_instance()
        months = config.get_months()
        future_indicators = config.get_future_indicators()
        relation_types = config.get_kg_relation_types()
    """

    _instance: Optional['I18nConfig'] = None
    _config_data: Optional[Dict[str, Any]] = None

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize config loader

        Args:
            config_path: Path to config YAML file. If None, uses default location.
        """
        if config_path is None:
            # Default to project_root/config/i18n_patterns.yaml
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "i18n_patterns.yaml"

        self.config_path = config_path
        self._load_config()

    @classmethod
    def get_instance(cls, config_path: Optional[Path] = None) -> 'I18nConfig':
        """Get singleton instance of I18nConfig

        Args:
            config_path: Optional custom config path

        Returns:
            I18nConfig instance
        """
        if cls._instance is None:
            cls._instance = cls(config_path)
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Reset singleton instance (useful for testing)"""
        cls._instance = None
        cls._config_data = None

    def _load_config(self):
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config_data = yaml.safe_load(f)


        except FileNotFoundError:
            logger.error(f"Config file not found: {self.config_path}")
            self._config_data = self._get_default_config()

        except (yaml.YAMLError) as e:
            logger.error(f"Error parsing YAML config: {e}")
            self._config_data = self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Return minimal default config if file cannot be loaded"""
        return {
            'version': '0.0.0',
            'language': 'en',
            'temporal': {
                'months': [],
                'future_indicators': ['going to', 'will', 'planning to']
            },
            'knowledge_graph': {
                'relation_types': []
            }
        }

    # ========================================================================
    # Temporal Patterns
    # ========================================================================

    @lru_cache(maxsize=1)
    def get_months(self) -> List[Dict[str, Any]]:
        """Get list of month definitions

        Returns:
            List of dicts with 'name', 'aliases', 'number'
        """
        return self._config_data.get('temporal', {}).get('months', [])

    @lru_cache(maxsize=1)
    def get_month_names(self) -> List[str]:
        """Get list of month names (lowercase)

        Returns:
            ['january', 'february', ...]
        """
        return [month['name'] for month in self.get_months()]

    @lru_cache(maxsize=1)
    def get_month_aliases(self) -> Dict[str, str]:
        """Get mapping of month aliases to canonical names

        Returns:
            {'jan': 'january', 'feb': 'february', ...}
        """
        aliases = {}
        for month in self.get_months():
            canonical = month['name']
            for alias in month.get('aliases', []):
                aliases[alias.lower()] = canonical
        return aliases

    def get_month_number(self, month_name: str) -> Optional[int]:
        """Get month number (1-12) from month name or alias

        Args:
            month_name: Month name or alias (case-insensitive)

        Returns:
            Month number (1-12) or None if not found
        """
        month_name_lower = month_name.lower()

        # Check canonical names
        for month in self.get_months():
            if month['name'] == month_name_lower:
                return month['number']

        # Check aliases
        aliases = self.get_month_aliases()
        canonical = aliases.get(month_name_lower)
        if canonical:
            for month in self.get_months():
                if month['name'] == canonical:
                    return month['number']

        return None

    @lru_cache(maxsize=1)
    def get_seasons(self) -> List[Dict[str, Any]]:
        """Get list of season definitions

        Returns:
            List of dicts with 'name', 'months', 'aliases'
        """
        return self._config_data.get('temporal', {}).get('seasons', [])

    @lru_cache(maxsize=1)
    def get_past_markers(self) -> Dict[str, List[str]]:
        """Get past tense temporal markers

        Returns:
            Dict with keys: 'relative_year', 'relative_time', 'ago_patterns'
        """
        return self._config_data.get('temporal', {}).get('markers_past', {})

    @lru_cache(maxsize=1)
    def get_future_markers(self) -> Dict[str, List[Any]]:
        """Get future tense temporal markers

        Returns:
            Dict with keys: 'relative_year', 'relative_time', 'in_patterns', 'from_now_patterns'
        """
        return self._config_data.get('temporal', {}).get('markers_future', {})

    @lru_cache(maxsize=1)
    def get_future_indicators(self) -> List[str]:
        """Get future tense indicators (going to, will, planning to, etc.)

        Returns:
            List of future indicator phrases
        """
        return self._config_data.get('temporal', {}).get('future_indicators', [])

    @lru_cache(maxsize=1)
    def get_temporal_query_keywords(self) -> Dict[str, List[str]]:
        """Get temporal query keywords for gap detection

        Returns:
            Dict with keys: 'when', 'duration', 'frequency'
        """
        return self._config_data.get('temporal', {}).get('query_keywords', {})

    def get_ago_patterns(self) -> List[Tuple[re.Pattern, str]]:
        """Get compiled regex patterns for 'ago' expressions

        Returns:
            List of (compiled_pattern, unit) tuples
        """
        patterns = []
        for pattern_def in self.get_past_markers().get('ago_patterns', []):
            pattern_str = pattern_def.get('pattern', '')
            unit = pattern_def.get('unit', '')
            try:
                compiled = re.compile(pattern_str, re.IGNORECASE)
                patterns.append((compiled, unit))
            except (re.error) as e:
                logger.warning(f"Invalid regex pattern '{pattern_str}': {e}")
        return patterns

    def get_in_patterns(self) -> List[Tuple[re.Pattern, str]]:
        """Get compiled regex patterns for 'in N units' expressions

        Returns:
            List of (compiled_pattern, unit) tuples
        """
        patterns = []
        for pattern_def in self.get_future_markers().get('in_patterns', []):
            pattern_str = pattern_def.get('pattern', '')
            unit = pattern_def.get('unit', '')
            try:
                compiled = re.compile(pattern_str, re.IGNORECASE)
                patterns.append((compiled, unit))
            except (re.error) as e:
                logger.warning(f"Invalid regex pattern '{pattern_str}': {e}")
        return patterns

    def get_from_now_patterns(self) -> List[Tuple[re.Pattern, str]]:
        """Get compiled regex patterns for 'N units from now' expressions

        Returns:
            List of (compiled_pattern, unit) tuples
        """
        patterns = []
        for pattern_def in self.get_future_markers().get('from_now_patterns', []):
            pattern_str = pattern_def.get('pattern', '')
            unit = pattern_def.get('unit', '')
            try:
                compiled = re.compile(pattern_str, re.IGNORECASE)
                patterns.append((compiled, unit))
            except (re.error) as e:
                logger.warning(f"Invalid regex pattern '{pattern_str}': {e}")
        return patterns

    # ========================================================================
    # Knowledge Graph Patterns
    # ========================================================================

    @lru_cache(maxsize=1)
    def get_kg_entity_types(self) -> List[Dict[str, Any]]:
        """Get knowledge graph entity type definitions

        Returns:
            List of dicts with 'type', 'aliases', 'description'
        """
        return self._config_data.get('knowledge_graph', {}).get('entity_types', [])

    @lru_cache(maxsize=1)
    def get_kg_relation_types(self) -> List[Dict[str, Any]]:
        """Get knowledge graph relation type definitions

        Returns:
            List of dicts with 'relation', 'aliases', 'description', 'examples'
        """
        return self._config_data.get('knowledge_graph', {}).get('relation_types', [])

    @lru_cache(maxsize=1)
    def get_kg_relation_names(self) -> List[str]:
        """Get list of relation type names

        Returns:
            ['is_a', 'works_as', 'lives_in', ...]
        """
        return [rel['relation'] for rel in self.get_kg_relation_types()]

    def get_kg_relation_patterns(self) -> Dict[str, List[Tuple[re.Pattern, str]]]:
        """Get compiled regex patterns for relation extraction

        Returns:
            Dict mapping category to list of (compiled_pattern, relation) tuples
        """
        result = {}
        patterns_config = self._config_data.get('knowledge_graph', {}).get('relation_patterns', {})

        for category, patterns in patterns_config.items():
            compiled_patterns = []
            for pattern_def in patterns:
                pattern_str = pattern_def.get('pattern', '')
                relation = pattern_def.get('relation', '')
                try:
                    compiled = re.compile(pattern_str, re.IGNORECASE)
                    compiled_patterns.append((compiled, relation))
                except (re.error) as e:
                    logger.warning(f"Invalid regex pattern '{pattern_str}': {e}")
            result[category] = compiled_patterns

        return result

    # ========================================================================
    # Multi-Round Retrieval Patterns
    # ========================================================================

    @lru_cache(maxsize=1)
    def get_gap_detection_keywords(self) -> Dict[str, List[str]]:
        """Get keywords for gap detection in retrieval

        Returns:
            Dict with keys: 'temporal_keywords', 'entity_keywords', etc.
        """
        return self._config_data.get('retrieval', {}).get('gap_detection', {})

    @lru_cache(maxsize=1)
    def get_retrieval_thresholds(self) -> Dict[str, float]:
        """Get confidence thresholds for retrieval

        Returns:
            Dict with keys: 'high_confidence', 'medium_confidence', etc.
        """
        return self._config_data.get('retrieval', {}).get('thresholds', {})

    # ========================================================================
    # LLM Prompts
    # ========================================================================

    def get_prompt(self, prompt_name: str) -> Dict[str, str]:
        """Get LLM prompt by name

        Args:
            prompt_name: Name of prompt (e.g., 'kg_extraction', 'gap_detection')

        Returns:
            Dict with prompt components (system, user_template, etc.)
        """
        return self._config_data.get('prompts', {}).get(prompt_name, {})

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def get_version(self) -> str:
        """Get config version"""
        return self._config_data.get('version', 'unknown')

    def get_language(self) -> str:
        """Get config language"""
        return self._config_data.get('language', 'en')

    def reload(self):
        """Reload configuration from file"""
        self._load_config()
        # Clear caches
        self.get_months.cache_clear()
        self.get_month_names.cache_clear()
        self.get_month_aliases.cache_clear()
        self.get_seasons.cache_clear()
        self.get_past_markers.cache_clear()
        self.get_future_markers.cache_clear()
        self.get_future_indicators.cache_clear()
        self.get_temporal_query_keywords.cache_clear()
        self.get_kg_entity_types.cache_clear()
        self.get_kg_relation_types.cache_clear()
        self.get_kg_relation_names.cache_clear()
        self.get_gap_detection_keywords.cache_clear()
        self.get_retrieval_thresholds.cache_clear()



# ============================================================================
# Convenience Functions
# ============================================================================

def get_config() -> I18nConfig:
    """Get global I18nConfig instance

    Returns:
        I18nConfig singleton instance
    """
    return I18nConfig.get_instance()


def get_months() -> List[str]:
    """Convenience: Get month names"""
    return get_config().get_month_names()


def get_future_indicators() -> List[str]:
    """Convenience: Get future tense indicators"""
    return get_config().get_future_indicators()


def get_kg_relation_types() -> List[str]:
    """Convenience: Get KG relation type names"""
    return get_config().get_kg_relation_names()


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    # Demo usage
    logging.basicConfig(level=logging.INFO)

    config = I18nConfig.get_instance()







    gap_keywords = config.get_gap_detection_keywords()
