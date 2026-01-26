# Manifest 코드 리뷰 - 리팩토링 관점
**Review Date**: 2025-01-27 14:30:00

## 프로젝트 통계

- **총 Python 파일**: 58개
- **총 코드 라인**: 16,458줄
- **평균 파일 크기**: ~284줄
- **디렉토리 구조**: 11개 주요 디렉토리

### 큰 파일 Top 4
1. **`ui/app.py`**: 1,584줄, 35개 메서드 ⚠️
2. **`agents/agent_coordinator.py`**: 883줄, 23개 메서드 ⚠️
3. **`audit/code_extractor.py`**: 664줄
4. **`core/state_manager.py`**: 643줄

## 1. 디렉토리 구조 및 모듈 분리

### ✅ 잘 구성된 부분

#### 명확한 패키지 분리
```
src/manifest/
├── core/          # 핵심 기능 (config, state, settings)
├── ui/            # UI 관련 (app, widgets, settings)
├── agents/        # 에이전트 시스템 (coordinator, context, scoping)
├── bridge/        # 브리지 패턴 (agent_bridge)
├── audit/         # 감사 및 검증 (drift, blueprint, structure)
└── runtime/       # 런타임 (agent, hooks, router, shadow)
```

**장점**:
- 관심사 분리가 명확함
- 각 패키지의 책임이 분명함
- `src/` 레이아웃 사용으로 표준 구조 준수

### ⚠️ 개선 필요 사항

#### 1. `runtime/agent/` 디렉토리 구조
**현재 상태**:
- 모든 Agent 클래스가 한 디렉토리에 있음
- Agent별로 하위 디렉토리 분리 없음

**개선 방안**:
```
runtime/agent/
├── base/              # BaseAgent, AgentExecutor
├── orchestrator/      # OrchestratorAgent, OrchestratorPrompt
├── planner/           # PlannerAgent, PlannerPrompt
├── coder/            # CoderAgent, CoderPrompt
├── test/             # TestAgent, IntegrationTestAgent, E2ETestAgent
├── review/           # ApproverAgent, ProjectReviewAgent
└── debug/            # DebugAgent
```

#### 2. `ui/widgets/` vs `ui/widgets.py` 혼재
**현재 상태**:
- `ui/widgets/` 디렉토리와 `ui/widgets.py` 파일이 공존
- 일부 위젯은 디렉토리, 일부는 파일

**개선 방안**:
- 모든 위젯을 `ui/widgets/` 디렉토리로 통일
- 각 위젯을 별도 파일로 분리

#### 3. `audit/` 패키지의 책임 과다
**현재 상태**:
- `audit/`에 너무 많은 책임 (drift, blueprint, structure, file_watcher, code_extractor)

**개선 방안**:
```
audit/                 # 감사 (drift, comparison)
blueprint/            # Blueprint 관리 (metadata, synchronizer, comparator)
structure/            # 구조 분석 (code_extractor, file_watcher, structure_manager)
```

---

## 2. 코드 중복 및 재사용성

### ⚠️ 발견된 중복

#### 1. 중복 Import
**위치**: `src/manifest/ui/app.py`
```python
# Line 11-13
from manifest.ui.widgets.structure_hierarchy_view import StructureHierarchyView
from manifest.ui.widgets.structure_graph_view import StructureGraphView
from manifest.ui.widgets.project_view import TaskTreeView, SprintStatusView, HistoryView

# Line 24-26 (중복!)
from manifest.ui.widgets.structure_hierarchy_view import StructureHierarchyView
from manifest.ui.widgets.structure_graph_view import StructureGraphView
from manifest.ui.widgets.project_view import TaskTreeView, SprintStatusView, HistoryView
```

**개선**: 중복 import 제거 (Line 24-26 삭제)

#### 1-1. process_command 메서드의 거대한 if-elif 체인
**위치**: `src/manifest/ui/app.py` (Line 886-1256, 약 370줄)
**문제점**:
- 단일 메서드에 20+ 개의 명령 처리 로직
- 가독성 저하
- 테스트 어려움
- 확장성 문제

