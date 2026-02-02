"""
Unit tests for blueprint_comparator.py
"""
import pytest
from manifest.audit.blueprint.blueprint_comparator import BlueprintComparator, BlueprintConflict, ConflictType
from manifest.audit.code.drift_auditor import Severity


@pytest.fixture
def comparator():
    """Create a BlueprintComparator instance."""
    return BlueprintComparator()


@pytest.fixture
def sample_top_down():
    """Sample top-down blueprint."""
    return {
        "version": "1.0",
        "components": [
            {
                "id": "comp-1",
                "name": "TestClass",
                "type": "class",
                "methods": ["method1", "method2"]
            },
            {
                "id": "comp-2",
                "name": "AnotherClass",
                "type": "class",
                "methods": ["method3"]
            }
        ],
        "contracts": [
            {
                "from": "comp-1",
                "to": "comp-2",
                "type": "dependency"
            }
        ],
        "zones": {
            "client": ["comp-1"],
            "server": ["comp-2"],
            "data": []
        }
    }


@pytest.fixture
def sample_bottom_up():
    """Sample bottom-up blueprint."""
    return {
        "version": "1.0",
        "source": "code_extraction",
        "components": [
            {
                "id": "comp-1",
                "name": "TestClass",
                "type": "class",
                "methods": ["method1"]  # Missing method2
            },
            {
                "id": "comp-3",
                "name": "NewClass",
                "type": "class",
                "methods": ["method4"]  # Extra class not in design
            }
        ],
        "contracts": [],
        "zones": {
            "client": ["comp-1"],
            "server": [],
            "data": []
        }
    }


def test_compare_components_missing(comparator, sample_top_down, sample_bottom_up):
    """Test detecting missing components."""
    conflicts = comparator.compare_components(
        sample_top_down["components"],
        sample_bottom_up["components"]
    )

    # Should detect missing AnotherClass
    missing_conflicts = [
        c for c in conflicts
        if c.type == ConflictType.MISSING_COMPONENT
    ]
    assert len(missing_conflicts) > 0
    assert any("AnotherClass" in c.message for c in missing_conflicts)


def test_compare_components_extra(comparator, sample_top_down, sample_bottom_up):
    """Test detecting extra components."""
    conflicts = comparator.compare_components(
        sample_top_down["components"],
        sample_bottom_up["components"]
    )

    # Should detect extra NewClass
    extra_conflicts = [
        c for c in conflicts
        if c.type == ConflictType.EXTRA_COMPONENT
    ]
    assert len(extra_conflicts) > 0
    assert any("NewClass" in c.message for c in extra_conflicts)


def test_compare_methods_missing(comparator, sample_top_down, sample_bottom_up):
    """Test detecting missing methods."""
    conflicts = comparator.compare_components(
        sample_top_down["components"],
        sample_bottom_up["components"]
    )

    # Should detect missing method2
    method_conflicts = [
        c for c in conflicts
        if c.type == ConflictType.METHOD_MISMATCH and "method2" in c.message
    ]
    assert len(method_conflicts) > 0


def test_compare_contracts(comparator, sample_top_down, sample_bottom_up):
    """Test comparing contracts."""
    conflicts = comparator.compare_contracts(
        sample_top_down["contracts"],
        sample_bottom_up["contracts"]
    )

    # Should detect missing contract
    contract_conflicts = [
        c for c in conflicts
        if c.type == ConflictType.CONTRACT_MISMATCH
    ]
    assert len(contract_conflicts) > 0


def test_compare_zones(comparator, sample_top_down, sample_bottom_up):
    """Test comparing zones."""
    conflicts = comparator.compare_zones(
        sample_top_down["zones"],
        sample_bottom_up["zones"]
    )

    # Should detect zone mismatches
    zone_conflicts = [
        c for c in conflicts
        if c.type == ConflictType.ZONE_MISMATCH
    ]
    assert len(zone_conflicts) > 0


def test_compare_blueprints_full(comparator, sample_top_down, sample_bottom_up):
    """Test full blueprint comparison."""
    conflicts = comparator.compare_blueprints(sample_top_down, sample_bottom_up)

    assert len(conflicts) > 0

    # Should have various conflict types
    conflict_types = {c.type for c in conflicts}
    assert ConflictType.MISSING_COMPONENT in conflict_types
    assert ConflictType.EXTRA_COMPONENT in conflict_types
    assert ConflictType.METHOD_MISMATCH in conflict_types


def test_get_conflicts_by_severity(comparator, sample_top_down, sample_bottom_up):
    """Test grouping conflicts by severity."""
    conflicts = comparator.compare_blueprints(sample_top_down, sample_bottom_up)
    grouped = comparator.get_conflicts_by_severity(conflicts)

    assert "error" in grouped
    assert "warning" in grouped
    assert "info" in grouped


def test_get_conflicts_by_type(comparator, sample_top_down, sample_bottom_up):
    """Test grouping conflicts by type."""
    conflicts = comparator.compare_blueprints(sample_top_down, sample_bottom_up)
    grouped = comparator.get_conflicts_by_type(conflicts)

    assert ConflictType.MISSING_COMPONENT.value in grouped
    assert ConflictType.EXTRA_COMPONENT.value in grouped
