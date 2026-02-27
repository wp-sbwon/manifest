"""Parse terminal input into op and two numbers."""


def parse_args(argv):  # noqa: D401 - public API
    """Return (op, a, b) from argv. Default: add 0 0."""
    if len(argv) < 3:
        return "add", 0.0, 0.0
    op = (argv[0] or "add").lower()
    try:
        a = float(argv[1])
        b = float(argv[2])
    except (ValueError, TypeError):
        a, b = 0.0, 0.0
    return op, a, b
