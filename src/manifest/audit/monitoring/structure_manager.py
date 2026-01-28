"""
Structure Manager - Manages structural changes based on Blueprint specifications.
Implements Spec-First Management: Blueprint changes drive code changes, and vice versa.
"""
import json
import ast
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field

from manifest.audit.code.code_extractor import CodeExtractor, Component, Contract
from manifest.audit.blueprint.blueprint_metadata import load_blueprint_with_metadata, save_blueprint_with_metadata
from manifest.audit.blueprint.blueprint_comparator import BlueprintComparator
from manifest.audit.monitoring.file_watcher import FileWatcher
from manifest.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StructuralChange:
    """Represents a structural change detected in code."""
    change_type: str  # "added", "modified", "deleted"
    component_id: Optional[str] = None
    file_path: str = ""
    component_data: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class BlueprintUpdateSuggestion:
    """Suggestion to update Blueprint based on code changes."""
    suggestion_type: str  # "add_component", "update_component", "add_contract", "remove_component"
    component: Optional[Component] = None
    contract: Optional[Contract] = None
    reason: str = ""
    confidence: float = 0.0  # 0.0 to 1.0
    affected_files: List[str] = field(default_factory=list)


@dataclass
class CodeChangeSuggestion:
    """Suggestion to change code based on Blueprint changes."""
    suggestion_type: str  # "create_file", "modify_file", "add_import", "add_class", "add_method"
    file_path: str = ""
    action: str = ""  # Detailed action description
    blueprint_component_id: str = ""
    reason: str = ""
    affected_components: List[str] = field(default_factory=list)
    action_data: Optional[Dict[str, Any]] = None  # Additional structured data for parsing


