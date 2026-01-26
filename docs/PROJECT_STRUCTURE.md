# Manifest 프로젝트 구조

**최종 업데이트**: 2026-01-24
**출처**: `.manifest/blueprint_code.json` (코드에서 추출)

**통계**: 29개 컴포넌트, 28개 내부 관계

---

## 📊 개요

이 문서는 Manifest 프로젝트 자체의 구조를 Bottom-Up 방식으로 추출한 정보를 담고 있습니다. 코드에서 AST 파싱을 통해 자동으로 추출되었습니다.

### 데이터 파일 상태

- ✅ **blueprint_code.json**: 데이터 있음 (29개 컴포넌트)
- ❌ **blueprint.json**: 비어있음 (intended design 없음)
- ❌ **architecture.json**: 비어있음 (features 없음)
- ❌ **intent.json**: 비어있음 (features 없음)

### UI에서 보기

현재 UI는 `blueprint_code.json`을 fallback으로 사용하여 프로젝트 구조를 표시합니다. `/audit_drift` 명령을 실행하면 코드에서 최신 구조를 추출하여 업데이트할 수 있습니다.

---

## 🏗️ Zone별 컴포넌트

### Zone: CLIENT (11 components)

UI 및 클라이언트 측 컴포넌트들입니다.

#### UI Widgets
- **RequirementMap** - 요구사항 맵 표시
- **ArchitectureGraph** - 아키텍처 그래프 표시
- **FeatureTree** - Feature 트리 표시
- **TaskTree** - Task 트리 표시
- **GateController** - 승인/거부 컨트롤러

#### Applications
- **ManifestApp** - 메인 애플리케이션
- **BootstrapApp** - 부트스트랩 UI
- **run_bootstrap** - 부트스트랩 실행 함수

자세한 컴포넌트 정보는 [아카이브 문서](./archive/v1.0/MANIFEST_PROJECT_STRUCTURE.md)를 참조하세요.

### Zone: SERVER (4 components)

서버 측 핵심 관리 컴포넌트들입니다.

- **StateManager** - 상태 관리 (16개 메서드)
- **ConfigManager** - 설정 관리 (10개 메서드)
- **get_config_manager** - ConfigManager 팩토리 함수
- **OMOCBridge** - OMOC 브릿지

### Zone: DATA (14 components)

데이터 처리 및 Audit 관련 컴포넌트들입니다.

#### Agent System
- **TaskScoper** - Task 범위 관리 (9개 메서드)
- **ContextProvider** - 컨텍스트 제공 (8개 메서드)
- **AgentCoordinator** - Agent 조정 (3개 메서드)

#### Audit & Blueprint
- **CodeExtractor** - 코드 구조 추출 (10개 메서드)
- **Component** - 컴포넌트 데이터 클래스
- **Contract** - 관계 데이터 클래스
- **DriftAuditor** - Drift 감지 (10개 메서드)
- **Severity** - 심각도 Enum
- **DriftConflict** - Drift 충돌 데이터 클래스
- **BlueprintSynchronizer** - Blueprint 동기화 (10개 메서드)
- **ConflictReport** - 충돌 보고서
- **BlueprintComparator** - Blueprint 비교 (9개 메서드)
- **ConflictType** - 충돌 타입 Enum
- **BlueprintConflict** - Blueprint 충돌 데이터 클래스

---

## 🔗 컴포넌트 의존성 그래프

```
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
```

---

## 📦 모듈 구조

```
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
```

---

## 📋 Contracts 요약

총 **28개** 내부 관계 (모두 CALL 타입)

주요 관계:
- `RequirementMap` → `GateController` (3개)
- `ManifestApp` → `ManifestApp` (self-reference)
- `Component` → `Contract` (8개)
- `BlueprintComparator` → `BlueprintConflict` (8개)

자세한 Contract 정보는 [아카이브 문서](./archive/v1.0/MANIFEST_PROJECT_STRUCTURE.md)를 참조하세요.

---

## 🔍 상세 정보

각 컴포넌트의 상세 정보 (메서드, 속성, Contracts)는 다음 문서를 참조하세요:

- [상세 컴포넌트 목록](./archive/v1.0/MANIFEST_PROJECT_STRUCTURE.md) - 모든 컴포넌트의 상세 정보
- [ASCII 시각화](./archive/v1.0/MANIFEST_PROJECT_VISUALIZATION.md) - ASCII 아트로 표현된 구조
- [UI 표시 상태](./archive/v1.0/MANIFEST_PROJECT_VIEW_STATUS.md) - UI에서의 표시 방법

---

## 🔄 업데이트 방법

프로젝트 구조를 업데이트하려면:

1. **자동 추출**: `/audit_drift` 명령 실행
2. **수동 확인**: `.manifest/blueprint_code.json` 파일 확인
3. **UI 새로고침**: Structure View에서 자동으로 반영됨
