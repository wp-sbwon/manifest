# E2E 테스트 커버리지 (API 키 없이 실행 가능)

**작성일**: 2026-01-28

## 개요

현재 e2e 테스트는 **API 키 없이도 모두 실행 가능**합니다. 이는 대부분의 테스트가 실제 LLM API 호출을 하지 않고, coordinator 레벨에서 mock을 사용하기 때문입니다.

## 테스트 범위 (59개 테스트)

### ✅ 보장되는 범위 (API 키 불필요)

#### 1. **Mission/Task 생성 및 관리** (`test_mission_creation_execution.py`, `test_manual_task_creation_execution.py`)
- ✅ Mission 생성 및 persistence
- ✅ Task 생성 및 상태 관리
- ✅ Task extraction from mission
- ✅ State persistence throughout workflow
- ✅ UI 업데이트 및 결과 표시

**Mock 사용**:
- `agent_coordinator.start_orchestrator = mock_start_orchestrator`
- `agent_coordinator.worker_squad_executor.execute = mock_execute`

#### 2. **Agent Coordination** (`test_multi_agent_coordination.py`)
- ✅ Multi-agent coordination
- ✅ Dependency enforcement
- ✅ Agent communication
- ✅ Race condition 방지
- ✅ Parallel execution where possible

**Mock 사용**:
- `agent_coordinator.start_worker_agent = track_agent`

#### 3. **Permission Approval Flow** (`test_permission_approval_flow.py`)
- ✅ Dangerous commands blocked
- ✅ Approval UI works
- ✅ Commands execute after approval
- ✅ Commands cancelled after rejection
- ✅ Multiple approval requests handling
- ✅ Approval callback execution

**특징**: 실제 터미널 명령 실행 테스트 (subprocess 사용)

#### 4. **State Management** (`test_state_recovery.py`)
- ✅ State persistence
- ✅ State recovery on restart
- ✅ Active agents restored
- ✅ Work continues seamlessly
- ✅ Corrupted file handling
- ✅ Partial data recovery

#### 5. **Blueprint Sync & Drift Detection** (`test_blueprint_sync_drift_detection.py`)
- ✅ Changes detected
- ✅ Drift correctly identified
- ✅ Conflicts classified correctly
- ✅ Resolution workflow works
- ✅ File watcher triggers drift detection

#### 6. **Large Mission Handling** (`test_large_mission_handling.py`)
- ✅ All tasks created
- ✅ Execution efficiency
- ✅ No memory leaks
- ✅ Results correctness
- ✅ Parallel execution works
- ✅ State persistence during execution

#### 7. **Network/API Failure Handling** (`test_network_api_failure.py`)
- ✅ Retries work correctly
- ✅ Errors handled gracefully
- ✅ User informed
- ✅ State not lost
- ✅ Rate limit handling
- ✅ Network timeout handling

**Mock 사용**:
- `agent_coordinator.start_worker_agent_and_wait = mock_agent_execution`

#### 8. **Agent Failure Recovery** (`test_agent_failure_recovery.py`)
- ✅ Failures detected
- ✅ Recovery strategies work
- ✅ State not corrupted
- ✅ Workflow can continue
- ✅ Timeout failure detection
- ✅ Error failure detection

## ❌ 보장되지 않는 범위 (실제 LLM API 호출 필요)

### 실제 LLM API 호출
- ❌ 실제 LLM 응답 품질
- ❌ 실제 코드 생성
- ❌ 실제 코드 실행 결과
- ❌ OpenCode 서버 통신
- ❌ Tool execution 결과의 정확성

### 실제 Agent 실행
- ❌ OrchestratorAgent의 실제 mission breakdown
- ❌ PlannerAgent의 실제 plan 생성
- ❌ CoderAgent의 실제 코드 작성
- ❌ TestAgent의 실제 테스트 실행

## Mock 전략

### 1. Coordinator 레벨 Mock
```python
# Orchestrator mock
agent_coordinator.start_orchestrator = mock_start_orchestrator

# Worker agent mock
agent_coordinator.start_worker_agent = track_agent

# Worker squad executor mock
agent_coordinator.worker_squad_executor.execute = mock_execute
```

### 2. Executor 생성은 하지만 호출하지 않음
- `AgentBridge`가 생성될 때 `ExecutorFactory.create_executor()` 호출
- 하지만 실제 `executor.execute_agent()`는 호출되지 않음
- Coordinator 레벨에서 mock하므로 executor까지 도달하지 않음

### 3. 실제 실행되는 부분
- ✅ Terminal command execution (subprocess)
- ✅ File operations
- ✅ State management
- ✅ Permission checking
- ✅ Blueprint file operations

## 테스트 실행 방법

```bash
# API 키 없이 모든 e2e 테스트 실행
PYTHONPATH=src pytest tests/e2e/ -v

# 특정 테스트만 실행
PYTHONPATH=src pytest tests/e2e/test_permission_approval_flow.py -v
```

## 결론

**현재 e2e 테스트는**:
- ✅ **시스템 통합 및 워크플로우**를 완전히 보장
- ✅ **상태 관리, 복구, coordination** 등을 검증
- ✅ **API 키 없이 실행 가능**
- ❌ **실제 LLM API 호출 및 코드 생성**은 검증하지 않음

**실제 LLM 기능을 테스트하려면**:
- Integration test 필요 (실제 API 키 사용)
- 또는 실제 OpenCode 서버와 통신하는 테스트 필요
