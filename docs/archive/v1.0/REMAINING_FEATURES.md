# 남은 기능 구현 목록

**작성일**: 2026-01-24
**기준**: MANIFEST_REQUIREMENTS.md, PROJECT_STATUS.md

## 🔴 Critical Priority (즉시 필요)

### 1. User Input → Agent 통합 완성
**현재 상태**: ✅ 대부분 구현됨 (약 80%)

**구현된 부분**:
- ✅ `app.py:1070-1150`: Orchestrator로 사용자 입력 전달 완전 구현됨
- ✅ Agent 응답 스트리밍 구현됨
- ✅ Task 자동 생성 로직 구현됨
- ✅ Worker Squad 자동 시작 로직 구현됨

**미완성 부분**:
- ⚠️ Agent 응답을 실시간으로 UI에 표시하는 완전한 통합 (동적 TabPane 제한)
- ⚠️ Squad 채널이 별도 탭이 아닌 main log에 prefix로만 표시
- ⚠️ 여러 Agent 동시 실행 시 출력 혼합 문제

**위치**: `src/manifest/ui/app.py:1070-1150`

**필요 작업**:
- Agent 응답 실시간 표시 개선 (현재는 작동하나 개선 여지 있음)
- 동적 채널 UI 구현 (Textual 제약 고려)
- Agent 출력을 별도 탭으로 표시하는 대안 구현

### 2. Agent Output Display 개선
**현재 상태**: ⚠️ 부분 구현 (70%)

**구현된 부분**:
- ✅ `handle_agent_output()` 메서드 존재
- ✅ State에 Agent 출력 저장
- ✅ Main log에 출력 표시

**제한사항**:
- ⚠️ 동적 TabPane 생성이 Textual 제한으로 완전하지 않음
- ⚠️ Squad 채널이 별도 탭으로 표시되지 않고 main log에 prefix로 표시
- ✅ 코드 주석: "Full implementation would require Textual's dynamic widget support"

**필요 작업**:
- Textual의 동적 위젯 생성 방법 연구
- 또는 대안 UI 패턴 구현 (예: 채널 버튼 + 필터링)

## 🟡 High Priority

### 3. Multi-Agent Workflow 완전 통합
**현재 상태**: ⚠️ 부분 구현 (약 60%)

**구현된 부분**:
- ✅ 개별 Agent 실행 가능 (`/start_agent <task_id> <agent_type>`)
- ✅ WorkerSquadExecutor 완전 구현 (순차적 stage 실행)
- ✅ 각 Agent 타입별 구현 완료
- ✅ Orchestrator 응답에서 Task 추출 및 자동 생성 (`app.py:1162-1260`)
- ✅ Task 생성 후 Worker Squad 자동 시작 (`app.py:1239-1252`)
- ✅ Sprint 내 Task 병렬 실행 (`SprintExecutor`)

**미구현 부분**:
- ⚠️ Agent 간 직접 메시지 전달 프로토콜
- ⚠️ Agent 완료 대기 및 결과 파싱 로직
- ⚠️ Agent 출력에서 다음 stage 트리거 자동화

**위치**:
- `src/manifest/agents/worker_squad_executor.py` - 구조는 완전하나 Agent 완료 대기 로직 필요
- `src/manifest/agents/agent_coordinator.py:427` - TODO 주석 (Blueprint 충돌 시 Planner 전달)

**필요 작업**:
- Agent 완료 이벤트 처리 및 결과 파싱
- Agent 간 메시지 전달 프로토콜 구현
- Agent 출력에서 자동으로 다음 stage 트리거

### 4. Agent Bridge → Planner 통합
**현재 상태**: ❌ 미구현

**위치**: `src/manifest/agents/agent_coordinator.py:427`
```python
# TODO: Integrate with agent bridge to actually send to planner
# await self.agent_bridge.send_to_planner(planner_request)
```

**필요 작업**:
- Blueprint 충돌 시 Planner로 자동 전달
- `AgentBridge.send_to_planner()` 메서드 구현
- Planner 응답 처리 및 Blueprint 업데이트

## 🟢 Medium Priority

### 5. Container-to-Container Communication
**현재 상태**: ⚠️ 부분 구현 (40%)

**구현된 부분**:
- ✅ ContainerManager 기본 구조
- ✅ ContainerStateSync 클래스 존재
- ✅ ContainerMessageBus 구조 존재

**미구현 부분**:
- ❌ Docker 컨테이너 간 완전한 통신 프로토콜
- ❌ Container State Sync 완전 구현
- ❌ 컨테이너 간 메시지 라우팅

