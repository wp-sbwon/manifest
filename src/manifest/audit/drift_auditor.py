"""
Drift Auditor - Detects architecture drift by comparing code against blueprint.
Uses AST parsing to detect structural mismatches.
"""
import json
import ast
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

from manifest.audit.code_extractor import CodeExtractor


class Severity(Enum):
    """Severity levels for drift conflicts."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class DriftConflict:
    """Represents a single drift conflict."""
    
    def __init__(self, severity: Severity, message: str, node_id: Optional[str] = None, file_path: Optional[str] = None):
        self.severity = severity
        self.message = message
        self.node_id = node_id
        self.file_path = file_path
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "severity": self.severity.value,
            "message": self.message,
            "node_id": self.node_id,
            "file_path": self.file_path
        }


class DriftAuditor:
    """Audits code structure against blueprint.json."""
    
    def __init__(self, manifest_dir: Path = None):
        self.manifest_dir = manifest_dir or Path(".manifest")
        self.blueprint_file = self.manifest_dir / "blueprint.json"
        self.blueprint: Dict[str, Any] = {}
        self._load_blueprint()
    
    def _load_blueprint(self):
        """Load blueprint.json with metadata."""
        from manifest.audit.blueprint_metadata import load_blueprint_with_metadata
        self.blueprint = load_blueprint_with_metadata(
            self.blueprint_file, "llm_design", False
        )
    
    def reload_blueprint(self):
        """Reload blueprint from file."""
        self._load_blueprint()
    
    def parse_python_file(self, file_path: Path) -> Dict[str, Any]:
        """Parse a Python file and extract structure."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            classes = []
            functions = []
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    classes.append({
                        "name": node.name,
                        "methods": methods,
                        "line": node.lineno
                    })
                elif isinstance(node, ast.FunctionDef) and not any(
                    isinstance(parent, ast.ClassDef) for parent in ast.walk(tree) if hasattr(parent, 'body') and node in getattr(parent, 'body', [])
                ):
                    functions.append({
                        "name": node.name,
                        "line": node.lineno
                    })
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        imports.extend([alias.name for alias in node.names])
                    else:
                        imports.append(node.module or "")
            
            return {
                "classes": classes,
                "functions": functions,
                "imports": imports,
                "file_path": str(file_path)
            }
        except Exception as e:
            return {
                "error": str(e),
                "file_path": str(file_path)
            }
    
    def find_python_files(self, root: Path = Path(".")) -> List[Path]:
        """Find all Python files in the project."""
        python_files = []
        for path in root.rglob("*.py"):
            # Skip virtual environments and hidden directories
            if any(part.startswith(".") and part != "." for part in path.parts):
                continue
            if "venv" in path.parts or "__pycache__" in path.parts:
                continue
            python_files.append(path)
        return python_files
    
    def compare_with_blueprint(self, code_structure: Dict[str, Any]) -> List[DriftConflict]:
        """Compare code structure against blueprint and return conflicts."""
        conflicts = []
        components = self.blueprint.get("components", [])
        
        # Check for missing classes
        blueprint_classes = {comp.get("name"): comp for comp in components if comp.get("type") == "class"}
        code_classes = {cls["name"]: cls for cls in code_structure.get("classes", [])}
        
        for class_name, blueprint_comp in blueprint_classes.items():
            if class_name not in code_classes:
                conflicts.append(DriftConflict(
                    Severity.ERROR,
                    f"Missing class '{class_name}' as specified in blueprint",
                    node_id=blueprint_comp.get("id"),
                    file_path=code_structure.get("file_path")
                ))
            else:
                # Check methods
                blueprint_methods = set(blueprint_comp.get("methods", []))
                code_methods = set(code_classes[class_name].get("methods", []))
                missing_methods = blueprint_methods - code_methods
                extra_methods = code_methods - blueprint_methods
                
                for method in missing_methods:
                    conflicts.append(DriftConflict(
                        Severity.WARNING,
                        f"Missing method '{method}' in class '{class_name}'",
                        node_id=blueprint_comp.get("id"),
                        file_path=code_structure.get("file_path")
                    ))
                
                for method in extra_methods:
                    conflicts.append(DriftConflict(
                        Severity.INFO,
                        f"Extra method '{method}' in class '{class_name}' (not in blueprint)",
                        node_id=blueprint_comp.get("id"),
                        file_path=code_structure.get("file_path")
                    ))
        
        # Check for extra classes (not in blueprint)
        for class_name in code_classes:
            if class_name not in blueprint_classes:
                conflicts.append(DriftConflict(
                    Severity.WARNING,
                    f"Class '{class_name}' exists in code but not in blueprint",
                    file_path=code_structure.get("file_path")
                ))
        
        return conflicts
    
    def audit_project(self, root: Path = Path(".")) -> List[DriftConflict]:
        """Audit entire project for drift."""
        all_conflicts = []
        python_files = self.find_python_files(root)
        
        for file_path in python_files:
            structure = self.parse_python_file(file_path)
            if "error" not in structure:
                conflicts = self.compare_with_blueprint(structure)
                all_conflicts.extend(conflicts)
        
        return all_conflicts
    
    def get_conflicts_by_severity(self, conflicts: List[DriftConflict]) -> Dict[str, List[DriftConflict]]:
        """Group conflicts by severity."""
        grouped = {
            "error": [],
            "warning": [],
            "info": []
        }
        
        for conflict in conflicts:
            grouped[conflict.severity.value].append(conflict)
        
        return grouped
    
    def get_conflicts_for_node(self, conflicts: List[DriftConflict], node_id: str) -> List[DriftConflict]:
        """Get conflicts for a specific blueprint node."""
        return [c for c in conflicts if c.node_id == node_id]
    
    def generate_bottom_up_blueprint(self, root: Path = None) -> Dict[str, Any]:
        """Generate bottom-up blueprint from code structure."""
        if root is None:
            root = Path(".")
        
        extractor = CodeExtractor(root)
        blueprint = extractor.extract_project_structure(root)
        
        # Save to blueprint_code.json
        blueprint_file = self.manifest_dir / "blueprint_code.json"
        extractor.save_blueprint(blueprint, blueprint_file)
        
        return blueprint