# 재검토된 우선순위 계획

**작성일**: 2026-01-24
**기준**: 새로운 Tool System, OpenCode 통합, Permission System 구조 반영

---

## 🔍 구조 변경 사항 요약

### 새로 추가된 핵심 구조
1. **Tool System (LLM Tool Use/Function Calling)**
   - Agent가 tool calls를 생성하고 실제로 실행
   - `ToolExecutor`, `FileManager`, `ToolCallParser` 구현
   - `CoderAgent`가 tool execution loop 사용

2. **OpenCode 통합**
   - `opencode-ai` 기본 의존성으로 추가
   - `OpenCodeAdapter`로 자동 설치 및 fallback
   - TerminalRouter가 OpenCode 우선 사용

3. **Permission System**
   - `PermissionManager`로 agent 타입별 권한 관리
   - OpenCode 스타일: `allow`, `ask`, `deny`
   - FileManager와 TerminalRouter에 통합

4. **Agent Output Display 개선**
   - Tool calls와 results를 UI에 실시간 표시
   - ChannelManager로 채널별 출력 분리

---

## 🔴 Critical Priority (즉시 필요)

### 1. Tool Execution 완료 감지 및 결과 파싱 ⚠️ **재평가 필요**
**현재 상태**: 부분 구현 (약 50%)

**새로운 구조에서의 변화**:
- ✅ Agent가 tool execution loop를 통해 작업 수행
- ✅ Tool calls 완료 후 "complete" chunk yield
- ⚠️ Tool execution이 완료되었는지 감지하는 로직 필요
- ⚠️ Tool execution 결과를 다음 stage로 전달하는 로직 필요

**문제점**:
- Tool execution loop가 완료되었는지 명확히 감지하지 못함
- Tool execution 결과를 파싱하여 다음 stage에 전달하지 않음
- Worker Squad가 tool execution 완료를 기다리지 않을 수 있음

**필요 작업**:
```python
# Tool execution 완료 감지
# CoderAgent.implement()에서 tool execution loop 완료 후
# 명확한 완료 신호 필요

# Tool execution 결과 파싱
# - 어떤 파일이 수정되었는지
# - 어떤 명령이 실행되었는지
# - 에러가 발생했는지
# 이 정보를 다음 stage (test, debug)에 전달
```

**위치**:
- `src/manifest/runtime/agent/agents/coder_agent.py`
- `src/manifest/agents/worker_squad_executor.py`

**예상 작업량**: 중간 (2-3일)

---

### 2. Tool Execution 에러 처리 및 복구 ⚠️ **새로운 요구사항**
**현재 상태**: 부분 구현 (약 40%)

**새로운 구조에서의 변화**:
- Tool execution 실패 시 복구 전략 필요
- Permission denied, 파일 수정 실패, 명령 실행 실패 등 다양한 에러 처리

**문제점**:
- Tool execution 실패 시 자동 복구 없음
- Permission denied 시 사용자 승인 요청 미구현 ("ask" 권한)
- Tool execution 실패 원인 분석 부족

**필요 작업**:
1. **Permission "ask" 처리**
   - 사용자 승인 요청 UI
   - 승인/거부 응답 처리

2. **Tool Execution 실패 복구**
   - 파일 수정 실패 시 재시도
   - 명령 실행 실패 시 대안 명령 시도
   - Tool execution 결과 검증

3. **에러 원인 분석**
   - Permission denied
   - 파일이 존재하지 않음
   - 명령 실행 실패
   - 컨텍스트 오버플로우

**위치**:
- `src/manifest/runtime/tools/tool_executor.py`
- `src/manifest/runtime/permissions/permission_manager.py`
- `src/manifest/ui/app.py` (승인 UI)

**예상 작업량**: 중간 (2-3일)

---

### 3. 컨텍스트 크기 제한 및 Tool 사용 최적화 ⚠️ **재평가 필요**
**현재 상태**: 부분 구현 (약 50%)

**새로운 구조에서의 변화**:
- ✅ Agent가 `read` tool로 필요한 파일만 읽을 수 있음
- ✅ 큰 파일의 경우 필요한 부분만 읽을 수 있음
- ⚠️ 하지만 여전히 컨텍스트 크기 제한 필요
- ⚠️ Tool execution 결과도 컨텍스트에 포함되므로 크기 관리 필요

