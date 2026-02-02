"""
Unit tests for ExecutorFactory.
"""
import pytest
from unittest.mock import Mock, patch
from manifest.runtime.agent.core.executor_factory import ExecutorFactory
from manifest.core.config import ConfigManager
from manifest.core.state_manager import StateManager
from manifest.runtime.agent.core.base_executor import BaseAgentExecutor
from pathlib import Path


@pytest.fixture
def mock_config_manager(tmp_path):
    """Create a mock config manager."""
    config = Mock(spec=ConfigManager)
    config.manifest_dir = tmp_path
    config.get_setting = Mock(side_effect=lambda key, default=None: default)
    return config


@pytest.fixture
def mock_state_manager(tmp_path):
    """Create a mock state manager."""
    state = Mock(spec=StateManager)
    state.manifest_dir = tmp_path
    return state


def test_get_available_backends():
    """Test that get_available_backends returns correct backends."""
    backends = ExecutorFactory.get_available_backends()
    assert isinstance(backends, list)
    assert "direct" in backends
    assert "opencode" in backends
    assert len(backends) == 2


def test_create_executor_direct(mock_config_manager, mock_state_manager):
    """Test creating direct executor."""
    with patch("manifest.runtime.agent.core.executor_factory.AgentExecutor") as mock_executor_class:
        mock_executor = Mock(spec=BaseAgentExecutor)
        mock_executor_class.return_value = mock_executor

        executor = ExecutorFactory.create_executor(
            mock_config_manager,
            mock_state_manager,
            backend="direct"
        )

        assert executor is not None
        mock_executor_class.assert_called_once()


def test_create_executor_opencode(mock_config_manager, mock_state_manager):
    """Test creating OpenCode executor."""
    def get_setting_side_effect(key, default=None):
        settings = {
            "opencode.server_host": "localhost",
            "opencode.server_port": 4096,
            "opencode.auto_start": True
        }
        return settings.get(key, default)

    mock_config_manager.get_setting = Mock(side_effect=get_setting_side_effect)

    with patch("manifest.runtime.opencode_llm_adapter.OpenCodeLLMAdapter") as mock_adapter_class:
        mock_adapter = Mock(spec=BaseAgentExecutor)
        mock_adapter_class.return_value = mock_adapter

        executor = ExecutorFactory.create_executor(
            mock_config_manager,
            mock_state_manager,
            backend="opencode"
        )

        assert executor is not None
        mock_adapter_class.assert_called_once()


def test_create_executor_from_config(mock_config_manager, mock_state_manager):
    """Test creating executor from config settings."""
    def get_setting_side_effect(key, default=None):
        settings = {
            "agent.execution_backend": "opencode",
            "opencode.server_host": "localhost",
            "opencode.server_port": 4096,
            "opencode.auto_start": True
        }
        return settings.get(key, default)

    mock_config_manager.get_setting = Mock(side_effect=get_setting_side_effect)

    with patch("manifest.runtime.opencode_llm_adapter.OpenCodeLLMAdapter") as mock_adapter_class:
        mock_adapter = Mock(spec=BaseAgentExecutor)
        mock_adapter_class.return_value = mock_adapter

        executor = ExecutorFactory.create_executor(
            mock_config_manager,
            mock_state_manager
        )

        assert executor is not None
        # Should default to opencode
        mock_adapter_class.assert_called_once()


def test_create_executor_invalid_backend(mock_config_manager, mock_state_manager):
    """Test that invalid backend raises ValueError."""
    with pytest.raises(ValueError, match="Unsupported execution backend"):
        ExecutorFactory.create_executor(
            mock_config_manager,
            mock_state_manager,
            backend="invalid_backend"
        )


def test_create_executor_default_backend(mock_config_manager, mock_state_manager):
    """Test that default backend is opencode."""
    def get_setting_side_effect(key, default=None):
        if key == "agent.execution_backend":
            return default  # Should default to "opencode"
        return default

    mock_config_manager.get_setting = Mock(side_effect=get_setting_side_effect)

    with patch("manifest.runtime.opencode_llm_adapter.OpenCodeLLMAdapter") as mock_adapter_class:
        mock_adapter = Mock(spec=BaseAgentExecutor)
        mock_adapter_class.return_value = mock_adapter

        executor = ExecutorFactory.create_executor(
            mock_config_manager,
            mock_state_manager
        )

        assert executor is not None
        # Should use opencode as default
        mock_adapter_class.assert_called_once()
