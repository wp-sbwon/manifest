"""Unit tests for inspector_content and sidebar_content view helpers."""
import pytest

from manifest.audit.entity_schema import empty_entity
from manifest.view.content.inspector_content import (
    _test_badge,
    build_info_hub_node_content,
    build_info_hub_diff_view,
)
from manifest.view.content.sidebar_content import get_sidebar_health_text


# ===========================================================================
# _test_badge
# ===========================================================================

@pytest.mark.unit
def test_badge_no_results_returns_dash() -> None:
    assert "—" in _test_badge("x", 0, None)


@pytest.mark.unit
def test_badge_implemented_returns_pass() -> None:
    tr = {"x": [{"index": 0, "status": "implemented"}]}
    badge = _test_badge("x", 0, tr)
    assert "PASS" in badge
    assert "green" in badge


@pytest.mark.unit
def test_badge_stub_returns_stub() -> None:
    tr = {"x": [{"index": 0, "status": "stub"}]}
    badge = _test_badge("x", 0, tr)
    assert "STUB" in badge
    assert "yellow" in badge


@pytest.mark.unit
def test_badge_no_matching_index_returns_dash() -> None:
    tr = {"x": [{"index": 5, "status": "implemented"}]}
    assert "—" in _test_badge("x", 0, tr)


# ===========================================================================
# get_sidebar_health_text
# ===========================================================================

@pytest.mark.unit
def test_sidebar_status_counts() -> None:
    comp = {"a": "healthy", "b": "planned", "c": "deviation"}
    text = get_sidebar_health_text(comp, {})
    assert "Healthy: 1" in text
    assert "Planned: 1" in text
    assert "Deviation: 1" in text


@pytest.mark.unit
def test_sidebar_zero_counts_omitted() -> None:
    comp = {"a": "healthy", "b": "healthy"}
    text = get_sidebar_health_text(comp, {})
    assert "Healthy: 2" in text
    assert "Planned" not in text
    assert "Deviation" not in text


@pytest.mark.unit
def test_sidebar_proof_rate_all_implemented() -> None:
    tr = {"e": [{"index": 0, "status": "implemented"}, {"index": 1, "status": "implemented"}]}
    text = get_sidebar_health_text({}, tr)
    assert "2/2" in text
    assert "100%" in text
    assert "green" in text


@pytest.mark.unit
def test_sidebar_proof_rate_partial() -> None:
    tr = {"e": [{"index": 0, "status": "implemented"}, {"index": 1, "status": "stub"}]}
    text = get_sidebar_health_text({}, tr)
    assert "1/2" in text
    assert "50%" in text
    assert "yellow" in text


@pytest.mark.unit
def test_sidebar_no_assertions() -> None:
    text = get_sidebar_health_text({}, {})
    assert "No assertions" in text


# ===========================================================================
# build_info_hub_node_content
# ===========================================================================

def _sample_data() -> dict:
    ent = empty_entity("n1")
    ent["narrative"] = {"role": "Worker", "mission": "Do work."}
    ent["governance"] = {"rules": [], "assertions": ["Must be fast", "Must be safe"]}
    ent["protocol"] = {"input": [{"name": "x", "type": "int"}], "output": [{"name": "y", "type": "str"}]}
    ent["profile"] = {"language": ["Python"], "platform": "linux", "io_model": "sync", "state_model": "stateless"}
    ent["blueprint"] = {"type": "FLOW", "topology": {}}
    ent["outgoing_contracts"] = [{"to": "n2", "type": "dependency", "file": "a.py", "symbols": ["fn"]}]
    return ent


@pytest.mark.unit
def test_node_content_has_four_sections() -> None:
    data = _sample_data()
    content = build_info_hub_node_content("Header", "n1", data, False, None, {})
    assert "Identity" in content
    assert "Contract" in content
    assert "Intent" in content
    assert "Outgoing contracts" in content


@pytest.mark.unit
def test_node_content_identity_has_role_mission() -> None:
    data = _sample_data()
    content = build_info_hub_node_content("Header", "n1", data, False, None, {})
    assert "Worker" in content
    assert "Do work." in content


@pytest.mark.unit
def test_node_content_intent_shows_badges() -> None:
    data = _sample_data()
    tr = {"n1": [
        {"index": 0, "status": "implemented"},
        {"index": 1, "status": "stub"},
    ]}
    content = build_info_hub_node_content("Header", "n1", data, False, None, {}, test_results=tr)
    assert "PASS" in content
    assert "STUB" in content
    assert "Must be fast" in content
    assert "Must be safe" in content


@pytest.mark.unit
def test_node_content_intent_no_assertions() -> None:
    data = _sample_data()
    data["governance"] = {"rules": [], "assertions": []}
    content = build_info_hub_node_content("Header", "n1", data, False, None, {})
    assert "No assertions defined." in content


@pytest.mark.unit
def test_node_content_contract_has_protocol() -> None:
    data = _sample_data()
    content = build_info_hub_node_content("Header", "n1", data, False, None, {})
    assert "Protocol" in content
    assert "Profile" in content
    assert "Blueprint" in content


# ===========================================================================
# build_info_hub_diff_view
# ===========================================================================

@pytest.mark.unit
def test_diff_view_contractual_rows_only() -> None:
    data = _sample_data()
    result = build_info_hub_diff_view("Header", "n1", data, False, data, data)
    # Result is a Rich Group — render to string to check content
    from rich.console import Console
    from io import StringIO
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=120)
    console.print(result)
    rendered = buf.getvalue()
    # Contractual fields present
    assert "Type" in rendered
    assert "Protocol" in rendered
    assert "Language" in rendered
    assert "Symbol" in rendered
    # Narrative/governance fields absent from diff table
    assert "Role" not in rendered
    assert "Mission" not in rendered
    assert "Governance" not in rendered


@pytest.mark.unit
def test_diff_view_returns_group() -> None:
    from rich.console import Group
    data = _sample_data()
    result = build_info_hub_diff_view("Header", "n1", data, False, data, data)
    assert isinstance(result, Group)
