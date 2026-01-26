# Manifest 프로젝트 요구사항 명세서

**버전**: 1.0
**최종 업데이트**: 2025-01-23

## 프로젝트 목표

### 문제 정의
**Code Blindness**: 개발자가 대규모 코드베이스에서 다음을 파악하기 어려움
- 전체적인 아키텍처 구조
- 컴포넌트 간 의존성
- 설계 의도와 실제 구현의 일치 여부
- 변경사항의 영향 범위

### 해결 방안
**AI-Native Orchestration IDE**: 개발자를 Conductor(지휘자)로 승격
- Visual Truth: 설계와 구현의 실시간 동기화
- Tiered Context: Mission Stage에 따른 계층적 컨텍스트
- Drift Detection: 아키텍처 불일치 실시간 감지
- Multi-Agent System: 전문 Agent들의 협업

## 기능 요구사항 (Functional Requirements)

### FR-1: Visual Truth System
**우선순위**: Critical
**상태**: ✅ 완전 구현

**설명**: 설계(Architect)와 구현(Blueprint)의 실시간 동기화

**요구사항**:
- Architect View에서 의도(intent)와 요구사항(requirements) 표시
- Blueprint View에서 기술 설계(components, contracts) 표시
- 두 뷰 간의 실시간 동기화
- 불일치 시 즉시 감지 및 표시

**구현 위치**:
- `src/manifest/ui/app.py`: View 관리
- `src/manifest/ui/widgets.py`: RequirementMap, ArchitectureGraph
- `src/manifest/audit/drift_auditor.py`: 불일치 감지

### FR-2: Tiered Context System
**우선순위**: Critical
**상태**: ✅ 완전 구현

**설명**: Mission Stage에 따른 계층적 컨텍스트 제공

**요구사항**:
- **Tier 0 (The Law)**: 모든 Agent에 Policy 주입
  - 파일: `.claude/rules/manifest-policy.md`
  - 내용: Blueprint-First Development 원칙
- **Tier 1 (The Intent)**: Orchestrator/Planner에게 제공
  - 파일: `architecture.json`, `blueprint.json` (high-level)
  - 내용: 아키텍처 및 고수준 목표
- **Tier 2 (The Blueprint)**: Coder에게 제공
  - 파일: `blueprint.json` (relevant nodes)
  - 내용: 관련 컴포넌트 및 구조적 스펙
- **Tier 3 (Surgical Code)**: 필요 시에만 제공
  - 파일: Blueprint에서 참조된 파일 또는 Agent가 요청한 파일
  - 내용: 전체 파일 내용

**구현 위치**:
- `src/manifest/agents/context_provider.py`: Tiered Context 제공
- `src/manifest/agents/task_scoper.py`: Task 범위 관리

### FR-3: Multi-Agent System
**우선순위**: Critical
**상태**: ⚠️ 부분 구현 (60%)

**설명**: 여러 전문 Agent의 협업을 통한 작업 수행

**Agent 타입**:
1. **Orchestrator**: Mission 조정 및 Task 위임
2. **Planner**: 상세 Task 계획 및 Blueprint 생성
3. **Coder**: 코드 구현
4. **Test**: 테스트 작성 및 실행
5. **Review**: 코드 리뷰

**요구사항**:
- ✅ Agent Infrastructure: 완전 구현
  - AgentExecutor (LLM API 호출)
  - AgentManager (Agent 생성/관리)
  - AgentBridge (통합)
- ✅ 개별 Agent 실행: 완전 구현
  - `/start_agent <task_id> <agent_type>` 명령어
  - Agent별 프롬프트 생성
  - Context 주입
- ⚠️ Agent 간 협업: 부분 구현
  - 구조는 있으나 실제 메시지 전달 미완성
- ❌ 자동 워크플로우: 미구현
  - Orchestrator → Planner → Coder 자동 흐름

