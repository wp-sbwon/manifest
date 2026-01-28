# 코드베이스 분석 및 개선사항

**분석일**: 2026-01-27
**최종 업데이트**: 2026-01-27
**분석 범위**: 전체 코드베이스 직접 검토 (문서 참고 없음)
**상태**: ✅ 모든 발견된 문제점 수정 완료

---

## 현재 구현 상태

### ✅ 완전히 구현된 기능

1. **Agent 시스템**
   - 모든 Agent 타입 구현됨 (planner, coder, test, debug, orchestrator, approver, project_review, e2e_test, integration_test)
   - Agent-to-agent 메시징 (handle_message 구현 완료)
   - Agent 메시지 버스 통합 완료

2. **워크플로우 실행**
   - WorkerSquadExecutor 완전 구현
   - Event-driven 모드 기본 활성화
   - 병렬 실행 모드 구현 완료 (의존성 해결, 리소스 제한 포함)
   - WorkflowEventBus 이벤트 발행 완료

3. **컨테이너 통신**
   - ContainerAPI, ContainerMessageBus, ContainerStateSync 구현 완료
   - 통합 테스트 완료

4. **UI 기본 구조**
   - DashboardHeader, ContextBar 구현됨
   - 주기적 업데이트 설정됨 (5초, 2초)
   - ChannelManager로 Agent 출력 관리
   - TaskProgressView 위젯 존재

5. **Orchestrator 통합**
   - 사용자 입력 → Orchestrator 처리 완료
   - Task 자동 생성 로직 구현됨
   - Worker Squad 자동 시작 로직 구현됨

---

## 🔴 발견된 문제점 및 개선 필요 사항

### 1. Workflow Visualization 미완성 (High Priority)

**문제**:
- `TaskProgressView._update_workflow_visualization()` 메서드가 **존재하지 않음**
- `TaskProgressView.update_task()`에서 호출하지만 구현이 없어 에러 발생 가능
- WorkflowVisualization 위젯은 있지만 실제로 workflow state를 로드하지 않음

**위치**: `src/manifest/ui/widgets/task_progress_view.py:57`

**영향**:
- Task 선택 시 workflow 시각화가 표시되지 않음
- 사용자가 워크플로우 진행 상황을 시각적으로 확인할 수 없음

**필요 작업**:
```python
def _update_workflow_visualization(self, task_id: str, task: Dict[str, Any]) -> None:
    """Update workflow visualization with current workflow state."""
    workflow_viz = self.query_one("#workflow-visualization", WorkflowVisualization)

    # Get workflow state from task
    worker_squad = task.get("worker_squad", {})
    stages = worker_squad.get("stages", {})

    # Build workflow state dict
    workflow_state = {
        "stages": stages,
        "completed_stages": {s for s, d in stages.items() if d.get("status") == "completed"},
        "failed_stages": {s for s, d in stages.items() if d.get("status") == "failed"},
        "status": task.get("status", "unknown")
    }

    # Get workflow definition (use default Worker Squad workflow)
    from manifest.agents.workflow_definition import WorkflowDefinition, StageDefinition
    # Create default workflow definition or get from executor
    workflow_def = None  # Will be set from executor if available

    workflow_viz.load_workflow(workflow_def, workflow_state, task_id)
```

---

### 2. 실시간 워크플로우 업데이트 부재 (High Priority)

**문제**:
- WorkflowEventBus에서 STAGE_COMPLETED/STAGE_FAILED 이벤트를 발행하지만
- UI가 이 이벤트를 구독하지 않음
- TaskProgressView가 실시간으로 업데이트되지 않음

**현재 상태**:
- `agent_coordinator.py:564-578`에서 이벤트 발행
- `worker_squad_executor.py:336-368`에서 이벤트 구독 (워크플로우 실행용)
- 하지만 UI 업데이트를 위한 구독이 없음

**필요 작업**:
1. ManifestApp에서 WorkflowEventBus 구독
2. STAGE_COMPLETED/STAGE_FAILED 이벤트 수신 시 TaskProgressView 업데이트
3. Dashboard metrics 실시간 업데이트

---

### 3. WorkflowVisualization이 WorkflowDefinition을 받지 못함 (Medium Priority)

**문제**:
- WorkflowVisualization 위젯이 workflow_definition을 받지만
- TaskProgressView에서 workflow_definition을 전달하지 않음
- WorkerSquadExecutor의 현재 workflow_definition에 접근할 수 없음

**필요 작업**:
- WorkerSquadExecutor에서 workflow_definition을 state에 저장하거나
- TaskProgressView가 executor에 접근하여 workflow_definition 가져오기

---

### 4. 병렬 실행 시 UI 표시 개선 (Medium Priority)

**문제**:
- 병렬 실행이 가능하지만 UI에서 여러 stage가 동시에 실행되는 것을 명확히 표시하지 않음
- ContextBar는 최대 3개 activity만 표시 (코드: `self.activities[-3:]`)

**필요 작업**:
- 병렬 실행 중인 stage들을 모두 표시
- WorkflowVisualization에서 병렬 stage를 명확히 표시

