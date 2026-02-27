"""Calculator CLI: parse args, compute, format, print."""
import sys
from cli.parser import parse_args
from engine.calculator import compute
from output.formatter import format_result


def main() -> int:
    op, a, b = parse_args(sys.argv[1:])
    result = compute(op, a, b)
    print(format_result(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
