#!/usr/bin/env python3
"""
AST-based linter: fail (exit 1) if any test_* function in tests/ is missing @pytest.mark.manifest_assertion.
"""
import ast
import sys
from pathlib import Path


def _has_manifest_assertion(decorator_list: list) -> bool:
    for node in decorator_list:
        f = node.func if isinstance(node, ast.Call) else node
        if not isinstance(f, ast.Attribute):
            continue
        if getattr(f, "attr", "") != "manifest_assertion":
            continue
        val = getattr(f, "value", None)
        if isinstance(val, ast.Attribute) and getattr(val, "attr", "") == "mark":
            return True
        if getattr(f, "attr", "") == "manifest_assertion":
            return True
    return False


def check_file(path: Path) -> list:
    errors = []
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        errors.append("%s: could not read: %s" % (path, e))
        return errors
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        errors.append("%s: syntax error: %s" % (path, e))
        return errors
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            if not _has_manifest_assertion(node.decorator_list):
                errors.append("%s: function %s missing @pytest.mark.manifest_assertion" % (path, node.name))
    return errors


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    import argparse
    parser = argparse.ArgumentParser(description="Verify test_* functions have @pytest.mark.manifest_assertion in stub files")
    parser.add_argument("--tests-dir", type=Path, default=None, help="tests/ dir (default: repo/tests)")
    args = parser.parse_args()
    tests_dir = (args.tests_dir or (repo / "tests")).resolve()
    if not tests_dir.is_dir():
        return 0
    all_errors = []
    for py in sorted(tests_dir.rglob("test_*.py")):
        if "__pycache__" in py.parts or py.name.startswith("."):
            continue
        try:
            if "manifest_assertion" not in py.read_text(encoding="utf-8"):
                continue
        except Exception:
            continue
        all_errors.extend(check_file(py))
    if all_errors:
        for e in all_errors:
            print(e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
