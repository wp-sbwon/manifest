# 기능 누락 및 다음에 할 일 (코드베이스 기준)

**최종 업데이트**: 2026-01-28
**기준**: 문서 의존 없이, 실제 코드·설정·데이터만 보고 정리함.

**중요**: 이 문서는 실제 코드 상태를 기준으로 작성됩니다. 문서의 "미구현" 표기는 신뢰하지 않습니다.

---

## 1. 즉시 고칠 것 (버그/불일치)

### 1.1 `/start_task` 명령 없음 ✅ **구현 완료**
- **상황**: UI 로그에 `Use /start_task <task_id> to start worker squad` 안내가 있음.
- **사실**: `CommandHandler`에 `/start_task`가 **이미 구현되어 있음** (`command_handler.py:153-178`).
- **구현 위치**: `src/manifest/ui/commands/command_handler.py:_handle_start_task()`
- **처리 내용**: `agent_coordinator._start_task_worker_squad(task_id)` 호출하여 Worker Squad 전체 플로우 실행.

### 1.2 OpenCode 터미널 실행: 실제 미구현
- **상황**: `opencode_adapter._execute_with_opencode`가 플레이스홀더라, 항상 `_execute_internal`로 폴백.
- **사실**: OpenCode 터미널 라우터 연동 없음. LLM용 OpenCode 어댑터(`opencode_llm_adapter`)와 별개.
- **영향**: 터미널 명령 실행은 어디서나 “internal”만 사용. OpenCode 터미널 기능 미사용.
- **반영 완료**: `opencode_adapter.py` 모듈 docstring에 “이름은 확장 포인트, 현재는 internal 전용” 명시.
- **남은 일**: OpenCode 터미널 API가 정의되면 `_execute_with_opencode`에 실제 연동 구현.

### 1.3 `settings.json` 기본 부재
- **상황**: `get_setting()`은 `.manifest/settings.json`만 봄. 해당 파일이 없으면 전부 default.
- **사실**: `agent.execution_backend`, `opencode.*` 등이 전부 default 값으로만 동작.
- **설계**: **OpenCode가 기본(default) 백엔드**임. `agent.execution_backend` 미설정 시 "opencode" 사용.
- **반영 완료**: `ConfigManager._ensure_default_settings()`로 최초 사용 시 `settings.json`에 템플릿(agent.execution_backend, opencode.*) 생성.
- **영향**:
  - OpenCode 미설치/미실행이면 `opencode serve` 실패로 LLM 불가.
  - 그때는 사용자가 `.manifest/settings.json`에서 `agent.execution_backend`를 `"direct"`로 수정해 전환 가능.

---

## 2. 설정/진입점 정리

### 2.1 실행 백엔드
- **설계**: **OpenCode가 기본(default)**. `ExecutorFactory` 기본값 `"opencode"` 유지.
- **선택**: OpenCode를 쓰지 않을 때만 `settings.json`에 `agent.execution_backend: "direct"`로 수동 설정. 자동 폴백(direct)은 하지 않음.

### 2.2 Bootstrap UI
- **현재**: API 키만 설정. `settings.json` / `agent_config` 스크린 없음.
- **선택**:
  - 설정 화면에서 execution backend, opencode 옵션 등을 편집할 수 있게 하거나,
  - 최소한 `settings.json` 예시를 docs에 두고, “이걸 .manifest에 복사해 쓰라”고 안내.

### 2.3 `intent.json` / `project.json` 비어 있음
- **현재**:
  - `intent.json`: `version`, `sprint`, `features` 구조만 있고 대부분 비어 있음.
  - `project.json`: `docs/project-manifest/project.json`만 존재, `.manifest/project.json` 없음.
- **영향**:
  - Architect/Feature 트리, progress 등이 “No features defined” 위주.
  - `load_project_data`는 .manifest 쪽 project가 없으면 빈 dict.
- **선택**:
  - “빈 상태로도 앱 기동”은 유지하되,
  - Intent/Project 편집 UI 또는 `/` 명령으로 features/project 메타를 채울 수 있게 하는 건 별도 기능 검토.

---

## 3. 플로우/기능 누락

