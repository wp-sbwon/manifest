# Manifest 프로젝트 테스트 현황

**최종 업데이트**: 2026-01-24
**리뷰 목적**: 현재 테스트 구조, 커버리지, 문제점 파악

---

## 📊 테스트 구조 개요

### 테스트 디렉토리 구조

```
tests/
├── __init__.py
├── unit/                    # 단위 테스트 (13개 파일)
│   ├── test_agent_coordinator.py
│   ├── test_agent_executor.py
│   ├── test_blueprint_comparator.py
│   ├── test_code_extractor.py
│   ├── test_container_manager.py
│   ├── test_context_provider.py
│   ├── test_drift_auditor.py
│   ├── test_opencode_adapter.py
│   ├── test_settings_manager.py
│   ├── test_skills_manager.py
│   ├── test_state_manager.py
│   ├── test_task_scoper.py
│   └── test_terminal_router.py
├── integration/              # 통합 테스트 (5개 파일)
│   ├── test_agent_bridge.py
│   ├── test_agent_integration.py
│   ├── test_app.py
│   ├── test_app_input.py
│   └── test_blueprint_synchronizer.py
└── e2e/                      # E2E 테스트 (빈 디렉토리)
    └── __init__.py
```

**총 테스트 파일**: 22개 (unit: 13, integration: 5, e2e: 0)

---

## 🔧 테스트 설정

### pytest 설정

**파일**: `pytest.ini`, `pyproject.toml`

```ini
[pytest]
pythonpath = src
testpaths = tests/unit tests/integration tests/e2e
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

### 테스트 실행 스크립트

**파일**: `scripts/run_tests.sh`

```bash
PYTHONPATH=src pytest tests/ -v
```

### 의존성

- `pytest>=7.4.0`
- `pytest-asyncio>=0.21.0` (비동기 테스트 지원)

---

## ⚠️ 현재 문제점

### 1. 테스트 실패 (6개)

다음 테스트들이 실패:

1. `test_agent_coordinator.py::test_start_worker_agent` - TypeError: 'Mock' object is not iterable
2. `test_agent_coordinator.py::test_stop_agent` - TypeError: 'Mock' object is not iterable
3. `test_agent_executor.py::test_execute_agent_anthropic_mock` - AssertionError (API 호출 시그니처 변경)
4. `test_agent_executor.py::test_execute_agent_api_error` - AssertionError (에러 메시지 불일치)
5. `test_agent_executor.py::test_prepare_messages` - AssertionError (메시지 포맷 변경)
6. `test_agent_executor.py::test_execute_agent_with_message_history` - AssertionError (Mock 호출 확인 실패)

**원인**:
- AgentExecutor API 시그니처 변경으로 인한 Mock 불일치
- AgentCoordinator Mock 설정 문제

### 2. pytest-asyncio 마크 경고

```
PytestUnknownMarkWarning: Unknown pytest.mark.asyncio
```

**위치**: `test_terminal_router.py` (5개 테스트)

**원인**: pytest-asyncio 플러그인이 제대로 등록되지 않음

**해결 방법**:
```python
# pytest.ini 또는 conftest.py에 추가
[pytest]
asyncio_mode = auto
```

### 3. Import 에러 (5개)

다음 테스트들이 Import 에러 발생:

- `test_app_input.py` (5개 테스트 모두)
  - 에러: `ModuleNotFoundError: No module named 'manifest.ui.widgets.structure_hierarchy_view'`
  - 원인: `manifest.ui.widgets`가 패키지가 아닌 모듈인데, 서브모듈을 import하려고 시도

### 4. E2E 테스트 부재

- `tests/e2e/` 디렉토리가 비어있음
- E2E 테스트 파일 없음

---

## ✅ 정상 작동하는 테스트

다음 테스트들은 정상적으로 수집됨:

### Unit Tests (7개 파일)
- ✅ `test_blueprint_comparator.py` (9개 테스트)
- ✅ `test_code_extractor.py` (7개 테스트)
- ✅ `test_drift_auditor.py` (6개 테스트)
- ✅ `test_opencode_adapter.py` (10개 테스트)
- ✅ `test_skills_manager.py` (8개 테스트)
- ✅ `test_task_scoper.py`
- ✅ `test_terminal_router.py` (경고 있음)

### Integration Tests (5개 파일)
- ✅ `test_agent_bridge.py`
- ✅ `test_agent_integration.py`
- ✅ `test_app.py` (4개 테스트)
- ✅ `test_app_input.py`
- ✅ `test_blueprint_synchronizer.py` (13개 테스트)

**예상 테스트 수**: 약 50-60개 (정상 수집되는 것만)

---

## 📈 테스트 커버리지

### 실제 커버리지 측정 결과

**측정일**: 2026-01-24
**도구**: pytest-cov

```
전체 커버리지:    24%  (매우 낮음)
총 라인 수:       10,489
커버된 라인:      2,529
미커버 라인:      7,960
```

**모듈별 커버리지**:
- Core 모듈: 24-80% (불균형)
- UI 모듈: 0-33% (매우 낮음)
  - `app.py`: 1% (1,324 라인 중 11 라인만)
  - `channel_manager.py`: 0%
  - `command_handler.py`: 0%
  - `settings_screen.py`: 0%
- Agent 모듈: 8-44% (낮음)
- Runtime 모듈: 0-81% (불균형)

### 문서화된 커버리지 vs 실제

**문서화된 값** (부정확):
- Core modules: 80%
- UI modules: 60%
- Overall: 70%

**실제 측정값**:
- Overall: **24%** (문서와 큰 차이)

**결론**: 문서화된 커버리지는 오래된 값이며, 실제로는 매우 낮은 상태입니다.

---

## 🎯 테스트 커버리지 목표

### 현재 상태
- **Core 모듈**: 80% (목표 달성)
- **UI 모듈**: 60% (목표 미달)
- **전체**: 70% (목표 미달)

### 목표
- **전체 커버리지**: >80%
- **UI 모듈**: >70%
- **Core 모듈**: 유지 (80%+)

### 우선순위
1. **High**: 테스트 수집 에러 수정
2. **High**: pytest-asyncio 설정 수정
3. **Medium**: UI 모듈 테스트 추가
4. **Medium**: E2E 테스트 추가
5. **Low**: 커버리지 리포트 자동화

---

## 📋 테스트되지 않은 모듈

### UI 모듈 (낮은 커버리지)
- `manifest.ui.app` - ManifestApp (메인 앱)
- `manifest.ui.widgets` - Custom widgets
- `manifest.ui.widgets.*` - 개별 위젯들
- `manifest.ui.channels` - Channel Manager
- `manifest.ui.commands` - Command Handler

### Agent 모듈
- `manifest.agents.worker_squad_executor` - Worker Squad 실행
- `manifest.agents.sprint_executor` - Sprint 실행
- `manifest.agents.failure_recovery` - 실패 복구
- `manifest.agents.resource_monitor` - 리소스 모니터링

### Runtime 모듈
- `manifest.runtime.hooks` - Prompt hooks
- `manifest.runtime.permissions` - Permission 관리
- `manifest.runtime.tools` - Tool 시스템

---

## 🔍 테스트 품질 평가

### 강점 ✅
1. **구조화된 테스트 디렉토리**: unit/integration/e2e 분리
2. **pytest 설정**: 적절한 설정 파일 존재
3. **Fixture 사용**: temp_dir, state_manager 등 재사용 가능한 fixture
4. **비동기 테스트 지원**: pytest-asyncio 사용

### 약점 ⚠️
1. **테스트 수집 실패**: 6개 파일 에러
2. **E2E 테스트 부재**: End-to-end 테스트 없음
3. **UI 테스트 부족**: UI 모듈 테스트 거의 없음
4. **커버리지 측정 부재**: 자동화된 커버리지 리포트 없음
5. **CI/CD 부재**: 자동화된 테스트 실행 없음

---

## 🛠️ 권장 개선 사항

### 즉시 수정 필요 (High Priority)

1. **테스트 수집 에러 수정**
   ```bash
   # 각 에러 파일 확인 및 수정
   python -m pytest tests/unit/test_state_manager.py -v
   ```

2. **pytest-asyncio 설정 추가**
   ```ini
   # pytest.ini 또는 conftest.py
   [pytest]
   asyncio_mode = auto
   ```

3. **conftest.py 생성**
   ```python
   # tests/conftest.py
   import pytest
   pytest_plugins = ['pytest_asyncio']
   ```

### 단기 개선 (Medium Priority)

4. **커버리지 측정 도구 추가**
   ```bash
   pip install pytest-cov
   ```

5. **UI 테스트 추가**
   - Textual 앱 테스트
   - Widget 테스트
   - Integration 테스트

6. **E2E 테스트 추가**
   - 전체 워크플로우 테스트
   - Agent 통합 테스트

### 장기 개선 (Low Priority)

7. **CI/CD 설정**
   - GitHub Actions
   - 자동 테스트 실행
   - 커버리지 리포트

8. **테스트 문서화**
   - 테스트 전략 문서
   - 테스트 가이드라인

---

## 📝 테스트 실행 방법

### 전체 테스트 실행
```bash
PYTHONPATH=src pytest tests/ -v
```

### 특정 카테고리만 실행
```bash
# Unit tests only
PYTHONPATH=src pytest tests/unit/ -v

