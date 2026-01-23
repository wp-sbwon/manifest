# Manifest 프로젝트 전체 아키텍처 및 요구사항

**생성일**: 2025-01-23  
**분석 방법**: Manifest CodeExtractor를 사용한 Bottom-up 분석

## 프로젝트 개요

### 비전
**AI-Native Orchestration IDE** - "Code Blindness" 문제를 해결하여 개발자를 **Conductor(지휘자)**로 승격

### 핵심 가치
1. **Visual Truth**: 설계(Architect)와 구현(Blueprint)의 실시간 동기화
2. **Tiered Context**: Mission Stage에 따른 계층적 컨텍스트 관리
3. **Drift Detection**: 아키텍처와 코드 간의 불일치 실시간 감지
4. **State Continuity**: 세션 중단 후에도 정확한 재개
5. **Blueprint-First Development**: 모든 코드 변경은 blueprint.json에 정렬

## 전체 아키텍처

### 시스템 레이어 구조

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ ManifestApp  │  │SettingsScreen│  │BootstrapApp │       │
│  │  (TUI Main)  │  │  (Settings)  │  │  (Bootstrap)│       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                 │                 │                │
│  ┌──────▼──────────────────▼─────────────────▼───────┐       │
│  │           Custom Widgets                         │       │
│  │  RequirementMap │ ArchitectureGraph │ TaskTree  │       │
│  │  FeatureTree    │ GateController                 │       │
│  └──────────────────────────────────────────────────┘       │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                  Business Logic Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │AgentBridge   │  │AgentCoordinator│ │ContextProvider│    │
│  │              │  │              │  │              │      │
│  │- Orchestrator│  │- Task Scoping│  │- Tiered Ctx │      │
│  │- AgentManager│  │- Agent Lifecycle│- Skills Inject│    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │               │
│  ┌──────▼──────────────────▼─────────────────▼───────┐      │
│  │           Agent Runtime System                   │      │
│  │  OrchestratorAgent │ PlannerAgent │ CoderAgent  │      │
│  │  AgentExecutor (LLM API)                        │      │
│  └──────────────────────────────────────────────────┘      │
│         │                                                  │
│  ┌──────▼──────────────────────────────────────────┐      │
│  │        Audit & Drift Detection                  │      │
│  │  DriftAuditor │ BlueprintComparator │          │      │
│  │  CodeExtractor │ BlueprintSynchronizer         │      │
│  └─────────────────────────────────────────────────┘      │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                Infrastructure Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │StateManager  │  │ConfigManager │  │SettingsManager│    │
│  │              │  │              │  │              │     │
│  │- Persistence │  │- API Keys    │  │- Unified     │     │
│  │- Session     │  │- Encryption  │  │  Settings    │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                 │                 │              │
│  ┌──────▼──────────────────▼─────────────────▼───────┐    │
│  │        Terminal & Command Execution               │    │
│  │  TerminalRouter │ OpenCodeAdapter                 │    │
│  │  Watchdog │ ResourceMonitor                      │    │
│  └───────────────────────────────────────────────────┘    │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                    Data Layer                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │.manifest/    │  │.claude/rules/│  │AGENTS.md     │      │
│  │              │  │              │  │              │      │
│  │- state.json  │  │- manifest-   │  │- Project     │      │
│  │- intent.json │  │  policy.md   │  │  Skills      │      │
│  │- blueprint.json│ │- *.md skills │  │              │      │
│  │- agent_config.json│            │  │              │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## 모듈 구조 및 책임

### 1. Presentation Layer (`src/manifest/ui/`)

#### `app.py` - ManifestApp
**책임**: 메인 TUI 애플리케이션 및 뷰 관리

**주요 기능**:
- 5-View Workspace 관리 (Architect, Blueprint, History, Feature Explorer, Project Info)
- Inspector View (3 모드: Visual, Data, Drift)
- Mission Control Sidebar
- 사용자 입력 처리 및 명령 라우팅
- Agent 출력 표시

**의존성**:
- `core.config`, `core.state_manager`
- `bridge.agent_bridge`
- `audit.drift_auditor`
- `agents.agent_coordinator`
- `ui.widgets`, `ui.settings_screen`

**상태**: ✅ 완전 구현 (단, User Input → Agent 통합은 부분 구현)