**구현 위치**:
- `src/manifest/runtime/agent/`: Agent 실행 시스템
- `src/manifest/agents/agent_coordinator.py`: Agent 조정
- `src/manifest/bridge/agent_bridge.py`: Agent 통합

### FR-4: Architecture Drift Detection
**우선순위**: High
**상태**: ✅ 완전 구현

**설명**: 아키텍처와 코드 간의 불일치 실시간 감지

**요구사항**:
- AST 파싱을 통한 코드 구조 추출
- Top-down Blueprint (`.manifest/blueprint.json`)와 Bottom-up Blueprint 비교
- 충돌 감지 및 심각도 분류 (ERROR, WARNING, INFO)
- Inspector View에 실시간 표시

**구현 위치**:
- `src/manifest/audit/drift_auditor.py`: 드리프트 감지
- `src/manifest/audit/code_extractor.py`: 코드 구조 추출
- `src/manifest/audit/blueprint_comparator.py`: Blueprint 비교

### FR-5: State Continuity
**우선순위**: High
**상태**: ✅ 완전 구현

**설명**: 세션 중단 후에도 정확한 재개

**요구사항**:
- Mission Tree 영속성
- Task Checklist 영속성
- Chat History 영속성
- Last Action 기록
- 세션 재개 시 "Next Action" 프롬프트

**구현 위치**:
- `src/manifest/core/state_manager.py`: 상태 영속성

### FR-6: Settings Management UI
**우선순위**: Medium
**상태**: ✅ 완전 구현

**설명**: 모든 설정을 UI에서 관리 (파일 직접 편집 불필요)

**요구사항**:
- API 키 설정/검증 (Anthropic, OpenAI, Google)
- Agent 모델 선택 (provider, model)
- Skills 관리 (agent 기본, 프로젝트 스코프)
- Policy 파일 편집
- `/config` 명령어 또는 `Ctrl+,` 단축키

**구현 위치**:
- `src/manifest/ui/settings_screen.py`: Settings UI
- `src/manifest/core/settings_manager.py`: 통합 설정 관리

### FR-7: Skills System
**우선순위**: Medium
**상태**: ✅ 완전 구현

**설명**: Agent별 및 프로젝트별 Skills 관리 (OpenCode 컨벤션)

**요구사항**:
- Agent 기본 Skills (`.manifest/agent_config.json`)
- 프로젝트 스코프 Skills (`AGENTS.md`)
- Skill 정의 파일 (`.claude/rules/*.md`)
- Skills를 Agent 프롬프트에 자동 주입

**구현 위치**:
- `src/manifest/agents/skills_manager.py`: Skills 관리

### FR-8: Terminal Command Execution
**우선순위**: High
**상태**: ✅ 완전 구현

**설명**: Agent가 터미널 명령을 실행할 수 있어야 함

**요구사항**:
- OpenCode 선택적 통합 (있으면 사용, 없으면 Fallback)
- 프로세스 추적 및 취소
- Watchdog 통합
- 스트리밍 출력

**구현 위치**:
- `src/manifest/runtime/router/terminal_router.py`: 터미널 라우터
- `src/manifest/runtime/opencode_adapter.py`: OpenCode 통합

### FR-9: User Input Processing
**우선순위**: Critical
**상태**: ⚠️ 부분 구현 (30%)

**설명**: 사용자 입력을 Agent로 전달하여 처리

**요구사항**:
- 사용자 입력을 Agent로 전달
- Agent 응답을 실시간으로 UI에 표시
- 명령어 처리 (`/audit`, `/config`, `/start_agent`, etc.)

**현재 상태**:
- ✅ 명령어 처리: 완전 구현
- ⚠️ 일반 입력 → Agent: 부분 구현 (주석 처리됨)
- ⚠️ Agent 출력 표시: 제한적 (동적 TabPane 제한)

**구현 위치**:
- `src/manifest/ui/app.py:779`: "In real implementation" 주석

