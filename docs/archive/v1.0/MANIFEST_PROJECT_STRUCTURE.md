# Manifest 프로젝트 구조 (Bottom-Up Blueprint)

**생성일**: 2026-01-24
**출처**: `.manifest/blueprint_code.json` (코드에서 추출)

**통계**: 29개 컴포넌트, 28개 내부 관계

---

## Zone: CLIENT (11 components)

### RequirementMap [class]

- **ID**: `comp-manifest.ui.widgets-RequirementMap`
- **File**: `src/manifest/ui/widgets.py:12`
- **Module**: `manifest.ui.widgets`

- **Methods** (3):
  - `__init__()`
  - `render()`
  - `update_data()`

- **Outgoing Contracts** (3):
  - → `GateController` (call) (`Approved`) @ `src/manifest/ui/widgets.py`
  - → `GateController` (call) (`Rejected`) @ `src/manifest/ui/widgets.py`
  - → `GateController` (call) (`FeedbackRequested`) @ `src/manifest/ui/widgets.py`

---

### ArchitectureGraph [class]

- **ID**: `comp-manifest.ui.widgets-ArchitectureGraph`
- **File**: `src/manifest/ui/widgets.py:57`
- **Module**: `manifest.ui.widgets`

- **Methods** (3):
  - `__init__()`
  - `render()`
  - `update_data()`

---

### FeatureTree [class]

- **ID**: `comp-manifest.ui.widgets-FeatureTree`
- **File**: `src/manifest/ui/widgets.py:103`
- **Module**: `manifest.ui.widgets`

- **Methods** (2):
  - `__init__()`
  - `load_features()`

---

### TaskTree [class]

- **ID**: `comp-manifest.ui.widgets-TaskTree`
- **File**: `src/manifest/ui/widgets.py:144`
- **Module**: `manifest.ui.widgets`

- **Methods** (3):
  - `__init__()`
  - `load_tasks()`
  - `get_selected_task()`

---

### GateController [class]

- **ID**: `comp-manifest.ui.widgets-GateController`
- **File**: `src/manifest/ui/widgets.py:199`
- **Module**: `manifest.ui.widgets`

- **Methods** (5):
  - `__init__()`
  - `compose()`
  - `on_approve()`
  - `on_reject()`
  - `on_feedback()`

- **Incoming Contracts** (3):
  - ← `RequirementMap` (call)
  - ← `RequirementMap` (call)
  - ← `RequirementMap` (call)

---

### Approved [class]

- **ID**: `comp-manifest.ui.widgets-Approved`
- **File**: `src/manifest/ui/widgets.py:230`
- **Module**: `manifest.ui.widgets`

- **Methods** (1):
  - `__init__()`

---

### Rejected [class]

- **ID**: `comp-manifest.ui.widgets-Rejected`
- **File**: `src/manifest/ui/widgets.py:237`
- **Module**: `manifest.ui.widgets`

- **Methods** (1):
  - `__init__()`

---

### FeedbackRequested [class]

- **ID**: `comp-manifest.ui.widgets-FeedbackRequested`
- **File**: `src/manifest/ui/widgets.py:244`
- **Module**: `manifest.ui.widgets`

- **Methods** (1):
  - `__init__()`

---

### ManifestApp [class]

- **ID**: `comp-manifest.ui.app-ManifestApp`
- **File**: `src/manifest/ui/app.py:33`
- **Module**: `manifest.ui.app`

- **Methods** (5):
  - `__init__()`
  - `compose()`
  - `action_toggle_inspector()`
  - `action_show_history()`
  - `action_show_project()`

- **Attributes** (2):
  - `CSS`
  - `BINDINGS`

- **Outgoing Contracts** (1):
  - → `ManifestApp` (call) (`ManifestApp`) @ `src/manifest/ui/app.py`

- **Incoming Contracts** (1):
  - ← `ManifestApp` (call)

---

### BootstrapApp [class]

- **ID**: `comp-manifest.ui.bootstrap_ui-BootstrapApp`
- **File**: `src/manifest/ui/bootstrap_ui.py:12`
- **Module**: `manifest.ui.bootstrap_ui`

- **Methods** (4):
  - `__init__()`
  - `compose()`
  - `on_mount()`
  - `on_skip()`

- **Attributes** (2):
  - `CSS`
  - `BINDINGS`

