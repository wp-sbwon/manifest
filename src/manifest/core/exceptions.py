"""
Custom exception classes for Manifest.
Provides structured error handling across the application.
"""
from typing import Optional, Dict, Any


class ManifestError(Exception):
    """Base exception for all Manifest errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize Manifest error.
        
        Args:
            message: Error message
            details: Optional additional error details
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        """Return formatted error message."""
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class ConfigurationError(ManifestError):
    """Raised when there's a configuration error."""
    pass


class StateError(ManifestError):
    """Raised when there's a state management error."""
    pass


class AgentError(ManifestError):
    """Raised when there's an agent execution error."""
    pass


class BlueprintError(ManifestError):
    """Raised when there's a blueprint-related error."""
    pass


class ValidationError(ManifestError):
    """Raised when validation fails."""
    pass


class FileOperationError(ManifestError):
    """Raised when file operations fail."""
    pass


class NetworkError(ManifestError):
    """Raised when network operations fail."""
    pass


class ContainerError(ManifestError):
    """Raised when container operations fail."""
    pass


class TaskError(ManifestError):
    """Raised when task operations fail."""
    pass


class SprintError(ManifestError):
    """Raised when sprint operations fail."""
    pass
