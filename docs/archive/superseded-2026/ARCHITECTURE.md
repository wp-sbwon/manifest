# Manifest 프로젝트 아키텍처 문서

## 개요

Manifest는 **AI-Native Orchestration IDE**로, "Code Blindness" 문제를 해결하기 위해 개발자를 **Conductor(지휘자)**로 승격시키는 도구입니다. 이 문서는 Manifest 프로젝트 자체의 아키텍처와 현재 구현 상태를 설명합니다.

## 프로젝트 비전

Manifest는 다음과 같은 핵심 가치를 제공합니다:
- **Visual Truth**: 설계(Architect)와 구현(Blueprint)의 실시간 동기화
- **Tiered Context**: Mission Stage에 따른 계층적 컨텍스트 관리
- **Drift Detection**: 아키텍처와 코드 간의 불일치 실시간 감지
- **State Continuity**: 세션 중단 후에도 정확한 재개

## 현재 구현 상태

### ✅ 완료된 기능 (Phase 1: TUI MVP)

#### 1. Core Infrastructure
- **디렉토리 구조**: `.manifest/`, `.claude/rules/`, `tests/`
- **JSON 스키마**: `architecture.json`, `blueprint.json`, `intent.json`, `state.json`
- **정책 파일**: `.claude/rules/manifest-policy.md`

#### 2. Configuration & Bootstrap
- **config.py**: 암호화된 API 키 관리
- **bootstrap_ui.py**: API 키 설정 TUI (현재는 데모 모드로 동작)
- API 키 검증 및 암호화 저장

#### 3. State Management
- **state_manager.py**: 완전한 상태 영속성 시스템
- Mission Tree, Task Checklist, Chat History 관리
- 세션 재개 기능

#### 4. Agent Bridge
- **agent_bridge.py**: Agent system integration
- JSON 기반 메시지 프로토콜
- 비동기 메시지 처리
- 명령 인터페이스: `start_mission()`, `get_status()`, `promote_task()`
- **ExecutorFactory**: LLM execution backend 선택 및 생성
  - "direct": 직접 LLM API 호출 (AgentExecutor)
  - "opencode": OpenCode HTTP API (OpenCodeLLMAdapter) - 기본값

#### 5. Drift Auditor
- **drift_auditor.py**: 아키텍처 드리프트 감지
- AST 파싱 (Python 파일)
- Blueprint 비교 로직
- 심각도 기반 충돌 보고 (ERROR, WARNING, INFO)

#### 6. Custom Widgets
- **widgets.py**: 완전한 위젯 라이브러리
  - `RequirementMap`: 기능 의존성 시각화
  - `ArchitectureGraph`: 노드-엣지 그래프
  - `FeatureTree`: AST 인식 코드 네비게이션
  - `TaskTree`: 상태 인식 미션 트래커
  - `GateController`: 승인 버튼 (Approve/Reject/Feedback)

#### 7. 진입점 및 UI (현재)
- **진입점**: `manifest` 또는 `python -m manifest` → **launcher** (`manifest.launcher.main`)
- **launcher**: (1) 상시 시각화 **View** 프로세스 시작, (2) **OpenCode** 터미널 실행 (`opencode . --agent manifest-orchestrator -c`)
- **채팅/입력**: OpenCode 터미널에서 전부 처리 (우리 채팅 TUI 제거됨)
- **상시 시각화 View** (`manifest.view.app.ManifestViewApp`): blueprint·구조·drift·태스크를 상시 표시하는 MVP Textual 앱. 추후 Electron 앱으로 전환 예정.

