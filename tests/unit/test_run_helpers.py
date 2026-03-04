"""Tests for manifest.opencode.run_helpers — pure function tests, no mocks needed."""
import json

import pytest

from manifest.opencode.run_helpers import extract_json_from_text, parse_opencode_stdout


# --- parse_opencode_stdout ---


def test_parse_single_text_part():
    """Single text part extracted from JSON-line."""
    line = json.dumps({"type": "text", "part": {"text": "hello world"}})
    assert parse_opencode_stdout(line) == "hello world"


def test_parse_multiple_text_parts():
    """Multiple text parts joined with newlines."""
    lines = (
        json.dumps({"type": "text", "part": {"text": "line one"}}) + "\n"
        + json.dumps({"type": "text", "part": {"text": "line two"}})
    )
    result = parse_opencode_stdout(lines)
    assert result == "line one\nline two"


def test_parse_ignores_non_text_events():
    """Non-text events (type=tool, type=error) are skipped."""
    lines = (
        json.dumps({"type": "tool", "part": {"name": "read"}}) + "\n"
        + json.dumps({"type": "text", "part": {"text": "keep this"}}) + "\n"
        + json.dumps({"type": "error", "message": "oops"})
    )
    assert parse_opencode_stdout(lines) == "keep this"


def test_parse_ignores_malformed_lines():
    """Non-JSON lines and empty lines are silently skipped."""
    lines = "not json\n\n{bad json{}\n" + json.dumps({"type": "text", "part": {"text": "ok"}})
    assert parse_opencode_stdout(lines) == "ok"


def test_parse_empty_input():
    """Empty string returns empty string."""
    assert parse_opencode_stdout("") == ""
    assert parse_opencode_stdout(None) == ""


def test_parse_text_part_missing_text_key():
    """Text event with no 'text' in part is skipped."""
    line = json.dumps({"type": "text", "part": {"content": "no text key"}})
    assert parse_opencode_stdout(line) == ""


# --- extract_json_from_text ---


def test_extract_plain_json():
    """Plain JSON object extracted directly."""
    text = '{"children": [{"id": "a"}]}'
    result = extract_json_from_text(text)
    assert result == {"children": [{"id": "a"}]}


def test_extract_json_from_markdown_block():
    """JSON inside ```json ... ``` block extracted."""
    text = 'Some text\n```json\n{"verdict": "pass"}\n```\nMore text'
    result = extract_json_from_text(text)
    assert result == {"verdict": "pass"}


def test_extract_json_from_bare_markdown_block():
    """JSON inside bare ``` ... ``` block (no language tag)."""
    text = '```\n{"key": "value"}\n```'
    result = extract_json_from_text(text)
    assert result == {"key": "value"}


def test_extract_json_with_whitespace():
    """Whitespace around JSON is handled."""
    text = '  \n  {"a": 1}  \n  '
    result = extract_json_from_text(text)
    assert result == {"a": 1}


def test_extract_raises_on_invalid_json():
    """Raises JSONDecodeError on unparseable text."""
    with pytest.raises(json.JSONDecodeError):
        extract_json_from_text("not json at all")


def test_extract_raises_on_empty():
    """Raises on empty string."""
    with pytest.raises(json.JSONDecodeError):
        extract_json_from_text("")


def test_extract_handles_nested_json():
    """Nested JSON structures parsed correctly."""
    nested = {"gaps": [{"index": 0, "reason": "missing"}], "verdict": "fail"}
    text = f"```json\n{json.dumps(nested)}\n```"
    result = extract_json_from_text(text)
    assert result == nested
