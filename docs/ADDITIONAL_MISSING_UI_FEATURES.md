# 추가 누락된 UI 기능

**작성일**: 2026-01-24  
**기준**: `INTEGRATED_VIEW_UX_DESIGN.md`에 계획된 기능 vs 실제 구현

---

## 🔴 Critical - 문서에 계획된 탭 누락

### 1. Task Progress 탭 미구현
**문서**: `INTEGRATED_VIEW_UX_DESIGN.md:140-145`

**계획된 기능**:
- 선택된 task의 상세 진행상황:
  - Worker Squad stages 진행률
  - 각 stage 상태
  - 수정된 파일 목록 (task와 연계)
  - Git diff 링크

**현재 상태**:
- ✅ `tab-task-progress` 탭 구현됨 (`app.py:419-422`)
- ✅ `TaskProgressView` 위젯 구현됨 (`widgets/task_progress_view.py`)
- ✅ Worker Squad stages 진행률 표시
- ✅ 수정된 파일 목록 표시
- ✅ Git diff 표시 (TaskManager 연동)
- ✅ Task 선택 시 자동 업데이트 (`app.py:2073-2079`)

**위치**: `src/manifest/ui/app.py:392-427` (design-tabs)

---

### 2. Agent Channels 탭 미구현
**문서**: `INTEGRATED_VIEW_UX_DESIGN.md:147-150`

**계획된 기능**:
- 채널 선택 버튼
- 선택된 채널의 로그 출력
- 실시간 스트리밍

**현재 상태**:
- ✅ `tab-agent-channels` 탭 구현됨 (`app.py:424-426`)
- ✅ `AgentChannelsView` 위젯 구현됨 (`widgets/agent_channels_view.py`)
- ✅ 채널 선택 버튼 동적 생성 및 클릭 핸들러 구현
- ✅ 선택된 채널의 로그 출력 및 실시간 업데이트
- ✅ Channel Manager와 연동하여 채널 목록 자동 업데이트

**위치**: `src/manifest/ui/app.py:392-426` (design-tabs)

---

## 🟡 High Priority - 기능 누락

### 3. Task 선택 시 관련 파일/컴포넌트 자동 하이라이트
**문서**: `INTEGRATED_VIEW_UX_DESIGN.md:156-159`

**계획된 기능**:
- 파일/디렉토리 옆에 관련 task 표시 ✅ (구현됨)
- 컴포넌트 그래프에서 task 진행상황 하이라이트 ⚠️ (부분 구현 - 하이라이트는 Hierarchy View에만)
- **Task 선택 시 관련 파일/컴포넌트 자동 하이라이트** ✅ (구현됨)

**현재 상태**:
- ✅ 파일 노드에 task 표시됨
- ✅ Task 선택 시 Structure Hierarchy View에서 관련 파일/컴포넌트를 ⭐ 마커로 하이라이트 (`app.py:2081-2087`)
- ✅ `highlight_task_files_and_components()` 메서드로 task scope, worker squad stages, tool_execution에서 파일/컴포넌트 수집
- ✅ 하이라이트된 항목은 ⭐ 마커로 표시됨 (`structure_hierarchy_view.py:147, 192`)

---

### 4. 리소스 사용량 그래프
**문서**: `INTEGRATED_VIEW_UX_DESIGN.md:138, 162-164`

**계획된 기능**:
- Agent Status 탭에 리소스 사용량 그래프 (선택적)
- CPU, 메모리 사용량 시각화

**현재 상태**:
- ✅ CPU, 메모리 사용량은 텍스트로 표시됨
- ✅ ASCII 바 차트로 그래프 형태 표시됨 (`agent_status_view.py`)
- ✅ `_create_bar_chart()` 메서드로 CPU와 메모리 사용량을 시각화
- ✅ 색상 코딩 (green < 50%, yellow < 80%, red >= 80%)

---

## 🟠 Medium Priority - 향후 개선

### 5. 패널 크기 조절
**문서**: `INTEGRATED_VIEW_UX_DESIGN.md:173`

**계획된 기능**:
- 각 패널 크기 조절 가능

**현재 상태**:
- ❌ 패널 크기 조절 기능 없음
- CSS로 고정 크기

---

### 6. 패널 표시/숨김 토글
**문서**: `INTEGRATED_VIEW_UX_DESIGN.md:174`

**계획된 기능**:
- 필요한 패널만 표시 가능

**현재 상태**:
- ❌ 패널 표시/숨김 토글 없음

---

## 📊 현재 탭 구조 vs 계획된 탭 구조

### 현재 구현된 탭
1. ✅ Structure (Hierarchy + Graph)
2. ✅ Project (Tasks + History)
3. ✅ Agent Status
4. ✅ **Task Progress** - Worker Squad stages, 수정된 파일 목록, Git diff
5. ✅ **Agent Channels** - 채널 선택, 로그 출력, 실시간 스트리밍

---

## 📋 우선순위별 요약

### ✅ 완료된 기능 (Critical & High)
1. ✅ **Task Progress 탭 추가** - Worker Squad 진행률, 수정된 파일 목록, Git diff
2. ✅ **Agent Channels 탭 추가** - 채널 선택 및 로그 출력, 실시간 업데이트
3. ✅ **Task 선택 시 관련 파일/컴포넌트 하이라이트** - ⭐ 마커로 시각적 표시
4. ✅ **리소스 사용량 그래프** - ASCII 바 차트로 CPU/메모리 시각화

### 중간 우선순위 (Medium)
5. **패널 크기 조절** - 사용자 커스터마이징
6. **패널 표시/숨김 토글** - UI 정리

---

## 💡 참고사항

- `WorkerSquadProgress` 위젯은 이미 구현되어 있음 (`widgets.py:263`)
- Channel Manager는 이미 구현되어 있음 (`channels/channel_manager.py`)
- 이 기능들을 탭으로 통합하면 됨