**문제점**:
- Tool execution 결과가 컨텍스트에 누적되어 크기 증가
- Agent가 불필요하게 많은 파일을 읽을 수 있음
- 모델별 최대 토큰 수 고려 없음

**필요 작업**:
1. **Tool Execution 결과 크기 관리**
   - Tool execution 결과 요약
   - 오래된 tool results 제거
   - 중요한 결과만 유지

2. **파일 읽기 최적화**
   - Agent가 큰 파일을 읽으려 할 때 경고
   - 필요한 부분만 읽도록 프롬프트 개선
   - 파일 크기 제한 설정

3. **컨텍스트 크기 계산 및 제한**
   - Message history + tool results 크기 계산
   - 모델별 최대 토큰 수 설정
   - 컨텍스트 초과 시 자동 정리

**위치**:
- `src/manifest/runtime/agent/core/executor.py`
- `src/manifest/runtime/agent/agents/coder_agent.py`
- `src/manifest/agents/context_provider.py`

**예상 작업량**: 큰 (4-5일)

---

## 🟡 High Priority (단기 필요)

### 4. Tool Execution 결과 검증 및 테스트 연동 ⚠️ **새로운 요구사항**
**현재 상태**: 미구현 (0%)

**새로운 구조에서의 변화**:
- Tool execution으로 파일이 수정됨
- 수정된 파일에 대한 테스트 실행 필요
- Tool execution 결과를 Test Agent에 전달 필요

**문제점**:
- Tool execution 결과를 Test Agent가 알 수 없음
- 수정된 파일 목록을 추적하지 않음
- 테스트 실행 시 수정된 파일만 테스트하지 않음

**필요 작업**:
1. **Tool Execution 결과 추적**
   - 수정된 파일 목록 저장
   - 실행된 명령 목록 저장
   - Tool execution 메타데이터 저장

2. **Test Agent 연동**
   - 수정된 파일 목록을 Test Agent에 전달
   - 관련 테스트만 실행
   - Tool execution 결과를 테스트 컨텍스트에 포함

**위치**:
- `src/manifest/runtime/tools/tool_executor.py`
- `src/manifest/runtime/agent/agents/coder_agent.py`
- `src/manifest/runtime/agent/agents/test_agent.py`

**예상 작업량**: 중간 (2-3일)

---

### 5. Permission "ask" 사용자 승인 UI ⚠️ **새로운 요구사항**
**현재 상태**: 미구현 (0%)

**문제점**:
- Permission이 "ask"일 때 사용자 승인 요청 없음
- 현재는 경고만 하고 허용함
- 사용자가 권한을 제어할 수 없음

**필요 작업**:
1. **승인 요청 UI**
   - Tool execution 전에 승인 요청
   - 승인/거부 버튼
   - 요청 내용 표시 (어떤 agent가 무엇을 하려고 하는지)

2. **승인 응답 처리**
   - 승인 시 tool execution 진행
   - 거부 시 tool execution 취소
   - 승인/거부 기록 저장

**위치**:
- `src/manifest/runtime/permissions/permission_manager.py`
- `src/manifest/ui/app.py`

**예상 작업량**: 작음 (1-2일)

---

### 6. Tool Execution 로깅 및 감사 ⚠️ **새로운 요구사항**
**현재 상태**: 부분 구현 (약 30%)

**문제점**:
- Tool execution이 발생했는지 추적 어려움
- 어떤 파일이 수정되었는지 기록 없음
- 어떤 명령이 실행되었는지 기록 없음
- 감사(audit) 로그 부족

**필요 작업**:
1. **Tool Execution 로깅**
   - 모든 tool calls 기록
   - Tool execution 결과 기록
   - 에러 발생 시 상세 로그

2. **파일 변경 추적**
   - 수정된 파일 목록
   - 변경 전/후 내용 (diff)
   - 변경 시점

3. **명령 실행 추적**
   - 실행된 명령 목록
   - 명령 결과
   - 실행 시점

**위치**:
- `src/manifest/runtime/tools/tool_executor.py`
- `src/manifest/core/state_manager.py`

**예상 작업량**: 작음 (1-2일)

---

## 🟢 Medium Priority

### 7. Tool Execution 성능 최적화
**현재 상태**: 미구현 (0%)

