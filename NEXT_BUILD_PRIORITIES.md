# Next Build Priorities - Manifest Project

**Date**: 2026-01-27
**Last Updated**: 2026-01-27
**Based on**: Actual codebase review (not docs)

---

## 🔍 Current State Analysis

### ✅ Fully Implemented (Working)
1. **runner.py** - All agent types handled (orchestrator, planner, coder, test, debug, approver, project_review, e2e_test, integration_test)
2. **prompt_hooks.py** - Fully implemented and integrated in executor (VisualRealityHook, PolicyInjectionHook)
3. **shadow_manager.py** - Complete implementation with sandbox support
4. **agent_message_bus.py** - Infrastructure complete, registered in agent_bridge
5. **container_api.py** - Implemented and started in app.py
6. **worker_squad_executor.py** - Sequential and event-driven mode fully working
7. **Event-driven workflow mode** - ✅ Enabled by default (MANIFEST_EVENT_DRIVEN=true)
8. **Agent-to-agent messaging** - ✅ All agents implement handle_message()
9. **Container communication** - ✅ Full integration tests complete
10. **Parallel stage execution** - ✅ Implemented with dependency resolution and resource limits
11. **Workflow visualization** - ✅ Basic implementation complete, real-time updates added

### ⚠️ Recently Completed (2026-01-27)
1. ✅ **Event-driven workflow mode** - Enabled by default, fully tested
2. ✅ **Agent-to-agent messaging** - All agents (planner, coder, test, debug) implement handle_message()
3. ✅ **Container communication** - Full integration tests (8 tests) passing
4. ✅ **Parallel stage execution** - Dependency resolution, resource limits, tracking implemented
5. ✅ **Workflow visualization** - _update_workflow_visualization() implemented, real-time event subscriptions added

---

## 🎯 Recommended Next Build Priorities

### ✅ Priority 1: Enable Event-Driven Workflow Mode (COMPLETED)

**Status**: ✅ Completed (2026-01-27)

**What was done**:
- ✅ Event-driven mode enabled by default (MANIFEST_EVENT_DRIVEN=true)
- ✅ All agent completions publish `STAGE_COMPLETED`/`STAGE_FAILED` events
- ✅ Event-driven workflow end-to-end tested (7 integration tests)
- ✅ Fallback to sequential mode if events fail

**Result**: Event-driven workflow fully operational

---

### ✅ Priority 2: Implement Agent Message Handling (COMPLETED)

**Status**: ✅ Completed (2026-01-27)

**What was done**:
- ✅ All agents implement `handle_message()` method (planner, coder, test, debug)
- ✅ Message handlers for each agent type implemented
- ✅ Message bus correlation_id 수정 (이벤트 전달 전 설정)
- ✅ Agent-to-agent communication tested (6 integration tests)

**Result**: Agents can now communicate via message bus

---

### ✅ Priority 3: Complete Container Communication Integration (COMPLETED)

**Status**: ✅ Completed (2026-01-27)

**What was done**:
- ✅ Full end-to-end testing of container communication (8 integration tests)
- ✅ State synchronization verified and tested
- ✅ Error handling for container failures tested
- ✅ Container API endpoints fully tested

**Result**: Container communication fully integrated and tested

---

### ✅ Priority 4: Parallel Stage Execution (COMPLETED)

**Status**: ✅ Completed (2026-01-27)

**What was done**:
- ✅ Dependency graph resolution implemented
- ✅ Parallel stage execution logic with task tracking
- ✅ Resource limits (max_concurrent_stages, default: 3)
- ✅ Parallel execution tested (9 integration tests)

**Result**: Independent stages can run in parallel with proper dependency resolution

---

## 🎯 Current Next Priorities (2026-01-27)

### Priority 1: Workflow Visualization 완성 (HIGH IMPACT)

**Status**: ✅ Just Completed

**What was done**:
- ✅ `TaskProgressView._update_workflow_visualization()` 구현
- ✅ WorkflowVisualization에 workflow state 전달
- ✅ 기본 Worker Squad workflow definition 로드
- ✅ 실시간 워크플로우 업데이트 (이벤트 구독 추가)
- ✅ Dashboard metrics 계산 로직 개선

**Result**: Task 선택 시 workflow 시각화가 표시되고, stage 완료 시 실시간 업데이트됨

---

### Priority 2: UI 개선 및 사용자 경험 향상 (MEDIUM IMPACT)

**Status**: Ongoing improvements

**개선 사항**:
- ✅ ContextBar activity 제한 확장 (3개 → 10개)
- ✅ 실시간 workflow 이벤트 구독
- ⚠️ 병렬 실행 시 UI 표시 개선 (부분 완료)

**추가 개선 가능 사항**:
- WorkflowVisualization에서 병렬 stage를 더 명확히 표시
- Dashboard에 병렬 실행 중인 stage 수 표시
- 에러 메시지 및 디버깅 정보 개선

---

## 📊 Completed Priorities Summary

| Feature | Status | Completion Date |
|---------|--------|----------------|
| Event-driven mode | ✅ Complete | 2026-01-27 |
| Agent messaging | ✅ Complete | 2026-01-27 |
| Container integration | ✅ Complete | 2026-01-27 |
| Parallel execution | ✅ Complete | 2026-01-27 |
| Workflow visualization | ✅ Complete | 2026-01-27 |

---

## 🚫 NOT Recommended Now

### Don't Build These Yet:
1. **New agent types** - Current set is sufficient
2. **New workflow types** - Worker squad covers most needs
3. **Advanced UI features** - Core functionality is more important
4. **Performance optimizations** - Not a bottleneck yet

---

## 💡 Recent Improvements (2026-01-27)

1. ✅ **Event-driven mode** - Enabled by default, fully tested
2. ✅ **Agent message handling** - All agents implement handle_message()
3. ✅ **Container communication** - Full integration tests complete
4. ✅ **Parallel execution** - Dependency resolution and resource limits
5. ✅ **Workflow visualization** - Real-time updates via event subscriptions

---

## 🔍 Code Locations

### Event-Driven Mode:
- `src/manifest/agents/worker_squad_executor.py` - Event-driven mode (enabled by default)
- `src/manifest/agents/workflow_event_bus.py` - Event bus implementation
- `src/manifest/ui/app.py` - UI event subscriptions for real-time updates

### Agent Messaging:
- `src/manifest/agents/agent_message_bus.py` - Message bus
- `src/manifest/bridge/agent_bridge.py` - Agent registration
- `src/manifest/runtime/agent/agents/*.py` - All agents implement handle_message()

### Container Communication:
- `src/manifest/agents/container_communication.py` - Message bus and state sync
- `src/manifest/agents/container_api.py` - HTTP API
- `src/manifest/agents/container_manager.py` - Docker operations
- `tests/integration/test_container_communication_integration.py` - Integration tests

### Parallel Execution:
- `src/manifest/agents/worker_squad_executor.py` - Parallel execution logic
- `src/manifest/agents/workflow_definition.py` - Dependency resolution
- `tests/integration/test_parallel_stage_execution.py` - Integration tests

### Workflow Visualization:
- `src/manifest/ui/widgets/task_progress_view.py` - Task progress view
- `src/manifest/ui/widgets/workflow_visualization.py` - Workflow graph visualization
- `src/manifest/ui/app.py` - Real-time event subscriptions

---

**Conclusion**: All 4 original priorities completed. Current focus: UI improvements and user experience enhancements.
