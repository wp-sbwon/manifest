"""
Centralized logging configuration for Manifest.

This module provides a unified logging interface that replaces print()
statements throughout the codebase. Loggers can be configured with both
console and file handlers, with appropriate formatting and log levels.

The logging system uses Python's standard logging module and provides
convenience functions for setting up loggers with sensible defaults.
"""
import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str,
    log_file: Optional[Path] = None,
    level: int = logging.INFO,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Set up a logger with console and optional file handlers.

    Args:
        name: Logger name (typically __name__)
        log_file: Optional path to log file
        level: Logging level (default: INFO)
        format_string: Optional custom format string

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Default format
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    formatter = logging.Formatter(format_string)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # File logs are more verbose
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str, manifest_dir: Optional[Path] = None) -> logging.Logger:
    """Get or create a logger instance with automatic file logging.

    This is the main function to use for getting loggers throughout the
    codebase. It automatically sets up file logging if a manifest directory
    is provided, creating log files in the logs subdirectory.

    If the logger has already been configured (has handlers), returns the
    existing logger to avoid duplicate handlers.

    Args:
        name: Logger name, typically the module name (e.g., __name__).
        manifest_dir: Optional path to the .manifest directory. If provided,
            log files will be created in manifest_dir/logs/ with a filename
            based on the logger name.

    Returns:
        Logger instance ready to use. If manifest_dir is provided, the logger
        will write to both console and file.
    """
    logger = logging.getLogger(name)

    # If logger already configured, return it
    if logger.handlers:
        return logger

    # Set up logger with file logging if manifest_dir provided
    log_file = None
    if manifest_dir:
        log_file = manifest_dir / "logs" / f"{name.replace('.', '_')}.log"

    return setup_logger(name, log_file=log_file)
