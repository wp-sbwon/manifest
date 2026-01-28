# Manifest 프로젝트 문서

이 디렉토리는 **Manifest 프로젝트 자체**를 문서화한 파일들을 저장합니다.

## 용도

Manifest IDE를 개발하면서 만든 프로젝트 문서들입니다. Manifest 앱의 런타임 데이터가 아닙니다.

## 파일 구조

- `project.json` - Manifest 프로젝트의 전체 아키텍처 및 상태
  - Features, Requirements, Modules 구조
  - 구현 상태 및 메트릭
  - 다음 단계 및 백로그

- `documentation.json` - Manifest 프로젝트의 모든 문서를 구조화된 JSON 형태로 제공
  - 프로젝트 개요 및 비전
  - 아키텍처 레이어
  - 데이터 모델
  - 구현 상태
  - 테스트 상태
  - 의존성

- `visualization.md` - Manifest 프로젝트 아키텍처 시각화
  - Mermaid 다이어그램
  - Feature 기반 구조
  - 데이터 흐름

## 구분

- **이 디렉토리**: Manifest 프로젝트 자체 문서 (개발용)
- **`.manifest/`**: Manifest 앱의 런타임 데이터 (실행용)

## 업데이트

프로젝트 구조나 구현 상태가 변경될 때 이 문서들을 업데이트합니다.
