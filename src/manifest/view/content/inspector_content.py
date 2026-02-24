"""Inspector (info hub) content: node view, diff view, sections, deviation formatting."""
from typing import Any, Dict, List, Optional, Tuple, Union

from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text

from manifest.view.constants import INSPECTOR_ACCENT, INSPECTOR_RULE_LENGTH

# Dotted horizontal lines between table rows (U+2504 = box drawings light triple dash)
from rich.box import Box
_DIFF_TABLE_BOX = Box(
    "    \n"
    "    \n"
    " \u2504\u2504 \n"
    "    \n"
    " \u2504\u2504 \n"
    "    \n"
    "    \n"
    "    \n"
)


def format_for_display(val: Any, max_len: int = 200, max_items: int = 12) -> str:
    """Format value for Inspector: no raw [] or {}; use — for empty, readable list/dict."""
    if val is None:
        return "—"
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return "—"
        return (s[:max_len] + "…") if len(s) > max_len else s
    if isinstance(val, (int, float, bool)):
        return str(val)
    if isinstance(val, list):
        if not val:
            return "—"
        parts = []
        for i, item in enumerate(val[:max_items]):
            if isinstance(item, dict):
                parts.append("{" + ", ".join(f"{k}: {format_for_display(v, 60, 3)}" for k, v in list(item.items())[:4]) + "}")
            else:
                parts.append(format_for_display(item, 80, 3))
        out = ", ".join(parts)
        if len(val) > max_items:
            out += f" … +{len(val) - max_items}"
        return (out[:max_len] + "…") if len(out) > max_len else out
    if isinstance(val, dict):
        if not val:
            return "—"
        parts = [f"{k}: {format_for_display(v, 60, 3)}" for k, v in list(val.items())[:max_items]]
        out = "; ".join(parts)
        if len(val) > max_items:
            out += " …"
        return (out[:max_len] + "…") if len(out) > max_len else out
    s = str(val).strip()
    return (s[:max_len] + "…") if len(s) > max_len else s


def inspection_section(title: str, body: str) -> str:
    """One inspection section: title, rule, then content. Blank line between each row."""
    rule = f"[{INSPECTOR_ACCENT}]" + "─" * INSPECTOR_RULE_LENGTH + "[/]"
    lines = [line.strip() for line in body.split("\n") if line.strip()]
    indented = "\n  \n  ".join(lines)
    return f"\n\n[bold {INSPECTOR_ACCENT}]{title}[/]\n{rule}\n  {indented}\n"


def deviation_box(deviates: bool) -> str:
    """Color-coded box for deviation status: red for deviates, green for aligned."""
    if deviates:
        return " [red reverse] ⚠ [/]"
    return " [green reverse] ✓ [/]"


def deviates_at(view_entity: Optional[Dict[str, Any]], path: Tuple[str, ...]) -> bool:
    """True if view_entity has a pair at path with deviates=True."""
    if not view_entity:
        return False
    cur: Any = view_entity
    for key in path:
        cur = cur.get(key) if isinstance(cur, dict) else None
        if cur is None:
            return False
    return bool(cur.get("deviates")) if isinstance(cur, dict) else False


def deviations_from_view_entity(view_entity: Dict[str, Any], prefix: str = "") -> List[str]:
    """List of field paths where plan ≠ actual (deviates=True)."""
    out: List[str] = []
    for key, val in (view_entity or {}).items():
        if key in ("plan", "actual", "deviates"):
            continue
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(val, dict):
            if val.get("deviates") is True:
                out.append(path)
            else:
                out.extend(deviations_from_view_entity(val, path))
    return out[:20]


def _cap(s: str) -> str:
    if not s:
        return s
    return " ".join(w.capitalize() for w in s.replace("_", " ").strip().split())


