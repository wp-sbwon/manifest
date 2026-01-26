# 코드베이스 전체 검토 및 개선 계획

**작성일**: 2026-01-24  
**검토 범위**: 전체 코드베이스 (Tool System 구조 반영)

---

## 🔍 발견된 문제점

### 1. 중복된 Agent Output 처리 ⚠️ **심각**

**문제**:
- `agent_bridge.py`의 `_handle_agent_chunk()`가 state와 channel_manager 모두 업데이트
- `channel_manager.py`의 `handle_agent_output()`도 state와 UI 업데이트
- 결과적으로 **이중 저장** 발생:
  ```python
  # agent_bridge.py:_handle_agent_chunk()
  self.state_manager.add_chat_message(channel, "assistant", content)
  await self.channel_manager.handle_agent_output(channel, content, "assistant")
  
  # channel_manager.py:handle_agent_output()
  self.state_manager.add_chat_message(channel, role, content)  # 중복!
  await self.state_manager.save_state()
  ```

**영향**:
- State에 중복 메시지 저장
- 불필요한 save_state 호출
- 성능 저하

**위치**:
- `src/manifest/bridge/agent_bridge.py:362-430`
- `src/manifest/ui/channels/channel_manager.py:288-356`

**해결 방안**:
- `_handle_agent_chunk`에서 state 저장 제거, channel_manager만 호출
- 또는 channel_manager에서 state 저장 제거, _handle_agent_chunk에서만 저장

---

### 2. 일관성 없는 Agent Output 처리 ⚠️ **중간**

**문제**:
- 일부 agent는 `_handle_agent_chunk` 사용 (planner, coder, test)
- 일부 agent는 직접 처리 (integration_test, e2e_test)
- PlannerAgent는 자체적으로 `add_chat_message` 호출 (planner_agent.py:131)

**현재 상태**:
```python
# agent_bridge.py - planner, coder, test
await self._handle_agent_chunk(chunk, channel)

# agent_bridge.py - integration_test, e2e_test
if chunk.get("type") == "chunk":
    self.state_manager.add_chat_message(channel, "assistant", chunk.get("content", ""))
# 직접 처리, _handle_agent_chunk 미사용

# planner_agent.py - 자체 처리
channel = f"squad-{self.agent_id}-planner"
self.state_manager.add_chat_message(channel, "assistant", content)
```

**영향**:
- 코드 일관성 부족
- 유지보수 어려움
- 버그 발생 가능성 증가

**위치**:
- `src/manifest/bridge/agent_bridge.py:430-643`
- `src/manifest/runtime/agent/agents/planner_agent.py:120-140`

**해결 방안**:
- 모든 agent output을 `_handle_agent_chunk`로 통일
- Agent 자체에서 state 저장하지 않도록 수정

---

### 3. Tool System 불일치 ⚠️ **중간**

**문제**:
- CoderAgent만 tool execution loop 사용
- 다른 agent들(TestAgent, DebugAgent 등)도 tool_executor를 받지만 사용하지 않음
- TestAgent는 테스트 실행을 위해 bash tool이 필요할 수 있음
- DebugAgent는 파일 읽기/수정을 위해 tool이 필요할 수 있음

**현재 상태**:
```python
# CoderAgent - tool execution loop 사용
tools = get_tool_definitions()
while iteration < max_iterations:
    async for chunk in self.executor.execute_agent(..., tools=tools):
        # tool_use 처리
    tool_results = await self.tool_executor.execute_tool_calls(...)

# TestAgent, DebugAgent 등 - tool_executor 받지만 미사용
def __init__(..., tool_executor: Optional[ToolExecutor] = None):
    self.tool_executor = tool_executor  # 받지만 사용 안 함
```

**영향**:
- Agent들이 실제로 파일 수정/명령 실행을 할 수 없음
- LLM이 tool calls를 생성해도 실행되지 않음
- 일관성 부족

**위치**:
- `src/manifest/runtime/agent/agents/coder_agent.py:64-338`
- `src/manifest/runtime/agent/agents/test_agent.py`
- `src/manifest/runtime/agent/agents/debug_agent.py`

**해결 방안**:
- TestAgent, DebugAgent 등도 tool execution loop 구현
- 또는 tool이 필요 없는 agent는 tool_executor를 받지 않도록 수정

---

### 4. 중복된 State 저장 ⚠️ **경미**

**문제**:
- `_handle_agent_chunk`에서 `save_state()` 호출
- `channel_manager.handle_agent_output`에서도 `save_state()` 호출
- 결과적으로 여러 번 저장

**현재 상태**:
```python
# agent_bridge.py:_handle_agent_chunk()
elif chunk_type == "complete":
    self.state_manager.add_chat_message(...)
    await self.state_manager.save_state()  # 저장 1
    if self.channel_manager:
        await self.channel_manager.handle_agent_output(...)  # 저장 2

# channel_manager.py:handle_agent_output()
self.state_manager.add_chat_message(channel, role, content)
await self.state_manager.save_state()  # 중복 저장!
```

**영향**:
- 불필요한 I/O 작업
- 성능 저하

**해결 방안**:
- 한 곳에서만 save_state 호출
- 또는 배치 저장으로 변경

---

### 5. 사용되지 않는 코드 ⚠️ **경미**

**문제**:
- `terminal_router`를 agent에 전달하지만 일부 agent는 사용하지 않음
- Tool system 도입 후 terminal_router 직접 사용이 줄어듦

**현재 상태**:
```python
# AgentManager.create_agent()
agent_instance = CoderAgent(..., terminal_router=terminal_router, tool_executor=tool_executor)

# CoderAgent.__init__()
self.terminal_router = terminal_router  # 받지만 직접 사용 안 함 (tool_executor 통해 사용)
```

