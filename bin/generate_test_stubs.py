#!/usr/bin/env python3
"""
Generate test stubs from blueprint_design.json.

Reads design; for each entity (except root) writes tests/test_<entity_id>.py with one
function per governance.assertions item: test_<id>_assertion_<i>, docstring = assertion,
raise NotImplementedError, @pytest.mark.manifest_assertion(entity_id, assertion_index).
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from manifest.audit.entity_schema import PROJECT_ROOT_ID


def _safe_module_name(eid: str) -> str:
    return eid.replace(".", "_").replace("-", "_")


def generate_stubs(manifest_dir: Path, tests_dir: Path) -> int:
    design_file = manifest_dir / "blueprint_design.json"
    if not design_file.exists():
        print(f"Missing {design_file}", file=sys.stderr)
        return 1
    with open(design_file, "r", encoding="utf-8") as f:
        design = json.load(f)
    entities = design.get("entities") or []
    tests_dir.mkdir(parents=True, exist_ok=True)
    for ent in entities:
        eid = (ent.get("id") or "").strip()
        if not eid or eid == PROJECT_ROOT_ID:
            continue
        assertions = ent.get("governance") or {}
        if isinstance(assertions, dict):
            assertions = assertions.get("assertions") or []
        if not isinstance(assertions, list):
            assertions = []
        if not assertions:
            assertions = [""]
        mod_name = _safe_module_name(eid)
        lines = [
            '"""Generated test stubs for entity %s. Assertions from blueprint_design.json."""' % eid,
            "import pytest",
            "",
        ]
        for i, text in enumerate(assertions):
            doc = (text or "").strip() or "Assertion %d" % i
            if '"""' in doc:
                doc = doc.replace('"""', "'")
            lines.append('@pytest.mark.manifest_assertion("%s", %d)' % (eid, i))
            lines.append('def test_%s_assertion_%d():' % (mod_name, i))
            lines.append('    """%s"""' % doc)
            lines.append("    raise NotImplementedError")
            lines.append("")
        out_file = tests_dir / ("test_%s.py" % mod_name)
        out_file.write_text("\n".join(lines), encoding="utf-8")
    return 0


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Generate test stubs from blueprint_design.json")
    parser.add_argument("--manifest-dir", type=Path, default=None, help=".manifest dir (default: cwd/.manifest)")
    parser.add_argument("--tests-dir", type=Path, default=None, help="tests/ dir (default: manifest_dir.parent/tests)")
    args = parser.parse_args()
    manifest_dir = (args.manifest_dir or (Path.cwd() / ".manifest")).resolve()
    tests_dir = args.tests_dir or (manifest_dir.parent / "tests")
    tests_dir = tests_dir.resolve()
    return generate_stubs(manifest_dir, tests_dir)


if __name__ == "__main__":
    sys.exit(main())