- **Outgoing Contracts** (1):
  - → `BootstrapApp` (call) (`BootstrapApp`) @ `src/manifest/ui/bootstrap_ui.py`

- **Incoming Contracts** (1):
  - ← `BootstrapApp` (call)

---

### run_bootstrap [function]

- **ID**: `comp-manifest.ui.bootstrap_ui-run_bootstrap`
- **File**: `src/manifest/ui/bootstrap_ui.py:142`
- **Module**: `manifest.ui.bootstrap_ui`

---

## Zone: SERVER (4 components)

### StateManager [class]

- **ID**: `comp-manifest.core.state_manager-StateManager`
- **File**: `src/manifest/core/state_manager.py:12`
- **Module**: `manifest.core.state_manager`

- **Methods** (16):
  - `__init__()`
  - `_load_state()`
  - `_default_state()`
  - `get_state()`
  - `get_mission_tree()`
  - `get_task_checklist()`
  - `get_chat_history()`
  - `get_last_action()`
  - `set_mission_tree()`
  - `set_task_checklist()`
  - `add_chat_message()`
  - `set_last_action()`
  - `save_state_sync()`
  - `get_next_action_prompt()`
  - `clear_state()`
  - `get_state_version()`

---

### ConfigManager [class]

- **ID**: `comp-manifest.core.config-ConfigManager`
- **File**: `src/manifest/core/config.py:14`
- **Module**: `manifest.core.config`

- **Methods** (10):
  - `__init__()`
  - `_load_or_create_key()`
  - `get_api_keys()`
  - `save_api_keys()`
  - `has_all_keys()`
  - `_load_agent_config()`
  - `_default_agent_config()`
  - `get_agent_model_config()`
  - `set_agent_model_config()`
  - `get_default_model_for_agent()`

- **Outgoing Contracts** (1):
  - → `ConfigManager` (call) (`ConfigManager`) @ `src/manifest/core/config.py`

- **Incoming Contracts** (1):
  - ← `ConfigManager` (call)

---

### get_config_manager [function]

- **ID**: `comp-manifest.core.config-get_config_manager`
- **File**: `src/manifest/core/config.py:273`
- **Module**: `manifest.core.config`

---

### OMOCBridge [class]

- **ID**: `comp-manifest.bridge.omoc_bridge-OMOCBridge`
- **File**: `src/manifest/bridge/omoc_bridge.py:13`
- **Module**: `manifest.bridge.omoc_bridge`

- **Methods** (2):
  - `__init__()`
  - `is_omoc_available()`

---

## Zone: DATA (14 components)

### TaskScoper [class]

- **ID**: `comp-manifest.agents.task_scoper-TaskScoper`
- **File**: `src/manifest/agents/task_scoper.py:10`
- **Module**: `manifest.agents.task_scoper`

- **Methods** (9):
  - `__init__()`
  - `_load_data()`
  - `get_task_context()`
  - `_get_task_components()`
  - `_get_task_files()`
  - `_get_task_requirements()`
  - `_get_allowed_modifications()`
  - `validate_task_scope()`
  - `get_task_scope_summary()`

---

### ContextProvider [class]

- **ID**: `comp-manifest.agents.context_provider-ContextProvider`
- **File**: `src/manifest/agents/context_provider.py:15`
- **Module**: `manifest.agents.context_provider`

- **Methods** (8):
  - `__init__()`
  - `get_orchestrator_context()`
  - `get_worker_context()`
  - `_load_tier_0()`
  - `_load_tier_1()`
  - `_load_tier_2_scoped()`
  - `_load_tier_3_scoped()`
  - `get_context_summary()`

---

### AgentCoordinator [class]

- **ID**: `comp-manifest.agents.agent_coordinator-AgentCoordinator`
- **File**: `src/manifest/agents/agent_coordinator.py:13`
- **Module**: `manifest.agents.agent_coordinator`

- **Methods** (3):
  - `__init__()`
  - `get_active_agents()`
  - `get_agent_channel()`

---

### Component [class]

- **ID**: `comp-manifest.audit.code_extractor-Component`
- **File**: `src/manifest/audit/code_extractor.py:14`
- **Module**: `manifest.audit.code_extractor`

