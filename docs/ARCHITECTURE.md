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

#### 4. OMOC Bridge
- **omoc_bridge.py**: IPC 파이프 엔진
- JSON 기반 메시지 프로토콜
- 비동기 메시지 처리
- 명령 인터페이스: `start_mission()`, `get_status()`, `promote_task()`

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

#### 7. TUI Application
- **app.py**: 완전한 5-뷰 워크스페이스
  - **View 1: Architect (의도)**: `intent.json` 렌더링
  - **View 2: Blueprint (설계)**: `blueprint.json` 렌더링
  - **View 3: Inspector (검증)**: 3가지 모드 (Visual/Data/Drift)
  - **View 4: Mission Control**: 작업 트리 및 승인 게이트
  - **View 5: History**: Git 타임라인 통합
- 멀티 채널 채팅 시스템
- 실시간 상태 업데이트
- 명령 처리 (`/audit`, `/reload`, `/status`)

#### 8. Testing
- **tests/**: 완전한 테스트 스위트
  - `test_state_manager.py`: 상태 영속성 테스트
  - `test_drift_auditor.py`: 드리프트 감지 테스트
  - `test_bridge.py`: OMOC 브리지 프로토콜 테스트
  - `test_app.py`: 통합 테스트
  - `test_app_input.py`: 입력 처리 테스트

### ⏳ 미구현 기능 (향후 구현 예정)

1. **Full Multi-Agent Squad System**
   - Prometheus (Planner), Sisyphus (Coder) 등 에이전트 통합
   - 에이전트 간 협업 메커니즘

2. **Enhanced OMOC Protocol**
   - 완전한 OMOC 프로토콜 구현
   - Shadow Manager (샌드박스 운영)

3. **Advanced Drift Resolution**
   - 자동 드리프트 해결
   - 구조적 제안 시스템

4. **Context Injection Hooks**
   - 에이전트 프롬프트 가로채기
   - Visual Reality 업데이트 주입

5. **Structural Spec-First Management**
   - Blueprint 기반 파일 시스템 관리
   - 구조적 변경 제안 시스템

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
│ State Manager│ │OMOC Bridge │ │Drift Auditor│
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
            │   OMOC Process      │
            │  (External)         │
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

#### `omoc_bridge.py` - OMOC Integration
- **책임**: OMOC 프로세스와의 IPC 통신
- **의존성**: `state_manager`
- **주요 클래스**: `OMOCBridge`
- **주요 메서드**:
  - `start()`: OMOC 프로세스 시작
  - `send_message()`: 메시지 전송
  - `start_mission()`: 미션 시작
  - `promote_task()`: 작업 승격

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
   ├─> OMOCBridge.start() 연결 시도
   ├─> Intent/Blueprint 데이터 로드
   ├─> 각 뷰 업데이트
   └─> DriftAuditor.audit_project() 실행
```

### 2. 사용자 입력 처리 흐름
```
1. 사용자 입력 (Enter)
   ├─> on_input_submitted()
   │   ├─> 입력 클리어
   │   ├─> StateManager.add_chat_message()
   │   └─> process_command()
   │       ├─> 명령 파싱 (/audit, /reload, etc.)
   │       ├─> OMOCBridge 통신 (선택적)
   │       └─> 상태 저장
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
├── omoc_bridge.py            # OMOC IPC 브리지
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
- **Business Logic Layer**: `state_manager.py`, `omoc_bridge.py`, `drift_auditor.py`
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
- OMOC 브리지는 선택적 (독립 실행 모드 지원)
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
- **httpx**: HTTP 클라이언트 (API 검증)
- **pytest**: 테스트 프레임워크

## 향후 개선 사항

### 단기 (Phase 2)
1. **Full OMOC Integration**: 완전한 OMOC 프로토콜 구현
2. **Multi-Agent System**: 에이전트 스쿼드 시스템
3. **Enhanced Drift Resolution**: 자동 드리프트 해결

### 중기 (Phase 3)
1. **Context Injection**: 에이전트 프롬프트 가로채기
2. **Structural Management**: Blueprint 기반 파일 시스템 관리
3. **Shadow Manager**: 샌드박스 운영 및 안전한 승격

### 장기 (Phase 4)
1. **Visual Editor**: Blueprint 시각적 편집
2. **Real-time Collaboration**: 다중 사용자 협업
3. **Plugin System**: 확장 가능한 플러그인 아키텍처

## 테스트 커버리지

현재 테스트는 다음을 포함합니다:
- ✅ 상태 관리 테스트
- ✅ 드리프트 감지 테스트
- ✅ OMOC 브리지 프로토콜 테스트
- ✅ 통합 테스트
- ✅ 입력 처리 테스트

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