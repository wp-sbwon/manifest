# Test Definition List (TDL) - Manifest

**Purpose**: Define what "100% meaningful test coverage" means for Manifest
**Last Updated**: 2026-01-26
**Coverage Goal**: Meaningful coverage of business logic, critical paths, and user workflows

## Progress Summary

**Completed**:
- ✅ Agent Coordinator (28 tests) - All coordination logic covered
- ✅ Worker Squad Executor (28 tests) - All workflow logic covered
- ✅ State Management (27 tests) - All business logic covered
- ✅ Configuration (25 tests) - All security-critical paths covered
- ✅ Task Management (30 tests) - All operations covered
- ✅ Context Provider (23 tests) - All context logic covered
- ✅ Task Scoper (21 tests) - All scoping logic covered
- ✅ Orchestrator Agent (13 tests) - All orchestration logic covered
- ✅ Planner Agent (19 tests) - All planning logic covered
- ✅ Coder Agent (16 tests) - All coding logic covered
- ✅ Test Agent (16 tests) - All test generation logic covered
- ✅ Debug Agent (11 tests) - All debugging logic covered
- ✅ Terminal Router (28 tests) - All routing logic covered
- ✅ Tool Executor (42 tests) - All tool execution logic covered
- ✅ Drift Auditor (22 tests) - All drift detection logic covered
- ✅ Blueprint Synchronizer (28 tests) - All sync logic covered
- ✅ Agent Message Bus (45 tests) - All messaging logic covered
- ✅ Workflow Event Bus (29 tests) - All event logic covered
- ✅ Command Handler (42 tests) - All command logic covered
- ✅ Channel Manager (25 tests) - All channel logic covered
- ✅ Permission Manager (36 tests) - All permission logic covered
- ✅ File Watcher (36 tests) - All watching logic covered
- ✅ Structure Manager (30 tests) - All structure logic covered

**Integration Tests Completed**:
- ✅ Agent Bridge → Agent Coordinator (8 tests) - All integration paths covered
- ✅ Agent Coordinator → Worker Squad Executor (11 tests) - All workflow integration covered
- ✅ Context Provider → Agent Execution (11 tests) - All context integration covered
- ✅ State Manager → All Components (12 tests) - All state management integration covered
- ✅ Blueprint Synchronizer → Drift Auditor (8 tests) - All blueprint-drift integration covered
- ✅ Tool Executor → Terminal Router (9 tests) - All tool-terminal integration covered
- ✅ Tool Executor → Permission Manager (8 tests) - All tool-permission integration covered
- ✅ File Watcher → Drift Auditor (8 tests) - All file-drift integration covered
- ✅ App → Command Handler → Agent Coordinator (11 tests) - All UI-command integration covered
- ✅ App → Channel Manager → Agent Bridge (11 tests) - All channel management integration covered

**In Progress**:
- 🔄 Next component - TBD

**Total Tests**: 1115 passing

## Test Coverage Philosophy

**100% Coverage Definition**: Not line-by-line coverage, but:
- ✅ All critical business logic paths tested
- ✅ All error handling scenarios covered
- ✅ All user workflows validated end-to-end
- ✅ All agent coordination patterns verified
- ✅ All state management operations tested
- ✅ All integration points validated

**Excluded from "100%"**:
- ❌ Logger calls (debug/warning/error)
- ❌ Trivial getters/setters without logic
- ❌ Enum definitions
- ❌ Simple data structure initialization

---

## 1. UNIT TESTS

### 1.1 Core Infrastructure

#### State Management (`state_manager.py`)
**Priority**: CRITICAL
**Coverage Target**: 100% of business logic
**Status**: ✅ COMPLETED (27 tests)

- [x] State persistence (save/load)
- [x] Mission tree operations (add/update/remove)
- [x] Task checklist management
- [x] Chat history persistence
- [x] Sprint management (create/list/load)
- [x] State recovery after crash
- [x] Concurrent access handling
- [x] Invalid state handling
- [x] State migration/versioning

#### Configuration (`config.py`)
**Priority**: HIGH
**Coverage Target**: 100% of security-critical paths
**Status**: ✅ COMPLETED (25 tests)

- [x] API key encryption/decryption
- [x] API key validation
- [x] Missing key handling
- [x] Invalid key format handling
- [x] Key rotation
- [x] Configuration persistence