**개선 방안**:
```python
# ui/commands/command_handler.py
class CommandHandler:
    def __init__(self, app: ManifestApp):
        self.app = app
        self.handlers = {
            "audit": self._handle_audit,
            "reload": self._handle_reload,
            "status": self._handle_status,
            "create_task": self._handle_create_task,
            # ...
        }
    
    async def handle(self, command: str, args: List[str], log: RichLog):
        handler = self.handlers.get(command)
        if handler:
            await handler(args, log)
        else:
            log.write(f"[bold red]Unknown command: {command}[/]")
```

#### 1-2. 명령 파싱 로직 중복
**위치**: `process_command` 메서드 내
**문제점**:
- 각 명령마다 `user_input.split()` 반복
- 파라미터 파싱 로직 중복

**개선 방안**:
```python
# ui/commands/command_parser.py
class CommandParser:
    @staticmethod
    def parse(user_input: str) -> Tuple[str, List[str]]:
        """Parse command and arguments."""
        parts = user_input[1:].split() if user_input.startswith("/") else []
        command = parts[0] if parts else ""
        args = parts[1:] if len(parts) > 1 else []
        return command, args
```

#### 2. Blueprint 로딩 로직 중복
**위치**: 여러 파일에서 반복
- `structure_manager.py`: `_load_blueprint()`, `_load_code_blueprint()`
- `drift_auditor.py`: `_load_blueprint()`
- `context_provider.py`: `_load_tier_2_scoped()` 내부에서 Blueprint 로딩
- `task_scoper.py`: `_load_data()` 내부에서 Blueprint 로딩

**구체적 중복 코드**:
```python
# structure_manager.py (Line 748)
def _load_blueprint(self) -> Dict[str, Any]:
    blueprint_file = self.manifest_dir / "blueprint.json"
    if not blueprint_file.exists():
        return {"components": [], "contracts": []}
    with open(blueprint_file, "r") as f:
        return json.load(f)

# drift_auditor.py (Line 49)
def _load_blueprint(self):
    blueprint_file = self.manifest_dir / "blueprint.json"
    if blueprint_file.exists():
        with open(blueprint_file, "r") as f:
            self._blueprint_data = json.load(f)
    else:
        self._blueprint_data = {"components": [], "contracts": []}
```

**개선 방안**:
```python
# audit/blueprint_loader.py
class BlueprintLoader:
    """Centralized Blueprint loading utility."""
    
    @staticmethod
    def load_blueprint(manifest_dir: Path, with_metadata: bool = False) -> Dict[str, Any]:
        """Load blueprint.json with optional metadata."""
        blueprint_file = manifest_dir / "blueprint.json"
        if not blueprint_file.exists():
            return {"version": "1.0", "components": [], "contracts": [], "zones": {}}
        
        with open(blueprint_file, "r") as f:
            data = json.load(f)
        
        if with_metadata:
            from manifest.audit.blueprint_metadata import load_blueprint_with_metadata
            return load_blueprint_with_metadata(blueprint_file, "llm_design", False)
        
        return data
    
    @staticmethod
    def load_code_blueprint(manifest_dir: Path) -> Dict[str, Any]:
        """Load blueprint_code.json."""
        code_blueprint_file = manifest_dir / "blueprint_code.json"
        if not code_blueprint_file.exists():
            return {"components": [], "contracts": []}
        
        with open(code_blueprint_file, "r") as f:
            return json.load(f)
```

#### 3. Sprint 데이터 로딩/저장 중복
**위치**: 여러 Agent 파일
- `e2e_test_agent.py`: `load_sprint()`, `save_sprint()` 반복 (5회 이상)
- `integration_test_agent.py`: 동일한 패턴 반복 (5회 이상)
- `agent_coordinator.py`: Sprint 로딩/저장 반복

**구체적 중복 코드**:
```python
# e2e_test_agent.py (여러 곳)
sprint_data = self.state_manager.load_sprint(sprint_id)
# ... 수정 ...
self.state_manager.save_sprint(sprint_data)

# integration_test_agent.py (여러 곳)
sprint_data = self.state_manager.load_sprint(sprint_id)
# ... 수정 ...
self.state_manager.save_sprint(sprint_data)
```

