"""
Code Quality Manager - Handles linting, formatting, and security checks.
"""
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class CodeQualityManager:
    """Manages code quality tools like ruff, bandit, etc."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()

    def run_lint(self, file_path: str) -> Dict[str, Any]:
        """Run linter (ruff) on a file."""
        try:
            # Check if ruff is installed
            subprocess.run(["ruff", "--version"], capture_output=True, check=True)

            result = subprocess.run(
                ["ruff", "check", "--format", "json", file_path],
                capture_output=True,
                text=True,
                cwd=str(self.project_root)
            )

            if result.stdout:
                issues = json.loads(result.stdout)
                return {
                    "success": len(issues) == 0,
                    "issues": issues,
                    "count": len(issues)
                }
            return {"success": True, "issues": [], "count": 0}
        except Exception as e:
            logger.debug(f"Linting failed or ruff not available: {e}")
            return {"success": False, "error": str(e)}

    def run_security_check(self, file_path: str) -> Dict[str, Any]:
        """Run security check (bandit) on a file."""
        try:
            # Check if bandit is installed
            subprocess.run(["bandit", "--version"], capture_output=True, check=True)

            result = subprocess.run(
                ["bandit", "-f", "json", file_path],
                capture_output=True,
                text=True,
                cwd=str(self.project_root)
            )

            if result.stdout:
                data = json.loads(result.stdout)
                issues = data.get("results", [])
                return {
                    "success": len(issues) == 0,
                    "issues": issues,
                    "count": len(issues)
                }
            return {"success": True, "issues": [], "count": 0}
        except Exception as e:
            logger.debug(f"Security check failed or bandit not available: {e}")
            return {"success": False, "error": str(e)}

    def check_architecture_compliance(self, file_path: str, component_id: str) -> Dict[str, Any]:
        """Check if code matches blueprint specification."""
        from manifest.audit.code.code_extractor import CodeExtractor
        from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
        from manifest.audit.blueprint.blueprint_comparator import BlueprintComparator

        try:
            extractor = CodeExtractor()
            loader = BlueprintLoader()
            comparator = BlueprintComparator()

            # Extract from code
            code_components = extractor.extract_file_structure(Path(file_path))
            code_comp = next((c for c in code_components if c.id == component_id), None)

            if not code_comp:
                return {"success": False, "error": f"Component {component_id} not found in {file_path}"}

            # Load from blueprint
            manifest_dir = self.project_root / ".manifest"
            blueprint = loader.load_blueprint(manifest_dir)
            blueprint_comp = next((c for c in blueprint.get("components", []) if c.get("id") == component_id), None)

            if not blueprint_comp:
                return {"success": False, "error": f"Component {component_id} not found in blueprint"}

            # Compare
            # Convert Component object to dict for comparison
            code_comp_dict = {
                "id": code_comp.id,
                "name": code_comp.name,
                "methods": code_comp.methods,
                "attributes": code_comp.attributes
            }

            conflicts = comparator.compare_components([blueprint_comp], [code_comp_dict])

            return {
                "success": len(conflicts) == 0,
                "conflicts": [c.to_dict() for c in conflicts],
                "count": len(conflicts)
            }
        except Exception as e:
            logger.error(f"Architecture compliance check failed: {e}")
            return {"success": False, "error": str(e)}