**영향**:
- 코드 복잡도 증가
- 혼란 가능성

**해결 방안**:
- Tool system을 사용하는 agent는 terminal_router를 받지 않도록 수정
- 또는 명확한 사용 목적 문서화

---

### 6. TODO 주석 ⚠️ **기능 미구현**

**발견된 TODO**:
1. `src/manifest/ui/app.py:782`: "TODO: Add approval buttons/widgets"
2. `src/manifest/runtime/router/terminal_router.py:128`: "TODO: Implement user approval request" (Permission "ask" 처리)

**상태**: 기능 구현 필요

---

## 📊 우선순위별 개선 계획

### 🔴 Critical (즉시 수정)

#### 1. 중복된 Agent Output 처리 제거 (1일)
**작업**:
- `_handle_agent_chunk`에서 state 저장 제거
- `channel_manager.handle_agent_output`만 state 저장하도록 통일
- 또는 반대로 channel_manager에서 저장 제거

**위치**:
- `src/manifest/bridge/agent_bridge.py:362-430`
- `src/manifest/ui/channels/channel_manager.py:288-356`

**예상 작업량**: 작음 (0.5-1일)

---

#### 2. Agent Output 처리 통일 (1-2일)
**작업**:
- 모든 agent output을 `_handle_agent_chunk`로 통일
- integration_test, e2e_test도 `_handle_agent_chunk` 사용
- PlannerAgent의 자체 state 저장 제거

**위치**:
- `src/manifest/bridge/agent_bridge.py:430-643`
- `src/manifest/runtime/agent/agents/planner_agent.py:120-140`

**예상 작업량**: 작음 (1-2일)

---

### 🟡 High Priority (단기 수정)

#### 3. Tool System 일관성 확보 (2-3일)
**작업**:
- TestAgent, DebugAgent 등도 tool execution loop 구현
- 또는 tool이 필요 없는 agent는 tool_executor를 받지 않도록 수정
- Agent별 tool 사용 여부 명확화

**위치**:
- `src/manifest/runtime/agent/agents/test_agent.py`
- `src/manifest/runtime/agent/agents/debug_agent.py`
- `src/manifest/runtime/agent/core/manager.py`

**예상 작업량**: 중간 (2-3일)

---

#### 4. State 저장 최적화 (0.5일)
**작업**:
- 중복 save_state 제거
- 배치 저장 고려

**위치**:
- `src/manifest/bridge/agent_bridge.py`
- `src/manifest/ui/channels/channel_manager.py`

**예상 작업량**: 작음 (0.5일)

---

### 🟢 Medium Priority (중기 개선)

#### 5. 사용되지 않는 코드 정리 (1일)
**작업**:
- Tool system을 사용하는 agent는 terminal_router를 받지 않도록 수정
- 또는 명확한 사용 목적 문서화

**위치**:
- `src/manifest/runtime/agent/core/manager.py`
- 각 agent 클래스

**예상 작업량**: 작음 (1일)

---

#### 6. TODO 주석 처리 (1-2일)
**작업**:
- Permission "ask" 사용자 승인 UI 구현
- Approval buttons/widgets 구현

**위치**:
- `src/manifest/runtime/router/terminal_router.py:128`
- `src/manifest/ui/app.py:782`

**예상 작업량**: 작음-중간 (1-2일)

---

## 🎯 통합 개선 계획

### Phase 1: Critical 수정 (1-2일)
1. 중복된 Agent Output 처리 제거
2. Agent Output 처리 통일

### Phase 2: High Priority 수정 (2-4일)
3. Tool System 일관성 확보
4. State 저장 최적화

### Phase 3: Medium Priority 개선 (2-3일)
5. 사용되지 않는 코드 정리
6. TODO 주석 처리

---

## 📋 재정리된 우선순위 (기존 + 개선)

### 🔴 Critical Priority

1. **중복된 Agent Output 처리 제거** (0.5-1일) ⚠️ **새로운 발견**
2. **Agent Output 처리 통일** (1-2일) ⚠️ **새로운 발견**
3. **Tool Execution 완료 감지 및 결과 파싱** (2-3일) - 기존
4. **Tool Execution 에러 처리 및 복구** (2-3일) - 기존

### 🟡 High Priority

5. **Tool System 일관성 확보** (2-3일) ⚠️ **새로운 발견**
6. **State 저장 최적화** (0.5일) ⚠️ **새로운 발견**
7. **컨텍스트 크기 제한 및 Tool 사용 최적화** (4-5일) - 기존
8. **Tool Execution 결과 검증 및 테스트 연동** (2-3일) - 기존

### 🟢 Medium Priority

9. **Permission "ask" 사용자 승인 UI** (1-2일) - 기존
10. **Tool Execution 로깅 및 감사** (1-2일) - 기존
11. **사용되지 않는 코드 정리** (1일) ⚠️ **새로운 발견**

---

## ⚠️ 주의사항

1. **중복 저장 문제**는 즉시 수정 필요 (데이터 무결성 문제)
2. **일관성 문제**는 유지보수성에 직접 영향
3. **Tool System 불일치**는 기능적 문제로 확장성에 영향
4. 기존 TODO는 새로운 구조에서도 여전히 유효

---

## ✅ 검증 체크리스트

수정 후 확인 사항:
- [ ] State에 중복 메시지가 저장되지 않는지
- [ ] 모든 agent output이 일관되게 처리되는지
- [ ] Tool system이 필요한 agent에서 작동하는지
- [ ] save_state가 적절한 빈도로만 호출되는지
- [ ] 사용되지 않는 코드가 제거되었는지