**개선 방안**:
```python
# core/sprint_manager.py
class SprintManager:
    """Manages Sprint data with business logic."""
    
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
    
    def load_sprint(self, sprint_id: str) -> Optional[Dict[str, Any]]:
        """Load sprint with validation."""
        return self.state_manager.load_sprint(sprint_id)
    
    def update_sprint_tests(
        self,
        sprint_id: str,
        test_type: str,  # "integration" or "e2e"
        status: str,
        test_files: List[str] = None,
        test_plan: str = None
    ) -> bool:
        """Update sprint test data."""
        sprint_data = self.load_sprint(sprint_id)
        if not sprint_data:
            return False
        
        test_key = f"{test_type}_tests"
        if test_key not in sprint_data:
            sprint_data[test_key] = {}
        
        sprint_data[test_key]["status"] = status
        if test_files:
            sprint_data[test_key]["test_files"] = test_files
        if test_plan:
            sprint_data[test_key]["test_plan"] = test_plan
        
        return self.state_manager.save_sprint(sprint_data)
```

#### 4. 에러 처리 패턴 중복
**현재 상태**:
- 모든 파일에서 `try-except` + `print()` 패턴 반복

**개선 방안**:
- 통합 로깅 시스템 도입
- 에러 핸들러 유틸리티 생성

---

## 3. 의존성 관리

### ✅ 잘 처리된 부분

#### Lazy Import 패턴
**위치**: `src/manifest/agents/__init__.py`, `agent_bridge.py`
```python
# Lazy import to avoid circular dependencies
from manifest.agents.resource_monitor import ResourceMonitor
```

**장점**: 순환 의존성 방지

### ⚠️ 개선 필요 사항

#### 1. 순환 의존성 위험
**위치**: 여러 파일
- `AgentBridge` → `AgentCoordinator` → `AgentBridge` (간접적)
- `StateManager` → 여러 Agent → `StateManager`

**개선 방안**:
- 의존성 주입(DI) 패턴 강화
- 인터페이스/프로토콜 도입
- 이벤트 기반 통신 고려

#### 2. 강한 결합도
**현재 상태**:
- `ManifestApp`이 너무 많은 클래스에 직접 의존
- `AgentCoordinator`가 `AgentBridge`의 내부 구조에 의존

**개선 방안**:
- 의존성 역전 원칙(DIP) 적용
- 인터페이스 추상화
- 이벤트 버스 패턴 고려

#### 3. 전역 상태 사용
**현재 상태**:
- `StateManager`가 여러 곳에서 직접 인스턴스화
- 설정 파일이 여러 곳에서 직접 로드

**개선 방안**:
- 싱글톤 패턴 또는 의존성 주입 컨테이너
- 설정 관리자 통합

---

## 4. 코드 품질

### ⚠️ 주요 문제점

#### 1. 로깅 시스템 부재
**현재 상태**:
- 모든 파일에서 `print()` 사용 (137개 발견)
- 로그 레벨 구분 없음
- 로그 포맷팅 없음
- 파일 로깅 없음

**개선 방안**:
```python
# src/manifest/core/logger.py 생성
import logging
from pathlib import Path

def setup_logger(name: str, log_file: Path = None) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
    
    return logger
```

**마이그레이션**:
- 모든 `print()` → `logger.info()`, `logger.error()` 등으로 변경
- 에러는 `logger.error()` 또는 `logger.exception()`

#### 2. 타입 힌트 불완전
**현재 상태**:
- 일부 함수에만 타입 힌트 존재
- `Dict[str, Any]` 남용
- Optional 타입 명시 부족

**개선 방안**:
- `mypy` 도입 및 타입 체크
- TypedDict 사용으로 구조화된 딕셔너리 타입 정의
- Protocol 사용으로 인터페이스 정의

#### 3. 에러 처리 불일치
**현재 상태**:
- 일부는 예외를 잡아서 print만 함
- 일부는 예외를 다시 raise
- 일부는 None을 return

**개선 방안**:
- 커스텀 예외 클래스 정의
- 에러 처리 전략 통일
- Result/Either 패턴 고려

