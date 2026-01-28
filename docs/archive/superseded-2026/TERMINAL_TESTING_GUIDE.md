# 터미널에서 Manifest 테스트 가이드

**작성일**: 2026-01-28

## 빠른 시작

### 1. 앱 실행

```bash
# 프로젝트 루트에서
cd /Users/wonseongbae/Documents/Cursor/manifest

# Virtual environment 활성화
source venv/bin/activate

# 앱 실행 (OpenCode 터미널 + 상시 시각화 View)
PYTHONPATH=src python -m manifest
```

**또는** (`pip install -e .` 후):
```bash
manifest
```

실행 시 **OpenCode 터미널**(채팅/입력)과 **Manifest View**(blueprint·구조·drift·태스크 상시 표시)가 함께 뜹니다. OpenCode 설치 및 PATH 설정이 필요하며, OpenCode에 `manifest-orchestrator` 에이전트를 설정해 두어야 합니다.

### 2. API 키 / OpenCode

채팅·LLM 호출은 OpenCode에서 처리하므로, OpenCode 측 API 키 설정이 필요합니다. Manifest View는 audit/ 데이터만 표시합니다.

---

## 테스트 방법

### 1. 기본 기능 테스트

#### A. PRD 생성 (Ideation Mode)

```bash
# 앱 실행 후
# 채팅 입력창에 일반 텍스트 입력 (명령어 아님)
"사용자 인증 기능을 만들어줘"
```

**예상 동작**:
- Orchestrator가 질문을 시작
- PRD 생성 대화 진행
- PRD가 `.manifest/prd.json`에 저장됨

#### B. Task 생성 및 실행

```bash
# 앱 실행 후
/create_task "사용자 인증 구현" "로그인/로그아웃 기능 구현"
/start_task task-xxx
```

**예상 동작**:
- Task 생성됨
- Worker Squad 자동 시작 (planner → coder → test → ...)
- 진행 상황이 UI에 표시됨

#### C. Sprint 생성 및 실행

```bash
# 앱 실행 후
/create_sprint "Sprint 1" task-1 task-2 task-3
/start_sprint sprint-xxx
```

**예상 동작**:
- Sprint 생성됨
- 여러 task가 병렬로 실행됨
- Dashboard에 병렬 실행 정보 표시

### 2. UI 기능 확인

#### A. Structure View 확인
- `Structure` 탭 → `Hierarchy` 탭
- Features → Requirements → Components 트리 확인
- `Graph` 탭에서 컴포넌트 그래프 확인

#### B. Task 관리 확인
- Sidebar의 `MISSION CONTROL`에서 Task Tree 확인
- Task 선택 시 Task Progress View 확인
- Workflow Visualization에서 병렬 실행 확인

#### C. Ground Truth 확인
- Structure View에서 컴포넌트 상태 확인:
  - ✅ Implemented (구현됨)
  - 👻 Ghost (미구현)
  - ⚠️ Drift (불일치)
- Inspector에서 Drift 상세 정보 확인

### 3. 명령어 테스트

#### 사용 가능한 명령어 목록

```bash
# Task 관리
/create_task <name> [description]
/list_tasks
/update_task <task_id> [field=value]
/delete_task <task_id>
/start_task <task_id>

# Sprint 관리
/create_sprint <name> [task_id ...]
/add_task_to_sprint <sprint_id> <task_id> [task_id ...]
/start_sprint <sprint_id>
/approve_sprint <sprint_id>

# Agent 실행
/start_agent <task_id> <agent_type>
/stop_agent <task_id>

# Blueprint 관리
/sync_blueprints
/resolve_conflict <conflict_id>
/apply_blueprint_updates
/apply_code_changes

# Git 관리
/git_status
/git_commit [message]
/git_push
/git_pull

# 기타
/status
/reload
/config
```

---

## 단위 테스트 실행

### 모든 테스트 실행

```bash
# Virtual environment 활성화
source venv/bin/activate

# 모든 테스트 실행
PYTHONPATH=src pytest tests/ -v

# 특정 테스트만 실행
PYTHONPATH=src pytest tests/unit/test_command_handler.py -v

# E2E 테스트만 실행
PYTHONPATH=src pytest tests/e2e/ -v
```

### CI 체크 실행

