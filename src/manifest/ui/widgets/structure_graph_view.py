"""
Structure Graph View - Graph-based visualization of Features and Components.
Shows Features as boxes/clusters with Components as nodes inside, and Contracts as edges.
"""
from textual.widgets import Static
from textual import on
from typing import Dict, Any, List, Optional, Set
from pathlib import Path


class StructureGraphView(Static):
    """Graph-based visualization showing Features and Components together."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.architecture_data: Dict[str, Any] = {}
        self.blueprint_data: Dict[str, Any] = {}
        self.status_info: Dict[str, Any] = {}
        self.component_statuses: Dict[str, str] = {}
        self.feature_completions: Dict[str, float] = {}
        self.filters: Dict[str, Any] = {
            "zone": "all",  # "all", "client", "server", "data"
            "status": "all"  # "all", "implemented", "ghost", "drift"
        }
    
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
            blueprint: Blueprint data (components, contracts)
            status_info: Status information from BlueprintSynchronizer
        """
        self.architecture_data = architecture
        self.blueprint_data = blueprint
        self.status_info = status_info or {}
        self.component_statuses = status_info.get("component_statuses", {}) if status_info else {}
        self.feature_completions = status_info.get("feature_completions", {}) if status_info else {}
        
        self.refresh()
    
    def set_filter(self, filter_type: str, value: str):
        """Set filter for graph display."""
        if filter_type in self.filters:
            self.filters[filter_type] = value
            self.refresh()
    
    def render(self) -> str:
        """Render the graph visualization."""
        if not self.architecture_data or not self.blueprint_data:
            return "No architecture or blueprint data available"
        
        features = self.architecture_data.get("features", [])
        components_by_id: Dict[str, Dict[str, Any]] = {}
        contracts = self.blueprint_data.get("contracts", [])
        
        # Build component lookup
        for comp in self.blueprint_data.get("components", []):
            comp_id = comp.get("id", "")
            if comp_id:
                components_by_id[comp_id] = comp
        
        # Build contract lookup for data flow
        contracts_by_from: Dict[str, List[Dict[str, Any]]] = {}
        for contract in contracts:
            from_id = contract.get("from", "")
            if from_id:
                if from_id not in contracts_by_from:
                    contracts_by_from[from_id] = []
                contracts_by_from[from_id].append(contract)
        
        lines = []
        
        # Render each feature as a box/cluster
        for feature in features:
            feature_id = feature.get("id", "")
            feature_name = feature.get("name", "Unknown Feature")
            completion = self.feature_completions.get(feature_id, feature.get("completion_percentage", 0))
            
            # Feature box header
            status_icon = "✅" if completion == 100 else "⚡" if completion > 0 else "⏳"
            lines.append(f"┌─────────────────────────────────────────────────────────────┐")
            lines.append(f"│ {status_icon} Feature: {feature_name} ({completion}%)")
            # Pad to box width
            padding = 59 - len(feature_name) - len(str(completion)) - 15
            lines[-1] += " " * max(0, padding) + "│"
            lines.append(f"│" + " " * 59 + "│")
            
            # Get components for this feature
            feature_components = feature.get("components", [])
            requirements = feature.get("requirements", [])
            
            # Collect all components from requirements
            all_comp_ids: Set[str] = set(feature_components)
            for req in requirements:
                all_comp_ids.update(req.get("components", []))
            
            # Filter components based on filters
            filtered_comp_ids = self._filter_components(list(all_comp_ids), components_by_id)
            
            if not filtered_comp_ids:
                lines.append(f"│  (No components to display)                              │")
            else:
                # Render components in a simple grid layout
                comp_nodes = []
                for comp_id in filtered_comp_ids:
                    comp = components_by_id.get(comp_id)
                    if comp:
                        comp_nodes.append((comp_id, comp))
                
                # Simple layout: show components in rows
                max_per_row = 2
                for i in range(0, len(comp_nodes), max_per_row):
                    row_comps = comp_nodes[i:i + max_per_row]
                    row_lines = []
                    
                    for comp_id, comp in row_comps:
                        comp_name = comp.get("name", "Unknown")
                        status = self.component_statuses.get(comp_id, comp.get("status", "pending"))
                        status_icon, _ = self._get_component_status_icon(status)
                        
                        # Metadata tags
                        metadata_tags = []
                        if comp.get("algorithm"):
                            metadata_tags.append(comp["algorithm"])
                        if comp.get("design_pattern"):
                            metadata_tags.append(comp["design_pattern"])
                        
                        metadata_str = f" [{'] ['.join(metadata_tags)}]" if metadata_tags else ""
                        
                        # Component box (simplified ASCII art)
                        comp_box = f"  ┌──────────────┐"
                        comp_label = f"  │{status_icon} {comp_name[:12]:<12}│"
                        if metadata_str:
                            comp_meta = f"  │{metadata_str[:15]:<15}│"
                        else:
                            comp_meta = f"  │              │"
                        comp_bottom = f"  └──────────────┘"
                        
                        row_lines.append([comp_box, comp_label, comp_meta, comp_bottom])
                    
                    # Combine row components
                    if len(row_lines) == 1:
                        for line in row_lines[0]:
                            lines.append(f"│{line}" + " " * (59 - len(line) - 1) + "│")
                    else:
                        # Two components side by side
                        for j in range(len(row_lines[0])):
                            combined = row_lines[0][j] + "    " + row_lines[1][j]
                            lines.append(f"│{combined}" + " " * (59 - len(combined) - 1) + "│")
                    
                    lines.append(f"│" + " " * 59 + "│")
                    
                    # Add contract arrows between components in this feature
                    if i < len(comp_nodes) - 1:
                        # Show contract if exists
                        comp1_id = comp_nodes[i][0]
                        if i + 1 < len(comp_nodes):
                            comp2_id = comp_nodes[i + 1][0]
                            # Check for contract
                            for contract in contracts_by_from.get(comp1_id, []):
                                if contract.get("to", "") == comp2_id:
                                    contract_type = contract.get("type", "")
                                    data_flow = contract.get("data_flow", {})
                                    if data_flow:
                                        flow_label = f"  → {contract_type}: {data_flow.get('input', '')} → {data_flow.get('output', '')}"
                                    else:
                                        flow_label = f"  → {contract_type}"
                                    lines.append(f"│{flow_label}" + " " * (59 - len(flow_label) - 1) + "│")
                                    break
            
            lines.append(f"└─────────────────────────────────────────────────────────────┘")
            lines.append("")
        
        # Add filter info
        filter_info = f"[Zones: {self.filters['zone'].upper()}] [Status: {self.filters['status'].upper()}]"
        lines.append(filter_info)
        
        return "\n".join(lines) if lines else "No features to display"
    
    def _filter_components(
        self,
        comp_ids: List[str],
        components_by_id: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """Filter components based on current filters."""
        filtered = []
        
        for comp_id in comp_ids:
            comp = components_by_id.get(comp_id)
            if not comp:
                continue
            
            # Zone filter
            if self.filters["zone"] != "all":
                comp_zone = comp.get("zone", "")
                if comp_zone != self.filters["zone"]:
                    continue
            
            # Status filter
            if self.filters["status"] != "all":
                comp_status = self.component_statuses.get(comp_id, comp.get("status", "pending"))
                if comp_status != self.filters["status"]:
                    continue
            
            filtered.append(comp_id)
        
        return filtered
    
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