### FR-10: Container Support
**우선순위**: Medium
**상태**: ⚠️ 부분 구현 (40%)

**설명**: Docker 컨테이너에서 Agent 실행 지원

**요구사항**:
- Docker 컨테이너에서 Agent 실행
- 컨테이너 간 통신
- State 동기화

**현재 상태**:
- ✅ ContainerManager: 기본 구조 구현
- ⚠️ Container Communication: 부분 구현
- ❌ 완전한 통신 프로토콜: 미구현

## 비기능 요구사항 (Non-Functional Requirements)

### NFR-1: 성능
**우선순위**: High

**요구사항**:
- 앱 시작 시간: < 1초 ✅
- 드리프트 감지: 프로젝트 크기에 비례 ✅
- 상태 저장: < 100ms ✅
- 뷰 전환: 즉시 ✅
- Agent 시작: < 500ms ✅

### NFR-2: 보안
**우선순위**: Critical

**요구사항**:
- API 키 암호화 저장 ✅
- 파일 권한 관리 (0o600) ✅
- 입력 검증 ✅
- 네트워크 통신 암호화 (향후)

### NFR-3: 확장성
**우선순위**: Medium

**요구사항**:
- 모듈화된 구조 ✅
- 플러그인 가능한 아키텍처 ✅
- 선택적 의존성 지원 ✅

### NFR-4: 테스트 가능성
**우선순위**: High

**요구사항**:
- 단위 테스트 커버리지 > 70% ✅ (현재 ~70%)
- Mock 기반 테스트 ✅
- 통합 테스트 ✅

### NFR-5: 사용성
**우선순위**: High

**요구사항**:
- 직관적인 TUI 인터페이스 ✅
- 명확한 명령어 시스템 ✅
- 실시간 피드백 ✅
- 에러 메시지 명확성 ✅

## 제약사항 (Constraints)

### 기술적 제약사항
1. **Textual 프레임워크 제한**
   - 동적 TabPane 생성 제한
   - 중첩 App 실행 시 이벤트 루프 충돌

2. **Python 3.9+ 요구**
   - 최신 Python 기능 사용

3. **선택적 의존성**
   - GitPython: Git 통합 (선택적)
   - OpenCode: 터미널 실행 (선택적)
   - Docker: 컨테이너 실행 (선택적)

### 아키텍처 제약사항
1. **Blueprint-First Development**
   - 모든 구조적 변경은 Blueprint에 먼저 반영
   - Blueprint와 코드의 일관성 유지

2. **Tiered Context**
   - Mission Stage에 따라 다른 컨텍스트 제공
   - 불필요한 정보 노출 최소화

3. **State Continuity**
   - 모든 상태 변경은 영속화되어야 함
   - 세션 재개 시 정확한 상태 복원

## 데이터 요구사항

### 필수 데이터 파일
1. **`.manifest/state.json`**: 애플리케이션 상태
2. **`.manifest/intent.json`**: 의도 및 요구사항
3. **`.manifest/blueprint.json`**: 기술 설계
4. **`.manifest/agent_config.json`**: Agent 설정

### 선택적 데이터 파일
1. **`.claude/rules/manifest-policy.md`**: 정책 (없으면 기본값)
2. **`AGENTS.md`**: 프로젝트 스코프 Skills (없으면 기본값)
3. **`.claude/rules/*.md`**: Skill 정의 파일들

### 데이터 무결성
- JSON 스키마 검증
- 파일 권한 관리
- 백업 및 복구 (향후)

## 인터페이스 요구사항

### 사용자 인터페이스
1. **TUI (Textual 기반)**
   - 5-View Workspace
   - Inspector View (3 모드)
   - Mission Control Sidebar
   - Settings Screen (별도 Screen)

