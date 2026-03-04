"""Unit tests for build_view_schema with test_results parameter."""
import pytest

from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_entity
from manifest.audit.blueprint.view_schema import build_view_schema


def _bp(entities_dicts: list) -> dict:
    """Wrap entity dicts into a blueprint root."""
    return {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": entities_dicts}


def _make_aligned_pair(*child_ids: str):
    """Create design + code blueprints with root + children, no deviations."""
    root_d = dict(empty_entity(PROJECT_ROOT_ID))
    root_d["children"] = list(child_ids)
    root_c = dict(empty_entity(PROJECT_ROOT_ID))
    root_c["children"] = list(child_ids)
    d_ents = [root_d]
    c_ents = [root_c]
    for cid in child_ids:
        d_ents.append(dict(empty_entity(cid)))
        c_ents.append(dict(empty_entity(cid)))
    return _bp(d_ents), _bp(c_ents)


def _status_of(view: dict, eid: str) -> str:
    by_id = {e["id"]: e for e in view.get("entities") or []}
    return by_id[eid]["validation"]["status"]


# ---------------------------------------------------------------------------
# Status derivation with test_results
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_stub_tests_produce_partial_status() -> None:
    design, code = _make_aligned_pair("a")
    tr = {"a": [{"index": 0, "assertion": "", "status": "stub"}]}
    view = build_view_schema(design, code, test_results=tr)
    assert _status_of(view, "a") == "partial"


@pytest.mark.unit
def test_implemented_tests_keep_healthy() -> None:
    design, code = _make_aligned_pair("a")
    tr = {"a": [{"index": 0, "assertion": "", "status": "implemented"}]}
    view = build_view_schema(design, code, test_results=tr)
    assert _status_of(view, "a") == "healthy"


@pytest.mark.unit
def test_mixed_tests_one_stub_produces_partial() -> None:
    design, code = _make_aligned_pair("a")
    tr = {"a": [
        {"index": 0, "assertion": "", "status": "implemented"},
        {"index": 1, "assertion": "", "status": "implemented"},
        {"index": 2, "assertion": "", "status": "stub"},
    ]}
    view = build_view_schema(design, code, test_results=tr)
    assert _status_of(view, "a") == "partial"


@pytest.mark.unit
def test_no_test_results_keeps_healthy() -> None:
    design, code = _make_aligned_pair("a")
    view_none = build_view_schema(design, code, test_results=None)
    view_empty = build_view_schema(design, code, test_results={})
    assert _status_of(view_none, "a") == "healthy"
    assert _status_of(view_empty, "a") == "healthy"


@pytest.mark.unit
def test_deviation_overrides_stub_tests() -> None:
    """Deviation takes priority over stub test results."""
    design, code = _make_aligned_pair("a")
    # Introduce a deviation by changing symbol in code
    for e in code["entities"]:
        if e["id"] == "a":
            e["symbol"] = "changed.py"
    tr = {"a": [{"index": 0, "assertion": "", "status": "stub"}]}
    view = build_view_schema(design, code, test_results=tr)
    assert _status_of(view, "a") == "deviation"


@pytest.mark.unit
def test_planned_ignores_test_results() -> None:
    """Design-only entity stays 'planned' regardless of test_results."""
    root_d = dict(empty_entity(PROJECT_ROOT_ID))
    root_d["children"] = ["p"]
    p_d = dict(empty_entity("p"))
    design = _bp([root_d, p_d])
    # code has root only — no "p"
    root_c = dict(empty_entity(PROJECT_ROOT_ID))
    root_c["children"] = ["p"]
    code = _bp([root_c])
    tr = {"p": [{"index": 0, "assertion": "", "status": "stub"}]}
    view = build_view_schema(design, code, test_results=tr)
    assert _status_of(view, "p") == "planned"


@pytest.mark.unit
def test_extra_ignores_test_results() -> None:
    """Code-only entity stays 'extra' regardless of test_results."""
    root_d = dict(empty_entity(PROJECT_ROOT_ID))
    design = _bp([root_d])
    root_c = dict(empty_entity(PROJECT_ROOT_ID))
    root_c["children"] = ["x"]
    x_c = dict(empty_entity("x"))
    code = _bp([root_c, x_c])
    tr = {"x": [{"index": 0, "assertion": "", "status": "stub"}]}
    view = build_view_schema(design, code, test_results=tr)
    assert _status_of(view, "x") == "extra"


# ---------------------------------------------------------------------------
# test_results attached to view entities
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_test_results_attached_to_view_entity() -> None:
    design, code = _make_aligned_pair("a")
    tr = {"a": [
        {"index": 0, "assertion": "checks X", "status": "implemented"},
        {"index": 1, "assertion": "checks Y", "status": "stub"},
    ]}
    view = build_view_schema(design, code, test_results=tr)
    by_id = {e["id"]: e for e in view["entities"]}
    assert by_id["a"]["test_results"] == tr["a"]


@pytest.mark.unit
def test_entity_without_tests_has_empty_list() -> None:
    design, code = _make_aligned_pair("a", "b")
    tr = {"a": [{"index": 0, "assertion": "", "status": "implemented"}]}
    view = build_view_schema(design, code, test_results=tr)
    by_id = {e["id"]: e for e in view["entities"]}
    assert by_id["b"]["test_results"] == []
