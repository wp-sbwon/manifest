"""
Unit tests for drift_auditor.py
"""
import pytest
import json
import tempfile
import shutil
from pathlib import Path
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
