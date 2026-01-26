# 아키텍처 변경사항 정리

**작성일**: 2026-01-26
**목적**: OpenCode LLM adapter 통합으로 인한 구조 변경사항 정리

---

## 주요 변경사항

### 1. LLM Execution Backend 아키텍처 변경

#### 이전 구조
- `AgentExecutor`가 직접 LLM API 호출
- 단일 실행 방식만 지원
- Context 관리, Tool execution을 Manifest에서 직접 처리

#### 현재 구조
- **BaseAgentExecutor**: 모든 executor의 공통 인터페이스
- **ExecutorFactory**: 백엔드 선택 및 생성
- **AgentExecutor**: Direct LLM API 호출 (기존 방식)
- **OpenCodeLLMAdapter**: OpenCode HTTP API를 통한 LLM 실행 (새로운 방식)

```
┌─────────────────────────────────────────────────────────┐
│              AgentBridge / AgentManager                 │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │         ExecutorFactory                          │  │
│  │  (백엔드 선택: direct 또는 opencode)              │  │
│  └──────────────────────────────────────────────────┘  │
│                    │                                    │
│        ┌───────────┴───────────┐                       │
│        │                       │                       │
│  ┌─────▼─────┐        ┌────────▼────────┐            │
│  │ AgentExecutor      │ OpenCodeLLMAdapter            │
│  │ (Direct API)       │ (OpenCode HTTP API)            │
│  └───────────┘        └─────────────────┘            │
│        │                       │                       │
│        └───────────┬───────────┘                       │
│                    │                                    │
│            BaseAgentExecutor (인터페이스)              │
└─────────────────────────────────────────────────────────┘
```

### 2. 설정 시스템 확장

#### 새로운 설정 키
- `agent.execution_backend`: "direct" 또는 "opencode" (기본값: "opencode")
- `opencode.server_host`: OpenCode 서버 호스트 (기본값: "localhost")
- `opencode.server_port`: OpenCode 서버 포트 (기본값: 4096)
- `opencode.auto_start`: 서버 자동 시작 여부 (기본값: true)

#### ConfigManager 확장
- `get_setting(key, default)`: Dot notation 지원 (예: "agent.execution_backend")
- `set_setting(key, value)`: Dot notation 지원

### 3. OpenCode 통합

#### OpenCodeLLMAdapter 역할
- OpenCode 서버와 HTTP API로 통신
- Context 관리, Tool execution을 OpenCode에 위임
- Manifest는 워크플로우 오케스트레이션에 집중

#### 서버 관리
- 자동 감지: 기존 서버가 실행 중인지 확인
- 자동 시작: 서버가 없으면 `opencode serve` 실행
- 세션 관리: Agent별 세션 생성 및 재사용

### 4. 코드 변경사항

#### AgentBridge
```python
# 이전
self.executor = AgentExecutor(config_manager, state_manager, hook_manager)

# 현재
from manifest.runtime.agent.core.executor_factory import ExecutorFactory
self.executor = ExecutorFactory.create_executor(
    config_manager or ConfigManager(),
    state_manager
)
```

#### AgentManager
- `executor` 파라미터로 `BaseAgentExecutor` 인터페이스 사용
- Backend에 관계없이 동일한 인터페이스로 작동

### 5. Claude Code 제거

#### 제거된 내용
- Claude Code backend 옵션
- 관련 주석 및 문서 언급

#### 이유
- OpenCode 우선 사용 결정
- Claude Code는 미래 옵션으로 보류

---

## 변경이 필요한 부분

### 1. 문서 업데이트 필요
- [ ] ARCHITECTURE.md: LLM execution backend 구조 설명
- [ ] API.md: ExecutorFactory, OpenCodeLLMAdapter API 문서
- [ ] USER_GUIDE.md: OpenCode 설정 방법
- [ ] MODULES.md: 새로운 모듈 구조 반영
- [ ] PROJECT_STATUS.md: 최신 구조 반영

### 2. 코드 정리 필요
- [x] ExecutorFactory에서 Claude Code fallback 제거 (완료)
- [ ] OpenCode 서버 연결 에러 처리 개선
- [ ] 세션 관리 최적화

### 3. 테스트 강화 필요
- [x] OpenCodeLLMAdapter 단위 테스트 (완료)
- [ ] ExecutorFactory 통합 테스트
- [ ] 실제 OpenCode 서버와의 통합 테스트

---

## 아키텍처 다이어그램 업데이트

### LLM Execution Flow

```
User Input
    │
    ▼
AgentBridge
    │
    ▼
ExecutorFactory.create_executor()
    │
    ├─→ "direct" → AgentExecutor
    │                  │
    │                  └─→ Direct LLM API (Anthropic, OpenAI, etc.)
    │
    └─→ "opencode" → OpenCodeLLMAdapter
                        │
                        └─→ OpenCode HTTP API
                                │
                                └─→ OpenCode Server
                                        │
                                        └─→ LLM API + Context Management
```

### Agent Execution Flow

```
AgentManager.create_agent()
    │
    ▼
Agent Instance (OrchestratorAgent, CoderAgent, etc.)
    │
    ▼
agent.execute() → executor.execute_agent()
    │
    ├─→ AgentExecutor.execute_agent()
    │       │
    │       └─→ Direct API calls with hooks
    │
    └─→ OpenCodeLLMAdapter.execute_agent()
            │
            └─→ HTTP POST to OpenCode server
                    │
                    └─→ Stream response chunks
```

---

## 설정 예시

### settings.json
```json
{
  "agent": {
    "execution_backend": "opencode"
  },
  "opencode": {
    "server_host": "localhost",
    "server_port": 4096,
    "auto_start": true
  }
}
```

### Python 코드
```python
from manifest.core.config import ConfigManager
from manifest.runtime.agent.core.executor_factory import ExecutorFactory

config = ConfigManager()
state_manager = StateManager()

# OpenCode 백엔드 사용 (기본값)
executor = ExecutorFactory.create_executor(config, state_manager)

# Direct 백엔드 사용
executor = ExecutorFactory.create_executor(config, state_manager, backend="direct")
```

---

## 마이그레이션 가이드

### 기존 코드에서 변경 필요
1. `AgentExecutor` 직접 인스턴스화 → `ExecutorFactory.create_executor()` 사용
2. 설정 파일에 `agent.execution_backend` 추가 (선택사항, 기본값: "opencode")
3. OpenCode 사용 시 서버 설정 확인

### 호환성
- 기존 `AgentExecutor` 코드는 `direct` 백엔드로 계속 작동
- `BaseAgentExecutor` 인터페이스로 통일되어 backend 변경이 쉬움

---

## 다음 단계

1. 문서 업데이트 완료
2. OpenCode 통합 테스트 강화
3. 에러 처리 및 재시도 로직 개선
4. 성능 최적화 (세션 재사용, 연결 풀링 등)
