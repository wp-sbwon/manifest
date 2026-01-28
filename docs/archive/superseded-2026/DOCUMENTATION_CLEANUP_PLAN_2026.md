# 문서 정리 계획 (2026-01-28)

**목적**: 실제 코드 상태에 맞게 문서 정리 및 업데이트
**기준**: 코드베이스 직접 검토 결과

---

## 📊 현재 문서 현황

- **총 문서 수**: 57개
- **핵심 문서**: ~15개
- **중복/오래된 문서**: ~20개
- **아카이브 문서**: 26개 (이미 archive/v1.0에 있음)

---

## 🗑️ 삭제/통합할 문서

### 1. 중복 문서 통합

#### 테스트 관련 문서 (3개 → 1개로 통합)
- ❌ `TESTING_STATUS.md` (2026-01-24, 오래됨)
- ❌ `TESTING_STATUS_SUMMARY.md` (2026-01-24, 요약본)
- ❌ `TESTING_REALITY_CHECK.md` (2026-01-24, 중복)
- ✅ **유지**: `TESTING_STATUS.md` 하나로 통합 (최신 상태 반영)

#### TODO/우선순위 문서 (3개 → 1개로 통합)
- ❌ `TODO_UPDATED.md` (2026-01-26, GAPS_AND_NEXT와 중복)
- ❌ `NEXT_STEPS.md` (완료된 항목 많음, GAPS_AND_NEXT와 중복)
- ✅ **유지**: `GAPS_AND_NEXT.md` 하나로 통합 (실제 코드 기준)

#### CI/CD 문서 (2개 → 1개로 통합)
- ❌ `CI_CD_SETUP.md` (2026-01-24)
- ❌ `CI_FAILURE_DETECTION.md` (2026-01-26)
- ✅ **유지**: `CI_CD_SETUP.md` 하나로 통합 (CI_FAILURE 내용 포함)

#### 프로젝트 상태 문서 (중복 정리)
- ❌ `MANIFEST_PROJECT_AUDIT.md` (PROJECT_STATUS와 중복)
- ✅ **유지**: `PROJECT_STATUS.md` (실제 코드 상태 반영)

### 2. 아카이브로 이동할 문서

#### 완료된 기능 문서 (이미 archive에 있지만 추가 정리)
- `MULTI_AGENT_WORKFLOW_IMPROVEMENTS.md` → archive/v1.0 (완료된 내용)
- `ARCHITECTURE_CHANGES.md` → archive/v1.0 (변경 이력)
- `CODE_QUALITY_REVIEW.md` → archive/v1.0 (리뷰 문서)

#### 계획/개선 문서 (완료됨)
- `UX_IMPROVEMENT_PLAN.md` → archive/v1.0 (일부 완료, 나머지 선택적)
- `PROJECT_STRUCTURE.md` → 유지 (현재 구조 설명)

---

## ✅ 업데이트할 핵심 문서

### 1. PROJECT_STATUS.md (최우선)
**현재 문제**:
- "미구현"으로 표기된 기능들이 실제로는 구현되어 있음
- Context Injection Hooks, Multi-Agent Workflow, Container Communication 등

**업데이트 내용**:
- ✅ 실제 구현 상태 반영
- ✅ 완료된 기능 정확히 표시
- ✅ 실제로 남은 작업만 "미구현"으로 표시

### 2. GAPS_AND_NEXT.md
**현재 문제**:
- 완료된 항목들이 여전히 "해야 할 일"로 표시됨
- 실제 코드와 불일치

**업데이트 내용**:
- ✅ 완료된 항목 제거 또는 "완료" 표시
- ✅ 실제로 남은 작업만 정리
- ✅ 코드 기준으로만 작성

### 3. ARCHITECTURE.md
**현재 문제**:
- Orchestrator vs OrchestratorAgent 혼동
- 실제 데이터 흐름과 다름

**업데이트 내용**:
- ✅ 실제 사용되는 클래스 명확히 표시
- ✅ 정확한 데이터 흐름 반영
- ✅ 실제 코드 위치 반영

### 4. docs/README.md
**현재 문제**:
- 존재하지 않는 문서 참조
- 오래된 구조 반영

**업데이트 내용**:
- ✅ 실제 존재하는 문서만 나열
- ✅ 새로운 구조 반영
- ✅ 중복 문서 제거

### 5. ORCHESTRATOR_WORKFLOW.md
**현재 문제**:
- 잘못된 코드 위치 참조

**업데이트 내용**:
- ✅ 정확한 코드 위치 반영

---

## 📁 최종 문서 구조

### 핵심 문서 (유지 및 업데이트)