- **Outgoing Contracts** (8):
  - → `Component` (call) (`Component`) @ `src/manifest/audit/code_extractor.py`
  - → `Contract` (call) (`Contract`) @ `src/manifest/audit/code_extractor.py`
  - → `Component` (call) (`Component`) @ `src/manifest/audit/code_extractor.py`
  - → `Contract` (call) (`Contract`) @ `src/manifest/audit/code_extractor.py`
  - → `Contract` (call) (`Contract`) @ `src/manifest/audit/code_extractor.py`
  - → `Contract` (call) (`Contract`) @ `src/manifest/audit/code_extractor.py`
  - → `Contract` (call) (`Contract`) @ `src/manifest/audit/code_extractor.py`
  - → `Contract` (call) (`Contract`) @ `src/manifest/audit/code_extractor.py`

- **Incoming Contracts** (2):
  - ← `Component` (call)
  - ← `Component` (call)

---

### Contract [class]

- **ID**: `comp-manifest.audit.code_extractor-Contract`
- **File**: `src/manifest/audit/code_extractor.py:27`
- **Module**: `manifest.audit.code_extractor`

- **Incoming Contracts** (6):
  - ← `Component` (call)
  - ← `Component` (call)
  - ← `Component` (call)
  - ← `Component` (call)
  - ← `Component` (call)
  - ... +1 more

---

### CodeExtractor [class]

- **ID**: `comp-manifest.audit.code_extractor-CodeExtractor`
- **File**: `src/manifest/audit/code_extractor.py:36`
- **Module**: `manifest.audit.code_extractor`

- **Methods** (10):
  - `__init__()`
  - `extract_project_structure()`
  - `_find_python_files()`
  - `_extract_file_structure()`
  - `_identify_entities()`
  - `_infer_relationships()`
  - `_find_containing_entity()`
  - `_find_file_entity()`
  - `_generate_blueprint()`
  - `save_blueprint()`

---

### ConflictReport [class]

- **ID**: `comp-manifest.audit.blueprint_synchronizer-ConflictReport`
- **File**: `src/manifest/audit/blueprint_synchronizer.py:16`
- **Module**: `manifest.audit.blueprint_synchronizer`

- **Methods** (1):
  - `to_dict()`

- **Outgoing Contracts** (2):
  - → `ConflictReport` (call) (`ConflictReport`) @ `src/manifest/audit/blueprint_synchronizer.py`
  - → `ConflictReport` (call) (`ConflictReport`) @ `src/manifest/audit/blueprint_synchronizer.py`

- **Incoming Contracts** (2):
  - ← `ConflictReport` (call)
  - ← `ConflictReport` (call)

---

### BlueprintSynchronizer [class]

- **ID**: `comp-manifest.audit.blueprint_synchronizer-BlueprintSynchronizer`
- **File**: `src/manifest/audit/blueprint_synchronizer.py:43`
- **Module**: `manifest.audit.blueprint_synchronizer`

- **Methods** (10):
  - `__init__()`
  - `detect_mismatch()`
  - `create_conflict_issue()`
  - `save_conflict_report()`
  - `load_conflict_report()`
  - `resend_to_worker_squad()`
  - `request_planner_review()`
  - `request_user_approval()`
  - `update_conflict_status()`
  - `sync_blueprints()`

---

### Severity [class]

- **ID**: `comp-manifest.audit.drift_auditor-Severity`
- **File**: `src/manifest/audit/drift_auditor.py:14`
- **Module**: `manifest.audit.drift_auditor`

- **Attributes** (3):
  - `ERROR`
  - `WARNING`
  - `INFO`

- **Outgoing Contracts** (4):
  - → `DriftConflict` (call) (`DriftConflict`) @ `src/manifest/audit/drift_auditor.py`
  - → `DriftConflict` (call) (`DriftConflict`) @ `src/manifest/audit/drift_auditor.py`
  - → `DriftConflict` (call) (`DriftConflict`) @ `src/manifest/audit/drift_auditor.py`
  - → `DriftConflict` (call) (`DriftConflict`) @ `src/manifest/audit/drift_auditor.py`

---

### DriftConflict [class]

- **ID**: `comp-manifest.audit.drift_auditor-DriftConflict`
- **File**: `src/manifest/audit/drift_auditor.py:21`
- **Module**: `manifest.audit.drift_auditor`

- **Methods** (2):
  - `__init__()`
  - `to_dict()`

- **Incoming Contracts** (4):
  - ← `Severity` (call)
  - ← `Severity` (call)
  - ← `Severity` (call)
  - ← `Severity` (call)

---

### DriftAuditor [class]