# Integration tests only
PYTHONPATH=src pytest tests/integration/ -v
```

### 커버리지 포함 실행
```bash
PYTHONPATH=src pytest tests/ --cov=src/manifest --cov-report=term-missing
```

### 특정 파일만 실행
```bash
PYTHONPATH=src pytest tests/unit/test_state_manager.py -v
```

---

## 📊 테스트 통계 요약

| 항목 | 수치 |
|------|------|
| 총 테스트 파일 | 22개 |
| Unit 테스트 | 13개 파일 |
| Integration 테스트 | 5개 파일 |
| E2E 테스트 | 0개 파일 |
| **실제 테스트 수** | **125개** |
| **통과한 테스트** | **114개 (91.2%)** |
| **실패한 테스트** | **6개** |
| **에러 발생** | **5개** |
| **실제 커버리지** | **24%** (매우 낮음) |
| 문서화된 커버리지 | 70% (부정확) |
| 목표 커버리지 | >80% |

---

## 🔄 다음 단계

1. **즉시**: 테스트 수집 에러 수정
2. **즉시**: pytest-asyncio 설정 수정
3. **단기**: 커버리지 측정 및 리포트 생성
4. **단기**: UI 테스트 추가
5. **중기**: E2E 테스트 추가
6. **장기**: CI/CD 설정

---

## 📚 참고 문서

- [CONTRIBUTING.md](./CONTRIBUTING.md) - 테스트 작성 가이드
- [PROJECT_STATUS.md](./PROJECT_STATUS.md) - 프로젝트 상태
- [NEXT_STEPS.md](./NEXT_STEPS.md) - 다음 단계
