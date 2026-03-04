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


def _test_badge(entity_id: str, index: int, test_results: Optional[Dict[str, list]]) -> str:
    """Badge for a single assertion test: PASS/FAIL/STUB/—."""
    if not test_results:
        return "[dim]—[/]"
    tests = test_results.get(entity_id, [])
    for t in tests:
        if t.get("index") == index:
            status = t.get("status", "")
            if status == "implemented":
                return "[green] PASS [/]"
            if status == "stub":
                return "[yellow] STUB [/]"
            return "[red] FAIL [/]"
    return "[dim]—[/]"


def build_info_hub_node_content(
    header: str,
    nid: str,
    data: Dict[str, Any],
    deviating: bool,
    view_entity: Optional[Dict[str, Any]],
    id_to_display_name: Dict[str, str],
    test_results: Optional[Dict[str, list]] = None,
) -> str:
    """Inspector: Identity, Contract (mechanical fields), Intent (assertions + badges), Outgoing contracts."""
    def _box(path: Tuple[str, ...]) -> str:
        return deviation_box(deviates_at(view_entity, path))

    def _plan_actual_at(path: Tuple[str, ...]) -> Tuple[Any, Any]:
        cur: Any = view_entity
        for key in path:
            cur = (cur or {}).get(key) if isinstance(cur, dict) else None
            if cur is None:
                break
        if isinstance(cur, dict) and "plan" in cur and "actual" in cur:
            return cur.get("plan"), cur.get("actual")
        cur = data
        for key in path:
            cur = (cur or {}).get(key) if isinstance(cur, dict) else None
        return cur, cur

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

    narrative = data.get("narrative") or {}
    blueprint = data.get("blueprint") or {}
    bp_topology = blueprint.get("topology") or {}
    protocol = data.get("protocol") or {}
    profile = data.get("profile") or {}
    gov = data.get("governance") or {}
    deps = data.get("dependencies") or []
    traits = data.get("traits") or []
    topology_actual = data.get("topology_actual") or {}
    children_ids = data.get("children") or []
    children_display = [id_to_display_name.get(cid, cid) for cid in children_ids]
    contracts = data.get("outgoing_contracts") or []

    # --- Identity section ---
    role_text = format_for_display(narrative.get("role"), 80)
    mission_text = format_for_display(narrative.get("mission"), 240)
    identity_lines = [
        f"[white]{_cap('id')}[/]: {nid}",
        f"[white]{_cap('children')}[/]: {', '.join(children_display) or '—'}{_box(('children',))}",
        f"[white]{_cap('dependencies')}[/]: {', '.join(deps[:12]) or '—'}{_box(('dependencies',))}",
        f"[white]{_cap('role')}[/]: {role_text}",
        f"[white]{_cap('mission')}[/]: {mission_text}",
    ]
    identity_body = "\n".join(identity_lines)

    # --- Contract section (mechanical fields with deviation boxes) ---
    topology_summary = "—"
    if isinstance(bp_topology, dict) and bp_topology:
        dims = bp_topology.get("dimensions") or {}
        topology_summary = "dimensions " + format_for_display(dims, 80) if dims else "present"
    topology_actual_summary = "—"
    if isinstance(topology_actual, dict) and topology_actual:
        topology_actual_summary = format_for_display(topology_actual.get("type")) or "present"

    contract_lines: List[str] = []
    contract_lines.append(f"{_cap('blueprint')}")
    contract_lines.append(f"  — {_cap('type')}: {format_for_display(blueprint.get('type'), 20)}{_box(('blueprint', 'type'))}")
    contract_lines.append(f"  — {_cap('topology')}: {topology_summary}{_box(('blueprint', 'topology'))}")
    contract_lines.append(f"{_cap('protocol')}")
    plan_in, actual_in = _plan_actual_at(("protocol", "input"))
    ln, dev = _spec_line("input", plan_in, actual_in, ("protocol", "input"))
    contract_lines.append(f"  — {ln}{_box(('protocol', 'input'))}")
    plan_out, actual_out = _plan_actual_at(("protocol", "output"))
    ln, dev = _spec_line("output", plan_out, actual_out, ("protocol", "output"))
    contract_lines.append(f"  — {ln}{_box(('protocol', 'output'))}")
    contract_lines.append(f"{_cap('profile')}")
    for key in ("language", "platform", "io_model", "state_model"):
        plan_v, actual_v = _plan_actual_at(("profile", key))
        ln, dev = _spec_line(key, plan_v, actual_v, ("profile", key))
        contract_lines.append(f"  — {ln}{_box(('profile', key))}")
    contract_lines.append(f"{_cap('symbol')}: {format_for_display(data.get('symbol'), 120)}{_box(('symbol',))}")
    contract_lines.append(f"{_cap('traits')}: {', '.join(traits[:10]) or '—'}{_box(('traits',))}")
    contract_lines.append(f"{_cap('topology_actual')}: {topology_actual_summary}{_box(('topology_actual',))}")
    contract_lines.append(f"{_cap('preview')}: {format_for_display(data.get('preview'), 160)}{_box(('preview',))}")
    contract_body = "\n".join(contract_lines)

    # --- Intent section (governance assertions with test badges) ---
    assertions = gov.get("assertions") or []
    if assertions and isinstance(assertions, list):
        intent_lines: List[str] = []
        for i, assertion in enumerate(assertions):
            text = assertion if isinstance(assertion, str) else format_for_display(assertion, 120)
            badge = _test_badge(nid, i, test_results)
            intent_lines.append(f"  {i}: \"{text}\"  {badge}")
        intent_body = "\n".join(intent_lines)
    else:
        intent_body = "No assertions defined."

    # --- Outgoing contracts section ---
    outgoing_lines = [f"→ {c.get('to') or '—'} [{c.get('type') or 'dependency'}] {c.get('file') or ''} {', '.join((c.get('symbols') or [])[:4])}" for c in (contracts or [])[:10]]
    outgoing_body = "\n".join(outgoing_lines) if outgoing_lines else "—"
    outgoing_body += "  " + _box(("outgoing_contracts",))

    parts = [
        header.strip(),
        inspection_section("Identity", identity_body),
        inspection_section("Contract", contract_body),
        inspection_section("Intent", intent_body),
        inspection_section("Outgoing contracts", outgoing_body),
    ]
    return "\n".join(parts)


