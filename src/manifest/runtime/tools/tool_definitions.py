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
        },
        {
            "name": "task_management",
            "description": "Create, update, list, or get tasks. Updates .manifest/tasks.json for real-time View sync. Use create_task to add a task, update_task_status/assign_task/update_task_progress/update_task_stage to update, list_tasks/get_task to read.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "One of: create_task, update_task_status, assign_task, update_task_progress, update_task_stage, list_tasks, get_task"
                    },
                    "name": {"type": "string", "description": "Task name (for create_task)"},
                    "task_id": {"type": "string", "description": "Task ID (for update/get/assign)"},
                    "status": {"type": "string", "description": "pending|in_progress|paused|blocked|completed|cancelled"},
                    "stage": {"type": "string", "description": "planning|coding|testing|review|done"},
                    "agent_name": {"type": "string", "description": "Agent to assign (e.g. manifest-coder)"},
                    "percentage": {"type": "number", "description": "Progress 0-100"},
                    "sprint_id": {"type": "string", "description": "Sprint ID (for create_task or filter list_tasks)"},
                    "blueprint_entity_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Blueprint entity IDs for this task"
                    },
                    "mission_id": {"type": "string", "description": "Mission ID (optional)"}
                },
                "required": ["action"]
            }
        },
        {
            "name": "sprint_management",
            "description": "Create, list, get, or update sprints. Sprints are stored in .manifest/tasks.json.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "One of: create_sprint, list_sprints, get_sprint, update_sprint"
                    },
                    "name": {"type": "string", "description": "Sprint name"},
                    "sprint_id": {"type": "string", "description": "Sprint ID"},
                    "start_date": {"type": "string", "description": "Start date YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "End date YYYY-MM-DD"},
                    "status": {"type": "string", "description": "Sprint status (e.g. active)"},
                    "task_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Task IDs in this sprint"
                    }
                },
                "required": ["action"]
            }
        },
        {
            "name": "worker_squad_spawn",
            "description": "Spawn a worker squad agent (planner, coder, test, debug, approver) as an OpenCode agent process. Returns agent_process_id.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "One of: run_squad (full workflow), spawn_planner, spawn_coder, spawn_test, spawn_debug, spawn_approver"
                    },
                    "task_id": {"type": "string", "description": "Task ID for this agent"},
                    "context": {"type": "object", "description": "Context dict (Tier 1/2/3) for the agent"},
                    "plan": {"type": "object", "description": "Plan from planner (for spawn_coder)"},
                    "code_changes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Paths of changed files (for spawn_test)"
                    },
                    "error_info": {"type": "object", "description": "Error details (for spawn_debug)"},
                    "work_summary": {"type": "object", "description": "Work summary (for spawn_approver)"}
                },
                "required": ["action", "task_id"]
            }
        },
        {
            "name": "blueprint_sync",
            "description": "Compare Design Plan vs Actual Code (top-down vs bottom-up), detect deviation, run sync workflow, or compare all docs with implementation status (Healthy/Planned/Partial/Deviation).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "One of: compare_blueprints, detect_drift, sync_blueprint, compare_all_docs (detect_drift returns deviation)"
                    },
                    "mode": {
                        "type": "string",
                        "description": "For sync_blueprint: strict | workflow | merge"
                    }
                },
                "required": ["action"]
            }
        },
        {
            "name": "drift_check",
            "description": "Detect deviation between Design Plan and Actual Code (component status: Healthy/Planned/Partial/Deviation).",
            "input_schema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "architect",
            "description": "Write PRD or blueprint to .manifest only. Use write_architecture with blueprint content (version, root_id, entities). Use write_prd with PRD content. Use ideate for discussion only.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "One of: write_prd, write_architecture, ideate"
                    },
                    "content": {
                        "type": "object",
                        "description": "For write_architecture: blueprint (version, root_id, entities). For write_prd: PRD doc. Omit for ideate."
                    }
                },
                "required": ["action"]
            }
        }
    ]


def get_tool_names() -> List[str]:
    """Get list of all available tool names."""
    return [tool["name"] for tool in get_tool_definitions()]
