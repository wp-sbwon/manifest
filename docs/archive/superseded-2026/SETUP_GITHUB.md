# GitHub 원격 저장소 설정 가이드

## GitHub CLI 설치 (선택사항)

### macOS에서 Homebrew로 설치
```bash
# Homebrew 설치 (없는 경우)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# GitHub CLI 설치
brew install gh

# GitHub CLI 로그인
gh auth login
```

### 수동 설치
1. https://cli.github.com/ 에서 macOS용 설치 파일 다운로드
2. 설치 후 `gh auth login` 실행

## 원격 저장소 수동 설정

GitHub CLI 없이도 원격 저장소를 설정할 수 있습니다:

### 1. GitHub에서 저장소 생성
1. https://github.com/new 접속
2. Repository name: `manifest` (또는 원하는 이름)
3. Public 또는 Private 선택
4. "Create repository" 클릭

### 2. 로컬에서 원격 저장소 연결
```bash
cd /Users/wonseongbae/Documents/Cursor/manifest

# 원격 저장소 추가 (YOUR_USERNAME을 실제 GitHub 사용자명으로 변경)
git remote add origin https://github.com/YOUR_USERNAME/manifest.git

# 또는 SSH 사용 (SSH 키가 설정된 경우)
# git remote add origin git@github.com:YOUR_USERNAME/manifest.git

# 브랜치 푸시
git push -u origin main
git push -u origin dev
```

### 3. 현재 브랜치 확인 및 푸시
```bash
# 현재 브랜치 확인 (dev여야 함)
git branch

# dev 브랜치 푸시
git push -u origin dev

# main 브랜치로 전환 후 푸시
git checkout main
git push -u origin main

# 다시 dev로 전환
git checkout dev
```

## 현재 상태

- ✅ 로컬 Git 저장소 초기화 완료
- ✅ main, dev 브랜치 생성 완료
- ✅ 현재 브랜치: dev
- ⏳ 원격 저장소 설정 필요

## 빠른 설정 (GitHub CLI 사용 시)

```bash
# GitHub CLI로 저장소 생성 및 푸시
gh repo create manifest --public --source=. --remote=origin --push
```

## 빠른 설정 (수동)

```bash
# 1. GitHub 웹에서 저장소 생성 후
# 2. 아래 명령 실행 (YOUR_USERNAME 변경 필요)
git remote add origin https://github.com/YOUR_USERNAME/manifest.git
git push -u origin main
git push -u origin dev
```
