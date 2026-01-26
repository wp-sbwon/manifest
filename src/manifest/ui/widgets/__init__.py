"""
UI Widgets package.

This package contains custom Textual widgets for the Manifest UI.
"""

# Import legacy widgets from _legacy.py
from manifest.ui.widgets._legacy import (
    RequirementMap,
    ArchitectureGraph,
    FeatureTree,
    TaskTree,
    GateController,
    WorkerSquadProgress,
    TaskManagementWidget,
    SprintApprovalWidget,
    PermissionApprovalWidget,
)

# Import new widgets from submodules
from manifest.ui.widgets.structure_hierarchy_view import StructureHierarchyView, ComponentSelected
from manifest.ui.widgets.structure_graph_view import StructureGraphView, ComponentSelectedFromGraph
from manifest.ui.widgets.project_view import (
    ProjectView,
    TaskTreeView,
    SprintStatusView,
    HistoryView,
    TaskSelected,
    SprintSelected
)
from manifest.ui.widgets.agent_status_view import AgentStatusView, AgentStatusCard
from manifest.ui.widgets.agent_channels_view import AgentChannelsView, ChannelSelected
from manifest.ui.widgets.task_progress_view import TaskProgressView

__all__ = [
    # Legacy widgets
    "RequirementMap",
    "ArchitectureGraph",
    "FeatureTree",
    "TaskTree",
    "GateController",
    "WorkerSquadProgress",
    "TaskManagementWidget",
    "SprintApprovalWidget",
    "PermissionApprovalWidget",
    # New widgets
    "StructureHierarchyView",
    "ComponentSelected",
    "StructureGraphView",
    "ComponentSelectedFromGraph",
    "ProjectView",
    "TaskTreeView",
    "SprintStatusView",
    "HistoryView",
    "TaskSelected",
    "SprintSelected",
    "AgentStatusView",
    "AgentStatusCard",
    "AgentChannelsView",
    "ChannelSelected",
    "TaskProgressView",
]
