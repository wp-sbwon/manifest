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
        self.tasks: List[Dict[str, Any]] = []  # Tasks for task-file association
        self.app_ref: Optional[Any] = None  # Reference to app for accessing state
        self.highlighted_files: set = set()  # Set of file paths currently highlighted
        self.highlighted_components: set = set()  # Set of component IDs currently highlighted

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

        # Add highlight marker if component is highlighted
        highlight_marker = " ⭐" if comp_id in self.highlighted_components else ""

        # Component label with type
        comp_type_display = f"[{comp_type}]" if comp_type != "unknown" else ""
        comp_label = f"{status_icon} {comp_name} {comp_type_display}{metadata_str}{highlight_marker}"
        comp_node = parent_node.add(comp_label, expand=False)
        comp_node.data = {
            "type": "component",
            "id": comp_id,
            "status": status,
            "file": comp_file,
            "line": comp_line,
            "component_type": comp_type
        }

        # Build component lookup for contract target names
        components_by_id = {}
        for c in self.blueprint_data.get("components", []):
            cid = c.get("id", "")
            if cid:
                components_by_id[cid] = c

        # Add file path as child node
        if comp_file:
            # Find related tasks for this file
            related_tasks = self._find_tasks_for_file(comp_file)
            task_icons = []
            if related_tasks:
                for task in related_tasks[:3]:  # Show max 3 tasks
                    task_id = task.get("id", "")
                    task_status = task.get("status", "unknown")
                    status_icon = {
                        "done": "✅",
                        "in_progress": "⚡",
                        "pending": "⏳",
                        "blocked": "🚫"
                    }.get(task_status, "○")
                    task_icons.append(f"{status_icon} {task_id[:8]}")

            task_suffix = " " + " ".join(task_icons) if task_icons else ""
            if len(related_tasks) > 3:
                task_suffix += f" (+{len(related_tasks) - 3})"

            # Add highlight marker if file is highlighted
            highlight_marker = " ⭐" if comp_file in self.highlighted_files else ""
            file_label = f"📁 {comp_file}:{comp_line}{task_suffix}{highlight_marker}"
            file_node = comp_node.add(file_label, expand=False)
            file_node.data = {
                "type": "file",
                "file": comp_file,
                "line": comp_line,
                "related_tasks": related_tasks
            }

        # Add module path if available
        module_path = comp.get("module_path", "")
        if module_path:
            module_label = f"📦 {module_path}"
            module_node = comp_node.add(module_label, expand=False)
            module_node.data = {
                "type": "module",
                "module_path": module_path
            }

        # Add methods if available (expandable)
        methods = comp.get("methods", [])
        if methods:
            methods_count = len(methods)
            methods_label = f"Methods ({methods_count}) [▶]"
            methods_node = comp_node.add(methods_label, expand=False)
            methods_node.data = {
                "type": "methods_header",
                "methods": methods,
                "expanded": False
            }

            # Add individual method nodes (initially collapsed)
            for method_name in methods:
                method_node = methods_node.add(f"  • {method_name}", expand=False)
                method_node.data = {
                    "type": "method",
                    "name": method_name,
                    "component_id": comp_id
                }

        # Add attributes if available (expandable)
        attributes = comp.get("attributes", [])
        if attributes:
            attributes_count = len(attributes)
            attributes_label = f"Attributes ({attributes_count}) [▶]"
            attributes_node = comp_node.add(attributes_label, expand=False)
            attributes_node.data = {
                "type": "attributes_header",
                "attributes": attributes,
                "expanded": False
            }

            # Add individual attribute nodes (initially collapsed)
            for attr_name in attributes:
                attr_node = attributes_node.add(f"  • {attr_name}", expand=False)
                attr_node.data = {
                    "type": "attribute",
                    "name": attr_name,
                    "component_id": comp_id
                }

        # Add contracts if available (expandable)
        contracts = self.blueprint_data.get("contracts", [])
        outgoing_contracts = [c for c in contracts if c.get("from") == comp_id]
        incoming_contracts = [c for c in contracts if c.get("to") == comp_id]

        if outgoing_contracts or incoming_contracts:
            contracts_count = len(outgoing_contracts) + len(incoming_contracts)
            contracts_label = f"Contracts ({contracts_count}) [▶]"
            contracts_node = comp_node.add(contracts_label, expand=False)
            contracts_node.data = {
                "type": "contracts_header",
                "outgoing": outgoing_contracts,
                "incoming": incoming_contracts,
                "expanded": False
            }

            # Add outgoing contracts
            if outgoing_contracts:
                outgoing_label = f"  → Outgoing ({len(outgoing_contracts)})"
                outgoing_node = contracts_node.add(outgoing_label, expand=False)
                outgoing_node.data = {
                    "type": "contracts_outgoing_header",
                    "contracts": outgoing_contracts,
                    "expanded": False
                }

                for contract in outgoing_contracts:
                    to_id = contract.get("to", "")
                    contract_type = contract.get("type", "unknown")
                    symbols = contract.get("symbols", [])

                    # Try to get target component name
                    target_name = to_id.split("-")[-1] if "-" in to_id else to_id
                    target_comp = components_by_id.get(to_id)
                    if target_comp:
                        target_name = target_comp.get("name", target_name)

                    contract_label = f"    → {target_name} ({contract_type})"
                    if symbols:
                        symbols_str = ", ".join(symbols[:2])
                        if len(symbols) > 2:
                            symbols_str += f" (+{len(symbols) - 2})"
                        contract_label += f" [{symbols_str}]"

                    contract_node = outgoing_node.add(contract_label, expand=False)
                    contract_node.data = {
                        "type": "contract",
                        "contract": contract,
                        "direction": "outgoing",
                        "component_id": comp_id
                    }

            # Add incoming contracts
            if incoming_contracts:
                incoming_label = f"  ← Incoming ({len(incoming_contracts)})"
                incoming_node = contracts_node.add(incoming_label, expand=False)
                incoming_node.data = {
                    "type": "contracts_incoming_header",
                    "contracts": incoming_contracts,
                    "expanded": False
                }

                for contract in incoming_contracts:
                    from_id = contract.get("from", "")
                    contract_type = contract.get("type", "unknown")
                    symbols = contract.get("symbols", [])

                    # Try to get source component name
                    source_name = from_id.split("-")[-1] if "-" in from_id else from_id
                    source_comp = components_by_id.get(from_id)
                    if source_comp:
                        source_name = source_comp.get("name", source_name)

                    contract_label = f"    ← {source_name} ({contract_type})"
                    if symbols:
                        symbols_str = ", ".join(symbols[:2])
                        if len(symbols) > 2:
                            symbols_str += f" (+{len(symbols) - 2})"
                        contract_label += f" [{symbols_str}]"

                    contract_node = incoming_node.add(contract_label, expand=False)
                    contract_node.data = {
                        "type": "contract",
                        "contract": contract,
                        "direction": "incoming",
                        "component_id": comp_id
                    }

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

    def _find_tasks_for_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Find tasks associated with a file.

        Args:
            file_path: Path to the file.

        Returns:
            List of tasks that have modified or are working on this file.
        """
        if not self.tasks and self.app_ref:
            # Load tasks from state if not already loaded
            try:
                self.tasks = self.app_ref.state_manager.get_task_checklist()
            except Exception:
                pass

        associated = []
        for task in self.tasks:
            # Check if task has modified this file
            worker_squad = task.get("worker_squad", {})
            stages = worker_squad.get("stages", {})
            for stage_data in stages.values():
                output = stage_data.get("output", "")
                tool_execution = stage_data.get("tool_execution", {})
                modified_files = tool_execution.get("modified_files", [])

                if file_path in modified_files:
                    associated.append(task)
                    break

            # Also check task scope
            scope = task.get("scope", {})
            allowed_files = scope.get("files", [])
            if file_path in allowed_files:
                if task not in associated:
                    associated.append(task)

        return associated

    def set_app(self, app: Any):
        """Set reference to app for accessing state.

        Args:
            app: ManifestApp instance.
        """
        self.app_ref = app
        if app:
            try:
                self.tasks = app.state_manager.get_task_checklist()
            except Exception:
                pass

    @on(Tree.NodeSelected)
    def on_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle node selection - can be used to update Inspector or toggle expansion."""
        node_data = event.node.data
        if not node_data:
            return

        node_type = node_data.get("type")

        # Handle methods/attributes header expansion
        if node_type == "methods_header":
            methods = node_data.get("methods", [])
            is_expanded = node_data.get("expanded", False)

            # Toggle expansion
            if is_expanded:
                # Collapse: remove individual method nodes
                event.node.collapse()
                # Update label
                event.node.label = f"Methods ({len(methods)}) [▶]"
                node_data["expanded"] = False
            else:
                # Expand: individual method nodes are already added in _add_component_node
                event.node.expand()
                # Update label
                event.node.label = f"Methods ({len(methods)}) [▼]"
                node_data["expanded"] = True

        elif node_type == "attributes_header":
            attributes = node_data.get("attributes", [])
            is_expanded = node_data.get("expanded", False)

            # Toggle expansion
            if is_expanded:
                # Collapse
                event.node.collapse()
                event.node.label = f"Attributes ({len(attributes)}) [▶]"
                node_data["expanded"] = False
            else:
                # Expand
                event.node.expand()
                event.node.label = f"Attributes ({len(attributes)}) [▼]"
                node_data["expanded"] = True

        elif node_type == "contracts_header":
            outgoing = node_data.get("outgoing", [])
            incoming = node_data.get("incoming", [])
            is_expanded = node_data.get("expanded", False)

            # Toggle expansion
            if is_expanded:
                event.node.collapse()
                total = len(outgoing) + len(incoming)
                event.node.label = f"Contracts ({total}) [▶]"
                node_data["expanded"] = False
            else:
                event.node.expand()
                total = len(outgoing) + len(incoming)
                event.node.label = f"Contracts ({total}) [▼]"
                node_data["expanded"] = True

        elif node_type in ("contracts_outgoing_header", "contracts_incoming_header"):
            contracts = node_data.get("contracts", [])
            is_expanded = node_data.get("expanded", False)

            # Toggle expansion
            if is_expanded:
                event.node.collapse()
                direction = "Outgoing" if node_type == "contracts_outgoing_header" else "Incoming"
                event.node.label = f"  {'→' if direction == 'Outgoing' else '←'} {direction} ({len(contracts)})"
                node_data["expanded"] = False
            else:
                event.node.expand()
                direction = "Outgoing" if node_type == "contracts_outgoing_header" else "Incoming"
                event.node.label = f"  {'→' if direction == 'Outgoing' else '←'} {direction} ({len(contracts)})"
                node_data["expanded"] = True

        # Emit message for Inspector to handle (for component selection)
        if node_type == "component":
            self.post_message(ComponentSelected(node_data))

    def highlight_task_files_and_components(self, task: Dict[str, Any]) -> None:
        """Highlight files and components related to a task.

        Args:
            task: Task dictionary with scope information.
        """
        # Clear previous highlights
        self.highlighted_files.clear()
        self.highlighted_components.clear()

        # Get task scope
        scope = task.get("scope", {})
        task_files = scope.get("files", [])
        task_components = scope.get("components", [])

        # Also check modified files from worker squad stages
        worker_squad = task.get("worker_squad", {})
        stages = worker_squad.get("stages", {})
        for stage_data in stages.values():
            tool_execution = stage_data.get("tool_execution", {})
            modified_files = tool_execution.get("modified_files", [])
            task_files.extend(modified_files)

        # Also check task-level tool_execution
        tool_execution = task.get("tool_execution", {})
        task_summary = tool_execution.get("last_summary", {})
        modified_files = task_summary.get("modified_files", [])
        task_files.extend(modified_files)

        # Store highlighted items
        self.highlighted_files.update(task_files)
        self.highlighted_components.update(task_components)

        # Rebuild tree to show highlights
        self._build_tree()

    def clear_highlights(self) -> None:
        """Clear all highlights."""
        self.highlighted_files.clear()
        self.highlighted_components.clear()
        self._build_tree()


class ComponentSelected(Message):
    """Message sent when a component is selected in the hierarchy."""

    def __init__(self, data: Dict[str, Any]):
        super().__init__()
        self.data = data
