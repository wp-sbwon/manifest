"""
Blueprint management and status.

This package contains modules for managing blueprints:
- BlueprintLoader: Centralized blueprint loading
- BlueprintMetadata: Metadata management for blueprints
- BlueprintComparator: Compares top-down and bottom-up blueprints
- blueprint_status: calculate_implementation_status
"""
from .manifest_filenames import BLUEPRINT_DESIGN_FILE, BLUEPRINT_CODE_FILE, BLUEPRINT_VIEW_FILE
from .blueprint_loader import BlueprintLoader
from .blueprint_metadata import load_blueprint_with_metadata, save_blueprint_with_metadata
from .blueprint_comparator import BlueprintComparator, BlueprintConflict, ConflictType
from .blueprint_status import calculate_implementation_status
from .status_enums import ConflictWorkflowStatus, ImplementationStatus
from .view_schema import (
    build_view_schema,
    entity_has_any_deviates,
    load_view_schema,
    to_single_value,
    unwrap_list_field,
    write_view_schema,
)

__all__ = [
    "BLUEPRINT_DESIGN_FILE",
    "BLUEPRINT_CODE_FILE",
    "BLUEPRINT_VIEW_FILE",
    "BlueprintLoader",
    "load_blueprint_with_metadata",
    "save_blueprint_with_metadata",
    "BlueprintComparator",
    "BlueprintConflict",
    "ConflictType",
    "calculate_implementation_status",
    "ConflictWorkflowStatus",
    "ImplementationStatus",
    "build_view_schema",
    "entity_has_any_deviates",
    "load_view_schema",
    "to_single_value",
    "unwrap_list_field",
    "write_view_schema",
]
