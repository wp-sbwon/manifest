"""Tests for output.formatter."""
from output.formatter import format_result


def test_format_result():
    assert format_result(3.14) == "3.14"
    assert format_result(0) == "0"
