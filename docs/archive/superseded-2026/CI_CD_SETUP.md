# CI/CD 설정 가이드

**최종 업데이트**: 2026-01-28
**목적**: GitHub Actions를 사용한 자동화된 테스트 및 배포 설정, CI 실패 감지

---

## 📋 설정된 CI/CD

### 1. GitHub Actions 워크플로우

#### Tests Workflow (`.github/workflows/test.yml`)
- **트리거**: `push` 및 `pull_request` (dev, main 브랜치)
- **Python 버전**: 3.9, 3.10, 3.11 (매트릭스)
- **작업**:
  1. 코드 체크아웃
  2. Python 환경 설정
  3. 의존성 설치
  4. 테스트 실행 (pytest)
  5. 커버리지 리포트 생성
  6. Codecov 업로드 (Python 3.9만)

#### Lint Workflow (`.github/workflows/lint.yml`)
- **트리거**: `push` 및 `pull_request`
- **작업**:
  1. Import 검증
  2. Python 문법 검사

### 2. Pre-commit Hooks (`.pre-commit-config.yaml`)
- **설치 필요**: `pip install pre-commit && pre-commit install`
- **기본 hooks**: whitespace, file endings, YAML/JSON 검증
- **테스트 hook**: Pre-push 시 pytest 빠른 체크 (선택적)

---

## 🚀 사용 방법

### GitHub Actions 자동 실행

**자동으로 실행됨**:
- 코드를 `dev` 또는 `main` 브랜치에 push할 때
- Pull Request를 생성할 때

**확인 방법**:
1. GitHub 저장소 → "Actions" 탭
2. 워크플로우 실행 상태 확인
3. 실패 시 상세 로그 확인

### Pre-commit Hooks 설정

```bash
# Pre-commit 설치
pip install pre-commit

# Hooks 설치
pre-commit install

# Pre-push hook도 설치 (테스트 실행)
pre-commit install --hook-type pre-push

# 수동 실행 (테스트)
pre-commit run --all-files
```

---

## ⚙️ 설정 세부사항

### 테스트 워크플로우

**Python 버전 매트릭스**:
- 3.9, 3.10, 3.11에서 테스트 실행
- 각 버전별로 독립적으로 실행

**커버리지**:
- `pytest-cov`로 커버리지 측정
- XML 리포트 생성 (Codecov용)
- 터미널 리포트 생성

**실패 처리**:
- 테스트 실패 시 워크플로우 실패
- PR 머지 차단 (옵션 설정 가능)

### Lint 워크플로우

**Import 검증**:
- 주요 모듈 import 테스트
- 문법 오류 검사

---

## 🔧 커스터마이징

### 커버리지 임계값 설정

`test.yml`에 추가:
```yaml
- name: Check coverage threshold
  run: |
    pytest --cov=src/manifest --cov-fail-under=50
```

### PR 머지 차단 설정

GitHub 저장소 설정에서:
1. Settings → Branches
2. Branch protection rules
3. "Require status checks to pass before merging" 활성화
4. `test` 워크플로우 선택

### Pre-commit Hook 커스터마이징

`.pre-commit-config.yaml` 수정:
- `always_run: true` - 모든 커밋에서 실행
- `stages: [commit]` - 커밋 시 실행
- `stages: [pre-push]` - Push 시 실행

---

## 📊 결과 확인

### GitHub Actions

1. **Actions 탭**:
   - 워크플로우 실행 히스토리
   - 각 실행의 상세 로그
   - 테스트 결과 요약

2. **Pull Request**:
   - PR 페이지에 테스트 상태 표시
   - ✅ 통과 / ❌ 실패

3. **Codecov** (설정 시):
   - 커버리지 트렌드
   - 커버리지 리포트

---

## ⚠️ 주의사항

### 1. 비밀 정보
- API 키 등은 GitHub Secrets에 저장
- `.env` 파일은 커밋하지 않음

### 2. 테스트 시간
- 매트릭스 테스트는 시간이 걸림
- 필요시 Python 버전 줄이기

### 3. Pre-commit Hook
- 모든 커밋에서 실행하면 느려질 수 있음
- Pre-push만 사용 권장

---

## 🐛 문제 해결

### 테스트 실패 시
1. Actions 탭에서 로그 확인
2. 로컬에서 동일한 환경으로 재현
3. 수정 후 다시 push

### Pre-commit Hook 스킵
```bash
# 특정 커밋만 스킵
git commit --no-verify -m "message"
```

### 워크플로우 수동 실행
GitHub Actions 탭에서 "Run workflow" 버튼 사용

---

## 🔍 CI 실패 감지

### Local CI Checks (`src/manifest/core/ci_monitor.py`)

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

### GitHub Actions Status Checker (`scripts/check_ci_status.py`)

GitHub Actions의 최신 워크플로우 실행 상태를 확인:
- GitHub API를 통해 최신 워크플로우 상태 조회
- 실패 시 상세 정보 및 URL 제공
- `gh` CLI 또는 `GITHUB_TOKEN` 환경 변수 사용

**사용법**:
```bash
# 직접 실행
PYTHONPATH=src python scripts/check_ci_status.py

# 또는
./scripts/check_ci_status.py
```

**요구사항**:
- `gh auth login` 또는 `GITHUB_TOKEN` 환경 변수 설정
- `httpx` 패키지 (이미 requirements.txt에 포함)

### Pre-push Hook Integration

Push 전에 자동으로 CI 체크 실행:

**설정**:
```bash
# Pre-commit hooks 설치
pre-commit install --hook-type pre-push
```

**동작**:
- Push 전에 로컬 CI 체크 실행
- Import 및 Syntax 오류 감지
- CI-equivalent 테스트 실행 (pytest)
- 실패 시 Push 차단 (선택적)

### Cursor Agent Rule (`.cursor/rules/ci-before-commit-push.mdc`)

**목적**: 코딩 에이전트(Cursor AI)가 commit/push **전에 반드시** CI 체크를 실행하도록 강제.

- **규칙 내용**: push 전에 `PYTHONPATH=src python scripts/check_ci_status.py` 를 실행하고, 성공할 때만 push 함.
- **효과**: 에이전트가 푸시하는 코드는 로컬에서 이미 CI와 동일한 테스트를 통과한 상태.

## 📝 다음 단계

1. ✅ GitHub Actions 워크플로우 생성 (완료)
2. ✅ CI 실패 감지 시스템 구현 (완료)
3. ⚠️ Pre-commit hooks 설치 (로컬에서)
4. ⚠️ Branch protection rules 설정 (GitHub에서)
5. ⚠️ Codecov 연동 (선택사항)

---

## 🔗 참고

- [GitHub Actions 문서](https://docs.github.com/en/actions)
- [Pre-commit 문서](https://pre-commit.com/)
- [Pytest 문서](https://docs.pytest.org/)
