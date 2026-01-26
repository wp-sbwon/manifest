# Manifest 프로젝트 시각화

## 1. Feature 중심 아키텍처 구조

```mermaid
graph TB
    subgraph Features["Features"]
        F1[Feature: Core Infrastructure]
        F2[Feature: Configuration System]
        F3[Feature: State Management]
        F4[Feature: Agent Bridge]
        F5[Feature: Drift Auditor]
        F6[Feature: Custom Widgets]
        F7[Feature: 5-View Workspace]
        F8[Feature: Testing Framework]
    end

    subgraph Requirements["Requirements"]
        R1[REQ-01: API Key Management]
        R2[REQ-02: State Persistence]
        R3[REQ-03: IPC Communication]
        R4[REQ-04: Architecture Validation]
        R5[REQ-05: Visual Components]
        R6[REQ-06: Multi-View Interface]
        R7[REQ-07: Test Coverage]
    end

    subgraph Modules["Modules"]
        M1[Module: Presentation Layer]
        M2[Module: Business Logic]
        M3[Module: Infrastructure]
    end

    F1 --> R1
    F2 --> R1
    F3 --> R2
    F4 --> R3
    F5 --> R4
    F6 --> R5
    F7 --> R6
    F8 --> R7

    R1 --> M3
    R2 --> M2
    R3 --> M2
    R4 --> M2
    R5 --> M1
    R6 --> M1
    R7 --> M1
```

## 2. Feature → Class → Method 계층 구조

```mermaid
graph TD
    subgraph Feature1["Feature: State Management"]
        C1[Class: StateManager]
        C1 --> M1[Method: load_state]
        C1 --> M2[Method: save_state]
        C1 --> M3[Method: add_chat_message]
        C1 --> M4[Method: set_last_action]
    end

    subgraph Feature2["Feature: Agent Bridge"]
        C2[Class: AgentBridge]
        C2 --> M5[Method: start]
        C2 --> M6[Method: stop]
        C2 --> M7[Method: send_message]
        C2 --> M8[Method: receive_message]
    end

    subgraph Feature3["Feature: Drift Auditor"]
        C3[Class: DriftAuditor]
        C3 --> M9[Method: audit_project]
        C3 --> M10[Method: parse_python_file]
        C3 --> M11[Method: compare_with_blueprint]
    end

    subgraph Feature4["Feature: Custom Widgets"]
        C4[Class: RequirementMap]
        C5[Class: ArchitectureGraph]
        C6[Class: FeatureTree]
        C7[Class: TaskTree]
        C8[Class: GateController]
    end
```

## 3. 뷰 구조 및 데이터 흐름 (strict doc > view)

```mermaid
graph LR
    subgraph Views["7 Views"]
        V1[Architect<br/>Intent View]
        V2[Blueprint<br/>Design View]
        V3[Inspector<br/>3 Modes]
        V4[Mission Control<br/>Task Management]
        V5[History<br/>Git Timeline]
        V6[Feature Explorer<br/>Feature → Class → Method]
        V7[Project Info<br/>Architecture]
    end

    subgraph Data["Data Sources (strict doc)"]
        D1[intent.json<br/>Features & Requirements]
        D2[blueprint.json<br/>Components & Contracts]
        D3[state.json<br/>Session State]
        D4[project.json<br/>Architecture Spec]
        D5[architecture.json<br/>Architecture Spec]
        D6[documentation.json<br/>Full Documentation]
    end

    V1 --> D1
    V2 --> D2
    V4 --> D3
    V6 --> D1
    V7 --> D4
    V7 --> D6
```

## 4. Feature Explorer 구조

```mermaid
graph TD
    FE[Feature Explorer View] --> FT[FeatureTree Widget]
    FT --> F1[Feature: Auth System]
    FT --> F2[Feature: Payment]
    FT --> F3[Feature: Order Management]

    F1 --> C1[Class: AuthService]
    F1 --> C2[Class: OAuthHandler]

    C1 --> M1[Method: login]
    C1 --> M2[Method: logout]
    C1 --> M3[Method: validate_token]

    C2 --> M4[Method: handle_oauth]
    C2 --> M5[Method: get_user_info]

    F2 --> C3[Class: PaymentProcessor]
    C3 --> M6[Method: process_payment]
    C3 --> M7[Method: refund]
```

## 5. Module 의존성 (Feature 기반)

```mermaid
graph TD
    subgraph Presentation["Presentation Module"]
        F1[Feature: Custom Widgets]
        F2[Feature: 5-View Workspace]
    end

    subgraph BusinessLogic["Business Logic Module"]
        F3[Feature: State Management]
        F4[Feature: Agent Bridge]
        F5[Feature: Drift Auditor]
    end

    subgraph Infrastructure["Infrastructure Module"]
        F6[Feature: Configuration System]
        F7[Feature: Core Infrastructure]
    end

    F2 --> F3
    F2 --> F4
    F2 --> F5
    F1 --> F2
    F3 --> F6
    F4 --> F6
    F5 --> F6
```

## 6. 데이터 모델 관계 (Feature 중심)

```mermaid
erDiagram
    INTENT ||--o{ FEATURE : "contains"
    FEATURE ||--o{ REQUIREMENT : "has"
    FEATURE ||--o{ CLASS : "implements"
    CLASS ||--o{ METHOD : "contains"

    BLUEPRINT ||--o{ COMPONENT : "specifies"
    COMPONENT ||--o{ CONTRACT : "defines"

    PROJECT ||--o{ MODULE : "organizes"
    MODULE ||--o{ FEATURE : "contains"

    STATE ||--o{ MISSION_TREE : "tracks"
    STATE ||--o{ TASK_CHECKLIST : "tracks"
    STATE ||--o{ CHAT_HISTORY : "stores"
```

