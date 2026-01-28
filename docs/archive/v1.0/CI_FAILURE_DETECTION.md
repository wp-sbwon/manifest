# CI Failure Detection

**작성일**: 2026-01-26
**목적**: GitHub Actions CI 실패를 자동으로 감지하고 알림

---

## 개요

Manifest는 이제 GitHub Actions CI 실패를 자동으로 감지할 수 있습니다. Push 전후에 CI 상태를 확인하여 문제를 조기에 발견합니다.

## 구성 요소

### 1. Local CI Checks (`src/manifest/core/ci_monitor.py`)

로컬에서 CI와 동일한 체크를 실행:

- **Import 체크**: 모든 주요 모듈 import 검증
- **Syntax 체크**: Python 문법 오류 검사
- **CI Readiness**: Push 전 코드 준비 상태 확인

**사용법**:
```python
from manifest.core.ci_monitor import verify_ci_readiness

result = verify_ci_readiness()
if result["ready"]:
    print("✅ Ready for CI")
else:
    print("❌ Not ready - fix issues first")
```

### 2. GitHub Actions Status Checker (`scripts/check_ci_status.py`)

GitHub Actions의 최신 워크플로우 실행 상태를 확인:

- GitHub API를 통해 최신 워크플로우 상태 조회
- 실패 시 상세 정보 및 URL 제공
- `gh` CLI 또는 `GITHUB_TOKEN` 환경 변수 사용

**사용법**:
```bash
# 직접 실행
python scripts/check_ci_status.py

# 또는
./scripts/check_ci_status.py
```

**요구사항**:
- `gh auth login` 또는 `GITHUB_TOKEN` 환경 변수 설정
- `httpx` 패키지 (이미 requirements.txt에 포함)

### 3. Pre-push Hook Integration

Push 전에 자동으로 CI 체크 실행:

**설정**:
```bash
# Pre-commit hooks 설치 (이미 설정됨)
pre-commit install --hook-type pre-push
```

**동작**:
- Push 전에 로컬 CI 체크 실행
- Import 및 Syntax 오류 감지
- 실패 시 Push 차단 (선택적)

### 4. Cursor Agent Rule (`.cursor/rules/ci-before-commit-push.mdc`)

**목적**: 코딩 에이전트(Cursor AI)가 commit/push **전에 반드시** CI 체크를 실행하도록 강제.

- **규칙 내용**: push 전에 `PYTHONPATH=src python scripts/check_ci_status.py` 를 실행하고, 성공할 때만 push 함. `git push --no-verify` 로 검사를 건너뛰지 않음.
- **효과**: 에이전트가 푸시하는 코드는 로컬에서 이미 CI와 동일한 테스트를 통과한 상태이므로, "에이전트가 모르는 문제가 사용자에게만 리포팅되는" 상황을 방지.

## CI 실패 감지 방법

### 자동 감지 (Pre-push Hook)

Push 시 자동으로 체크:
```bash
git push origin dev
# → Pre-push hook이 자동 실행
# → CI readiness 체크
# → 실패 시 경고 또는 차단
```

### 수동 확인

```bash
# CI 상태 확인
python scripts/check_ci_status.py

# 또는 CI readiness만 확인
python -c "from manifest.core.ci_monitor import verify_ci_readiness; print(verify_ci_readiness())"
```

## CI 실패 시 동작

### Pre-push Hook

1. **로컬 체크 실패**:
   - Import 오류 감지
   - Syntax 오류 감지
   - Push 차단 (선택적) 또는 경고

2. **원격 CI 실패 감지** (토큰 설정 시):
   - 최신 워크플로우 상태 확인
   - 실패 시 경고 및 URL 제공
   - Push는 계속 진행 (선택적)

### 수동 스크립트

`scripts/check_ci_status.py` 실행 시:
- 로컬 체크 먼저 실행
- 실패 시 즉시 종료 (exit code 1)
- 성공 시 GitHub 상태 확인
- 실패 시 상세 정보 출력

## 설정

### GitHub Token 설정

**방법 1: gh CLI 사용** (권장):
```bash
gh auth login
```

**방법 2: 환경 변수**:
```bash
export GITHUB_TOKEN=your_token_here
```

### Pre-push Hook 활성화

```bash
# Pre-commit 설치 (이미 되어있음)
pip install pre-commit

# Pre-push hook 설치
pre-commit install --hook-type pre-push
```

## 문제 해결

### "GitHub token not found"

해결:
1. `gh auth login` 실행
2. 또는 `GITHUB_TOKEN` 환경 변수 설정

### "Import errors detected"

해결:
1. 로컬에서 import 테스트:
   ```bash
   PYTHONPATH=src python -c "from manifest.ui.app import ManifestApp"
   ```
2. 오류 메시지 확인
3. 순환 import 또는 누락된 의존성 확인

### "CI failed on GitHub"

해결:
1. GitHub Actions 페이지에서 로그 확인
2. 로컬에서 동일한 환경으로 재현:
   ```bash
   PYTHONPATH=src pytest tests/ -v
   ```
3. 수정 후 다시 push

## 향후 개선

1. **자동 알림**: CI 실패 시 자동으로 알림 (이메일, 슬랙 등)
2. **상세 리포트**: 실패한 테스트 목록 및 원인 분석
3. **자동 재시도**: 일시적 실패 시 자동 재시도
4. **CI 상태 대시보드**: 로컬에서 CI 상태 시각화

---

## 참고

- [GitHub Actions API](https://docs.github.com/en/rest/actions)
- [Pre-commit Hooks](https://pre-commit.com/)
