====================================================================================================
MANIFEST 프로젝트 구조 시각화 (ASCII)
====================================================================================================

총 29개 컴포넌트, 28개 내부 관계
출처: blueprint_code.json (코드에서 추출)

┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ZONE: CLIENT                                                                                     │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ RequirementMap                           [class] Methods:3   Out:3   In:0                             │
│ 📁 src/manifest/ui/widgets.py                                                                 │
│ 📦 manifest.ui.widgets                                                                        │
│ Methods: __init__(), render(), update_data()                                                        │
│   → GateController (call)                                                                    │
│   → GateController (call)                                                                    │
│   ... +1 more                                                                                 │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ ArchitectureGraph                        [class] Methods:3   Out:0   In:0                             │
│ 📁 src/manifest/ui/widgets.py                                                                 │
│ 📦 manifest.ui.widgets                                                                        │
│ Methods: __init__(), render(), update_data()                                                        │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ FeatureTree                              [class] Methods:2   Out:0   In:0                             │
│ 📁 src/manifest/ui/widgets.py                                                                 │
│ 📦 manifest.ui.widgets                                                                        │
│ Methods: __init__(), load_features()                                                                │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ TaskTree                                 [class] Methods:3   Out:0   In:0                             │
│ 📁 src/manifest/ui/widgets.py                                                                 │
│ 📦 manifest.ui.widgets                                                                        │
│ Methods: __init__(), load_tasks(), get_selected_task()                                              │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ GateController                           [class] Methods:5   Out:0   In:3                             │
│ 📁 src/manifest/ui/widgets.py                                                                 │
│ 📦 manifest.ui.widgets                                                                        │
│ Methods: __init__(), compose(), on_approve() (+2 more)                                              │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ Approved                                 [class] Methods:1   Out:0   In:0                             │
│ 📁 src/manifest/ui/widgets.py                                                                 │
│ 📦 manifest.ui.widgets                                                                        │
│ Methods: __init__()                                                                                 │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ Rejected                                 [class] Methods:1   Out:0   In:0                             │
│ 📁 src/manifest/ui/widgets.py                                                                 │
│ 📦 manifest.ui.widgets                                                                        │
│ Methods: __init__()                                                                                 │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ FeedbackRequested                        [class] Methods:1   Out:0   In:0                             │
│ 📁 src/manifest/ui/widgets.py                                                                 │
│ 📦 manifest.ui.widgets                                                                        │
│ Methods: __init__()                                                                                 │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ ManifestApp                              [class] Methods:5   Out:1   In:1                             │
│ 📁 src/manifest/ui/app.py                                                                     │
│ 📦 manifest.ui.app                                                                            │
│ Methods: __init__(), compose(), action_toggle_inspector() (+2 more)                                 │
│   → ManifestApp (call)                                                                       │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ BootstrapApp                             [class] Methods:4   Out:1   In:1                             │
│ 📁 src/manifest/ui/bootstrap_ui.py                                                            │
│ 📦 manifest.ui.bootstrap_ui                                                                   │
│ Methods: __init__(), compose(), on_mount() (+1 more)                                                │
│   → BootstrapApp (call)                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ run_bootstrap                            [function] Methods:0   Out:0   In:0                             │
│ 📁 src/manifest/ui/bootstrap_ui.py                                                            │
│ 📦 manifest.ui.bootstrap_ui                                                                   │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ZONE: SERVER                                                                                     │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ StateManager                             [class] Methods:16  Out:0   In:0                             │
│ 📁 src/manifest/core/state_manager.py                                                         │
│ 📦 manifest.core.state_manager                                                                │
│ Methods: __init__(), _load_state(), _default_state() (+13 more)                                     │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ ConfigManager                            [class] Methods:10  Out:1   In:1                             │
│ 📁 src/manifest/core/config.py                                                                │
│ 📦 manifest.core.config                                                                       │
│ Methods: __init__(), _load_or_create_key(), get_api_keys() (+7 more)                                │
│   → ConfigManager (call)                                                                     │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ get_config_manager                       [function] Methods:0   Out:0   In:0                             │
│ 📁 src/manifest/core/config.py                                                                │
│ 📦 manifest.core.config                                                                       │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ OMOCBridge                               [class] Methods:2   Out:0   In:0                             │
│ 📁 src/manifest/bridge/omoc_bridge.py                                                         │
│ 📦 manifest.bridge.omoc_bridge                                                                │
│ Methods: __init__(), is_omoc_available()                                                            │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ ZONE: DATA                                                                                       │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ TaskScoper                               [class] Methods:9   Out:0   In:0                             │
│ 📁 src/manifest/agents/task_scoper.py                                                         │
│ 📦 manifest.agents.task_scoper                                                                │
│ Methods: __init__(), _load_data(), get_task_context() (+6 more)                                     │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ ContextProvider                          [class] Methods:8   Out:0   In:0                             │
│ 📁 src/manifest/agents/context_provider.py                                                    │
│ 📦 manifest.agents.context_provider                                                           │
│ Methods: __init__(), get_orchestrator_context(), get_worker_context() (+5 more)                     │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ AgentCoordinator                         [class] Methods:3   Out:0   In:0                             │
│ 📁 src/manifest/agents/agent_coordinator.py                                                   │
│ 📦 manifest.agents.agent_coordinator                                                          │
│ Methods: __init__(), get_active_agents(), get_agent_channel()                                       │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ Component                                [class] Methods:0   Out:8   In:2                             │
│ 📁 src/manifest/audit/code_extractor.py                                                       │
│ 📦 manifest.audit.code_extractor                                                              │
│   → Component (call)                                                                         │
│   → Contract (call)                                                                          │
│   ... +6 more                                                                                 │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ Contract                                 [class] Methods:0   Out:0   In:6                             │
│ 📁 src/manifest/audit/code_extractor.py                                                       │
│ 📦 manifest.audit.code_extractor                                                              │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ CodeExtractor                            [class] Methods:10  Out:0   In:0                             │
│ 📁 src/manifest/audit/code_extractor.py                                                       │
│ 📦 manifest.audit.code_extractor                                                              │
│ Methods: __init__(), extract_project_structure(), _find_python_files() (+7 more)                    │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ ConflictReport                           [class] Methods:1   Out:2   In:2                             │
│ 📁 src/manifest/audit/blueprint_synchronizer.py                                               │
│ 📦 manifest.audit.blueprint_synchronizer                                                      │
│ Methods: to_dict()                                                                                  │
│   → ConflictReport (call)                                                                    │
│   → ConflictReport (call)                                                                    │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ BlueprintSynchronizer                    [class] Methods:10  Out:0   In:0                             │
│ 📁 src/manifest/audit/blueprint_synchronizer.py                                               │
│ 📦 manifest.audit.blueprint_synchronizer                                                      │
│ Methods: __init__(), detect_mismatch(), create_conflict_issue() (+7 more)                           │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ Severity                                 [class] Methods:0   Out:4   In:0                             │
│ 📁 src/manifest/audit/drift_auditor.py                                                        │
│ 📦 manifest.audit.drift_auditor                                                               │
│   → DriftConflict (call)                                                                     │
│   → DriftConflict (call)                                                                     │
│   ... +2 more                                                                                 │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ DriftConflict                            [class] Methods:2   Out:0   In:4                             │
│ 📁 src/manifest/audit/drift_auditor.py                                                        │
│ 📦 manifest.audit.drift_auditor                                                               │
│ Methods: __init__(), to_dict()                                                                      │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ DriftAuditor                             [class] Methods:10  Out:0   In:0                             │
│ 📁 src/manifest/audit/drift_auditor.py                                                        │
│ 📦 manifest.audit.drift_auditor                                                               │
│ Methods: __init__(), _load_blueprint(), reload_blueprint() (+7 more)                                │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ ConflictType                             [class] Methods:0   Out:8   In:0                             │
│ 📁 src/manifest/audit/blueprint_comparator.py                                                 │
│ 📦 manifest.audit.blueprint_comparator                                                        │
│   → BlueprintConflict (call)                                                                 │
│   → BlueprintConflict (call)                                                                 │
│   ... +6 more                                                                                 │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ BlueprintConflict                        [class] Methods:1   Out:0   In:8                             │
│ 📁 src/manifest/audit/blueprint_comparator.py                                                 │
│ 📦 manifest.audit.blueprint_comparator                                                        │
│ Methods: to_dict()                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ BlueprintComparator                      [class] Methods:9   Out:0   In:0                             │
│ 📁 src/manifest/audit/blueprint_comparator.py                                                 │
│ 📦 manifest.audit.blueprint_comparator                                                        │
│ Methods: compare_blueprints(), compare_components(), _compare_methods() (+6 more)                   │
└──────────────────────────────────────────────────────────────────────────────────────────────┘

