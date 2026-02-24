"""Invoke opencode backend to fill intent from code (ground truth); design used only for structure."""
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

from manifest.audit.entity_validation import normalize_for_schema, validate_blueprint_data
from manifest.core.logger import get_logger

logger = get_logger(__name__)

ENRICH_INSTRUCTIONS = """
Use the design blueprint ONLY for structure and entity identity: same root_id, entity ids, and children.
Fill intent (narrative, profile, governance, protocol) from the CODE: describe what the code actually does.
The draft has reality from extraction (file, symbol, methods, dependencies). Infer intent from that.
Do not copy or paraphrase design intent. Output must be ground truth from the code.
"""

DEFAULT_TIMEOUT = 300
MAX_RETRIES = 3
RETRY_DELAYS = (5, 15, 30)


def _run_enrich_once(
    cmd: list,
    output_path: Path,
    project_root: Path,
    env: dict,
    timeout: int,
) -> Dict[str, Any]:
    """Run opencode once; raise with actionable error on failure."""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(project_root),
        env=env,
    )
    if result.returncode != 0:
        stderr = (result.stdout or "") + (result.stderr or "")
        stderr = stderr.strip()
        msg = (
            f"opencode enrich-code-blueprint exited with code {result.returncode}. "
            "Check that opencode is installed and the project parses correctly. "
        )
        if stderr:
            excerpt = stderr[:500].replace("\n", " ")
            msg += f"Last output: {excerpt}"
        raise RuntimeError(msg)

    if not output_path.exists():
        raise RuntimeError(
            "opencode did not write enriched blueprint. "
            "The subprocess may have crashed or written to a different path. "
            "Check opencode logs and ensure it supports enrich-code-blueprint."
        )

    try:
        with open(output_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as e:
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                content = f.read(500)
        except Exception:
            content = "(unreadable)"
        raise RuntimeError(
            f"opencode wrote invalid JSON: {e}. "
            f"Output file preview: {content!r}. "
            "opencode may have written an error message or partial output. Check opencode logs."
        )

    if not isinstance(raw, dict):
        raise RuntimeError(
            "opencode output is not a JSON object. "
            "Expected a blueprint with version, root_id, entities."
        )

    out = normalize_for_schema(raw)
    valid, errors = validate_blueprint_data(out)
    if not valid and errors:
        raise RuntimeError(
            "opencode output failed blueprint validation: " + "; ".join(errors[:5])
        )
    return out


def enrich_code_blueprint(
    design_blueprint: Dict[str, Any],
    code_draft: Dict[str, Any],
    project_root: Path,
    manifest_dir: Path,
) -> Dict[str, Any]:
    """
    Fill intent in code_draft via opencode; design for match/structure only, intent from code (ground truth).
    Retries on transient failures. Validates output before returning.
    Raises with actionable message if opencode is unavailable or enrichment fails.
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

    with tempfile.TemporaryDirectory(prefix="manifest_enrich_") as tmp:
        design_path = Path(tmp) / "design.json"
        draft_path = Path(tmp) / "draft.json"
        output_path = Path(tmp) / "enriched.json"
        instructions_path = Path(tmp) / "instructions.txt"
        with open(design_path, "w", encoding="utf-8") as f:
            json.dump(design_blueprint, f, indent=2, ensure_ascii=False)
        with open(draft_path, "w", encoding="utf-8") as f:
            json.dump(code_draft, f, indent=2, ensure_ascii=False)
        with open(instructions_path, "w", encoding="utf-8") as f:
            f.write(ENRICH_INSTRUCTIONS.strip())

        env = os.environ.copy()
        env["MANIFEST_ENRICH_DESIGN"] = str(design_path)
        env["MANIFEST_ENRICH_DRAFT"] = str(draft_path)
        env["MANIFEST_ENRICH_OUTPUT"] = str(output_path)
        env["MANIFEST_ENRICH_INSTRUCTIONS"] = str(instructions_path)
        env["MANIFEST_ENRICH_INSTRUCTIONS_TEXT"] = ENRICH_INSTRUCTIONS.strip()
        cmd = [
            opencode_path,
            str(project_root),
            "enrich-code-blueprint",
            "--design", str(design_path),
            "--draft", str(draft_path),
            "--output", str(output_path),
        ]

        last_error: Optional[Exception] = None
        for attempt in range(MAX_RETRIES):
            try:
                return _run_enrich_once(cmd, output_path, project_root, env, timeout)
            except subprocess.TimeoutExpired:
                last_error = RuntimeError(
                    f"opencode enrich-code-blueprint timed out after {timeout}s. "
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