#### `settings_screen.py` - SettingsScreen
**책임**: 설정 관리 UI (별도 Screen)

**주요 기능**:
- API 키 설정/검증
- Agent 모델 설정
- Skills 관리
- Policy 파일 편집

**상태**: ✅ 완전 구현

#### `widgets.py` - Custom Widgets
**책임**: 재사용 가능한 Textual 위젯

**위젯 목록**:
- `RequirementMap`: 요구사항 맵 시각화
- `ArchitectureGraph`: 아키텍처 그래프
- `FeatureTree`: Feature 탐색 트리
- `TaskTree`: Task 관리 트리
- `GateController`: 승인 게이트 컨트롤러

**상태**: ✅ 완전 구현

### 2. Business Logic Layer

#### `bridge/agent_bridge.py` - AgentBridge
**책임**: Agent 시스템 직접 통합

**주요 기능**:
- Agent 시스템 초기화 및 관리
- Mission 시작/중지
- Agent 시작/중지
- Terminal Router 통합
- Watchdog 통합

**상태**: ✅ 완전 구현

#### `agents/agent_coordinator.py` - AgentCoordinator
**책임**: Agent 조정 및 Task 범위 관리

**주요 기능**:
- Orchestrator 시작
- Worker Agent 시작 (planner, coder, test, review)
- Task 범위 검증
- Container 기반 실행 지원
- State 동기화

**상태**: ✅ 완전 구현 (단, Container 통신은 부분 구현)

#### `agents/context_provider.py` - ContextProvider
**책임**: Tiered Context 제공

**주요 기능**:
- Tier 0: Policy & Principles
- Tier 1: Architecture & Blueprint
- Tier 2: Blueprint nodes
- Tier 3: File contents
- Skills 주입

**상태**: ✅ 완전 구현

#### `agents/task_scoper.py` - TaskScoper
**책임**: Task 범위 관리

**주요 기능**:
- Task 범위 추출 (components, files, allowed modifications)
- 범위 검증
- 범위 요약 생성

**상태**: ✅ 완전 구현

#### `agents/skills_manager.py` - SkillsManager
**책임**: Agent Skills 관리

**주요 기능**:
- Agent 기본 Skills 로드 (agent_config.json)
- 프로젝트 스코프 Skills 로드 (AGENTS.md)
- Skill 정의 로드 (`.claude/rules/`)
- Skills를 프롬프트에 포맷팅

**상태**: ✅ 완전 구현

### 3. Runtime Layer (`src/manifest/runtime/`)

#### `runtime/agent/executor.py` - AgentExecutor
**책임**: LLM API 호출 및 Agent 실행

**주요 기능**:
- Anthropic API 통합
- OpenAI API 통합
- Streaming 응답 처리
- 에러 처리 및 재시도

**상태**: ✅ 완전 구현

#### `runtime/agent/manager.py` - AgentManager
**책임**: Agent 생성 및 생명주기 관리

**주요 기능**:
- Agent 생성 (orchestrator, planner, coder, test, review)
- Agent 프롬프트 생성
- Agent 시작/중지

**상태**: ✅ 완전 구현

#### `runtime/agent/orchestrator_agent.py` - OrchestratorAgent
**책임**: Mission 조정

**상태**: ✅ 완전 구현

#### `runtime/agent/planner_agent.py` - PlannerAgent
**책임**: Task 계획 수립

**상태**: ✅ 완전 구현

#### `runtime/agent/coder_agent.py` - CoderAgent
**책임**: 코드 구현

**상태**: ✅ 완전 구현

#### `runtime/router/terminal_router.py` - TerminalRouter
**책임**: 터미널 명령 실행

**주요 기능**:
- 명령 실행 (buffered, streaming)
- 프로세스 추적
- 명령 취소
- Watchdog 통합

**상태**: ✅ 완전 구현

#### `runtime/opencode_adapter.py` - OpenCodeAdapter
**책임**: OpenCode 선택적 통합

**주요 기능**:
- OpenCode 자동 감지
- Fallback 내부 구현
- 프로세스 추적 및 취소 지원

**상태**: ✅ 완전 구현

### 4. Audit Layer (`src/manifest/audit/`)

