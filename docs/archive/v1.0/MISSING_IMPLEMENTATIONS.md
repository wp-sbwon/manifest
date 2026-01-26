# 누락된 구현 사항 정리

**작성일**: 2026-01-24
**목적**: 문서에 계획되어 있거나 코드에 준비되어 있지만 실제로 구현되지 않은 기능들 정리

---

## 🔴 Critical - 메시지 핸들러 누락

### 1. ComponentSelected 핸들러 미구현
**위치**: `src/manifest/ui/app.py`

**상태**:
- ✅ `ComponentSelected` 메시지 클래스 정의됨 (`structure_hierarchy_view.py:345`)
- ✅ Component 선택 시 메시지 발송됨 (`structure_hierarchy_view.py:342`)
- ❌ `@on(ComponentSelected)` 핸들러가 `app.py`에 없음

**영향**:
- Component 선택 시 Inspector에 상세 정보가 표시되지 않음
- 사용자가 Component의 상세 정보를 볼 수 없음

**참고**: `TaskSelected`는 핸들러가 구현되어 있음 (`app.py:1756`)

---

## 🟡 High Priority - 계층 정보 표시 누락

### 2. Contract 정보가 Hierarchy View에 없음
**위치**: `src/manifest/ui/widgets/structure_hierarchy_view.py`

**상태**:
- ✅ Contract 데이터는 blueprint에 있음
- ✅ Graph View에는 일부 Contract 표시됨 (인접 컴포넌트만)
- ❌ Hierarchy View 트리에 Contract 노드가 없음

**계획된 기능** (`COMPONENT_GRAPH_IMPROVEMENT_PROPOSAL.md:106-115`):
```
Contracts [▼ Expand]
  → UserModel (dependency)
    Type: call
    Symbols: login() → UserModel.get()
    📁 src/auth/service.py:45
```

**현재 상태**:
- Component 노드 아래에 Methods, Attributes는 있음
- Contracts는 없음

---

### 3. Component Inspector 상세 정보 표시 미구현
**위치**: `src/manifest/ui/app.py`

**상태**:
- ✅ `_update_task_inspector()` 메서드 존재 (Task용)
- ❌ `_update_component_inspector()` 메서드 없음

**계획된 기능** (`COMPONENT_GRAPH_IMPROVEMENT_PROPOSAL.md:196-248`):
- Component 기본 정보 (Type, Status, File, Module, Zone)
- Metadata (Algorithm, Design Pattern, Complexity)
- Methods 전체 목록 (signature 포함)
- Attributes 전체 목록
- Contracts (Outgoing/Incoming)
- Related Tasks

**현재 상태**:
- Task 선택 시 Inspector 업데이트됨
- Component 선택 시 Inspector 업데이트 안 됨

---

## 🟠 Medium Priority - 기능 미활용

### 4. _find_tasks_for_file 메서드 미사용
**위치**: `src/manifest/ui/widgets/structure_hierarchy_view.py:244`

**상태**:
- ✅ `_find_tasks_for_file()` 메서드 구현됨
- ✅ 파일과 task 연관 관계 찾는 로직 있음
- ❌ 실제로 파일 노드에 task 정보를 표시하지 않음

**계획된 기능** (`INTEGRATED_VIEW_UX_DESIGN.md:27-28`):
```
├─ manifest/ [task-1] ⚡
│  ├─ ui/ [task-2] ✅
```

**현재 상태**:
- 파일 노드는 표시되지만 관련 task 정보 없음
- 메서드는 있지만 호출되지 않음

---

### 5. Graph View에서 Component 선택 기능 없음
**위치**: `src/manifest/ui/widgets/structure_graph_view.py`

**상태**:
- ✅ Graph View에 Component 표시됨
- ✅ Contract 정보 일부 표시됨
- ❌ Component 클릭/선택 기능 없음
- ❌ 선택 시 Inspector 업데이트 없음

**계획된 기능**:
- Component 클릭 시 상세 정보 표시
- Inspector 연동

**현재 상태**:
- Static 위젯이라 클릭 이벤트 처리 안 됨
- 선택 기능 없음

---

## 📋 문서에 계획된 기능 vs 실제 구현

### Phase 1 (필수) - 부분 구현
**문서**: `COMPONENT_GRAPH_IMPROVEMENT_PROPOSAL.md:321-324`

