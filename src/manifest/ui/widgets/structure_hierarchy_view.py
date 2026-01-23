"""
Structure Hierarchy View - Tree-based hierarchical display of Features, Requirements, and Components.
"""
from textual.widgets import Tree
from textual import on
from typing import Dict, Any, List, Optional
from pathlib import Path


class StructureHierarchyView(Tree):
    """Tree-based hierarchical view showing Features → Requirements → Components."""
    
    def __init__(self, *args, **kwargs):
        super().__init__("Project Structure", *args, **kwargs)
        self.architecture_data: Dict[str, Any] = {}
        self.blueprint_data: Dict[str, Any] = {}
        self.status_info: Dict[str, Any] = {}
        self.component_statuses: Dict[str, str] = {}
        self.feature_completions: Dict[str, float] = {}
    
    def load_data(
        self,
        architecture: Dict[str, Any],
        blueprint: Dict[str, Any],
        status_info: Optional[Dict[str, Any]] = None
    ):
        """
        Load architecture and blueprint data with status information.
        
        Args:
            architecture: Architecture data (features, requirements)
            blueprint: Blueprint data (components)
            status_info: Status information from BlueprintSynchronizer
        """
        self.architecture_data = architecture
        self.blueprint_data = blueprint
        self.status_info = status_info or {}
        self.component_statuses = status_info.get("component_statuses", {}) if status_info else {}
        self.feature_completions = status_info.get("feature_completions", {}) if status_info else {}
        
        self._build_tree()
    
    def _build_tree(self):
        """Build the tree structure from architecture and blueprint data."""
        self.clear()
        root = self.root
        
        features = self.architecture_data.get("features", [])
        components_by_id: Dict[str, Dict[str, Any]] = {}
        
        # Build component lookup from blueprint
        for comp in self.blueprint_data.get("components", []):
            comp_id = comp.get("id", "")
            if comp_id:
                components_by_id[comp_id] = comp
        
        # Add each feature
        for feature in features:
            feature_id = feature.get("id", "")
            feature_name = feature.get("name", "Unknown Feature")
            feature_status = feature.get("status", "pending")
            completion = self.feature_completions.get(feature_id, feature.get("completion_percentage", 0))
            
            # Status icon and color
            status_icon, status_color = self._get_status_icon_color(feature_status, completion)
            
            # Feature node with completion percentage
            feature_label = f"{status_icon} {feature_name} ({completion}% 완료)"
            feature_node = root.add(feature_label, expand=True)
            feature_node.data = {
                "type": "feature",
                "id": feature_id,
                "status": feature_status,
                "completion": completion
            }
            
            # Add requirements
            requirements = feature.get("requirements", [])
            for req in requirements:
                req_id = req.get("id", "")
                req_desc = req.get("description", req.get("desc", "Unknown Requirement"))
                req_state = req.get("state", "pending")
                
                # Requirement state icon
                req_icon = "✔" if req_state == "done" else "○" if req_state == "pending" else "⚡"
                req_label = f"{req_icon} {req_id}: {req_desc}"
                req_node = feature_node.add(req_label, expand=True)
                req_node.data = {
                    "type": "requirement",
                    "id": req_id,
                    "state": req_state
                }
                
                # Add components for this requirement
                req_components = req.get("components", [])
                for comp_id in req_components:
                    comp = components_by_id.get(comp_id)
                    if comp:
                        self._add_component_node(req_node, comp, comp_id)
            
            # Also add components directly linked to feature
            feature_components = feature.get("components", [])
            for comp_id in feature_components:
                comp = components_by_id.get(comp_id)
                if comp:
                    # Check if already added under a requirement
                    already_added = False
                    for req in requirements:
                        if comp_id in req.get("components", []):
                            already_added = True
                            break
                    
                    if not already_added:
                        self._add_component_node(feature_node, comp, comp_id)
        
        # Expand root by default
        root.expand()
    
    def _add_component_node(self, parent_node, comp: Dict[str, Any], comp_id: str):
        """Add a component node to the tree."""
        comp_name = comp.get("name", "Unknown")
        comp_type = comp.get("type", "unknown")
        comp_file = comp.get("file", "")
        comp_line = comp.get("line", 0)
        
        # Get status
        status = self.component_statuses.get(comp_id, comp.get("status", "pending"))
        
        # Status icon and metadata tags
        status_icon, _ = self._get_component_status_icon(status)
        
        # Metadata tags (algorithm, design_pattern, complexity)
        metadata_tags = []
        if comp.get("algorithm"):
            metadata_tags.append(comp["algorithm"])
        if comp.get("design_pattern"):
            metadata_tags.append(comp["design_pattern"])
        if comp.get("complexity"):
            metadata_tags.append(comp["complexity"])
        
        metadata_str = f" [{'] ['.join(metadata_tags)}]" if metadata_tags else ""
        
        # Component label
        comp_label = f"{status_icon} {comp_name}{metadata_str}"
        comp_node = parent_node.add(comp_label, expand=False)
        comp_node.data = {
            "type": "component",
            "id": comp_id,
            "status": status,
            "file": comp_file,
            "line": comp_line
        }
        
        # Add file path as child node
        if comp_file:
            file_label = f"📁 {comp_file}:{comp_line}"
            file_node = comp_node.add(file_label, expand=False)
            file_node.data = {
                "type": "file",
                "file": comp_file,
                "line": comp_line
            }
        
        # Add methods if available
        methods = comp.get("methods", [])
        if methods:
            methods_label = f"Methods: {', '.join(methods[:5])}"
            if len(methods) > 5:
                methods_label += f" (+{len(methods) - 5} more)"
            methods_node = comp_node.add(methods_label, expand=False)
            methods_node.data = {"type": "methods", "methods": methods}
    
    def _get_status_icon_color(self, status: str, completion: float) -> tuple[str, str]:
        """Get status icon and color for feature."""
        if completion == 100:
            return "✅", "green"
        elif completion > 0:
            return "⚡", "yellow"
        elif status == "blocked":
            return "🚫", "red"
        else:
            return "⏳", "gray"
    
    def _get_component_status_icon(self, status: str) -> tuple[str, str]:
        """Get status icon and color for component."""
        if status == "implemented":
            return "●", "green"
        elif status == "drift":
            return "⚠️", "yellow"
        elif status == "ghost":
            return "○", "gray"
        elif status == "extra":
            return "➕", "blue"
        else:
            return "○", "gray"
    
    @on(Tree.NodeSelected)
    def on_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle node selection - can be used to update Inspector."""
        node_data = event.node.data
        if node_data:
            # Emit message for Inspector to handle
            self.post_message(ComponentSelected(node_data))


class ComponentSelected(Message):
    """Message sent when a component is selected in the hierarchy."""
    
    def __init__(self, data: Dict[str, Any]):
        super().__init__()
        self.data = data
