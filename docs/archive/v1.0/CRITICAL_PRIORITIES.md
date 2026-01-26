# Critical Priorities - 최종 정리

**작성일**: 2026-01-24
**기준**: REMAINING_FEATURES.md, PROJECT_REVIEW.md

---

## 🔴 Critical Priority (즉시 필요)

### 1. Agent 완료 대기 및 결과 파싱 ⚠️
**현재 상태**: 부분 구현 (약 40%)

**문제점**:
- `start_worker_agent()`가 Agent를 시작만 하고 완료를 기다리지 않음
- Worker Squad가 다음 stage로 진행하기 전에 Agent 완료를 확인하지 않음
- Agent 결과를 파싱하여 다음 stage에 전달하는 로직 부족

**영향**:
- Worker Squad가 Agent 완료 전에 다음 stage로 진행할 수 있음
- Agent 출력을 제대로 활용하지 못함
- Stage 간 데이터 전달이 불완전함

**필요 작업**:
```python
# 현재: Agent 시작만 하고 반환
success = await self.coordinator.start_worker_agent(...)

# 필요: Agent 완료 대기 및 결과 파싱
result = await self.coordinator.start_worker_agent_and_wait(...)
# result = {
#     "status": "completed",
#     "output": "...",
#     "parsed_data": {...}
# }
```

**위치**:
- `src/manifest/agents/worker_squad_executor.py`
- `src/manifest/agents/agent_coordinator.py`

**예상 작업량**: 중간 (2-3일)

---

### 2. Agent Output Display 개선 ⚠️
**현재 상태**: 부분 구현 (70%)

**문제점**:
- Agent 출력이 State에 저장되지만 UI 표시가 제한적
- 동적 TabPane 생성이 Textual 제약으로 불가능
- Squad 채널이 별도 탭이 아닌 main log에 prefix로만 표시
- 여러 Agent 동시 실행 시 출력 혼합 문제

**영향**:
- 사용자가 Agent 출력을 제대로 확인하기 어려움
- 여러 Task의 Agent 출력이 섞여서 구분 어려움
- 실시간 진행 상황 파악 어려움

**필요 작업**:
1. **대안 UI 패턴 구현** (Textual 제약 고려)
   - 채널 버튼으로 필터링
   - 채널별 히스토리 표시
   - 실시간 스트리밍 표시

2. **출력 분리 및 라우팅**
   - Task별, Agent별 출력 분리
   - 채널별 State 저장 및 로드
   - 출력 우선순위 및 표시 순서 관리

**위치**:
- `src/manifest/ui/app.py`
- `src/manifest/ui/channels/channel_manager.py`

**예상 작업량**: 중간 (2-3일)

---

### 3. 컨텍스트 크기 제한 및 Task Granularity 강화 ⚠️
**현재 상태**: 부분 구현 (약 50%)

**문제점**:
- LLM 모델의 최대 컨텍스트 크기를 고려하지 않음
- Task scope가 너무 크면 컨텍스트 초과 가능
- 파일 전체 내용을 제공하여 큰 파일의 경우 컨텍스트 낭비
- 모델별 최대 토큰 수 고려 없음

**영향**:
- 컨텍스트 초과로 Agent 실행 실패 가능
- 불필요한 컨텍스트로 비용 증가
- 큰 Task는 실행 불가능

**필요 작업**:
1. **컨텍스트 크기 계산**
   ```python
   def calculate_context_size(context: Dict) -> int:
       # 토큰 수 추정 (대략 4 chars = 1 token)
       # 또는 tiktoken 라이브러리 사용
       pass
   ```

2. **모델별 최대 토큰 수 설정**
   ```python
   MODEL_LIMITS = {
       "claude-3-opus": 200000,
       "claude-3-sonnet": 200000,
       "gpt-4": 128000,
       "gpt-3.5-turbo": 16385
   }
   ```

3. **파일 크기 제한**
   - 1000줄 이상이면 관련 부분만 추출
   - 함수/클래스 단위로 필요한 부분만 제공
   - 코드 요약 제공

4. **Task 크기 검증 강화**
   - Orchestrator에 강제 적용
   - Task가 너무 크면 자동 분할 제안
   - 컨텍스트 크기 기반 Task 분할 자동화

**위치**:
- `src/manifest/agents/context_provider.py`
- `src/manifest/agents/task_scoper.py`
- `src/manifest/runtime/agent/agents/orchestrator_agent.py`

**예상 작업량**: 큰 (4-5일)

---

## 🟡 High Priority (단기 필요)

### 4. Multi-Agent Workflow 자동화 ⚠️
**현재 상태**: 부분 구현 (약 60%)

