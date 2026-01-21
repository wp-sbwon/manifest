"""
Blueprint Comparator - Compares top-down (design) and bottom-up (code) blueprints.
Detects conflicts and mismatches between intended design and actual implementation.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from manifest.audit.drift_auditor import Severity


class ConflictType(Enum):
    """Types of blueprint conflicts."""
    MISSING_COMPONENT = "missing_component"
    EXTRA_COMPONENT = "extra_component"
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
    top_down_component: Optional[Dict[str, Any]] = None
    bottom_up_component: Optional[Dict[str, Any]] = None
    file_path: Optional[str] = None
    component_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "severity": self.severity.value,
            "type": self.type.value,
            "message": self.message,
            "top_down_component": self.top_down_component,
            "bottom_up_component": self.bottom_up_component,
            "file_path": self.file_path,
            "component_id": self.component_id
        }


class BlueprintComparator:
    """Compares top-down (design) and bottom-up (code) blueprints."""
    
    def compare_blueprints(
        self,
        top_down: Dict[str, Any],
        bottom_up: Dict[str, Any]
    ) -> List[BlueprintConflict]:
        """Compare two blueprints and return all conflicts."""
        conflicts = []
        
        # Compare components
        component_conflicts = self.compare_components(
            top_down.get("components", []),
            bottom_up.get("components", [])
        )
        conflicts.extend(component_conflicts)
        
        # Compare contracts
        contract_conflicts = self.compare_contracts(
            top_down.get("contracts", []),
            bottom_up.get("contracts", [])
        )
        conflicts.extend(contract_conflicts)
        
        # Compare zones
        zone_conflicts = self.compare_zones(
            top_down.get("zones", {}),
            bottom_up.get("zones", {})
        )
        conflicts.extend(zone_conflicts)
        
        return conflicts
    
    def compare_components(
        self,
        top_down_components: List[Dict[str, Any]],
        bottom_up_components: List[Dict[str, Any]]
    ) -> List[BlueprintConflict]:
        """Compare components between blueprints."""
        conflicts = []
        
        # Build lookup dictionaries
        top_down_by_name: Dict[str, Dict[str, Any]] = {}
        bottom_up_by_name: Dict[str, Dict[str, Any]] = {}
        
        for comp in top_down_components:
            name = comp.get("name")
            if name:
                top_down_by_name[name] = comp
        
        for comp in bottom_up_components:
            name = comp.get("name")
            if name:
                bottom_up_by_name[name] = comp
        
        # Check for missing components (in top-down but not in bottom-up)
        for name, td_comp in top_down_by_name.items():
            if name not in bottom_up_by_name:
                conflicts.append(BlueprintConflict(
                    severity=Severity.ERROR,
                    type=ConflictType.MISSING_COMPONENT,
                    message=f"Component '{name}' specified in design but not found in code",
                    top_down_component=td_comp,
                    component_id=td_comp.get("id"),
                    file_path=td_comp.get("file")
                ))
            else:
                # Component exists, check methods
                bu_comp = bottom_up_by_name[name]
                method_conflicts = self._compare_methods(td_comp, bu_comp)
                conflicts.extend(method_conflicts)
                
                # Check attributes
                attr_conflicts = self._compare_attributes(td_comp, bu_comp)
                conflicts.extend(attr_conflicts)
        
        # Check for extra components (in bottom-up but not in top-down)
        for name, bu_comp in bottom_up_by_name.items():
            if name not in top_down_by_name:
                conflicts.append(BlueprintConflict(
                    severity=Severity.WARNING,
                    type=ConflictType.EXTRA_COMPONENT,
                    message=f"Component '{name}' exists in code but not in design blueprint",
                    bottom_up_component=bu_comp,
                    component_id=bu_comp.get("id"),
                    file_path=bu_comp.get("file")
                ))
        
        return conflicts
    
    def _compare_methods(
        self,
        top_down: Dict[str, Any],
        bottom_up: Dict[str, Any]
    ) -> List[BlueprintConflict]:
        """Compare methods between two components."""
        conflicts = []
        
        td_methods = set(top_down.get("methods", []))
        bu_methods = set(bottom_up.get("methods", []))
        
        # Missing methods
        missing = td_methods - bu_methods
        for method in missing:
            conflicts.append(BlueprintConflict(
                severity=Severity.WARNING,
                type=ConflictType.METHOD_MISMATCH,
                message=f"Method '{method}' in component '{top_down.get('name')}' specified in design but not in code",
                top_down_component=top_down,
                bottom_up_component=bottom_up,
                component_id=top_down.get("id"),
                file_path=bottom_up.get("file")
            ))
        
        # Extra methods (informational)
        extra = bu_methods - td_methods
        for method in extra:
            conflicts.append(BlueprintConflict(
                severity=Severity.INFO,
                type=ConflictType.METHOD_MISMATCH,
                message=f"Method '{method}' in component '{bottom_up.get('name')}' exists in code but not in design",
                top_down_component=top_down,
                bottom_up_component=bottom_up,
                component_id=bottom_up.get("id"),
                file_path=bottom_up.get("file")
            ))
        
        return conflicts
    
    def _compare_attributes(
        self,
        top_down: Dict[str, Any],
        bottom_up: Dict[str, Any]
    ) -> List[BlueprintConflict]:
        """Compare attributes between two components."""
        conflicts = []
        
        td_attrs = set(top_down.get("attributes", []))
        bu_attrs = set(bottom_up.get("attributes", []))
        
        # Missing attributes
        missing = td_attrs - bu_attrs
        for attr in missing:
            conflicts.append(BlueprintConflict(
                severity=Severity.INFO,
                type=ConflictType.ATTRIBUTE_MISMATCH,
                message=f"Attribute '{attr}' in component '{top_down.get('name')}' specified in design but not in code",
                top_down_component=top_down,
                bottom_up_component=bottom_up,
                component_id=top_down.get("id"),
                file_path=bottom_up.get("file")
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
                component_id=contract_key
            ))
        
        # Extra contracts (informational)
        extra = bu_contracts - td_contracts
        for contract_key in extra:
            conflicts.append(BlueprintConflict(
                severity=Severity.INFO,
                type=ConflictType.CONTRACT_MISMATCH,
                message=f"Contract '{contract_key}' exists in code but not in design",
                component_id=contract_key
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
    
    def compare_zones(
        self,
        top_down_zones: Dict[str, List[str]],
        bottom_up_zones: Dict[str, List[str]]
    ) -> List[BlueprintConflict]:
        """Compare zone assignments between blueprints."""
        conflicts = []
        
        # Compare each zone
        for zone_name in ["client", "server", "data"]:
            td_components = set(top_down_zones.get(zone_name, []))
            bu_components = set(bottom_up_zones.get(zone_name, []))
            
            # Components in top-down but not in bottom-up for this zone
            missing = td_components - bu_components
            for comp_id in missing:
                conflicts.append(BlueprintConflict(
                    severity=Severity.INFO,
                    type=ConflictType.ZONE_MISMATCH,
                    message=f"Component '{comp_id}' assigned to '{zone_name}' zone in design but not in code",
                    component_id=comp_id
                ))
        
        return conflicts
    
    def get_conflicts_by_severity(
        self,
        conflicts: List[BlueprintConflict]
    ) -> Dict[str, List[BlueprintConflict]]:
        """Group conflicts by severity."""
        grouped = {
            "error": [],
            "warning": [],
            "info": []
        }
        
        for conflict in conflicts:
            grouped[conflict.severity.value].append(conflict)
        
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
