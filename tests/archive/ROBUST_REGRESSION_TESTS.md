# Robust Regression Tests - Manifest App

**Purpose**: Identify tests that remain robust and catch regressions even as new features are added.

These tests verify **core functionality** that must continue working for the Manifest app to function correctly. They are designed to be:
- ✅ **Stable**: Don't break when new features are added
- ✅ **Comprehensive**: Test complete workflows, not just individual components
- ✅ **Critical Path**: Verify functionality users depend on
- ✅ **Regression Detectors**: Catch breaking changes in core systems

---

## 🎯 Core App Functionality Tests

### 1. App Initialization & Startup
**Location**: `tests/integration/test_app.py`, `tests/unit/test_app.py`

**Critical Tests**:
- ✅ `test_app_initialization` - Verifies app can initialize with all components
- ✅ `test_state_persistence_workflow` - Verifies state can be saved and loaded
- ✅ `test_intent_data_loading` - Verifies intent.json can be loaded
- ✅ `test_blueprint_data_loading` - Verifies blueprint.json can be loaded

**Why Robust**: These test the absolute minimum required for the app to start. If these fail, the app is broken.

**What They Protect**:
- App can initialize without crashing
- Core data files can be loaded
- State persistence works

---

### 2. Complete Mission Workflow (E2E)
**Location**: `tests/e2e/test_mission_creation_execution.py`

**Critical Test**: `test_complete_mission_workflow`

**What It Tests**:
1. User enters mission description
2. Orchestrator processes mission
3. Tasks are automatically created
4. Worker Squad executes tasks
5. Results are displayed

**Why Robust**: This is the **primary user workflow**. If this breaks, the app's core value proposition is broken.

**What It Protects**:
- Mission → Task breakdown works
- Agent coordination works
- Task execution pipeline works
- State persists throughout workflow

---

### 3. State Recovery After Restart (E2E)
**Location**: `tests/e2e/test_state_recovery.py`

**Critical Test**: `test_complete_state_recovery_workflow`

**What It Tests**:
1. User works on mission (creates tasks, adds chat history)
2. App crashes/restarts
3. All state is recovered correctly

**Why Robust**: Users expect their work to persist. This is a **critical reliability feature**.

**What It Protects**:
- State persistence works correctly
- State recovery after crash works
- No data loss on restart
- All state components (missions, tasks, chat) are recovered

---

### 4. Complete Integration Workflow
**Location**: `tests/integration/test_coordinator_worker_squad.py`

**Critical Test**: `test_integration_complete_workflow_with_all_components`

**What It Tests**:
- All components (Coordinator, Bridge, State Manager, Event Bus) work together
- Complete workflow from task creation to execution
- Events are published correctly
- State is saved correctly

**Why Robust**: This verifies the **entire system integration**. If components can't work together, the app is broken.

**What It Protects**:
- Component integration works
- Event system works
- State management works across components
- Workflow orchestration works

---

### 5. Agent Lifecycle Through Bridge
**Location**: `tests/integration/test_agent_bridge.py`

**Critical Test**: `test_agent_lifecycle_through_bridge`

**What It Tests**:
- Agents can be started through the bridge
- Agent coordination works
- Task state is updated correctly

**Why Robust**: Agents are the **core execution engine**. If agents can't start, nothing works.

**What It Protects**:
- Agent startup works
- Bridge → Coordinator communication works
- Task state updates work

---

### 6. State Persistence Integration
**Location**: `tests/integration/test_state_manager_integration.py`

**Critical Test**: `test_integration_complete_workflow_state_persistence`

**What It Tests**:
- Mission creation persists
- Task creation persists
- Task status updates persist
- Chat messages persist
- All state survives restart

**Why Robust**: State persistence is **fundamental**. Without it, users lose work.

**What It Protects**:
- All state operations persist correctly
- State survives app restart
- No data corruption
- Concurrent state updates work

---

### 7. Command Handler Integration
**Location**: `tests/integration/test_app_command_handler_coordinator.py`

**Critical Test**: `test_integration_complete_command_workflow`

**What It Tests**:
- User commands are parsed correctly
- Commands trigger agent actions
- UI is updated correctly

**Why Robust**: Commands are the **primary user interface**. If commands don't work, users can't interact with the app.

**What It Protects**:
- Command parsing works
- Commands route to correct components
- Agent actions are triggered
- UI updates correctly

---

## 🔒 Critical E2E Workflows

### 8. Manual Task Creation & Execution
**Location**: `tests/e2e/test_manual_task_creation_execution.py`

**Critical Test**: `test_complete_manual_task_workflow`

**What It Tests**:
- User manually creates a task
- Agent executes the task
- Results are displayed

**Why Robust**: This is an **alternative workflow** to mission-based execution. Users need both paths to work.

---

### 9. Multi-Agent Coordination
**Location**: `tests/e2e/test_multi_agent_coordination.py`

