# Component Graph 개선 제안 (ASCII 시각화)

**작성일**: 2026-01-24
**목적**: Component Graph의 세부 정보 표시 개선안

---

## 🎨 개선된 StructureGraphView (Graph 탭)

### 현재 (Before)
```
┌─────────────────────────────────────────────────────────────┐
│ ⚡ Feature: User Authentication (45%)                        │
│                                                              │
│   ┌──────────────┐    ┌──────────────┐                      │
│   │● AuthService │    │○ UserModel   │                      │
│   │ [Strategy]   │    │              │                      │
│   └──────────────┘    └──────────────┘                      │
│   → dependency: user_data → auth_token                      │
└─────────────────────────────────────────────────────────────┘
```

### 개선안 (After) - 확장 가능한 Component 박스
```
┌─────────────────────────────────────────────────────────────┐
│ ⚡ Feature: User Authentication (45%)                        │
│                                                              │
│   ┌──────────────────────────────────────┐                  │
│   │● AuthService [class] [Strategy]      │                  │
│   │  📁 src/auth/service.py:100          │                  │
│   │  📦 manifest.auth.service             │                  │
│   │  ──────────────────────────────────  │                  │
│   │  Methods (5):                         │                  │
│   │    • login(user, password)            │                  │
│   │    • logout(session_id)               │                  │
│   │    • validate_token(token)            │                  │
│   │    • refresh_token(token)             │                  │
│   │    • revoke_token(token)             │                  │
│   │  [+3 more] [Click to expand]          │                  │
│   │  ──────────────────────────────────  │                  │
│   │  Attributes (3):                      │                  │
│   │    • _session_store                   │                  │
│   │    • _token_validator                 │                  │
│   │    • _config                          │                  │
│   │  ──────────────────────────────────  │                  │
│   │  → UserModel (dependency)             │                  │
│   │    Symbols: login() calls UserModel.get()                │
│   │    📁 src/auth/service.py:45          │                  │
│   └──────────────────────────────────────┘                  │
│                                                              │
│   ┌──────────────────────────────────────┐                  │
│   │○ UserModel [class]                   │                  │
│   │  📁 src/models/user.py:20            │                  │
│   │  📦 manifest.models.user              │                  │
│   │  ──────────────────────────────────  │                  │
│   │  Methods (3):                         │                  │
│   │    • get(user_id)                     │                  │
│   │    • create(user_data)                │                  │
│   │    • update(user_id, data)             │                  │
│   │  ──────────────────────────────────  │                  │
│   │  Attributes (2):                      │                  │
│   │    • _db_connection                   │                  │
│   │    • _cache                          │                  │
│   └──────────────────────────────────────┘                  │
│                                                              │
│   [⚡ task-1] [✅ task-2]  ← 관련 Task 표시                │
└─────────────────────────────────────────────────────────────┘
```

---

## 🌳 개선된 StructureHierarchyView (Hierarchy 탭)

### 현재 (Before)
```
Feature: User Authentication
  Requirement: REQ-01
    ● AuthService [Strategy] [O(n)]
      📁 src/auth/service.py:100 ⚡ [task-1]
      Methods: login, logout, validate_token (+2 more)
```

### 개선안 (After) - 확장 가능한 트리
```
Feature: User Authentication (45%)
  Requirement: REQ-01: User login/logout
    ● AuthService [class] [Strategy] [O(n)]
      📁 src/auth/service.py:100 ⚡ [task-1]
      📦 manifest.auth.service
      ──────────────────────────────────────
      Methods (8) [▼ Expand]
        • login(user: str, password: str) -> Session
        • logout(session_id: str) -> bool
        • validate_token(token: str) -> bool
        • refresh_token(token: str) -> Token
        • revoke_token(token: str) -> bool
        • create_session(user_id: str) -> Session
        • get_session(session_id: str) -> Session
        • cleanup_expired_sessions() -> int
      ──────────────────────────────────────
      Attributes (3) [▼ Expand]
        • _session_store: Dict[str, Session]
        • _token_validator: TokenValidator
        • _config: AuthConfig
      ──────────────────────────────────────
      Contracts [▼ Expand]
        → UserModel (dependency)
          Type: call
          Symbols: login() → UserModel.get()
          📁 src/auth/service.py:45
        → TokenValidator (dependency)
          Type: dependency
          Symbols: validate_token() uses TokenValidator
          📁 src/auth/service.py:12
      ──────────────────────────────────────
      Tasks [▼ Expand]
        ⚡ task-1: Implement login (in_progress)
        ✅ task-2: Add token validation (done)
```