====================================================================================================
COMPONENT DEPENDENCY GRAPH (주요 관계)
====================================================================================================

                    ┌─────────────────────┐
                    │   ManifestApp      │
                    │   [UI Client]      │
                    └──────────┬──────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
    ┌────▼────┐          ┌────▼────┐          ┌────▼────┐
    │State    │          │Config   │          │Agent    │
    │Manager  │          │Manager  │          │Coordinator│
    │[Server] │          │[Server] │          │[Data]   │
    └─────────┘          └─────────┘          └────┬────┘
                                                    │
         ┌─────────────────────────────────────────┘
         │
    ┌────▼─────────────────────────────────────────┐
    │  Data Zone Components                        │
    │                                               │
    │  ┌──────────────┐  ┌──────────────┐         │
    │  │Context       │  │TaskScoper    │         │
    │  │Provider      │  │              │         │
    │  └──────────────┘  └──────────────┘         │
    │                                               │
    │  ┌──────────────┐  ┌──────────────┐         │
    │  │DriftAuditor  │  │Blueprint     │         │
    │  │              │  │Synchronizer  │         │
    │  └──────┬───────┘  └──────┬─────────┘         │
    │         │                 │                   │
    │         └────────┬─────────┘                   │
    │                  │                            │
    │         ┌────────▼─────────┐                   │
    │         │BlueprintComparator│                 │
    │         └───────────────────┘                 │
    │                                               │
    │  ┌──────────────┐                             │
    │  │CodeExtractor │                             │
    │  │              │                             │
    │  │  → Component │                             │
    │  │  → Contract  │                             │
    │  └──────────────┘                             │
    └───────────────────────────────────────────────┘

