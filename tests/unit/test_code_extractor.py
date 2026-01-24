"""
Unit tests for code_extractor.py
"""
import pytest
import json
import tempfile
import shutil
from pathlib import Path

from manifest.audit.code.code_extractor import CodeExtractor, Component, Contract


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_code_file(temp_dir):
    """Create a sample Python file for testing."""
    code_file = temp_dir / "test_module.py"
    code_file.write_text("""
class TestClass:
    def method1(self):
        pass
    
    def method2(self):
        pass

def standalone_function():
    pass

class AnotherClass(TestClass):
    def method3(self):
        pass
""")
    return code_file


def test_extract_single_file(sample_code_file, temp_dir):
    """Test extracting structure from a single file."""
    extractor = CodeExtractor(temp_dir)
    blueprint = extractor.extract_project_structure(temp_dir)
    
    assert blueprint["version"] == "1.0"
    assert blueprint["source"] == "code_extraction"
    assert "components" in blueprint
    assert "contracts" in blueprint
    
    # Check that classes are extracted
    component_names = [c["name"] for c in blueprint["components"]]
    assert "TestClass" in component_names
    assert "AnotherClass" in component_names


def test_extract_methods(sample_code_file, temp_dir):
    """Test that methods are extracted from classes."""
    extractor = CodeExtractor(temp_dir)
    blueprint = extractor.extract_project_structure(temp_dir)
    
    test_class = next(
        (c for c in blueprint["components"] if c["name"] == "TestClass"),
        None
    )
    assert test_class is not None
    assert "method1" in test_class.get("methods", [])
    assert "method2" in test_class.get("methods", [])


def test_extract_inheritance(sample_code_file, temp_dir):
    """Test that inheritance relationships are extracted."""
    extractor = CodeExtractor(temp_dir)
    blueprint = extractor.extract_project_structure(temp_dir)
    
    # Check for inheritance contract
    inheritance_contracts = [
        c for c in blueprint["contracts"]
        if c.get("type") == "inheritance"
    ]
    assert len(inheritance_contracts) > 0


def test_extract_imports(temp_dir):
    """Test that imports create dependency contracts."""
    code_file = temp_dir / "test_imports.py"
    code_file.write_text("""
import os
from pathlib import Path

class TestClass:
    def method(self):
        os.path.join("a", "b")
        Path("test")
""")
    
    extractor = CodeExtractor(temp_dir)
    blueprint = extractor.extract_project_structure(temp_dir)
    
    # Check for dependency contracts
    dependency_contracts = [
        c for c in blueprint["contracts"]
        if c.get("type") == "dependency"
    ]
    assert len(dependency_contracts) > 0


def test_save_blueprint(temp_dir):
    """Test saving blueprint to file."""
    extractor = CodeExtractor(temp_dir)
    blueprint = extractor.extract_project_structure(temp_dir)
    
    output_file = temp_dir / "test_blueprint.json"
    result = extractor.save_blueprint(blueprint, output_file)
    
    assert result is True
    assert output_file.exists()
    
    # Verify content
    with open(output_file, "r") as f:
        loaded = json.load(f)
    assert loaded["version"] == "1.0"
    assert loaded["source"] == "code_extraction"


def test_skip_hidden_directories(temp_dir):
    """Test that hidden directories are skipped."""
    # Create hidden directory
    hidden_dir = temp_dir / ".hidden"
    hidden_dir.mkdir()
    (hidden_dir / "test.py").write_text("class Hidden: pass")
    
    extractor = CodeExtractor(temp_dir)
    blueprint = extractor.extract_project_structure(temp_dir)
    
    # Hidden class should not be extracted
    component_names = [c["name"] for c in blueprint["components"]]
    assert "Hidden" not in component_names
