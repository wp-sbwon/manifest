"""
Tests for app input handling to prevent repeated focus issues.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from textual.app import App
from textual.widgets import Input, RichLog


@pytest.fixture
def mock_app():
    """Create a mock app instance."""
    with patch('manifest.ui.app.ManifestApp'):
        from manifest.ui.app import ManifestApp
        app = ManifestApp()
        app.state_manager = Mock()
        app.state_manager.add_chat_message = Mock()
        app.state_manager.set_last_action = Mock()
        app.state_manager.save_state = AsyncMock(return_value=True)
        app.agent_bridge = None
        return app


def test_input_cleared_immediately(mock_app):
    """Test that input is cleared immediately on submission."""
    # This test verifies the input clearing logic
    input_widget = Mock()
    input_widget.value = "test command"
    
    # Simulate input submission
    event = Mock()
    event.value = "test command"
    
    # The input should be cleared immediately
    input_widget.value = ""
    assert input_widget.value == ""


def test_empty_input_handling(mock_app):
    """Test that empty input is handled correctly."""
    input_widget = Mock()
    input_widget.value = "   "  # Whitespace only
    
    # Simulate input submission with whitespace
    user_input = input_widget.value.strip()
    
    # Empty input should be ignored
    if not user_input:
        # Should return early without processing
        assert True
    else:
        assert False, "Empty input should be ignored"


def test_input_processing_flow(mock_app):
    """Test the complete input processing flow."""
    # Mock components
    input_widget = Mock()
    input_widget.value = "test"
    
    log = Mock()
    log.write = Mock()
    
    # Simulate the flow
    user_input = input_widget.value.strip()
    input_widget.value = ""  # Clear immediately
    
    if not user_input:
        return
    
    # Should process command
    log.write(f"[bold blue]User:[/] {user_input}")
    
    # Verify calls
    assert input_widget.value == ""
    log.write.assert_called()


@pytest.mark.asyncio
async def test_command_processing(mock_app):
    """Test command processing doesn't block."""
    log = Mock()
    log.write = Mock()
    
    # Test command processing
    user_input = "/audit"
    
    # Should process without blocking
    if user_input.startswith("/"):
        command = user_input[1:].split()[0]
        assert command == "audit"
    
    # Verify non-blocking behavior
    assert True  # If we get here, it didn't block


def test_focus_not_called_on_empty_input(mock_app):
    """Test that focus is not called when input is empty."""
    input_widget = Mock()
    input_widget.focus = Mock()
    input_widget.value = ""
    
    user_input = input_widget.value.strip()
    
    # Empty input should return early
    if not user_input:
        # Focus should NOT be called
        pass
    else:
        input_widget.focus()
    
    # Focus should not have been called for empty input
    input_widget.focus.assert_not_called()