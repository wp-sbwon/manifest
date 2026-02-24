"""
Blueprint Comparator - Compares top-down (design) and bottom-up (code) blueprints.
Detects conflicts and mismatches between intended design and actual implementation.

Terminology (aligned with Manifest View): design = Design Plan; code = Actual Code; conflicts = Deviation.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from manifest.audit.code.deviation_auditor import Severity
from manifest.audit.entity_schema import PROJECT_ROOT_ID, contracts_from_entities, entity_display_name


class ConflictType(Enum):
    MISSING_ENTITY = "missing_entity"
    EXTRA_ENTITY = "extra_entity"
    NAME_MISMATCH = "name_mismatch"
    METHOD_MISMATCH = "method_mismatch"
    CONTRACT_MISMATCH = "contract_mismatch"
    ZONE_MISMATCH = "zone_mismatch"
    ATTRIBUTE_MISMATCH = "attribute_mismatch"


@dataclass
class BlueprintConflict:
    """Represents a conflict between top-down and bottom-up blueprints."""
    severity: Severity
    type: ConflictType
    message: str
    top_down_node: Optional[Dict[str, Any]] = None
    bottom_up_node: Optional[Dict[str, Any]] = None
    file_path: Optional[str] = None
    node_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "severity": self.severity.value,
            "type": self.type.value,
            "message": self.message,
            "top_down_node": self.top_down_node,
            "bottom_up_node": self.bottom_up_node,
            "file_path": self.file_path,
            "node_id": self.node_id
        }


class BlueprintComparator:
    """Compares top-down (design) and bottom-up (code) blueprints."""

    def compare_blueprints(
        self,
        top_down: Dict[str, Any],
        bottom_up: Dict[str, Any]
    ) -> List[BlueprintConflict]:
        """Compare two blueprints; return all conflicts."""
        conflicts = []

        entity_conflicts = self.compare_entities(
            top_down.get("entities", []),
            bottom_up.get("entities", [])
        )
        conflicts.extend(entity_conflicts)

        td_contracts = contracts_from_entities(top_down.get("entities", []))
        bu_contracts = contracts_from_entities(bottom_up.get("entities", []))
        contract_conflicts = self.compare_contracts(td_contracts, bu_contracts)
        conflicts.extend(contract_conflicts)

        return conflicts

    def compare_entities(
        self,
        top_down_entities: List[Dict[str, Any]],
        bottom_up_entities: List[Dict[str, Any]]
    ) -> List[BlueprintConflict]:
        """Compare entities by id (design and code share same schema and ids)."""
        conflicts = []
        td_list = [e for e in (top_down_entities or []) if (e.get("id") or "") != PROJECT_ROOT_ID]
        bu_list = [e for e in (bottom_up_entities or []) if (e.get("id") or "") != PROJECT_ROOT_ID]

        td_by_id: Dict[str, Dict[str, Any]] = {e.get("id"): e for e in td_list if e.get("id")}
        bu_by_id: Dict[str, Dict[str, Any]] = {e.get("id"): e for e in bu_list if e.get("id")}

        for eid, td_ent in td_by_id.items():
            bu_ent = bu_by_id.get(eid)
            name = entity_display_name(td_ent) or eid
            if bu_ent is None:
                file_path = (td_ent.get("reality") or {}).get("symbol") or td_ent.get("file")
                conflicts.append(BlueprintConflict(
                    severity=Severity.IN_PROGRESS,
                    type=ConflictType.MISSING_ENTITY,
                    message=f"Entity '{name}' specified in design but not found in code",
                    top_down_node=td_ent,
                    node_id=eid,
                    file_path=file_path
                ))
            else:
                conflicts.extend(self._compare_methods(td_ent, bu_ent))
                conflicts.extend(self._compare_attributes(td_ent, bu_ent))
                conflicts.extend(self._compare_structural_fields(td_ent, bu_ent))
                conflicts.extend(self._compare_metadata_fields(td_ent, bu_ent))

        for eid, bu_ent in bu_by_id.items():
            if eid not in td_by_id:
                name = entity_display_name(bu_ent) or eid
                file_path = (bu_ent.get("reality") or {}).get("symbol") or bu_ent.get("file")
                conflicts.append(BlueprintConflict(
                    severity=Severity.WARNING,
                    type=ConflictType.EXTRA_ENTITY,
                    message=f"Entity '{name}' exists in code but not in design",
                    bottom_up_node=bu_ent,
                    node_id=eid,
                    file_path=file_path
                ))

        return conflicts

    def _compare_methods(
        self,
        top_down: Dict[str, Any],
        bottom_up: Dict[str, Any]
    ) -> List[BlueprintConflict]:
        """Compare methods between two nodes."""
        conflicts = []
        td_methods = set((top_down.get("reality") or {}).get("methods", top_down.get("methods", [])))
        bu_methods = set((bottom_up.get("reality") or {}).get("methods", bottom_up.get("methods", [])))

        td_name = entity_display_name(top_down)
        bu_name = entity_display_name(bottom_up)
        bu_file = (bottom_up.get("reality") or {}).get("symbol", bottom_up.get("file"))

        missing = td_methods - bu_methods
        for method in missing:
            conflicts.append(BlueprintConflict(
                severity=Severity.IN_PROGRESS,
                type=ConflictType.METHOD_MISMATCH,
                message=f"Method '{method}' in entity '{td_name}' specified in design but not in code (in progress)",
                top_down_node=top_down,
                bottom_up_node=bottom_up,
                node_id=top_down.get("id"),
                file_path=bu_file
            ))

        extra = bu_methods - td_methods
        for method in extra:
            conflicts.append(BlueprintConflict(
                severity=Severity.INFO,
                type=ConflictType.METHOD_MISMATCH,
                message=f"Method '{method}' in entity '{bu_name}' exists in code but not in design",
                top_down_node=top_down,
                bottom_up_node=bottom_up,
                node_id=bottom_up.get("id"),
                file_path=bu_file
            ))

        return conflicts

    def _compare_attributes(
        self,
        top_down: Dict[str, Any],
        bottom_up: Dict[str, Any]
    ) -> List[BlueprintConflict]:
        """Compare attributes between two nodes."""
        conflicts = []
        td_attrs = set((top_down.get("reality") or {}).get("attributes", top_down.get("attributes", [])))
        bu_attrs = set((bottom_up.get("reality") or {}).get("attributes", bottom_up.get("attributes", [])))

        td_name = entity_display_name(top_down)
        bu_file = (bottom_up.get("reality") or {}).get("symbol", bottom_up.get("file"))

        missing = td_attrs - bu_attrs
        for attr in missing:
            conflicts.append(BlueprintConflict(
                severity=Severity.IN_PROGRESS,
                type=ConflictType.ATTRIBUTE_MISMATCH,
                message=f"Attribute '{attr}' in entity '{td_name}' specified in design but not in code (in progress)",
                top_down_node=top_down,
                bottom_up_node=bottom_up,
                node_id=top_down.get("id"),
                file_path=bu_file
            ))

        return conflicts

    def compare_contracts(
        self,
        top_down_contracts: List[Dict[str, Any]],
        bottom_up_contracts: List[Dict[str, Any]]
    ) -> List[BlueprintConflict]:
        """Compare contracts (relationships) between blueprints."""
        conflicts = []

        # Build lookup sets for comparison
        td_contracts = self._normalize_contracts(top_down_contracts)
        bu_contracts = self._normalize_contracts(bottom_up_contracts)

        # Missing contracts
        missing = td_contracts - bu_contracts
        for contract_key in missing:
            conflicts.append(BlueprintConflict(
                severity=Severity.WARNING,
                type=ConflictType.CONTRACT_MISMATCH,
                message=f"Contract '{contract_key}' specified in design but not found in code",
                node_id=contract_key
            ))

        # Extra contracts (informational)
        extra = bu_contracts - td_contracts
        for contract_key in extra:
            conflicts.append(BlueprintConflict(
                severity=Severity.INFO,
                type=ConflictType.CONTRACT_MISMATCH,
                message=f"Contract '{contract_key}' exists in code but not in design",
                node_id=contract_key
            ))

        return conflicts

    def _normalize_contracts(self, contracts: List[Dict[str, Any]]) -> set:
        """Normalize contracts to comparable keys."""
        normalized = set()
        for contract in contracts:
            from_id = contract.get("from", "")
            to_id = contract.get("to", "")
            contract_type = contract.get("type", "")
            key = f"{from_id}->{to_id}:{contract_type}"
            normalized.add(key)
        return normalized

    def get_conflicts_by_severity(
        self,
        conflicts: List[BlueprintConflict]
    ) -> Dict[str, List[BlueprintConflict]]:
        """Group conflicts by severity (error, warning, info, in_progress)."""
        grouped = {
            "error": [],
            "warning": [],
            "info": [],
            "in_progress": [],
        }

        for conflict in conflicts:
            key = conflict.severity.value
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(conflict)

        return grouped

    def get_conflicts_by_type(
        self,
        conflicts: List[BlueprintConflict]
    ) -> Dict[str, List[BlueprintConflict]]:
        """Group conflicts by type."""
        grouped = {}

        for conflict in conflicts:
            conflict_type = conflict.type.value
            if conflict_type not in grouped:
                grouped[conflict_type] = []
            grouped[conflict_type].append(conflict)

        return grouped

    def _compare_structural_fields(
        self,
        top_down: Dict[str, Any],
        bottom_up: Dict[str, Any]
    ) -> List[BlueprintConflict]:
        """Compare structural fields (id, name, type, file) between nodes."""
        conflicts = []
        td_name = entity_display_name(top_down)
        bu_name = entity_display_name(bottom_up)
        td_file = (top_down.get("reality") or {}).get("symbol", top_down.get("file", ""))
        bu_file = (bottom_up.get("reality") or {}).get("symbol", bottom_up.get("file", ""))

        if td_name != bu_name:
            conflicts.append(BlueprintConflict(
                severity=Severity.ERROR,
                type=ConflictType.NAME_MISMATCH,
                message=f"Entity name mismatch: design has '{td_name}', code has '{bu_name}'",
                top_down_node=top_down,
                bottom_up_node=bottom_up,
                node_id=top_down.get("id"),
                file_path=bu_file
            ))

        td_type = (top_down.get("reality") or {}).get("type", top_down.get("type"))
        bu_type = (bottom_up.get("reality") or {}).get("type", bottom_up.get("type"))
        if td_type and bu_type and td_type != bu_type:
            conflicts.append(BlueprintConflict(
                severity=Severity.WARNING,
                type=ConflictType.METHOD_MISMATCH,
                message=f"Entity type mismatch: design has '{td_type}', code has '{bu_type}'",
                top_down_node=top_down,
                bottom_up_node=bottom_up,
                node_id=top_down.get("id"),
                file_path=bu_file
            ))

        if td_file and bu_file and td_file != bu_file:
            if not (td_file.endswith(bu_file) or bu_file.endswith(td_file)):
                conflicts.append(BlueprintConflict(
                    severity=Severity.INFO,
                    type=ConflictType.METHOD_MISMATCH,
                    message=f"Entity file path differs: design has '{td_file}', code has '{bu_file}'",
                    top_down_node=top_down,
                    bottom_up_node=bottom_up,
                    node_id=top_down.get("id"),
                    file_path=bu_file
                ))

        return conflicts

    def _entity_get(self, ent: Dict[str, Any], key: str) -> Any:
        """Get field: reality.key or top-level key."""
        return (ent.get("reality") or {}).get(key, ent.get(key))

    def _compare_metadata_fields(
        self,
        top_down: Dict[str, Any],
        bottom_up: Dict[str, Any]
    ) -> List[BlueprintConflict]:
        """Compare metadata fields (algorithm, design_pattern, complexity)."""
        conflicts = []

        td_algorithm = self._entity_get(top_down, "algorithm")
        bu_algorithm = self._entity_get(bottom_up, "algorithm")
        if td_algorithm and bu_algorithm:
            # Allow case-insensitive comparison and partial matches
            if td_algorithm.lower() != bu_algorithm.lower():
                conflicts.append(BlueprintConflict(
                    severity=Severity.INFO,  # INFO level - LLM inference differences are acceptable
                    type=ConflictType.METHOD_MISMATCH,
                    message=f"Algorithm differs: design has '{td_algorithm}', code has '{bu_algorithm}' (LLM inference difference acceptable)",
                    top_down_node=top_down,
                    bottom_up_node=bottom_up,
                    node_id=top_down.get("id"),
                    file_path=bottom_up.get("file")
                ))
        elif td_algorithm and not bu_algorithm:
            # Design has algorithm but code doesn't - informational
            conflicts.append(BlueprintConflict(
                severity=Severity.INFO,
                type=ConflictType.METHOD_MISMATCH,
                message=f"Algorithm '{td_algorithm}' specified in design but not detected in code",
                top_down_node=top_down,
                bottom_up_node=bottom_up,
                node_id=top_down.get("id"),
                file_path=bottom_up.get("file")
            ))

        td_pattern = self._entity_get(top_down, "design_pattern")
        bu_pattern = self._entity_get(bottom_up, "design_pattern")
        if td_pattern and bu_pattern:
            if td_pattern.lower() != bu_pattern.lower():
                conflicts.append(BlueprintConflict(
                    severity=Severity.INFO,
                    type=ConflictType.METHOD_MISMATCH,
                    message=f"Design pattern differs: design has '{td_pattern}', code has '{bu_pattern}' (LLM inference difference acceptable)",
                    top_down_node=top_down,
                    bottom_up_node=bottom_up,
                    node_id=top_down.get("id"),
                    file_path=bottom_up.get("file")
                ))
        elif td_pattern and not bu_pattern:
            conflicts.append(BlueprintConflict(
                severity=Severity.INFO,
                type=ConflictType.METHOD_MISMATCH,
                message=f"Design pattern '{td_pattern}' specified in design but not detected in code",
                top_down_node=top_down,
                bottom_up_node=bottom_up,
                node_id=top_down.get("id"),
                file_path=bottom_up.get("file")
            ))

        td_complexity = self._entity_get(top_down, "complexity")
        bu_complexity = self._entity_get(bottom_up, "complexity")
        if td_complexity and bu_complexity:
            if td_complexity.lower() != bu_complexity.lower():
                conflicts.append(BlueprintConflict(
                    severity=Severity.INFO,
                    type=ConflictType.METHOD_MISMATCH,
                    message=f"Complexity differs: design has '{td_complexity}', code has '{bu_complexity}' (LLM inference difference acceptable)",
                    top_down_node=top_down,
                    bottom_up_node=bottom_up,
                    node_id=top_down.get("id"),
                    file_path=bottom_up.get("file")
                ))
        elif td_complexity and not bu_complexity:
            conflicts.append(BlueprintConflict(
                severity=Severity.INFO,
                type=ConflictType.METHOD_MISMATCH,
                message=f"Complexity '{td_complexity}' specified in design but not detected in code",
                top_down_node=top_down,
                bottom_up_node=bottom_up,
                node_id=top_down.get("id"),
                file_path=bottom_up.get("file")
            ))

        return conflicts