- **ID**: `comp-manifest.audit.drift_auditor-DriftAuditor`
- **File**: `src/manifest/audit/drift_auditor.py:40`
- **Module**: `manifest.audit.drift_auditor`

- **Methods** (10):
  - `__init__()`
  - `_load_blueprint()`
  - `reload_blueprint()`
  - `parse_python_file()`
  - `find_python_files()`
  - `compare_with_blueprint()`
  - `audit_project()`
  - `get_conflicts_by_severity()`
  - `get_conflicts_for_node()`
  - `generate_bottom_up_blueprint()`

---

### ConflictType [class]

- **ID**: `comp-manifest.audit.blueprint_comparator-ConflictType`
- **File**: `src/manifest/audit/blueprint_comparator.py:12`
- **Module**: `manifest.audit.blueprint_comparator`

- **Attributes** (6):
  - `MISSING_COMPONENT`
  - `EXTRA_COMPONENT`
  - `METHOD_MISMATCH`
  - `CONTRACT_MISMATCH`
  - `ZONE_MISMATCH`
  - `ATTRIBUTE_MISMATCH`

- **Outgoing Contracts** (8):
  - → `BlueprintConflict` (call) (`BlueprintConflict`) @ `src/manifest/audit/blueprint_comparator.py`
  - → `BlueprintConflict` (call) (`BlueprintConflict`) @ `src/manifest/audit/blueprint_comparator.py`
  - → `BlueprintConflict` (call) (`BlueprintConflict`) @ `src/manifest/audit/blueprint_comparator.py`
  - → `BlueprintConflict` (call) (`BlueprintConflict`) @ `src/manifest/audit/blueprint_comparator.py`
  - → `BlueprintConflict` (call) (`BlueprintConflict`) @ `src/manifest/audit/blueprint_comparator.py`
  - → `BlueprintConflict` (call) (`BlueprintConflict`) @ `src/manifest/audit/blueprint_comparator.py`
  - → `BlueprintConflict` (call) (`BlueprintConflict`) @ `src/manifest/audit/blueprint_comparator.py`
  - → `BlueprintConflict` (call) (`BlueprintConflict`) @ `src/manifest/audit/blueprint_comparator.py`

---

### BlueprintConflict [class]

- **ID**: `comp-manifest.audit.blueprint_comparator-BlueprintConflict`
- **File**: `src/manifest/audit/blueprint_comparator.py:23`
- **Module**: `manifest.audit.blueprint_comparator`

- **Methods** (1):
  - `to_dict()`

- **Incoming Contracts** (8):
  - ← `ConflictType` (call)
  - ← `ConflictType` (call)
  - ← `ConflictType` (call)
  - ← `ConflictType` (call)
  - ← `ConflictType` (call)
  - ... +3 more

---

### BlueprintComparator [class]

- **ID**: `comp-manifest.audit.blueprint_comparator-BlueprintComparator`
- **File**: `src/manifest/audit/blueprint_comparator.py:46`
- **Module**: `manifest.audit.blueprint_comparator`

- **Methods** (9):
  - `compare_blueprints()`
  - `compare_components()`
  - `_compare_methods()`
  - `_compare_attributes()`
  - `compare_contracts()`
  - `_normalize_contracts()`
  - `compare_zones()`
  - `get_conflicts_by_severity()`
  - `get_conflicts_by_type()`

---

## Contracts Summary

총 **28개** 내부 관계

### CALL (28개)

- `RequirementMap` → `GateController` [Approved] @ `src/manifest/ui/widgets.py`
- `RequirementMap` → `GateController` [Rejected] @ `src/manifest/ui/widgets.py`
- `RequirementMap` → `GateController` [FeedbackRequested] @ `src/manifest/ui/widgets.py`
- `ManifestApp` → `ManifestApp` [ManifestApp] @ `src/manifest/ui/app.py`
- `BootstrapApp` → `BootstrapApp` [BootstrapApp] @ `src/manifest/ui/bootstrap_ui.py`
- `ConfigManager` → `ConfigManager` [ConfigManager] @ `src/manifest/core/config.py`
- `Component` → `Component` [Component] @ `src/manifest/audit/code_extractor.py`
- `Component` → `Contract` [Contract] @ `src/manifest/audit/code_extractor.py`
- `Component` → `Component` [Component] @ `src/manifest/audit/code_extractor.py`
- `Component` → `Contract` [Contract] @ `src/manifest/audit/code_extractor.py`
- ... +18 more
