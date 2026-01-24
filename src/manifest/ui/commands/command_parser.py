"""
Command Parser - Parses user input into command and arguments.
"""
from typing import Tuple, List


class CommandParser:
    """Parses command-line style commands from user input."""
    
    @staticmethod
    def parse(user_input: str) -> Tuple[str, List[str]]:
        """
        Parse command and arguments from user input.
        
        Args:
            user_input: Raw user input string
            
        Returns:
            Tuple of (command, args)
            - command: Command name (empty if not a command)
            - args: List of arguments
        """
        if not user_input.startswith("/"):
            return "", []
        
        parts = user_input[1:].split()
        command = parts[0] if parts else ""
        args = parts[1:] if len(parts) > 1 else []
        
        return command, args
    
    @staticmethod
    def parse_key_value_pairs(args: List[str], allowed_keys: List[str] = None) -> dict:
        """
        Parse key=value pairs from arguments.
        
        Args:
            args: List of argument strings
            allowed_keys: Optional list of allowed keys (filters out others)
            
        Returns:
            Dictionary of key-value pairs
        """
        result = {}
        
        for arg in args:
            if "=" in arg:
                key, value = arg.split("=", 1)
                if allowed_keys is None or key in allowed_keys:
                    result[key] = value
        
        return result
    
    @staticmethod
    def parse_filters(args: List[str]) -> dict:
        """
        Parse filter arguments (status=, stage=, sprint=, etc.).
        
        Args:
            args: List of argument strings
            
        Returns:
            Dictionary of filter key-value pairs
        """
        filters = {}
        
        for arg in args:
            if "=" in arg:
                key, value = arg.split("=", 1)
                filters[key] = value
        
        return filters