```
docs/
├── README.md                    # 문서 인덱스 (업데이트 필요)
├── USER_GUIDE.md               # 사용자 가이드 ✅
├── DEV_SETUP.md                # 개발 환경 설정 ✅
├── ARCHITECTURE.md             # 시스템 아키텍처 (업데이트 필요)
├── API.md                      # API 레퍼런스 ✅
├── MODULES.md                  # 모듈 문서 ✅
├── PROJECT_STATUS.md           # 프로젝트 상태 (업데이트 필요)
├── GAPS_AND_NEXT.md            # 남은 작업 (업데이트 필요)
├── CONTRIBUTING.md             # 기여 가이드 ✅
├── SKILLS.md                   # Skills 문서 ✅
├── ORCHESTRATOR_WORKFLOW.md    # Orchestrator 워크플로우 (업데이트 필요)
├── SETUP_GITHUB.md             # GitHub 설정 ✅
├── REFACTORING.md              # 리팩토링 히스토리 ✅
├── DOCUMENTATION_POLICY.md     # 문서 정책 ✅
├── CI_CD_SETUP.md              # CI/CD 설정 (통합 후)
└── TESTING_STATUS.md           # 테스트 현황 (통합 후)
```

### 아카이브 문서

```
docs/archive/
├── README.md                   # 아카이브 인덱스
└── v1.0/                       # v1.0 문서들 (26개 + 새로 추가될 문서들)
    ├── MULTI_AGENT_WORKFLOW_IMPROVEMENTS.md
    ├── ARCHITECTURE_CHANGES.md
    ├── CODE_QUALITY_REVIEW.md
    └── UX_IMPROVEMENT_PLAN.md
```

---

## 🎯 정리 작업 순서

### Phase 1: 문서 삭제 및 통합
1. ✅ 중복 문서 통합
   - TESTING_STATUS 시리즈 → TESTING_STATUS.md 하나로
   - TODO_UPDATED, NEXT_STEPS → GAPS_AND_NEXT.md에 통합
   - CI_CD_SETUP, CI_FAILURE_DETECTION → CI_CD_SETUP.md로 통합

2. ✅ 아카이브로 이동
   - 완료된 기능 문서들 archive/v1.0으로 이동

### Phase 2: 핵심 문서 업데이트
1. ✅ PROJECT_STATUS.md 업데이트
   - 실제 구현 상태 반영
   - "미구현" 항목 재검토

2. ✅ GAPS_AND_NEXT.md 업데이트
   - 완료된 항목 제거
   - 실제 남은 작업만 정리

3. ✅ ARCHITECTURE.md 업데이트
   - 실제 구조 반영
   - 정확한 코드 위치

4. ✅ docs/README.md 업데이트
   - 새로운 구조 반영

---

## 📝 작업 체크리스트

### 삭제/통합
- [ ] TESTING_STATUS_SUMMARY.md 삭제 (TESTING_STATUS.md에 통합)
- [ ] TESTING_REALITY_CHECK.md 삭제 (TESTING_STATUS.md에 통합)
- [ ] TODO_UPDATED.md 삭제 (GAPS_AND_NEXT.md에 통합)
- [ ] NEXT_STEPS.md 삭제 (GAPS_AND_NEXT.md에 통합)
- [ ] CI_FAILURE_DETECTION.md 삭제 (CI_CD_SETUP.md에 통합)
- [ ] MANIFEST_PROJECT_AUDIT.md 아카이브로 이동

### 아카이브 이동
- [ ] MULTI_AGENT_WORKFLOW_IMPROVEMENTS.md → archive/v1.0
- [ ] ARCHITECTURE_CHANGES.md → archive/v1.0
- [ ] CODE_QUALITY_REVIEW.md → archive/v1.0
- [ ] UX_IMPROVEMENT_PLAN.md → archive/v1.0

### 업데이트
- [ ] PROJECT_STATUS.md 업데이트
- [ ] GAPS_AND_NEXT.md 업데이트
- [ ] ARCHITECTURE.md 업데이트
- [ ] ORCHESTRATOR_WORKFLOW.md 업데이트
- [ ] docs/README.md 업데이트
- [ ] TESTING_STATUS.md 통합 및 업데이트
- [ ] CI_CD_SETUP.md 통합 및 업데이트

---

## 📊 예상 결과

### Before
- 총 문서: 57개
- 핵심 문서: ~15개
- 중복 문서: ~20개

### After
- 총 문서: ~35개 (삭제/통합 후)
- 핵심 문서: ~15개 (정리됨)
- 아카이브 문서: ~30개 (정리됨)

### 개선 사항
1. ✅ 중복 제거
2. ✅ 실제 코드 상태 반영
3. ✅ 명확한 문서 구조
4. ✅ 유지보수 용이성 향상
