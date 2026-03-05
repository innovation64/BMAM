import pytest
import os
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from src.utils.model_selector import select_model_for_query, select_model_for_task
from src.utils.config import SystemSettings

@pytest.fixture
def mock_settings():
    with patch('src.utils.model_selector.get_settings') as mock_get_settings:
        settings = MagicMock(spec=SystemSettings)
        settings.fast_llm_model = 'gpt-4o-mini'
        settings.default_llm_model = 'gpt-4o'
        settings.heavy_llm_model = 'gpt-4o'
        mock_get_settings.return_value = settings
        yield settings

def test_select_model_for_task(mock_settings):
    """Test explicit task-based selection"""
    # Fast tasks
    assert select_model_for_task('extraction') == 'gpt-4o-mini'
    assert select_model_for_task('summary') == 'gpt-4o-mini'
    
    # Heavy tasks
    assert select_model_for_task('consolidation') == 'gpt-4o'
    assert select_model_for_task('complex_reasoning') == 'gpt-4o'
    
    # Default
    assert select_model_for_task('unknown_task') == 'gpt-4o'

def test_select_model_for_query_simple(mock_settings):
    """Test simple query detection"""
    assert select_model_for_query("What is an apple?") == 'gpt-4o-mini'
    assert select_model_for_query("Define gravity") == 'gpt-4o-mini'
    assert select_model_for_query("List 5 fruits") == 'gpt-4o-mini'

def test_select_model_for_query_complex(mock_settings):
    """Test complex query detection"""
    assert select_model_for_query("Compare and contrast capitalism and socialism") == 'gpt-4o'
    assert select_model_for_query("Analyze the impact of AI on society") == 'gpt-4o'
    assert select_model_for_query("Explain why the sky is blue using physics") == 'gpt-4o'

def test_select_model_for_query_length(mock_settings):
    """Test length-based selection"""
    long_query = "This is a very long query that should definitely trigger the default model because it has many words and exceeds the threshold for simple queries which is usually around 15 words or so."
    assert select_model_for_query(long_query) == 'gpt-4o'

def test_env_switching():
    """Test that changing settings affects selection"""
    with patch('src.utils.model_selector.get_settings') as mock_get_settings:
        settings = MagicMock(spec=SystemSettings)
        # Simulate a configuration change (e.g. cost saving mode)
        settings.fast_llm_model = 'gpt-3.5-turbo'
        settings.default_llm_model = 'gpt-3.5-turbo' 
        settings.heavy_llm_model = 'gpt-4'
        mock_get_settings.return_value = settings
        
        assert select_model_for_task('extraction') == 'gpt-3.5-turbo'
        assert select_model_for_task('consolidation') == 'gpt-4'
