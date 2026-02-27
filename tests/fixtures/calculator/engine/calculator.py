"""Pure arithmetic: add, sub (side-effect free)."""


def add(a: float, b: float) -> float:
    """Return a + b."""
    return a + b


def sub(a: float, b: float) -> float:
    """Return a - b."""
    return a - b


def compute(op: str, a: float, b: float) -> float:
    """Dispatch op to add or sub. Unknown op returns 0."""
    if op == "add":
        return add(a, b)
    if op == "sub":
        return sub(a, b)
    return 0.0
