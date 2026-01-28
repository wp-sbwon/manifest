# Worker Squad 구현 및 Agent 등록 현황

## 요약

| 구분 | 상태 | 설명 |
|------|------|------|
| **Worker Squad 로직** | ✅ 구현됨 | Manifest 내부 (WorkerSquadExecutor, AgentCoordinator) |
| **Worker Agent 클래스** | ✅ 구현됨 | planner, coder, test, debug, approver, project_review 등 (AgentManager) |
| **OpenCode agent 등록** | ⚠️ orchestrator만 | `.opencode/agents/manifest-orchestrator.json` 만 있음 |
| **Worker agent OpenCode 등록** | ❌ 없음 | planner, coder, test 등은 OpenCode agent로 등록되어 있지 않음 |
| **Worker Squad 트리거** | ⚠️ 경로 없음 | 예전 TUI의 `/start_task` 제거됨 → OpenCode에서 호출할 API/도구 필요 |

---

## 1. Worker Squad는 어떻게 구현되어 있는가

### 1.1 실행 흐름

```
AgentCoordinator.execute_worker_squad(task_id)
  → WorkerSquadExecutor.execute(task_id)
  → 단계별 실행:
       planner → tdd_test → coder → test → debug → self_review → approver
  → 각 단계: coordinator.start_worker_agent(task_id, agent_type, stage=...)
  → AgentBridge.start_agent_mission(task_id, agent_type, ...)
  → AgentManager.create_agent() → PlannerAgent / CoderAgent / TestAgent 등 생성
  → executor.execute_agent() → LLM 호출 (OpenCode LLM Adapter 또는 Direct API)
```

### 1.2 관련 코드 위치

| 역할 | 파일 | 설명 |
|------|------|------|
| 워크플로 오케스트레이션 | `src/manifest/agents/worker_squad_executor.py` | 단계 순서, 이벤트 구동, 타임아웃, 복구 |
| 에이전트 기동 | `src/manifest/agents/agent_coordinator.py` | `start_worker_agent`, `_start_task_worker_squad`, `execute_worker_squad` |
| 에이전트 ↔ 실행기 연결 | `src/manifest/bridge/agent_bridge.py` | `start_agent_mission`, planner/coder 채널 처리 |
| 에이전트 생성/실행 | `src/manifest/runtime/agent/core/manager.py` | `create_agent`, planner/coder/test/debug/approver 등 생성 |
| planner | `src/manifest/runtime/agent/agents/planner_agent.py` | PlannerAgent |
| coder | `src/manifest/runtime/agent/agents/coder_agent.py` | CoderAgent |
| test | `src/manifest/runtime/agent/agents/test_agent.py` | TestAgent |
| debug | `src/manifest/runtime/agent/agents/debug_agent.py` | DebugAgent |
| approver | `src/manifest/runtime/agent/agents/approver_agent.py` | ApproverAgent |
| project_review | `src/manifest/runtime/agent/agents/project_review_agent.py` | ProjectReviewAgent |

즉, Worker Squad와 planner/coder/test 등은 **Manifest 내부**에서만 구현되어 있고, OpenCode UI에 보이는 “채팅용 에이전트”와는 별개다.

---

## 2. Agent 등록은 되어 있는가

### 2.1 OpenCode 쪽 (프로젝트 `.opencode/agents/`)

- **등록됨**: `manifest-orchestrator` 만
  - 파일: `.opencode/agents/manifest-orchestrator.json`
  - 용도: OpenCode 채팅에서 “기본 에이전트”로 사용 (미션 조율, 태스크 분해, 안내 등).

- **등록 안 됨**: planner, coder, test, review, debug, approver, project_review
  - 이 타입들은 `.opencode/agents/` 에 JSON이 없음.
  - OpenCode는 이들을 “에이전트”로 인식하지 않음.

### 2.2 Manifest 쪽 (내부 “에이전트”)

- **등록/구성됨**:
  - `AgentManager` 가 planner, coder, test, debug, approver, project_review, e2e_test, integration_test 등을 **코드로** 생성.
  - `create_agent(agent_type="planner")` 등으로 인스턴스 생성 후, `Executor`(OpenCode LLM Adapter 또는 Direct API)로 LLM 호출.

정리하면:

- **OpenCode agent 등록**: orchestrator만 되어 있음.
- **Worker squad용 “에이전트”**: OpenCode에 등록된 게 아니라, Manifest 내부에서만 생성·실행됨.

---

## 3. Worker Squad를 지금 어떻게 돌릴 수 있는가

- **과거**: TUI가 있을 때 `CommandHandler`에서 `/start_task <task_id>` 로
  `agent_coordinator._start_task_worker_squad(task_id)` 호출 → Worker Squad 실행.
- **현재**: TUI(CommandHandler)가 제거된 상태라, **OpenCode 채팅만으로는 Worker Squad를 시작할 수 있는 경로가 없음.**

즉, 구현은 되어 있지만 “누르면 돌아가는 진입점”이 없음.

가능한 방향:

1. **OpenCode용 Manifest 도구(툴) 추가**
   - 예: `start_task(task_id)` 같은 툴을 정의하고,
     OpenCode가 그 툴을 호출할 때 Manifest 쪽 API(예: HTTP 또는 로컬 CLI)를 호출하도록 연결.
   - 그 API 안에서 `AgentCoordinator.execute_worker_squad(task_id)` 또는 `_start_task_worker_squad(task_id)` 호출.

2. **로컬 CLI 제공**
   - 예: `manifest start-task <task_id>` 같은 명령을 만들어서,
     내부에서 `execute_worker_squad(task_id)` 호출.
   - 사용자는 터미널에서 직접 실행하거나, OpenCode가 `terminal` 도구로 이 CLI를 실행하게 할 수 있음.

3. **OpenCode에 worker를 “서브에이전트”로 등록**
   - OpenCode가 서브에이전트/툴 호출을 지원한다면,
     “planner”, “coder” 등을 서브에이전트로 등록하고,
     각각이 Manifest의 해당 agent 타입을 호출하는 API/CLI를 감싸도록 구성할 수 있음.
   - 이건 OpenCode 쪽 문서/스펙을 봐야 함.

---

## 4. 정리

- **Worker Squad**: Manifest 안에 전부 구현되어 있음 (단계, 에이전트 클래스, 브릿지, 실행기).
- **Agent 등록**:
  - OpenCode에는 **manifest-orchestrator만** 등록되어 있음.
  - planner, coder, test 등은 **OpenCode agent로는 등록되어 있지 않고**, Manifest **내부**에서만 “에이전트”로 쓰임.
- **실행 트리거**:
  - 예전 `/start_task` 경로는 사라진 상태이므로,
    OpenCode에서 “태스크 실행/Worker Squad 실행”을 하려면
    위와 같은 **API/CLI/OpenCode 툴** 중 하나를 추가해 주어야 함.

이 문서는 그 현황을 설명하는 용도로 두면 됨.