class StructureManager:
    """
    Manages structural changes and enforces Spec-First Development.

    Responsibilities:
    1. Detect code changes and suggest Blueprint updates
    2. Detect Blueprint changes and suggest code changes
    3. Maintain consistency between Blueprint and code
    """

    def __init__(self, manifest_dir: Path = None, project_root: Path = None):
        """
        Initialize Structure Manager.

        Args:
            manifest_dir: Manifest directory (default: .manifest)
            project_root: Project root directory (default: current directory)
        """
        self.manifest_dir = manifest_dir or Path(".manifest")
        self.project_root = project_root or Path.cwd()
        self.code_extractor = CodeExtractor(manifest_dir)
        self.comparator = BlueprintComparator()
        self.file_watcher = FileWatcher(project_root)

        # File paths
        self.blueprint_file = self.manifest_dir / "blueprint.json"
        self.blueprint_code_file = self.manifest_dir / "blueprint_code.json"
        self.architecture_file = self.manifest_dir / "architecture.json"

        # Pending changes
        self._pending_changes: List[str] = []

        # Register file change callback
        self.file_watcher.register_change_callback(self._on_files_changed)

    def detect_code_changes(
        self,
        changed_files: List[str],
        previous_blueprint: Optional[Dict[str, Any]] = None
    ) -> List[StructuralChange]:
        """
        Detect structural changes in code files.

        Args:
            changed_files: List of file paths that changed
            previous_blueprint: Previous blueprint for comparison (optional)

        Returns:
            List of detected structural changes
        """
        changes = []

        # Extract current structure from changed files
        for file_path in changed_files:
            path = Path(file_path)
            if not path.exists():
                # File deleted
                changes.append(StructuralChange(
                    change_type="deleted",
                    file_path=str(path)
                ))
                continue

            # Extract structure from file
            try:
                file_components = self.code_extractor.extract_file_structure(path)

                for component in file_components:
                    # Check if component is new or modified
                    change_type = "added"  # Assume new for now

                    if previous_blueprint:
                        # Check if component exists in previous blueprint
                        existing = self._find_component_in_blueprint(
                            component.id,
                            previous_blueprint
                        )
                        if existing:
                            change_type = "modified"

                    changes.append(StructuralChange(
                        change_type=change_type,
                        component_id=component.id,
                        file_path=str(path),
                        component_data={
                            "name": component.name,
                            "type": component.type,
                            "methods": component.methods,
                            "attributes": component.attributes
                        }
                    ))
            except Exception as e:
                # Skip files that can't be parsed
                logger.debug(f"Error extracting structure from {file_path}: {e}")
                continue

        return changes

    def suggest_blueprint_updates(
        self,
        code_changes: List[StructuralChange],
        current_blueprint: Optional[Dict[str, Any]] = None
    ) -> List[BlueprintUpdateSuggestion]:
        """
        Generate suggestions to update Blueprint based on code changes.

        Args:
            code_changes: List of detected code changes
            current_blueprint: Current blueprint (optional, will load if not provided)

        Returns:
            List of Blueprint update suggestions
        """
        if current_blueprint is None:
            current_blueprint = self._load_blueprint()

        suggestions = []

        for change in code_changes:
            if change.change_type == "added" and change.component_data:
                # Suggest adding new component to Blueprint
                component = self._create_component_from_change(change)
                if component:
                    suggestions.append(BlueprintUpdateSuggestion(
                        suggestion_type="add_component",
                        component=component,
                        reason=f"New component detected in {change.file_path}",
                        confidence=0.8,
                        affected_files=[change.file_path]
                    ))

            elif change.change_type == "modified" and change.component_data:
                # Suggest updating existing component
                component = self._create_component_from_change(change)
                if component:
                    suggestions.append(BlueprintUpdateSuggestion(
                        suggestion_type="update_component",
                        component=component,
                        reason=f"Component modified in {change.file_path}",
                        confidence=0.9,
                        affected_files=[change.file_path]
                    ))

            elif change.change_type == "deleted":
                # Suggest removing component from Blueprint
                if change.component_id:
                    suggestions.append(BlueprintUpdateSuggestion(
                        suggestion_type="remove_component",
                        reason=f"Component deleted: {change.component_id}",
                        confidence=0.7,
                        affected_files=[change.file_path]
                    ))

        return suggestions

    def detect_blueprint_changes(
        self,
        previous_blueprint: Optional[Dict[str, Any]] = None,
        current_blueprint: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Detect changes between previous and current Blueprint.

        Args:
            previous_blueprint: Previous Blueprint (optional, will load if not provided)
            current_blueprint: Current Blueprint (optional, will load if not provided)

        Returns:
            Dict with detected changes:
            {
                "new_components": [...],
                "modified_components": [...],
                "deleted_components": [...],
                "new_contracts": [...],
                "modified_contracts": [...],
                "deleted_contracts": [...]
            }
        """
        if previous_blueprint is None:
            # Try to load from backup or use empty
            previous_blueprint = self._load_previous_blueprint() or {"components": [], "contracts": []}

        if current_blueprint is None:
            current_blueprint = self._load_blueprint()

        changes = {
            "new_components": [],
            "modified_components": [],
            "deleted_components": [],
            "new_contracts": [],
            "modified_contracts": [],
            "deleted_contracts": []
        }

        # Compare components
        prev_components = {c.get("id"): c for c in previous_blueprint.get("components", [])}
        curr_components = {c.get("id"): c for c in current_blueprint.get("components", [])}

        # Find new components
        for comp_id, comp in curr_components.items():
            if comp_id not in prev_components:
                changes["new_components"].append(comp)
            else:
                # Check if modified (simple comparison)
                prev_comp = prev_components[comp_id]
                if (comp.get("methods") != prev_comp.get("methods") or
                    comp.get("attributes") != prev_comp.get("attributes")):
                    changes["modified_components"].append(comp)

        # Find deleted components
        for comp_id in prev_components:
            if comp_id not in curr_components:
                changes["deleted_components"].append(prev_components[comp_id])

        # Compare contracts
        prev_contracts = {
            (c.get("from_id"), c.get("to_id"), c.get("type")): c
            for c in previous_blueprint.get("contracts", [])
        }
        curr_contracts = {
            (c.get("from_id"), c.get("to_id"), c.get("type")): c
            for c in current_blueprint.get("contracts", [])
        }

        # Find new contracts
        for contract_key, contract in curr_contracts.items():
            if contract_key not in prev_contracts:
                changes["new_contracts"].append(contract)
            else:
                # Check if modified
                prev_contract = prev_contracts[contract_key]
                if contract.get("symbols") != prev_contract.get("symbols"):
                    changes["modified_contracts"].append(contract)

        # Find deleted contracts
        for contract_key in prev_contracts:
            if contract_key not in curr_contracts:
                changes["deleted_contracts"].append(prev_contracts[contract_key])

        return changes

    def suggest_code_changes(
        self,
        blueprint_changes: Optional[Dict[str, Any]] = None,
        current_code_blueprint: Optional[Dict[str, Any]] = None
    ) -> List[CodeChangeSuggestion]:
        """
        Generate suggestions to change code based on Blueprint changes.

        Args:
            blueprint_changes: Dict with changed components/contracts (optional, will detect if not provided)
            current_code_blueprint: Current code-extracted blueprint (optional)

        Returns:
            List of code change suggestions
        """
        if blueprint_changes is None:
            blueprint_changes = self.detect_blueprint_changes()

        if current_code_blueprint is None:
            current_code_blueprint = self._load_code_blueprint()

        suggestions = []

        # Check for new components in Blueprint
        new_components = blueprint_changes.get("new_components", [])
        for component in new_components:
            file_path = component.get("file", "")
            if not file_path or not Path(file_path).exists():
                # Component doesn't exist in code - suggest creating it
                suggested_path = self._suggest_file_path(component)
                suggestions.append(CodeChangeSuggestion(
                    suggestion_type="create_file",
                    file_path=suggested_path,
                    action=f"Create {component.get('type', 'component')} {component.get('name', '')} with methods: {', '.join(component.get('methods', []))}",
                    blueprint_component_id=component.get("id", ""),
                    reason=f"Component '{component.get('name', '')}' defined in Blueprint but not found in code",
                    affected_components=[component.get("id", "")]
                ))
            else:
                # Component exists but might need updates
                existing = self._find_component_in_blueprint(
                    component.get("id", ""),
                    current_code_blueprint
                )
                if not existing:
                    suggestions.append(CodeChangeSuggestion(
                        suggestion_type="add_class",
                        file_path=file_path,
                        action=f"Add class {component.get('name', '')} with methods: {', '.join(component.get('methods', []))}",
                        blueprint_component_id=component.get("id", ""),
                        reason=f"Component '{component.get('name', '')}' defined in Blueprint but missing in code file",
                        affected_components=[component.get("id", "")]
                    ))
                else:
                    # Component exists but might need method/attribute updates
                    existing_methods = set(existing.get("methods", []))
                    blueprint_methods = set(component.get("methods", []))
                    missing_methods = blueprint_methods - existing_methods

                    if missing_methods:
                        suggestions.append(CodeChangeSuggestion(
                            suggestion_type="add_method",
                            file_path=file_path,
                            action=f"Add methods to {component.get('name', '')}: {', '.join(missing_methods)}",
                            blueprint_component_id=component.get("id", ""),
                            reason=f"Component '{component.get('name', '')}' is missing methods defined in Blueprint",
                            affected_components=[component.get("id", "")],
                            # Store method names for easier parsing
                            action_data={"class_name": component.get('name', ''), "methods": list(missing_methods)}
                        ))

        # Check for modified components
        modified_components = blueprint_changes.get("modified_components", [])
        for component in modified_components:
            file_path = component.get("file", "")
            if file_path and Path(file_path).exists():
                existing = self._find_component_in_blueprint(
                    component.get("id", ""),
                    current_code_blueprint
                )
                if existing:
                    existing_methods = set(existing.get("methods", []))
                    blueprint_methods = set(component.get("methods", []))
                    missing_methods = blueprint_methods - existing_methods
                    extra_methods = existing_methods - blueprint_methods

                    if missing_methods:
                        suggestions.append(CodeChangeSuggestion(
                            suggestion_type="add_method",
                            file_path=file_path,
                            action=f"Add methods: {', '.join(missing_methods)}",
                            blueprint_component_id=component.get("id", ""),
                            reason=f"Component '{component.get('name', '')}' needs methods from updated Blueprint",
                            affected_components=[component.get("id", "")],
                            # Store method names for easier parsing
                            action_data={"class_name": component.get('name', ''), "methods": list(missing_methods)}
                        ))

        # Check for new contracts (dependencies)
        new_contracts = blueprint_changes.get("new_contracts", [])
        for contract in new_contracts:
            from_id = contract.get("from_id", "")
            to_id = contract.get("to_id", "")
            contract_type = contract.get("type", "dependency")

            from_file = self._get_file_for_component(from_id)
            to_file = self._get_file_for_component(to_id)

            if from_file and to_file:
                # Determine import path
                to_component = self._find_component_in_blueprint(to_id, self._load_blueprint())
                if to_component:
                    module_path = to_component.get("module_path", "")
                    component_name = to_component.get("name", "")

                    suggestions.append(CodeChangeSuggestion(
                        suggestion_type="add_import",
                        file_path=from_file,
                        action=f"Import {component_name} from {module_path}",
                        blueprint_component_id=from_id,
                        reason=f"Contract defined in Blueprint: {from_id} → {to_id} ({contract_type})",
                        affected_components=[from_id, to_id]
                    ))

        return suggestions

    def analyze_impact(
        self,
        blueprint_changes: Dict[str, Any],
        current_code_blueprint: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze impact of Blueprint changes on existing code.

        Args:
            blueprint_changes: Dict with changed components/contracts
            current_code_blueprint: Current code-extracted blueprint (optional)

        Returns:
            Dict with impact analysis:
            {
                "affected_files": [...],
                "affected_components": [...],
                "breaking_changes": [...],
                "safe_changes": [...],
                "migration_steps": [...]
            }
        """
        if current_code_blueprint is None:
            current_code_blueprint = self._load_code_blueprint()

        impact = {
            "affected_files": set(),
            "affected_components": [],
            "breaking_changes": [],
            "safe_changes": [],
            "migration_steps": []
        }

        # Analyze new components
        for component in blueprint_changes.get("new_components", []):
            file_path = component.get("file", "")
            if file_path:
                impact["affected_files"].add(file_path)
            impact["affected_components"].append(component.get("id", ""))
            impact["safe_changes"].append({
                "type": "new_component",
                "component_id": component.get("id", ""),
                "description": f"New component '{component.get('name', '')}' - safe to add"
            })

        # Analyze modified components
        for component in blueprint_changes.get("modified_components", []):
            file_path = component.get("file", "")
            if file_path:
                impact["affected_files"].add(file_path)

            component_id = component.get("id", "")
            impact["affected_components"].append(component_id)

            # Check if it's a breaking change (removed methods)
            existing = self._find_component_in_blueprint(component_id, current_code_blueprint)
            if existing:
                existing_methods = set(existing.get("methods", []))
                blueprint_methods = set(component.get("methods", []))
                removed_methods = existing_methods - blueprint_methods

                if removed_methods:
                    impact["breaking_changes"].append({
                        "type": "removed_methods",
                        "component_id": component_id,
                        "methods": list(removed_methods),
                        "description": f"Component '{component.get('name', '')}' has removed methods: {', '.join(removed_methods)}"
                    })

        # Analyze deleted components
        for component in blueprint_changes.get("deleted_components", []):
            file_path = component.get("file", "")
            if file_path:
                impact["affected_files"].add(file_path)

            component_id = component.get("id", "")
            impact["breaking_changes"].append({
                "type": "deleted_component",
                "component_id": component_id,
                "description": f"Component '{component.get('name', '')}' was deleted from Blueprint"
            })

        # Analyze new contracts
        for contract in blueprint_changes.get("new_contracts", []):
            from_file = self._get_file_for_component(contract.get("from_id", ""))
            to_file = self._get_file_for_component(contract.get("to_id", ""))

            if from_file:
                impact["affected_files"].add(from_file)
            if to_file:
                impact["affected_files"].add(to_file)

            impact["safe_changes"].append({
                "type": "new_contract",
                "from_id": contract.get("from_id", ""),
                "to_id": contract.get("to_id", ""),
                "description": f"New dependency: {contract.get('from_id', '')} → {contract.get('to_id', '')}"
            })

        # Convert sets to lists for JSON serialization
        impact["affected_files"] = list(impact["affected_files"])

        # Generate migration steps
        impact["migration_steps"] = self._generate_migration_steps(blueprint_changes, impact)

        return impact

    def _generate_migration_steps(
        self,
        blueprint_changes: Dict[str, Any],
        impact: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate step-by-step migration plan.

        Args:
            blueprint_changes: Detected Blueprint changes
            impact: Impact analysis result

        Returns:
            List of migration steps
        """
        steps = []
        step_num = 1

        # Step 1: Handle breaking changes first (deletions)
        deleted = blueprint_changes.get("deleted_components", [])
        if deleted:
            steps.append({
                "step": step_num,
                "type": "breaking",
                "action": "Review and remove deleted components",
                "components": [c.get("id", "") for c in deleted],
                "priority": "high"
            })
            step_num += 1

        # Step 2: Handle removed methods
        breaking = [c for c in impact["breaking_changes"] if c["type"] == "removed_methods"]
        if breaking:
            steps.append({
                "step": step_num,
                "type": "breaking",
                "action": "Update code to remove deprecated methods",
                "details": breaking,
                "priority": "high"
            })
            step_num += 1

        # Step 3: Add new components
        new_components = blueprint_changes.get("new_components", [])
        if new_components:
            steps.append({
                "step": step_num,
                "type": "addition",
                "action": "Create new components",
                "components": [c.get("id", "") for c in new_components],
                "priority": "medium"
            })
            step_num += 1

        # Step 4: Update modified components
        modified = blueprint_changes.get("modified_components", [])
        if modified:
            steps.append({
                "step": step_num,
                "type": "modification",
                "action": "Update existing components",
                "components": [c.get("id", "") for c in modified],
                "priority": "medium"
            })
            step_num += 1

        # Step 5: Add new contracts (dependencies)
        new_contracts = blueprint_changes.get("new_contracts", [])
        if new_contracts:
            steps.append({
                "step": step_num,
                "type": "dependency",
                "action": "Add imports and dependencies",
                "contracts": [f"{c.get('from_id', '')} → {c.get('to_id', '')}" for c in new_contracts],
                "priority": "low"
            })
            step_num += 1

        return steps

    def apply_blueprint_update(
        self,
        suggestion: BlueprintUpdateSuggestion,
        auto_apply: bool = False
    ) -> bool:
        """
        Apply a Blueprint update suggestion.

        Args:
            suggestion: Blueprint update suggestion
            auto_apply: If True, apply without confirmation

        Returns:
            True if applied successfully
        """
        if not auto_apply:
            # In real implementation, this would require user confirmation
            # For now, we'll just log it
            logger.info(f"Would apply Blueprint update: {suggestion.suggestion_type}")
            return False

        # Save backup before applying
        self._save_blueprint_backup()

        blueprint = self._load_blueprint()

        if suggestion.suggestion_type == "add_component" and suggestion.component:
            if "components" not in blueprint:
                blueprint["components"] = []

            # Convert Component to dict
            component_dict = {
                "id": suggestion.component.id,
                "name": suggestion.component.name,
                "type": suggestion.component.type,
                "file": suggestion.component.file,
                "line": suggestion.component.line,
                "methods": suggestion.component.methods,
                "attributes": suggestion.component.attributes,
                "module_path": suggestion.component.module_path
            }

            # Check if component already exists
            existing = self._find_component_in_blueprint(suggestion.component.id, blueprint)
            if not existing:
                blueprint["components"].append(component_dict)

        elif suggestion.suggestion_type == "update_component" and suggestion.component:
            # Find and update existing component
            if "components" in blueprint:
                for comp in blueprint["components"]:
                    if comp.get("id") == suggestion.component.id:
                        comp.update({
                            "name": suggestion.component.name,
                            "methods": suggestion.component.methods,
                            "attributes": suggestion.component.attributes
                        })
                        break

        elif suggestion.suggestion_type == "remove_component":
            # Remove component from Blueprint
            if "components" in blueprint:
                blueprint["components"] = [
                    c for c in blueprint["components"]
                    if c.get("id") != suggestion.component_id
                ]

        elif suggestion.suggestion_type == "add_contract" and suggestion.contract:
            if "contracts" not in blueprint:
                blueprint["contracts"] = []

            contract_dict = {
                "from_id": suggestion.contract.from_id,
                "to_id": suggestion.contract.to_id,
                "type": suggestion.contract.type,
                "symbols": suggestion.contract.symbols,
                "file": suggestion.contract.file
            }

            # Check if contract already exists
            existing_contract = next(
                (c for c in blueprint.get("contracts", [])
                 if (c.get("from_id") == contract_dict["from_id"] and
                     c.get("to_id") == contract_dict["to_id"] and
                     c.get("type") == contract_dict["type"])),
                None
            )
            if not existing_contract:
                blueprint["contracts"].append(contract_dict)

        return save_blueprint_with_metadata(
            blueprint,
            self.blueprint_file,
            "spec_first_management",
            False,
            "automatic_update"
        )

    def apply_blueprint_updates_batch(
        self,
        suggestions: List[BlueprintUpdateSuggestion],
        auto_apply: bool = False
    ) -> Dict[str, Any]:
        """
        Apply multiple Blueprint update suggestions in batch.

        Args:
            suggestions: List of Blueprint update suggestions
            auto_apply: If True, apply without confirmation

        Returns:
            Dict with results:
            {
                "applied": int,
                "failed": int,
                "errors": List[str]
            }
        """
        if not auto_apply:
            return {
                "applied": 0,
                "failed": 0,
                "errors": ["Auto-apply is disabled"]
            }

        results = {
            "applied": 0,
            "failed": 0,
            "errors": []
        }

        # Save backup before batch update
        self._save_blueprint_backup()

        for suggestion in suggestions:
            try:
                success = self.apply_blueprint_update(suggestion, auto_apply=True)
                if success:
                    results["applied"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(f"Failed to apply: {suggestion.suggestion_type}")
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Error applying {suggestion.suggestion_type}: {str(e)}")

        return results

    def _load_blueprint(self) -> Dict[str, Any]:
        """Load current Blueprint."""
        from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
        return BlueprintLoader.load_blueprint(self.manifest_dir, with_metadata=True)

    def _load_code_blueprint(self) -> Dict[str, Any]:
        """Load code-extracted Blueprint."""
        from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
        return BlueprintLoader.load_code_blueprint(self.manifest_dir)

    def _find_component_in_blueprint(
        self,
        component_id: str,
        blueprint: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Find a component in Blueprint by ID."""
        if not blueprint or "components" not in blueprint:
            return None

        return next(
            (c for c in blueprint["components"] if c.get("id") == component_id),
            None
        )

    def _create_component_from_change(
        self,
        change: StructuralChange
    ) -> Optional[Component]:
        """Create Component object from structural change."""
        if not change.component_data:
            return None

        return Component(
            id=change.component_id or f"{change.file_path}:{change.component_data.get('name', 'unknown')}",
            name=change.component_data.get("name", ""),
            type=change.component_data.get("type", "class"),
            file=change.file_path,
            line=0,  # Would need to extract from AST
            methods=change.component_data.get("methods", []),
            attributes=change.component_data.get("attributes", []),
            module_path=change.file_path.replace(str(self.project_root), "").lstrip("/")
        )

    def _suggest_file_path(self, component: Dict[str, Any]) -> str:
        """Suggest file path for a new component."""
        component_type = component.get("type", "class")
        component_name = component.get("name", "component")

        # Simple heuristic: use component name and type
        if component_type == "class":
            # Convert CamelCase to snake_case
            import re
            snake_case = re.sub(r'(?<!^)(?=[A-Z])', '_', component_name).lower()
            return f"src/{snake_case}.py"

        return f"src/{component_name.lower()}.py"

    def _get_file_for_component(self, component_id: str) -> str:
        """Get file path for a component ID."""
        blueprint = self._load_blueprint()
        component = self._find_component_in_blueprint(component_id, blueprint)
        return component.get("file", "") if component else ""

    def _save_blueprint_backup(self) -> bool:
        """Save a backup of the current Blueprint before applying changes."""
        try:
            if not self.blueprint_file.exists():
                return True  # Nothing to backup

            backup_file = self.blueprint_file.with_suffix(
                f".backup.{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            )

            import shutil
            shutil.copy2(self.blueprint_file, backup_file)

            # Keep only last 5 backups
            backup_dir = self.blueprint_file.parent
            backups = sorted(
                backup_dir.glob(f"{self.blueprint_file.stem}.backup.*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            for old_backup in backups[5:]:
                old_backup.unlink()

            return True
        except Exception as e:
            logger.warning(f"Failed to create Blueprint backup: {e}", exc_info=True)
            return False

    def _on_files_changed(self, changed_files: List[str]):
        """Callback when files are changed."""
        logger.info(f"Files changed: {changed_files}")
        # This will be used to trigger automatic detection in background
        pass

    def apply_code_change(self, suggestion: CodeChangeSuggestion) -> bool:
        """Apply a code change suggestion.

        Supports:
        - create_file: Create a new file with class skeleton
        - add_method: Add methods to an existing class
        - add_class: Add a class to an existing file
        - add_import: Add import statements to a file
        """
        try:
            file_path = Path(suggestion.file_path)

            if suggestion.suggestion_type == "create_file":
                # Create directory if needed
                file_path.parent.mkdir(parents=True, exist_ok=True)

                # Create file with basic skeleton
                content = f'"""\n{suggestion.action}\n"""\n\n'
                if suggestion.blueprint_component_id:
                    blueprint = self._load_blueprint()
                    comp = self._find_component_in_blueprint(suggestion.blueprint_component_id, blueprint)
                    if comp:
                        content += self._generate_class_skeleton(comp)

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                logger.info(f"Created file: {file_path}")
                return True

            elif suggestion.suggestion_type == "add_method":
                return self._add_method_to_class(file_path, suggestion)

            elif suggestion.suggestion_type == "add_class":
                return self._add_class_to_file(file_path, suggestion)

            elif suggestion.suggestion_type == "add_import":
                return self._add_import_to_file(file_path, suggestion)

            return False
        except Exception as e:
            logger.error(f"Error applying code change: {e}", exc_info=True)
            return False

    def _generate_class_skeleton(self, component: Dict[str, Any]) -> str:
        """Generate a basic Python class skeleton."""
        name = component.get("name", "NewClass")
        methods = component.get("methods", [])

        skeleton = f"class {name}:\n"
        skeleton += f'    """{component.get("type", "Component")} implementation."""\n\n'

        if not methods:
            skeleton += "    pass\n"
        else:
            for method in methods:
                skeleton += f"    def {method}(self):\n"
                skeleton += f'        """{method} implementation."""\n'
                skeleton += "        pass\n\n"

        return skeleton

    def _add_method_to_class(self, file_path: Path, suggestion: CodeChangeSuggestion) -> bool:
        """Add methods to an existing class using AST manipulation.

        Args:
            file_path: Path to the Python file
            suggestion: CodeChangeSuggestion with action containing method names

        Returns:
            True if methods were added successfully
        """
        try:
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return False

            # Extract method names and class name from action_data if available, otherwise parse action
            if suggestion.action_data and "class_name" in suggestion.action_data:
                target_class_name = suggestion.action_data["class_name"]
                method_names = suggestion.action_data.get("methods", [])
            else:
                # Fallback: Parse action to extract method names and class name
                # Format: "Add methods to ClassName: method1, method2" or "Add methods: method1, method2"
                action = suggestion.action
                class_match = re.search(r"to\s+(\w+)", action)
                methods_match = re.search(r":\s*(.+)", action)

                if not class_match:
                    logger.error(f"Could not extract class name from action: {action}")
                    return False

                target_class_name = class_match.group(1)
                method_names = []

                if methods_match:
                    method_names = [m.strip() for m in methods_match.group(1).split(",")]

            if not method_names:
                logger.warning(f"No methods specified in action: {suggestion.action}")
                return False

            # Read file content
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse AST
            try:
                tree = ast.parse(content, filename=str(file_path))
            except SyntaxError as e:
                logger.error(f"Syntax error in {file_path}: {e}")
                return False

            # Find the target class
            target_class = None
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == target_class_name:
                    target_class = node
                    break

            if not target_class:
                logger.error(f"Class '{target_class_name}' not found in {file_path}")
                return False

            # Check which methods already exist
            existing_methods = {
                n.name for n in target_class.body
                if isinstance(n, ast.FunctionDef)
            }

            methods_to_add = [m for m in method_names if m not in existing_methods]
            if not methods_to_add:
                logger.info(f"All methods already exist in class {target_class_name}")
                return True

            # Find insertion point (after last method or after docstring)
            lines = content.split("\n")
            insertion_line = target_class.lineno - 1  # 0-based index

            # Find the last method's end line
            last_method_end = insertion_line
            for node in target_class.body:
                if isinstance(node, ast.FunctionDef):
                    # Use end_lineno if available (Python 3.8+), otherwise estimate
                    if hasattr(node, 'end_lineno') and node.end_lineno:
                        last_method_end = node.end_lineno - 1  # 0-based index
                    else:
                        # Estimate: find the last line of the method by counting lines
                        method_start = node.lineno - 1
                        # Count non-empty lines in method body (rough estimate)
                        method_lines = 1  # def line
                        for stmt in node.body:
                            if hasattr(stmt, 'lineno'):
                                method_lines = max(method_lines, (stmt.lineno - node.lineno) + 1)
                        last_method_end = method_start + method_lines

            # Generate method code
            indent = "    "  # Standard Python indentation
            method_code = []
            for method_name in methods_to_add:
                method_code.append(f"{indent}def {method_name}(self):")
                method_code.append(f'{indent}    """{method_name} implementation."""')
                method_code.append(f"{indent}    pass")
                method_code.append("")

            # Insert methods after the last method
            lines.insert(last_method_end + 1, "\n".join(method_code))

            # Write back
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            logger.info(f"Added methods {methods_to_add} to class {target_class_name} in {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error adding methods to class: {e}", exc_info=True)
            return False

    def _add_class_to_file(self, file_path: Path, suggestion: CodeChangeSuggestion) -> bool:
        """Add a class to an existing file.

        Args:
            file_path: Path to the Python file
            suggestion: CodeChangeSuggestion with blueprint_component_id

        Returns:
            True if class was added successfully
        """
        try:
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return False

            # Load component from blueprint
            blueprint = self._load_blueprint()
            comp = self._find_component_in_blueprint(suggestion.blueprint_component_id, blueprint)
            if not comp:
                logger.error(f"Component {suggestion.blueprint_component_id} not found in blueprint")
                return False

            # Read file content
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Check if class already exists
            try:
                tree = ast.parse(content, filename=str(file_path))
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and node.name == comp.get("name"):
                        logger.info(f"Class {comp.get('name')} already exists in {file_path}")
                        return True
            except SyntaxError:
                # File might have syntax errors, but we'll still try to add the class
                pass

            # Generate class skeleton
            class_code = self._generate_class_skeleton(comp)

            # Append to file
            lines = content.split("\n")
            # Add blank line if file doesn't end with one
            if lines and lines[-1].strip():
                lines.append("")
            lines.append(class_code)

            # Write back
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            logger.info(f"Added class {comp.get('name')} to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error adding class to file: {e}", exc_info=True)
            return False

    def _add_import_to_file(self, file_path: Path, suggestion: CodeChangeSuggestion) -> bool:
        """Add import statement to a file.

        Args:
            file_path: Path to the Python file
            suggestion: CodeChangeSuggestion with action containing import statement

        Returns:
            True if import was added successfully
        """
        try:
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return False

            # Parse action to extract import statement
            # Format: "Import ClassName from module.path"
            action = suggestion.action
            import_match = re.search(r"Import\s+(\w+)\s+from\s+(.+)", action)

            if not import_match:
                logger.error(f"Could not parse import from action: {action}")
                return False

            import_name = import_match.group(1)
            module_path = import_match.group(2).strip()

            # Read file content
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Check if import already exists
            import_line = f"from {module_path} import {import_name}"
            if import_line in content:
                logger.info(f"Import already exists: {import_line}")
                return True

            # Parse AST to find insertion point (after existing imports)
            try:
                tree = ast.parse(content, filename=str(file_path))
                last_import_line = 0

                for node in ast.walk(tree):
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        if hasattr(node, 'lineno'):
                            last_import_line = max(last_import_line, node.lineno)
                        elif isinstance(node, ast.ImportFrom) and node.module:
                            # Find the line number
                            for child in ast.walk(tree):
                                if child == node and hasattr(child, 'lineno'):
                                    last_import_line = max(last_import_line, child.lineno)
                                    break
            except SyntaxError:
                # If parsing fails, insert at the top
                last_import_line = 0

            # Insert import
            lines = content.split("\n")
            insertion_idx = last_import_line  # 0-based index (lineno is 1-based)

            # Find the actual insertion point (after last import block)
            if insertion_idx > 0:
                # Skip to after the last import
                while insertion_idx < len(lines) and (
                    lines[insertion_idx].strip().startswith("import ") or
                    lines[insertion_idx].strip().startswith("from ") or
                    not lines[insertion_idx].strip()
                ):
                    insertion_idx += 1
            else:
                # Insert at the beginning, but skip shebang and docstring
                insertion_idx = 0
                if lines and lines[0].startswith("#!"):
                    insertion_idx = 1
                # Skip module docstring
                if insertion_idx < len(lines) and (
                    lines[insertion_idx].strip().startswith('"""') or
                    lines[insertion_idx].strip().startswith("'''")
                ):
                    # Find end of docstring
                    quote = lines[insertion_idx].strip()[:3]
                    insertion_idx += 1
                    while insertion_idx < len(lines) and quote not in lines[insertion_idx]:
                        insertion_idx += 1
                    insertion_idx += 1

            # Add blank line before import if needed
            if insertion_idx > 0 and lines[insertion_idx - 1].strip():
                lines.insert(insertion_idx, "")
                insertion_idx += 1

            # Insert import
            lines.insert(insertion_idx, import_line)

            # Write back
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            logger.info(f"Added import '{import_line}' to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error adding import to file: {e}", exc_info=True)
            return False