def build_info_hub_node_content(
    header: str,
    nid: str,
    data: Dict[str, Any],
    deviating: bool,
    view_entity: Optional[Dict[str, Any]],
    id_to_display_name: Dict[str, str],
) -> str:
    """Inspector: Identity, Spec (per-line deviation box), Outgoing contracts."""
    def _box(path: Tuple[str, ...]) -> str:
        return deviation_box(deviates_at(view_entity, path))

    def _spec_line(
        label: str,
        plan_val: Any,
        actual_val: Any,
        path: Tuple[str, ...],
        fmt_len: int = 200,
    ) -> Tuple[str, bool]:
        p = format_for_display(plan_val, fmt_len)
        a = format_for_display(actual_val, fmt_len)
        has_alert = deviates_at(view_entity, path)
        if p == "—" and a == "—":
            return f"{_cap(label)}: —", False
        if p == "—":
            return f"{_cap(label)}: {a}", False
        if a == "—":
            return f"{_cap(label)}: {p}", False
        if p == a:
            return f"{_cap(label)}: {p}", has_alert
        if has_alert:
            return f"{_cap(label)}: {p}  ⚠ actual: [red]{a}[/]", True
        return f"{_cap(label)}: {p}  (actual: {a})", False

    intent = data.get("intent") or {}
    reality = data.get("reality") or {}
    narrative = intent.get("narrative") or {}
    blueprint = intent.get("blueprint") or {}
    bp_topology = blueprint.get("topology") or {}
    protocol_i = intent.get("protocol") or {}
    protocol_r = reality.get("protocol") or {}
    profile_i = intent.get("profile") or {}
    profile_r = reality.get("profile") or {}
    gov = intent.get("governance") or {}
    reality_deps = reality.get("dependencies") or []
    traits = reality.get("traits") or []
    topology_actual = reality.get("topology_actual") or {}
    children_ids = data.get("children") or []
    children_display = [id_to_display_name.get(cid, cid) for cid in children_ids]
    contracts = data.get("outgoing_contracts") or []

    identity_lines = [
        f"[white]{_cap('id')}[/]: {nid}",
        f"[white]{_cap('children')}[/]: {', '.join(children_display) or '—'}{_box(('children',))}",
        f"[white]{_cap('dependencies')}[/]: {', '.join((data.get('dependencies') or [])[:12]) or '—'}{_box(('dependencies',))}",
    ]
    identity_body = "\n".join(identity_lines)
    topology_summary = "—"
    if isinstance(bp_topology, dict) and bp_topology:
        dims = bp_topology.get("dimensions") or {}
        topology_summary = "dimensions " + format_for_display(dims, 80) if dims else "present"
    topology_actual_summary = "—"
    if isinstance(topology_actual, dict) and topology_actual:
        topology_actual_summary = format_for_display(topology_actual.get("type")) or "present"

    spec_lines: List[str] = []
    any_spec_deviation = False

    def _role_mission_line(label: str, val: Any, path: Tuple[str, ...], fmt_len: int = 200) -> str:
        raw = format_for_display(val, fmt_len)
        return f"{_cap(label)}: {raw}{_box(path)}"

    spec_lines.append(_role_mission_line("role", narrative.get("role"), ("intent", "narrative", "role"), 80))
    spec_lines.append(_role_mission_line("mission", narrative.get("mission"), ("intent", "narrative", "mission"), 240))
    spec_lines.append(f"{_cap('blueprint')}")
    spec_lines.append(f"  — {_cap('type')}: {format_for_display(blueprint.get('type'), 20)}{_box(('intent', 'blueprint', 'type'))}")
    spec_lines.append(f"  — {_cap('topology')}: {topology_summary}{_box(('intent', 'blueprint', 'topology'))}")
    spec_lines.append(f"{_cap('protocol')}")
    ln, dev = _spec_line("input", protocol_i.get("input"), protocol_r.get("input"), ("intent", "protocol", "input"))
    spec_lines.append(f"  — {ln}{_box(('intent', 'protocol', 'input'))}")
    any_spec_deviation = any_spec_deviation or dev
    ln, dev = _spec_line("output", protocol_i.get("output"), protocol_r.get("output"), ("intent", "protocol", "output"))
    spec_lines.append(f"  — {ln}{_box(('intent', 'protocol', 'output'))}")
    any_spec_deviation = any_spec_deviation or dev
    spec_lines.append(f"{_cap('profile')}")
    for key in ("language", "platform", "io_model", "state_model"):
        pi = profile_i.get(key)
        pr = profile_r.get(key)
        ln, dev = _spec_line(key, pi, pr, ("intent", "profile", key))
        spec_lines.append(f"  — {ln}{_box(('intent', 'profile', key))}")
        any_spec_deviation = any_spec_deviation or dev
    spec_lines.append(f"{_cap('governance')}")
    spec_lines.append(f"  — {_cap('rules')}: {format_for_display(gov.get('rules'))}{_box(('intent', 'governance', 'rules'))}")
    spec_lines.append(f"  — {_cap('assertions')}: {format_for_display(gov.get('assertions'))}{_box(('intent', 'governance', 'assertions'))}")
    spec_lines.append(f"{_cap('symbol')}: {format_for_display(reality.get('symbol'), 120)}{_box(('reality', 'symbol'))}")
    spec_lines.append(f"{_cap('dependencies')} (code): {', '.join(reality_deps[:12]) or '—'}{_box(('reality', 'dependencies'))}")
    spec_lines.append(f"{_cap('traits')}: {', '.join(traits[:10]) or '—'}{_box(('reality', 'traits'))}")
    spec_lines.append(f"{_cap('topology_actual')}: {topology_actual_summary}{_box(('reality', 'topology_actual'))}")
    spec_lines.append(f"{_cap('preview')}: {format_for_display(reality.get('preview'), 160)}{_box(('reality', 'preview'))}")

    spec_body = "\n".join(spec_lines)
    contract_lines = [f"→ {c.get('to') or '—'} [{c.get('type') or 'dependency'}] {c.get('file') or ''} {', '.join((c.get('symbols') or [])[:4])}" for c in (contracts or [])[:10]]
    contracts_body = "\n".join(contract_lines) if contract_lines else "—"
    contracts_body += "  " + _box(("outgoing_contracts",))

    parts = [
        header.strip(),
        inspection_section("Identity", identity_body),
        inspection_section("Spec", spec_body),
        inspection_section("Outgoing contracts", contracts_body),
    ]
    if deviating or any_spec_deviation:
        parts.append(inspection_section("Deviation", "Plan and code differ. [bold][D] DIFF[/] to compare."))
    return "\n".join(parts)


