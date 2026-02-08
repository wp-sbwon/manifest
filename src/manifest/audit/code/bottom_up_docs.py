"""
Build intent and architecture from code with LLM.

CodeExtractor makes blueprint_code.json. This makes intent_code.json and
architecture_code.json from code (same shape as top-down docs).
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional, Callable, Awaitable

from manifest.core.logger import get_logger

logger = get_logger(__name__)

INTENT_SCHEMA = {
    "version": "1.0",
    "sprint": "string",
    "features": [{"id": "string", "name": "string", "description": "string", "components": []}],
}

# Manifest View expects goals as list of dicts with id?, name, description, status.
ARCHITECTURE_SCHEMA = {
    "version": "1.0",
    "features": [{"id": "string", "name": "string", "components": [], "requirements": []}],
    "requirements": [{"id": "string", "description": "string", "components": []}],
    "goals": [{"id": "string", "name": "string", "description": "string", "status": "string"}],
}

PROMPT_TEMPLATE = """Infer intent and architecture from the code below. Output two JSON blobs (same shape as top-down docs).

## Code (blueprint_code)
{blueprint_summary}

## Code context (key files)
{code_context}

## Output
Two JSON objects, one after the other, no other text:

1. **intent**: version, sprint, features (id, name, description, components).
2. **architecture**: version, features, requirements, goals. goals = list of {{id, name, description, status}}. status = Planned | In Progress | Done | Deviation.

Intent example:
{{"version": "1.0", "sprint": "", "features": [{{"id": "f1", "name": "...", "description": "...", "components": []}}]}}

Architecture example (goals are objects):
{{"version": "1.0", "features": [...], "requirements": [], "goals": [{{"id": "g1", "name": "Goal name", "description": "What it means.", "status": "Planned"}}]}}

Output: intent JSON, then "---", then architecture JSON.
"""


def _truncate_blueprint(blueprint: Dict[str, Any], max_components: int = 80) -> str:
    """Short summary of blueprint for prompt."""
    from manifest.audit.entity_schema import non_root_entities, entity_display_name

    entities = non_root_entities(blueprint)[:max_components]
    lines = []
    for e in entities:
        name = entity_display_name(e)
        r = e.get("reality") or {}
        typ = r.get("type", e.get("type", "?"))
        file_path = r.get("symbol", e.get("file", ""))
        lines.append(f"- {name or e.get('id', '?')} ({typ}) @ {file_path}")
    return "\n".join(lines) if lines else "(no nodes)"


def _read_file_sample(path: Path, max_chars: int = 4000) -> str:
    """Read a file with a size limit."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read(max_chars)
    except Exception as e:
        logger.debug("_read_file_sample failed for %s: %s", path, e)
        return ""


async def generate_higher_level_docs_from_code(
    manifest_dir: Path,
    project_root: Path,
    llm_caller: Optional[Callable[[str, Dict[str, Any]], Awaitable[str]]] = None,
    code_files: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Generate intent_code.json and architecture_code.json from code using an LLM.

    Args:
        manifest_dir: Path to .manifest (where intent_code.json, architecture_code.json are written).
        project_root: Project root (for resolving code file paths).
        llm_caller: Async callable (prompt: str, context: dict) -> str. If None, no generation is performed.
        code_files: Optional list of file paths (relative or absolute) to include as context.

    Returns:
        {"intent": <saved intent dict or None>, "architecture": <saved architecture dict or None>, "error": <str or None>}
    """
    if not llm_caller:
        logger.debug("No LLM caller provided; skipping bottom-up intent/architecture generation")
        return {"intent": None, "architecture": None, "error": None}

    from manifest.audit.blueprint.blueprint_loader import BlueprintLoader

    bottom_blueprint = BlueprintLoader.load_code_blueprint(manifest_dir)
    blueprint_summary = _truncate_blueprint(bottom_blueprint)

    code_context = ""
    if code_files:
        for fp in code_files[:10]:  # Limit files
            path = Path(fp) if not isinstance(fp, Path) else fp
            if not path.is_absolute():
                path = project_root / path
            if path.exists():
                code_context += f"\n### {path.name}\n```\n{_read_file_sample(path)}\n```\n"

    prompt = PROMPT_TEMPLATE.format(
        blueprint_summary=blueprint_summary,
        code_context=code_context or "(no file context)",
    )
    context = {"manifest_dir": str(manifest_dir), "project_root": str(project_root)}

    try:
        response = await llm_caller(prompt, context)
    except Exception as e:
        logger.warning("LLM call failed for bottom-up docs: %s", e)
        return {"intent": None, "architecture": None, "error": str(e)}

    intent_data = None
    architecture_data = None

    try:
        if "---" in response:
            part1, _, part2 = response.partition("---")
            intent_str = part1.strip()
            arch_str = part2.strip()
        else:
            intent_str = response.strip()
            arch_str = ""

        # Try to parse intent (may be inside markdown code block)
        for block in (intent_str,):
            for start in ("```json", "```"):
                if start in block:
                    block = block.split(start, 1)[-1].split("```", 1)[0].strip()
                    break
            try:
                intent_data = json.loads(block)
                break
            except json.JSONDecodeError:
                continue

        if arch_str:
            for block in (arch_str,):
                for start in ("```json", "```"):
                    if start in block:
                        block = block.split(start, 1)[-1].split("```", 1)[0].strip()
                        break
                try:
                    architecture_data = json.loads(block)
                    break
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        logger.warning("Failed to parse LLM response for bottom-up docs: %s", e)
        return {"intent": None, "architecture": None, "error": str(e)}

    manifest_dir = Path(manifest_dir)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    if intent_data:
        intent_path = manifest_dir / "intent_code.json"
        try:
            with open(intent_path, "w", encoding="utf-8") as f:
                json.dump(intent_data, f, indent=2, ensure_ascii=False)
            logger.info("Wrote %s", intent_path)
        except Exception as e:
            logger.warning("Failed to write intent_code.json: %s", e)

    if architecture_data:
        arch_path = manifest_dir / "architecture_code.json"
        try:
            with open(arch_path, "w", encoding="utf-8") as f:
                json.dump(architecture_data, f, indent=2, ensure_ascii=False)
            logger.info("Wrote %s", arch_path)
        except Exception as e:
            logger.warning("Failed to write architecture_code.json: %s", e)

    return {"intent": intent_data, "architecture": architecture_data, "error": None}