**Critical Test**: `test_complete_multi_agent_coordination_workflow`

**What It Tests**:
- Multiple agents can work on different tasks simultaneously
- No race conditions
- State is consistent

**Why Robust**: Multi-agent coordination is **complex** and **critical**. If this breaks, parallel execution fails.

---

### 10. State Recovery Edge Cases
**Location**: `tests/e2e/test_state_recovery.py`

**Critical Tests**:
- `test_state_recovery_after_crash`
- `test_state_recovery_with_partial_data`
- `test_state_recovery_with_corrupted_file`

**Why Robust**: State recovery must work in **all scenarios**, including edge cases.

---

## 🛡️ Core Component Tests (Unit Level)

These unit tests are **critical** because they test core business logic that everything else depends on:

### State Manager Core Operations
**Location**: `tests/unit/test_state_manager.py`, `tests/unit/test_state_manager_extended.py`

**Critical Tests**:
- `test_state_persistence` - Save/load works
- `test_state_recovery_after_crash` - Recovery works
- `test_concurrent_access_handling` - Concurrent access works

**Why Robust**: State management is the **foundation**. If this breaks, everything breaks.

---

### Agent Coordinator Core Operations
**Location**: `tests/unit/test_agent_coordinator.py`

**Critical Tests**:
- `test_start_worker_agent` - Agents can start
- `test_stop_agent` - Agents can stop
- `test_execute_worker_squad` - Worker squad execution works

**Why Robust**: Agent coordination is the **execution engine**. If this breaks, no work gets done.

---

### Configuration Management
**Location**: `tests/unit/test_config.py`

**Critical Tests**:
- API key encryption/decryption
- API key validation
- Missing key handling

**Why Robust**: Configuration is **security-critical**. If this breaks, the app can't authenticate.

---

## 📊 Test Robustness Criteria

A test is considered **robust** if it:

1. ✅ **Tests Core Functionality**: Verifies functionality that users depend on
2. ✅ **Minimal Mocking**: Uses real components when possible, mocks only external dependencies
3. ✅ **Complete Workflows**: Tests end-to-end workflows, not just individual functions
4. ✅ **State Verification**: Verifies state changes, not just that code runs
5. ✅ **Error Recovery**: Tests that errors are handled gracefully
6. ✅ **Integration Focus**: Tests how components work together, not in isolation

---

## 🚨 Tests That Should ALWAYS Pass

These tests form the **safety net** for the Manifest app. If any of these fail, the app is **broken** and should not be deployed:

### Critical Path Tests (Must Pass):
1. ✅ App initialization (`test_app_initialization`)
2. ✅ State persistence (`test_state_persistence`)
3. ✅ Mission workflow (`test_complete_mission_workflow`)
4. ✅ State recovery (`test_complete_state_recovery_workflow`)
5. ✅ Agent lifecycle (`test_agent_lifecycle_through_bridge`)
6. ✅ Complete integration workflow (`test_integration_complete_workflow_with_all_components`)

### High Priority Tests (Should Pass):
7. ✅ Manual task workflow (`test_complete_manual_task_workflow`)
8. ✅ Multi-agent coordination (`test_complete_multi_agent_coordination_workflow`)
9. ✅ Command workflow (`test_integration_complete_command_workflow`)
10. ✅ State persistence integration (`test_integration_complete_workflow_state_persistence`)

---

## 🔄 Maintenance Guidelines

### When Adding New Features:

1. **Don't Break Existing Tests**: New features should not cause these robust tests to fail
2. **Add New Tests**: Add tests for new features, but keep them separate from core tests
3. **Update If Needed**: If core functionality changes, update these tests to reflect the new behavior
4. **Document Changes**: If a robust test needs to change, document why

### When Tests Fail:

1. **Investigate Immediately**: Robust test failures indicate a breaking change
2. **Fix Before Merging**: Don't merge code that breaks robust tests
3. **Update Documentation**: If behavior intentionally changes, update tests and docs

---

## 📈 Test Coverage Summary

**Total Robust Tests**: ~50+ critical tests across:
- **E2E Tests**: 10 complete workflow tests
- **Integration Tests**: 15+ component integration tests
- **Unit Tests**: 25+ core component tests

**Protection Level**:
- ✅ **Core App Functionality**: Fully protected
- ✅ **User Workflows**: Fully protected
- ✅ **State Management**: Fully protected
- ✅ **Agent Coordination**: Fully protected
- ✅ **Component Integration**: Fully protected

---

## 🎯 Conclusion

These robust regression tests ensure that:
1. **The app can start** and initialize correctly
2. **Core workflows work** end-to-end
3. **State persists** correctly
4. **Agents can execute** tasks
5. **Components integrate** correctly

**As long as these tests pass, the Manifest app's core functionality is intact**, even as new features are added.

---

**Last Updated**: 2026-01-27
**Maintained By**: Test Suite
**Review Frequency**: After major feature additions
