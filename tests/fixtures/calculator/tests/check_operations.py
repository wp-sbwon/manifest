"""Tests for arithmetic (engine.calculator)."""
from engine.calculator import add, sub, compute


def test_add():
    assert add(2, 3) == 5


def test_sub():
    assert sub(5, 2) == 3


def test_compute_add():
    assert compute("add", 1, 2) == 3


def test_compute_sub():
    assert compute("sub", 5, 1) == 4
