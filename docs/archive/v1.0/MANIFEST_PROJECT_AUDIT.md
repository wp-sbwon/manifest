# Manifest 프로젝트 전체 점검 보고서

**점검일**: 코드베이스·테스트·CI 기준으로 작성
**목적**: 완료된 기능, 존재하는 기능, 정상 동작 여부를 한 문서에서 파악

---

## 1. 테스트 현황

| 구분 | 결과 | 비고 |
|------|------|------|
| **전체** | 1136 passed, 6 skipped | `pytest tests/` 기준 |
| **수집 테스트 수** | 1142 collected | unit + integration + e2e |
| **통과률** | 1136/1142 (99.5%) | skip은 OpenCode 서버 미기동 등 조건부 |
| **CI** | `.github/workflows/test.yml` | push/PR 시 pytest, Python 3.9/3.10/3.11, timeout 300s |
| **로컬 검사** | `scripts/check_ci_status.py` | 푸시 전 CI 동일 테스트 실행 (규칙: `.cursor/rules/ci-before-commit-push.mdc`) |

**스킵 원인**: `tests/integration/test_opencode_integration.py` 등 OpenCode 서버 필요 시 `skipif`로 스킵.

---

## 2. 진입점·앱 기동

| 항목 | 상태 | 설명 |
|------|------|------|
| **실행 방법** | ✅ | `PYTHONPATH=src python -m manifest` |
| **진입점** | `src/manifest/__main__.py` | `get_config_manager()` → 키 없으면 `run_bootstrap()` → `ManifestApp().run()` |
| **앱 클래스** | `ManifestApp` (Textual `App` 상속) | `src/manifest/ui/app.py` |
| **부트스트랩** | `run_bootstrap()` | API 키 미설정 시 키 설정 UI 실행 후 본 앱 진입 |

**정상 동작**: Config 로드·키 검사·앱 생성·Textual `run()` 호출까지 경로 존재. 실제 UI는 로컬 실행으로만 검증 가능.

---

## 3. 슬래시 명령 (/) — 등록된 기능

`CommandHandler`에 등록된 명령 **30개**. 아래는 전부 현재 구현된 핸들러와 1:1 대응.

| 명령 | 기능 요약 |
|------|------------|
| `/audit` | 드리프트 감사 실행 |
| `/reload` | intent/blueprint/project 리로드 및 뷰 갱신 |
| `/status` | 상태 출력 |
| `/start_agent` | 워커 에이전트 기동 (task_id, agent_type) |
| `/start_task` | 테스크 Worker Squad 전체 플로우 기동 |
| `/stop_agent` | 에이전트 정지 |
| `/sync_blueprints` | 블루프린트 동기화 |
| `/resolve_conflict` | 블루프린트 충돌 해결 |
| `/config` | 설정 관련 |
| `/sprint_history` | 스프린트 이력 |
| `/orchestrator` | 오케스트레이터 채팅 화면 |
| `/create_task` | 테스크 생성 (name, description, stage, status, sprint_id) |
| `/create_sprint` | 스프린트 생성 및 선택 테스크 연결 |
| `/update_task` | 테스크 수정 (name, description, status, stage, sprint_id) |
| `/delete_task` | 테스크 삭제 |
| `/list_tasks` | 테스크 목록 (필터: status, stage, sprint) |
| `/approve_sprint` | 스프린트 승인 UI |
| `/start_sprint` | 스프린트 기동 (에이전트 coordinator 연동) |
| `/apply_blueprint_updates`, `/apply_blueprint_update` | 블루프린트 적용 |
| `/apply_code_changes`, `/apply_code_change` | 코드 변경 적용 |
| `/shadow_status`, `/shadow_stop` | 섀도우 실행 제어 |
| `/git_status`, `/git_log`, `/git_commit`, `/git_push`, `/git_pull`, `/git_rollback` | Git 관련 |

**정상 동작**: 각 명령은 `_handle_*`에 매핑되어 있으며, 단위/통합 테스트에서 라우팅·실행이 검증됨.

---

## 4. 핵심 기능별 상태

### 4.1 에이전트·실행 백엔드