#### 4. 매직 넘버/문자열
**현재 상태**:
- 하드코딩된 값들 (예: `max_debug_iterations = 5`, `sync_interval = 5.0`)

**개선 방안**:
- 상수 파일 생성 (`src/manifest/core/constants.py`)
- 설정 파일로 이동 가능한 값들은 설정으로

---

## 5. 큰 파일/클래스 분리

### 🔴 Critical: ManifestApp 클래스

**현재 상태**:
- **파일 크기**: ~1,535줄
- **메서드 수**: 50+ 개
- **책임**: UI 렌더링, 명령 처리, Agent 통신, 데이터 로딩, 상태 관리 등

**문제점**:
- 단일 책임 원칙(SRP) 위반
- 테스트 어려움
- 유지보수 어려움

**개선 방안**:
```
ui/
├── app.py                    # Main App (200줄 이하)
├── commands/                # 명령 처리
│   ├── command_handler.py   # 명령 라우팅
│   ├── task_commands.py     # Task 관련 명령
│   ├── sprint_commands.py    # Sprint 관련 명령
│   └── agent_commands.py    # Agent 관련 명령
├── data/                    # 데이터 로딩
│   ├── data_loader.py       # 데이터 로딩 로직
│   └── data_refresher.py    # 데이터 새로고침
└── channels/                 # 채널 관리
    ├── channel_manager.py   # 채널 관리 로직
    └── channel_history.py   # 히스토리 관리
```

**리팩토링 전략**:
1. Command Handler 패턴 도입
2. Data Loader 분리
3. Channel Manager 분리
4. Event-driven 아키텍처 고려

### 🔴 Critical: AgentCoordinator 클래스

**현재 상태**:
- **파일 크기**: ~884줄
- **메서드 수**: 30+ 개
- **책임**: Agent 조정, Worker Squad 실행, Sprint 관리, Container 통신 등

**개선 방안**:
```
agents/
├── coordinator/
│   ├── agent_coordinator.py      # 메인 Coordinator (200줄 이하)
│   ├── worker_squad_executor.py  # Worker Squad 실행 로직
│   ├── sprint_manager.py         # Sprint 관리
│   └── stage_executor.py         # 각 Stage 실행 로직
```

### 🟡 Medium: StateManager 클래스

**현재 상태**:
- **파일 크기**: ~644줄
- **책임**: State 관리, PRD 관리, Sprint 관리, Task 관리, Chat 관리

**개선 방안**:
```
core/
├── state/
│   ├── state_manager.py      # 메인 StateManager (200줄 이하)
│   ├── prd_manager.py        # PRD 관리
│   ├── sprint_manager.py     # Sprint 관리
│   ├── task_manager.py       # Task 관리
│   └── chat_manager.py       # Chat 관리
```

### 🟡 Medium: CodeExtractor 클래스

**현재 상태**:
- **파일 크기**: ~659줄
- **책임**: AST 파싱, Component 추출, Contract 추출, Blueprint 생성

**개선 방안**:
```
structure/
├── extractor/
│   ├── code_extractor.py     # 메인 Extractor
│   ├── ast_parser.py         # AST 파싱 로직
│   ├── component_extractor.py # Component 추출
│   ├── contract_extractor.py # Contract 추출
│   └── blueprint_generator.py # Blueprint 생성
```

---

## 6. 테스트 구조

### ✅ 잘 구성된 부분

- 테스트 파일이 `tests/` 디렉토리에 분리
- 각 모듈별 테스트 파일 존재

### ⚠️ 개선 필요 사항

#### 1. 테스트 커버리지
**현재 상태**:
- Core: ~80%
- UI: ~60%
- Overall: ~70%

**개선 방안**:
- UI 테스트 커버리지 향상
- 통합 테스트 추가
- E2E 테스트 추가

#### 2. 테스트 파일 구조
**개선 방안**:
```
tests/
├── unit/
│   ├── core/
│   ├── agents/
│   ├── audit/
│   └── runtime/
├── integration/
│   ├── test_agent_workflow.py
│   └── test_ui_integration.py
└── e2e/
    └── test_full_workflow.py
```

---

## 7. 설정 관리

