# 최종 개선 계획 (통합)

**작성일**: 2026-01-24  
**기준**: 코드베이스 검토 + Tool System 구조 반영

---

## 📋 통합 우선순위

### 🔴 Critical Priority (즉시 수정)

#### 1. 중복된 Agent Output 처리 제거 ⚠️ **새로운 발견**
**상태**: ✅ 완료
**작업량**: 0.5-1일
**위치**: `agent_bridge.py`, `channel_manager.py`
**완료 내용**: 중복 저장 제거, channel_manager에 통합, BatchSaver로 최적화

#### 2. Agent Output 처리 통일 ⚠️ **새로운 발견**
**상태**: ✅ 완료
**작업량**: 1-2일
**위치**: `agent_bridge.py`, `planner_agent.py`, `integration_test_agent.py`, `e2e_test_agent.py`
**완료 내용**: 모든 agent output이 agent_bridge를 통해 일관되게 처리

#### 3. Tool Execution 완료 감지 및 결과 파싱
**상태**: ✅ 완료
**작업량**: 2-3일
**위치**: `coder_agent.py`, `worker_squad_executor.py`
**완료 내용**: tool_execution_summary 도입, complete chunk에 포함, task state에 저장

#### 4. Tool Execution 에러 처리 및 복구
**상태**: ✅ 완료
**작업량**: 2-3일
**위치**: `tool_executor.py`, `permission_manager.py`, `app.py`
**완료 내용**: permission_required 처리, validation 추가, 에러 추적 강화

---

### 🟡 High Priority (단기 수정)

#### 5. Tool System 일관성 확보 ⚠️ **새로운 발견**
**상태**: ✅ 완료
**작업량**: 2-3일
**위치**: `test_agent.py`, `debug_agent.py`, `agent_manager.py`
**완료 내용**: test_agent, debug_agent에 tool execution loop 추가, tool_executor 통합

#### 6. State 저장 최적화 ⚠️ **새로운 발견**
**상태**: ✅ 완료
**작업량**: 0.5일
**위치**: `agent_bridge.py`, `channel_manager.py`
**완료 내용**: BatchSaver로 shadow agent 출력 배치 처리, save_immediately 플래그 도입

#### 7. 컨텍스트 크기 제한 및 Tool 사용 최적화
**상태**: ✅ 완료
**작업량**: 4-5일
**위치**: `executor.py`, `coder_agent.py`, `context_provider.py`
**완료 내용**: ContextSizeCalculator 통합, _optimize_tool_list로 tool 필터링, 토큰 수 검증

#### 8. Tool Execution 결과 검증 및 테스트 연동
**상태**: ✅ 완료
**작업량**: 2-3일
**위치**: `tool_executor.py`, `coder_agent.py`, `test_agent.py`
**완료 내용**: _validate_tool_result 추가, tool_execution_summary를 test_agent에 전달

---

### 🟢 Medium Priority (중기 개선)

#### 9. Permission "ask" 사용자 승인 UI
**상태**: ✅ 완료
**작업량**: 1-2일
**위치**: `terminal_router.py`, `app.py`
**완료 내용**: PermissionApprovalManager, PermissionApprovalWidget 구현, UI 통합

#### 10. Tool Execution 로깅 및 감사
**상태**: ✅ 완료
**작업량**: 1-2일
**위치**: `tool_executor.py`, `state_manager.py`
**완료 내용**: ToolExecutionAuditor 구현, 모든 ToolExecutor 경로에 통합

#### 11. 사용되지 않는 코드 정리 ⚠️ **새로운 발견**
**상태**: ✅ 완료
**작업량**: 1일
**위치**: `agent_manager.py`, 각 agent 클래스
**완료 내용**: TODO 주석 정리, terminal_router 사용 명확화 및 문서화

---

## 🎯 권장 작업 순서

### Week 1: Critical 버그 수정
**Day 1-2**: 중복 처리 제거 + 일관성 확보
- 중복된 Agent Output 처리 제거 (0.5일)
- Agent Output 처리 통일 (1-2일)

**Day 3-5**: Tool System 핵심 기능
- Tool Execution 완료 감지 및 결과 파싱 (2-3일)

### Week 2: Tool System 안정화
**Day 1-3**: Tool Execution 에러 처리 및 복구 (2-3일)
**Day 4**: State 저장 최적화 (0.5일)
**Day 5**: Tool System 일관성 확보 시작 (1일)

### Week 3: Tool System 최적화
**Day 1-2**: Tool System 일관성 확보 완료 (1-2일)
**Day 3-7**: 컨텍스트 크기 제한 및 Tool 사용 최적화 (4-5일)

### Week 4: Tool System 고급 기능
**Day 1-3**: Tool Execution 결과 검증 및 테스트 연동 (2-3일)
**Day 4-5**: Permission "ask" 사용자 승인 UI (1-2일)

### Week 5: 마무리
**Day 1-2**: Tool Execution 로깅 및 감사 (1-2일)
**Day 3**: 사용되지 않는 코드 정리 (1일)

---

## 📊 예상 완료 시점

- **Critical 항목 완료**: 약 1주 (5-6일)
- **High Priority 항목 완료**: 약 3주 (15-18일)
- **전체 완료**: 약 5주 (25-30일)

---

## ⚠️ 주의사항

1. **중복 저장 버그**는 즉시 수정 필요 (데이터 무결성)
2. **일관성 문제**는 다른 작업의 기반이 되므로 우선 수정
3. **Tool System 불일치**는 기능 확장에 직접 영향
4. 각 작업은 독립적으로 진행 가능하나, 일부는 의존성 있음

---

## ✅ 검증 체크리스트

각 작업 완료 후:
- [x] State에 중복 메시지가 저장되지 않는지 ✅
- [x] 모든 agent output이 일관되게 처리되는지 ✅
- [x] Tool system이 필요한 agent에서 작동하는지 ✅
- [x] save_state가 적절한 빈도로만 호출되는지 ✅
- [x] 사용되지 않는 코드가 제거되었는지 ✅
- [x] Tool execution 완료가 명확히 감지되는지 ✅
- [x] Tool execution 에러가 적절히 처리되는지 ✅

## 🎉 완료 현황

**완료일**: 2026-01-24

### ✅ Critical Priority (4/4 완료)
1. 중복된 Agent Output 처리 제거
2. Agent Output 처리 통일
3. Tool Execution 완료 감지 및 결과 파싱
4. Tool Execution 에러 처리 및 복구

### ✅ High Priority (4/4 완료)
5. Tool System 일관성 확보
6. State 저장 최적화
7. 컨텍스트 크기 제한 및 Tool 사용 최적화
8. Tool Execution 결과 검증 및 테스트 연동

### ✅ Medium Priority (3/3 완료)
9. Permission "ask" 사용자 승인 UI
10. Tool Execution 로깅 및 감사
11. 사용되지 않는 코드 정리

**전체 완료율**: 11/11 (100%)
