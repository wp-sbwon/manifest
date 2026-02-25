"""Fill narrative, governance, etc. from code; design blueprint as context for naming/wording."""
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional

from manifest.audit.entity_validation import normalize_for_schema, validate_blueprint_data
from manifest.core.logger import get_logger
from manifest.opencode.run_helpers import (
    extract_json_from_text,
    parse_opencode_stdout,
)

logger = get_logger(__name__)

ENRICH_DIR_NAME = ".manifest_enrich"
DESIGN_FILENAME = "design.json"
DRAFT_FILENAME = "draft.json"

DEFAULT_TIMEOUT = 300
MAX_RETRIES = 3
RETRY_DELAYS = (5, 15, 30)

ENRICH_PROMPT_TEMPLATE = (
    "Read design blueprint from {design_name} and code draft from {draft_name}. "
    "Use design as context so names and wording align. Same structure (root_id, entity ids, children). "
    "Fill narrative, profile, governance, protocol from the code draft (mechanical fields already set). "
    "Output a valid blueprint JSON with version, root_id, entities (same schema as design). "
    "Output ONLY valid JSON, no markdown or explanation."
)


def _run_enrich_once(
    cmd: list,
    project_root: Path,
    timeout: int,
) -> Dict[str, Any]:
    """Run opencode once; parse stdout, validate blueprint, return. Raises on failure."""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(project_root),
    )
    if result.returncode != 0:
        stderr = (result.stdout or "") + (result.stderr or "")
        stderr = stderr.strip()
        msg = (
            f"opencode exited with code {result.returncode}. "
            "Check that opencode is installed and the project parses correctly. "
        )
        if stderr:
            excerpt = stderr[:500].replace("\n", " ")
            msg += f"Last output: {excerpt}"
        raise RuntimeError(msg)

    combined = (result.stdout or "") + "\n" + (result.stderr or "")
    merged = parse_opencode_stdout(combined)
    if not merged:
        preview = (combined.strip()[:500] + "…") if len((combined or "").strip()) > 500 else (combined or "").strip()
        raise RuntimeError(
            "No response from opencode (no JSONL text events in stdout/stderr). "
            "Ensure opencode.json is in the project and the enrich-code-blueprint agent is defined. "
            f"Output preview: {preview!r}"
        )

    try:
        raw = extract_json_from_text(merged)
    except (json.JSONDecodeError, KeyError) as e:
        raise RuntimeError(
            f"opencode wrote invalid JSON: {e}. "
            f"Output preview: {merged[:200]!r}. "
            "Check opencode logs."
        )

    if not isinstance(raw, dict):
        raise RuntimeError(
            "Enrich output is not a JSON object. "
            "Expected a blueprint with version, root_id, entities."
        )

    out = normalize_for_schema(raw)
    valid, errors = validate_blueprint_data(out)
    if not valid and errors:
        raise RuntimeError(
            "Enrich output failed blueprint validation: " + "; ".join(errors[:5])
        )
    return out


def enrich_code_blueprint(
    design_blueprint: Dict[str, Any],
    code_draft: Dict[str, Any],
    project_root: Path,
    manifest_dir: Path,
) -> Dict[str, Any]:
    """
    Fill narrative, governance, etc. in code_draft from code; design as context for alignment.
    Retries on transient failure. Validates and returns blueprint; raises if opencode unavailable or enrichment fails.
    """
    project_root = Path(project_root)
    manifest_dir = Path(manifest_dir)
    opencode_path = shutil.which("opencode")
    if not opencode_path:
        raise RuntimeError(
            "opencode is not on PATH. "
            "Install opencode and ensure it is available (e.g. pip install opencode, or add to PATH). "
            "Code blueprint enrichment requires opencode."
        )

    timeout = int(os.environ.get("MANIFEST_ENRICH_TIMEOUT", str(DEFAULT_TIMEOUT)))

    enrich_dir = project_root / ENRICH_DIR_NAME
    enrich_dir.mkdir(parents=True, exist_ok=True)
    design_path = enrich_dir / DESIGN_FILENAME
    draft_path = enrich_dir / DRAFT_FILENAME
    try:
        with open(design_path, "w", encoding="utf-8") as f:
            json.dump(design_blueprint, f, indent=2, ensure_ascii=False)
        with open(draft_path, "w", encoding="utf-8") as f:
            json.dump(code_draft, f, indent=2, ensure_ascii=False)

        rel_design = f"{ENRICH_DIR_NAME}/{DESIGN_FILENAME}"
        rel_draft = f"{ENRICH_DIR_NAME}/{DRAFT_FILENAME}"
        prompt = ENRICH_PROMPT_TEMPLATE.format(
            design_name=rel_design,
            draft_name=rel_draft,
        )
        cmd = [
            opencode_path,
            "run",
            prompt,
            "--agent", "enrich-code-blueprint",
            "--dir", str(project_root.resolve()),
            "--format", "json",
            "-f", str(design_path.resolve()),
            "-f", str(draft_path.resolve()),
        ]

        last_error: Optional[Exception] = None
        for attempt in range(MAX_RETRIES):
            try:
                return _run_enrich_once(cmd, project_root, timeout)
            except subprocess.TimeoutExpired:
                last_error = RuntimeError(
                    f"opencode timed out after {timeout}s. "
                    f"Try increasing MANIFEST_ENRICH_TIMEOUT (e.g. 600) for large projects."
                )
                logger.warning("Enrich attempt %d timed out", attempt + 1)
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAYS[attempt]
                    logger.info("Retrying in %ds (attempt %d/%d)", delay, attempt + 2, MAX_RETRIES)
                    time.sleep(delay)
                else:
                    raise last_error
            except FileNotFoundError:
                raise RuntimeError("opencode binary not found on PATH after resolution.")
            except RuntimeError as e:
                is_transient = "exited with code" in str(e)
                if is_transient and attempt < MAX_RETRIES - 1:
                    last_error = e
                    delay = RETRY_DELAYS[attempt]
                    logger.info("Retrying in %ds after exit failure (attempt %d/%d)", delay, attempt + 2, MAX_RETRIES)
                    time.sleep(delay)
                else:
                    raise
        if last_error is not None:
            raise last_error
        raise RuntimeError("Enrichment failed after retries")
    finally:
        if design_path.exists():
            design_path.unlink(missing_ok=True)
        if draft_path.exists():
            draft_path.unlink(missing_ok=True)
        if enrich_dir.exists() and not any(enrich_dir.iterdir()):
            enrich_dir.rmdir()
