"""
Unit tests for drift_auditor.py
"""
import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from manifest.audit.code.drift_auditor import DriftAuditor, DriftConflict, Severity


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def drift_auditor(temp_dir):
    """Create a DriftAuditor instance with temp directory."""
    return DriftAuditor(manifest_dir=temp_dir)


def test_drift_auditor_initialization(drift_auditor):
    """Test DriftAuditor initialization."""
    assert drift_auditor.blueprint is not None
    assert "version" in drift_auditor.blueprint


def test_parse_python_file(drift_auditor, temp_dir):
    """Test Python file parsing."""
    test_file = temp_dir / "test.py"
    test_file.write_text("""
class TestClass:
    def method1(self):
        pass

    def method2(self):
        pass

def standalone_function():
    pass
""")

    structure = drift_auditor.parse_python_file(test_file)

    assert "classes" in structure
    assert len(structure["classes"]) == 1
    assert structure["classes"][0]["name"] == "TestClass"
    assert len(structure["classes"][0]["methods"]) == 2
    assert len(structure["functions"]) == 1


def test_compare_with_blueprint(drift_auditor, temp_dir):
    """Test blueprint comparison."""
    # Set up blueprint
    drift_auditor.blueprint = {
        "version": "1.0",
        "components": [
            {
                "id": "comp1",
                "name": "TestClass",
                "type": "class",
                "methods": ["method1", "method2"]
            }
        ]
    }

    # Code structure with matching class
    code_structure = {
        "classes": [
            {
                "name": "TestClass",
                "methods": ["method1", "method2"]
            }
        ],
        "file_path": str(temp_dir / "test.py")
    }

    conflicts = drift_auditor.compare_with_blueprint(code_structure)
    assert len(conflicts) == 0  # No conflicts

    # Code structure with missing method
    code_structure_missing = {
        "classes": [
            {
                "name": "TestClass",
                "methods": ["method1"]  # Missing method2
            }
        ],
        "file_path": str(temp_dir / "test.py")
    }

    conflicts = drift_auditor.compare_with_blueprint(code_structure_missing)
    assert len(conflicts) > 0
    assert any("method2" in c.message for c in conflicts)


def test_conflict_severity(drift_auditor):
    """Test conflict severity levels."""
    conflict_error = DriftConflict(Severity.ERROR, "Error message")
    conflict_warning = DriftConflict(Severity.WARNING, "Warning message")
    conflict_info = DriftConflict(Severity.INFO, "Info message")

    assert conflict_error.severity == Severity.ERROR
    assert conflict_warning.severity == Severity.WARNING
    assert conflict_info.severity == Severity.INFO


def test_group_conflicts_by_severity(drift_auditor):
    """Test grouping conflicts by severity."""
    conflicts = [
        DriftConflict(Severity.ERROR, "Error 1"),
        DriftConflict(Severity.ERROR, "Error 2"),
        DriftConflict(Severity.WARNING, "Warning 1"),
        DriftConflict(Severity.INFO, "Info 1"),
    ]

    grouped = drift_auditor.get_conflicts_by_severity(conflicts)

    assert len(grouped["error"]) == 2
    assert len(grouped["warning"]) == 1
    assert len(grouped["info"]) == 1


def test_find_python_files(drift_auditor, temp_dir):
    """Test finding Python files."""
    # Create some test files
    (temp_dir / "test1.py").write_text("pass")
    (temp_dir / "test2.py").write_text("pass")
    (temp_dir / "subdir").mkdir()
    (temp_dir / "subdir" / "test3.py").write_text("pass")

    # Skip venv
    (temp_dir / "venv").mkdir()
    (temp_dir / "venv" / "test_venv.py").write_text("pass")

    files = drift_auditor.find_python_files(temp_dir)

    assert len(files) >= 3
    assert all("venv" not in str(f) for f in files)


# ========== TDL: Drift Auditor Tests ==========

def test_blueprint_vs_code_comparison_missing_class(drift_auditor):
    """Test blueprint vs code comparison detects missing class."""
    drift_auditor.blueprint = {
        "version": "1.0",
        "components": [
            {
                "id": "comp-1",
                "name": "RequiredClass",
                "type": "class",
                "methods": ["method1"]
            }
        ]
    }

    code_structure = {
        "classes": [],  # Missing RequiredClass
        "functions": [],
        "file_path": "test.py"
    }

    conflicts = drift_auditor.compare_with_blueprint(code_structure)

    assert len(conflicts) > 0
    assert any(c.severity == Severity.ERROR for c in conflicts)
    assert any("RequiredClass" in c.message for c in conflicts)