```bash
# CI와 동일한 체크 실행
PYTHONPATH=src python scripts/check_ci_status.py
```

---

## 실제 사용 시나리오 테스트

### 시나리오 1: PRD 생성 → Task 생성 → 실행

```bash
# 1. 앱 실행
PYTHONPATH=src python -m manifest

# 2. PRD 생성 (일반 텍스트 입력)
"온라인 쇼핑몰을 만들어줘"

# Orchestrator가 질문 시작:
# - "어떤 기능이 필요하신가요?"
# - "사용자 타입은 무엇인가요?"
# - 등등...

# 3. PRD 완성 후 Task 생성 확인
/list_tasks

# 4. Task 실행
/start_task task-xxx

# 5. 진행 상황 확인
# - Sidebar에서 Task 상태 확인
# - Task 선택 시 Progress View 확인
# - Workflow Visualization 확인
```

### 시나리오 2: Sprint로 여러 Task 병렬 실행

```bash
# 1. 여러 Task 생성
/create_task "사용자 인증" "로그인/로그아웃"
/create_task "상품 목록" "상품 조회 기능"
/create_task "장바구니" "장바구니 추가/삭제"

# 2. Sprint 생성
/create_sprint "Phase 1" task-1 task-2 task-3

# 3. Sprint 시작
/start_sprint sprint-xxx

# 4. 병렬 실행 확인
# - Dashboard에서 "⚡ Parallel: X" 확인
# - ContextBar에서 병렬 실행 중인 stage 확인
# - Workflow Visualization에서 "⚡ PARALLEL EXECUTION" 확인
```

### 시나리오 3: Ground Truth 확인

```bash
# 1. Blueprint와 실제 코드 비교
/sync_blueprints

# 2. Drift 확인
# - Structure View에서 컴포넌트 상태 확인
# - Inspector에서 Drift 상세 정보 확인

# 3. Visual Reality 확인
# - Agent가 실행될 때 VisualRealityHook이 자동으로 주입됨
# - Agent 출력에서 "VISUAL REALITY" 섹션 확인 가능
```

---

## 디버깅 팁

### 로그 확인

```bash
# 앱 실행 시 로그 레벨 설정
PYTHONPATH=src python -m manifest --log-level DEBUG

# 또는 환경 변수로
export MANIFEST_LOG_LEVEL=DEBUG
PYTHONPATH=src python -m manifest
```

### 상태 파일 확인

```bash
# State 파일 확인
cat .manifest/state.json | jq

# PRD 확인
cat .manifest/prd.json | jq

# Settings 확인
cat .manifest/settings.json | jq
```

### OpenCode 서버 확인

```bash
# OpenCode 서버 상태 확인
curl http://localhost:4096/global/health

# 또는 브라우저에서
open http://localhost:4096/global/health
```

---

## 문제 해결

### 문제: "ModuleNotFoundError: No module named 'manifest'"

**해결**:
```bash
export PYTHONPATH=src
python -m manifest
```

### 문제: "API key not found"

**해결**:
- 앱 실행 시 BootstrapScreen에서 API 키 입력
- 또는 `.manifest/keys.json` 파일 확인

### 문제: "OpenCode server not running"

**해결**:
- OpenCode 서버가 자동으로 시작됨 (auto_start=True)
- 수동으로 시작하려면:
  ```bash
  opencode serve --port 4096
  ```

### 문제: "Permission denied"

**해결**:
- Permission Approval Widget에서 승인
- 또는 `/config` 명령으로 permission 설정 확인

---

## 빠른 참조

### 실행 명령어
```bash
# 기본 실행
PYTHONPATH=src python -m manifest

# 테스트 실행
PYTHONPATH=src pytest tests/ -v

# CI 체크
PYTHONPATH=src python scripts/check_ci_status.py
```

### 주요 디렉토리
- `.manifest/`: 앱 데이터 및 설정
- `.manifest/keys.json`: 암호화된 API 키
- `.manifest/prd.json`: PRD 문서
- `.manifest/state.json`: 세션 상태
- `.manifest/blueprint.json`: Blueprint 설계
- `.manifest/architecture.json`: Architecture 설계

### 주요 단축키 (TUI)
- `Ctrl+C`: 앱 종료
- `Tab`: 탭 전환
- `Enter`: 명령 실행
- `Esc`: 화면 닫기
