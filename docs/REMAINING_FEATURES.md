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