**위치**: `src/manifest/agents/container_communication.py`

**필요 작업**:
- 컨테이너 간 통신 프로토콜 완성
- State 동기화 로직 완성
- 메시지 버스 라우팅 구현

### 6. Bootstrap UI 이벤트 루프 충돌 해결
**현재 상태**: ⚠️ 부분 구현 (50%)

**구현된 부분**:
- ✅ BootstrapApp 클래스 완전 구현
- ✅ API 키 입력 UI
- ✅ 키 검증 기능

**문제**:
- ⚠️ Textual 앱 중첩 실행 시 이벤트 루프 충돌
- ⚠️ 현재는 데모 모드로 동작 (수동 키 설정 필요)

**필요 작업**:
- 모달 방식으로 변경
- 또는 별도 프로세스 실행
- 이벤트 루프 충돌 해결

### 7. Approval Buttons/Widgets
**현재 상태**: ❌ 미구현

**위치**: `src/manifest/ui/app.py:644`
```python
# TODO: Add approval buttons/widgets
# For now, user can approve via command: /approve_sprint {sprint_id}
```

**필요 작업**:
- Sprint 승인 UI 위젯 추가
- Task 승인 UI 개선
- GateController와 통합

## 🔵 Low Priority

### 8. Context Injection Hooks
**현재 상태**: ❌ 미구현 (0%)

**구현된 부분**:
- ✅ HookManager 클래스 존재
- ✅ VisualRealityHook 기본 구조 존재
- ✅ PromptHook ABC 존재

**미구현 부분**:
- ❌ 프롬프트 가로채기 시스템 완전 구현
- ❌ Visual Reality 주입 로직
- ❌ Runtime Hook 시스템 활성화

**위치**: `src/manifest/runtime/hooks/prompt_hooks.py`

**필요 작업**:
- Hook 시스템 활성화
- Visual Reality 주입 로직 구현
- 프롬프트 수정 파이프라인 완성

### 9. Structural Spec-First Management
**현재 상태**: ❌ 미구현 (0%)

**구현된 부분**:
- ✅ Blueprint 비교 가능
- ✅ StructureManager 기본 구조
- ✅ 변경 제안 생성 가능

**미구현 부분**:
- ❌ Blueprint 기반 자동 파일 시스템 관리
- ❌ 구조적 변경 제안 자동화
- ❌ Blueprint 변경 시 자동 코드 업데이트

**위치**: `src/manifest/audit/monitoring/structure_manager.py`

**필요 작업**:
- Blueprint 변경 감지 및 자동 코드 업데이트
- 파일 시스템 자동 관리
- 변경 제안 승인 워크플로우

### 10. Shadow Manager 완전 구현
**현재 상태**: ❌ 미구현 (0%)

**구현된 부분**:
- ✅ ShadowManager 클래스 존재
- ✅ Shadow 프로세스 실행 가능
- ✅ 출력 스트리밍 구현됨

**미구현 부분**:
- ❌ 샌드박스 운영
- ❌ 안전한 승격 로직
- ❌ 변경사항 검토 시스템

**위치**: `src/manifest/runtime/shadow_manager.py`

**필요 작업**:
- 샌드박스 환경 설정
- 승격 로직 구현
- 변경사항 검토 UI

### 11. Git Integration 고급 기능
**현재 상태**: ⚠️ 부분 구현 (70%)

**구현된 부분**:
- ✅ GitPython 선택적 의존성
- ✅ Git 히스토리 표시
- ✅ Git 없을 때 graceful fallback

**미구현 부분**:
- ❌ Git 기반 Blueprint 동기화
- ❌ Git 워크플로우 통합
- ❌ Commit 기반 변경 추적

**필요 작업**:
- Blueprint와 Git 연동
- Commit 메시지 자동 생성
- Git 워크플로우 통합

### 12. Task 생명주기 관리
**현재 상태**: ⚠️ 부분 구현 (60%)

**구현된 부분**:
- ✅ Task 저장/로드
- ✅ Task 표시 (UI)
- ✅ Task 승인/거부
- ✅ Task Stage 변경

**미구현 부분**:
- ❌ Task 삭제 기능
- ❌ Task 편집 기능 (직접 State 수정 필요)
- ❌ Task 검색/필터링
- ❌ Task 자동 생성 (Orchestrator/Planner에서)

**위치**: `docs/TASK_MANAGER_STATUS.md`

**필요 작업**:
- `StateManager.delete_task()` 메서드
- `StateManager.update_task()` 메서드
- `StateManager.find_tasks()` 메서드
- UI에서 Task 편집/삭제 기능

## 📊 우선순위별 요약

