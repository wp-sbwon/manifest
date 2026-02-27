"""Bottom-up agent: reads extraction outline, actual code, and design (guide); produces blueprint_code from code."""
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

from manifest.audit.entity_validation import normalize_for_schema, validate_blueprint_data
from manifest.core.app_temp import get_manifest_tmp_dir
from manifest.core.logger import get_logger
from manifest.opencode.run_helpers import (
    extract_json_from_text,
    parse_opencode_stdout,
)

logger = get_logger(__name__)


def _normalize_agent_refs_to_entity_ids(blueprint: Dict[str, Any]) -> None:
    """Rewrite refs like 'entity.symbol' to 'entity' so validation passes. Mutates blueprint."""
    entities = blueprint.get("entities") or []
    valid_ids = {e.get("id") for e in entities if e.get("id")}
    if not valid_ids:
        return

    def to_entity_id(ref: str) -> str:
        s = (ref or "").strip()
        if not s or s in valid_ids or s.startswith("external-"):
            return s
        if "." in s:
            prefix = s.split(".", 1)[0]
            if prefix in valid_ids:
                return prefix
        return s

    for e in entities:
        deps = e.get("dependencies") or []
        normalized_deps = [
            to_entity_id(d if isinstance(d, str) else (d.get("to") or d.get("id") or ""))
            for d in deps
        ]
        e["dependencies"] = list(dict.fromkeys(d for d in normalized_deps if d in valid_ids))
        oc = e.get("outgoing_contracts") or []
        for c in oc:
            if isinstance(c, dict) and "to" in c:
                c["to"] = to_entity_id(c.get("to") or "")
        e["outgoing_contracts"] = [c for c in oc if isinstance(c, dict) and (c.get("to") or "").strip() in valid_ids]


DESIGN_FILENAME = "design.json"
EXTRACTION_FILENAME = "extraction.json"

DEFAULT_TIMEOUT = 300
MAX_RETRIES = 3
RETRY_DELAYS = (5, 15, 30)

ENRICH_PROMPT_TEMPLATE = (
    "You have three inputs: (1) the code extraction outline in {extraction_name}, (2) the actual code in this project (read the source files), (3) the design blueprint in {design_name}. "
    "Produce the blueprint_code document (entity-layer: version, root_id, entities with id, children, narrative, blueprint, protocol, profile, governance, symbol, traits, topology_actual, preview, outgoing_contracts). "
    "RULES: The result MUST be based strictly on the actual code. Include ONLY entities present in the code; omit any design entity not in the code. "
    "NAMING: When an extraction entity has design_id, use that as its id and use design entity ids everywhere: in children, dependencies, and outgoing_contracts[].to (so top-down and bottom-up share the same names and references). Use extraction id only when there is no design_id. "
    "Output a valid blueprint JSON. Output ONLY valid JSON, no markdown or explanation."
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
    _normalize_agent_refs_to_entity_ids(out)
    valid, errors = validate_blueprint_data(out)
    if not valid and errors:
        raise RuntimeError(
            "Enrich output failed blueprint validation: " + "; ".join(errors[:5])
        )
    return out


def enrich_code_blueprint(
    design_blueprint: Dict[str, Any],
    extracted_blueprint: Dict[str, Any],
    project_root: Path,
    manifest_dir: Path,
) -> Dict[str, Any]:
    """
    Bottom-up: agent reads (1) extraction outline, (2) actual code in project_root, (3) blueprint_design.
    Produces blueprint_code from actual code only. Design is a guide; entities not in the code must not appear.
    Temp files are written to the manifest app temp dir (MANIFEST_TMP_DIR or system temp / manifest). Retries on transient failure.
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

    # Use app temp dir (system temp / manifest or MANIFEST_TMP_DIR); run-unique subdir per invocation.
    enrich_dir = Path(tempfile.mkdtemp(dir=get_manifest_tmp_dir(), prefix="enrich_"))
    design_path = enrich_dir / DESIGN_FILENAME
    extraction_path = enrich_dir / EXTRACTION_FILENAME
    rel_design = DESIGN_FILENAME
    rel_extraction = EXTRACTION_FILENAME
    prompt = ENRICH_PROMPT_TEMPLATE.format(
        design_name=rel_design,
        extraction_name=rel_extraction,
    )
    cmd = [
        opencode_path,
        "run",
        prompt,
        "--agent", "enrich-code-blueprint",
        "--dir", str(project_root.resolve()),
        "--format", "json",
        "-f", str(design_path.resolve()),
        "-f", str(extraction_path.resolve()),
    ]
    try:
        last_error: Optional[Exception] = None
        for attempt in range(MAX_RETRIES):
            with open(design_path, "w", encoding="utf-8") as f:
                json.dump(design_blueprint, f, indent=2, ensure_ascii=False)
            with open(extraction_path, "w", encoding="utf-8") as f:
                json.dump(extracted_blueprint, f, indent=2, ensure_ascii=False)
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
        shutil.rmtree(enrich_dir, ignore_errors=True)