def build_info_hub_diff_view(
    header: str,
    nid: str,
    data: Dict[str, Any],
    deviating: bool,
    design_ent: Optional[Dict[str, Any]],
    code_ent: Optional[Dict[str, Any]],
) -> Union[str, Group]:
    """Diff view: Plan vs Code as a Rich table; only contractual fields, differing values in red."""
    plan = design_ent or data
    actual = code_ent or data
    plan_blueprint = plan.get("blueprint") or {}
    actual_blueprint = actual.get("blueprint") or {}
    plan_protocol = plan.get("protocol") or {}
    actual_protocol = actual.get("protocol") or {}
    plan_profile = plan.get("profile") or {}
    actual_profile = actual.get("profile") or {}
    max_cell = 28

    def _s(v: Any, w: int = 28) -> str:
        return format_for_display(v, max_len=w, max_items=5)[:w].replace("\n", " ")

    rows = [
        ("Type", _s(plan_blueprint.get("type")), _s(actual_blueprint.get("type"))),
        ("Protocol input", _s(plan_protocol.get("input")), _s(actual_protocol.get("input"))),
        ("Protocol output", _s(plan_protocol.get("output")), _s(actual_protocol.get("output"))),
        ("Language", _s(plan_profile.get("language")), _s(actual_profile.get("language"))),
        ("Platform", _s(plan_profile.get("platform")), _s(actual_profile.get("platform"))),
        ("Symbol", _s(plan.get("symbol")), _s(actual.get("symbol"))),
        ("Dependencies", _s(plan.get("dependencies")), _s(actual.get("dependencies"))),
        ("Traits", _s(plan.get("traits")), _s(actual.get("traits"))),
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