====================================================================================================
UI WIDGETS (Client Zone)
====================================================================================================

┌────────────────────────────────────────────────────────────────────────────┐
│ UI Widgets                                                                  │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐            │
│  │RequirementMap│      │Architecture │      │FeatureTree   │            │
│  │              │      │Graph         │      │              │            │
│  └──────┬───────┘      └──────────────┘      └──────────────┘            │
│         │                                                                  │
│         │ (calls)                                                          │
│         │                                                                  │
│         ▼                                                                  │
│  ┌──────────────┐                                                          │
│  │GateController│                                                          │
│  │              │                                                          │
│  └──────┬───────┘                                                          │
│         │                                                                  │
│         ├──→ Approved                                                      │
│         ├──→ Rejected                                                      │
│         └──→ FeedbackRequested                                             │
│                                                                            │
│  ┌──────────────┐                                                          │
│  │TaskTree      │                                                          │
│  └──────────────┘                                                          │
└────────────────────────────────────────────────────────────────────────────┘

====================================================================================================
AUDIT SYSTEM (Data Zone)
====================================================================================================

┌────────────────────────────────────────────────────────────────────────────┐
│ Audit & Blueprint Management                                              │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  CodeExtractor                                                            │
│    ├──→ Component [dataclass]                                             │
│    └──→ Contract [dataclass]                                               │
│                                                                            │
│  DriftAuditor                                                              │
│    ├──→ Severity [Enum]                                                   │
│    │     ├──→ DriftConflict [ERROR]                                       │
│    │     ├──→ DriftConflict [WARNING]                                     │
│    │     └──→ DriftConflict [INFO]                                         │
│    └──→ CodeExtractor (uses)                                              │
│                                                                            │
│  BlueprintSynchronizer                                                    │
│    └──→ ConflictReport                                                    │
│                                                                            │
│  BlueprintComparator                                                      │
│    ├──→ ConflictType [Enum]                                               │
│    │     └──→ BlueprintConflict (8 types)                                │
│    └──→ BlueprintSynchronizer (used by)                                   │
└────────────────────────────────────────────────────────────────────────────┘

====================================================================================================
MODULE ORGANIZATION
====================================================================================================

manifest/
├── ui/                    [CLIENT]
│   ├── app.py             → ManifestApp
│   ├── widgets.py         → RequirementMap, ArchitectureGraph, FeatureTree, TaskTree, GateController
│   └── bootstrap_ui.py    → BootstrapApp, run_bootstrap
│
├── core/                  [SERVER]
│   ├── state_manager.py   → StateManager
│   └── config.py          → ConfigManager, get_config_manager
│
├── bridge/                [SERVER]
│   └── omoc_bridge.py     → OMOCBridge
│
├── agents/                [DATA]
│   ├── task_scoper.py     → TaskScoper
│   ├── context_provider.py → ContextProvider
│   └── agent_coordinator.py → AgentCoordinator
│
└── audit/                 [DATA]
    ├── code_extractor.py  → Component, Contract, CodeExtractor
    ├── drift_auditor.py   → Severity, DriftConflict, DriftAuditor
    ├── blueprint_synchronizer.py → ConflictReport, BlueprintSynchronizer
    └── blueprint_comparator.py → ConflictType, BlueprintConflict, BlueprintComparator
