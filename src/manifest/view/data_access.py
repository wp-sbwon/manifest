"""
View data access: timeline events.
"""
from pathlib import Path
from typing import List, Tuple

from manifest.audit.blueprint.manifest_filenames import BLUEPRINT_DESIGN_FILE, PRD_FILE
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

    design_doc_names = [BLUEPRINT_DESIGN_FILE, PRD_FILE]
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
