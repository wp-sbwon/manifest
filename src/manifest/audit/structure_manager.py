"""
Structure Manager - Manages structural changes based on Blueprint specifications.
Implements Spec-First Management: Blueprint changes drive code changes, and vice versa.
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field

from manifest.audit.code_extractor import CodeExtractor, Component, Contract
from manifest.audit.blueprint_metadata import load_blueprint_with_metadata, save_blueprint_with_metadata
from manifest.audit.blueprint_comparator import BlueprintComparator
from manifest.audit.file_watcher import FileWatcher


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
                print(f"Error extracting structure from {file_path}: {e}")
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
    
    def suggest_code_changes(
        self,
        blueprint_changes: Dict[str, Any],
        current_code_blueprint: Optional[Dict[str, Any]] = None
    ) -> List[CodeChangeSuggestion]:
        """
        Generate suggestions to change code based on Blueprint changes.
        
        Args:
            blueprint_changes: Dict with changed components/contracts
            current_code_blueprint: Current code-extracted blueprint (optional)
            
        Returns:
            List of code change suggestions
        """
        if current_code_blueprint is None:
            current_code_blueprint = self._load_code_blueprint()
        
        suggestions = []
        
        # Check for new components in Blueprint
        new_components = blueprint_changes.get("new_components", [])
        for component in new_components:
            file_path = component.get("file", "")
            if not file_path or not Path(file_path).exists():
                # Component doesn't exist in code - suggest creating it
                suggestions.append(CodeChangeSuggestion(
                    suggestion_type="create_file",
                    file_path=file_path or self._suggest_file_path(component),
                    action=f"Create {component.get('type', 'component')} {component.get('name', '')}",
                    blueprint_component_id=component.get("id", ""),
                    reason=f"Component defined in Blueprint but not found in code",
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
                        action=f"Add class {component.get('name', '')}",
                        blueprint_component_id=component.get("id", ""),
                        reason=f"Component defined in Blueprint but missing in code",
                        affected_components=[component.get("id", "")]
                    ))
        
        # Check for new contracts (dependencies)
        new_contracts = blueprint_changes.get("new_contracts", [])
        for contract in new_contracts:
            from_id = contract.get("from_id", "")
            to_id = contract.get("to_id", "")
            
            suggestions.append(CodeChangeSuggestion(
                suggestion_type="add_import",
                file_path=self._get_file_for_component(from_id),
                action=f"Import {to_id}",
                blueprint_component_id=from_id,
                reason=f"Contract defined in Blueprint: {from_id} → {to_id}",
                affected_components=[from_id, to_id]
            ))
        
        return suggestions
    
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
            print(f"Would apply Blueprint update: {suggestion.suggestion_type}")
            return False
        
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
        
        # Save updated blueprint
        return save_blueprint_with_metadata(
            blueprint,
            self.blueprint_file,
            "spec_first_management",
            False,
            "automatic_update"
        )
    
    def _load_blueprint(self) -> Dict[str, Any]:
        """Load current Blueprint."""
        if self.blueprint_file.exists():
            return load_blueprint_with_metadata(
                self.blueprint_file,
                "llm_design",
                False
            )
        return {"version": "1.0", "components": [], "contracts": []}
    
    def _load_code_blueprint(self) -> Dict[str, Any]:
        """Load code-extracted Blueprint."""
        if self.blueprint_code_file.exists():
            return load_blueprint_with_metadata(
                self.blueprint_code_file,
                "code_extraction",
                True
            )
        return {"version": "1.0", "components": [], "contracts": []}
    
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
