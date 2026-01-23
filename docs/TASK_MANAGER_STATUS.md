# Task Manager 구현 상태

**최종 업데이트**: 2025-01-23

## 개요

Manifest의 Task Manager는 Mission의 작업 단위를 관리하는 시스템입니다. Task는 Agent에게 할당되어 실행되며, 상태와 Stage를 추적합니다.

## 구현된 기능 (✅)

### 1. Task 저장 및 로드
**위치**: `src/manifest/core/state_manager.py`

**기능**:
- ✅ `get_task_checklist()`: Task 목록 가져오기
- ✅ `set_task_checklist()`: Task 목록 설정
- ✅ Task는 `.manifest/state.json`에 영속화됨

**Task 스키마**:
```json
{
  "id": "task-1",
  "name": "Task Name",
  "status": "pending|in_progress|done|blocked|approved",
  "stage": "planning|implementation|testing|review|pending",
  "subtasks": [],
  "agent": {
    "type": "coder|planner|orchestrator|test|review",
    "status": "active|stopped",
    "channel": "squad-task-1-coder"
  },
  "scope": {
    "components": [],
    "files": [],
    "allowed_modifications": []
  }
}
```

### 2. Task 표시 (UI)
**위치**: `src/manifest/ui/widgets.py` - `TaskTree`

**기능**:
- ✅ Task 목록을 트리 형태로 표시
- ✅ Task 상태 아이콘 표시 (✅ done, ⚡ in_progress, ⏳ pending, 🚫 blocked, ✓ approved)
- ✅ Task Stage 표시 (`[planning]`, `[implementation]`, etc.)
- ✅ Subtask 표시
- ✅ 선택된 Task 가져오기 (`get_selected_task()`)

**위치**: `src/manifest/ui/app.py` - `update_task_tree()`

**기능**:
- ✅ State에서 Task 목록 로드
- ✅ TaskTree 위젯에 Task 로드
- ✅ 기본 샘플 Task 생성 (Task가 없을 때)

### 3. Task 승인/거부 (Gate Controller)
**위치**: `src/manifest/ui/widgets.py` - `GateController`

**기능**:
- ✅ Approve 버튼 (✅)
- ✅ Reject 버튼 (❌)
- ✅ Feedback 버튼 (💬)
- ✅ 이벤트 메시지 발생 (`Approved`, `Rejected`, `FeedbackRequested`)

**위치**: `src/manifest/ui/app.py`

**기능**:
- ✅ `on_task_approved()`: Task 승인 처리
- ✅ `on_task_rejected()`: Task 거부 처리
- ✅ `promote_task()` 호출로 Task Stage 변경

### 4. Task Stage 변경 (Promote)
**위치**: `src/manifest/bridge/agent_bridge.py` - `promote_task()`

**기능**:
- ✅ Task의 `stage` 필드 업데이트
- ✅ State에 저장

**사용 예시**:
```python
await agent_bridge.promote_task("task-1", "approved")
await agent_bridge.promote_task("task-1", "implementation")
```

### 5. Task 범위 관리 (Task Scoping)
**위치**: `src/manifest/agents/task_scoper.py` - `TaskScoper`

**기능**:
- ✅ `get_task_context()`: Task 범위 추출
  - Components (Blueprint에서)
  - Files (Component에서)
  - Requirements (Intent에서)
  - Allowed modifications (디렉토리)
- ✅ `validate_task_scope()`: 파일이 Task 범위에 있는지 검증
- ✅ `get_task_scope_summary()`: Task 범위 요약

### 6. Task에 Agent 할당 및 상태 관리
**위치**: `src/manifest/agents/agent_coordinator.py`

**기능**:
- ✅ Agent 시작 시 Task에 Agent 정보 추가
  ```python
  task["agent"] = {
    "type": "coder",
    "status": "active",
    "channel": "squad-task-1-coder"
  }
  ```
- ✅ Agent 중지 시 Task의 Agent 상태 업데이트
- ✅ Task Scope를 Task에 저장
  ```python
  task["scope"] = {
    "components": [...],
    "files": [...],
    "allowed_modifications": [...]
  }
  ```

### 7. Task 상태 업데이트
**위치**: `src/manifest/agents/agent_coordinator.py`

**기능**:
- ✅ Agent 시작 시 Task 상태 업데이트
- ✅ Agent 중지 시 Task 상태 업데이트
- ✅ Blueprint 충돌 시 Task에 Conflict 정보 추가

## 부분 구현 (⚠️)

### 1. Task 생성
**현재 상태**: ⚠️ 수동 생성만 가능

**문제점**:
- ❌ `create_task()` 같은 메서드가 없음
- ❌ UI에서 Task 생성 기능 없음
- ❌ Agent가 Task를 자동 생성하는 기능 없음

**현재 방법**:
1. 수동으로 `.manifest/state.json`에 Task 추가
2. `update_task_tree()`에서 기본 샘플 Task 생성 (하드코딩)

**필요한 기능**:
```python
# StateManager에 추가 필요
def create_task(
    self,
    name: str,
    description: str = "",
    stage: str = "planning",
    status: str = "pending"
) -> str:
    """Create a new task and return its ID."""
    task_id = f"task-{len(self.get_task_checklist()) + 1}"
    task = {
        "id": task_id,
        "name": name,
        "description": description,
        "status": status,
        "stage": stage,
        "subtasks": []
    }
    tasks = self.get_task_checklist()
    tasks.append(task)
    self.set_task_checklist(tasks)
    return task_id
```

