# 문서 정리 계획

**작성일**: 2026-01-24  
**목적**: docs 디렉토리 정리, 중복 제거, 버전 관리

---

## 📊 현재 문서 분류

### 1. 핵심 문서 (유지)
- `README.md` - 문서 인덱스
- `USER_GUIDE.md` - 사용자 가이드
- `DEV_SETUP.md` - 개발 환경 설정
- `ARCHITECTURE.md` - 시스템 아키텍처
- `API.md` - API 레퍼런스
- `MODULES.md` - 모듈 문서
- `PROJECT_STATUS.md` - 프로젝트 상태 (최신 버전으로 통합)
- `CONTRIBUTING.md` - 기여 가이드
- `DOCUMENTATION_POLICY.md` - 문서 정책

### 2. 완료된 기능 문서 (아카이브)
- `MISSING_IMPLEMENTATIONS.md` - ✅ 모든 기능 구현 완료
- `ADDITIONAL_MISSING_UI_FEATURES.md` - ✅ 모든 기능 구현 완료
- `IMPLEMENTATION_SUMMARY.md` - Phase 1 완료 요약
- `FINAL_IMPLEMENTATION_REPORT.md` - 최종 구현 보고서
- `CRITICAL_IMPLEMENTATION_SUMMARY.md` - Critical 기능 완료
- `HIGH_PRIORITY_IMPLEMENTATION_SUMMARY.md` - High Priority 완료

### 3. 중복/구버전 문서 (통합 또는 삭제)
- `CODE_REVIEW.md` + `CODE_REVIEW_SUMMARY.md` + `CODEBASE_REVIEW_FINDINGS.md` → `ARCHIVE/CODE_REVIEW_v1.0.md` (통합)
- `PROJECT_REVIEW.md` → `ARCHIVE/PROJECT_REVIEW_v1.0.md`
- `CODEBASE_AUDIT.md` → `ARCHIVE/CODEBASE_AUDIT_v1.0.md`
- `MANIFEST_ARCHITECTURE.md` → `ARCHITECTURE.md`와 통합 또는 아카이브
- `MANIFEST_REQUIREMENTS.md` → `ARCHIVE/MANIFEST_REQUIREMENTS_v1.0.md`
- `REMAINING_FEATURES.md` → `ARCHIVE/REMAINING_FEATURES_v1.0.md`
- `CRITICAL_PRIORITIES.md` → `ARCHIVE/CRITICAL_PRIORITIES_v1.0.md`
- `REVISED_PRIORITIES.md` → `ARCHIVE/REVISED_PRIORITIES_v1.0.md`

### 4. 상태/진행 문서 (통합)
- `PROJECT_STATUS.md` - 최신 상태로 통합
- `TASK_MANAGER_STATUS.md` → `PROJECT_STATUS.md`에 통합
- `REFACTORING_STATUS.md` → `REFACTORING.md`에 통합
- `CURRENT_VISIBILITY_STATUS.md` → `PROJECT_STATUS.md`에 통합

### 5. 계획/설계 문서 (유지 또는 아카이브)
- `INTEGRATED_VIEW_UX_DESIGN.md` - ✅ 구현 완료, 아카이브
- `COMPONENT_GRAPH_IMPROVEMENT_PROPOSAL.md` - ✅ 구현 완료, 아카이브
- `UX_IMPROVEMENT_PLAN.md` - 계획 문서, 유지
- `NEXT_STEPS.md` - 다음 단계, 유지
- `FINAL_PLAN.md` - 최종 계획, 아카이브

### 6. 프로젝트 구조 문서 (통합)
- `MANIFEST_PROJECT_STRUCTURE.md` + `MANIFEST_PROJECT_VIEW_STATUS.md` + `MANIFEST_PROJECT_VISUALIZATION.md` → `PROJECT_STRUCTURE.md` (통합)

### 7. 기타
- `SKILLS.md` - 유지
- `ORCHESTRATOR_WORKFLOW.md` - 유지
- `SETUP_GITHUB.md` - 유지
- `REFACTORING.md` - 유지

---

## 🗂️ 정리 후 구조

```
docs/
├── README.md                          # 문서 인덱스 (업데이트)
├── USER_GUIDE.md                      # 사용자 가이드
├── DEV_SETUP.md                       # 개발 환경 설정
├── ARCHITECTURE.md                    # 시스템 아키텍처 (통합)
├── API.md                             # API 레퍼런스
├── MODULES.md                         # 모듈 문서
├── PROJECT_STATUS.md                  # 프로젝트 상태 (통합, 최신)
├── PROJECT_STRUCTURE.md               # 프로젝트 구조 (통합)
├── CONTRIBUTING.md                    # 기여 가이드
├── DOCUMENTATION_POLICY.md            # 문서 정책
├── NEXT_STEPS.md                      # 다음 단계
├── UX_IMPROVEMENT_PLAN.md             # UX 개선 계획
├── SKILLS.md                          # Skills 문서
├── ORCHESTRATOR_WORKFLOW.md           # Orchestrator 워크플로우
├── SETUP_GITHUB.md                   # GitHub 설정
├── REFACTORING.md                     # 리팩토링 히스토리
├── project-manifest/                  # 프로젝트 매니페스트
│   ├── project.json
│   ├── documentation.json
│   ├── visualization.md
│   └── README.md
└── archive/                           # 아카이브 (버전 관리)
    ├── v1.0/
    │   ├── MISSING_IMPLEMENTATIONS.md
    │   ├── ADDITIONAL_MISSING_UI_FEATURES.md
    │   ├── IMPLEMENTATION_SUMMARY.md
    │   ├── FINAL_IMPLEMENTATION_REPORT.md
    │   ├── CODE_REVIEW_v1.0.md
    │   ├── PROJECT_REVIEW_v1.0.md
    │   ├── CODEBASE_AUDIT_v1.0.md
    │   ├── MANIFEST_REQUIREMENTS_v1.0.md
    │   ├── REMAINING_FEATURES_v1.0.md
    │   ├── CRITICAL_PRIORITIES_v1.0.md
    │   ├── REVISED_PRIORITIES_v1.0.md
    │   ├── INTEGRATED_VIEW_UX_DESIGN.md
    │   ├── COMPONENT_GRAPH_IMPROVEMENT_PROPOSAL.md
    │   └── FINAL_PLAN.md
    └── README.md                       # 아카이브 설명
```

---

## 📋 작업 순서

1. **아카이브 디렉토리 생성**
2. **완료된 기능 문서 이동** (v1.0)
3. **중복 문서 통합 및 아카이브**
4. **상태 문서 통합** (PROJECT_STATUS.md)
5. **구조 문서 통합** (PROJECT_STRUCTURE.md)
6. **README.md 업데이트**
7. **버전 태그 추가** (선택사항)

---

## ✅ 검증 체크리스트

- [ ] 모든 핵심 문서가 유지됨
- [ ] 중복 문서가 제거되거나 통합됨
- [ ] 아카이브에 버전 정보 포함
- [ ] README.md가 최신 구조 반영
- [ ] 링크가 깨지지 않음
- [ ] Git 히스토리 보존 (파일 이동만, 삭제 아님)
