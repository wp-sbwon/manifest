# Orchestrator 워크플로우 및 Task 할당

**작성일**: 2026-01-24  
**목적**: Orchestrator를 통한 task 생성 및 할당 워크플로우 설명

---

## 🔄 기본 워크플로우

### 1. **Orchestrator를 통한 Task 할당 (기본)**

```
사용자 입력
    ↓
Orchestrator Agent
    ↓
Task 생성 (자동)
    ↓
Worker Squad 자동 시작 (선택적)
```

**상세 과정**:

1. **사용자 입력**: 일반 텍스트 입력 (명령어가 아닌 경우)
   - 예: "사용자 인증 기능을 구현해줘"
   - 위치: `app.py:1418-1551`

2. **Orchestrator 처리**:
   - Orchestrator Agent 생성
   - 사용자 입력을 mission description으로 처리
   - LLM을 통해 작업을 분석하고 task로 분해

3. **Task 자동 생성**:
   - Orchestrator 응답에서 task 패턴 추출
   - `_process_orchestrator_response()` 메서드가 task 생성
   - 위치: `app.py:1601-1708`
   - 패턴:
     - "Create task: <name>"
     - "Task: <name>"
     - Bullet points (`-`, `*`)
     - Numbered list (`1.`, `2.`)

4. **Worker Squad 자동 시작** (선택적):
   - Orchestrator 응답에 "start", "execute", "begin" 키워드가 있으면 자동 시작
   - `agent_coordinator._start_task_worker_squad()` 호출
   - Worker Squad는 순차적으로 agent들을 실행 (planner → coder → test → ...)

**코드 위치**:
- Orchestrator 처리: `app.py:1418-1551`
- Task 생성: `app.py:1601-1708`
- Worker Squad 시작: `app.py:1686-1703`

---

### 2. **사용자가 직접 Task 생성 및 할당 (수동)**

사용자도 직접 task를 생성하고 agent를 시작할 수 있습니다.

#### Task 생성
```
/create_task <name> [description] [stage] [status] [sprint_id]
```

**예시**:
```
/create_task "사용자 인증 구현" "로그인/로그아웃 기능" planning pending
```

**위치**: `command_handler.py:205-226`

#### Agent 시작
```
/start_agent <task_id> <agent_type>
```

**예시**:
```
/start_agent task-1 planner
/start_agent task-1 coder
```

**위치**: `command_handler.py:130-145`

#### Worker Squad 시작
```
/start_task <task_id>
```

**위치**: `command_handler.py` (구현 필요할 수 있음)

---

## 📊 워크플로우 비교

| 방식 | Task 생성 | Agent 시작 | 자동화 |
|------|-----------|------------|--------|
| **Orchestrator (기본)** | ✅ 자동 | ✅ 자동 (선택적) | 높음 |
| **사용자 직접** | ✅ 수동 | ✅ 수동 | 낮음 |

---

## 🎯 권장 사용 패턴

### 기본 사용 (Orchestrator 활용)
```
사용자: "사용자 인증 기능을 구현해줘"
  ↓
Orchestrator: "다음 task들을 생성하겠습니다:
  - 로그인 기능 구현
  - 로그아웃 기능 구현
  - 세션 관리 구현"
  ↓
자동으로 task 생성 및 Worker Squad 시작
```

### 고급 사용 (수동 제어)
```
사용자: /create_task "로그인 기능" "사용자 인증" planning pending
사용자: /start_agent task-1 planner
사용자: /start_agent task-1 coder
```

---

## 🔍 구현 세부사항

### Orchestrator 응답 파싱

**위치**: `app.py:1601-1708`

**패턴**:
```python
task_patterns = [
    r"(?:Create|Add|New)\s+task[:\s]+(.+?)(?:\n|$)",
    r"Task[:\s]+(.+?)(?:\n|$)",
    r"^\s*[-*]\s*(.+?)(?:\n|$)",  # Bullet points
    r"^\s*\d+\.\s*(.+?)(?:\n|$)",  # Numbered list
]
```

**자동 시작 조건**:
```python
auto_start = "start" in response.lower() or "execute" in response.lower() or "begin" in response.lower()
```

---

## ✅ 결론

**기본은 Orchestrator를 통한 할당이 맞습니다.**

- ✅ 사용자 입력 → Orchestrator → Task 자동 생성 → Worker Squad 자동 시작
- ✅ 사람도 `/create_task`, `/start_agent` 명령으로 직접 제어 가능
- ✅ 두 방식 모두 지원하여 유연성 제공

**권장 사항**:
- 일반적인 경우: Orchestrator 활용 (자동화)
- 세밀한 제어가 필요한 경우: 수동 명령 사용