#### `audit/drift_auditor.py` - DriftAuditor
**책임**: 아키텍처 드리프트 감지

**주요 기능**:
- AST 파싱 (Python 파일)
- Blueprint 비교
- 충돌 감지 및 보고
- Bottom-up Blueprint 생성

**상태**: ✅ 완전 구현

#### `audit/code_extractor.py` - CodeExtractor
**책임**: 코드 구조 추출 및 Blueprint 생성

**주요 기능**:
- Python 파일 파싱
- Component 추출 (classes, functions)
- Contract 추출 (dependencies, calls, inheritance)
- Blueprint JSON 생성

**상태**: ✅ 완전 구현

#### `audit/blueprint_comparator.py` - BlueprintComparator
**책임**: Blueprint 비교

**상태**: ✅ 완전 구현

#### `audit/blueprint_synchronizer.py` - BlueprintSynchronizer
**책임**: Blueprint 동기화 및 충돌 해결

**상태**: ✅ 완전 구현

### 5. Infrastructure Layer (`src/manifest/core/`)

#### `core/config.py` - ConfigManager
**책임**: 설정 및 API 키 관리

**주요 기능**:
- API 키 암호화 저장/로드
- API 키 검증
- Agent 모델 설정 관리

**상태**: ✅ 완전 구현

#### `core/settings_manager.py` - SettingsManager
**책임**: 통합 설정 관리

**주요 기능**:
- API 키 관리
- Agent 모델 설정
- Skills 관리
- Policy 파일 관리
- AGENTS.md 관리

**상태**: ✅ 완전 구현

#### `core/state_manager.py` - StateManager
**책임**: 상태 영속성

**주요 기능**:
- Mission Tree 관리
- Task Checklist 관리
- Chat History 관리
- 세션 재개

**상태**: ✅ 완전 구현

### 6. Agents Infrastructure (`src/manifest/agents/`)

#### `agents/watchdog.py` - AgentWatchdog
**책임**: Agent 모니터링 및 문제 감지

**상태**: ✅ 완전 구현

#### `agents/resource_monitor.py` - ResourceMonitor
**책임**: 리소스 사용량 모니터링

**상태**: ✅ 완전 구현

#### `agents/container_manager.py` - ContainerManager
**책임**: Docker 컨테이너 관리

**상태**: ⚠️ 부분 구현 (기본 구조만)

#### `agents/container_communication.py` - Container Communication
**책임**: 컨테이너 간 통신

**상태**: ⚠️ 부분 구현 (기본 구조만)

## 데이터 모델

### State Schema (`.manifest/state.json`)
```json
{
  "version": "1.0",
  "session_id": "string",
  "last_updated": "ISO8601",
  "mission_tree": {
    "root": {},
    "branches": []
  },
  "task_checklist": [
    {
      "id": "task-1",
      "name": "Task Name",
      "status": "pending|in_progress|done|blocked",
      "stage": "planning|implementation|testing|review",
      "subtasks": [],
      "agent": {
        "type": "coder",
        "status": "active|stopped",
        "channel": "squad-task-1-coder"
      },
      "scope": {
        "components": [],
        "files": [],
        "allowed_modifications": []
      }
    }
  ],
  "chat_history": {
    "main": [
      {"role": "user|assistant|system", "content": "..."}
    ],
    "squad-*": []
  },
  "last_action": "string"
}
```

### Intent Schema (`.manifest/intent.json`)
```json
{
  "version": "1.0",
  "sprint": "Sprint Name",
  "features": [
    {
      "id": "feature-1",
      "name": "Feature Name",
      "status": "pending|wip|done",
      "reqs": [
        {
          "id": "REQ-01",
          "desc": "Requirement Description",
          "state": "pending|wip|done"
        }
      ]
    }
  ]
}
```

### Blueprint Schema (`.manifest/blueprint.json`)
```json
{
  "version": "1.0",
  "zones": {
    "client": ["comp-id-1", "comp-id-2"],
    "server": ["comp-id-3"],
    "data": ["comp-id-4"]
  },
  "components": [
    {
      "id": "comp-id-1",
      "name": "ComponentName",
      "type": "class|function",
      "file": "path/to/file.py",
      "line": 10,
      "module_path": "manifest.ui.app",
      "methods": ["method1", "method2"],
      "attributes": ["attr1"],
      "status": "active|ghost|pending|error"
    }
  ],
  "contracts": [
    {
      "from": "comp-id-1",
      "to": "comp-id-2",
      "type": "dependency|call|inheritance",
      "symbols": ["method_name"],
      "file": "path/to/file.py"
    }
  ]
}
```

