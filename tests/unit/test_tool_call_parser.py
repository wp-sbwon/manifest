"""
Unit tests for ToolCallParser.

Tests tool call parsing, validation, and extraction.
"""
import pytest
from manifest.runtime.tools.tool_call_parser import ToolCallParser


def test_parse_anthropic_tool_use():
    """Test parsing Anthropic tool_use block."""
    data = {
        "type": "tool_use",
        "id": "tool-1",
        "name": "read_file",
        "input": {"file_path": "test.py"}
    }

    parsed = ToolCallParser.parse_anthropic_tool_use(data)
    assert parsed is not None
    assert parsed["id"] == "tool-1"
    assert parsed["name"] == "read_file"
    assert parsed["input"]["file_path"] == "test.py"


def test_parse_anthropic_tool_use_invalid():
    """Test parsing non-tool_use data."""
    data = {"type": "text", "text": "hello"}
    parsed = ToolCallParser.parse_anthropic_tool_use(data)
    assert parsed is None


def test_parse_openai_function_call():
    """Test parsing OpenAI function call."""
    data = {
        "choices": [{
            "delta": {
                "function_call": {
                    "name": "read_file",
                    "arguments": '{"file_path": "test.py"}'
                }
            }
        }]
    }

    parsed = ToolCallParser.parse_openai_function_call(data)
    assert parsed is not None
    assert parsed["name"] == "read_file"
    assert parsed["input"]["file_path"] == "test.py"


def test_parse_from_text():
    """Test parsing tool calls from text with markdown code blocks."""
    text = '''
    Here's a tool call:
    ```json
    {"type": "tool_use", "id": "tool-1", "name": "read_file", "input": {"file_path": "test.py"}}
    ```
    '''

    tool_calls = ToolCallParser.parse_from_text(text)
    assert len(tool_calls) == 1
    assert tool_calls[0]["name"] == "read_file"


def test_parse_streaming_response_anthropic():
    """Test parsing streaming response from Anthropic."""
    data = {
        "type": "content_block_start",
        "content_block": {
            "type": "tool_use",
            "id": "tool-1",
            "name": "read_file",
            "input": {"file_path": "test.py"}
        }
    }

    parsed = ToolCallParser.parse_streaming_response("anthropic", data)
    assert parsed is not None
    assert parsed["name"] == "read_file"


def test_extract_tool_results_from_response_anthropic():
    """Test extracting tool results from Anthropic response."""
    response_data = {
        "content": [{
            "type": "tool_use",
            "id": "tool-1",
            "name": "read_file",
            "input": {"file_path": "test.py"}
        }]
    }

    tool_calls = ToolCallParser.extract_tool_results_from_response("anthropic", response_data)
    assert len(tool_calls) == 1
    assert tool_calls[0]["name"] == "read_file"