#### 8. Testing
- **tests/**: 완전한 테스트 스위트
  - `test_state_manager.py`: 상태 영속성 테스트
  - `test_drift_auditor.py`: 드리프트 감지 테스트
  - `test_agent_bridge.py`: Agent bridge protocol tests
  - `test_app.py`: 통합 테스트
  - `test_app_input.py`: 입력 처리 테스트

### ✅ 완전 구현된 기능 (이전에 "미구현"으로 잘못 표기됨)

1. **Full Multi-Agent Squad System** ✅
   - ✅ Orchestrator, Planner, Coder 등 에이전트 통합 완료
   - ✅ 에이전트 간 협업 메커니즘 (AgentMessageBus)
   - ✅ Event-driven 워크플로우 (기본 활성화)
   - ✅ 병렬 실행 지원 (의존성 해결 포함)
   - **위치**: `src/manifest/agents/worker_squad_executor.py`, `src/manifest/agents/agent_message_bus.py`

2. **Agent System Integration** ✅
   - ✅ 완전한 Agent 시스템 통합 완료
   - ✅ Shadow Manager (샌드박스 운영) 구현 완료
   - **위치**: `src/manifest/runtime/shadow_manager.py`

3. **Context Injection Hooks** ✅
   - ✅ 에이전트 프롬프트 가로채기 (HookManager)
   - ✅ Visual Reality 업데이트 주입 (VisualRealityHook)
   - ✅ Policy 주입 (PolicyInjectionHook)
   - **위치**: `src/manifest/runtime/hooks/prompt_hooks.py`
   - **통합**: `ExecutorFactory`에서 자동 등록, `AgentExecutor`에서 실제 사용

4. **Container Communication** ✅
   - ✅ Container API 구현 완료
   - ✅ Container Message Bus 구현 완료
   - ✅ Container State Sync 구현 완료
   - **위치**: `src/manifest/agents/container_communication.py`, `src/manifest/agents/container_api.py`

### ⏳ 실제 미구현 기능

1. **Advanced Drift Resolution** (부분 구현)
   - ✅ 드리프트 감지 (구현됨)
   - ✅ 충돌 보고 (구현됨)
   - ❌ 자동 드리프트 해결 (미구현)
   - ❌ 구조적 제안 시스템 (미구현)

2. **Structural Spec-First Management** (부분 구현)
   - ✅ Blueprint 비교 및 동기화 (구현됨)
   - ✅ 구조적 변경 감지 (구현됨)
   - ❌ Blueprint 변경 시 파일 시스템 자동 생성/삭제 (미구현)
   - ❌ 구조적 변경 제안 자동화 (미구현)

## 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│                    Manifest TUI (app.py)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Architect │  │Blueprint │  │Inspector │  │Mission   │   │
│  │  View    │  │  View    │  │  View    │  │ Control  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         Multi-Channel Chat System                    │   │
│  │  (#manifest-ai, #squad-*, etc.)                      │   │
│  └─────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
│ State Manager│ │Agent Bridge│ │Drift Auditor│
│              │ │            │ │            │
│ - Mission    │ │ - IPC Pipes │ │ - AST Parse│
│ - Tasks      │ │ - Messages │ │ - Compare  │
│ - Chat       │ │ - Commands │ │ - Conflicts│
└───────┬──────┘ └─────┬──────┘ └─────┬──────┘
        │              │               │
        └──────────────┼───────────────┘
                       │
            ┌──────────▼──────────┐
            │   .manifest/        │
            │  - state.json       │
            │  - intent.json      │
            │  - blueprint.json   │
            │  - architecture.json│
            └─────────────────────┘
                       │
            ┌──────────▼──────────┐
            │   Agent System      │
            │                     │
            │  ┌──────────────┐   │
            │  │ExecutorFactory│  │
            │  └──────┬───────┘   │
            │    ┌────┴────┐      │
            │    │         │      │
            │ AgentExecutor│OpenCode│
            │ (Direct API) │Adapter│
            │    │         │      │
            │    └────┬────┘      │
            │         │           │
            │    LLM APIs         │
            └─────────────────────┘
```

## 모듈 구조

### Core Modules

#### `app.py` - Main Application
- **책임**: TUI 애플리케이션의 진입점 및 뷰 관리
- **의존성**: 모든 다른 모듈
- **주요 클래스**: `ManifestApp`
- **주요 메서드**:
  - `on_mount()`: 앱 초기화
  - `on_input_submitted()`: 사용자 입력 처리
  - `process_command()`: 명령 처리
  - `update_*_view()`: 각 뷰 업데이트

#### `config.py` - Configuration Management
- **책임**: API 키 관리 및 설정
- **의존성**: `cryptography`
- **주요 클래스**: `ConfigManager`
- **주요 메서드**:
  - `get_api_keys()`: API 키 조회
  - `save_api_keys()`: API 키 저장 (암호화)
  - `validate_key()`: API 키 검증

#### `state_manager.py` - State Persistence
- **책임**: 애플리케이션 상태 영속성
- **의존성**: `aiofiles`
- **주요 클래스**: `StateManager`
- **주요 메서드**:
  - `save_state()`: 상태 저장
  - `load_state_async()`: 상태 로드
  - `add_chat_message()`: 채팅 메시지 추가
  - `get_next_action_prompt()`: 재개 프롬프트

#### `agent_bridge.py` - Agent System Integration
- **책임**: Agent 시스템과의 직접 통합
- **의존성**: `state_manager`, `executor_factory`
- **주요 클래스**: `AgentBridge`
- **주요 메서드**:
  - `start()`: Agent 시스템 초기화
  - `get_status()`: 상태 조회
  - `start_agent_mission()`: Agent 미션 시작
  - `get_agent_status()`: Agent 상태 조회
  - `stop_agent()`: Agent 중지
- **Executor 통합**: `ExecutorFactory`를 통해 LLM execution backend 선택
- **Agent 생성**: `AgentManager.create_agent()`를 통해 실제 Agent 인스턴스 생성
- **실제 사용**: `OrchestratorAgent` 클래스가 실제로 LLM 호출 (레거시 `Orchestrator` 클래스는 거의 미사용)

#### `drift_auditor.py` - Architecture Drift Detection
- **책임**: 코드와 Blueprint 간 불일치 감지
- **의존성**: 없음 (표준 라이브러리만 사용)
- **주요 클래스**: `DriftAuditor`, `DriftConflict`
- **주요 메서드**:
  - `parse_python_file()`: Python 파일 파싱
  - `compare_with_blueprint()`: Blueprint 비교
  - `audit_project()`: 프로젝트 전체 감사

#### `widgets.py` - Custom Widgets
- **책임**: Textual 커스텀 위젯
- **의존성**: `textual`
- **주요 클래스**:
  - `RequirementMap`: 요구사항 맵
  - `ArchitectureGraph`: 아키텍처 그래프
  - `TaskTree`: 작업 트리
  - `GateController`: 승인 컨트롤러

#### `bootstrap_ui.py` - Bootstrap Mode
- **책임**: API 키 설정 TUI
- **의존성**: `config`, `textual`
- **주요 클래스**: `BootstrapApp`
- **상태**: 현재는 데모 모드로 동작 (중첩 앱 실행 문제로 비활성화)

## 데이터 흐름

### 1. 앱 시작 흐름
```
1. ManifestApp.on_mount()
   ├─> ConfigManager.has_all_keys() 체크
   ├─> StateManager.load_state_async() 로드
   ├─> AgentBridge.start() 초기화
   │   ├─> ExecutorFactory.create_executor() (OpenCode 또는 Direct)
   │   ├─> HookManager 등록 (VisualRealityHook, PolicyInjectionHook)
   │   └─> Watchdog.start()
   ├─> AgentCoordinator 초기화
   │   ├─> WorkerSquadExecutor 생성
   │   ├─> SprintExecutor 생성
   │   └─> Event-driven 모드 활성화
   ├─> Intent/Blueprint 데이터 로드
   ├─> 각 뷰 업데이트
   └─> DriftAuditor.audit_project() 실행 (선택적)
```

### 2. 사용자 입력 처리 흐름 (정확한 경로)
```
1. 사용자 입력 (일반 텍스트, "/"로 시작 안 함)
   ├─> app.py:process_command() (line 1704)
   │   ├─> CommandHandler.handle() (명령어인 경우)
   │   └─> 일반 입력인 경우:
   │       ├─> AgentManager.create_agent("orchestrator") (line 1736)
   │       │   └─> OrchestratorAgent 인스턴스 생성
   │       ├─> orchestrator_instance.coordinate() 호출 (line 1769)
   │       │   └─> OrchestratorAgent.coordinate()
   │       │       └─> executor.execute_agent() 호출
   │       │           ├─> HookManager.apply_hooks() (프롬프트 가로채기)
   │       │           └─> LLM API 호출 (스트리밍)
   │       ├─> chunk 스트리밍 처리 (line 1774-1855)
   │       │   ├─> ChannelManager.handle_agent_output() (UI 표시)
   │       │   └─> State에 저장
   │       └─> _process_orchestrator_response() 호출 (line 1859)
   │           ├─> 정규식으로 Task 패턴 추출
   │           ├─> state_manager.create_task() (Task 생성)
   │           └─> 조건부: Worker Squad 자동 시작
   └─> 입력 필드 포커스 복원
```

### 3. 드리프트 감지 흐름
```
1. DriftAuditor.audit_project()
   ├─> find_python_files() - Python 파일 찾기
   ├─> parse_python_file() - 각 파일 파싱
   ├─> compare_with_blueprint() - Blueprint 비교
   └─> get_conflicts_by_severity() - 충돌 그룹화
       └─> Inspector 뷰에 표시
```

### 4. 상태 저장 흐름
```
1. 상태 변경 이벤트
   ├─> StateManager.set_*() 메서드 호출
   ├─> StateManager.save_state() 자동 호출
   └─> .manifest/state.json에 저장
```

## 파일 구조

```
manifest/
├── app.py                    # 메인 TUI 애플리케이션
├── config.py                 # 설정 및 API 키 관리
├── state_manager.py          # 상태 영속성
├── agent_bridge.py            # Agent system integration
├── drift_auditor.py          # 드리프트 감지
├── widgets.py                # 커스텀 위젯
├── bootstrap_ui.py           # 부트스트랩 UI
├── requirements.txt           # Python 의존성
├── .manifest/                # 런타임 디렉토리
│   ├── state.json           # 세션 상태
│   ├── architecture.json    # 아키텍처 스펙
│   ├── blueprint.json       # Blueprint 스펙
│   └── intent.json          # Intent 스펙
├── .claude/rules/
│   └── manifest-policy.md   # 정책 파일
├── tests/                    # 테스트 스위트
│   ├── test_app.py
│   ├── test_bridge.py
│   ├── test_drift_auditor.py
│   ├── test_state_manager.py
│   └── test_app_input.py
└── reference/                # 참조 문서
    ├── implementation_plan.md
    └── test.py
```

## 주요 설계 결정

### 1. 계층적 아키텍처
- **UI Layer**: `app.py`, `widgets.py`, `bootstrap_ui.py`
- **Business Logic Layer**: `state_manager.py`, `agent_bridge.py`, `drift_auditor.py`
- **Infrastructure Layer**: `config.py`

### 2. 상태 관리
- **중앙 집중식**: `StateManager`가 모든 상태 관리
- **자동 저장**: 상태 변경 시 자동 저장
- **비동기 지원**: `async/await` 패턴 사용

### 3. 모듈화
- 각 모듈은 단일 책임 원칙 준수
- 느슨한 결합, 강한 응집력
- 명확한 인터페이스

### 4. 확장성
- Agent 시스템은 직접 통합됨
- 위젯은 재사용 가능한 컴포넌트
- 플러그인 가능한 구조

## 기술 스택

### Core
- **Python 3.9+**: 메인 언어
- **Textual**: TUI 프레임워크
- **asyncio**: 비동기 처리

### Dependencies
- **aiofiles**: 비동기 파일 I/O
- **cryptography**: API 키 암호화
- **GitPython**: Git 통합
- **httpx**: HTTP 클라이언트 (API 검증, OpenCode 통신)
- **pytest**: 테스트 프레임워크

### LLM Execution Backends
- **Direct API**: `AgentExecutor` - 직접 LLM API 호출 (Anthropic, OpenAI 등)
- **OpenCode**: `OpenCodeLLMAdapter` - OpenCode HTTP API를 통한 실행 (기본값)
  - Context 관리, Tool execution을 OpenCode에 위임
  - 서버 자동 감지 및 시작 지원
- **선택**: `ExecutorFactory`가 `settings.json`의 `agent.execution_backend` 설정에 따라 선택
- **Hook 통합**: 두 백엔드 모두 `HookManager`를 통해 프롬프트 가로채기 지원

## 향후 개선 사항 (2026-01-28 업데이트)

### ✅ 완료된 항목 (이전 Phase 2-3)
1. ✅ **Full Agent System Integration**: 완전한 Agent 시스템 통합 완료
2. ✅ **Multi-Agent System**: 에이전트 스쿼드 시스템 완료 (Event-driven 모드)
3. ✅ **Context Injection**: 에이전트 프롬프트 가로채기 완료 (HookManager)
4. ✅ **Shadow Manager**: 샌드박스 운영 및 안전한 승격 완료

### 단기 (실제 남은 작업)
1. **Enhanced Drift Resolution**: 자동 드리프트 해결 (현재는 감지만 가능)
2. **Structural Spec-First Management**: Blueprint 기반 파일 시스템 자동 관리
3. **Bootstrap UI 문제 해결**: 이벤트 루프 충돌 해결

### 중기 (선택적)
1. **Visual Editor**: Blueprint 시각적 편집
2. **UI 개선**: 병렬 실행 시각화 개선
3. **OpenCode 터미널 Adapter**: OpenCode 터미널 API 연동 (API 정의되면)

### 장기 (Phase 4)
1. **Real-time Collaboration**: 다중 사용자 협업
2. **Plugin System**: 확장 가능한 플러그인 아키텍처

## 테스트 커버리지 (2026-01-28)

현재 테스트는 다음을 포함합니다:
- ✅ 상태 관리 테스트
- ✅ 드리프트 감지 테스트
- ✅ Agent bridge protocol tests
- ✅ 통합 테스트 (30개 파일, ~500개 테스트)
- ✅ E2E 테스트 (13개 파일, ~142개 테스트)
- ✅ 입력 처리 테스트
- ✅ Agent-to-Agent 메시징 테스트
- ✅ Container Communication 테스트
- ✅ 병렬 실행 테스트
- ✅ Event-driven 워크플로우 테스트

**총 테스트 수**: 1142개
**통과율**: 100% (1142/1142)
**커버리지**: ~70% (추정)

## 성능 고려사항

- **비동기 처리**: UI 블로킹 방지
- **지연 로딩**: 필요 시에만 데이터 로드
- **캐싱**: 파싱 결과 캐싱 (향후 구현)
- **배치 처리**: 여러 파일 동시 처리 (향후 구현)

## 보안 고려사항

- **API 키 암호화**: `cryptography` 사용
- **파일 권한**: `.manifest/.key` 파일은 소유자만 읽기 가능
- **입력 검증**: 사용자 입력 검증 및 샌드박싱

## 참고 문서

- `IMPLEMENTATION_SUMMARY.md`: 구현 요약
- `reference/implementation_plan.md`: 원본 구현 계획
- `README.md`: 사용자 가이드
- `DEV_SETUP.md`: 개발 환경 설정
