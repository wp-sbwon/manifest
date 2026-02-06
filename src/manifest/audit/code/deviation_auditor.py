"""
Design Plan vs Actual Code deviation detection and auditing.

This module provides the DeviationAuditor class which compares the actual code
structure against the design plan to detect inconsistencies. It uses AST
(Abstract Syntax Tree) parsing to extract structural information from Python
files and compares it with design plan components.

Deviation detection helps maintain architectural integrity by identifying when
code diverges from the intended design.
"""
import json
import ast
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

from manifest.audit.code.code_extractor import CodeExtractor


class Severity(Enum):
    """Severity levels for deviation conflicts."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    IN_PROGRESS = "in_progress"  # In design plan, not yet in actual code (not a conflict)


class DeviationConflict:
    """Represents a single deviation (design plan vs actual code) conflict."""

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


class DeviationAuditor:
    """Audits code structure against design plan to detect deviation.

    Compares actual code structure (classes, functions, imports) extracted
    via AST parsing against the design plan. Identifies missing
    components, extra components, and structural mismatches.

    Attributes:
        manifest_dir: Path to .manifest directory.
        blueprint_file: Path to blueprint_design.json (design plan).
        blueprint: Loaded design plan data dictionary.
    """

    def __init__(self, manifest_dir: Path = None):
        """Initialize the deviation auditor.

        Args:
            manifest_dir: Path to .manifest directory. Defaults to .manifest.
        """
        self.manifest_dir = manifest_dir or Path(".manifest")
        from manifest.audit.blueprint.manifest_filenames import BLUEPRINT_DESIGN_FILE
        self.blueprint_file = self.manifest_dir / BLUEPRINT_DESIGN_FILE
        self.blueprint: Dict[str, Any] = {}
        self._load_blueprint()

    def _load_blueprint(self) -> None:
        """Load blueprint_design (design plan) with metadata."""
        from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
        self.blueprint = BlueprintLoader.load_blueprint(
            self.manifest_dir, with_metadata=True
        )

    def reload_blueprint(self) -> None:
        """Reload design plan from disk."""
        self._load_blueprint()

    def parse_python_file(self, file_path: Path) -> Dict[str, Any]:
        """Parse a Python file and extract its structure using AST."""
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
            if any(part.startswith(".") and part != "." for part in path.parts):
                continue
            if "venv" in path.parts or "__pycache__" in path.parts:
                continue
            python_files.append(path)
        return python_files

    def compare_with_blueprint(self, code_structure: Dict[str, Any]) -> List[DeviationConflict]:
        """Compare code structure against design plan and return conflicts."""
        from manifest.audit.entity_schema import non_root_entities, entity_display_name

        conflicts = []
        entities = non_root_entities(self.blueprint)
        reality_type = lambda e: (e.get("reality") or {}).get("type", e.get("type", ""))
        reality_methods = lambda e: (e.get("reality") or {}).get("methods", e.get("methods", []))
        blueprint_classes = {
            entity_display_name(e): e for e in entities if reality_type(e) == "class"
        }
        code_classes = {cls["name"]: cls for cls in code_structure.get("classes", [])}

        for class_name, blueprint_comp in blueprint_classes.items():
            if class_name not in code_classes:
                conflicts.append(DeviationConflict(
                    Severity.ERROR,
                    f"Missing class '{class_name}' as specified in design plan",
                    node_id=blueprint_comp.get("id"),
                    file_path=code_structure.get("file_path")
                ))
            else:
                blueprint_methods = set(reality_methods(blueprint_comp))
                code_methods = set(code_classes[class_name].get("methods", []))
                missing_methods = blueprint_methods - code_methods
                extra_methods = code_methods - blueprint_methods

                for method in missing_methods:
                    conflicts.append(DeviationConflict(
                        Severity.WARNING,
                        f"Missing method '{method}' in class '{class_name}'",
                        node_id=blueprint_comp.get("id"),
                        file_path=code_structure.get("file_path")
                    ))

                for method in extra_methods:
                    conflicts.append(DeviationConflict(
                        Severity.INFO,
                        f"Extra method '{method}' in class '{class_name}' (not in design plan)",
                        node_id=blueprint_comp.get("id"),
                        file_path=code_structure.get("file_path")
                    ))

        for class_name in code_classes:
            if class_name not in blueprint_classes:
                conflicts.append(DeviationConflict(
                    Severity.WARNING,
                    f"Class '{class_name}' exists in code but not in design plan",
                    file_path=code_structure.get("file_path")
                ))

        return conflicts

    def audit_project(self, root: Path = Path(".")) -> List[DeviationConflict]:
        """Audit entire project for deviation."""
        all_conflicts = []
        python_files = self.find_python_files(root)

        for file_path in python_files:
            structure = self.parse_python_file(file_path)
            if "error" not in structure:
                conflicts = self.compare_with_blueprint(structure)
                all_conflicts.extend(conflicts)

        return all_conflicts

    def get_conflicts_by_severity(self, conflicts: List[DeviationConflict]) -> Dict[str, List[DeviationConflict]]:
        """Group conflicts by severity."""
        grouped = {
            "error": [],
            "warning": [],
            "info": []
        }
        for conflict in conflicts:
            grouped[conflict.severity.value].append(conflict)
        return grouped

    def get_conflicts_for_node(self, conflicts: List[DeviationConflict], node_id: str) -> List[DeviationConflict]:
        """Get conflicts for a specific design plan node."""
        return [c for c in conflicts if c.node_id == node_id]

    def generate_bottom_up_blueprint(self, root: Path = None) -> Dict[str, Any]:
        """Generate bottom-up (actual code) blueprint from code structure."""
        if root is None:
            root = Path(".")

        extractor = CodeExtractor(root)
        blueprint = extractor.extract_project_structure(root)

        from manifest.audit.blueprint.manifest_filenames import BLUEPRINT_CODE_FILE
        blueprint_file = self.manifest_dir / BLUEPRINT_CODE_FILE
        extractor.save_blueprint(blueprint, blueprint_file)

        return blueprint
