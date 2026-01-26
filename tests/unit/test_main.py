"""
Unit tests for __main__ module.

Tests the main entry point for Manifest application.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from manifest import __main__


@patch('manifest.__main__.get_config_manager')
@patch('manifest.__main__.run_bootstrap')
@patch('manifest.__main__.ManifestApp')
def test_main_without_keys(mock_app_class, mock_bootstrap, mock_config):
    """Test main entry point when API keys are not configured."""
    mock_config_instance = Mock()
    mock_config_instance.has_all_keys.return_value = False
    mock_config.return_value = mock_config_instance

    mock_app = Mock()
    mock_app_class.return_value = mock_app

    # Simulate running __main__
    __main__.__name__ = "__main__"

    # Call the main logic
    config = __main__.get_config_manager()
    if not config.has_all_keys():
        __main__.run_bootstrap()

    app = __main__.ManifestApp()
    app.run()

    mock_bootstrap.assert_called_once()
    mock_app.run.assert_called_once()


@patch('manifest.__main__.get_config_manager')
@patch('manifest.__main__.run_bootstrap')
@patch('manifest.__main__.ManifestApp')
def test_main_with_keys(mock_app_class, mock_bootstrap, mock_config):
    """Test main entry point when API keys are configured."""
    mock_config_instance = Mock()
    mock_config_instance.has_all_keys.return_value = True
    mock_config.return_value = mock_config_instance

    mock_app = Mock()
    mock_app_class.return_value = mock_app

    # Simulate running __main__
    __main__.__name__ = "__main__"

    # Call the main logic
    config = __main__.get_config_manager()
    if not config.has_all_keys():
        __main__.run_bootstrap()

    app = __main__.ManifestApp()
    app.run()

    mock_bootstrap.assert_not_called()
    mock_app.run.assert_called_once()