**필요 작업**:
- 병렬 tool execution (여러 파일 동시 수정)
- Tool execution 결과 캐싱
- 불필요한 tool calls 방지

**예상 작업량**: 중간 (2-3일)

---

### 8. Tool Execution 디버깅 도구
**현재 상태**: 미구현 (0%)

**필요 작업**:
- Tool execution 단계별 시각화
- Tool execution 실패 원인 분석 도구
- Tool execution 재현 도구

**예상 작업량**: 중간 (2-3일)

---

## 📊 우선순위 재정리

### 즉시 시작해야 할 작업 (Critical)

1. **Tool Execution 완료 감지 및 결과 파싱** (2-3일) ⚠️ **재평가됨**
   - Tool system과 통합 필요
   - Tool execution 완료 신호 명확화

2. **Tool Execution 에러 처리 및 복구** (2-3일) ⚠️ **새로운 요구사항**
   - Permission "ask" 처리
   - 실패 복구 전략

3. **컨텍스트 크기 제한 및 Tool 사용 최적화** (4-5일) ⚠️ **재평가됨**
   - Tool execution 결과 크기 관리
   - 파일 읽기 최적화

### 단기 내 완료 필요 (High Priority)

4. **Tool Execution 결과 검증 및 테스트 연동** (2-3일) ⚠️ **새로운 요구사항**
5. **Permission "ask" 사용자 승인 UI** (1-2일) ⚠️ **새로운 요구사항**
6. **Tool Execution 로깅 및 감사** (1-2일) ⚠️ **새로운 요구사항**

---

## 🎯 권장 작업 순서

### Week 1: Tool System 안정화
1. Tool Execution 완료 감지 및 결과 파싱 (2-3일)
2. Tool Execution 에러 처리 및 복구 (2-3일)

### Week 2: Tool System 최적화
3. 컨텍스트 크기 제한 및 Tool 사용 최적화 (4-5일)

### Week 3: Tool System 고급 기능
4. Tool Execution 결과 검증 및 테스트 연동 (2-3일)
5. Permission "ask" 사용자 승인 UI (1-2일)
6. Tool Execution 로깅 및 감사 (1-2일)

---

## ⚠️ 주의사항

1. **Tool System이 핵심**이므로 Tool execution 관련 작업이 최우선
2. **Permission "ask" 처리**는 사용자 경험에 중요
3. **Tool Execution 결과 파싱**은 다음 stage로의 데이터 전달에 필수
4. 기존 TODO 중 일부는 Tool System으로 해결되었거나 우선순위가 낮아짐

---

## ✅ 완료된 항목 (재평가 결과)

- ✅ Agent Output Display 개선 (tool_use, tool_result 표시 완료)
- ✅ Multi-Agent Workflow 자동화 (WorkflowEventBus 구현됨)
- ✅ Agent Bridge → Planner 통합 (send_to_planner 구현됨)
- ✅ Task 상태 변경 UI 개선 (action_change_task_status 구현됨)
- ✅ 실패 복구 메커니즘 (FailureRecoveryManager 구현됨, 하지만 Tool execution과 통합 필요)

---

## 🔄 변경된 우선순위

**기존 Critical Priority**:
- ❌ Agent 완료 대기 및 결과 파싱 → ⚠️ **Tool Execution 완료 감지 및 결과 파싱**으로 변경
- ✅ Agent Output Display 개선 → ✅ **완료됨**
- ⚠️ 컨텍스트 크기 제한 → ⚠️ **Tool 사용 최적화 포함**으로 확장

**새로운 Critical Priority**:
- ⚠️ Tool Execution 에러 처리 및 복구 (새로운 요구사항)

**기존 High Priority**:
- ✅ Multi-Agent Workflow 자동화 → ✅ **완료됨**
- ✅ Agent Bridge → Planner 통합 → ✅ **완료됨**
- ✅ Task 상태 변경 UI 개선 → ✅ **완료됨**
- ✅ 실패 복구 메커니즘 → ✅ **완료됨** (하지만 Tool execution과 통합 필요)

**새로운 High Priority**:
- ⚠️ Tool Execution 결과 검증 및 테스트 연동 (새로운 요구사항)
- ⚠️ Permission "ask" 사용자 승인 UI (새로운 요구사항)
- ⚠️ Tool Execution 로깅 및 감사 (새로운 요구사항)
