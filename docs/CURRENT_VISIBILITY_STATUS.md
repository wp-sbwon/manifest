# 현재 구조의 가시성 및 현황 파악 기능 분석

**작성일**: 2026-01-24  
**목적**: 여러 agent 프로세스와 task 진행상황을 한눈에 보고 현황을 파악할 수 있는지 평가

---

## ✅ 현재 구현된 기능

### 1. **Dashboard Header (상단 헤더)**
**위치**: `app.py:64-91`, `update_dashboard_metrics()`

**표시 내용**:
- Architecture Match % (설계-코드 일치율)
- Tasks: 완료/전체
- Active Agents: 현재 실행 중인 agent 수

**업데이트 주기**: 5초마다 자동 업데이트 (`set_interval(5.0)`)

**장점**:
- 프로젝트 전체 건강 상태를 한눈에 파악 가능
- 실시간으로 업데이트됨

**제한사항**:
- 각 agent의 상세 상태는 표시되지 않음
- Task별 진행률은 요약만 표시

---

### 2. **Context Bar (컨텍스트 바)**
**위치**: `app.py:94-137`, `update_context_bar()`

**표시 내용**:
- 현재 활성화된 agent들의 활동 (최대 3개)
- 각 agent의 task_id, agent_type, 현재 stage

**예시**: `coder on task-123: planner | test on task-456: in_progress`

**장점**:
- 실시간 agent 활동 추적
- 어떤 agent가 어떤 task에서 무엇을 하고 있는지 표시

**제한사항**:
- 최대 3개만 표시 (여러 agent 동시 실행 시 일부만 보임)
- 상세 정보는 별도 채널로 이동해야 확인 가능

---

### 3. **TaskTreeView (사이드바 Task 트리)**
**위치**: `widgets/project_view.py:95-256`

**표시 내용**:
- Sprint별로 그룹화된 Task 목록
- Task 상태 아이콘 (⏳ pending, ⚡ in_progress, ✅ done, 🚫 blocked)
- Task별 진행률 % (Worker Squad stages 기반)
- Worker Squad stages 상세 표시 (planner, coder, test, debug 등)

**기능**:
- 필터링 (상태별)
- 검색 (task_id, name, description)
- Task 선택 시 상세 정보 표시

**장점**:
- 모든 task의 상태를 한눈에 파악 가능
- 진행률과 stage 정보 제공
- 필터링으로 원하는 task만 볼 수 있음

**제한사항**:
- 실시간 자동 업데이트가 보장되지 않음 (수동 새로고침 필요할 수 있음)
- 프로젝트 구조와의 연계가 시각적으로 부족

---

### 4. **Channel Manager (채널 관리)**
**위치**: `channels/channel_manager.py`

**기능**:
- 각 agent의 출력을 채널별로 분리
- 채널 버튼으로 전환 가능
- 실시간 스트리밍 지원

**장점**:
- 여러 agent 동시 실행 시 출력이 섞이지 않음
- 각 agent의 로그를 독립적으로 확인 가능

**제한사항**:
- 채널이 많아지면 버튼이 많아져 UI가 복잡해질 수 있음

---

### 5. **Inspector (인스펙터)**
**위치**: `app.py:797-894`, `_update_task_inspector()`

**표시 내용**:
- 선택된 Task의 상세 정보
- Worker Squad Logs (각 stage의 출력)
- Git Diff (변경사항)

**장점**:
- Task 선택 시 모든 관련 정보를 한 화면에 표시
- Agent 로그와 코드 변경사항을 함께 확인 가능

**제한사항**:
- 한 번에 하나의 task만 상세 확인 가능
- 프로젝트 구조와의 연계가 텍스트 기반

---

## ⚠️ 부족한 부분

### 1. **통합 대시보드 뷰**
**문제**: 
- 프로젝트 구조와 task 진행상황을 한 화면에 통합한 뷰가 없음
- Architecture Match, Task 진행률, Agent 상태가 각각 다른 위치에 분산

**필요 기능**:
- 프로젝트 구조 그래프에 task 진행상황 오버레이
- 컴포넌트별로 어떤 task가 진행 중인지 표시

