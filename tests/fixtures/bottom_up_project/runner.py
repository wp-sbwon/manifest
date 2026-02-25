"""Runner: orchestrates greeter and formatter."""

from greeter import greet
from formatter import format


def run(name: str) -> str:
    """Produce a greeting and return formatted result."""
    raw = greet(name)
    return format(raw)
