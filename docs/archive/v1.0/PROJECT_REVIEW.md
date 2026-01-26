# Manifest 프로젝트 리뷰
**Review Date**: 2025-01-27 14:30:00

## 리뷰 기준
1. 바이브코딩 - 프로젝트 구조와 현재 상황을 사용자가 잘 볼 수 있는가? 컨텍스트를 덜 소모하고 더 정확히 전달하는 매개체가 있는가?
2. LLM 모델의 컨텍스트 크기와 작업 스코프 분할이 잘 되어 있는가?
3. 작업 진행상황 확인 및 사용자가 쉽게 확인하고 변경할 수 있는가?
4. 개발 프로세스가 안정적으로 목표 완수까지 잘 짜여져 있는가?

---

## 1. 바이브코딩 - 프로젝트 구조 및 현재 상황 시각화

### ✅ 구현된 기능

#### Visual Reality Hook
- **위치**: `src/manifest/runtime/hooks/prompt_hooks.py`
- **기능**: 에이전트 프롬프트에 현재 프로젝트 상태를 자동 주입
- **제공 정보**:
  - Architecture Status (Features, completion %)
  - Implementation Status (Implemented, Ghost, Drift components)
  - Current Task Status
- **장점**: 
  - 에이전트가 전체 코드를 읽지 않고도 프로젝트 상태 파악 가능
  - 구조화된 정보로 컨텍스트 효율적 사용

#### Structure View (UI)
- **위치**: `src/manifest/ui/widgets/structure_hierarchy_view.py`, `structure_graph_view.py`
- **기능**:
  - Hierarchy View: Features → Requirements → Components 트리 구조
  - Graph View: 시각적 다이어그램
  - Implementation Status 표시 (implemented, ghost, drift)
  - Completion percentage 표시
- **장점**: 사용자가 프로젝트 구조를 직관적으로 파악 가능

#### Tiered Context System
- **위치**: `src/manifest/agents/context_provider.py`
- **구조**:
  - Tier 0: Policy (manifest-policy.md)
  - Tier 1: Architecture & Intent (architecture.json, intent.json)
  - Tier 2: Blueprint (scoped to task)
  - Tier 3: Code files (scoped to task)
- **장점**: 
  - 계층적 컨텍스트 제공으로 효율적 정보 전달
  - Task별 스코핑으로 불필요한 정보 제거

### ⚠️ 개선 필요 사항

#### 1. Visual Reality Hook의 정보 부족
**현재 상태**:
- Architecture Status: 상위 5개 Feature만 표시
- Implementation Status: 숫자만 표시 (구체적 컴포넌트 정보 없음)
- Task Status: 기본 정보만

**개선 방안**:
- 더 상세한 컴포넌트 상태 정보 제공
- Drift 정보에 구체적 불일치 내용 포함
- 관련 파일 목록 표시

#### 2. Structure View의 실시간 업데이트 부족
**현재 상태**:
- 데이터 로딩은 있으나 실시간 동기화 불명확

**개선 방안**:
- 파일 변경 감지 시 자동 업데이트
- Blueprint 변경 시 즉시 반영
- 실시간 상태 표시

#### 3. 사용자 시각화와 에이전트 컨텍스트의 불일치
**현재 상태**:
- UI에서 보는 정보와 에이전트가 받는 정보가 다를 수 있음

**개선 방안**:
- Visual Reality Hook이 UI와 동일한 정보 제공
- 사용자가 보는 구조를 에이전트도 동일하게 인식

---

## 2. LLM 모델 컨텍스트 크기와 작업 스코프 분할

### ✅ 구현된 기능

#### Task Scoping System
- **위치**: `src/manifest/agents/task_scoper.py`
- **기능**:
  - Task별 Component 필터링
  - Task별 File 필터링
  - Allowed modifications 제한
  - Requirements 스코핑
- **장점**: 
  - Task별로 필요한 컨텍스트만 제공
  - 전체 코드베이스 대신 관련 부분만 전달

#### Tiered Context (단계별 컨텍스트)
- **Orchestrator**: Tier 0 + Tier 1 (Policy + Architecture)
- **Worker Agents**: Tier 0 + Tier 2 + Tier 3 (Policy + Scoped Blueprint + Scoped Code)
- **Stage-specific Context**: 각 단계별 필요한 정보만 제공
  - Planner: Tier 0, Tier 1, Task Scope
  - TDD Test: Tier 0, Planner plan, Task Scope
  - Coder: Tier 0, Tier 2, Tier 3, Planner plan, Test skeleton
  - Test: Tier 0, Coder output, Test skeleton
  - Debug: Tier 0, Test results, Coder output, Error messages