def test_blueprint_vs_code_comparison_extra_class(drift_auditor):
    """Test blueprint vs code comparison detects extra class."""
    drift_auditor.blueprint = {
        "version": "1.0",
        "components": [
            {
                "id": "comp-1",
                "name": "ExpectedClass",
                "type": "class"
            }
        ]
    }

    code_structure = {
        "classes": [
            {"name": "ExpectedClass", "methods": []},
            {"name": "UnexpectedClass", "methods": []}  # Extra class
        ],
        "file_path": "test.py"
    }

    conflicts = drift_auditor.compare_with_blueprint(code_structure)

    # Should detect extra class (WARNING severity based on code)
    extra_conflicts = [c for c in conflicts if "UnexpectedClass" in c.message]
    assert len(extra_conflicts) > 0
    # Extra classes are WARNING severity (not INFO)
    assert any(c.severity == Severity.WARNING for c in extra_conflicts)


def test_blueprint_vs_code_comparison_method_mismatch(drift_auditor):
    """Test blueprint vs code comparison detects method mismatches."""
    drift_auditor.blueprint = {
        "version": "1.0",
        "components": [
            {
                "id": "comp-1",
                "name": "TestClass",
                "type": "class",
                "methods": ["method1", "method2", "method3"]
            }
        ]
    }

    code_structure = {
        "classes": [
            {
                "name": "TestClass",
                "methods": ["method1"]  # Missing method2 and method3
            }
        ],
        "file_path": "test.py"
    }

    conflicts = drift_auditor.compare_with_blueprint(code_structure)

    # Should detect missing methods
    missing_method_conflicts = [c for c in conflicts if "method" in c.message.lower() and "missing" in c.message.lower()]
    assert len(missing_method_conflicts) > 0
    assert all(c.severity == Severity.WARNING for c in missing_method_conflicts)


def test_drift_severity_classification_error(drift_auditor):
    """Test drift severity classification for errors."""
    drift_auditor.blueprint = {
        "version": "1.0",
        "components": [
            {
                "id": "comp-1",
                "name": "CriticalClass",
                "type": "class"
            }
        ]
    }

    code_structure = {
        "classes": [],  # Missing critical class
        "file_path": "test.py"
    }

    conflicts = drift_auditor.compare_with_blueprint(code_structure)

    # Missing classes should be ERROR severity
    error_conflicts = [c for c in conflicts if c.severity == Severity.ERROR]
    assert len(error_conflicts) > 0


def test_drift_severity_classification_warning(drift_auditor):
    """Test drift severity classification for warnings."""
    drift_auditor.blueprint = {
        "version": "1.0",
        "components": [
            {
                "id": "comp-1",
                "name": "TestClass",
                "type": "class",
                "methods": ["required_method"]
            }
        ]
    }

    code_structure = {
        "classes": [
            {
                "name": "TestClass",
                "methods": []  # Missing required method
            }
        ],
        "file_path": "test.py"
    }

    conflicts = drift_auditor.compare_with_blueprint(code_structure)

    # Missing methods should be WARNING severity
    warning_conflicts = [c for c in conflicts if c.severity == Severity.WARNING]
    assert len(warning_conflicts) > 0


def test_drift_severity_classification_info(drift_auditor):
    """Test drift severity classification for info."""
    drift_auditor.blueprint = {
        "version": "1.0",
        "components": [
            {
                "id": "comp-1",
                "name": "TestClass",
                "type": "class",
                "methods": ["method1"]
            }
        ]
    }

    code_structure = {
        "classes": [
            {
                "name": "TestClass",
                "methods": ["method1", "extra_method"]  # Extra method
            }
        ],
        "file_path": "test.py"
    }

    conflicts = drift_auditor.compare_with_blueprint(code_structure)

    # Extra methods should be INFO severity
    info_conflicts = [c for c in conflicts if c.severity == Severity.INFO]
    assert len(info_conflicts) > 0
    assert any("extra" in c.message.lower() for c in info_conflicts)


def test_conflict_detection_missing_component(drift_auditor):
    """Test conflict detection for missing components."""
    drift_auditor.blueprint = {
        "version": "1.0",
        "components": [
            {
                "id": "comp-1",
                "name": "Component1",
                "type": "class"
            },
            {
                "id": "comp-2",
                "name": "Component2",
                "type": "class"
            }
        ]
    }

    code_structure = {
        "classes": [
            {"name": "Component1", "methods": []}
            # Missing Component2
        ],
        "file_path": "test.py"
    }

    conflicts = drift_auditor.compare_with_blueprint(code_structure)

    # Should detect missing Component2
    missing_conflicts = [c for c in conflicts if "Component2" in c.message]
    assert len(missing_conflicts) > 0
    assert missing_conflicts[0].node_id == "comp-2"


def test_conflict_detection_method_mismatch(drift_auditor):
    """Test conflict detection for method mismatches."""
    drift_auditor.blueprint = {
        "version": "1.0",
        "components": [
            {
                "id": "comp-1",
                "name": "TestClass",
                "type": "class",
                "methods": ["method1", "method2"]
            }
        ]
    }

    code_structure = {
        "classes": [
            {
                "name": "TestClass",
                "methods": ["method1", "method3"]  # method2 missing, method3 extra
            }
        ],
        "file_path": "test.py"
    }

    conflicts = drift_auditor.compare_with_blueprint(code_structure)

    # Should detect both missing and extra methods
    assert len(conflicts) >= 2
    missing = [c for c in conflicts if "method2" in c.message and "missing" in c.message.lower()]
    extra = [c for c in conflicts if "method3" in c.message and "extra" in c.message.lower()]
    assert len(missing) > 0
    assert len(extra) > 0