#### Task Management (`task_manager.py`)
**Priority**: HIGH
**Coverage Target**: 100% of operations
**Status**: ✅ COMPLETED (30 tests)

- [x] Task creation with validation
- [x] Task updates (status, stage, dependencies)
- [x] Task dependencies resolution
- [x] Task filtering/queries
- [x] Task deletion
- [x] Invalid task data handling

### 1.2 Agent System

#### Agent Coordinator (`agent_coordinator.py`)
**Priority**: CRITICAL
**Coverage Target**: 100% of coordination logic
**Status**: ✅ COMPLETED (28 tests)

- [x] Orchestrator startup and mission handling
- [x] Worker agent startup (planner, coder, test, etc.)
- [x] Agent lifecycle management (start/stop/status)
- [x] Agent communication routing
- [x] Task scoping and validation
- [x] Context provisioning per agent type
- [x] Error recovery and retry logic
- [x] Agent timeout handling
- [x] Container vs direct execution modes

#### Worker Squad Executor (`worker_squad_executor.py`)
**Priority**: CRITICAL
**Coverage Target**: 100% of workflow logic
**Status**: ✅ COMPLETED (28 tests)

- [x] Complete TDD workflow execution
- [x] Stage sequencing (planner → test → coder → test → debug → review → approver)
- [x] Stage completion detection
- [x] Stage failure handling and retry
- [x] Previous stage data passing
- [x] Workflow termination conditions
- [x] Event-driven vs sequential modes
- [x] Workflow state persistence

#### Context Provider (`context_provider.py`)
**Priority**: HIGH
**Coverage Target**: 100% of context logic
**Status**: ✅ COMPLETED (23 tests)

- [x] Tier 0 context (manifest-policy.md)
- [x] Tier 1 context (architecture.json)
- [x] Tier 2 context (blueprint.json scoped)
- [x] Tier 3 context (surgical code files)
- [x] Context size calculation
- [x] Context validation
- [x] Agent-specific context filtering

#### Task Scoper (`task_scoper.py`)
**Priority**: HIGH
**Coverage Target**: 100% of scoping logic
**Status**: ✅ COMPLETED (21 tests)

- [x] Task granularity validation
- [x] Component scope extraction
- [x] File scope determination
- [x] Dependency analysis
- [x] Scope boundary enforcement

### 1.3 Agent Implementations

#### Orchestrator Agent (`orchestrator_agent.py`)
**Priority**: HIGH
**Coverage Target**: 100% of orchestration logic
**Status**: ✅ COMPLETED (13 tests)

- [x] Mission breakdown
- [x] Task extraction from responses
- [x] Task dependency analysis
- [x] Mission state management
- [x] Response streaming and parsing

#### Planner Agent (`planner_agent.py`)
**Priority**: HIGH
**Coverage Target**: 100% of planning logic
**Status**: ✅ COMPLETED (19 tests)

- [x] Plan generation
- [x] Plan validation
- [x] Plan updates
- [x] Plan compliance checking

#### Coder Agent (`coder_agent.py`)
**Priority**: HIGH
**Coverage Target**: 100% of coding logic
**Status**: ✅ COMPLETED (16 tests)

- [x] Code implementation
- [x] Self-review functionality
- [x] Plan compliance checking
- [x] Code quality validation

#### Test Agents (`test_agent.py`, `integration_test_agent.py`, `e2e_test_agent.py`)
**Priority**: MEDIUM
**Coverage Target**: 100% of test generation logic
**Status**: ✅ COMPLETED (16 tests)

- [x] Test skeleton generation
- [x] Test execution
- [x] Test result parsing
- [x] Test failure analysis

#### Debug Agent (`debug_agent.py`)
**Priority**: HIGH
**Coverage Target**: 100% of debugging logic
**Status**: ✅ COMPLETED (11 tests)

- [x] Bug analysis from test failures
- [x] Root cause identification
- [x] Fix proposal generation

### 1.4 Communication & Messaging

#### Agent Message Bus (`agent_message_bus.py`)
**Priority**: HIGH
**Coverage Target**: 95%+ (already at 94%)
**Status**: ✅ COMPLETED (45 tests)

- [x] Message routing (direct, type-based, broadcast)
- [x] Request-response pattern
- [x] Message history and filtering
- [x] Error handling in delivery
- [x] Message timeout handling
- [x] Message correlation