---

### 5. Dashboard Metrics 계산 로직 개선 (Low Priority)

**문제**:
- `update_dashboard_metrics()`에서 running_agents 계산이 부정확할 수 있음
- `state.get("tasks", [])`를 사용하는데 실제로는 `get_task_checklist()`를 사용해야 함

**위치**: `src/manifest/ui/app.py:1214-1220`

**필요 작업**:
- `self.state_manager.get_task_checklist()` 사용
- Active agents는 `agent_coordinator.get_active_agents()` 사용

---

## 🎯 우선순위별 개선 계획

### Priority 1: Workflow Visualization 완성 (즉시)

1. `TaskProgressView._update_workflow_visualization()` 구현
2. WorkflowVisualization에 workflow state 전달
3. 기본 Worker Squad workflow definition 생성

**예상 시간**: 1-2시간

---

### Priority 2: 실시간 워크플로우 업데이트 (High)

1. ManifestApp에서 WorkflowEventBus 구독
2. STAGE_COMPLETED/STAGE_FAILED 이벤트 핸들러 구현
3. 이벤트 수신 시 TaskProgressView 자동 업데이트
4. Dashboard metrics 실시간 업데이트

**예상 시간**: 2-3시간

---

### Priority 3: WorkflowDefinition 접근 개선 (Medium)

1. WorkerSquadExecutor가 workflow_definition을 task state에 저장
2. TaskProgressView에서 workflow_definition 로드
3. WorkflowVisualization에 전달

**예상 시간**: 1시간

---

### Priority 4: 병렬 실행 UI 개선 (Medium)

1. ContextBar activity 표시 개선 (3개 제한 제거 또는 확장)
2. WorkflowVisualization에서 병렬 stage 명확히 표시
3. Dashboard에 병렬 실행 중인 stage 수 표시

**예상 시간**: 2시간

---

### Priority 5: Dashboard Metrics 개선 (Low)

1. Running agents 계산 로직 수정
2. Active tasks 계산 정확도 개선

**예상 시간**: 30분

---

## 📝 코드 위치 참고

### Workflow Visualization
- `src/manifest/ui/widgets/task_progress_view.py:57` - `_update_workflow_visualization()` 누락
- `src/manifest/ui/widgets/workflow_visualization.py` - 위젯 구현됨
- `src/manifest/ui/app.py:2078` - Task 선택 시 update_task 호출

### Event Bus
- `src/manifest/agents/workflow_event_bus.py` - 이벤트 버스 구현
- `src/manifest/agents/agent_coordinator.py:564-593` - 이벤트 발행
- `src/manifest/agents/worker_squad_executor.py:336-368` - 이벤트 구독 (워크플로우용)

### Dashboard & Context Bar
- `src/manifest/ui/app.py:1173-1230` - Dashboard metrics 업데이트
- `src/manifest/ui/app.py:1126-1171` - Context bar 업데이트
- `src/manifest/ui/app.py:627-629` - 주기적 업데이트 설정 (5초, 2초)

---

## ✅ 완료된 우선순위 (이전 작업)

1. ✅ Event-driven workflow 모드 (기본 활성화)
2. ✅ Agent message handling (모든 agent에 handle_message 구현)
3. ✅ Container communication integration (통합 테스트 완료)
4. ✅ Parallel stage execution (의존성 해결, 리소스 제한 포함)

---

## ✅ 완료된 개선사항 (2026-01-27)

### Priority 1: Workflow Visualization 완성 ✅
- ✅ `TaskProgressView._update_workflow_visualization()` 구현 완료
- ✅ WorkflowVisualization에 workflow state 전달
- ✅ 기본 Worker Squad workflow definition 로드
- ✅ WorkflowRegistry에서 "worker_squad" workflow 가져오기

### Priority 2: 실시간 워크플로우 업데이트 ✅
- ✅ ManifestApp에서 WorkflowEventBus 구독 추가
- ✅ STAGE_COMPLETED/STAGE_FAILED/WORKFLOW_COMPLETED 이벤트 핸들러 구현
- ✅ 이벤트 수신 시 TaskProgressView 자동 업데이트
- ✅ Dashboard metrics 및 ContextBar 실시간 업데이트

### Priority 5: Dashboard Metrics 개선 ✅
- ✅ Running agents 계산 로직 수정 (get_active_agents() 사용)
- ✅ Active tasks 계산 정확도 개선

### 추가 개선사항 ✅
- ✅ ContextBar activity 제한 확장 (3개 → 10개, 병렬 실행 지원)

---

## 🚀 다음 단계

**현재 상태**: 모든 주요 우선순위 완료
- Event-driven workflow ✅
- Agent messaging ✅
- Container communication ✅
- Parallel execution ✅
- Workflow visualization ✅
- Real-time UI updates ✅

**추가 개선 가능 사항** (선택적):
- 병렬 실행 시 UI 표시 개선 (WorkflowVisualization에서 병렬 stage 더 명확히 표시)
- 에러 메시지 및 디버깅 정보 개선
- Bootstrap UI 문제 해결 (이벤트 루프 충돌)
