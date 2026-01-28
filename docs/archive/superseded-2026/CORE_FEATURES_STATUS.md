# Manifest 핵심 기능 구현 상태 (2026-01-28)

**사용자 요구사항 확인**:
1. OpenCode를 사용해서 개발하는 것과 완전 동일하게 개발 가능
2. Orchestrator와 ideation 과정에서 PRD 문서를 만들고, 이 PRD 문서에 대한 구조를 시각화 해서 볼 수 있음
3. 자동 코딩으로 개발됨에 따라 프로젝트 전체 현황에 대한 정확한 확인(ground truth 기준 - no hallucination allowed)과, task 등을 보고 관리할 수 있음

---

## 1. OpenCode 사용 개발 ✅ **완전 구현**

### 구현 상태
- ✅ **OpenCode LLM Adapter**: 완전 구현, 기본 백엔드로 사용 중
- ✅ **Tool execution**: OpenCode가 tool_use 이벤트 반환 → Manifest가 실행
- ✅ **Context management**: OpenCode가 처리
- ✅ **Session management**: OpenCode 세션 관리 완료

### 동작 방식
```python
# 기본 백엔드: "opencode"
executor = ExecutorFactory.create_executor(...)
# → OpenCodeLLMAdapter 생성

# Agent 실행
CoderAgent.implement()
→ executor.execute_agent()
→ OpenCode HTTP API 호출 (http://localhost:4096/api/v1/agents/...)
→ OpenCode가 Claude/GPT 호출
→ OpenCode가 tool_use 이벤트 반환
→ Manifest가 실제 도구 실행 (bash/edit/write/read)
```

### 완전 동일한 개발 가능 여부
**✅ 예**: OpenCode를 사용한 개발과 완전 동일하게 작동합니다.
- OpenCode가 LLM 호출, 컨텍스트 관리, tool execution 처리
- Manifest는 워크플로우 오케스트레이션만 담당
- 실제 코드 생성/실행은 OpenCode와 동일한 방식

**코드 위치**:
- `src/manifest/runtime/opencode_llm_adapter.py`
- `src/manifest/runtime/agent/core/executor_factory.py`

---

## 2. PRD 생성 및 구조 시각화 ⚠️ **부분 구현**

### 구현 상태

#### ✅ PRD 생성 (완전 구현)
- ✅ **Ideation Mode**: OrchestratorAgent.start_ideation() 구현 완료
- ✅ **PRD Template**: `.claude/rules/prd-template.md` 사용
- ✅ **대화형 PRD 생성**: 사용자와 질문/답변을 통해 PRD 생성
- ✅ **PRD 저장**: PRDManager.save_prd() 구현 완료
- ✅ **PRD 로드**: PRDManager.load_prd() 구현 완료
- ✅ **Context에 포함**: Tier 1 context에 PRD 포함

**코드 위치**:
- `src/manifest/runtime/agent/agents/orchestrator_agent.py` (line 122-171)
- `src/manifest/core/prd_manager.py`
- `src/manifest/runtime/agent/prompts/orchestrator_prompt.py` (get_ideation_prompt)

#### ⚠️ PRD 구조 시각화 (부분 구현)
- ✅ **Architecture 시각화**: StructureHierarchyView, StructureGraphView 구현 완료
- ✅ **Blueprint 시각화**: StructureHierarchyView에서 Features → Requirements → Components 표시
- ❌ **PRD 전용 시각화**: UI에 PRD 전용 뷰/위젯 없음
- ⚠️ **PRD 표시**: PRD는 생성/저장되지만 UI에서 직접적으로 시각화되지 않음

**현재 상태**:
- PRD는 `.manifest/prd.json`에 저장됨
- PRD는 context에 포함되어 agent들에게 전달됨
- 하지만 UI에서 PRD를 직접 보는 전용 뷰는 없음
- Architecture/Blueprint 시각화는 있지만 PRD 구조를 명시적으로 표시하지 않음

**코드 위치**:
- `src/manifest/ui/widgets/structure_hierarchy_view.py` (Architecture/Blueprint 시각화)
- `src/manifest/ui/widgets/structure_graph_view.py` (Blueprint Graph 시각화)

### 부족한 부분
**PRD 전용 시각화 위젯 필요**:
- PRD Overview, User Flows, Technical Constraints 등을 시각화하는 위젯
- PRD → Architecture → Blueprint 연결 관계 표시
- PRD 요구사항과 구현 상태 매핑 표시

---

## 3. Ground Truth 확인 및 Hallucination 방지 ✅ **완전 구현**

### 구현 상태

#### ✅ VisualRealityHook (완전 구현)
- ✅ **실제 프로젝트 상태 주입**: Agent 프롬프트에 현재 프로젝트 상태 자동 주입
- ✅ **Architecture 상태**: Features, completion percentage 표시
- ✅ **Implementation Status**: Implemented/Ghost/Drift 컴포넌트 수 표시
- ✅ **Drift Details**: Active drift 상세 정보 표시
- ✅ **Task Context**: 현재 task의 상태, scope, allowed files 표시