### ⚠️ 개선 필요 사항

#### 1. 설정 파일 분산
**현재 상태**:
- `.manifest/keys.json`
- `.manifest/agent_config.json`
- `.manifest/spec_first_settings.json`
- `.manifest/shadow_settings.json`
- `.claude/rules/manifest-policy.md`
- `AGENTS.md`

**개선 방안**:
- 설정 파일 통합 또는 명확한 분리 기준
- 설정 스키마 정의
- 설정 검증 로직

#### 2. 환경 변수 관리
**개선 방안**:
- `.env` 파일 지원
- 환경별 설정 (dev, prod)
- 설정 우선순위 명확화

---

## 8. 문서화

### ✅ 잘 구성된 부분

- 각 모듈에 docstring 존재
- `docs/` 디렉토리에 상세 문서

### ⚠️ 개선 필요 사항

#### 1. 타입 힌트와 docstring 불일치
**개선 방안**:
- 타입 힌트를 docstring과 일치시키기
- Sphinx 또는 mkdocs로 API 문서 자동 생성

#### 2. 아키텍처 다이어그램 부족
**개선 방안**:
- 모듈 간 의존성 다이어그램
- 데이터 흐름도
- 시퀀스 다이어그램

---

## 우선순위별 리팩토링 계획

### High Priority (즉시)

1. **로깅 시스템 도입**
   - 모든 `print()` → `logger`로 변경 (137개 발견)
   - 로그 레벨 및 포맷 설정
   - 파일 로깅 추가
   - **예상 작업량**: 2-3시간

2. **ManifestApp 클래스 분리**
   - Command Handler 분리 (370줄의 if-elif 체인)
   - Data Loader 분리
   - Channel Manager 분리
   - **예상 작업량**: 4-6시간

3. **중복 import 제거** ✅ (즉시 적용 가능)
   - `app.py`의 중복 import 정리 (Line 24-26)
   - **예상 작업량**: 5분

4. **Blueprint 로딩 로직 통합**
   - `BlueprintLoader` 유틸리티 생성
   - 4개 파일에서 중복 제거
   - **예상 작업량**: 1-2시간

5. **process_command 메서드 리팩토링**
   - Command Handler 패턴 도입
   - 명령 파서 분리
   - **예상 작업량**: 2-3시간

### Medium Priority (단기)

5. **AgentCoordinator 클래스 분리**
   - Worker Squad Executor 분리
   - Sprint Manager 분리

6. **타입 힌트 강화**
   - `mypy` 도입
   - TypedDict 사용

7. **에러 처리 통일**
   - 커스텀 예외 클래스
   - 에러 처리 전략 통일

8. **StateManager 분리**
   - 각 Manager 클래스로 분리

### Low Priority (중기)

9. **디렉토리 구조 개선**
   - `runtime/agent/` 하위 구조화
   - `audit/` 패키지 분리

10. **테스트 구조 개선**
    - unit/integration/e2e 분리
    - 커버리지 향상

11. **설정 관리 개선**
    - 설정 파일 통합
    - 환경 변수 지원

---

## 리팩토링 원칙

1. **점진적 리팩토링**: 한 번에 하나씩, 테스트와 함께
2. **기능 유지**: 리팩토링 중 기능 변경 없음
3. **테스트 우선**: 리팩토링 전 테스트 작성/확인
4. **작은 단위**: 작은 변경을 자주 커밋

---

## 결론

Manifest 프로젝트는 **기능적으로는 잘 구현**되어 있으나, **코드 구조와 품질 측면에서 개선이 필요**합니다.

**주요 문제점**:
1. 🔴 큰 클래스들 (ManifestApp, AgentCoordinator)
2. 🔴 로깅 시스템 부재
3. 🟡 코드 중복 (Blueprint 로딩, Sprint 관리)
4. 🟡 타입 힌트 불완전
5. 🟡 에러 처리 불일치

**강점**:
- ✅ 명확한 패키지 구조
- ✅ Lazy import로 순환 의존성 방지
- ✅ 테스트 구조 존재

**다음 단계**: High Priority 항목부터 순차적으로 리팩토링 진행 권장.
