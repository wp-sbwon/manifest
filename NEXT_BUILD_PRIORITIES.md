# Next Build Priorities - Manifest Project

**Date**: 2026-01-27
**Based on**: Actual codebase review (not docs)

---

## 🔍 Current State Analysis

### ✅ Fully Implemented (Working)
1. **runner.py** - All agent types handled (orchestrator, planner, coder, test, debug, approver, project_review, e2e_test, integration_test)
2. **prompt_hooks.py** - Fully implemented and integrated in executor (VisualRealityHook, PolicyInjectionHook)
3. **shadow_manager.py** - Complete implementation with sandbox support
4. **agent_message_bus.py** - Infrastructure complete, registered in agent_bridge
5. **container_api.py** - Implemented and started in app.py
6. **worker_squad_executor.py** - Sequential mode fully working

### ⚠️ Partially Implemented (Needs Completion)
1. **Event-driven workflow mode** - Code exists but disabled by default (`_use_event_driven = False`)
2. **Agent-to-agent messaging** - Infrastructure exists but agents don't implement `handle_message()`
3. **Container communication** - Basic structure exists but needs full integration testing

---

## 🎯 Recommended Next Build Priorities

### Priority 1: Enable Event-Driven Workflow Mode (HIGH IMPACT)

**Status**: Code exists, just needs to be enabled and tested

**What exists**:
- `WorkerSquadExecutor.enable_event_driven()` method
- Event subscription setup (`_setup_event_subscriptions`)
- Event handlers for stage completion/failure
- Workflow state tracking

**What's missing**:
- Actually enabling it somewhere (it's always `False`)
- Testing the event-driven flow
- Ensuring events are properly published when agents complete

**Why this matters**:
- Makes workflow execution more flexible and responsive
- Allows for conditional stage execution (e.g., skip debug if tests pass)
- Enables parallel execution of independent stages
- Better error recovery (events can trigger retries)

**Implementation steps**:
1. Add option to enable event-driven mode (config or command flag)
2. Ensure all agent completions publish `STAGE_COMPLETED` events
3. Test event-driven workflow end-to-end
4. Add fallback to sequential mode if events fail

**Estimated effort**: 2-3 days

---

### Priority 2: Implement Agent Message Handling (MEDIUM IMPACT)

**Status**: Infrastructure exists, agents need to implement handlers

**What exists**:
- `AgentMessageBus` fully implemented
- Agents registered with message bus in `agent_bridge.py`
- Message routing and delivery working

**What's missing**:
- Agents don't have `handle_message()` methods
- No actual agent-to-agent communication happening
- Message handlers not implemented

**Why this matters**:
- Enables agents to request information from each other
- Allows for dynamic coordination (e.g., coder asks planner for clarification)
- Supports request-response patterns between agents
- Enables real-time agent collaboration

**Implementation steps**:
1. Add `handle_message()` method to base agent classes
2. Implement message handlers for each agent type:
   - Planner: Handle requests for plan details
   - Coder: Handle requests for implementation status
   - Test: Handle requests for test results
   - Debug: Handle requests for error analysis
3. Add message sending examples in agent execution
4. Test agent-to-agent communication

**Estimated effort**: 3-4 days

---

### Priority 3: Complete Container Communication Integration (MEDIUM IMPACT)

**Status**: Basic structure exists, needs full integration

**What exists**:
- `ContainerMessageBus` implemented
- `ContainerStateSync` implemented
- `ContainerAPI` implemented and started
- `ContainerManager` for Docker operations

**What's missing**:
- Full end-to-end testing of container communication
- State synchronization verification
- Error handling for container failures
- Container lifecycle management

**Why this matters**:
- Enables agents to run in isolated Docker containers
- Provides better security and isolation
- Allows for distributed agent execution
- Supports scaling to multiple containers

**Implementation steps**:
1. Test container communication end-to-end
2. Verify state synchronization works correctly
3. Add error handling for container failures
4. Add container health monitoring
5. Test with actual Docker containers

**Estimated effort**: 4-5 days

---

### Priority 4: Parallel Stage Execution (LOW-MEDIUM IMPACT)

**Status**: Infrastructure exists, needs implementation

**What exists**:
- `enable_parallel_execution()` method
- Workflow definition system with dependencies
- Stage dependency tracking

**What's missing**:
- Actual parallel execution logic
- Dependency resolution
- Resource management for parallel execution

**Why this matters**:
- Improves workflow throughput
- Reduces total execution time
- Better resource utilization

**Implementation steps**:
1. Implement dependency graph resolution
2. Add parallel stage execution logic
3. Add resource limits (max concurrent stages)
4. Test parallel execution

**Estimated effort**: 3-4 days

---

## 🚫 NOT Recommended Now

### Don't Build These Yet:
1. **New agent types** - Current set is sufficient
2. **New workflow types** - Worker squad covers most needs
3. **Advanced UI features** - Core functionality is more important
4. **Performance optimizations** - Not a bottleneck yet

---

## 📊 Impact vs Effort Matrix

| Feature | Impact | Effort | Priority |
|---------|--------|--------|----------|
| Event-driven mode | HIGH | LOW (2-3 days) | **1** |
| Agent messaging | MEDIUM | MEDIUM (3-4 days) | **2** |
| Container integration | MEDIUM | HIGH (4-5 days) | **3** |
| Parallel execution | LOW-MEDIUM | MEDIUM (3-4 days) | **4** |

---

## 🎯 Recommended Next Steps

### Week 1: Event-Driven Mode
1. Enable event-driven mode by default or via config
2. Ensure all agent completions publish events
3. Test event-driven workflow end-to-end
4. Add error handling and fallback

### Week 2: Agent Messaging
1. Implement `handle_message()` in base agent classes
2. Add message handlers for each agent type
3. Test agent-to-agent communication
4. Add examples of agent collaboration

### Week 3-4: Container Integration
1. Test container communication end-to-end
2. Verify state synchronization
3. Add error handling
4. Document container usage

---

## 💡 Quick Wins (Can Do Anytime)

1. **Enable event-driven mode** - Just set `_use_event_driven = True` and test
2. **Add agent message examples** - Show how agents can communicate
3. **Improve error messages** - Better debugging for workflow failures
4. **Add workflow visualization** - Show current stage in UI

---

## 🔍 Code Locations

### Event-Driven Mode:
- `src/manifest/agents/worker_squad_executor.py` (lines 80-110, 909-947)
- `src/manifest/agents/workflow_event_bus.py`

### Agent Messaging:
- `src/manifest/agents/agent_message_bus.py`
- `src/manifest/bridge/agent_bridge.py` (lines 431-450)
- `src/manifest/runtime/agent/agents/*.py` (need to add handle_message)

### Container Communication:
- `src/manifest/agents/container_communication.py`
- `src/manifest/agents/container_api.py`
- `src/manifest/agents/container_manager.py`

---

**Conclusion**: Start with **Event-Driven Mode** - it's the highest impact with lowest effort. The code is already there, just needs to be enabled and tested.
