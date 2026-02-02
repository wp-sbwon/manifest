"""
Unit tests for custom exceptions.

Tests exception classes and error handling.
"""
import pytest
from manifest.core.exceptions import (
    ManifestError,
    AgentError,
    StateError,
    ConfigurationError
)


def test_manifest_error():
    """Test ManifestError base exception."""
    error = ManifestError("Test error")
    assert str(error) == "Test error"
    assert isinstance(error, Exception)


def test_agent_error():
    """Test AgentError exception."""
    error = AgentError("Agent failed")
    assert str(error) == "Agent failed"
    assert isinstance(error, ManifestError)


def test_state_error():
    """Test StateError exception."""
    error = StateError("State error")
    assert str(error) == "State error"
    assert isinstance(error, ManifestError)


def test_configuration_error():
    """Test ConfigurationError exception."""
    error = ConfigurationError("Config error")
    assert str(error) == "Config error"
    assert isinstance(error, ManifestError)


def test_exception_with_details():
    """Test exception with additional details."""
    error = ManifestError("Error", details={"key": "value"})
    # __str__ includes details in format
    assert "Error" in str(error)
    assert hasattr(error, "details")
    assert error.details == {"key": "value"}