## 7. 구현 상태 (Feature 기반)

```mermaid
pie title Feature Implementation Status
    "Complete" : 8
    "Partial" : 2
    "Unimplemented" : 5
```

## 8. Feature Explorer 위젯 구조

```mermaid
graph LR
    FeatureTree[FeatureTree Widget] --> Features[Features List]
    Features --> Feature1[Feature 1]
    Features --> Feature2[Feature 2]
    Features --> Feature3[Feature 3]

    Feature1 --> Classes1[Classes]
    Classes1 --> Class1[Class A]
    Classes1 --> Class2[Class B]

    Class1 --> Methods1[Methods]
    Methods1 --> Method1[method1]
    Methods1 --> Method2[method2]
```

## 9. 명령 처리 흐름 (Feature 기반)

```mermaid
sequenceDiagram
    participant User
    participant App
    participant StateMgr[State Management Feature]
    participant AgentBridge[Agent Bridge Feature]
    participant DriftAudit[Drift Auditor Feature]
    participant FeatureExplorer[Feature Explorer]

    User->>App: Enter Command
    App->>StateMgr: Save Chat Message
    App->>App: Process Command

    alt Command is /audit
        App->>DriftAudit: audit_project()
        DriftAudit-->>App: Conflicts
    else Command is /features
        App->>FeatureExplorer: Load Features
        FeatureExplorer-->>App: Feature Tree
    else Command is /reload
        App->>App: Reload JSON files
    else Regular Command
        App->>AgentBridge: Start Mission
        AgentBridge-->>App: Status
    end

    App->>StateMgr: Save State
```

## 10. 프로젝트 통계 (Feature 기반)

### Feature 통계
- **완료된 Feature**: 8개
- **부분 구현 Feature**: 2개
- **미구현 Feature**: 5개

### Feature별 구현 상태
- ✅ Core Infrastructure (100%)
- ✅ Configuration System (100%)
- ✅ State Management (100%)
- ✅ Agent Bridge (100%)
- ✅ Drift Auditor (100%)
- ✅ Custom Widgets (100%)
- ✅ 5-View Workspace (100%)
- ✅ Testing Framework (100%)
- ⚠️ Bootstrap UI (50%)
- ⚠️ Git Integration (70%)
- ❌ Multi-Agent System (0%)
- ❌ Context Injection (0%)
- ❌ Structural Management (0%)
- ❌ Shadow Manager (0%)
- ✅ Agent System Integration (100%)

## 11. Feature Explorer 사용 흐름

```mermaid
graph TD
    Start[User opens Feature Explorer] --> Load[Load intent.json]
    Load --> Parse[Parse Features]
    Parse --> Display[Display FeatureTree]
    Display --> Select[User selects Feature]
    Select --> ShowClasses[Show Classes in Feature]
    ShowClasses --> SelectClass[User selects Class]
    SelectClass --> ShowMethods[Show Methods in Class]
    ShowMethods --> ViewCode[View Code Implementation]
```

## 12. 데이터 파일 구조 (Feature 중심)

```
.manifest/
├── intent.json          ← Features & Requirements (strict doc)
├── blueprint.json       ← Components & Contracts (strict doc)
├── architecture.json    ← Architecture Spec (strict doc)
├── project.json         ← Project Architecture (strict doc)
├── documentation.json   ← Full Documentation (strict doc)
└── state.json           ← Session State
```

각 JSON 파일은 해당 뷰에서 렌더링됩니다 (strict doc > view 패턴).

## 13. Feature 중심 아키텍처 원칙

1. **Feature First**: 모든 아키텍처 표현은 Feature를 중심으로 구성
2. **Requirement Mapping**: 각 Feature는 Requirements와 연결
3. **Module Organization**: Features는 Modules로 그룹화
4. **Class/Method Hierarchy**: Feature → Class → Method 계층 구조
5. **Strict Doc > View**: JSON 문서가 뷰의 단일 소스

## 14. Feature Explorer 구현 상세

### 데이터 구조
```json
{
  "features": [
    {
      "id": "feature-1",
      "name": "Auth System",
      "status": "done",
      "classes": [
        {
          "id": "class-1",
          "name": "AuthService",
          "methods": [
            {"id": "method-1", "name": "login"},
            {"id": "method-2", "name": "logout"}
          ]
        }
      ]
    }
  ]
}
```

### 위젯 동작
- Feature 선택 시 해당 Feature의 Classes 표시
- Class 선택 시 해당 Class의 Methods 표시
- Method 선택 시 코드 구현 위치 표시 (향후 구현)

## 15. 아키텍처 레이어 (Module 기반)

```mermaid
graph TB
    subgraph Modules["Modules (not files)"]
        M1[Module: Presentation]
        M2[Module: Business Logic]
        M3[Module: Infrastructure]
    end

    subgraph Features["Features in Modules"]
        M1 --> F1[Feature: Custom Widgets]
        M1 --> F2[Feature: 5-View Workspace]
        M2 --> F3[Feature: State Management]
        M2 --> F4[Feature: Agent Bridge]
        M2 --> F5[Feature: Drift Auditor]
        M3 --> F6[Feature: Configuration]
    end
```

**중요**: 아키텍처는 파일(`app.py`, `widgets.py`)이 아닌 **Module과 Feature** 중심으로 표현됩니다.