**문제점**:
- Worker Squad 구조는 있으나 Agent 간 메시지 전달 프로토콜 없음
- Agent 출력에서 다음 stage 트리거 자동화 부족
- Agent 완료 이벤트 처리 부족

**필요 작업**:
- Agent 간 메시지 전달 프로토콜 구현
- Agent 완료 이벤트 처리 및 결과 파싱
- Agent 출력에서 자동으로 다음 stage 트리거

**위치**: `src/manifest/agents/worker_squad_executor.py`

**예상 작업량**: 중간 (3-4일)

---

### 5. Agent Bridge → Planner 통합 ❌
**현재 상태**: 미구현 (0%)

**문제점**:
- Blueprint 충돌 시 Planner로 자동 전달되지 않음
- `AgentBridge.send_to_planner()` 메서드 없음

**필요 작업**:
- `AgentBridge.send_to_planner()` 메서드 구현
- Blueprint 충돌 시 자동으로 Planner에 전달
- Planner 응답 처리 및 Blueprint 업데이트

**위치**:
- `src/manifest/agents/agent_coordinator.py:427`
- `src/manifest/bridge/agent_bridge.py`

**예상 작업량**: 작음 (1-2일)

---

### 6. Task 상태 변경 UI 개선 ⚠️
**현재 상태**: 부분 구현 (약 30%)

**문제점**:
- CLI 명령어로만 Task 상태 변경 가능
- UI에서 직접 클릭으로 변경 불가
- Context menu 없음
- 실시간 진행률 표시 없음

**필요 작업**:
- Task Tree에서 Task 클릭 시 상세 정보 및 액션 표시
- Context menu로 상태 변경
- 실시간 진행률 표시 (예: 50% complete)
- 예상 완료 시간 표시

**위치**: `src/manifest/ui/widgets/project_view.py`

**예상 작업량**: 중간 (2-3일)

---

### 7. 실패 복구 메커니즘 ❌
**현재 상태**: 미구현 (0%)

**문제점**:
- Stage 실패 시 수동 개입 필요
- 자동 복구 로직 없음
- Fallback 전략 없음
- 명확한 에러 메시지 부족

**필요 작업**:
- 실패 원인 분석 로직
- 자동 복구 시도 (다른 접근 방식)
- Fallback 전략 (다른 모델, 다른 프롬프트)
- 사용자에게 명확한 에러 메시지 및 해결 방안 제시

**위치**: `src/manifest/agents/worker_squad_executor.py`

**예상 작업량**: 큰 (4-5일)

---

## 📊 최종 우선순위 요약

### 즉시 시작해야 할 작업 (Critical)

1. **Agent 완료 대기 및 결과 파싱** (2-3일)
   - Worker Squad의 핵심 기능
   - 다른 기능들의 기반이 됨

2. **Agent Output Display 개선** (2-3일)
   - 사용자 경험에 직접적 영향
   - 상대적으로 구현 난이도 낮음

3. **컨텍스트 크기 제한 및 Task Granularity 강화** (4-5일)
   - 시스템 안정성에 필수
   - 큰 작업이지만 중요도 높음

### 단기 내 완료 필요 (High Priority)

4. **Multi-Agent Workflow 자동화** (3-4일)
5. **Agent Bridge → Planner 통합** (1-2일)
6. **Task 상태 변경 UI 개선** (2-3일)
7. **실패 복구 메커니즘** (4-5일)

---

## 🎯 권장 작업 순서

### Week 1: Critical 기반 작업
1. Agent 완료 대기 및 결과 파싱 (2-3일)
2. Agent Output Display 개선 (2-3일)

### Week 2: 안정성 강화
3. 컨텍스트 크기 제한 및 Task Granularity 강화 (4-5일)

### Week 3-4: High Priority 작업
4. Multi-Agent Workflow 자동화 (3-4일)
5. Agent Bridge → Planner 통합 (1-2일)
6. Task 상태 변경 UI 개선 (2-3일)
7. 실패 복구 메커니즘 (4-5일)

---

## 📈 예상 완료 시점

- **Critical 항목 완료**: 약 2주 (10-11일)
- **High Priority 항목 완료**: 약 4주 (17-22일)
- **전체 Critical + High Priority 완료**: 약 4-5주

---

## ⚠️ 주의사항

1. **Agent 완료 대기 및 결과 파싱**은 다른 기능들의 기반이 되므로 최우선
2. **컨텍스트 크기 제한**은 큰 작업이지만 시스템 안정성에 필수
3. **실패 복구 메커니즘**은 복잡하지만 사용자 경험에 중요
4. 각 작업은 독립적으로 진행 가능하나, 일부는 의존성 있음
