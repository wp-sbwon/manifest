# .manifest/ 디렉토리

이 디렉토리는 **Manifest 애플리케이션의 런타임 데이터**를 저장하는 워크스페이스입니다.

## 용도

Manifest 앱이 실행될 때 사용하는 파일들을 저장합니다.

## 파일 구조

### 런타임 상태 (Runtime State)
- `state.json` - 세션 상태, 미션 트리, 작업 체크리스트, 채팅 히스토리
  - 앱 실행 시 자동 생성/업데이트
  - 세션 복구에 사용

### 설정 파일 (Configuration)
- `keys.json` - 암호화된 API 키 (gitignore에 포함)
- `.key` - 암호화 키 (gitignore에 포함)
- `agent_config.json` - Multi-Agent 시스템의 LLM 모델 설정

### 프로젝트 설계 문서 (Project Design Documents)
사용자가 Manifest로 관리하는 **프로젝트**의 설계 문서:

- `prd.json` - 제품 요구사항 (PRD)
- `blueprint_design.json` - Top-down 설계 (설계도)
- `blueprint_code.json` - Bottom-up 설계 (코드에서 추출)
- `blueprint_view.json` - 비교 결과 (설계 vs 코드, 검증 포함)

### 충돌 리포트 (Conflict Reports)
- `conflicts/` - Blueprint 동기화 시 발생한 충돌 리포트 저장

## Manifest 프로젝트 자체 문서

Manifest 프로젝트를 개발하면서 만든 문서들은 **별도 위치**에 있습니다:
- `docs/project-manifest/project.json` - Manifest 프로젝트 아키텍처
- `docs/project-manifest/documentation.json` - Manifest 프로젝트 문서 통합본
- `docs/project-manifest/visualization.md` - Manifest 프로젝트 시각화

## Git 관리

다음 파일들은 민감한 정보를 포함하므로 gitignore에 포함되어 있습니다:
- `keys.json`
- `.key`
- `conflicts/`

나머지 설계 문서들은 버전 관리됩니다.