#### Workflow Event Bus (`workflow_event_bus.py`)
**Priority**: HIGH
**Coverage Target**: 95%+ (already at 97%)
**Status**: ✅ COMPLETED (29 tests)

- [x] Event publishing
- [x] Event subscription/unsubscription
- [x] Event history and filtering
- [x] Error handling in callbacks
- [x] Event-driven workflow triggers

### 1.5 Runtime Components

#### Terminal Router (`terminal_router.py`)
**Priority**: HIGH
**Coverage Target**: 100% of routing logic
**Status**: ✅ COMPLETED (28 tests)

- [x] Command execution (OpenCode vs subprocess)
- [x] Permission checking
- [x] Permission approval flow
- [x] Command result parsing
- [x] Error handling
- [x] Working directory management

#### Tool Executor (`tool_executor.py`)
**Priority**: HIGH
**Coverage Target**: 100% of tool execution
**Status**: ✅ COMPLETED (42 tests)

- [x] Tool call parsing
- [x] Tool execution (file ops, git, etc.)
- [x] Tool result validation
- [x] Tool error handling
- [x] Tool audit logging

#### Permission Manager (`permission_manager.py`)
**Priority**: MEDIUM
**Coverage Target**: 100% of permission logic
**Status**: ✅ COMPLETED (36 tests)

- [x] Permission rule evaluation
- [x] Permission approval workflow
- [x] Permission caching
- [x] Rule persistence

### 1.6 Audit & Monitoring

#### Drift Auditor (`drift_auditor.py`)
**Priority**: HIGH
**Coverage Target**: 100% of drift detection
**Status**: ✅ COMPLETED (22 tests)

- [x] Blueprint vs code comparison
- [x] Drift severity classification
- [x] Conflict detection
- [x] Drift resolution suggestions

#### Blueprint Synchronizer (`blueprint_synchronizer.py`)
**Priority**: HIGH
**Coverage Target**: 100% of sync logic
**Status**: ✅ COMPLETED (28 tests)

- [x] Blueprint loading
- [x] Blueprint saving
- [x] Conflict detection
- [x] Conflict resolution
- [x] Blueprint validation

#### File Watcher (`file_watcher.py`)
**Priority**: MEDIUM
**Coverage Target**: 100% of watching logic
**Status**: ✅ COMPLETED (36 tests)

- [x] File change detection
- [x] Git diff extraction
- [x] Change callback invocation
- [x] Blueprint change detection

#### Structure Manager (`structure_manager.py`)
**Priority**: MEDIUM
**Coverage Target**: 100% of structure logic
**Status**: ✅ COMPLETED (30 tests)

- [x] Structure analysis
- [x] Structure drift detection
- [x] Structure change suggestions

### 1.7 UI Components (Unit Tests)

#### Command Handler (`command_handler.py`)
**Priority**: HIGH
**Coverage Target**: 100% of command logic
**Status**: ✅ COMPLETED (42 tests)

- [x] Command parsing
- [x] Command routing
- [x] Command validation
- [x] Command execution
- [x] Error handling

#### Channel Manager (`channel_manager.py`)
**Priority**: MEDIUM
**Coverage Target**: 100% of channel logic
**Status**: ✅ COMPLETED (25 tests)

- [x] Channel creation
- [x] Channel switching
- [x] Message routing to channels
- [x] Channel state management

---

## 2. INTEGRATION TESTS

### 2.1 Agent Coordination Integration

#### Agent Bridge → Agent Coordinator
**Priority**: CRITICAL
**Status**: ✅ COMPLETED (8 tests)

- [x] Agent startup through bridge
- [x] Message passing through bridge
- [x] Status reporting
- [x] Error propagation

#### Agent Coordinator → Worker Squad Executor
**Priority**: CRITICAL
**Status**: ✅ COMPLETED (11 tests)

- [x] Task execution workflow
- [x] Stage transitions
- [x] Event publishing and handling
- [x] State persistence during workflow

#### Context Provider → Agent Execution
**Priority**: HIGH
**Status**: ✅ COMPLETED (11 tests)

- [x] Context delivery to agents
- [x] Context size validation
- [x] Tier-based context filtering
- [x] Context updates during execution

### 2.2 State Management Integration

#### State Manager → All Components
**Priority**: CRITICAL
**Status**: ✅ COMPLETED (12 tests)

- [x] State persistence across operations
- [x] State recovery after restart
- [x] Concurrent state updates
- [x] State consistency validation

### 2.3 Blueprint & Drift Integration