### 3.1 스프린트 생성 명령 ✅ **구현 완료**
- **현재**: `/create_sprint` 명령이 **이미 구현되어 있음** (`command_handler.py:315-343`).
- **구현 위치**: `src/manifest/ui/commands/command_handler.py:_handle_create_sprint()`
- **기능**: `/create_sprint <name> [task_id ...]` 형식으로 스프린트 생성 및 테스크 연결 지원.

### 3.2 스프린트 ↔ 테스크 연결
- **현재**: `create_task`에 `sprint_id` 인자 있음. `/create_task`로 스프린트 지정 가능.
- **부족한 점**:
  - 스프린트 생성 시 기존 테스크를 한 번에 묶는 흐름이 불명확.
  - “이 스프린트에 테스크 추가” 하는 명령도 없음.
- **제안**:
  - `/create_sprint` 설계 시 “생성 시 테스크 목록 지정” 또는
  - `/add_task_to_sprint <sprint_id> <task_id>` 같은 오퍼레이션 검토.

### 3.3 Worker Squad 완료 감지
- **현재**: `start_worker_agent_and_wait`가 `active_agents`, bridge `_active_agents`, executor `active_sessions`, `get_agent_status`, 채널 히스토리 등으로 완료 여부 폴링.
- **위험**:
  - 조건이 많고, 채널/세션 업데이트 타이밍에 따라 “완료로 안 보이는” 경우 가능성.
  - 실제로 이전에 `test_message_routing_creates_channel_if_missing`, `test_real_time_drift_detection_file_deletion` 등이 로컬/CI 차이로 실패한 적 있음.
- **제안**:
  - 완료 신호를 더 명시적으로 (예: 이벤트/메시지 한 종류) 정하고,
  - “완료” 판단 경로 단순화 및 테스트 보강.

---

## 4. 우선순위 제안 (실제 남은 작업)

### ✅ 완료된 항목 (2026-01-28 확인)
- ✅ `/start_task` 명령 구현 완료
- ✅ `settings.json` 최초 생성/템플릿 구현 완료
- ✅ OpenCode 터미널 adapter 현황 주석/문서화 완료
- ✅ `/create_sprint` 및 스프린트–테스크 연결 구현 완료
- ✅ Worker Squad 완료 감지 로직 개선 완료
- ✅ Multi-Agent Workflow 완전 구현 (Event-driven 모드)
- ✅ Context Injection Hooks 완전 구현
- ✅ Container Communication 완전 구현
- ✅ Shadow Manager 완전 구현

### 🔴 실제 남은 작업 (우선순위 순)

| 우선순위 | 항목 | 상태 | 비고 |
|----------|------|------|------|
| P1 | Structural Spec-First Management 완성 | ✅ 구현 완료 | add_method, add_class, add_import 구현 완료 (2026-01-28) |
| P2 | Bootstrap UI 문제 해결 | ⚠️ 이슈 있음 | 이벤트 루프 충돌, 현재는 데모 모드 |
| P3 | OpenCode 터미널 adapter 구현 | ⚠️ 선택적 | OpenCode 터미널 API 정의되면 구현 |
| P4 | UI 개선 (병렬 실행 표시) | ⚠️ 부분 완료 | WorkflowVisualization에서 병렬 stage 더 명확히 표시 |
| P5 | `/add_task_to_sprint` 명령 추가 | ❌ 미구현 | 스프린트에 테스크 추가하는 명령 |

---

## 5. 참고: 이미 갖춰진 것

- **에이전트 실행**: direct 모드 시 `ExecutorFactory` → `AgentExecutor`, API 키만 있으면 LLM 호출 가능.
- **Worker Squad 플로우**: planner → tdd_test → coder → test → debug → self_review → approver 순서로 `WorkerSquadExecutor`가 단일 테스크 실행.
- **오케스트레이터 → 테스크 생성**: `_process_orchestrator_response`에서 패턴/JSON 파싱으로 테스크 이름 추출 후 `create_task` 호출. 자동 start는 “start/execute/begin” 등 키워드 있을 때만.
- **설정**: `agent_config.json`으로 모델·퍼미션·스킬, `keys`(암호화)로 API 키. `get_setting`만 `settings.json` 사용.
- **상태**: `state.json` (task_checklist, mission_tree, chat_history), `.manifest/sprints/` (스프린트별 JSON).

---

*문서 의존하지 않고 코드·설정만 기준으로 정리함. 구현 시에는 테스트 및 CI 규칙(.cursor/rules, check_ci_status 등)을 유지할 것.*