---

## 🔗 개선된 Contract 표시

### 현재 (Before)
```
→ dependency: user_data → auth_token
```

### 개선안 (After) - 상세 정보
```
┌─────────────────────────────────────────────────────────────┐
│ Contract: AuthService → UserModel                           │
├─────────────────────────────────────────────────────────────┤
│ Type: dependency (call)                                      │
│                                                              │
│ Symbols:                                                     │
│   • AuthService.login() calls UserModel.get()                │
│   • AuthService.create_user() calls UserModel.create()      │
│                                                              │
│ Data Flow:                                                   │
│   Input:  user_id: str, password: str                        │
│   Output: user_data: Dict, session: Session                  │
│                                                              │
│ Location:                                                    │
│   📁 src/auth/service.py:45-67                              │
│                                                              │
│ Direction: AuthService ──[calls]──> UserModel               │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 개선된 Graph View - 관계 그래프

### 현재 (Before)
- Feature별 그룹화만
- Component 간 관계가 명확하지 않음

### 개선안 (After) - 전체 관계 그래프
```
┌─────────────────────────────────────────────────────────────┐
│ Component Dependency Graph                                   │
│ [Filter: All] [Zone: All] [Status: All]                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│                    ┌─────────────┐                          │
│                    │  Feature:   │                          │
│                    │  Auth       │                          │
│                    └──────┬──────┘                          │
│                           │                                 │
│         ┌─────────────────┼─────────────────┐              │
│         │                 │                 │              │
│    ┌────▼────┐      ┌────▼────┐      ┌────▼────┐          │
│    │Auth     │      │User     │      │Token    │          │
│    │Service  │─────▶│Model    │◀─────│Validator│          │
│    │[class]  │call  │[class]  │dep   │[class]  │          │
│    └────┬────┘      └────┬────┘      └────┬────┘          │
│         │                │                 │                │
│         │                │                 │                │
│    ┌────▼────┐      ┌────▼────┐      ┌────▼────┐          │
│    │Session  │      │Database │      │Cache    │          │
│    │Manager  │─────▶│Adapter  │◀─────│Service  │          │
│    │[class]  │uses  │[class]  │uses  │[class]  │          │
│    └─────────┘      └─────────┘      └─────────┘          │
│                                                              │
│ Legend:                                                      │
│   ──▶ call      ──▶ dependency    ──▶ inheritance          │
│   ● implemented  ○ ghost  ⚠️ drift  ➕ extra                │
│   ⚡ task-1      ✅ task-2                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 개선된 Component 상세 패널 (Inspector 연동)