#### Blueprint Synchronizer → Drift Auditor
**Priority**: HIGH
**Status**: ✅ COMPLETED (8 tests)

- [x] Blueprint sync triggers drift check
- [x] Drift detection after sync
- [x] Conflict resolution workflow

#### File Watcher → Drift Auditor
**Priority**: MEDIUM
**Status**: ✅ COMPLETED (8 tests)

- [x] File changes trigger drift check
- [x] Real-time drift detection

### 2.4 Tool Execution Integration

#### Tool Executor → Terminal Router
**Priority**: HIGH
**Status**: ✅ COMPLETED (9 tests)

- [x] Tool calls execute commands
- [x] Permission checks before execution
- [x] Result parsing and validation

#### Tool Executor → Permission Manager
**Priority**: HIGH
**Status**: ✅ COMPLETED (8 tests)

- [x] Permission checks for tool execution
- [x] Approval workflow integration

### 2.5 UI Integration

#### App → Command Handler → Agent Coordinator
**Priority**: CRITICAL
**Status**: ✅ COMPLETED (11 tests)

- [x] User commands trigger agent actions
- [x] Command parsing and routing
- [x] Response display

#### App → Channel Manager → Agent Bridge
**Priority**: HIGH
**Status**: ✅ COMPLETED (11 tests)

- [x] Agent output routed to channels
- [x] Channel state updates
- [x] Multi-channel management

---

## 3. END-TO-END (E2E) TESTS

### 3.1 Complete User Workflows

#### Workflow 1: Mission Creation & Execution
**Priority**: CRITICAL
**Status**: ✅ COMPLETED (6 tests)
**Description**: User creates mission, orchestrator breaks it down, tasks execute

**Steps**:
1. User starts app
2. User enters mission description
3. Orchestrator processes mission
4. Tasks are automatically created
5. Worker Squad executes tasks
6. Results are displayed

**Validation**:
- [x] Mission is created and persisted
- [x] Tasks are correctly extracted
- [x] Worker Squad completes all stages
- [x] State is persisted throughout
- [x] Results are displayed in UI

#### Workflow 2: Manual Task Creation & Execution
**Priority**: HIGH
**Status**: ✅ COMPLETED (6 tests)
**Description**: User manually creates task and starts agent

**Steps**:
1. User creates task via command
2. User starts planner agent
3. Planner completes
4. User starts coder agent
5. Coder completes
6. User reviews results

**Validation**:
- [x] Task is created correctly
- [x] Agent starts and completes
- [x] Results are saved
- [x] State is updated

#### Workflow 3: Blueprint Sync & Drift Detection
**Priority**: HIGH
**Description**: Code changes trigger drift detection

**Steps**:
1. User modifies code
2. File watcher detects change
3. Drift auditor compares with blueprint
4. Conflicts are reported
5. User resolves conflicts

**Validation**:
- [ ] Changes are detected
- [ ] Drift is correctly identified
- [ ] Conflicts are classified correctly
- [ ] Resolution workflow works

#### Workflow 4: State Recovery
**Priority**: CRITICAL
**Description**: App restarts and recovers previous state

**Steps**:
1. User works on mission
2. App crashes or is closed
3. App restarts
4. State is recovered
5. User continues work

**Validation**:
- [ ] State is persisted correctly
- [ ] State is recovered on restart
- [ ] Active agents are restored
- [ ] Work can continue seamlessly

#### Workflow 5: Multi-Agent Coordination
**Priority**: CRITICAL
**Description**: Multiple agents work on related tasks

**Steps**:
1. Multiple tasks are created
2. Agents start in parallel where possible
3. Agents communicate via message bus
4. Dependencies are respected
5. All tasks complete

**Validation**:
- [ ] Agents coordinate correctly
- [ ] Dependencies are enforced
- [ ] Communication works
- [ ] No race conditions

#### Workflow 6: Permission Approval Flow
**Priority**: MEDIUM
**Description**: Dangerous command requires approval

**Steps**:
1. Agent attempts dangerous command
2. Permission manager blocks it
3. Approval request is shown
4. User approves/rejects
5. Command executes or is cancelled

**Validation**:
- [ ] Dangerous commands are blocked
- [ ] Approval UI works
- [ ] Commands execute after approval
- [ ] Commands are cancelled after rejection

### 3.2 Error Recovery Workflows

