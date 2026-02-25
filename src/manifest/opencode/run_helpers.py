"""Helpers for parsing opencode JSON-line stdout."""
import json
import re
import uuid
from typing import Any, Dict


def opencode_run_session_id() -> str:
    """Unique session ID for a single scripted opencode run. Subprocesses do not share sessions."""
    return f"_manifest_run_{uuid.uuid4().hex[:12]}"


def parse_opencode_stdout(stdout: str) -> str:
    """
    Collect text from opencode JSON-line stdout (type=text part.text).
    Returns merged text or empty string.
    """
    texts = []
    for line in (stdout or "").strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
            if ev.get("type") == "text" and "part" in ev:
                txt = ev["part"].get("text")
                if txt:
                    texts.append(txt)
        except json.JSONDecodeError:
            continue
    return "\n".join(texts)


def extract_json_from_text(text: str) -> Dict[str, Any]:
    """
    Extract JSON object from text (handles ```json ... ``` wrapping).
    Raises on parse failure.
    """
    text = (text or "").strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()
    return json.loads(text)
