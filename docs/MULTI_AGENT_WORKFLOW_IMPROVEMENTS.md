# Multi-Agent Workflow 개선 사항

**작성일**: 2026-01-26
**최종 업데이트**: 2026-01-26
**현재 상태**: 완전 구현 (100%)
**목표**: 완전 구현 (100%) ✅

## OpenCode와의 관계

**중요**: Multi-Agent Workflow 개선은 **순수 Manifest에서 처리해야 하는 사안**입니다.

### OpenCode의 역할
- **OpenCode**: Terminal command execution을 위한 선택적 adapter
- **위치**: `src/manifest/runtime/opencode_adapter.py`
- **용도**: Agent가 terminal command를 실행할 때 사용 (예: `git`, `npm`, `python` 등)
- **범위**: Command execution만 담당, Agent coordination과는 무관

### Multi-Agent Workflow의 범위
- **Agent 간 협업**: Planner → Coder → Test 등의 워크플로우 조정
- **Agent 완료 감지**: BaseAgentExecutor 인터페이스의 chunk 처리, 상태 관리
  - AgentExecutor (Direct API) 또는 OpenCodeLLMAdapter (OpenCode) 사용
- **결과 파싱**: Agent 출력에서 구조화된 데이터 추출
- **이벤트 기반 자동화**: WorkflowEventBus를 통한 stage 자동 트리거
- **Agent 간 메시지 전달**: Agent 간 직접 통신 프로토콜

### 결론
Multi-Agent Workflow 개선은 **OpenCode와 무관**하며, **순수 Manifest의 Agent coordination 시스템**에서 처리해야 합니다.

---

## 현재 구현 상태

### ✅ 구현된 부분

1. **Worker Squad 순차 실행**
   - `WorkerSquadExecutor.execute()` - 전체 워크플로우 순차 실행
   - 각 stage별 `_execute_*_stage()` 메서드 구현
   - Stage 간 데이터 전달 (`previous_stages`)

2. **Agent 완료 대기**
   - `start_worker_agent_and_wait()` 메서드 구현
   - 채널 모니터링을 통한 완료 감지
   - 타임아웃 처리

3. **이벤트 시스템**
   - `WorkflowEventBus` 구현
   - Agent 완료/실패 이벤트 발행
   - Stage 완료/실패 이벤트 발행

4. **결과 파싱**
   - `_parse_agent_output()` 메서드 존재
   - Agent 타입별 파싱 로직

---

## 🔴 개선이 필요한 부분

### 1. Agent 완료 감지 개선 (Critical)

**현재 문제점**:
```python
# agent_coordinator.py:430-433
# Check for completion indicators
if any(indicator in content.lower() for indicator in [
    "[complete]", "[finished]", "[done]", "task completed"
]):
    break
```

**문제**:
- 문자열 기반 완료 감지로 불안정함
- Agent가 완료 메시지를 명시적으로 보내지 않으면 감지 실패
- `active_agents`에서 제거되는 것을 확인하지만, 타이밍 이슈 가능

**개선 방안**:
1. **명시적 완료 신호 구현**
   - Agent가 `{"type": "complete"}` chunk를 yield할 때 명확히 처리
   - AgentExecutor에서 완료 시 상태 업데이트 강제

2. **상태 기반 완료 감지 강화**
   - AgentExecutor의 `active_sessions` 상태 확인
   - AgentBridge의 `_active_agents` 상태 확인
   - 여러 소스를 종합하여 완료 판단

3. **타임아웃 및 폴백 로직**
   - 일정 시간 동안 새 메시지가 없으면 완료로 간주
   - Agent 상태를 주기적으로 폴링

**예상 작업량**: 중간 (2-3일)

---

### 2. 결과 파싱 개선 (High Priority)

**현재 문제점**:
```python
# agent_coordinator.py:450
parsed_data = self._parse_agent_output(agent_type, stage, output)
```

**문제**:
- `_parse_agent_output()` 메서드의 실제 구현 확인 필요
- Agent 출력에서 구조화된 데이터 추출이 제한적일 수 있음
- 다음 stage에 필요한 데이터가 제대로 전달되지 않을 수 있음

**개선 방안**:
1. **구조화된 출력 파싱 강화**
   - JSON, YAML, Markdown 등 구조화된 형식 파싱
   - Agent별 출력 형식 표준화
   - 파싱 실패 시 폴백 로직

2. **다음 Stage에 필요한 데이터 추출**
   - Planner → TDD Test: plan 추출
   - TDD Test → Coder: test_plan, test_skeleton 추출
   - Coder → Test: files_modified 추출
   - Test → Debug: test_results, errors 추출

