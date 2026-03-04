"""
Collect test results by AST-parsing test files for @pytest.mark.manifest_assertion markers.
Returns {entity_id: [{index, assertion, status}]} where status is "stub" or "implemented".
"""
import ast
from pathlib import Path
from typing import Any, Dict, List


def collect_test_results(project_root: Path) -> Dict[str, List[Dict[str, Any]]]:
    """Walk project_root/tests/ for test_*.py files, parse manifest_assertion markers.

    Returns {entity_id: [{index: int, assertion: str, status: "stub"|"implemented"}]}.
    """
    project_root = Path(project_root)
    tests_dir = project_root / "tests"
    if not tests_dir.is_dir():
        return {}

    results: Dict[str, List[Dict[str, Any]]] = {}
    for test_file in tests_dir.rglob("test_*.py"):
        _parse_test_file(test_file, results)
    return results


def _parse_test_file(
    path: Path, results: Dict[str, List[Dict[str, Any]]]
) -> None:
    """Parse a single test file for manifest_assertion markers."""
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (SyntaxError, OSError):
        return

    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for deco in node.decorator_list:
            entity_id, index = _extract_marker(deco)
            if entity_id is None:
                continue
            docstring = ast.get_docstring(node) or ""
            status = "stub" if _is_stub(node) else "implemented"
            results.setdefault(entity_id, []).append({
                "index": index,
                "assertion": docstring,
                "status": status,
            })


def _extract_marker(deco: ast.expr) -> tuple:
    """Extract (entity_id, index) from @pytest.mark.manifest_assertion(entity_id, index).

    Returns (None, None) if not a manifest_assertion marker.
    """
    if not isinstance(deco, ast.Call):
        return None, None
    func = deco.func
    # Match pytest.mark.manifest_assertion
    if isinstance(func, ast.Attribute) and func.attr == "manifest_assertion":
        mid = func.value
        if (
            isinstance(mid, ast.Attribute)
            and mid.attr == "mark"
            and isinstance(mid.value, ast.Attribute)
            and mid.value.attr == "mark"
        ):
            pass  # pytest.mark.mark.manifest_assertion — unlikely
        # Standard: pytest.mark.manifest_assertion
        if not (
            isinstance(mid, ast.Attribute)
            and mid.attr == "mark"
            and isinstance(mid.value, ast.Name)
            and mid.value.id == "pytest"
        ):
            return None, None
    else:
        return None, None

    args = deco.args
    if len(args) < 2:
        return None, None
    entity_id_node, index_node = args[0], args[1]
    entity_id = _const_value(entity_id_node)
    index = _const_value(index_node)
    if not isinstance(entity_id, str) or not isinstance(index, int):
        return None, None
    return entity_id, index


def _const_value(node: ast.expr) -> Any:
    """Extract a constant value from an AST node."""
    if isinstance(node, ast.Constant):
        return node.value
    return None


def _is_stub(func_node: ast.FunctionDef) -> bool:
    """True if function body is a single `raise NotImplementedError` (with optional docstring)."""
    body = func_node.body
    stmts = []
    for stmt in body:
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
            continue  # skip docstring
        stmts.append(stmt)
    if len(stmts) != 1:
        return False
    stmt = stmts[0]
    if isinstance(stmt, ast.Raise) and stmt.exc is not None:
        if isinstance(stmt.exc, ast.Call):
            func = stmt.exc.func
            return isinstance(func, ast.Name) and func.id == "NotImplementedError"
        if isinstance(stmt.exc, ast.Name):
            return stmt.exc.id == "NotImplementedError"
    return False
