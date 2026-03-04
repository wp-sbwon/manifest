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
    """Source tree: one row per file path; components that share a file listed under it."""
    root_label = project_root.name or "root"
    components = entities_for_display(code_blueprint.get("entities", []))
    # Group by (dir_name, file_path) so each file appears once; value = list of (comp_id, comp_name, status)
    by_file: Dict[Tuple[str, str], List[Tuple[str, str, str]]] = {}
    for c in components:
        if not isinstance(c, dict):
            continue
        fp = (c.get("file") or "?").replace("\\", "/")
        parts = fp.split("/")
        dir_name = parts[0] if len(parts) > 1 else "."
        fname = parts[-1] if parts else "?"
        cid = c.get("id") or "?"
        cname = (c.get("name") or cid or "?")[:24]
        st = comp_status.get(cid, "planned")
        key = (dir_name, fp)
        if key not in by_file:
            by_file[key] = []
        by_file[key].append((cid, cname, st))
    S = "■"
    lines = [
        "[dim]Source Tree[/]",
        f"[dim]Project root: {project_root}[/]",
        "",
        f"[white]{root_label}/[/]",
    ]
    items_sorted = sorted(by_file.items(), key=lambda x: (x[0][0], x[0][1]))
    for i, ((d, _fp), comps) in enumerate(items_sorted):
        prefix = "└── " if i == len(items_sorted) - 1 else "├── "
        lines.append(f"[{ACCENT_BLUE}]{prefix}{S}[/] {d}/")
        fname = _fp.split("/")[-1] if "/" in _fp else _fp
        # One line per file; show component(s) under it
        st_tag = status_color_tag(comps[0][2]) if comps else status_color_tag("planned")
        sub_prefix = "    " if i == len(items_sorted) - 1 else "│   "
        lines.append(f"[dim]{sub_prefix}└── {fname}[/] ..... [{st_tag}]{S}[/]")
        for _cid, cname, cst in comps[:10]:
            m_tag = status_color_tag(cst)
            lines.append(f"[dim]{sub_prefix}    ├── [/]{cname}[/] [{m_tag}]{S}[/]")
    if not by_file:
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