### Agent Config Schema (`.manifest/agent_config.json`)
```json
{
  "version": "1.0",
  "agent_models": {
    "orchestrator": {
      "provider": "anthropic",
      "model": "claude-3-5-sonnet-20241022",
      "use_default_key": true
    },
    "planner": {...},
    "coder": {...},
    "test": {...},
    "review": {...}
  },
  "default_models": {
    "anthropic": "claude-3-5-sonnet-20241022",
    "openai": "gpt-4-turbo-preview",
    "google": "gemini-pro"
  },
  "agent_skills": {
    "coder": ["skill1", "skill2"],
    "planner": ["skill3"]
  }
}
```

## 핵심 요구사항

### 기능 요구사항 (Functional Requirements)

#### FR-1: Visual Truth
**설명**: 설계(Architect)와 구현(Blueprint)의 실시간 동기화

**구현 상태**: ✅ 완전 구현
- Architect View: intent.json 표시
- Blueprint View: blueprint.json 표시
- Drift Detection: 실시간 불일치 감지

#### FR-2: Tiered Context System
**설명**: Mission Stage에 따른 계층적 컨텍스트 관리

**구현 상태**: ✅ 완전 구현
- Tier 0: Policy & Principles (`.claude/rules/manifest-policy.md`)
- Tier 1: Architecture & Blueprint (orchestrator, planner)
- Tier 2: Blueprint nodes (coder)
- Tier 3: File contents (surgical code)

#### FR-3: Multi-Agent System
**설명**: 여러 Agent의 협업을 통한 작업 수행

**구현 상태**: ⚠️ 부분 구현 (60%)
- ✅ Agent Infrastructure: 완전 구현
- ✅ 개별 Agent 실행: 완전 구현
- ⚠️ Agent 간 협업: 부분 구현
- ❌ 자동 워크플로우: 미구현

#### FR-4: Drift Detection
**설명**: 아키텍처와 코드 간의 불일치 실시간 감지

**구현 상태**: ✅ 완전 구현
- AST 파싱
- Blueprint 비교
- 충돌 감지 및 보고

#### FR-5: State Continuity
**설명**: 세션 중단 후에도 정확한 재개

**구현 상태**: ✅ 완전 구현
- 상태 영속성
- 세션 재개
- Chat History 관리

#### FR-6: Settings Management
**설명**: 모든 설정을 UI에서 관리

**구현 상태**: ✅ 완전 구현
- API 키 설정/검증
- Agent 모델 설정
- Skills 관리
- Policy 파일 편집

#### FR-7: Skills System
**설명**: Agent별 및 프로젝트별 Skills 관리

**구현 상태**: ✅ 완전 구현
- Agent 기본 Skills
- 프로젝트 스코프 Skills
- Skill 정의 파일 관리

### 비기능 요구사항 (Non-Functional Requirements)

#### NFR-1: 성능
- 앱 시작 시간: < 1초 ✅
- 드리프트 감지: 프로젝트 크기에 비례 ✅
- 상태 저장: < 100ms ✅
- 뷰 전환: 즉시 ✅

#### NFR-2: 보안
- API 키 암호화 ✅
- 파일 권한 관리 ✅
- 입력 검증 ✅

#### NFR-3: 확장성
- 모듈화된 구조 ✅
- 플러그인 가능한 아키텍처 ✅
- 선택적 의존성 지원 ✅

#### NFR-4: 테스트 가능성
- 단위 테스트: 125개 모두 통과 ✅
- Mock 기반 테스트 ✅
- 통합 테스트 ✅

## 아키텍처 원칙

### 1. 계층적 아키텍처
- **Presentation Layer**: UI 및 사용자 인터랙션
- **Business Logic Layer**: 핵심 비즈니스 로직
- **Infrastructure Layer**: 기본 인프라 및 유틸리티

