# 플랜 추가 사항: Container, Shadow, Bus, Adapter 설명

사용자 요청(1~7)에 대한 정리 및 Workflow/EventBus/MessageBus 판단용 설명.

---

## 1. Container 구조 (반영 확정)

**요구사항**
- 컨테이너 필요.
- 각 컨테이너 안에서 워커 에이전트들이 **OpenCode를 통해** 실행.
- 그 작업 메시지는 **main OpenCode terminal에서 스위칭(탭/컨텍스트 전환)** 으로 볼 수 있어야 함.

**구조**
```
Main OpenCode Terminal (사용자)
  ├─ [Orchestrator 채널]  ← 기본 화면
  ├─ [Container A: task_001 / planner]  ← 스위칭으로 전환
  ├─ [Container B: task_001 / coder]   ← 스위칭으로 전환
  ├─ [Container C: task_002 / test]    ← 스위칭으로 전환
  └─ ...
```
- 각 컨테이너 = 하나의 Worker Agent 실행 환경.
- 컨테이너 내부에서는 OpenCode 클라이언트/에이전트가 실행되고, stdout/메시지가 **채널**로 나감.
- Main OpenCode terminal이 **채널 스위칭**으로 어떤 컨테이너(어떤 task/agent)의 출력을 볼지 선택.

**플랜 반영**
- Worker Squad는 **컨테이너 단위** 실행.
- 컨테이너 내부에서 OpenCode 통해 에이전트 실행.
- Main OpenCode terminal에서 **채널/탭 스위칭**으로 각 컨테이너 작업 메시지 조회.

---

## 2. 승인 (Approval) — 설정 가능 (반영 확정)

- Tool 실행 전 승인 등 **승인 정책을 설정으로 켜기/끄기**.
- 예: `.manifest/settings.json` 또는 UI에서 `approval.require_before_tool_execution: true/false`, `approval.require_for_file_write: true/false` 등.
- 플랜에 "승인은 설정 가능(optional, 설정으로 활성화)" 명시.

---

## 3. 전체 테스트 에이전트 — Orchestrator와 동일 레벨 (반영 확정)

- **Worker Squad 내부**의 test 에이전트: task 단위 테스트 (기존 유지).
- **전체 테스트 에이전트**: Orchestrator와 **같은 레벨**에서 별도 실행.
  - 역할: 프로젝트 전체/스프린트 단위 테스트, E2E/통합 테스트 등.
  - OpenCode agent로 등록: 예) `manifest-full-test` 또는 `manifest-e2e`.
- 플랜에 "전체 테스트 에이전트(Full Test Agent)는 Orchestrator와 동일 레벨, 별도 OpenCode agent" 명시.

---

## 4. Skills, Failure recovery — 필수 (반영 확정)

- **Skills**: 에이전트가 참조하는 규칙/스킬 세트(예: Coder의 "Check Skills FIRST"). 필수 유지.
- **Failure recovery**: Worker Squad 단계 실패 시 재시도/복구 정책. 필수 유지.
- 플랜에 둘 다 "필수"로 명시.

---

## 5. Shadow Manager 개념 및 View 연동

**현재 코드에서 Shadow Manager가 하는 일**
- 에이전트를 **별도 프로세스**에서 실행 (격리).
- **실시간 출력 스트리밍**: `output_channel`(예: `shadow-task_001-coder`) + `output_callback(channel, line)`.
- View/다른 구독자가 이 콜백으로 stdout/stderr를 받아서 보여줌.
- (선택) 샌드박스 디렉터리에서 실행 후, 승인 시 `promote_shadow_changes`로 메인 코드베이스에 반영.

**요구사항 해석**
- "전체 구조에서 나눠진 **모듈별**로 **아웃풋 값**이 **실시간**으로 **뷰**에서 보여져야 한다."
- "여기선 이 **데이터를 값으로 뱉는다**" → 단순 로그가 아니라 **모듈(에이전트/컨테이너)별로 구조화된 출력 값**이 View에 실시간 표시.

**정리**
- **Shadow(또는 Container) 단위로 “출력 채널”**을 두고, 그 채널로 나오는 내용(텍스트/구조화 데이터)을 **View에서 실시간 표시**.
- 개념적으로:
  - **모듈** = 컨테이너(또는 shadow process) 단위의 실행 단위.
  - **아웃풋 값** = 해당 모듈이 뱉는 stdout/메시지/구조화된 결과(예: `{"step": "parse", "result": 42}`).
  - **실시간 뷰** = View가 채널별 스트림을 구독해, 모듈별로 “지금 이 모듈이 이 값을 뱉고 있음”을 표시.

**플랜 반영**
- Shadow/Container 출력을 **모듈(실행 단위)별 채널**로 정의.
- View는 **채널별 실시간 출력**을 표시 (텍스트 + 필요 시 구조화 데이터).
- “이 데이터를 값으로 뱉는다”는, 모듈별 출력을 값(데이터)으로 정의하고 View에 반영하는 것으로 설계.

---