| 기능 | 상태 | 비고 |
|------|------|------|
| **실행 백엔드** | ✅ | `ExecutorFactory`: `"opencode"`(기본), `"direct"` |
| **OpenCode LLM** | ✅ | `OpenCodeLLMAdapter` — HTTP API(`opencode serve`), 세션·프롬프트·스트리밍 구현 |
| **Direct LLM** | ✅ | `AgentExecutor` — API 키로 직접 LLM 호출 |
| **기본값** | ✅ | `agent.execution_backend` 미설정 시 `"opencode"` (코드·설정 일치) |

### 4.2 OpenCode 터미널

| 기능 | 상태 | 비고 |
|------|------|------|
| **터미널 실행** | ✅ 동작 | `OpenCodeAdapter` → 현재는 **항상 internal subprocess** |
| **OpenCode 터미널 API** | ❌ 미연동 | `_execute_with_opencode`는 플레이스홀더, 주석·문서로 명시됨 |

### 4.3 Worker Squad·오케스트레이션

| 기능 | 상태 | 비고 |
|------|------|------|
| **Worker Squad 단계** | ✅ | planner → tdd_test → coder → test → debug → self_review → approver |
| **WorkerSquadExecutor** | ✅ | 순차/이벤트 기반 실행, 스테이지 완료·실패 처리 |
| **완료 감지** | ✅ 정리됨 | `start_worker_agent_and_wait`: 1) active_agents 제거 2) bridge completed/status 3) get_agent_status 4) 채널 마커. docstring·테스트 추가됨 |
| **오케스트레이터** | ✅ | 채팅·응답 파싱·테스크 생성·자동 start 키워드 처리 |
| **스프린트 실행** | ✅ | `SprintExecutor.start_sprint`, TDD·통합·e2e 테스트 에이전트 연동 |

### 4.4 에이전트 타입 (런타임)

| 타입 | 모듈 | 용도 |
|------|------|------|
| planner | `planner_agent.py` | 계획 수립 |
| tdd_test | (test_agent 등) | TDD 테스트 작성/실행 |
| coder | `coder_agent.py` | 구현 |
| test | `test_agent.py` | 테스트 실행 |
| debug | `debug_agent.py` | 디버깅 |
| self_review | (coder 셀프 리뷰) | 자기 검토 |
| approver | `approver_agent.py` | 승인 |
| orchestrator | `orchestrator_agent.py` | 오케스트레이션·스프린트 플랜 |
| integration_test | `integration_test_agent.py` | 통합 테스트 |
| e2e_test | `e2e_test_agent.py` | E2E 테스트 |
| project_review | `project_review_agent.py` | 프로젝트 리뷰 |

### 4.5 설정·상태·스토리지

| 항목 | 상태 | 비고 |
|------|------|------|
| **ConfigManager** | ✅ | 키·agent_config·get_setting/set_setting |
| **settings.json** | ✅ | 최초 없을 때 `_ensure_default_settings()`로 템플릿 생성 (agent, opencode) |
| **.manifest/settings.json** | ✅ 존재 | `execution_backend: opencode`, opencode.* 설정 |
| **state.json** | ✅ | task_checklist, mission_tree, chat_history 등 |
| **스프린트** | ✅ | `.manifest/sprints/sprint-*.json`, SprintManager·StateManager 저장/로드 |
| **테스크–스프린트 연결** | ✅ | `update_task(sprint_id=...)`, `/create_sprint <name> [task_id...]` |

### 4.6 UI·브릿지·도구

| 항목 | 상태 | 비고 |
|------|------|------|
| **Textual UI** | ✅ | 앱·탭·로그·입력·트리·뷰 위젯 |
| **AgentBridge** | ✅ | direct 실행, 채널·_active_agents, 완료 시 `completed=True` 반영 |
| **ChannelManager** | ✅ | 채널별 히스토리·에이전트 출력 처리 |
| **PermissionManager** | ✅ | 역할/스코프 기반 퍼미션, 승인 UI 연동 |
| **TerminalRouter** | ✅ | OpenCodeAdapter 경유, 현재 internal subprocess만 사용 |
| **FileManager / ToolExecutor** | ✅ | 파일·도구 실행·터미널 호출 |

