"""
Main entry point for Manifest.

Runs launcher: View (visualization dashboard) and OpenCode terminal.
Usage: manifest | python -m manifest
"""


def main() -> int:
    """Entry point for console script and python -m manifest."""
    from manifest.launcher import main as launcher_main
    return launcher_main()


if __name__ == "__main__":
    raise SystemExit(main())