1. ✅ Methods/Attributes 전체 목록 표시 (expandable) - **구현됨**
2. ✅ Component Type 표시 - **구현됨**
3. ✅ Module Path 표시 - **구현됨**

### Phase 2 (중요) - 미구현
**문서**: `COMPONENT_GRAPH_IMPROVEMENT_PROPOSAL.md:326-328`

1. ❌ Contract 상세 정보 (symbols, file) - **미구현**
   - Graph View에 일부만 표시
   - Hierarchy View에 없음

2. ❌ Inspector 연동 (Component 선택 시 상세 표시) - **미구현**
   - ComponentSelected 핸들러 없음
   - Inspector 업데이트 메서드 없음

### Phase 3 (개선) - 부분 구현
**문서**: `COMPONENT_GRAPH_IMPROVEMENT_PROPOSAL.md:330-333`

1. ⚠️ Graph View 관계 그래프 - **부분 구현**
   - Feature별 그룹화만 됨
   - 전체 관계 그래프 없음

2. ⚠️ Contract 방향성 시각화 - **부분 구현**
   - 인접 컴포넌트만 표시
   - 전체 관계 시각화 없음

3. ❌ Zone별 색상 구분 - **미구현**

---

## 🔍 코드 분석 결과

### Message 클래스와 핸들러 매칭

| Message 클래스 | 발송 위치 | 핸들러 위치 | 상태 |
|---------------|----------|-----------|------|
| `ComponentSelected` | `structure_hierarchy_view.py:342` | 없음 | ❌ 미구현 |
| `TaskSelected` | `project_view.py:242` | `app.py:1756` | ✅ 구현됨 |
| `SprintSelected` | `project_view.py:328` | `app.py:1799` | ✅ 구현됨 |

### 준비된 메서드 미사용

| 메서드 | 위치 | 용도 | 사용 여부 |
|--------|------|------|----------|
| `_find_tasks_for_file()` | `structure_hierarchy_view.py:244` | 파일-태스크 연관 찾기 | ❌ 미사용 |
| `_update_task_inspector()` | `app.py:816` | Task Inspector 업데이트 | ✅ 사용됨 |
| `_update_component_inspector()` | 없음 | Component Inspector 업데이트 | ❌ 없음 |

---

## 📊 우선순위별 요약

### 즉시 구현 필요 (Critical)
1. **ComponentSelected 핸들러 추가** - Component 선택 기능 완성
2. **Component Inspector 업데이트 메서드** - 상세 정보 표시

### 높은 우선순위 (High)
3. **Contract 정보를 Hierarchy View에 추가** - 계층 정보 완성
4. **파일 노드에 관련 Task 표시** - `_find_tasks_for_file()` 활용

### 중간 우선순위 (Medium)
5. **Graph View Component 선택 기능** - 클릭 이벤트 처리
6. **Contract 상세 정보 표시** - symbols, file 위치 등

---

## 💡 구현 시 참고사항

### 1. Component Inspector 구현 시 포함할 정보
- Component 기본 정보 (id, name, type, status, file, line, module_path)
- Metadata (algorithm, design_pattern, complexity, notes)
- Methods 전체 목록 (expandable)
- Attributes 전체 목록 (expandable)
- Contracts (outgoing/incoming) - blueprint에서 가져오기
- Related Tasks - `_find_tasks_for_file()` 활용

### 2. Contract 정보 추가 시
- Component 노드 아래에 "Contracts [▶]" 노드 추가
- Outgoing Contracts와 Incoming Contracts 구분
- 각 Contract에 type, symbols, file 정보 표시
- Expandable로 구현

### 3. Task 연계 표시 시
- 파일 노드 옆에 task 아이콘과 ID 표시
- 예: `📁 src/manifest/ui/app.py:100 ⚡ [task-1]`
- `_find_tasks_for_file()` 메서드 활용

---

## 📝 참고 문서

- `docs/COMPONENT_GRAPH_IMPROVEMENT_PROPOSAL.md` - 계획된 개선사항
- `docs/INTEGRATED_VIEW_UX_DESIGN.md` - 통합 뷰 디자인
- `docs/CURRENT_VISIBILITY_STATUS.md` - 현재 가시성 상태
- `docs/REMAINING_FEATURES.md` - 남은 기능들
