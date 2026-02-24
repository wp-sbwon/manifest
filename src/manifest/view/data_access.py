"""
View data access: timeline events, chat/shadow state, health metrics.

Wraps GitManager and StateManager so app.py does not import core directly.
"""
from pathlib import Path
from typing import Any, Dict, List, Tuple

from manifest.view.views_content import ACCENT_BLUE


def get_timeline_events(manifest_dir: Path) -> List[Tuple[str, str, str, str]]:
    """
    Build timeline events: (timestamp, side, message, color).
    DESIGN = commits touching .manifest design docs; CODE = repo commits.
    """
    from manifest.core.git_manager import GitManager

    events: List[Tuple[str, str, str, str]] = []
    manifest_dir = Path(manifest_dir)
    project_root = manifest_dir.parent
    git_mgr = GitManager(project_root, search_parent_directories=False)

    design_doc_names = ["blueprint_design.json", "prd.json"]
    design_paths = [
        str(manifest_dir.relative_to(project_root) / name)
        for name in design_doc_names
        if (manifest_dir / name).exists()
    ]

    if git_mgr.is_available():
        try:
            for c in git_mgr.get_commits_for_paths(design_paths, limit=25):
                ts = (c.get("timestamp") or "?")[:16].replace("T", " ")
                msg = (c.get("message") or "?").replace("\n", " ")[:50]
                events.append((ts, "DESIGN", msg, ACCENT_BLUE))
        except Exception:
            pass
        try:
            for c in git_mgr.get_latest_commits(limit=25):
                ts = (c.get("timestamp") or "?")[:16].replace("T", " ")
                msg = (c.get("message") or "?").replace("\n", " ")[:50]
                events.append((ts, "CODE", msg, "green"))
        except Exception:
            pass
    events.sort(key=lambda x: x[0], reverse=True)
    return events


def get_inspector_shadow_channels(manifest_dir: Path) -> List[Tuple[str, List[Dict[str, Any]]]]:
    """
    Return [(channel_key, msgs), ...] for shadow-* channels from state.
    """
    from manifest.core.state_manager import StateManager

    state_mgr = StateManager(manifest_dir)
    chat_history = state_mgr.get_state().get("chat_history", {})
    if not isinstance(chat_history, dict):
        return []
    shadow_keys = [k for k in chat_history if isinstance(k, str) and k.startswith("shadow-")]
    out: List[Tuple[str, List[Dict[str, Any]]]] = []
    for key in shadow_keys:
        msgs = state_mgr.get_chat_history(key) or []
        out.append((key, msgs))
    return out


def get_shadow_results_for_node(manifest_dir: Path, nid: str) -> Tuple[str, str]:
    """
    Last output and trace for node from shadow-* channels. Returns (last_output, trace).
    """
    channels = get_inspector_shadow_channels(manifest_dir)
    for key, msgs in channels:
        if nid in key or key == f"shadow-{nid}":
            if not msgs:
                return "—", "—"
            last = msgs[-1]
            last_out = (last.get("content") or "")[:200].replace("\n", " ")
            trace = "\n".join((m.get("content") or "")[:120].replace("\n", " ") for m in msgs[-5:])
            return last_out or "—", trace or "—"
    if channels:
        _, msgs = channels[0]
        if msgs:
            last = msgs[-1]
            last_out = (last.get("content") or "")[:200].replace("\n", " ")
            trace = "\n".join((m.get("content") or "")[:120].replace("\n", " ") for m in msgs[-5:])
            return last_out or "—", trace or "—"
    return "—", "—"


def get_health_metrics(manifest_dir: Path, populate_if_blank: bool = False) -> Dict[str, Any]:
    """
    Load health_metrics from state.json. Optionally run write_health_to_state if blank.
    """
    import json

    from manifest.core.constants import STATE_FILE

    manifest_dir = Path(manifest_dir)
    state_file = manifest_dir / STATE_FILE
    metrics: Dict[str, Any] = {}
    if state_file.exists():
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            metrics = state.get("health_metrics") or {}
        except Exception:
            pass
    if populate_if_blank:
        blank = (metrics.get("code_quality") in (None, "—")) or (metrics.get("test_coverage") is None)
        if blank:
            try:
                from manifest.audit.code.health_from_code import write_health_to_state

                if write_health_to_state(manifest_dir):
                    with open(state_file, "r", encoding="utf-8") as f:
                        state = json.load(f)
                    metrics = state.get("health_metrics") or {}
            except Exception:
                pass
    return metrics