---

## 5. CI·스크립트·문서

| 항목 | 상태 | 비고 |
|------|------|------|
| **GitHub Actions** | ✅ | `test.yml`: pytest, cov, timeout 300, Python 3.9/3.10/3.11 |
| **check_ci_status.py** | ✅ | 로컬에서 CI와 동일한 pytest 실행, 푸시 전 검사용 |
| **pre_push_ci_check.sh** | ✅ | `check_ci_status.py` 호출 |
| **ci-before-commit-push.mdc** | ✅ | `alwaysApply`: 푸시 전 `check_ci_status.py` 실행, `--no-verify` 금지 |
| **GAPS_AND_NEXT.md** | ✅ 유지 | P0/P1/P2 반영 현황·남은 선택 작업 정리 |
| **README / USER_GUIDE / API / MODULES** | ✅ | 설치·실행·API·모듈 설명 |

---

## 6. 완료로 보는 항목 (이미 반영된 것)

- `/start_task` — Worker Squad 전체 플로우 기동 (GAPS 1.1의 “명령 없음”은 과거 상태, 현재는 구현됨)
- `/create_sprint` — 스프린트 생성 및 테스크 연결, `update_task(sprint_id)` 지원
- **OpenCode 기본** — 실행 백엔드 기본값·문서·설정 일치
- **settings.json 템플릿** — ConfigManager `_ensure_default_settings()`
- **OpenCode 터미널** — “지금은 internal 전용, 확장 포인트” 문서·주석
- **Worker Squad 완료 감지** — 우선순위 docstring, bridge 완료 시 완료 판정 테스트
- **CI 동일 검사** — 푸시 전 `check_ci_status.py`로 CI와 동일한 pytest 실행

---

## 7. 미구현·조건부·선택 사항

| 항목 | 분류 | 비고 |
|------|------|------|
| **OpenCode 터미널 API 연동** | 미구현 | 실제 API 정의 시 `_execute_with_opencode` 구현 필요 |
| **Bootstrap에서 settings/agent_config 편집** | 선택 | 현재는 API 키 위주, backend·opencode는 settings.json 직접 편집 |
| **docs 예시 settings.json** | 선택 | `docs/examples/settings.json` 있으면 안내에 유리 |
| **/add_task_to_sprint** | 선택 | 기존 스프린트에 테스크 추가용, 없으면 `/update_task task_id sprint_id=sprint_id`로 가능 |
| **intent.json / project.json 채우기** | 선택 | 편집 UI·`/` 명령 등 별도 기획 필요 |

---

## 8. 잘 작동하는지 요약

- **테스트**: 1136 passed, 6 skipped. 단위·통합·e2e 포함, CI·로컬 `check_ci_status.py`와 동일한 pytest로 검증됨.
- **진입·설정**: `python -m manifest` → 키 없으면 bootstrap → ManifestApp 실행 경로 확립. 설정은 `.manifest/settings.json`·ConfigManager로 로드되며, 기본값·템플릿 반영됨.
- **명령**: 30개 슬래시 명령 등록·핸들러 구현·테스트로 라우팅·동작 검증됨.
- **에이전트·스쿼드**: Worker Squad 단계·오케스트레이터·스프린트 실행·완료 감지 순서가 코드·doc·테스트에 맞게 정리되어 있음.
- **OpenCode**: LLM은 HTTP API로 정상 사용, 터미널은 internal만 사용하며 그 점이 문서·주석에 명시됨.
- **CI/푸시**: 워크플로·스크립트·커서 규칙으로 “푸시 전 CI와 동일 검사”가 유지되고 있음.

**결론**: Manifest 프로젝트는 전체 구조·핵심 플로우·설정·명령·테스트·CI가 정리된 상태이고, “완료된 기능·있는 기능·잘 작동하는지”는 위 섹션대로 파악하면 된다. 미구현·선택 사항은 GAPS_AND_NEXT.md 및 본 문서 §7과 일치시켜 두면 된다.
