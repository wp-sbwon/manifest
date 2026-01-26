"""
Command parsing utilities for user input.

This module provides parsing functions to extract command names and arguments
from user input strings. It supports parsing commands, key-value pairs, and
filter expressions commonly used in command-line interfaces.
"""
from typing import Tuple, List


class CommandParser:
    """Parses command-line style commands from user input strings.

    Provides static methods for parsing different types of command syntax
    including basic commands, key-value pairs, and filter expressions.
    """

    @staticmethod
    def parse(user_input: str) -> Tuple[str, List[str]]:
        """Parse a command and its arguments from user input.

        Commands must start with "/" to be recognized. The command name
        is the first word after the slash, and remaining words are arguments.

        Args:
            user_input: Raw input string from the user.

        Returns:
            Tuple containing:
            - command: Command name (empty string if input is not a command)
            - args: List of argument strings (empty list if no arguments)
        """
        if not user_input.startswith("/"):
            return "", []

        parts = user_input[1:].split()
        command = parts[0] if parts else ""
        args = parts[1:] if len(parts) > 1 else []

        return command, args

    @staticmethod
    def parse_key_value_pairs(args: List[str], allowed_keys: List[str] = None) -> dict:
        """Parse key=value pairs from a list of argument strings.

        Extracts arguments in the format "key=value" and returns them as
        a dictionary. If allowed_keys is provided, only those keys are
        included in the result.

        Args:
            args: List of argument strings that may contain key=value pairs.
            allowed_keys: Optional list of allowed key names. If provided,
                only these keys will be included in the result.

        Returns:
            Dictionary mapping keys to values. Only includes keys that
            appear in allowed_keys if that parameter is provided.
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
        """Parse filter expressions from argument strings.

        Extracts all key=value pairs from arguments and returns them as
        a dictionary. This is useful for commands that accept multiple
        filter criteria like status=, stage=, sprint=, etc.

        Args:
            args: List of argument strings containing filter expressions.

        Returns:
            Dictionary mapping filter keys to their values. All key=value
            pairs found in the arguments are included.
        """
        filters = {}

        for arg in args:
            if "=" in arg:
                key, value = arg.split("=", 1)
                filters[key] = value

        return filters