def build_info_hub_diff_view(
    header: str,
    nid: str,
    data: Dict[str, Any],
    deviating: bool,
    design_ent: Optional[Dict[str, Any]],
    code_ent: Optional[Dict[str, Any]],
) -> Union[str, Group]:
    """Diff view: Plan vs Code as a Rich table; only differing values in red."""
    plan = design_ent or data
    actual = code_ent or data
    plan_intent = plan.get("intent") or {}
    plan_narr = plan_intent.get("narrative") or {}
    plan_reality = plan.get("reality") or {}
    actual_intent = actual.get("intent") or {}
    actual_narr = actual_intent.get("narrative") or {}
    actual_reality = actual.get("reality") or {}
    max_cell = 28

    def _s(v: Any, w: int = 28) -> str:
        return format_for_display(v, max_len=w, max_items=5)[:w].replace("\n", " ")

    plan_protocol = plan_intent.get("protocol") or {}
    actual_protocol = actual_intent.get("protocol") or {}
    plan_profile = plan_intent.get("profile") or {}
    actual_profile = actual_intent.get("profile") or {}
    plan_gov = plan_intent.get("governance") or {}
    actual_gov = actual_intent.get("governance") or {}
    rows = [
        ("Role", _s(plan_narr.get("role")), _s(actual_narr.get("role"))),
        ("Mission", _s(plan_narr.get("mission")), _s(actual_narr.get("mission"))),
        ("Type", _s(plan_intent.get("blueprint", {}).get("type")), _s(actual_intent.get("blueprint", {}).get("type"))),
        ("Protocol input", _s(plan_protocol.get("input")), _s(actual_protocol.get("input"))),
        ("Protocol output", _s(plan_protocol.get("output")), _s(actual_protocol.get("output"))),
        ("Language", _s(plan_profile.get("language")), _s(actual_profile.get("language"))),
        ("Platform", _s(plan_profile.get("platform")), _s(actual_profile.get("platform"))),
        ("Governance rules", _s(plan_gov.get("rules")), _s(actual_gov.get("rules"))),
        ("Symbol", _s(plan_reality.get("symbol")), _s(actual_reality.get("symbol"))),
        ("Dependencies", _s(plan_reality.get("dependencies")), _s(actual_reality.get("dependencies"))),
        ("Traits", _s(plan_reality.get("traits")), _s(actual_reality.get("traits"))),
    ]
    table = Table(
        show_header=True,
        show_lines=True,
        header_style="bold cyan",
        box=_DIFF_TABLE_BOX,
        padding=(0, 1),
    )
    table.add_column("Field", style="dim", width=18)
    table.add_column("Plan", style="dim", max_width=max_cell, overflow="ellipsis")
    table.add_column("Code", style="dim", max_width=max_cell, overflow="ellipsis")
    for label, d_val, a_val in rows:
        d_str = (d_val or "—")[:max_cell].replace("\n", " ")
        a_str = (a_val or "—")[:max_cell].replace("\n", " ")
        match = (d_val or "—") == (a_val or "—")
        plan_cell = Text(d_str) if match else Text(d_str)
        code_cell = Text(a_str) if match else Text(a_str, style="red")
        table.add_row(label, plan_cell, code_cell)
    parts: List[RenderableType] = [Text.from_markup(header.strip()), table]
    if deviating:
        parts.append(Text("⚠ Plan and code differ.", style="dim"))
    return Group(*parts)
