"""
Custom exception classes for Manifest.

This module defines a hierarchy of custom exceptions that provide structured
error handling throughout the application. All exceptions inherit from
ManifestError, which allows for consistent error handling and the ability
to attach additional context via a details dictionary.

Using specific exception types makes it easier to catch and handle different
kinds of errors appropriately, and provides better error messages to users.
"""
from typing import Optional, Dict, Any


class ManifestError(Exception):
    """Base exception class for all Manifest-specific errors.
    
    All custom exceptions in Manifest inherit from this class. It provides
    a way to attach additional context via a details dictionary, which can
    be useful for debugging and error reporting.
    
    Attributes:
        message: The main error message string.
        details: Optional dictionary containing additional error context.
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize a Manifest error.
        
        Args:
            message: Human-readable error message describing what went wrong.
            details: Optional dictionary with additional error context, such
                as file paths, IDs, or other relevant information.
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        """Return a formatted error message.
        
        Includes details if they were provided, otherwise just returns
        the main message.
        
        Returns:
            Formatted error string with message and optional details.
        """
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class ConfigurationError(ManifestError):
    """Raised when there's an error with configuration.
    
    Use this when configuration files are missing, malformed, or contain
    invalid values. Examples: missing API keys, invalid model names,
    corrupted config files.
    """
    pass


class StateError(ManifestError):
    """Raised when there's an error managing application state.
    
    Use this for errors related to loading, saving, or accessing state
    data. Examples: corrupted state file, permission errors, invalid
    state structure.
    """
    pass


class AgentError(ManifestError):
    """Raised when there's an error executing an agent.
    
    Use this for errors that occur during agent execution, such as LLM
    API failures, agent initialization problems, or agent communication
    issues.
    """
    pass


class BlueprintError(ManifestError):
    """Raised when there's an error with blueprint operations.
    
    Use this for errors related to blueprint loading, comparison, or
    synchronization. Examples: missing blueprint file, drift conflicts,
    synchronization failures.
    """
    pass


class ValidationError(ManifestError):
    """Raised when validation of data or input fails.
    
    Use this when data doesn't meet expected requirements or constraints.
    Examples: invalid task status, missing required fields, out-of-range
    values.
    """
    pass


class FileOperationError(ManifestError):
    """Raised when file operations fail.
    
    Use this for errors during file I/O operations. Examples: permission
    denied, disk full, file not found (when it should exist).
    """
    pass


class NetworkError(ManifestError):
    """Raised when network operations fail.
    
    Use this for errors during network requests, such as API calls to
    LLM providers. Examples: connection timeout, HTTP errors, network
    unreachable.
    """
    pass


class ContainerError(ManifestError):
    """Raised when Docker container operations fail.
    
    Use this for errors related to container management. Examples: container
    creation failure, Docker daemon not available, container communication
    errors.
    """
    pass


class TaskError(ManifestError):
    """Raised when task operations fail.
    
    Use this for errors specific to task management. Examples: task not
    found, invalid task state transition, task creation failure.
    """
    pass


class SprintError(ManifestError):
    """Raised when sprint operations fail.
    
    Use this for errors related to sprint management. Examples: sprint not
    found, invalid sprint configuration, sprint execution failure.
    """
    pass
