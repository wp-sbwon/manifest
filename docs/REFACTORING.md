# 프로젝트 구조 리팩토링

## 변경 사항

### 새로운 패키지 구조

```
manifest/
├── src/
│   └── manifest/          # 메인 패키지 (src layout)
│       ├── __init__.py
│       ├── __main__.py    # Entry point: python -m manifest
│       ├── core/          # 핵심 모듈
│       │   ├── __init__.py
│       │   ├── config.py
│       │   └── state_manager.py
│       ├── ui/            # UI 모듈
│       │   ├── __init__.py
│       │   ├── app.py
│       │   ├── widgets.py
│       │   └── bootstrap_ui.py
│       ├── agents/        # 에이전트 모듈
│       │   ├── __init__.py
│       │   ├── agent_coordinator.py
│       │   ├── context_provider.py
│       │   └── task_scoper.py
│       ├── bridge/        # 브리지 모듈
│       │   ├── __init__.py
│       │   └── omoc_bridge.py
│       └── audit/         # 감사 모듈
│           ├── __init__.py
│           └── drift_auditor.py
├── tests/                 # 테스트 파일
├── docs/                  # 문서 파일
├── scripts/               # 스크립트 파일
├── pytest.ini             # Pytest 설정
└── .manifest/             # 애플리케이션 데이터
```

### 파일 이동

**Core 모듈:**
- `config.py` → `src/manifest/core/config.py`
- `state_manager.py` → `src/manifest/core/state_manager.py`

**UI 모듈:**
- `app.py` → `src/manifest/ui/app.py`
- `widgets.py` → `src/manifest/ui/widgets.py`
- `bootstrap_ui.py` → `src/manifest/ui/bootstrap_ui.py`

**Agent 모듈:**
- `agent_coordinator.py` → `src/manifest/agents/agent_coordinator.py`
- `context_provider.py` → `src/manifest/agents/context_provider.py`
- `task_scoper.py` → `src/manifest/agents/task_scoper.py`

**Bridge 모듈:**
- `omoc_bridge.py` → `src/manifest/bridge/omoc_bridge.py`

**Audit 모듈:**
- `drift_auditor.py` → `src/manifest/audit/drift_auditor.py`

**문서:**
- `ARCHITECTURE.md` → `docs/ARCHITECTURE.md`
- `PROJECT_STATUS.md` → `docs/PROJECT_STATUS.md`
- `IMPLEMENTATION_SUMMARY.md` → `docs/IMPLEMENTATION_SUMMARY.md`
- `DEV_SETUP.md` → `docs/DEV_SETUP.md`
- `SETUP_GITHUB.md` → `docs/SETUP_GITHUB.md`

**스크립트:**
- `setup.sh` → `scripts/setup.sh`
- `setup-docker.sh` → `scripts/setup-docker.sh`
- `run_tests.sh` → `scripts/run_tests.sh`

## 실행 방법 변경

### 이전
```bash
python app.py
```

### 현재 (src/ layout)
```bash
PYTHONPATH=src python -m manifest
```

또는 개발 환경에서:
```bash
export PYTHONPATH=src
python -m manifest
```

## Import 경로 변경

### 이전
```python
from config import get_config_manager
from state_manager import StateManager
from omoc_bridge import OMOCBridge
```

### 현재
```python
from manifest.core.config import get_config_manager
from manifest.core.state_manager import StateManager
from manifest.bridge.omoc_bridge import OMOCBridge
```

## 업데이트된 파일

- 모든 Python 모듈의 import 문
- 모든 테스트 파일의 import 문
- `Dockerfile` (CMD 업데이트)
- `docker-compose.yml` (command 업데이트)
- `README.md` (실행 방법 및 구조 업데이트)
- `docs/DEV_SETUP.md` (실행 방법 업데이트)

## src/ Layout의 장점

1. **로컬 패키지와 설치된 패키지 분리**: 개발 중인 코드와 설치된 패키지를 명확히 구분
2. **테스트 안정성**: 패키지를 설치해야 테스트 가능하므로 더 정확한 테스트 환경
3. **표준 Python 패키징 관행**: PEP 517/518 권장 구조
4. **명확한 소스 코드 분리**: 소스 코드와 프로젝트 파일의 명확한 구분

## 테스트

모든 import가 정상적으로 작동하는지 확인:
```bash
PYTHONPATH=src python3 -c "from manifest.ui.app import ManifestApp; print('OK')"
```