### 명령어 인터페이스
- `/audit`: 드리프트 감지
- `/config [tab]`: Settings 열기
- `/start_agent <task_id> <agent_type>`: Agent 시작
- `/stop_agent <task_id>`: Agent 중지
- `/reload`: 데이터 재로드
- `/status`: 상태 확인

### API 인터페이스
- AgentBridge: Agent 시스템 통합
- StateManager: 상태 관리
- ConfigManager: 설정 관리
- SettingsManager: 통합 설정 관리

## 통합 요구사항

### 외부 시스템 통합
1. **LLM APIs**
   - Anthropic Claude API ✅
   - OpenAI API ✅
   - Google Gemini API (기본 지원)

2. **OpenCode** (선택적)
   - 자동 감지 및 사용 ✅
   - Fallback 내부 구현 ✅

3. **Git** (선택적)
   - GitPython을 통한 히스토리 표시 ✅

4. **Docker** (선택적)
   - 컨테이너 기반 Agent 실행 ⚠️

## 품질 요구사항

### 신뢰성
- 상태 영속성 보장 ✅
- 에러 처리 및 복구 ✅
- Watchdog을 통한 프로세스 모니터링 ✅

### 유지보수성
- 모듈화된 구조 ✅
- 명확한 책임 분리 ✅
- 포괄적인 테스트 ✅

### 확장성
- 새로운 Agent 타입 추가 용이 ✅
- 새로운 View 추가 용이 ✅
- 플러그인 아키텍처 (향후)

## 구현 우선순위

### Phase 1: UI & Infrastructure ✅ (100% 완료)
- [x] UI Infrastructure
- [x] Core Infrastructure
- [x] Settings Management
- [x] Drift Detection
- [x] State Management
- [x] User Input → Agent 통합 (Critical) ✅ 완료됨 (2026-01-26)

### Phase 2: Agent System Integration ✅ (95% 완료)
- [x] Agent Infrastructure
- [x] Agent Execution
- [x] User Input → Agent 통합 (Critical) ✅ 완료됨 (2026-01-26)
- [x] Agent Output Display 개선 (High) ✅ 완료됨 (2026-01-26)
- [ ] Multi-Agent Workflow (High) ⚠️ 부분 구현 (60%)

### Phase 3: Advanced Features ❌ (20% 완료)
- [ ] Context Injection Hooks
- [ ] Structural Spec-First Management
- [ ] Shadow Manager
- [ ] Container Communication 완성

## 테스트 요구사항

### 단위 테스트
- 모든 Core 모듈 테스트 ✅
- 모든 Agent 모듈 테스트 ✅
- UI 모듈 테스트 (부분) ⚠️

### 통합 테스트
- Agent Bridge 통합 테스트 ✅
- State Manager 통합 테스트 ✅
- UI 통합 테스트 ✅

### 사용자 시나리오 테스트
- 전체 워크플로우 테스트 (부분) ⚠️

## 문서화 요구사항

### 사용자 문서
- [x] README.md
- [x] USER_GUIDE.md
- [x] API.md

### 개발자 문서
- [x] ARCHITECTURE.md
- [x] MODULES.md
- [x] DEV_SETUP.md
- [x] PROJECT_STATUS.md
- [x] MANIFEST_ARCHITECTURE.md (이 문서)

### API 문서
- [x] API.md
- [x] MODULES.md

## 배포 요구사항

### 설치
- Python 3.9+ ✅
- Virtual Environment 지원 ✅
- Docker 지원 (선택적) ✅

### 설정
- API 키 설정 (필수) ✅
- Agent 모델 설정 (선택적) ✅
- Skills 설정 (선택적) ✅

## 향후 요구사항 (Backlog)

### High Priority
1. User Input → Agent 통합 완성
2. Agent Output Display 개선
3. Multi-Agent Workflow 구현

### Medium Priority
1. Container Communication 완성
2. Context Injection Hooks
3. Structural Spec-First Management

### Low Priority
1. Shadow Manager
2. Visual Editor
3. Plugin System
