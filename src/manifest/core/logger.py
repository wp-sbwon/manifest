"""
Logging System - Centralized logging configuration.
Replaces all print() statements with proper logging.
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
    """
    Get or create a logger instance.
    
    Args:
        name: Logger name (typically __name__)
        manifest_dir: Optional .manifest directory for log files
        
    Returns:
        Logger instance
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


# Module-level logger for core operations
_core_logger = get_logger(__name__)
