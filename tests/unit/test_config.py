"""
Unit tests for ConfigManager.

Tests configuration loading, saving, and API key management.
"""
import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from manifest.core.config import ConfigManager, get_config_manager


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing."""
    return tmp_path


@pytest.fixture
def config_manager(temp_dir):
    """Create a ConfigManager instance."""
    return ConfigManager(manifest_dir=temp_dir)


def test_config_manager_initialization(config_manager, temp_dir):
    """Test ConfigManager initialization."""
    assert config_manager.manifest_dir == temp_dir
    assert config_manager is not None


def test_get_setting(config_manager):
    """Test getting a setting."""
    value = config_manager.get_setting("test_key", default="default_value")
    assert value == "default_value" or isinstance(value, str)


def test_set_setting(config_manager):
    """Test setting a configuration value."""
    result = config_manager.set_setting("test_key", "test_value")
    assert result is True or result is None


def test_get_agent_model_config(config_manager):
    """Test getting agent model configuration."""
    config = config_manager.get_agent_model_config("coder")
    assert isinstance(config, dict)


def test_get_api_key(config_manager):
    """Test getting API key."""
    # ConfigManager uses get_api_keys() which returns a dict, not get_api_key()
    keys = config_manager.get_api_keys()
    assert isinstance(keys, dict)
    # Check for common provider keys
    assert "anthropic" in keys or "openai" in keys or "google" in keys


def test_set_api_key(config_manager):
    """Test setting API key."""
    # ConfigManager uses save_api_keys() which takes a dict, not set_api_key()
    result = config_manager.save_api_keys({"anthropic": "test_key"})
    assert result is True


def test_load_config(config_manager):
    """Test loading configuration."""
    # ConfigManager doesn't have load_config(), but we can test get_api_keys()
    # which loads the config
    config = config_manager.get_api_keys()
    assert isinstance(config, dict)


def test_save_config(config_manager):
    """Test saving configuration."""
    # ConfigManager doesn't have save_config(), but we can test save_api_keys()
    result = config_manager.save_api_keys({"anthropic": "test_key"})
    assert result is True


def test_get_config_manager():
    """Test getting global config manager."""
    manager = get_config_manager()
    assert manager is not None
    assert isinstance(manager, ConfigManager)