### 2. Task 편집
**현재 상태**: ⚠️ 직접 State 수정 필요

**문제점**:
- ❌ Task 이름/설명 편집 기능 없음
- ❌ Task 상태 직접 변경 기능 없음 (승인/거부만 가능)
- ❌ Subtask 추가/삭제 기능 없음

**필요한 기능**:
```python
# StateManager에 추가 필요
def update_task(
    self,
    task_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    stage: Optional[str] = None
) -> bool:
    """Update task properties."""
    tasks = self.get_task_checklist()
    for task in tasks:
        if task.get("id") == task_id:
            if name is not None:
                task["name"] = name
            if description is not None:
                task["description"] = description
            if status is not None:
                task["status"] = status
            if stage is not None:
                task["stage"] = stage
            self.set_task_checklist(tasks)
            return True
    return False
```

### 3. Task 삭제
**현재 상태**: ❌ 미구현

**필요한 기능**:
```python
# StateManager에 추가 필요
def delete_task(self, task_id: str) -> bool:
    """Delete a task."""
    tasks = self.get_task_checklist()
    tasks = [t for t in tasks if t.get("id") != task_id]
    self.set_task_checklist(tasks)
    return True
```

### 4. Task 검색 및 필터링
**현재 상태**: ❌ 미구현

**필요한 기능**:
```python
# StateManager에 추가 필요
def find_tasks(
    self,
    status: Optional[str] = None,
    stage: Optional[str] = None,
    agent_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Find tasks matching criteria."""
    tasks = self.get_task_checklist()
    if status:
        tasks = [t for t in tasks if t.get("status") == status]
    if stage:
        tasks = [t for t in tasks if t.get("stage") == stage]
    if agent_type:
        tasks = [t for t in tasks if t.get("agent", {}).get("type") == agent_type]
    return tasks
```

## 미구현 기능 (❌)

### 1. Task 자동 생성
**설명**: Agent (특히 Orchestrator, Planner)가 Task를 자동으로 생성

**필요한 기능**:
- Orchestrator가 Mission을 분석하여 Task 생성
- Planner가 Blueprint를 분석하여 Task 생성
- Task 간 의존성 관리

### 2. Task 의존성 관리
**설명**: Task 간 의존성 추적 및 순서 관리

**필요한 기능**:
- Task 의존성 정의
- Task 실행 순서 결정
- Blocked 상태 자동 설정

### 3. Task 템플릿
**설명**: 재사용 가능한 Task 템플릿

**필요한 기능**:
- Task 템플릿 정의
- 템플릿에서 Task 생성
- 템플릿 관리

### 4. Task 히스토리
**설명**: Task 변경 이력 추적

**필요한 기능**:
- Task 상태 변경 이력
- Task 편집 이력
- Task 실행 로그

### 5. Task 통계 및 리포트
**설명**: Task 진행 상황 통계

**필요한 기능**:
- Task 완료율
- Task별 소요 시간
- Agent별 Task 성과

## 현재 Task 관리 워크플로우

### 1. Task 생성 (수동)
```
1. .manifest/state.json 파일 직접 편집
2. 또는 update_task_tree()에서 기본 샘플 Task 생성
```

### 2. Task에 Agent 할당
```
1. /start_agent <task_id> <agent_type> 명령어 실행
2. AgentCoordinator.start_worker_agent() 호출
3. Task에 Agent 정보 추가
4. Task Scope 추출 및 저장
```

### 3. Task 승인/거부
```
1. UI에서 GateController 버튼 클릭
2. on_task_approved() 또는 on_task_rejected() 호출
3. promote_task()로 Stage 변경
4. State 저장
```

### 4. Task 상태 업데이트
```
1. Agent 시작/중지 시 자동 업데이트
2. Blueprint 충돌 시 Conflict 정보 추가
3. State에 저장
```

## 개선 필요 사항

### High Priority
1. **Task 생성 API 추가**
   - `StateManager.create_task()` 메서드
   - UI에서 Task 생성 기능

2. **Task 편집 기능**
   - `StateManager.update_task()` 메서드
   - UI에서 Task 편집 기능

3. **Task 삭제 기능**
   - `StateManager.delete_task()` 메서드
   - UI에서 Task 삭제 기능

### Medium Priority
1. **Task 검색 및 필터링**
   - `StateManager.find_tasks()` 메서드
   - UI에서 필터링 기능

2. **Task 자동 생성**
   - Orchestrator/Planner가 Task 생성
   - Blueprint/Intent에서 Task 추출

### Low Priority
1. **Task 의존성 관리**
2. **Task 템플릿**
3. **Task 히스토리**
4. **Task 통계**

## 요약

### 구현 완료 (✅)
- Task 저장/로드
- Task 표시 (UI)
- Task 승인/거부
- Task Stage 변경
- Task 범위 관리
- Task에 Agent 할당
- Task 상태 업데이트

### 부분 구현 (⚠️)
- Task 생성 (수동만 가능)
- Task 편집 (직접 State 수정 필요)

### 미구현 (❌)
- Task 삭제
- Task 검색/필터링
- Task 자동 생성
- Task 의존성 관리
- Task 템플릿
- Task 히스토리
- Task 통계

**전체 완성도**: 약 **60%**

**핵심 기능은 구현되어 있으나, Task 생명주기 관리 (생성, 편집, 삭제)가 부족합니다.**
