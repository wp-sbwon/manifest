"""
Bottom-up higher-level docs: generate intent and architecture from code with LLM.

Mechanical docs (blueprint_code.json) are produced by CodeExtractor. This module
produces intent_code.json and architecture_code.json in the same schema as top-down
docs, using an LLM to infer intent and architecture from the codebase structure.
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

ARCHITECTURE_SCHEMA = {
    "version": "1.0",
    "features": [{"id": "string", "name": "string", "components": [], "requirements": []}],
    "requirements": [{"id": "string", "description": "string", "components": []}],
    "goals": ["string"],
}

PROMPT_TEMPLATE = """You are inferring project intent and architecture from the actual codebase (bottom-up).

Given the following code structure (blueprint extracted from code), produce two JSON objects in the same format as the project's top-down docs.

## Code structure (blueprint_code)
{blueprint_summary}

## Optional code context (key files)
{code_context}

## Output format
Respond with exactly two JSON objects, one after the other, no other text:

1. **intent** (same schema as intent.json): version, sprint, features (array with id, name, description, components).
2. **architecture** (same schema as architecture.json): version, features, requirements, goals.

Example structure for intent:
{{"version": "1.0", "sprint": "", "features": [{{"id": "f1", "name": "...", "description": "...", "components": []}}]}}

Example structure for architecture:
{{"version": "1.0", "features": [{{"id": "f1", "name": "...", "components": [], "requirements": []}}], "requirements": [], "goals": []}}

Output ONLY valid JSON for intent first, then a line "---", then valid JSON for architecture.
"""


def _truncate_blueprint(blueprint: Dict[str, Any], max_components: int = 80) -> str:
    """Summarize blueprint for prompt (avoid token overflow)."""
    components = blueprint.get("components", [])[:max_components]
    lines = [f"- {c.get('name', c.get('id', '?'))} ({c.get('type', '?')}) @ {c.get('file', '')}" for c in components]
    return "\n".join(lines) if lines else "(no components)"


def _read_file_sample(path: Path, max_chars: int = 4000) -> str:
    """Read a file with a size limit."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read(max_chars)
    except Exception:
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