## 6. Workflow Definition / EventBus / Agent Message Bus — 각각 역할과 필요 여부

### 6.1 Workflow Definition

**역할**
- **Worker Squad 단계**를 데이터로 정의: 단계 이름, 사용할 agent 타입, 의존성, 타임아웃, 재시도, 병렬 여부 등.
- 예: `planner → tdd_test → coder → test → debug → approver` 를 JSON/YAML로 정의하고 런타임에 로드/변경.

**필요 여부**
- **필요**. 단계 순서/조건/재시도를 코드에 하드코딩하지 않고 정의 파일로 두려면 WorkflowDefinition(또는 동일 개념)이 있으면 좋음.
- OpenCode가 단계를 전부 알 필요는 없고, **Manifest가 “다음에 누구를 어떤 컨테이너에서 돌릴지”** 결정할 때 이 정의를 사용.

**결론**: **유지 권장**. 단계/조건/재시도/병렬을 설정 가능하게 하려면 필요.

---

### 6.2 Workflow EventBus

**역할**
- **워크플로우 생명주기 이벤트** 퍼블리시: `AGENT_STARTED`, `AGENT_COMPLETED`, `AGENT_FAILED`, `STAGE_COMPLETED`, `WORKFLOW_COMPLETED` 등.
- 구독자(예: WorkerSquadExecutor)가 이벤트를 받아 **다음 단계 트리거**, **실패 시 재시도/복구** 등 수행.

**필요 여부**
- Worker Squad가 **이벤트 기반**으로 “planner 끝남 → coder 시작” 같은 전이를 하려면 **필요**.
- 이벤트 없이 폴링만 쓰면 복잡하고 지연도 생김.
- **결론**: **유지 권장**. 단계 전이와 Failure recovery를 이벤트로 끌어다 쓰는 구조에 잘 맞음.

---

### 6.3 Agent Message Bus

**역할**
- **에이전트 간 직접 메시징**: request/response, notification, broadcast.
- 예: Planner가 Coder에게 “이 plan으로 구현해” 메시지 전달, Coder가 결과로 응답.

**필요 여부**
- **현재**: Worker Squad에서는 보통 “Executor가 단계 결과를 다음 단계 context로 넘김”으로 충분한 경우가 많음.
- **컨테이너/프로세스가 분리**되면: 컨테이너 A(planner) → 컨테이너 B(coder) 로 **직접** 메시지를 넘기려면 메시지 버스나 이에 준하는 채널이 있으면 편함.
- OpenCode가 “에이전트 간 메시지”를 이미 제공하면, 그걸 쓰고 Agent Message Bus는 **선택**.
- OpenCode에 그런 게 없으면 **에이전트 간 협업(요청/응답)** 을 위해 **유지 권장**.

**결론**: **OpenCode에 에이전트 간 메시징이 있는지**에 따라 결정. 없으면 **유지 권장**, 있으면 **선택(점진적 제거 가능)**.

---

**6번 요약 (당신이 정할 부분)**
- **Workflow Definition**: 필요. 유지 권장.
- **Workflow EventBus**: 필요. 유지 권장.
- **Agent Message Bus**: OpenCode에 에이전트 간 메시징 유무에 따라 결정. 없으면 유지 권장.

---

## 7. OpenCode Terminal Adapter 설명

**위치**: `src/manifest/runtime/opencode_adapter.py`

**역할**
- **터미널 명령 실행**을 “OpenCode를 통해 할지 / 내부 subprocess로 할지” 추상화.
- `execute_command(command, args, timeout, stream)` 같은 하나의 인터페이스를 제공.
- 설계 의도: OpenCode가 **터미널/명령 실행 API**(예: `opencode.TerminalRouter`)를 제공하면, 그쪽으로 실행을 넘기고, 없거나 실패하면 **내부 subprocess**로 실행.

**현재 구현**
- **OpenCode 터미널 API는 미연동**: `_init_opencode_router()` 는 `None` 반환, `_execute_with_opencode()` 는 **스텁**이라 항상 `_execute_internal()` 로 폴백.
- 따라서 **지금은 모든 터미널 명령이 Manifest 내부 subprocess**로만 실행됨.
- **OpenCode LLM Adapter** (`opencode_llm_adapter.py`)와는 별개: LLM 호출은 OpenCode HTTP API 쓰고, **명령 실행**만 이 Adapter를 통해 함.

**정리**
- **OpenCode Terminal Adapter** = “터미널 명령 실행”을 OpenCode 쪽으로 넘길 수 있게 하는 **어댑터**.
- 현재는 OpenCode 터미널 API가 없어서 **미사용**이고, 확장 포인트로만 둔 상태.
- 나중에 OpenCode가 터미널 API를 제공하면, 여기만 구현해서 붙이면 되고, 호출부(TerminalRouter 등)는 그대로 둘 수 있음.

---

이 문서는 플랜 보조 자료이며, 1~5번은 플랜 본문에 반영하고, 6번은 위 판단을 참고해 사용자가 최종 결정하면 됨.
