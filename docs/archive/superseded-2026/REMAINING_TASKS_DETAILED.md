# 남은 작업 상세 설명 (2026-01-28)

**기준**: 실제 코드 상태 확인 후 작성

---

## P3: OpenCode 터미널 Adapter 구현 (선택적)

### 현재 상태

**구현됨**:
- ✅ OpenCode LLM Adapter (`opencode_llm_adapter.py`) - 완전 구현
- ✅ OpenCode 터미널 Adapter 구조 (`opencode_adapter.py`) - 클래스만 존재

**미구현**:
- ❌ `_execute_with_opencode()` 메서드 - 플레이스홀더만 있음
- ❌ `_init_opencode_router()` - 항상 `None` 반환

### 문제 설명

**OpenCode LLM Adapter vs OpenCode 터미널 Adapter**:
- **LLM Adapter**: LLM API 호출용 (이미 구현됨, 기본 백엔드)
- **터미널 Adapter**: 터미널 명령 실행용 (미구현)

**현재 동작**:
```python
# opencode_adapter.py:105
async def _execute_with_opencode(self, command: str, ...) -> Dict[str, Any]:
    # TODO: Implement OpenCode terminal API integration
    pass  # ⚠️ 항상 internal fallback 사용
```

모든 터미널 명령은 `_execute_internal()`로 실행됨 (subprocess 기반).

### 왜 선택적인가?

1. **OpenCode 터미널 API가 정의되지 않음**
   - OpenCode가 터미널 API를 제공하는지 불명확
   - API 스펙이 없으면 구현 불가능

2. **현재 동작에 문제 없음**
   - Internal subprocess 실행이 정상 작동
   - OpenCode 없이도 모든 기능 사용 가능

3. **LLM 기능은 이미 사용 중**
   - OpenCode LLM Adapter는 완전 구현되어 기본 백엔드로 사용
   - 터미널 기능만 미사용

### 구현 시 필요한 것

1. **OpenCode 터미널 API 스펙 확인**
   - OpenCode가 터미널 명령 실행 API를 제공하는지 확인
   - API 엔드포인트 및 사용법 확인

2. **구현 작업**
   - `_init_opencode_router()` 구현
   - `_execute_with_opencode()` 구현
   - 통합 테스트 작성

### 영향

- **현재**: 터미널 명령은 internal subprocess 사용 (정상 작동)
- **구현 후**: OpenCode 터미널 기능 활용 가능 (선택적 개선)

---

## P4: UI 개선 (병렬 실행 표시)

### 현재 상태

**구현됨**:
- ✅ 병렬 실행 로직 (`WorkerSquadExecutor`) - 완전 구현
- ✅ WorkflowVisualization 기본 구현 - 완료
- ✅ `_join_parallel_nodes()` 메서드 - 병렬 노드 표시

**개선 필요**:
- ⚠️ 병렬 실행 시각화가 명확하지 않음
- ⚠️ ContextBar가 최대 3개 activity만 표시 (병렬 실행 시 부족)
- ⚠️ Dashboard에 병렬 실행 중인 stage 수 미표시

### 문제 설명

**1. WorkflowVisualization의 병렬 표시**

현재 코드 (`workflow_visualization.py:95-98`):
```python
# Join parallel stages
if len(stage_nodes) > 1:
    # Multiple stages in parallel
    node_lines = self._join_parallel_nodes(stage_nodes)
```

`_join_parallel_nodes()`는 구현되어 있지만:
- 병렬 실행임을 명확히 표시하지 않음
- "동시 실행 중" 표시 없음
- 병렬 그룹 경계가 불명확할 수 있음

**2. ContextBar Activity 제한**

현재 코드 (`app.py:1126-1171`):
```python
# ContextBar는 최대 3개 activity만 표시
activities = self.activities[-3:]  # 마지막 3개만
```

병렬 실행 시 여러 stage가 동시에 실행되면 일부가 표시되지 않음.

**3. Dashboard Metrics**

현재 Dashboard에는:
- 총 테스크 수
- 완료된 테스크 수
- 실행 중인 에이전트 수

하지만:
- 병렬 실행 중인 stage 수 없음
- 병렬 실행 그룹 정보 없음

### 개선 방안

**1. WorkflowVisualization 개선**
- 병렬 stage를 명확히 표시 (예: `[PARALLEL]` 라벨)
- 병렬 실행 중인 stage에 "⚡ Running in parallel" 표시
- 병렬 그룹을 박스로 감싸서 시각적 구분

