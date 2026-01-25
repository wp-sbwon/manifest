"""
Tool definitions for LLM function calling / tool use.

This module defines the JSON schemas for all available tools that agents can use.
These definitions are passed to LLM APIs (Anthropic, OpenAI) to enable tool use.
"""
from typing import List, Dict, Any


def get_tool_definitions() -> List[Dict[str, Any]]:
    """
    Get all tool definitions for LLM tool use.
    
    Returns:
        List of tool definition dictionaries compatible with Anthropic/OpenAI APIs.
    """
    return [
        {
            "name": "bash",
            "description": "Execute a shell command in the terminal. Use this for running git commands, build scripts, tests, or any other terminal operations.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The command to execute (e.g., 'git', 'python', 'npm')"
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Command arguments as a list of strings"
                    }
                },
                "required": ["command"]
            }
        },
        {
            "name": "edit",
            "description": "Edit a file by replacing an exact string match with a new string. This is the primary way to modify existing files. The old_string must match exactly (including whitespace and newlines) for the replacement to succeed.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to edit, relative to the working directory"
                    },
                    "old_string": {
                        "type": "string",
                        "description": "The exact string to replace (must match exactly including whitespace)"
                    },
                    "new_string": {
                        "type": "string",
                        "description": "The replacement string"
                    }
                },
                "required": ["file_path", "old_string", "new_string"]
            }
        },
        {
            "name": "write",
            "description": "Create a new file or overwrite an existing file with the given content. Use this for creating new files or completely replacing file contents.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to create or overwrite, relative to the working directory"
                    },
                    "content": {
                        "type": "string",
                        "description": "The complete file content to write"
                    }
                },
                "required": ["file_path", "content"]
            }
        },
        {
            "name": "read",
            "description": "Read a file or a specific line range from a file. Use this to examine existing code, configuration files, or documentation.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to read, relative to the working directory"
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "Optional starting line number (1-indexed). If omitted, reads entire file."
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "Optional ending line number (1-indexed, inclusive). If omitted, reads to end of file."
                    }
                },
                "required": ["file_path"]
            }
        },
        {
            "name": "grep",
            "description": "Search for a pattern in a file using regular expressions. Useful for finding specific code patterns, function definitions, or text matches.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regular expression pattern to search for"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to search in, relative to the working directory"
                    }
                },
                "required": ["pattern", "file_path"]
            }
        },
        {
            "name": "glob",
            "description": "Find files matching a glob pattern. Use this to discover files in the project (e.g., '*.py', '**/*.ts', 'src/**/*.js').",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern to match files (e.g., '*.py', 'src/**/*.ts')"
                    }
                },
                "required": ["pattern"]
            }
        },
        {
            "name": "list",
            "description": "List files and directories in a directory. Use this to explore the project structure.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Path to the directory to list, relative to the working directory. Defaults to current directory if omitted."
                    }
                },
                "required": []
            }
        }
    ]


def get_tool_names() -> List[str]:
    """Get list of all available tool names."""
    return [tool["name"] for tool in get_tool_definitions()]