3. **파싱 결과 검증**
   - 필수 필드 존재 확인
   - 데이터 타입 검증
   - 파싱 실패 시 로깅 및 복구

**예상 작업량**: 중간 (2-3일)

---

### 3. 이벤트 기반 자동화 활성화 (High Priority)

**현재 문제점**:
```python
# worker_squad_executor.py:12-15
# The executor can operate in two modes:
# 1. Sequential mode: Explicitly calls each stage in order (current default)
# 2. Event-driven mode: Subscribes to workflow events and automatically
#    triggers next stages when agents complete (future enhancement)
```

**문제**:
- WorkflowEventBus가 있지만 실제로 사용되지 않음
- 순차적 모드만 사용 중
- 이벤트를 구독해서 자동으로 다음 stage를 트리거하는 로직 없음

**개선 방안**:
1. **이벤트 구독 시스템 구현**
   ```python
   # WorkerSquadExecutor가 이벤트 구독
   await self.coordinator.event_bus.subscribe(
       WorkflowEventType.STAGE_COMPLETED,
       self._on_stage_completed
   )
   ```

2. **자동 다음 Stage 트리거**
   - Stage 완료 이벤트 수신 시 자동으로 다음 stage 시작
   - 조건부 실행 (예: test 실패 시 debug로, 성공 시 self_review로)

3. **병렬 실행 지원**
   - 독립적인 stage들을 병렬로 실행
   - 의존성 그래프 기반 실행 순서 결정

**예상 작업량**: 중간-큼 (3-5일)

---

### 4. Agent 간 직접 메시지 전달 (Medium Priority)

**현재 문제점**:
- Agent 간 직접 통신 프로토콜 없음
- `previous_stages`를 통한 간접 데이터 전달만 존재
- Agent가 다른 Agent에게 직접 요청할 수 없음

**개선 방안**:
1. **Agent 간 메시지 버스 구현**
   - Agent가 다른 Agent에게 메시지 전송 가능
   - 메시지 라우팅 시스템
   - 비동기 메시지 큐

2. **요청-응답 패턴**
   - Agent A가 Agent B에게 정보 요청
   - Agent B가 응답 반환
   - 타임아웃 및 에러 처리

3. **이벤트 기반 통신**
   - Agent가 이벤트 발행
   - 다른 Agent가 이벤트 구독
   - 느슨한 결합 유지

**예상 작업량**: 큼 (5-7일)

---

### 5. 에러 처리 및 복구 개선 (Medium Priority)

**현재 상태**:
- `FailureRecoveryManager` 존재
- 기본적인 복구 로직 구현됨

**개선 방안**:
1. **더 정교한 복구 전략**
   - 단계별 복구 시도 (간단한 수정 → 재시도 → 단순화)
   - 컨텍스트 축소 후 재시도
   - 다른 Agent로 위임

2. **에러 분류 및 대응**
   - 에러 타입별 다른 복구 전략
   - 일시적 에러 vs 영구적 에러 구분
   - 사용자 개입 필요 시 알림

3. **부분 성공 처리**
   - 일부 stage만 성공한 경우 처리
   - 재개 가능한 지점 저장
   - 중단된 워크플로우 재개

**예상 작업량**: 중간 (3-4일)

---

## 우선순위별 작업 계획

### Phase 1: 안정성 개선 (1-2주)
1. ✅ Agent 완료 감지 개선
2. ✅ 결과 파싱 개선
3. ✅ 에러 처리 강화

### Phase 2: 자동화 개선 (1-2주)
1. ✅ 이벤트 기반 자동화 활성화
2. ✅ 조건부 실행 로직
3. ✅ 병렬 실행 지원

### Phase 3: 고급 기능 (2-3주) ✅ 완료
1. ✅ Agent 간 직접 메시지 전달
2. ✅ 동적 워크플로우 구성
3. ✅ 워크플로우 시각화

---

## 완료도

- **Phase 1 완료 후**: ✅ 80%
- **Phase 2 완료 후**: ✅ 95%
- **Phase 3 완료 후**: ✅ 100%

**현재 상태**: ✅ 100% 완료 (2026-01-26)

---

## 참고 파일

- `src/manifest/agents/worker_squad_executor.py` - Worker Squad 실행 로직
- `src/manifest/agents/agent_coordinator.py` - Agent 조정 및 완료 대기
- `src/manifest/agents/workflow_event_bus.py` - 이벤트 시스템
- `src/manifest/agents/failure_recovery.py` - 복구 로직