#### Workflow 7: Agent Failure Recovery
**Priority**: HIGH
**Description**: Agent fails, system recovers

**Steps**:
1. Agent starts execution
2. Agent fails (timeout/error)
3. Failure is detected
4. Recovery strategy is applied
5. Agent retries or workflow continues

**Validation**:
- [ ] Failures are detected
- [ ] Recovery strategies work
- [ ] State is not corrupted
- [ ] Workflow can continue

#### Workflow 8: Network/API Failure
**Priority**: MEDIUM
**Description**: LLM API fails, system handles gracefully

**Steps**:
1. Agent makes API call
2. API fails (network error, rate limit)
3. Retry logic activates
4. After retries, error is handled
5. User is notified

**Validation**:
- [ ] Retries work correctly
- [ ] Errors are handled gracefully
- [ ] User is informed
- [ ] State is not lost

### 3.3 Performance & Scalability

#### Workflow 9: Large Mission Handling
**Priority**: MEDIUM
**Description**: Mission with many tasks executes correctly

**Steps**:
1. User creates mission with 20+ tasks
2. All tasks are created
3. Tasks execute (some in parallel)
4. All complete successfully
5. Results are aggregated

**Validation**:
- [ ] All tasks are created
- [ ] Execution is efficient
- [ ] No memory leaks
- [ ] Results are correct

---

## 4. TEST METRICS & COVERAGE TARGETS

### Coverage Targets by Category

| Category | Target | Current | Priority |
|----------|--------|---------|----------|
| Core Infrastructure | 95%+ | ~80% | CRITICAL |
| Agent System | 95%+ | ~40% | CRITICAL |
| Communication | 95%+ | ~75% | HIGH |
| Runtime Components | 90%+ | ~50% | HIGH |
| Audit & Monitoring | 90%+ | ~60% | MEDIUM |
| UI Components | 80%+ | ~30% | MEDIUM |
| Integration Tests | 100% | ~20% | CRITICAL |
| E2E Tests | 100% | ~10% | CRITICAL |

### Test Count Targets

- **Unit Tests**: ~500-600 tests
- **Integration Tests**: ~50-80 tests
- **E2E Tests**: ~15-25 tests
- **Total**: ~565-705 tests

### Critical Path Coverage

**Must have 100% coverage**:
1. Agent coordination and lifecycle
2. State persistence and recovery
3. Worker Squad workflow execution
4. Blueprint synchronization
5. Permission approval flow
6. Error recovery mechanisms

---

## 5. TEST IMPLEMENTATION PRIORITY

### Phase 1: Critical Paths (Week 1-2)
1. Agent Coordinator unit tests
2. Worker Squad Executor unit tests
3. State Manager integration tests
4. Basic E2E: Mission creation workflow

### Phase 2: Core Functionality (Week 3-4)
1. All agent implementations
2. Context Provider and Task Scoper
3. Blueprint & Drift integration
4. E2E: Multi-agent coordination

### Phase 3: Runtime & Tools (Week 5-6)
1. Terminal Router
2. Tool Executor
3. Permission Manager
4. E2E: Permission approval flow

### Phase 4: UI & Polish (Week 7-8)
1. Command Handler
2. Channel Manager
3. UI component tests
4. All remaining E2E workflows

---

## 6. TEST QUALITY CRITERIA

### Unit Tests
- ✅ Test one thing at a time
- ✅ Use mocks for external dependencies
- ✅ Test both success and failure paths
- ✅ Test edge cases and boundary conditions
- ✅ Fast execution (< 1 second per test)

### Integration Tests
- ✅ Test real component interactions
- ✅ Use test databases/filesystems
- ✅ Test error propagation
- ✅ Test state consistency
- ✅ Moderate execution time (< 10 seconds per test)

### E2E Tests
- ✅ Test complete user workflows
- ✅ Use real (but isolated) environments
- ✅ Test error recovery
- ✅ Test state persistence
- ✅ Longer execution time acceptable (< 60 seconds per test)

---

## 7. NOTES

- **Logger calls**: Not counted in coverage (debug/warning/error)
- **Trivial getters**: Not tested unless they contain logic
- **Enum definitions**: Not tested
- **Data structures**: Only test if they contain business logic
- **Focus on**: Business logic, error handling, state management, workflows

---

**Next Steps**:
1. Review and approve this TDL
2. Begin Phase 1 implementation
3. Track progress against this list
4. Update TDL as architecture evolves