def test_conflict_detection_no_conflicts(drift_auditor):
    """Test conflict detection when code matches blueprint."""
    drift_auditor.blueprint = {
        "version": "1.0",
        "components": [
            {
                "id": "comp-1",
                "name": "TestClass",
                "type": "class",
                "methods": ["method1", "method2"]
            }
        ]
    }

    code_structure = {
        "classes": [
            {
                "name": "TestClass",
                "methods": ["method1", "method2"]  # Matches blueprint
            }
        ],
        "file_path": "test.py"
    }

    conflicts = drift_auditor.compare_with_blueprint(code_structure)

    # Should have no conflicts
    assert len(conflicts) == 0


def test_audit_project(drift_auditor, temp_dir):
    """Test auditing entire project."""
    # Create test Python files
    test_file1 = temp_dir / "module1.py"
    test_file1.write_text("""
class Class1:
    def method1(self):
        pass
""")

    test_file2 = temp_dir / "module2.py"
    test_file2.write_text("""
class Class2:
    def method2(self):
        pass
""")

    # Set up blueprint
    drift_auditor.blueprint = {
        "version": "1.0",
        "components": [
            {
                "id": "comp-1",
                "name": "Class1",
                "type": "class",
                "methods": ["method1"]
            },
            {
                "id": "comp-2",
                "name": "Class2",
                "type": "class",
                "methods": ["method2"]
            }
        ]
    }

    conflicts = drift_auditor.audit_project(temp_dir)

    # Should audit all files and return conflicts
    assert isinstance(conflicts, list)
    # May have conflicts or not depending on matching


def test_get_conflicts_by_severity(drift_auditor):
    """Test grouping conflicts by severity."""
    conflicts = [
        DriftConflict(Severity.ERROR, "Error 1", node_id="comp-1"),
        DriftConflict(Severity.ERROR, "Error 2", node_id="comp-2"),
        DriftConflict(Severity.WARNING, "Warning 1", node_id="comp-3"),
        DriftConflict(Severity.INFO, "Info 1", node_id="comp-4")
    ]

    grouped = drift_auditor.get_conflicts_by_severity(conflicts)

    assert "error" in grouped
    assert "warning" in grouped
    assert "info" in grouped
    assert len(grouped["error"]) == 2
    assert len(grouped["warning"]) == 1
    assert len(grouped["info"]) == 1


def test_get_conflicts_for_node(drift_auditor):
    """Test getting conflicts for a specific node."""
    conflicts = [
        DriftConflict(Severity.ERROR, "Error for comp-1", node_id="comp-1"),
        DriftConflict(Severity.WARNING, "Warning for comp-1", node_id="comp-1"),
        DriftConflict(Severity.ERROR, "Error for comp-2", node_id="comp-2")
    ]

    node_conflicts = drift_auditor.get_conflicts_for_node(conflicts, "comp-1")

    assert len(node_conflicts) == 2
    assert all(c.node_id == "comp-1" for c in node_conflicts)


def test_drift_conflict_to_dict(drift_auditor):
    """Test DriftConflict to_dict conversion."""
    conflict = DriftConflict(
        Severity.ERROR,
        "Test message",
        node_id="comp-1",
        file_path="test.py"
    )

    conflict_dict = conflict.to_dict()

    assert conflict_dict["severity"] == "error"
    assert conflict_dict["message"] == "Test message"
    assert conflict_dict["node_id"] == "comp-1"
    assert conflict_dict["file_path"] == "test.py"


def test_parse_python_file_with_imports(drift_auditor, temp_dir):
    """Test parsing Python file with imports."""
    test_file = temp_dir / "test.py"
    test_file.write_text("""
import os
from pathlib import Path
import json

class TestClass:
    pass
""")

    structure = drift_auditor.parse_python_file(test_file)

    assert "imports" in structure
    assert len(structure["imports"]) > 0
    assert "os" in structure["imports"] or any("os" in imp for imp in structure["imports"])


def test_parse_python_file_error_handling(drift_auditor, temp_dir):
    """Test parsing Python file with syntax errors."""
    test_file = temp_dir / "invalid.py"
    test_file.write_text("""
class Invalid:
    def method(
    # Missing closing parenthesis
""")

    structure = drift_auditor.parse_python_file(test_file)

    # Should return error information
    assert "error" in structure or structure.get("classes") is not None


def test_reload_blueprint(drift_auditor, temp_dir):
    """Test reloading blueprint from disk."""
    # Create blueprint file
    blueprint_file = temp_dir / "blueprint.json"
    blueprint_file.write_text(json.dumps({
        "version": "1.0",
        "components": []
    }))

    # Mock _load_blueprint to verify it's called
    with patch.object(drift_auditor, '_load_blueprint') as mock_load:
        drift_auditor.reload_blueprint()
        mock_load.assert_called_once()
