# Manifest 최종 계획 (OpenCode 기반)

**단일 문서.** 여기만 보면 됨.

---

## 1. 진입점

- **실행**: `manifest` (또는 `python -m manifest`) → **Launcher**
- Launcher가 하는 일:
  1. **View** 프로세스 시작 (별도 창, 시각화 전용)
  2. **OpenCode** 실행: `opencode . --agent manifest-orchestrator -c` (기본 에이전트 = 우리 orchestrator)
- 채팅/명령은 **전부 OpenCode 터미널**에서. Manifest는 OpenCode UI를 복제하지 않음.

---

## 2. 핵심 기능 (필수)

| # | 기능 | 요약 |
|---|------|------|
| 1 | **Task Management** | Task/Sprint 생성·수정·상태·진행도. 실시간 반영. View + OpenCode( orchestrator 명령)에서 사용. |
| 2 | **Ground Truth & Drift** | Top-down / Bottom-up **정의 포맷(.json)** 문서 생성 → **기계적 비교**로 drift 판별 (LLM 미사용). |
| 3 | **Bottom-up** | 코드에서 **기계적으로** 뽑을 수 있는 것 전부 추출 → 정의 문서. Intent/Architecture 등은 LLM 사용. |
| 4 | **Top-down** | PRD부터 **LLM 생성** → 그 아래 blueprint/architecture 등 **정의 문서**도 LLM이 생성. |
| 5 | **Tiered Context** | Tier 0(Policy) ~ Tier 3(Surgical Code). Agent별로 필요한 것만 제공. |
| 6 | **State Continuity** | Mission/Task 상태 영속. 세션 재개. |
| 7 | **Design Change History** | PRD/blueprint/architecture 변경 이력 저장. View History에 Git commits + 설계 이력 표시. |
| 8 | **Worker Squad** | planner, coder, test, debug, approver. **컨테이너** 안에서 OpenCode로 실행. Skills 필수. Failure recovery 필수. |
| 9 | **Container** | Worker 에이전트 = 컨테이너 단위. Main OpenCode terminal에서 **채널/탭 스위칭**으로 각 컨테이너 작업 메시지 조회. |
| 10 | **승인 (Approval)** | Tool 실행 전 승인 등 **설정으로** 켜기/끄기. |
| 11 | **전체 테스트 에이전트** | Orchestrator와 **동일 레벨** OpenCode agent. 프로젝트/스프린트 전체·E2E·통합 테스트. |
| 12 | **모듈별 출력 View** | 컨테이너(모듈)별 아웃풋을 **채널**로 스트리밍 → View에서 **실시간** 표시. |
| 13 | **Workflow** | Worker Squad 단계/조건/재시도/병렬을 **WorkflowDefinition**으로 정의. **필수.** |
| 14 | **Event Bus** | 워크플로 이벤트(AGENT_COMPLETED 등) publish/subscribe. 단계 전이·실패 복구. **필수.** |
| 15 | **Agent Message Bus** | 에이전트 간 메시징(planner→coder 등). **필수.** (OpenCode에 동일 기능 있으면 그쪽 사용) |

---

## 3. View (별도 창)

- **역할**: 시각화 + 보기 전환만. Task **실행/명령**은 OpenCode에서.
- **실시간 sync**: `.manifest/` 파일(tasks.json, blueprint_code.json, state.json, history 등) watch → 변경 시 View 갱신.
- **표시 내용**:
  - Task 목록·상태·진행도
  - Blueprint / 구조 / 진행도·완성도
  - Drift (기계적 비교 결과)
  - History (Git commits + 설계 변경 이력)
  - 모듈(컨테이너)별 출력 스트림
- **전환**: 보고 있는 뷰만 전환(스위칭). GUI로 task 실행/중지는 하지 않음.

---

## 4. OpenCode / 터미널

- **채팅·코딩·도구 호출·터미널 명령**: 전부 **OpenCode**가 처리.
- Manifest는 **별도 터미널 어댑터를 두지 않음.** (OpenCode로 작업하므로 불필요)

---

## 5. 데이터·구성

- **정의 문서**: 동일 스키마의 .json. Top-down(설계) vs Bottom-up(코드) → **기계적 비교**로 drift.
- **Task**: `.manifest/tasks.json` 등에서 실시간 갱신.
- **설정**: ConfigManager, `.manifest/settings.json`. API 키, execution backend, **승인 on/off** 등.
- **진입점**: Launcher (View 프로세스 + OpenCode 실행).

---

## 6. 구현 시 유지할 것

- WorkflowDefinition, WorkflowEventBus, AgentMessageBus
- Container(Worker Squad 컨테이너 실행), Skills, Failure recovery
- Task Management Tool, Blueprint Sync/Drift(기계적 비교), Design History
- View(별도 프로세스, .manifest watch, 실시간 표시)
- OpenCode agent: manifest-orchestrator(기본), manifest-planner/coder/test/debug/approver, manifest-full-test(Orchestrator와 동일 레벨)

---

## 7. 구현 시 제거/미사용

- **OpenCode Terminal Adapter**: 사용 안 함. OpenCode가 터미널 처리.
- 우리만의 채팅 UI 복제: 하지 않음. OpenCode 그대로 사용.

---

이 문서가 **최종 계획**이다. 다른 “추가 문서”나 “보고”는 이걸 대체하지 않는다.
