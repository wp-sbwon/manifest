"""Main view content: Files (source tree) and Timeline (git events) body text."""
from pathlib import Path
from typing import Dict, Any, List, Tuple

from manifest.view.views_content import (
    ACCENT_BLUE,
    entities_for_display,
    status_color_tag,
)


def build_files_view_content(
    comp_status: Dict[str, str],
    code_blueprint: Dict[str, Any],
    project_root: Path,
) -> str:
    """Source tree: dirs and files with status dots."""
    root_label = project_root.name or "root"
    components = entities_for_display(code_blueprint.get("entities", []))
    dirs: Dict[str, List[Tuple[str, Dict[str, Any], str]]] = {}
    for c in components:
        if not isinstance(c, dict):
            continue
        fp = (c.get("file") or "?").replace("\\", "/")
        parts = fp.split("/")
        dir_name = parts[0] if len(parts) > 1 else "."
        if dir_name not in dirs:
            dirs[dir_name] = []
        dirs[dir_name].append((parts[-1] if parts else "?", c, comp_status.get(c.get("id") or "", "planned")))
    S = "■"
    lines = [
        "[dim]Source Tree[/]",
        f"[dim]Project root: {project_root}[/]",
        "",
        f"[white]{root_label}/[/]",
    ]
    dir_list = sorted(dirs.items())
    for i, (d, items) in enumerate(dir_list):
        prefix = "└── " if i == len(dir_list) - 1 else "├── "
        lines.append(f"[{ACCENT_BLUE}]{prefix}{S}[/] {d}/")
        for j, (fname, comp, st) in enumerate(items[:12]):
            st_tag = status_color_tag(st)
            sub_prefix = "    " if i == len(dir_list) - 1 else "│   "
            lines.append(f"[dim]{sub_prefix}└── {fname}[/] ..... [{st_tag}]{S}[/]")
            for meth in (comp.get("methods") or [])[:4]:
                m_tag = status_color_tag(st)
                lines.append(f"[dim]{sub_prefix}    ├── [/][cyan]{meth}()[/] [{m_tag}]{S}[/]")
    if not dirs:
        for c in components[:20]:
            if not isinstance(c, dict):
                continue
            cid = c.get("id")
            name = (c.get("name") or cid or "?")[:28]
            st = comp_status.get(cid or "", "planned")
            tag = status_color_tag(st)
            lines.append(f"  [{tag}]{S}[/] {name}")
    return "\n".join(lines)


def build_timeline_view_content(
    events: List[Tuple[str, str, str, str]],
) -> str:
    """Timeline body from sorted (timestamp, side, message, color) events."""
    lines = ["[dim]Project Changes Timeline[/]", ""]
    lines.append("[dim]DESIGN = commits touching .manifest design docs  CODE = repo commits[/]")
    lines.append("")
    for ts, side, msg, color in events[:25]:
        lines.append(f"[dim]{ts}[/]  [{color}]{side}[/]  {msg}")
    if not events:
        lines.append("No design or code events (need git repo).")
    return "\n".join(lines)
