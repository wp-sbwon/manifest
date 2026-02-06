# UI 전면 수정 계획

## 목표
OpenCode처럼 사용할 수 있는 느낌 + 시각화 및 Task 관리 UI 통합

## 핵심 원칙
1. **채팅이 메인**: OpenCode 터미널에서 채팅·입력 (manifest 실행 시 OpenCode가 함께 뜸)
2. **시각화는 컴팩트**: View 앱은 사이드바·메트릭만 담당
3. **Task 관리**: 토글 가능한 별도 패널
4. **@, !, /** 는 **OpenCode 기본 기능** → View에서 따로 구현하지 않음

## 새로운 레이아웃 구조

```
┌─────────────────────────────────────────────────────────────┐
│ [Header: Manifest Dashboard | Metrics]                       │
├──────────┬───────────────────────────────────────────────────┤
│          │                                                   │
│ Sidebar  │         Main Chat Area (OpenCode Style)          │
│ (Compact)│                                                   │
│          │         - Large chat log                          │
│ - Tasks  │         - File references (@)                      │
│ - Status │         - Bash commands (!)                       │
│ - Viz    │         - Slash commands (/)                      │
│          │                                                   │
│          │         [Input: Type message...]                 │
├──────────┴───────────────────────────────────────────────────┤
│ [Optional: Task Panel (Toggle with keybind)]                │
└─────────────────────────────────────────────────────────────┘
```

## 구현 단계

### Phase 1: 레이아웃 재구성
- 채팅 영역을 메인으로 (70-80% 화면)
- 사이드바를 컴팩트하게 (20-30% 화면)
- Task 패널을 토글 가능하게

### Phase 2: ~~OpenCode 기능 추가~~ (해당 없음)
- **@, !, / 는 OpenCode 기본 기능.** View에서 재구현하지 않음. 채팅·입력은 OpenCode 터미널에서 처리.

### Phase 3: 시각화 통합
- Dashboard metrics를 상단 헤더로
- Task tree를 사이드바로
- Agent status를 사이드바로

### Phase 4: UX 개선
- 키보드 단축키
- 토글 기능
- 스크롤 개선
