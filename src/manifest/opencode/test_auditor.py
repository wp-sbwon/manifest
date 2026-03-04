"""
Test auditor: build context per entity; opencode reviews tests against design assertions.

Follows layer_writer.py patterns: build context dict, invoke opencode CLI,
parse JSON output report.
"""
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from manifest.audit.blueprint.view_schema import load_view_schema
from manifest.audit.code.test_result_collector import collect_test_results
from manifest.core.logger import get_logger
from manifest.io.blueprint_io import load_blueprint
from manifest.opencode.run_helpers import extract_json_from_text, parse_opencode_stdout

logger = get_logger(__name__)


def build_test_auditor_context(
    manifest_dir: Path,
    entity_id: str,
    project_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Build context dict for test-auditor agent.

    Loads blueprint design, test file contents, test results, and view deviations.
    Raises ValueError if entity missing or test file missing.
    """
    manifest_dir = Path(manifest_dir)
    if project_root is None:
        project_root = manifest_dir.parent
    project_root = Path(project_root)

    blueprint = load_blueprint(manifest_dir)
    entities = blueprint.get("entities") or []
    entity = next((e for e in entities if e.get("id") == entity_id), None)
    if not entity:
        raise ValueError(f"Entity '{entity_id}' not found in blueprint")

    test_file = project_root / "tests" / f"test_{entity_id}.py"
    if not test_file.exists():
        raise ValueError(f"Test file not found: {test_file}")

    test_file_contents = test_file.read_text(encoding="utf-8")

    all_results = collect_test_results(project_root)
    test_results = all_results.get(entity_id, [])

    # Load view deviations
    view_schema = load_view_schema(manifest_dir)
    view_entities = view_schema.get("entities") or []
    view_ent = next((ve for ve in view_entities if ve.get("id") == entity_id), None)
    view_deviations = []
    if view_ent:
        validation = view_ent.get("validation") or {}
        view_deviations = validation.get("deviations") or []

    # Extract design fields
    governance = entity.get("governance") or {}
    assertions = governance.get("assertions") or []
    protocol = entity.get("protocol") or {}
    narrative = entity.get("narrative") or {}
    symbol = entity.get("symbol") or ""

    return {
        "entity_id": entity_id,
        "test_file": str(test_file.resolve()),
        "test_file_contents": test_file_contents,
        "design": {
            "assertions": assertions,
            "protocol": {"input": protocol.get("input"), "output": protocol.get("output")},
            "narrative": {"role": narrative.get("role"), "mission": narrative.get("mission")},
            "symbol": symbol,
        },
        "test_results": test_results,
        "view_deviations": view_deviations,
    }


TEST_AUDITOR_PROMPT = (
    "Read the test audit context from the attached file context.json. "
    "Review the implemented tests against the design assertions to ensure "
    "they rigorously and accurately prove the intent. "
    "Output a JSON report with: gaps (assertions not covered), "
    "coverage_issues (weak tests), verdict (pass/warn/fail), and recommendations."
)


def audit_entity_tests(
    context: Dict[str, Any],
    project_root: Path,
) -> Dict[str, Any]:
    """
    Invoke opencode test-auditor to review tests against design.

    Returns audit report: {entity_id, gaps, coverage_issues, verdict, recommendations}.
    """
    project_root = Path(project_root)
    entity_id = context["entity_id"]

    opencode_path = shutil.which("opencode")
    if not opencode_path:
        raise RuntimeError(
            "opencode not on PATH. "
            "Test auditing requires opencode."
        )

    with tempfile.TemporaryDirectory(prefix="manifest_test_audit_") as tmp:
        context_path = Path(tmp) / "context.json"
        with open(context_path, "w", encoding="utf-8") as f:
            json.dump(context, f, indent=2, ensure_ascii=False)

        cmd = [
            opencode_path,
            "run",
            TEST_AUDITOR_PROMPT,
            "--agent", "test-auditor",
            "--dir", str(project_root.resolve()),
            "--format", "json",
            "-f", str(context_path.resolve()),
        ]

        timeout = int(os.environ.get("MANIFEST_TEST_AUDITOR_TIMEOUT", "120"))
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(project_root),
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"Test auditor timed out after {timeout}s. "
                "Set MANIFEST_TEST_AUDITOR_TIMEOUT for larger projects."
            )
        except FileNotFoundError:
            raise RuntimeError("opencode not found on PATH")

        if result.returncode != 0:
            stderr = ((result.stdout or "") + (result.stderr or "")).strip()
            excerpt = stderr[:400].replace("\n", " ") if stderr else ""
            raise RuntimeError(
                f"Test auditor failed (exit {result.returncode}). "
                f"Output: {excerpt}."
            )

    # Parse JSON output from opencode stdout
    merged = parse_opencode_stdout(result.stdout or "")
    if not merged:
        return {"entity_id": entity_id, "gaps": [], "verdict": "error", "error": "No output from auditor"}

    try:
        data = extract_json_from_text(merged)
    except (json.JSONDecodeError, KeyError):
        return {"entity_id": entity_id, "gaps": [], "verdict": "error", "error": "Failed to parse auditor output"}

    if not isinstance(data, dict):
        return {"entity_id": entity_id, "gaps": [], "verdict": "error", "error": "Auditor output is not a JSON object"}

    return {
        "entity_id": entity_id,
        "gaps": data.get("gaps") or [],
        "coverage_issues": data.get("coverage_issues") or [],
        "verdict": data.get("verdict") or "error",
        "recommendations": data.get("recommendations") or [],
    }
