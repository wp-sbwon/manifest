# Next Steps

This document outlines the immediate next steps for the Manifest project after the refactoring to `src/` layout and documentation organization.

## Completed ✅

1. **Project Structure Refactoring**
   - Migrated to `src/` layout
   - Organized modules into logical packages (core, ui, agents, bridge, audit)
   - Updated all imports and test paths

2. **Documentation Organization**
   - All documentation moved to `docs/` directory
   - Created comprehensive documentation (API, User Guide, Modules, Contributing)
   - Established documentation policy

3. **Import Verification**
   - All core imports verified and working
   - Module structure validated

## Immediate Next Steps

### 1. Test Suite Verification
- [ ] Install pytest in virtual environment
- [ ] Run full test suite to verify refactoring didn't break anything
- [ ] Fix any import or path issues in tests
- [ ] Verify test coverage

### 2. Git Commit
- [ ] Stage all refactoring changes
- [ ] Create meaningful commit message
- [ ] Commit to `dev` branch
- [ ] Verify no broken imports or missing files

### 3. Dependency Verification
- [ ] Ensure all dependencies are in `requirements.txt`
- [ ] Verify pytest is included
- [ ] Check for any missing dependencies

## Short-term Goals

### 1. Test Infrastructure
- Ensure all tests pass with new structure
- Add tests for new modules (agents, context_provider, task_scoper)
- Improve test coverage

### 2. Documentation Updates
- Update any outdated file paths in documentation
- Ensure all examples use correct import paths
- Verify all cross-references work

### 3. CI/CD Setup (Optional)
- Consider adding GitHub Actions for automated testing
- Set up pre-commit hooks
- Automated documentation checks

## Known Issues to Address

### High Priority
1. **Bootstrap UI Nested App Issue**
   - Status: Open
   - Workaround: Manual key configuration
   - Need: Fix event loop conflict

### Medium Priority
1. **Test Coverage**
   - Current: ~70%
   - Target: >80%
   - Focus: UI modules, agent modules

2. **Documentation Completeness**
   - Some modules need more detailed examples
   - API documentation could include more use cases

## Development Workflow

### Before Starting Work
1. Ensure virtual environment is activated
2. Set `PYTHONPATH=src` for development
3. Run tests to verify current state

### During Development
1. Write tests first (TDD approach)
2. Update documentation as needed
3. Keep documentation in `docs/` directory
4. Follow code style guidelines

### Before Committing
1. Run full test suite
2. Verify all imports work
3. Check documentation is updated
4. Ensure no files in wrong locations

## Testing Checklist

- [ ] All imports resolve correctly
- [ ] All tests pass
- [ ] No linter errors
- [ ] Documentation is up to date
- [ ] No files in project root (except README.md)

## File Structure Verification

Verify the following structure:
```
manifest/
├── README.md              # Only .md in root
├── docs/                  # All documentation
├── src/                   # All source code
├── tests/                 # All tests
├── scripts/               # Utility scripts
└── .manifest/             # Application data
```

## Next Major Features

Based on project status, these are the planned features:

1. **Multi-Agent System** (High Priority)
   - Complete agent coordination
   - Context injection hooks
   - Enhanced OMOC protocol

2. **Structural Spec-First Management** (Medium Priority)
   - Blueprint-based file system management
   - Structural drift detection

3. **Shadow Manager** (Medium Priority)
   - Sandbox operations
   - Safe promotion logic

## Backlog (Future Features)

Features planned for implementation after core infrastructure is complete:

### Agent Squad Monitoring & Watchdog System
**Priority**: Medium (후순위 - Multi-agent 시스템 뼈대 구현 후)

**Description**: 
Agent squad의 작업을 실시간으로 모니터링하고 문제를 감지/방지하는 시스템

**Requirements**:
- Agent 작업 모니터링
  - 각 agent의 실행 상태 추적
  - 작업 진행률 모니터링
  - 리소스 사용량 추적 (CPU, 메모리, 네트워크)
  
- 문제 감지 및 방지
  - Terminal command hanging 감지
  - 무한 루프 감지
  - 데드락 감지
  - 타임아웃 관리
  - 메모리 누수 감지
  - 무응답 프로세스 감지
  
- 자동 복구 메커니즘
  - Hanging 작업 자동 종료
  - 실패한 작업 재시도 로직
  - Agent 상태 복구
  - 리소스 정리

- 알림 및 로깅
  - 문제 발생 시 사용자 알림
  - 상세한 감사 로그
  - 성능 메트릭 수집
  - 문제 패턴 분석

**Implementation Notes**:
- Agent 실행을 프로세스/스레드 레벨에서 추적
- Heartbeat 메커니즘으로 agent 생존 확인
- Command timeout 설정 및 강제 종료
- Resource limits 설정 (CPU, memory)
- Watchdog thread/process로 전체 시스템 감시

**Dependencies**:
- Multi-Agent System 기본 구조 완성 후
- OMOC Bridge와의 통합 필요
- State Manager 확장 필요

## Notes

- All documentation should be in `docs/` directory
- Follow `DOCUMENTATION_POLICY.md` for new documentation
- Use `src/` layout for all source code
- Keep project root clean
