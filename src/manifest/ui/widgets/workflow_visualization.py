"""
Workflow Visualization Widget.

Displays workflow execution as a visual graph showing:
- Stage dependencies and flow
- Current execution status
- Progress indicators
- Conditional branches
"""
from typing import Dict, Any, Optional, List, Set, Tuple
from textual.widgets import Static
from textual.containers import Vertical, VerticalScroll
from manifest.core.logger import get_logger
from manifest.agents.workflow_definition import WorkflowDefinition, StageDefinition, StageCondition

logger = get_logger(__name__)


class WorkflowVisualization(Static):
    """Visual representation of workflow execution.

    Shows workflow stages as a graph with dependencies, current status,
    and progress indicators. Uses ASCII art for terminal display.
    """

    def __init__(self, *args, **kwargs):
        """Initialize workflow visualization."""
        super().__init__(*args, **kwargs)
        self.workflow_definition: Optional[WorkflowDefinition] = None
        self.workflow_state: Dict[str, Any] = {}
        self.task_id: Optional[str] = None

    def load_workflow(
        self,
        workflow_definition: Optional[WorkflowDefinition],
        workflow_state: Dict[str, Any],
        task_id: Optional[str] = None
    ):
        """Load workflow definition and state.

        Args:
            workflow_definition: Workflow definition (optional, uses default if None).
            workflow_state: Current workflow execution state.
            task_id: Optional task ID for context.
        """
        self.workflow_definition = workflow_definition
        self.workflow_state = workflow_state
        self.task_id = task_id
        self.refresh()

    def render(self) -> str:
        """Render workflow visualization as ASCII graph."""
        if not self.workflow_definition:
            return "[dim]No workflow definition loaded[/]"

        stages = self.workflow_definition.stages
        if not stages:
            return "[dim]No stages in workflow[/]"

        # Get execution levels (stages that can run in parallel)
        execution_levels = self.workflow_definition.get_execution_order()

        # Build graph representation
        lines = []

        # Header
        if self.task_id:
            lines.append(f"[bold cyan]Workflow: {self.workflow_definition.name} (Task: {self.task_id})[/]")
        else:
            lines.append(f"[bold cyan]Workflow: {self.workflow_definition.name}[/]")
        lines.append("")

        # Calculate progress
        completed_stages = self.workflow_state.get("completed_stages", set())
        failed_stages = self.workflow_state.get("failed_stages", set())
        total_stages = len(stages)
        completed_count = len(completed_stages)
        progress_pct = (completed_count / total_stages * 100) if total_stages > 0 else 0

        lines.append(f"[bold]Progress: {progress_pct:.0f}% ({completed_count}/{total_stages} stages)[/]")
        lines.append("")

        # Render graph level by level
        for level_idx, level_stages in enumerate(execution_levels):
            # Render stages in this level
            stage_nodes = []
            for stage_name in level_stages:
                stage_def = self.workflow_definition.get_stage(stage_name)
                if not stage_def:
                    continue

                node = self._render_stage_node(stage_def, stage_name)
                stage_nodes.append(node)

            # Join parallel stages
            if len(stage_nodes) > 1:
                # Multiple stages in parallel
                node_lines = self._join_parallel_nodes(stage_nodes)
            else:
                # Single stage
                node_lines = stage_nodes[0] if stage_nodes else []

            lines.extend(node_lines)

            # Add connector to next level
            if level_idx < len(execution_levels) - 1:
                next_level = execution_levels[level_idx + 1]
                connector = self._render_connector(level_stages, next_level)
                lines.extend(connector)
                lines.append("")

        # Add legend
        lines.append("")
        lines.append("[dim]Legend:[/]")
        lines.append("  [green]✅[/] Completed  [yellow]⚡[/] In Progress  [red]❌[/] Failed  [dim]⏳[/] Pending")

        # Add conditional branches info
        conditional_stages = [
            s for s in stages
            if s.condition in [StageCondition.ON_SUCCESS, StageCondition.ON_FAILURE, StageCondition.CONDITIONAL]
        ]
        if conditional_stages:
            lines.append("")
            lines.append("[dim]Conditional Branches:[/]")
            for stage in conditional_stages:
                condition_desc = {
                    StageCondition.ON_SUCCESS: "runs on success",
                    StageCondition.ON_FAILURE: "runs on failure",
                    StageCondition.CONDITIONAL: "runs conditionally"
                }.get(stage.condition, "")
                lines.append(f"  [dim]{stage.name}[/]: {condition_desc}")

        return "\n".join(lines)

    def _render_stage_node(self, stage_def: StageDefinition, stage_name: str) -> List[str]:
        """Render a single stage node.

        Args:
            stage_def: Stage definition.
            stage_name: Stage name.

        Returns:
            List of lines representing the node.
        """
        # Get status
        stages = self.workflow_state.get("stages", {})
        stage_data = stages.get(stage_name, {})
        status = stage_data.get("status", "pending")

        # Status icon and color
        status_config = {
            "completed": ("✅", "green", "[green]"),
            "in_progress": ("⚡", "yellow", "[yellow]"),
            "failed": ("❌", "red", "[red]"),
            "pending": ("⏳", "dim", "[dim]"),
            "approved": ("✅", "green", "[green]"),
            "rejected": ("❌", "red", "[red]")
        }
        icon, color, color_tag = status_config.get(status, ("○", "dim", "[dim]"))

        # Stage name with agent type
        agent_type = stage_def.agent_type
        # Remove color tags for width calculation
        display_name_plain = f"{icon} {stage_name}"
        if agent_type != stage_name:
            display_name_plain += f" ({agent_type})"
        display_name = f"{color_tag}{icon} {stage_name}[/]"
        if agent_type != stage_name:
            display_name += f" [dim]({agent_type})[/]"

        # Build node box
        lines = []
        width = max(len(display_name_plain) + 4, 20)

        # Top border
        lines.append(f"┌{'─' * (width - 2)}┐")

        # Content line (need to calculate without markup)
        padding = (width - len(display_name_plain) - 2) // 2
        content = f"│{' ' * padding}{display_name}{' ' * (width - len(display_name_plain) - padding - 2)}│"
        lines.append(content)

        # Status line
        status_display = f"Status: {color_tag}{status}[/]"
        status_line = f"│  {status_display}"
        # Calculate padding without markup
        status_plain = f"Status: {status}"
        status_padding = width - len(status_line) - 1
        if status_padding > 0:
            status_line += " " * status_padding
        status_line += "│"
        lines.append(status_line)

        # Additional info
        if status == "in_progress":
            # Show progress if available
            progress_info = stage_data.get("progress")
            if progress_info:
                progress_plain = f"Progress: {progress_info}"
                progress_line = f"│  Progress: {progress_info}"
                progress_padding = width - len(progress_plain) - 3
                if progress_padding > 0:
                    progress_line += " " * progress_padding
                progress_line += "│"
                lines.append(progress_line)

        # Bottom border
        lines.append(f"└{'─' * (width - 2)}┘")

        return lines

    def _join_parallel_nodes(self, nodes: List[List[str]]) -> List[str]:
        """Join multiple parallel stage nodes horizontally.

        Args:
            nodes: List of node line lists.

        Returns:
            Combined lines showing parallel nodes.
        """
        if not nodes:
            return []

        if len(nodes) == 1:
            return nodes[0]

        # Find max height
        max_height = max(len(node) for node in nodes)

        # Pad all nodes to same height
        padded_nodes = []
        for node in nodes:
            padded = node.copy()
            node_width = len(node[0]) if node else 20
            while len(padded) < max_height:
                # Pad with spaces matching the width of the node
                padded.append(" " * node_width)
            padded_nodes.append(padded)

        # Join horizontally with separator
        result = []
        for i in range(max_height):
            line_parts = [padded_nodes[j][i] for j in range(len(padded_nodes))]
            # Add separator between parallel nodes
            joined = "  →  ".join(line_parts)
            result.append(joined)

        return result

    def _render_connector(self, from_stages: List[str], to_stages: List[str]) -> List[str]:
        """Render connector between levels.

        Args:
            from_stages: Stages in the previous level.
            to_stages: Stages in the next level.

        Returns:
            Lines representing the connector.
        """
        lines = []

        if len(from_stages) == 1 and len(to_stages) == 1:
            # Simple single-to-single connection
            lines.append("    │")
            lines.append("    ↓")
        elif len(from_stages) == 1 and len(to_stages) > 1:
            # Single-to-multiple: fan out
            lines.append("    │")
            lines.append("    ├─" + "─" * max(0, (len(to_stages) - 1) * 3) + "─┐")
            for i in range(len(to_stages) - 1):
                indent = " " * (i * 3)
                lines.append(f"    │ {indent}├─→")
            lines.append("    └─" + "─" * max(0, (len(to_stages) - 1) * 3) + "─┘")
        elif len(from_stages) > 1 and len(to_stages) == 1:
            # Multiple-to-single: fan in
            connector_line = "    " + "│  " * (len(from_stages) - 1) + "│"
            lines.append(connector_line)
            arrow_line = "    " + "├─→" * (len(from_stages) - 1) + "└─→"
            lines.append(arrow_line)
            bottom_line = "    " + "└─┘" * (len(from_stages) - 1) + "  │"
            lines.append(bottom_line)
            lines.append("    " + " " * (len(from_stages) - 1) * 3 + " ↓")
        else:
            # Multiple-to-multiple: complex connection
            max_count = max(len(from_stages), len(to_stages))
            lines.append("    " + "│  " * max_count)
            lines.append("    " + "↓  " * max_count)

        return lines

    def _render_conditional_branch(
        self,
        from_stage: str,
        to_stages: List[Tuple[str, str]]  # (stage_name, condition)
    ) -> List[str]:
        """Render conditional branch (e.g., test → debug or self_review).

        Args:
            from_stage: Source stage name.
            to_stages: List of (target_stage, condition_label) tuples.

        Returns:
            Lines representing the conditional branch.
        """
        lines = []

        if len(to_stages) == 1:
            # Simple connection
            lines.append("    │")
            lines.append("    ↓")
        else:
            # Branch with conditions
            lines.append("    │")
            # Find success and failure branches
            success_stage = next((s for s in to_stages if s[1] == "success"), None)
            failure_stage = next((s for s in to_stages if s[1] == "failure"), None)

            if success_stage and failure_stage:
                lines.append(f"    ├─[green][success]─→[/] {success_stage[0]}")
                lines.append("    │")
                lines.append(f"    └─[red][failure]─→[/] {failure_stage[0]}")
            else:
                # Generic branch
                for i, (stage_name, condition) in enumerate(to_stages):
                    if i == 0:
                        lines.append(f"    ├─[{condition}]─→ {stage_name}")
                    else:
                        lines.append(f"    └─[{condition}]─→ {stage_name}")

        return lines