### 2. 단일 책임 원칙 (SRP)
- 각 모듈은 하나의 명확한 책임만 가짐
- 예: `StateManager`는 상태 관리만, `ConfigManager`는 설정만

### 3. 의존성 역전 원칙 (DIP)
- 고수준 모듈은 저수준 모듈에 의존하지 않음
- 인터페이스를 통한 추상화

### 4. Tiered Context
- Mission Stage에 따라 다른 컨텍스트 제공
- 불필요한 정보 노출 최소화

### 5. Blueprint-First Development
- 모든 구조적 변경은 Blueprint에 먼저 반영
- 코드와 Blueprint의 일관성 유지

## 데이터 흐름

### 1. 사용자 입력 처리 흐름
```
User Input
  ↓
ManifestApp.on_input_submitted()
  ↓
process_command()
  ├─> Command 파싱 (/audit, /config, /start_agent, etc.)
  ├─> AgentBridge 통신 (if agent command)
  ├─> StateManager 업데이트
  └─> UI 업데이트
```

### 2. Agent 실행 흐름
```
/start_agent <task_id> <agent_type>
  ↓
AgentCoordinator.start_worker_agent()
  ├─> TaskScoper.get_task_context() (범위 추출)
  ├─> ContextProvider.get_worker_context() (Tiered Context)
  ├─> AgentBridge.start_agent_mission()
  │   ├─> AgentManager.create_agent()
  │   ├─> AgentExecutor.execute_agent() (LLM API 호출)
  │   └─> StateManager.add_chat_message() (출력 저장)
  └─> UI 업데이트 (handle_agent_output)
```

### 3. Drift 감지 흐름
```
/audit
  ↓
DriftAuditor.audit_project()
  ├─> CodeExtractor.extract_project_structure() (Bottom-up)
  ├─> BlueprintComparator.compare_blueprints() (Top-down vs Bottom-up)
  ├─> 충돌 감지 및 그룹화
  └─> Inspector View에 표시
```

### 4. Settings 저장 흐름
```
SettingsScreen.on_save()
  ↓
SettingsManager.save_*()
  ├─> ConfigManager.save_api_keys() (암호화)
  ├─> ConfigManager.set_agent_model()
  ├─> SkillsManager.save_agent_skills()
  └─> Policy/AGENTS.md 파일 저장
```

## 컴포넌트 의존성 그래프

```
ManifestApp
├── ConfigManager
├── StateManager
├── AgentBridge
│   ├── AgentExecutor
│   ├── Orchestrator
│   ├── AgentManager
│   └── TerminalRouter
│       └── OpenCodeAdapter
├── AgentCoordinator
│   ├── ContextProvider
│   │   └── SkillsManager
│   ├── TaskScoper
│   └── ContainerManager
├── DriftAuditor
│   ├── CodeExtractor
│   ├── BlueprintComparator
│   └── BlueprintSynchronizer
├── SettingsScreen
│   └── SettingsManager
│       ├── ConfigManager
│       └── SkillsManager
└── Widgets
```

## 기술 스택

### Core
- **Python 3.9+**: 메인 언어
- **Textual**: TUI 프레임워크
- **asyncio**: 비동기 처리

### Required Dependencies
- **aiofiles**: 비동기 파일 I/O
- **cryptography**: API 키 암호화
- **httpx**: HTTP 클라이언트 (API 검증)
- **pytest**: 테스트 프레임워크

### Optional Dependencies
- **GitPython**: Git 통합
- **opencode**: OpenCode 통합 (선택적)
- **docker**: Docker 컨테이너 지원

## 구현 상태 요약

### 완전 구현 (100%)
- UI Infrastructure
- Agent System Infrastructure
- Settings Management
- Skills System
- Drift Detection
- State Management
- Terminal Execution

### 부분 구현 (60%)
- User Input → Agent 통합
- Agent Output Display
- Container Communication

### 미구현 (0-20%)
- Multi-Agent 자동 워크플로우
- Context Injection Hooks
- Structural Spec-First Management
- Shadow Manager

## 다음 우선순위

### Critical
1. User Input → Agent 통합 완성
2. Agent Output Display 개선

### High
1. Multi-Agent Workflow 구현
2. Container Communication 완성

### Medium
1. Context Injection Hooks
2. Structural Spec-First Management
3. Shadow Manager