#### Context Provider
- **위치**: `src/manifest/agents/context_provider.py`
- **기능**:
  - Agent type별 맞춤 컨텍스트
  - Stage별 맞춤 컨텍스트
  - Task scope 기반 필터링

### ⚠️ 개선 필요 사항

#### 1. 컨텍스트 크기 제한 없음
**현재 상태**:
- LLM 모델의 최대 컨텍스트 크기를 고려하지 않음
- Task scope가 너무 크면 컨텍스트 초과 가능

**개선 방안**:
- 컨텍스트 크기 계산 및 제한
- Task가 너무 크면 자동 분할 제안
- 모델별 최대 토큰 수 고려

#### 2. Task Granularity 규칙 부재
**현재 상태**:
- Task를 어떻게 나눌지에 대한 명확한 규칙 없음
- `.claude/rules/task-granularity.md` 파일은 있으나 실제 적용 불명확

**개선 방안**:
- Task granularity 규칙을 Orchestrator에 강제 적용
- Task 크기 검증 로직 추가
- 컨텍스트 크기 기반 Task 분할 자동화

#### 3. 파일 내용 크기 제한 없음
**현재 상태**:
- Tier 3에서 파일 전체 내용을 제공
- 큰 파일의 경우 컨텍스트 낭비

**개선 방안**:
- 파일 크기 제한 (예: 1000줄 이상이면 관련 부분만 추출)
- 함수/클래스 단위로 필요한 부분만 추출
- 코드 요약 제공

#### 4. 중복 컨텍스트 제거 부족
**현재 상태**:
- 여러 단계에서 동일한 정보 반복 제공 가능

**개선 방안**:
- 이전 단계에서 제공한 정보는 참조만 제공
- 컨텍스트 캐싱 및 중복 제거

---

## 3. 작업 진행상황 확인 및 변경

### ✅ 구현된 기능

#### Task Tree View
- **위치**: `src/manifest/ui/widgets/project_view.py`
- **기능**:
  - Sprint별 Task 그룹화
  - Task 상태 표시 (pending, in_progress, done, blocked, cancelled)
  - Worker Squad Stages 표시
  - Status icon으로 시각적 표시

#### Worker Squad Progress
- **위치**: `src/manifest/ui/widgets.py`
- **기능**:
  - 각 Stage별 상태 표시
  - Debug iteration count
  - Approver decision 표시

#### Task Management Commands
- **위치**: `src/manifest/ui/app.py`
- **기능**:
  - `/create_task`: Task 생성
  - `/update_task`: Task 업데이트
  - `/cancel_task`: Task 취소
  - `/start_task`: Task 시작
  - `/start_sprint`: Sprint 시작

#### Channel-based Output
- **위치**: `src/manifest/ui/app.py`
- **기능**:
  - Agent별 채널 분리
  - 채널별 히스토리 표시
  - 채널 전환 기능

### ⚠️ 개선 필요 사항

#### 1. Task 상태 변경 UI 부족
**현재 상태**:
- CLI 명령어로만 Task 상태 변경 가능
- UI에서 직접 클릭으로 변경 불가

**개선 방안**:
- Task Tree에서 Task 클릭 시 상세 정보 및 액션 표시
- Context menu로 상태 변경
- Drag & drop으로 상태 변경

#### 2. Worker Squad 진행상황 실시간 업데이트 부족
**현재 상태**:
- Stage 완료 시 업데이트는 되나 실시간 진행률 표시 없음

**개선 방안**:
- 각 Stage의 진행률 표시 (예: 50% complete)
- 실시간 로그 스트리밍
- 예상 완료 시간 표시

#### 3. Task 롤백 기능 미완성
**현재 상태**:
- `/cancel_task`는 있으나 롤백 기능 불명확

**개선 방안**:
- Git 기반 롤백 기능
- 특정 Stage로 롤백
- 변경사항 미리보기

#### 4. Task 필터링 및 검색 부족
**현재 상태**:
- Task 목록만 표시, 필터링/검색 기능 없음

**개선 방안**:
- Status별 필터링
- Sprint별 필터링
- Task 이름/ID 검색
- 정렬 기능 (날짜, 상태, 우선순위)

#### 5. Task 의존성 시각화 부족
**현재 상태**:
- Task 간 의존성 정보 없음

**개선 방안**:
- Task 의존성 그래프
- Blocked 상태의 원인 표시
- 병렬 실행 가능 여부 표시

---

## 4. 개발 프로세스 안정성

### ✅ 구현된 기능

#### Worker Squad Workflow
- **위치**: `src/manifest/agents/agent_coordinator.py`
- **플로우**:
  1. Planner: 계획 생성
  2. TDD Test: 테스트 스켈레톤 작성
  3. Coder: 구현
  4. Test: 테스트 실행
  5. Debug: 버그 수정 (반복, 최대 5회)
  6. Self Review: 계획 준수 확인
  7. Approver: 최종 승인
  8. Project Review: 프로젝트 레벨 검토
  9. E2E Test: 통합 테스트

