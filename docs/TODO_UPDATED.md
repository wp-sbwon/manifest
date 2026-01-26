# TODO 리스트 업데이트 (2026-01-26)

**목적**: OpenCode LLM adapter 구조 변경에 따른 TODO 리스트 업데이트

---

## ✅ 완료된 항목 (구조 변경으로 인해)

### 문서 업데이트
- [x] ARCHITECTURE.md: LLM execution backend 구조 설명
- [x] API.md: ExecutorFactory, OpenCodeLLMAdapter API 문서
- [x] USER_GUIDE.md: OpenCode 설정 방법
- [x] MODULES.md: 새로운 모듈 구조 반영
- [x] PROJECT_STATUS.md: 최신 구조 반영

### 코드 정리
- [x] ExecutorFactory에서 Claude Code fallback 제거
- [x] Claude Code 관련 주석 및 문서 언급 제거

### 테스트
- [x] OpenCodeLLMAdapter 단위 테스트 (13개 테스트 모두 통과)

---

## 🔄 업데이트된 TODO 항목

### 기존 TODO → 새로운 구조에 맞게 업데이트

#### 1. "Agent 완료 감지: AgentExecutor의 chunk 처리"
**기존**: AgentExecutor의 chunk 처리, 상태 관리
**업데이트**: BaseAgentExecutor 인터페이스의 chunk 처리, 상태 관리
- AgentExecutor (Direct API) 또는 OpenCodeLLMAdapter (OpenCode) 모두 지원
- ExecutorFactory를 통해 백엔드 선택

**위치**: `docs/MULTI_AGENT_WORKFLOW_IMPROVEMENTS.md` ✅ 업데이트 완료

#### 2. "OpenCode 통합"
**기존**: Terminal command execution만 언급
**업데이트**:
- Terminal command execution: `opencode_adapter.py` (기존)
- LLM execution: `opencode_llm_adapter.py` (새로 추가)
- 두 가지 역할 구분 필요

**위치**: 여러 문서에 분산되어 있음

---

## 📋 새로운 TODO 항목 (구조 변경으로 인해 추가)

### OpenCode LLM Adapter 관련

#### 1. OpenCode 서버 연결 안정화 (High Priority)
- [ ] 서버 연결 실패 시 재시도 로직
- [ ] 서버 자동 시작 실패 처리
- [ ] 연결 타임아웃 설정 및 처리
- [ ] 서버 상태 모니터링

**위치**: `src/manifest/runtime/opencode_llm_adapter.py`
**현재 상태**: 기본 구현 완료, 안정화 필요

#### 2. 세션 관리 최적화 (Medium Priority)
- [ ] 세션 재사용 로직 개선
- [ ] 세션 타임아웃 처리
- [ ] 세션 정리 및 리소스 해제
- [ ] 동시 세션 수 제한

**위치**: `src/manifest/runtime/opencode_llm_adapter.py`
**현재 상태**: 기본 세션 관리 구현됨, 최적화 필요

#### 3. ExecutorFactory 통합 테스트 (High Priority)
- [ ] ExecutorFactory.create_executor() 테스트
- [ ] Backend 선택 로직 테스트
- [ ] 설정 기반 백엔드 생성 테스트
- [ ] 에러 처리 테스트

**위치**: `tests/unit/test_executor_factory.py` (생성 필요)

#### 4. 실제 OpenCode 서버와의 통합 테스트 (High Priority)
- [ ] 실제 OpenCode 서버 연결 테스트
- [ ] End-to-end agent 실행 테스트
- [ ] 서버 재시작 시나리오 테스트
- [ ] 네트워크 오류 시나리오 테스트

**위치**: `tests/integration/test_opencode_integration.py` (생성 필요)

#### 5. BaseAgentExecutor 인터페이스 검증 (Medium Priority)
- [ ] 모든 executor가 인터페이스 준수 확인
- [ ] Chunk 형식 일관성 검증
- [ ] 에러 처리 일관성 검증

**위치**: `src/manifest/runtime/agent/core/base_executor.py`

---

## 🔄 기존 TODO 항목 재평가

### 유지되는 항목 (구조 변경과 무관)

#### 1. Tool Execution 완료 감지 및 결과 파싱
**상태**: 여전히 유효
**이유**: OpenCode LLM adapter와 무관, Tool System의 문제
**우선순위**: Critical

#### 2. Multi-Agent Workflow 완성
**상태**: 여전히 유효
**이유**: OpenCode LLM adapter는 실행 백엔드일 뿐, 워크플로우 조정과 무관
**우선순위**: High

#### 3. 컨텍스트 크기 제한 및 최적화
**상태**: 여전히 유효
**이유**: OpenCode가 context 관리를 하지만, Manifest에서도 검증 필요
**우선순위**: High

### 업데이트가 필요한 항목

#### 1. "AgentExecutor를 통한 LLM API 호출"
**기존**: AgentExecutor 직접 사용
**업데이트**: ExecutorFactory를 통한 백엔드 선택
- Direct API: AgentExecutor
- OpenCode: OpenCodeLLMAdapter
- BaseAgentExecutor 인터페이스로 통일

**위치**: 여러 문서에 분산
**상태**: ✅ PROJECT_STATUS.md 업데이트 완료

---

## 📝 문서별 TODO 업데이트 상태

### ARCHITECTURE_CHANGES.md
- [x] 문서 업데이트 TODO 완료 표시
- [ ] 코드 정리 TODO 업데이트 필요
- [ ] 테스트 강화 TODO 업데이트 필요

### MULTI_AGENT_WORKFLOW_IMPROVEMENTS.md
- [x] Agent 완료 감지 설명 업데이트 완료

### PROJECT_STATUS.md
- [x] LLM execution system 설명 업데이트 완료

### REVISED_PRIORITIES.md (archive)
- [ ] OpenCode 통합 설명 업데이트 필요 (archive이므로 선택적)

### CODEBASE_REVIEW_FINDINGS.md (archive)
- [ ] OpenCodeAdapter 설명 업데이트 필요 (archive이므로 선택적)

---

## 🎯 우선순위별 정리

### 즉시 작업 (Critical)
1. OpenCode 서버 연결 안정화
2. ExecutorFactory 통합 테스트 작성
3. 실제 OpenCode 서버와의 통합 테스트

### 단기 작업 (High Priority)
4. 세션 관리 최적화
5. BaseAgentExecutor 인터페이스 검증

### 중기 작업 (Medium Priority)
6. 문서의 TODO 항목 업데이트 (archive 문서 제외)

---

## ✅ 체크리스트

업데이트 완료 확인:
- [x] ARCHITECTURE_CHANGES.md 문서 업데이트 TODO 완료 표시
- [x] MULTI_AGENT_WORKFLOW_IMPROVEMENTS.md Agent 완료 감지 설명 업데이트
- [x] PROJECT_STATUS.md LLM execution system 설명 업데이트
- [ ] OpenCode 서버 연결 안정화 TODO 추가
- [ ] ExecutorFactory 통합 테스트 TODO 추가
- [ ] 실제 OpenCode 서버 통합 테스트 TODO 추가

---

## 참고

- 새로운 구조: BaseAgentExecutor 인터페이스 → AgentExecutor / OpenCodeLLMAdapter
- ExecutorFactory가 백엔드 선택 및 생성 담당
- OpenCode는 LLM execution과 Terminal command execution 두 가지 역할
- 모든 TODO는 새로운 구조를 반영하여 업데이트 필요