---

### 2. **Agent 프로세스 상세 상태**
**문제**:
- Dashboard Header에는 agent 수만 표시
- 각 agent의 CPU/메모리 사용량, 실행 시간 등 상세 정보가 없음

**현재 상태**:
- `agent_coordinator.get_agent_status()`는 구현되어 있으나 UI에 표시되지 않음
- Container 모드에서는 CPU/메모리 정보를 가져올 수 있음

**필요 기능**:
- Agent 목록 위젯 (각 agent의 상세 상태 표시)
- 리소스 사용량 모니터링

---

### 3. **실시간 업데이트 보장**
**문제**:
- Context Bar와 Dashboard는 주기적으로 업데이트되지만
- TaskTreeView는 명시적으로 `update_task_tree()`를 호출해야 업데이트됨

**현재 상태**:
- `update_dashboard_metrics()`: 5초마다 자동
- `update_context_bar()`: 호출 시점 불명확
- `update_task_tree()`: 수동 호출 또는 이벤트 기반

**필요 기능**:
- Task 상태 변경 시 자동으로 TaskTreeView 업데이트
- Agent 시작/종료 시 Context Bar 자동 업데이트

---

### 4. **프로젝트 구조와 Task 연계**
**문제**:
- 프로젝트 구조(Blueprint)와 task 진행상황이 분리되어 표시됨
- 어떤 파일/컴포넌트가 어떤 task와 연관되어 있는지 시각적으로 확인 어려움

**현재 상태**:
- StructureHierarchyView: 프로젝트 구조만 표시
- TaskTreeView: Task 진행상황만 표시
- 두 뷰 간 연계 없음

**필요 기능**:
- 프로젝트 구조에서 task 진행 중인 컴포넌트 하이라이트
- Task 선택 시 관련 파일/컴포넌트 자동 하이라이트

---

## 📊 종합 평가

### 현재 가능한 것 ✅

1. **여러 agent 프로세스 모니터링**
   - Context Bar에서 활성 agent 확인
   - Channel Manager로 각 agent 출력 분리 확인
   - Dashboard에서 전체 agent 수 확인

2. **Task 진행상황 파악**
   - TaskTreeView에서 모든 task 상태 확인
   - 진행률 % 표시
   - Worker Squad stages 상세 확인

3. **프로젝트 구조 확인**
   - StructureHierarchyView로 계층 구조 확인
   - StructureGraphView로 그래프 형태 확인
   - Blueprint 비교로 드리프트 확인

4. **실시간 현황 파악**
   - Dashboard Header: 5초마다 업데이트
   - Context Bar: 실시간 agent 활동
   - Channel Manager: 실시간 스트리밍

### 현재 어려운 것 ⚠️

1. **한 화면에서 모든 정보 통합 확인**
   - 여러 뷰를 전환해야 함
   - 프로젝트 구조와 task를 동시에 보기 어려움

2. **Agent 프로세스 상세 상태**
   - 각 agent의 리소스 사용량 확인 어려움
   - Agent별 실행 시간 등 상세 정보 부족

3. **프로젝트 구조와 Task 연계**
   - 어떤 파일이 어떤 task와 연관되어 있는지 시각적 확인 어려움
   - 컴포넌트별 task 진행상황 오버레이 없음

---

## 🎯 결론

**현재 구조로도 기본적인 현황 파악은 가능합니다:**

✅ 여러 agent 프로세스 모니터링 가능  
✅ Task 진행상황 파악 가능  
✅ 프로젝트 구조 확인 가능  
✅ 실시간 업데이트 지원

**하지만 더 나은 가시성을 위해서는:**

⚠️ 통합 대시보드 뷰 추가  
⚠️ Agent 프로세스 상세 상태 표시  
⚠️ 프로젝트 구조와 Task 연계 시각화  
⚠️ 실시간 업데이트 보장 강화

**권장 사항**: 현재 구조로도 충분히 사용 가능하지만, 위 개선사항을 추가하면 더욱 효율적인 현황 파악이 가능합니다.