**동작 방식**:
```python
# Agent 프롬프트 실행 전
VisualRealityHook.intercept_prompt()
→ _generate_visual_reality()
→ Architecture status, Implementation status, Drift details, Task context 수집
→ "## VISUAL REALITY (Current Project State)" 섹션을 프롬프트에 삽입
→ Agent가 실제 코드베이스 상태를 인지하고 작업
```

**코드 위치**: `src/manifest/runtime/hooks/prompt_hooks.py` (line 72-250)

#### ✅ BlueprintComparator Ground Truth 비교 (완전 구현)
- ✅ **Ground Truth Fields**: methods, attributes, structural info (id, name, type, file, line) strict comparison
- ✅ **Non-Ground Truth Fields**: metadata (algorithm, design_pattern, complexity) tolerant comparison
- ✅ **Drift Detection**: Design blueprint vs 실제 코드 비교
- ✅ **Conflict Reporting**: Missing methods, extra methods, type mismatches 등

**동작 방식**:
```python
BlueprintComparator.compare_blueprints(top_down, bottom_up)
→ _compare_methods() - Ground Truth strict comparison
→ _compare_attributes() - Ground Truth strict comparison
→ _compare_structural_fields() - Ground Truth strict comparison (id, name, type, file, line)
→ _compare_metadata_fields() - Non-Ground Truth tolerant comparison
→ BlueprintConflict 리스트 반환
```

**코드 위치**: `src/manifest/audit/blueprint/blueprint_comparator.py` (line 110-380)

#### ✅ Task 관리 UI (완전 구현)
- ✅ **Task Tree**: TaskTree 위젯으로 task 목록 표시
- ✅ **Task Status**: pending, in_progress, done, blocked 상태 표시
- ✅ **Task Progress View**: Worker Squad stages, modified files, git diff 표시
- ✅ **Workflow Visualization**: 병렬 실행 포함 workflow 시각화
- ✅ **Task-File 연결**: StructureHierarchyView에서 task와 file 연결 표시

**코드 위치**:
- `src/manifest/ui/widgets/project_view.py`
- `src/manifest/ui/widgets/task_progress_view.py`
- `src/manifest/ui/widgets/workflow_visualization.py`

### Hallucination 방지 메커니즘

1. **VisualRealityHook**: Agent가 실제 코드베이스 상태를 인지
   - "Component X is in GHOST status" → Agent가 존재하지 않는 컴포넌트 호출 방지
   - "Component Y has drift" → Agent가 잘못된 가정으로 작업 방지

2. **BlueprintComparator**: Ground Truth 필드 strict comparison
   - methods, attributes, structural info는 정확히 일치해야 함
   - 불일치 시 conflict로 보고

3. **Tiered Context**: 필요한 정보만 제공
   - Tier 0: Policy (모든 agent)
   - Tier 1: PRD, Architecture (Orchestrator/Planner)
   - Tier 2: Blueprint (Coder)
   - Tier 3: Surgical Code (필요 시에만)

4. **Drift Detection**: 실시간 아키텍처-코드 불일치 감지
   - BlueprintSynchronizer가 지속적으로 모니터링
   - Drift 발생 시 즉시 보고

---

## 요약

| 기능 | 구현 상태 | 비고 |
|------|----------|------|
| **1. OpenCode 사용 개발** | ✅ 완전 구현 | OpenCode와 완전 동일하게 작동 |
| **2. PRD 생성** | ✅ 완전 구현 | Ideation mode로 대화형 PRD 생성 |
| **2. PRD 구조 시각화** | ⚠️ 부분 구현 | PRD 생성/저장은 되지만 UI 전용 시각화 없음 |
| **3. Ground Truth 확인** | ✅ 완전 구현 | VisualRealityHook + BlueprintComparator |
| **3. Hallucination 방지** | ✅ 완전 구현 | Visual Reality + Ground Truth 비교 |
| **3. Task 관리 UI** | ✅ 완전 구현 | Task Tree, Progress View, Workflow Visualization |

---

## 부족한 부분

### PRD 구조 시각화 위젯 필요

**현재**: PRD는 생성되고 저장되지만 UI에서 직접적으로 시각화되지 않음

**필요한 기능**:
1. **PRD View 위젯**: PRD Overview, User Flows, Technical Constraints 등을 표시
2. **PRD → Architecture → Blueprint 연결**: PRD 요구사항과 구현 상태 매핑
3. **PRD 요구사항 추적**: 각 PRD 요구사항이 어떤 task/component로 구현되었는지 표시

**구현 위치**: `src/manifest/ui/widgets/prd_view.py` (신규 생성 필요)

**우선순위**: 중간 (기능적으로는 작동하지만 사용자 경험 개선)

---

## 결론

**현재 Manifest는**:
- ✅ **OpenCode와 완전 동일한 개발 환경** 제공
- ✅ **PRD 생성** 완전 구현 (대화형 ideation)
- ⚠️ **PRD 구조 시각화** 부분 구현 (생성/저장은 되지만 UI 시각화 부족)
- ✅ **Ground Truth 확인 및 Hallucination 방지** 완전 구현

**부족한 부분**: PRD 전용 시각화 위젯 (기능적으로는 작동하지만 UX 개선 필요)