**2. ContextBar 개선**
- Activity 제한 확장 (3개 → 10개 또는 제한 없음)
- 병렬 실행 중인 stage 모두 표시
- 병렬 그룹 표시 (예: "planner, coder (parallel)")

**3. Dashboard 개선**
- "Parallel Stages" 메트릭 추가
- 병렬 실행 그룹 수 표시
- 병렬 실행 중인 stage 목록 표시

### 영향

- **현재**: 병렬 실행은 작동하지만 UI에서 명확히 보이지 않음
- **개선 후**: 사용자가 병렬 실행 상태를 명확히 파악 가능

---

## P5: `/add_task_to_sprint` 명령 추가

### 현재 상태

**구현됨**:
- ✅ `/create_sprint <name> [task_id ...]` - 스프린트 생성 및 테스크 연결
- ✅ `update_task(task_id, sprint_id=...)` - 테스크에 스프린트 할당
- ✅ SprintManager 클래스 - 스프린트 관리

**미구현**:
- ❌ `/add_task_to_sprint <sprint_id> <task_id>` - 기존 스프린트에 테스크 추가

### 문제 설명

**현재 사용 방법**:
```bash
# 스프린트 생성 시 테스크 연결
/create_sprint "Sprint 1" task-1 task-2 task-3

# 또는 테스크 업데이트로 스프린트 할당
/update_task task-4 sprint_id=sprint-1
```

**부족한 점**:
- 스프린트 생성 후에 테스크를 추가하려면 `/update_task` 사용 필요
- 명시적인 "스프린트에 테스크 추가" 명령 없음
- 여러 테스크를 한 번에 추가하는 기능 없음

### 구현 방안

**명령 형식**:
```bash
/add_task_to_sprint <sprint_id> <task_id> [task_id ...]
```

**구현 위치**: `command_handler.py`

**구현 내용**:
```python
async def _handle_add_task_to_sprint(self, args: List[str], log: RichLog):
    """Handle /add_task_to_sprint command."""
    if len(args) < 2:
        log.write("[bold yellow]Usage: /add_task_to_sprint <sprint_id> <task_id> [task_id ...][/]")
        return

    sprint_id = args[0]
    task_ids = args[1:]

    # Sprint 존재 확인
    sprint = self.app.state_manager.get_sprint(sprint_id)
    if not sprint:
        log.write(f"[bold red]Sprint '{sprint_id}' not found.[/]")
        return

    # 각 테스크에 스프린트 할당
    added = 0
    for task_id in task_ids:
        if self.app.state_manager.update_task(task_id, sprint_id=sprint_id):
            added += 1

    log.write(f"[bold green]Added {added} task(s) to sprint {sprint_id}.[/]")
```

### 영향

- **현재**: `/update_task`로 수동 할당 필요
- **구현 후**: 명시적인 명령으로 편리하게 테스크 추가 가능

---

## 우선순위 비교

### P3: OpenCode 터미널 Adapter
- **우선순위**: 낮음 (선택적)
- **이유**: OpenCode API 정의 필요, 현재 동작에 문제 없음
- **작업량**: 중간 (API 확인 후 구현)
- **영향**: 낮음 (기능 개선, 필수 아님)

### P4: UI 개선 (병렬 실행 표시)
- **우선순위**: 중간
- **이유**: 사용자 경험 개선, 병렬 실행은 작동하지만 시각화 부족
- **작업량**: 중간 (UI 수정)
- **영향**: 중간 (사용성 개선)

### P5: `/add_task_to_sprint` 명령
- **우선순위**: 낮음
- **이유**: 편의 기능, `/update_task`로 우회 가능
- **작업량**: 낮음 (간단한 명령 추가)
- **영향**: 낮음 (편의성 개선)

---

## 권장 순서

1. **P5 (가장 쉬움)**: `/add_task_to_sprint` 명령 추가
   - 작업량: 30분
   - 즉시 사용 가능

2. **P4 (사용자 경험)**: UI 개선
   - 작업량: 2-3시간
   - 사용자 경험 개선

3. **P3 (선택적)**: OpenCode 터미널 Adapter
   - 작업량: 불명확 (API 확인 필요)
   - OpenCode 터미널 API 정의 후 진행

---

## 결론

**모든 남은 작업은 선택적 개선사항입니다:**
- MVP 핵심 기능은 모두 완료됨
- 남은 작업은 사용성/편의성 개선
- 즉시 구현하지 않아도 앱은 정상 작동

**추천**: P5 → P4 → P3 순서로 진행