### Critical (즉시 필요)
1. **User Input → Agent 통합 완성** (30% → 100%)
2. **Agent Output Display 개선** (70% → 100%)

### High Priority
3. **Multi-Agent Workflow 구현** (20% → 100%)
4. **Agent Bridge → Planner 통합** (0% → 100%)

### Medium Priority
5. **Container Communication 완성** (40% → 100%)
6. **Bootstrap UI 이벤트 루프 해결** (50% → 100%)
7. **Approval Buttons/Widgets** (0% → 100%)

### Low Priority
8. **Context Injection Hooks** (0% → 100%)
9. **Structural Spec-First Management** (0% → 100%)
10. **Shadow Manager 완전 구현** (0% → 100%)
11. **Git Integration 고급 기능** (70% → 100%)
12. **Task 생명주기 관리** (60% → 100%)

## 📈 전체 완성도

**Phase 1: UI & Infrastructure**: ✅ 90% 완료
- User Input → Agent 통합만 남음

**Phase 2: Agent System Integration**: ⚠️ 60% 완료
- User Input → Agent 통합 완성 필요
- Agent Output Display 개선 필요
- Multi-Agent Workflow 구현 필요

**Phase 3: Advanced Features**: ❌ 20% 완료
- 대부분 미구현 상태

## 🎯 다음 단계 권장사항

### 즉시 작업 (Critical)
1. User Input → Agent 통합 완성 확인 및 개선
   - 현재 코드가 이미 구현되어 있는지 재확인
   - 실시간 표시 개선
2. Agent Output Display 개선
   - Textual 제약 고려한 대안 구현

### 단기 작업 (High Priority)
3. Multi-Agent Workflow 자동화
4. Agent Bridge → Planner 통합

### 중기 작업 (Medium Priority)
5. Container Communication 완성
6. Bootstrap UI 문제 해결
7. Approval UI 개선

---

## 📋 PROJECT_REVIEW.md에서 추가로 확인된 개선 사항

**참고**: `PROJECT_REVIEW.md` 문서에서 바이브코딩 관점의 추가 개선 사항들이 확인되었습니다.

### High Priority (프로세스 개선)

#### 1. 컨텍스트 크기 제한 및 Task Granularity 강화
**현재 상태**: ⚠️ 부분 구현
- ✅ Task Granularity 검증 로직 존재 (`task_scoper.py:199`)
- ✅ Orchestrator에 granularity 규칙 주입 (`orchestrator_agent.py:198-202`)
- ❌ 컨텍스트 크기 계산 및 제한 없음
- ❌ 모델별 최대 토큰 수 고려 없음
- ❌ 파일 내용 크기 제한 없음

**필요 작업**:
- 컨텍스트 크기 계산 로직 (토큰 수 추정)
- 모델별 최대 토큰 수 설정 및 검증
- 파일 크기 제한 (1000줄 이상이면 관련 부분만 추출)
- Task가 너무 크면 자동 분할 제안

**위치**: `src/manifest/agents/context_provider.py`, `task_scoper.py`

#### 2. Task 상태 변경 UI 개선
**현재 상태**: ⚠️ 부분 구현
- ✅ Task Tree View 존재
- ✅ CLI 명령어로 상태 변경 가능
- ❌ UI에서 직접 클릭으로 변경 불가
- ❌ Context menu 없음
- ❌ 실시간 진행률 표시 없음

**필요 작업**:
- Task Tree에서 Task 클릭 시 상세 정보 및 액션 표시
- Context menu로 상태 변경
- 실시간 진행률 표시 (예: 50% complete)
- 예상 완료 시간 표시

**위치**: `src/manifest/ui/widgets/project_view.py`

#### 3. 실패 복구 메커니즘
**현재 상태**: ❌ 미구현
- ✅ 각 Stage 실패 시 에러 처리
- ✅ Debug 반복으로 자동 수정 시도
- ❌ 실패 원인 분석 및 자동 복구 로직 없음
- ❌ Fallback 전략 없음 (예: 다른 모델 사용)
- ❌ 명확한 에러 메시지 및 해결 방안 제시 부족

**필요 작업**:
- 실패 원인 분석 로직
- 자동 복구 시도 (다른 접근 방식)
- Fallback 전략 (다른 모델, 다른 프롬프트)
- 사용자에게 명확한 에러 메시지 및 해결 방안 제시

**위치**: `src/manifest/agents/worker_squad_executor.py`

### Medium Priority

