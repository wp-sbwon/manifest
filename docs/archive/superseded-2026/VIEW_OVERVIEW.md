# Manifest View 정리

상시 시각화 전용 UI (MVP). 채팅은 OpenCode, 시각화만 이 View에서 표시.

---

## 1. 패키지 구조

```
src/manifest/view/
├── __init__.py   # ManifestViewApp export
└── app.py        # ManifestViewApp, run_view()
```

- **`__init__.py`**: `ManifestViewApp`만 export.
- **`app.py`**: Textual 앱 한 개 + `run_view()` 진입점.

---

## 2. 파일별 역할

| 파일 | 내용 |
|------|------|
| **`view/__init__.py`** | `from manifest.view.app import ManifestViewApp` / `__all__ = ["ManifestViewApp"]` |
| **`view/app.py`** | `ManifestViewApp`: 상시 시각화 전용 Textual 앱 (채팅/입력 없음). `run_view(manifest_dir)`로 실행. |

---

## 3. ManifestViewApp 동작

- **표시**: blueprint(컴포넌트·구현 상태), tasks(태스크 목록), drift(요약 문구만).
- **데이터 소스**: `BlueprintLoader`, `BlueprintSynchronizer`, `StateManager`, `load_architecture_with_metadata`.
- **갱신**: 마운트 시 1회 + 30초마다 `refresh_view()`.
- **단축키**: `r` Refresh, `q` Quit.
- **스타일**: 다크 테마 (`#0d1117`, `#161b22`).

---

## 4. 실행 방법

| 방법 | 명령 |
|------|------|
| **manifest 실행 시 자동** | `manifest` 또는 `python -m manifest` → launcher가 View를 subprocess로 띄운 뒤 OpenCode 실행 |
| **View만 단독 실행** | `PYTHONPATH=src python -m manifest.view.app [--manifest-dir PATH]` |
| **코드에서** | `from manifest.view import ManifestViewApp` 또는 `from manifest.view.app import run_view` 후 `run_view(manifest_dir)` |

---

## 5. 사용처

| 위치 | 용도 |
|------|------|
| **launcher.py** | `_start_view()`에서 `python -m manifest.view.app --manifest-dir <path>` subprocess 실행 |
| **ci_monitor.py** | `check_imports()`에서 `manifest.view.app.ManifestViewApp` import 검사 |
| **ui/__init__.py** | 주석으로 "시각화는 manifest.view (ManifestViewApp) 사용" 안내 |
| **tests/unit/test_view.py** | ManifestViewApp 인스턴스 생성, `_load_view_data()`, `compose` 검증 |
| **tests/unit/test_launcher.py** | `_start_view()` 호출 시 `manifest.view.app` 인자 검증 |

---

## 6. 원래 TUI 기능 목록 vs 현재 View 상태

### 원래 TUI에 있던 뷰들 (5-View Workspace)

| 뷰 | 설명 | 데이터 소스 | 현재 View 상태 |
|----|------|-------------|----------------|
| **Architect View** | 의도/요구사항 표시 | `intent.json`, `architecture.json` (features/requirements) | ❌ 없음 |
| **Blueprint View** | 아키텍처 계층/그래프 표시 | `blueprint.json`, `architecture.json` | ⚠️ 부분만 (컴포넌트 목록만) |
| **History View** | Git 히스토리 표시 | `GitManager.get_latest_commits()` | ❌ 없음 (사라짐) |
| **Inspector View** | 3 모드: Visual, Data, Drift | `BlueprintSynchronizer`, `DriftAuditor` | ⚠️ 부분만 (drift 요약만) |
| **Mission Control Sidebar** | TaskTree, SprintStatus | `StateManager`, `TaskManager`, `SprintManager` | ⚠️ 부분만 (tasks 목록만) |

### 원래 TUI에 있던 위젯들

| 위젯 | 설명 | 현재 View 상태 |
|------|------|----------------|
| **StructureHierarchyView** | Architecture/Blueprint 계층 구조 표시 | ❌ 없음 |
| **StructureGraphView** | Blueprint 그래프 시각화 | ❌ 없음 |
| **RequirementMap** | 기능 의존성 시각화 | ❌ 없음 |
| **ArchitectureGraph** | 노드-엣지 그래프 | ❌ 없음 |
| **TaskTreeView** | Task 트리 표시 | ⚠️ 부분만 (리스트만) |
| **SprintStatusView** | Sprint 상태 표시 | ❌ 없음 |
| **HistoryView** | Git commits 표시 | ❌ 없음 (사라짐) |
| **FeatureTree** | AST 인식 코드 네비게이션 | ❌ 없음 |
| **TaskProgressView** | Worker Squad stages, git diff 표시 | ❌ 없음 |
| **AgentStatusView** | Agent 상태 표시 | ❌ 없음 |

### 현재 View에 있는 것

- ✅ **blueprint**: 컴포넌트 목록과 구현 상태 (간단한 텍스트)
- ✅ **tasks**: 태스크 목록 (간단한 텍스트)
- ⚠️ **drift**: 요약 문구만 ("use audit/ for details; MVP summary only")

### 누락된 주요 기능

1. **History View** (Git 히스토리) - `GitManager.get_latest_commits()` 사용하여 Git commits 표시
2. **Architect View** - intent.json의 features/requirements 표시
3. **Blueprint View** - 구조 계층/그래프 시각화 (StructureHierarchyView, StructureGraphView)
4. **Inspector View** - Drift 상세 정보 (Visual, Data 모드)
5. **Mission Control** - TaskTree, SprintStatus 위젯
6. **위젯들** - RequirementMap, ArchitectureGraph, FeatureTree, TaskProgressView 등

---

## 7. 추후 (Electron)

- MVP는 Textual 기반.
- 계획: 나중에 Electron 앱으로 전환하여 원래 TUI에 있던 모든 기능(Architect, Blueprint, History, Inspector, Mission Control + 모든 위젯들) 표시.