### Component 선택 시 Inspector에 표시
```
┌─────────────────────────────────────────────────────────────┐
│ Component: AuthService                                       │
├─────────────────────────────────────────────────────────────┤
│ Basic Info:                                                  │
│   Type: class                                                │
│   Status: ● implemented                                      │
│   File: src/auth/service.py:100                             │
│   Module: manifest.auth.service                              │
│   Zone: server                                               │
│                                                              │
│ Metadata:                                                     │
│   Algorithm: -                                               │
│   Design Pattern: Strategy                                   │
│   Complexity: O(n)                                           │
│   Notes: Main authentication service                         │
│                                                              │
│ Methods (8):                                                 │
│   ┌──────────────────────────────────────────────────────┐  │
│   │ login(user: str, password: str) -> Session          │  │
│   │   📁 Line 45-67                                      │  │
│   │   Calls: UserModel.get()                            │  │
│   │   [⚡ task-1]                                        │  │
│   ├──────────────────────────────────────────────────────┤  │
│   │ logout(session_id: str) -> bool                      │  │
│   │   📁 Line 70-85                                      │  │
│   │   Calls: SessionManager.delete()                     │  │
│   │   [✅ task-2]                                        │  │
│   └──────────────────────────────────────────────────────┘  │
│   [+6 more methods]                                          │
│                                                              │
│ Attributes (3):                                              │
│   • _session_store: Dict[str, Session]                      │
│   • _token_validator: TokenValidator                         │
│   • _config: AuthConfig                                      │
│                                                              │
│ Contracts:                                                   │
│   Outgoing (2):                                              │
│     → UserModel (call)                                       │
│     → SessionManager (dependency)                           │
│   Incoming (1):                                              │
│     ← AuthController (call)                                  │
│                                                              │
│ Related Tasks:                                               │
│   ⚡ task-1: Implement login (in_progress)                    │
│   ✅ task-2: Add token validation (done)                     │
│                                                              │
│ [View Source] [View Tests] [View History]                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 확장/축소 인터랙션

### 트리 노드 확장 예시
```
Feature: User Authentication (45%) [▼]
  Requirement: REQ-01 [▼]
    ● AuthService [class] [▼]          ← 클릭하면 확장
      📁 src/auth/service.py:100
      Methods (8) [▼]                   ← 클릭하면 methods 표시
        • login(...)
        • logout(...)
        ...
      Attributes (3) [▼]                ← 클릭하면 attributes 표시
        • _session_store
        ...
      Contracts [▼]                     ← 클릭하면 contracts 표시
        → UserModel
        ...
```

### 축소 상태
```
Feature: User Authentication (45%) [▶]
  Requirement: REQ-01 [▶]
    ● AuthService [class] [▶]
      📁 src/auth/service.py:100
      Methods (8) [▶]
      Attributes (3) [▶]
      Contracts [▶]
```

---

## 📋 개선 사항 요약

### 1. **Component 상세 정보**
- ✅ Type 표시 (class, function, variable)
- ✅ Module path 표시
- ✅ Methods 전체 목록 (expandable)
- ✅ Attributes 전체 목록 (expandable)
- ✅ Method signature 표시

### 2. **Contract 상세 정보**
- ✅ Symbols (어떤 메서드가 관계에 관여하는지)
- ✅ File location (어디서 관계 발생)
- ✅ Data flow 상세 (input/output)
- ✅ 방향성 시각화

### 3. **Graph View 개선**
- ✅ Component 간 관계 그래프
- ✅ Contract 방향성 화살표
- ✅ Zone별 색상 구분
- ✅ Task 연계 표시

### 4. **Inspector 연동**
- ✅ Component 선택 시 상세 정보 표시
- ✅ Methods/Attributes 전체 목록
- ✅ Contracts (incoming/outgoing)
- ✅ Related Tasks

### 5. **인터랙션**
- ✅ Expandable/Collapsible 노드
- ✅ 클릭으로 상세 정보 토글
- ✅ Inspector로 상세 정보 표시

---

## 🎨 구현 우선순위

### Phase 1 (필수)
1. Methods/Attributes 전체 목록 표시 (expandable)
2. Component Type 표시
3. Module Path 표시

### Phase 2 (중요)
1. Contract 상세 정보 (symbols, file)
2. Inspector 연동 (Component 선택 시 상세 표시)

### Phase 3 (개선)
1. Graph View 관계 그래프
2. Contract 방향성 시각화
3. Zone별 색상 구분

---

## 💡 사용자 경험 개선

### Before
- Component 정보가 부족함
- Methods가 5개 이상이면 "+N more"만 표시
- Contract 정보가 너무 간단함
- Component 간 관계가 불명확

### After
- 모든 정보를 확장 가능한 형태로 표시
- 클릭으로 원하는 정보만 볼 수 있음
- Inspector에서 상세 정보 확인 가능
- Component 간 관계가 시각적으로 명확