#### 4. Visual Reality Hook 정보 보강
**현재 상태**: ⚠️ 부분 구현
- ✅ Visual Reality Hook 기본 구조 존재
- ✅ Architecture Status, Implementation Status 제공
- ❌ 상위 5개 Feature만 표시 (제한적)
- ❌ Implementation Status가 숫자만 표시 (구체적 정보 없음)
- ❌ Drift 정보에 구체적 불일치 내용 없음

**필요 작업**:
- 더 상세한 컴포넌트 상태 정보 제공
- Drift 구체적 내용 포함
- 관련 파일 목록 표시
- UI와 동일한 정보 제공

**위치**: `src/manifest/runtime/hooks/prompt_hooks.py`

#### 5. Task 필터링 및 검색
**현재 상태**: ❌ 미구현
- ✅ Task 목록 표시
- ❌ Status별 필터링 없음
- ❌ Sprint별 필터링 없음
- ❌ Task 이름/ID 검색 없음
- ❌ 정렬 기능 없음

**필요 작업**:
- Status별 필터링 (pending, in_progress, done, etc.)
- Sprint별 필터링
- Task 이름/ID 검색
- 정렬 기능 (날짜, 상태, 우선순위)

**위치**: `src/manifest/ui/widgets/project_view.py`

#### 6. 타임아웃 및 리소스 제한
**현재 상태**: ❌ 미구현
- ✅ Watchdog으로 프로세스 모니터링
- ❌ Stage별 타임아웃 없음
- ❌ 리소스 사용량 제한 없음
- ❌ 자동 취소 로직 없음

**필요 작업**:
- Stage별 타임아웃 설정
- 리소스 사용량 모니터링 및 제한
- 타임아웃 시 자동 취소 로직
- 리소스 초과 시 경고 및 중단

**위치**: `src/manifest/agents/worker_squad_executor.py`, `watchdog.py`

### Low Priority

#### 7. Task 의존성 시각화
**현재 상태**: ❌ 미구현
- ❌ Task 간 의존성 정보 없음
- ❌ Blocked 상태의 원인 표시 없음
- ❌ 병렬 실행 가능 여부 표시 없음

**필요 작업**:
- Task 의존성 그래프
- Blocked 상태의 원인 표시
- 병렬 실행 가능 여부 표시

#### 8. 코드 품질 검증 강화
**현재 상태**: ⚠️ 부분 구현
- ✅ Self Review와 Approver 존재
- ❌ 코드 품질 검사 (linting, formatting) 없음
- ❌ 보안 검사 없음
- ❌ 성능 검사 없음
- ❌ 아키텍처 준수 검증 없음

**필요 작업**:
- 코드 품질 검사 통합
- 보안 검사
- 성능 검사
- 아키텍처 준수 검증

#### 9. 롤백 메커니즘 완성
**현재 상태**: ⚠️ 부분 구현
- ✅ `/cancel_task` 명령어 존재
- ❌ Git 기반 롤백 기능 없음
- ❌ 특정 Stage로 롤백 없음
- ❌ 변경사항 미리보기 없음

**필요 작업**:
- Git 기반 롤백 기능
- Stage별 롤백
- 변경사항 미리보기 및 선택적 롤백

---

## 📊 통합 우선순위 (기능 구현 + 프로세스 개선)

### Critical (즉시 필요)
1. **Agent 완료 대기 및 결과 파싱** (기능 구현)
2. **Agent Output Display 개선** (기능 구현)
3. **컨텍스트 크기 제한 및 Task Granularity 강화** (프로세스 개선)

### High Priority
4. **Multi-Agent Workflow 자동화** (기능 구현)
5. **Agent Bridge → Planner 통합** (기능 구현)
6. **Task 상태 변경 UI 개선** (프로세스 개선)
7. **실패 복구 메커니즘** (프로세스 개선)

### Medium Priority
8. **Container Communication 완성** (기능 구현)
9. **Bootstrap UI 이벤트 루프 해결** (기능 구현)
10. **Approval Buttons/Widgets** (기능 구현)
11. **Visual Reality Hook 정보 보강** (프로세스 개선)
12. **Task 필터링 및 검색** (프로세스 개선)
13. **타임아웃 및 리소스 제한** (프로세스 개선)

### Low Priority
14. **Context Injection Hooks** (기능 구현)
15. **Structural Spec-First Management** (기능 구현)
16. **Shadow Manager 완전 구현** (기능 구현)
17. **Git Integration 고급 기능** (기능 구현)
18. **Task 생명주기 관리** (기능 구현)
19. **Task 의존성 시각화** (프로세스 개선)
20. **코드 품질 검증 강화** (프로세스 개선)
21. **롤백 메커니즘 완성** (프로세스 개선)
