"""
Test implementer: build context per entity; opencode fills test stub logic.

Follows layer_writer.py patterns: build context dict, invoke opencode CLI,
verify results via test_result_collector.
"""
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from manifest.audit.code.test_result_collector import collect_test_results
from manifest.core.logger import get_logger
from manifest.io.blueprint_io import load_blueprint

logger = get_logger(__name__)


def build_test_implementer_context(
    manifest_dir: Path,
    entity_id: str,
    project_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Build context dict for test-implementer agent.

    Loads blueprint design, locates entity, finds test file and stubs.
    Raises ValueError if entity missing, test file missing, or no stubs found.
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

    all_results = collect_test_results(project_root)
    stubs = all_results.get(entity_id, [])
    if not stubs or not any(s.get("status") == "stub" for s in stubs):
        raise ValueError(f"No test stubs found for entity '{entity_id}'")

    # Extract design fields
    governance = entity.get("governance") or {}
    assertions = governance.get("assertions") or []
    protocol = entity.get("protocol") or {}
    narrative = entity.get("narrative") or {}
    symbol = entity.get("symbol") or ""
    profile = entity.get("profile") or {}

    return {
        "entity_id": entity_id,
        "test_file": str(test_file.resolve()),
        "stubs": stubs,
        "design": {
            "assertions": assertions,
            "protocol": {"input": protocol.get("input"), "output": protocol.get("output")},
            "narrative": {"role": narrative.get("role"), "mission": narrative.get("mission")},
            "symbol": symbol,
            "profile": profile,
        },
        "project_root": str(project_root.resolve()),
    }


TEST_IMPLEMENTER_PROMPT = (
    "Read the test context from the attached file context.json. "
    "Fill in the logic for each stub test function (status='stub') using mocks "
    "and fixtures based on the assertion docstrings and design context. "
    "Do not remove or alter @pytest.mark.manifest_assertion decorators. "
    "Edit the test file directly."
)


def implement_test_stubs(
    context: Dict[str, Any],
    project_root: Path,
) -> Dict[str, Any]:
    """
    Invoke opencode test-implementer to fill test stub logic.

    Returns {"implemented": int, "remaining_stubs": int}.
    """
    project_root = Path(project_root)
    entity_id = context["entity_id"]

    opencode_path = shutil.which("opencode")
    if not opencode_path:
        raise RuntimeError(
            "opencode not on PATH. "
            "Test implementation requires opencode."
        )

    # Count pre-run stubs
    pre_stubs = sum(1 for s in context.get("stubs", []) if s.get("status") == "stub")

    with tempfile.TemporaryDirectory(prefix="manifest_test_impl_") as tmp:
        context_path = Path(tmp) / "context.json"
        with open(context_path, "w", encoding="utf-8") as f:
            json.dump(context, f, indent=2, ensure_ascii=False)

        cmd = [
            opencode_path,
            "run",
            TEST_IMPLEMENTER_PROMPT,
            "--agent", "test-implementer",
            "--dir", str(project_root.resolve()),
            "--format", "json",
            "-f", str(context_path.resolve()),
        ]

        timeout = int(os.environ.get("MANIFEST_TEST_IMPLEMENTER_TIMEOUT", "180"))
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
                f"Test implementer timed out after {timeout}s. "
                "Set MANIFEST_TEST_IMPLEMENTER_TIMEOUT for larger projects."
            )
        except FileNotFoundError:
            raise RuntimeError("opencode not found on PATH")

        if result.returncode != 0:
            stderr = ((result.stdout or "") + (result.stderr or "")).strip()
            excerpt = stderr[:400].replace("\n", " ") if stderr else ""
            raise RuntimeError(
                f"Test implementer failed (exit {result.returncode}). "
                f"Output: {excerpt}."
            )

    # Post-run verification: re-collect and count remaining stubs
    post_results = collect_test_results(project_root)
    post_stubs_list = post_results.get(entity_id, [])
    post_stubs = sum(1 for s in post_stubs_list if s.get("status") == "stub")
    implemented = pre_stubs - post_stubs

    return {"implemented": implemented, "remaining_stubs": post_stubs}