#### Error Handling
- **기능**:
  - 각 Stage 실패 시 에러 처리
  - Debug 반복으로 자동 수정 시도
  - Approver 거부 시 Coder로 재전송 (최대 3회)
  - 최대 반복 횟수 제한

#### State Management
- **위치**: `src/manifest/core/state_manager.py`
- **기능**:
  - 각 Stage 결과 저장
  - Task 상태 추적
  - Worker Squad 단계별 기록

#### Non-blocking Architecture
- **기능**:
  - Sprint-level TDD는 백그라운드 실행
  - Orchestrator는 블로킹되지 않음
  - Worker Squad는 비동기 실행

### ⚠️ 개선 필요 사항

#### 1. 실패 복구 메커니즘 부족
**현재 상태**:
- Stage 실패 시 수동 개입 필요
- 자동 복구 로직 없음

**개선 방안**:
- 실패 원인 분석 및 자동 수정 시도
- Fallback 전략 (예: 다른 모델 사용)
- 사용자에게 명확한 에러 메시지 및 해결 방안 제시

#### 2. 타임아웃 및 리소스 제한 없음
**현재 상태**:
- 각 Stage에 타임아웃 없음
- 무한 대기 가능

**개선 방안**:
- Stage별 타임아웃 설정
- 리소스 사용량 모니터링
- 자동 취소 로직

#### 3. 검증 단계 부족
**현재 상태**:
- Self Review와 Approver만 있음
- 코드 품질 검증 부족

**개선 방안**:
- 코드 품질 검사 (linting, formatting)
- 보안 검사
- 성능 검사
- 아키텍처 준수 검증

#### 4. 롤백 메커니즘 미완성
**현재 상태**:
- Task 취소는 있으나 롤백 기능 불명확

**개선 방안**:
- Git 기반 롤백
- Stage별 롤백
- 변경사항 미리보기 및 선택적 롤백

#### 5. 병렬 실행 검증 부족
**현재 상태**:
- Sprint 내 Task 병렬 실행은 지원하나 충돌 검증 부족

**개선 방안**:
- 파일 충돌 사전 검사
- 의존성 검증
- 자동 충돌 해결

#### 6. 프로젝트 레벨 검증 부족
**현재 상태**:
- Project Review Agent는 있으나 실제 검증 로직 불명확

**개선 방안**:
- 전체 아키텍처 준수 검증
- 요구사항 충족 검증
- 통합 테스트 자동 실행

---

## 종합 평가 및 우선순위

### 강점
1. ✅ Tiered Context System으로 효율적 컨텍스트 관리
2. ✅ Visual Reality Hook으로 프로젝트 상태 자동 주입
3. ✅ Worker Squad Workflow로 체계적 개발 프로세스
4. ✅ UI로 프로젝트 구조 시각화

### 개선 우선순위

#### High Priority
1. **컨텍스트 크기 제한 및 Task Granularity 강화**
   - LLM 모델별 최대 토큰 수 고려
   - Task 크기 검증 및 자동 분할
   - 파일 내용 크기 제한

2. **Task 상태 변경 UI 개선**
   - Task Tree에서 직접 상태 변경
   - Context menu 추가
   - 실시간 진행률 표시

3. **실패 복구 메커니즘**
   - 자동 복구 로직
   - 명확한 에러 메시지
   - Fallback 전략

#### Medium Priority
4. **Visual Reality Hook 정보 보강**
   - 더 상세한 컴포넌트 상태
   - Drift 구체적 내용
   - 관련 파일 목록

5. **Task 필터링 및 검색**
   - Status/Sprint별 필터링
   - 검색 기능
   - 정렬 기능

6. **타임아웃 및 리소스 제한**
   - Stage별 타임아웃
   - 리소스 모니터링
   - 자동 취소

#### Low Priority
7. **Task 의존성 시각화**
8. **코드 품질 검증 강화**
9. **롤백 메커니즘 완성**

---

## 결론

현재 Manifest는 **바이브코딩**의 핵심 개념을 잘 구현하고 있습니다:
- ✅ 프로젝트 구조 시각화 (Structure View)
- ✅ 효율적 컨텍스트 전달 (Tiered Context, Visual Reality)
- ✅ 작업 진행상황 확인 (Task Tree, Worker Squad Progress)
- ✅ 체계적 개발 프로세스 (Worker Squad Workflow)

다만, **컨텍스트 크기 관리**, **UI 상호작용 개선**, **실패 복구 메커니즘** 등이 추가로 필요합니다.
