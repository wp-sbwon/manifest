# Manifest 프로젝트 자체를 볼 수 있는지 확인

**작성일**: 2026-01-24
**목적**: 현재 manifest 프로젝트 자체의 구조를 UI에서 볼 수 있는지 확인

---

## 📊 현재 데이터 파일 상태

### ✅ 있는 데이터
- **blueprint_code.json**: ✅ **데이터 있음**
  - Components: 약 29개 (코드에서 추출)
  - Contracts: 있음
  - Zones: client, server, data로 분류됨

### ❌ 없는 데이터
- **blueprint.json**: 비어있음 (intended design 없음)
- **architecture.json**: 비어있음 (features 없음)
- **intent.json**: 비어있음 (features 없음)

---

## 🔍 현재 UI 동작 방식

### StructureHierarchyView (Hierarchy 탭)
**현재 로직** (`app.py:1308-1344`):
```python
# Load architecture (비어있음)
architecture_data = load_architecture_with_metadata(architecture_file)

# Load top_down_blueprint (비어있음)
top_down_blueprint = BlueprintLoader.load_blueprint(...)

# Load bottom_up_blueprint (데이터 있음!)
bottom_up_blueprint = BlueprintLoader.load_code_blueprint(...)

# Display: architecture + top_down_blueprint
hierarchy_view.load_data(architecture_data, top_down_blueprint, status_info)
```

**문제점**:
- `top_down_blueprint`가 비어있어서 Component가 표시 안됨
- `architecture_data`가 비어있어서 Feature/Requirement가 표시 안됨
- `bottom_up_blueprint`는 로드하지만 표시에는 사용 안됨

### StructureGraphView (Graph 탭)
**현재 로직**:
```python
# Display: architecture + top_down_blueprint
graph_view.load_data(architecture_data, top_down_blueprint, status_info)
```

**문제점**:
- 마찬가지로 데이터가 비어있어서 표시 안됨

---

## 💡 해결 방법

### 옵션 1: blueprint_code.json을 직접 표시 (권장)
`bottom_up_blueprint` (blueprint_code.json)를 직접 표시하도록 수정

**장점**:
- 즉시 manifest 프로젝트 구조를 볼 수 있음
- 코드에서 추출한 실제 구조 표시

**구현**:
```python
# blueprint_code.json이 있고 blueprint.json이 비어있으면
# blueprint_code.json을 표시
if not top_down_blueprint.get("components"):
    if bottom_up_blueprint.get("components"):
        # Use code blueprint for display
        hierarchy_view.load_data(architecture_data, bottom_up_blueprint, status_info)
```

### 옵션 2: /audit_drift 실행
`/audit_drift` 명령을 실행하면 코드에서 blueprint를 추출하여 `blueprint_code.json`을 업데이트하고, 이를 표시할 수 있음

### 옵션 3: architecture.json 생성
Orchestrator나 Planner를 통해 manifest 프로젝트의 architecture를 생성

---

## 🎯 현재 상태 요약

### 볼 수 있는 것 ✅
- **Task 목록**: TaskTreeView에서 task 확인 가능
- **Agent 상태**: Agent Status 탭에서 활성 agent 확인 가능
- **채널 로그**: 각 agent의 출력 확인 가능

### 볼 수 없는 것 ❌
- **프로젝트 구조**: Component Graph가 비어있음
- **Feature/Requirement**: Architecture가 비어있음
- **Component 관계**: Blueprint가 비어있음

### 볼 수 있게 하려면 🔧
1. **즉시**: `blueprint_code.json`을 직접 표시하도록 코드 수정
2. **또는**: `/audit_drift` 실행하여 코드에서 구조 추출
3. **또는**: Orchestrator로 architecture 생성

---

## 📝 결론

**현재는 manifest 프로젝트 자체의 구조를 UI에서 볼 수 없습니다.**

하지만 `blueprint_code.json`에 데이터가 있으므로, 이를 표시하도록 코드를 수정하면 즉시 볼 수 있습니다.

**권장 사항**: `_load_structure_data()`에서 `blueprint_code.json`을 fallback으로 사용하도록 수정
