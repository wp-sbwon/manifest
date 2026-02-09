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
from manifest.audit.entity_schema import (
    PROJECT_ROOT_ID,
    empty_intent,
    empty_reality,
    empty_outgoing_contracts,
)
from manifest.audit.monitoring.file_watcher import FileWatcher
from manifest.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StructuralChange:
    """Represents a structural change detected in code."""
    change_type: str  # "added", "modified", "deleted"
    node_id: Optional[str] = None
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
    blueprint_entity_id: str = ""
    reason: str = ""
    affected_entities: List[str] = field(default_factory=list)
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
        from manifest.audit.blueprint.manifest_filenames import BLUEPRINT_DESIGN_FILE, BLUEPRINT_CODE_FILE
        self.blueprint_file = self.manifest_dir / BLUEPRINT_DESIGN_FILE
        self.blueprint_code_file = self.manifest_dir / BLUEPRINT_CODE_FILE

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
                        existing = self._find_entity_in_blueprint(
                            component.id,
                            previous_blueprint
                        )
                        if existing:
                            change_type = "modified"

                    changes.append(StructuralChange(
                        change_type=change_type,
                        node_id=component.id,
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
                # Suggest adding to Blueprint
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
                # Suggest updating in Blueprint
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
                # Suggest removing from Blueprint
                if change.node_id:
                    suggestions.append(BlueprintUpdateSuggestion(
                        suggestion_type="remove_component",
                        reason=f"Node deleted: {change.node_id}",
                        confidence=0.7,
                        affected_files=[change.file_path]
                    ))

        return suggestions

    def detect_blueprint_changes(
        self,
        previous_blueprint: Optional[Dict[str, Any]] = None,
        current_blueprint: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Detect changes between previous and current Blueprint.

        Args:
            previous_blueprint: Previous Blueprint (optional).
            current_blueprint: Current Blueprint (optional).

        Returns:
            Dict with new_entities, modified_entities, deleted_entities, new_contracts, modified_contracts, deleted_contracts.
        """
        if previous_blueprint is None:
            previous_blueprint = self._load_previous_blueprint() or {"entities": []}

        if current_blueprint is None:
            current_blueprint = self._load_blueprint()

        changes = {
            "new_entities": [],
            "modified_entities": [],
            "deleted_entities": [],
            "new_contracts": [],
            "modified_contracts": [],
            "deleted_contracts": []
        }

        from manifest.audit.entity_schema import non_root_entities

        def _entity_methods(e: Dict[str, Any]) -> list:
            return (e.get("reality") or {}).get("methods", e.get("methods", []))

        def _entity_attributes(e: Dict[str, Any]) -> list:
            return (e.get("reality") or {}).get("attributes", e.get("attributes", []))

        prev_entities = {e.get("id"): e for e in non_root_entities(previous_blueprint)}
        curr_entities = {e.get("id"): e for e in non_root_entities(current_blueprint)}

        for ent_id, ent in curr_entities.items():
            if ent_id not in prev_entities:
                changes["new_entities"].append(ent)
            else:
                prev_ent = prev_entities[ent_id]
                if (_entity_methods(ent) != _entity_methods(prev_ent) or
                    _entity_attributes(ent) != _entity_attributes(prev_ent)):
                    changes["modified_entities"].append(ent)

        for ent_id in prev_entities:
            if ent_id not in curr_entities:
                changes["deleted_entities"].append(prev_entities[ent_id])

        from manifest.audit.entity_schema import contracts_from_entities

        prev_flat = contracts_from_entities(previous_blueprint.get("entities", []))
        curr_flat = contracts_from_entities(current_blueprint.get("entities", []))
        prev_contracts = {
            (c.get("from"), c.get("to"), c.get("type")): c for c in prev_flat
        }
        curr_contracts = {
            (c.get("from"), c.get("to"), c.get("type")): c for c in curr_flat
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
            blueprint_changes: Detected changes (optional).
            current_code_blueprint: Code blueprint (optional).

        Returns:
            List of code change suggestions
        """
        if blueprint_changes is None:
            blueprint_changes = self.detect_blueprint_changes()

        if current_code_blueprint is None:
            current_code_blueprint = self._load_code_blueprint()

        suggestions = []

        new_entities = blueprint_changes.get("new_entities", [])
        for entity in new_entities:
            file_path = entity.get("file", "")
            if not file_path or not Path(file_path).exists():
                suggested_path = self._suggest_file_path(entity)
                suggestions.append(CodeChangeSuggestion(
                    suggestion_type="create_file",
                    file_path=suggested_path,
                    action=f"Create {entity.get('type', 'entity')} {entity.get('name', '')} with methods: {', '.join(entity.get('methods', []))}",
                    blueprint_entity_id=entity.get("id", ""),
                    reason=f"Entity '{entity.get('name', '')}' defined in Blueprint but not found in code",
                    affected_entities=[entity.get("id", "")]
                ))
            else:
                existing = self._find_entity_in_blueprint(
                    entity.get("id", ""),
                    current_code_blueprint
                )
                if not existing:
                    suggestions.append(CodeChangeSuggestion(
                        suggestion_type="add_class",
                        file_path=file_path,
                        action=f"Add class {entity.get('name', '')} with methods: {', '.join(entity.get('methods', []))}",
                        blueprint_entity_id=entity.get("id", ""),
                        reason=f"Entity '{entity.get('name', '')}' defined in Blueprint but missing in code file",
                        affected_entities=[entity.get("id", "")]
                    ))
                else:
                    existing_methods = set(existing.get("methods", []))
                    blueprint_methods = set(entity.get("methods", []))
                    missing_methods = blueprint_methods - existing_methods

                    if missing_methods:
                        suggestions.append(CodeChangeSuggestion(
                            suggestion_type="add_method",
                            file_path=file_path,
                            action=f"Add methods to {entity.get('name', '')}: {', '.join(missing_methods)}",
                            blueprint_entity_id=entity.get("id", ""),
                            reason=f"Entity '{entity.get('name', '')}' is missing methods defined in Blueprint",
                            affected_entities=[entity.get("id", "")],
                            action_data={"class_name": entity.get('name', ''), "methods": list(missing_methods)}
                        ))

        modified_entities = blueprint_changes.get("modified_entities", [])
        for entity in modified_entities:
            file_path = entity.get("file", "")
            if file_path and Path(file_path).exists():
                existing = self._find_entity_in_blueprint(
                    entity.get("id", ""),
                    current_code_blueprint
                )
                if existing:
                    existing_methods = set(existing.get("methods", []))
                    blueprint_methods = set(entity.get("methods", []))
                    missing_methods = blueprint_methods - existing_methods

                    if missing_methods:
                        suggestions.append(CodeChangeSuggestion(
                            suggestion_type="add_method",
                            file_path=file_path,
                            action=f"Add methods: {', '.join(missing_methods)}",
                            blueprint_entity_id=entity.get("id", ""),
                            reason=f"Entity '{entity.get('name', '')}' needs methods from updated Blueprint",
                            affected_entities=[entity.get("id", "")],
                            action_data={"class_name": entity.get('name', ''), "methods": list(missing_methods)}
                        ))

        new_contracts = blueprint_changes.get("new_contracts", [])
        for contract in new_contracts:
            from_id = contract.get("from", "")
            to_id = contract.get("to", "")
            contract_type = contract.get("type", "dependency")

            from_file = self._get_file_for_entity(from_id)
            to_file = self._get_file_for_entity(to_id)

            if from_file and to_file:
                to_entity = self._find_entity_in_blueprint(to_id, self._load_blueprint())
                if to_entity:
                    module_path = to_entity.get("module_path", "")
                    entity_name = to_entity.get("name", "")

                    suggestions.append(CodeChangeSuggestion(
                        suggestion_type="add_import",
                        file_path=from_file,
                        action=f"Import {entity_name} from {module_path}",
                        blueprint_entity_id=from_id,
                        reason=f"Contract defined in Blueprint: {from_id} → {to_id} ({contract_type})",
                        affected_entities=[from_id, to_id]
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
            blueprint_changes: Detected changes.
            current_code_blueprint: Code blueprint (optional).

        Returns:
            Dict with affected_files, affected_entities, breaking_changes, safe_changes, migration_steps.
        """
        if current_code_blueprint is None:
            current_code_blueprint = self._load_code_blueprint()

        impact = {
            "affected_files": set(),
            "affected_entities": [],
            "breaking_changes": [],
            "safe_changes": [],
            "migration_steps": []
        }

        for entity in blueprint_changes.get("new_entities", []):
            file_path = entity.get("file", "")
            if file_path:
                impact["affected_files"].add(file_path)
            impact["affected_entities"].append(entity.get("id", ""))
            impact["safe_changes"].append({
                "type": "new_entity",
                "entity_id": entity.get("id", ""),
                "description": f"New entity '{entity.get('name', '')}' - safe to add"
            })

        for entity in blueprint_changes.get("modified_entities", []):
            file_path = entity.get("file", "")
            if file_path:
                impact["affected_files"].add(file_path)

            entity_id = entity.get("id", "")
            impact["affected_entities"].append(entity_id)

            existing = self._find_entity_in_blueprint(entity_id, current_code_blueprint)
            if existing:
                existing_methods = set(existing.get("methods", []))
                blueprint_methods = set(entity.get("methods", []))
                removed_methods = existing_methods - blueprint_methods

                if removed_methods:
                    impact["breaking_changes"].append({
                        "type": "removed_methods",
                        "entity_id": entity_id,
                        "methods": list(removed_methods),
                        "description": f"Entity '{entity.get('name', '')}' has removed methods: {', '.join(removed_methods)}"
                    })

        for entity in blueprint_changes.get("deleted_entities", []):
            file_path = entity.get("file", "")
            if file_path:
                impact["affected_files"].add(file_path)

            entity_id = entity.get("id", "")
            impact["breaking_changes"].append({
                "type": "deleted_entity",
                "entity_id": entity_id,
                "description": f"Entity '{entity.get('name', '')}' was deleted from Blueprint"
            })

        # Analyze new contracts
        for contract in blueprint_changes.get("new_contracts", []):
            from_file = self._get_file_for_entity(contract.get("from", ""))
            to_file = self._get_file_for_entity(contract.get("to", ""))

            if from_file:
                impact["affected_files"].add(from_file)
            if to_file:
                impact["affected_files"].add(to_file)

            impact["safe_changes"].append({
                "type": "new_contract",
                "from_id": contract.get("from", ""),
                "to_id": contract.get("to", ""),
                "description": f"New dependency: {contract.get('from', '')} → {contract.get('to', '')}"
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

        deleted = blueprint_changes.get("deleted_entities", [])
        if deleted:
            steps.append({
                "step": step_num,
                "type": "breaking",
                "action": "Review and remove deleted entities",
                "entities": [e.get("id", "") for e in deleted],
                "priority": "high"
            })
            step_num += 1

        breaking = [c for c in impact["breaking_changes"] if c["type"] == "removed_methods"]
        if breaking:
            steps.append({
                "step": step_num,
                "type": "breaking",
                "action": "Update code to remove methods no longer in design",
                "details": breaking,
                "priority": "high"
            })
            step_num += 1

        new_entities = blueprint_changes.get("new_entities", [])
        if new_entities:
            steps.append({
                "step": step_num,
                "type": "addition",
                "action": "Create new entities",
                "entities": [e.get("id", "") for e in new_entities],
                "priority": "medium"
            })
            step_num += 1

        modified = blueprint_changes.get("modified_entities", [])
        if modified:
            steps.append({
                "step": step_num,
                "type": "modification",
                "action": "Update existing entities",
                "entities": [e.get("id", "") for e in modified],
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
                "contracts": [f"{c.get('from', '')} → {c.get('to', '')}" for c in new_contracts],
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
        entities = blueprint.get("entities") or []
        root_entity = next((e for e in entities if (e.get("id") or "") == PROJECT_ROOT_ID), None)

        if suggestion.suggestion_type == "add_component" and suggestion.component:
            if "entities" not in blueprint:
                blueprint["entities"] = []

            existing = self._find_entity_in_blueprint(suggestion.component.id, blueprint)
            if not existing:
                intent = empty_intent()
                intent.setdefault("narrative", {})["role"] = suggestion.component.name
                intent.setdefault("narrative", {})["mission"] = ""
                entity = {
                    "id": suggestion.component.id,
                    "children": [],
                    "dependencies": [],
                    "intent": intent,
                    "reality": empty_reality(),
                    "outgoing_contracts": empty_outgoing_contracts(),
                    "name": suggestion.component.name,
                    "file": suggestion.component.file or "",
                    "methods": suggestion.component.methods or [],
                    "attributes": suggestion.component.attributes or [],
                }
                if (suggestion.component.line or 0) > 0:
                    entity["line"] = suggestion.component.line
                entity["module_path"] = suggestion.component.module_path or ""
                blueprint["entities"].append(entity)
                if root_entity is not None:
                    children = list(root_entity.get("children") or [])
                    if suggestion.component.id not in children:
                        children.append(suggestion.component.id)
                        root_entity["children"] = children

        elif suggestion.suggestion_type == "update_component" and suggestion.component:
            for ent in blueprint.get("entities") or []:
                if (ent.get("id") or "") == PROJECT_ROOT_ID:
                    continue
                if ent.get("id") == suggestion.component.id:
                    ent["name"] = suggestion.component.name
                    intent = ent.get("intent") or {}
                    narrative = intent.get("narrative") or {}
                    narrative["role"] = suggestion.component.name
                    intent["narrative"] = narrative
                    ent["intent"] = intent
                    if suggestion.component.methods is not None:
                        ent["methods"] = suggestion.component.methods
                    if suggestion.component.attributes is not None:
                        ent["attributes"] = suggestion.component.attributes
                    break

        elif suggestion.suggestion_type == "remove_component":
            if entities:
                blueprint["entities"] = [
                    e for e in entities
                    if e.get("id") != suggestion.blueprint_entity_id
                ]
                if root_entity is not None:
                    root_entity["children"] = [
                        cid for cid in (root_entity.get("children") or [])
                        if cid != suggestion.blueprint_entity_id
                    ]

        elif suggestion.suggestion_type == "add_contract" and suggestion.contract:
            from_id = suggestion.contract.from_id or ""
            to_id = suggestion.contract.to_id or ""
            oc = {
                "to": to_id,
                "type": suggestion.contract.type or "dependency",
                "file": suggestion.contract.file or "",
                "symbols": list(suggestion.contract.symbols or []),
            }
            for ent in blueprint.get("entities") or []:
                if (ent.get("id") or "") != from_id:
                    continue
                ocs = ent.setdefault("outgoing_contracts", [])
                if not isinstance(ocs, list):
                    ent["outgoing_contracts"] = []
                    ocs = ent["outgoing_contracts"]
                if any(
                    (x.get("to") == to_id and (x.get("type") or "dependency") == (oc.get("type") or "dependency"))
                    for x in ocs if isinstance(x, dict)
                ):
                    break
                ocs.append(oc)
                break

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

    def _find_entity_in_blueprint(
        self,
        entity_id: str,
        blueprint: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Find entity in blueprint by ID."""
        if not blueprint:
            return None
        entities = blueprint.get("entities") or []
        for ent in entities:
            if (ent.get("id") or "") == PROJECT_ROOT_ID:
                continue
            if ent.get("id") == entity_id:
                return ent
        return None

    def _create_component_from_change(
        self,
        change: StructuralChange
    ) -> Optional[Component]:
        """Create Component object from structural change."""
        if not change.component_data:
            return None

        return Component(
            id=change.node_id or f"{change.file_path}:{change.component_data.get('name', 'unknown')}",
            name=change.component_data.get("name", ""),
            type=change.component_data.get("type", "class"),
            file=change.file_path,
            line=0,  # Would need to extract from AST
            methods=change.component_data.get("methods", []),
            attributes=change.component_data.get("attributes", []),
            module_path=change.file_path.replace(str(self.project_root), "").lstrip("/")
        )

    def _suggest_file_path(self, entity: Dict[str, Any]) -> str:
        """Suggest file path for a new entity."""
        entity_type = entity.get("type", "class")
        entity_name = entity.get("name", "entity")

        if entity_type == "class":
            import re
            snake_case = re.sub(r'(?<!^)(?=[A-Z])', '_', entity_name).lower()
            return f"src/{snake_case}.py"

        return f"src/{entity_name.lower()}.py"

    def _get_file_for_entity(self, entity_id: str) -> str:
        """Get file path for an entity ID."""
        blueprint = self._load_blueprint()
        ent = self._find_entity_in_blueprint(entity_id, blueprint)
        if not ent:
            return ""
        return (ent.get("reality") or {}).get("symbol", ent.get("file", ""))

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
                if suggestion.blueprint_entity_id:
                    blueprint = self._load_blueprint()
                    comp = self._find_entity_in_blueprint(suggestion.blueprint_entity_id, blueprint)
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
                # Parse action when action_data is missing. Format: "Add methods to ClassName: method1, method2"
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
            suggestion: CodeChangeSuggestion with blueprint_entity_id

        Returns:
            True if class was added successfully
        """
        try:
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return False

            # Load component from blueprint
            blueprint = self._load_blueprint()
            comp = self._find_entity_in_blueprint(suggestion.blueprint_entity_id, blueprint)
            if not comp:
                logger.error(f"Node {suggestion.blueprint_entity_id} not found in blueprint")
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
