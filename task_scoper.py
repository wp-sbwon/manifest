"""
Task Scoping System - Manages task boundaries and context scoping.
Ensures worker agents only see relevant context for their assigned tasks.
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Set


class TaskScoper:
    """Manages task boundaries and context scoping."""
    
    def __init__(self, manifest_dir: Path = None):
        self.manifest_dir = manifest_dir or Path(".manifest")
        self.blueprint_file = self.manifest_dir / "blueprint.json"
        self.intent_file = self.manifest_dir / "intent.json"
        self._blueprint_data = {}
        self._intent_data = {}
        self._load_data()
    
    def _load_data(self):
        """Load blueprint and intent data."""
        # Load blueprint
        if self.blueprint_file.exists():
            try:
                with open(self.blueprint_file, "r") as f:
                    self._blueprint_data = json.load(f)
            except Exception:
                self._blueprint_data = {"version": "1.0", "zones": {}, "components": [], "contracts": []}
        else:
            self._blueprint_data = {"version": "1.0", "zones": {}, "components": [], "contracts": []}
        
        # Load intent
        if self.intent_file.exists():
            try:
                with open(self.intent_file, "r") as f:
                    self._intent_data = json.load(f)
            except Exception:
                self._intent_data = {"version": "1.0", "sprint": "", "features": []}
        else:
            self._intent_data = {"version": "1.0", "sprint": "", "features": []}
    
    def get_task_context(self, task_id: str) -> Dict[str, Any]:
        """Get scoped context for a task."""
        # Get task from state (would need state_manager, but keeping it simple for now)
        # For now, we'll infer from blueprint and intent
        
        # Find components related to task
        components = self._get_task_components(task_id)
        
        # Find files related to task
        files = self._get_task_files(task_id, components)
        
        # Get task-specific requirements
        requirements = self._get_task_requirements(task_id)
        
        # Determine allowed file modifications
        allowed_modifications = self._get_allowed_modifications(components, files)
        
        return {
            "components": components,
            "files": files,
            "requirements": requirements,
            "allowed_modifications": allowed_modifications
        }
    
    def _get_task_components(self, task_id: str) -> List[Dict[str, Any]]:
        """Get blueprint components related to task."""
        # In a real implementation, tasks would be mapped to components
        # For now, return all components (can be refined later)
        components = self._blueprint_data.get("components", [])
        
        # Filter by task_id if components have task_id field
        task_components = []
        for comp in components:
            if comp.get("task_id") == task_id or task_id in comp.get("tasks", []):
                task_components.append(comp)
            # If no task mapping, include all (will be refined with actual task mapping)
        
        return task_components if task_components else components
    
    def _get_task_files(self, task_id: str, components: List[Dict[str, Any]]) -> List[str]:
        """Get files related to task based on components."""
        files = set()
        
        # Get files from components
        for comp in components:
            comp_files = comp.get("files", [])
            if isinstance(comp_files, list):
                files.update(comp_files)
            elif isinstance(comp_files, str):
                files.add(comp_files)
        
        # Get files from zones
        zones = self._blueprint_data.get("zones", {})
        for zone_name, zone_components in zones.items():
            for comp in zone_components:
                if comp in components or any(c.get("id") == comp.get("id") for c in components):
                    comp_files = comp.get("files", [])
                    if isinstance(comp_files, list):
                        files.update(comp_files)
                    elif isinstance(comp_files, str):
                        files.add(comp_files)
        
        return sorted(list(files))
    
    def _get_task_requirements(self, task_id: str) -> List[Dict[str, Any]]:
        """Get task-specific requirements from intent.json."""
        features = self._intent_data.get("features", [])
        requirements = []
        
        # Find feature that contains this task
        for feature in features:
            feature_tasks = feature.get("tasks", [])
            if task_id in feature_tasks or any(t.get("id") == task_id for t in feature_tasks if isinstance(t, dict)):
                # Get requirements for this feature
                reqs = feature.get("reqs", [])
                requirements.extend(reqs)
        
        return requirements
    
    def _get_allowed_modifications(self, components: List[Dict[str, Any]], files: List[str]) -> List[str]:
        """Determine allowed file modification paths."""
        allowed = set()
        
        # Add directories from files
        for file_path in files:
            path = Path(file_path)
            if path.parent != Path("."):
                allowed.add(str(path.parent))
        
        # Add directories from components
        for comp in components:
            comp_dir = comp.get("directory")
            if comp_dir:
                allowed.add(comp_dir)
        
        return sorted(list(allowed)) if allowed else ["."]  # Default to current directory
    
    def validate_task_scope(self, task_id: str, file_path: str) -> bool:
        """Check if file is in task scope."""
        task_context = self.get_task_context(task_id)
        allowed_files = task_context.get("files", [])
        allowed_modifications = task_context.get("allowed_modifications", [])
        
        # Check exact file match
        if file_path in allowed_files:
            return True
        
        # Check if file is in allowed modification directory
        file_path_obj = Path(file_path)
        for allowed_dir in allowed_modifications:
            allowed_dir_obj = Path(allowed_dir)
            try:
                file_path_obj.relative_to(allowed_dir_obj)
                return True
            except ValueError:
                continue
        
        return False
    
    def get_task_scope_summary(self, task_id: str) -> Dict[str, Any]:
        """Get a summary of task scope for display."""
        context = self.get_task_context(task_id)
        return {
            "task_id": task_id,
            "component_count": len(context.get("components", [])),
            "file_count": len(context.get("files", [])),
            "requirement_count": len(context.get("requirements", [])),
            "allowed_directories": context.get("allowed_modifications", [])
        }