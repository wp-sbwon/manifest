# Bootstrap UI 이벤트 루프 충돌 문제 설명

## 문제 개요

Bootstrap UI가 별도의 Textual 앱으로 실행되면서 발생하는 이벤트 루프 충돌 문제입니다.

---

## 현재 코드 구조

### 실행 흐름

```python
# src/manifest/__main__.py
if __name__ == "__main__":
    config = get_config_manager()
    if not config.has_all_keys():
        # 1. BootstrapApp 실행 (첫 번째 Textual 앱)
        run_bootstrap()  # ⚠️ 이벤트 루프 시작

    # 2. ManifestApp 실행 (두 번째 Textual 앱)
    app = ManifestApp()
    app.run()  # ⚠️ 또 다른 이벤트 루프 시작
```

### BootstrapApp 구조

```python
# src/manifest/ui/bootstrap_ui.py
class BootstrapApp(App):  # Textual의 App 상속
    """Bootstrap mode TUI for configuring API keys."""
    # ... UI 구성 ...

    async def on_save(self) -> None:
        # ... 키 검증 및 저장 ...
        self.exit(True)  # 앱 종료

def run_bootstrap() -> bool:
    """Run bootstrap mode and return True if keys were configured."""
    app = BootstrapApp()
    return app.run()  # ⚠️ Textual의 이벤트 루프 시작
```

---

## 문제의 핵심

### 1. Textual App의 이벤트 루프 동작

Textual의 `App.run()` 메서드는:
- **자체 이벤트 루프를 시작**합니다
- 앱이 종료될 때까지 **블로킹**됩니다
- 앱 종료 시 이벤트 루프를 정리합니다

### 2. 연속 실행 시 문제

같은 프로세스에서 두 개의 Textual 앱을 연속으로 실행하면:

```
프로세스 시작
  ↓
BootstrapApp.run() 호출
  ↓
[이벤트 루프 1 시작]
  ├─ UI 렌더링
  ├─ 사용자 입력 처리
  └─ BootstrapApp.exit() 호출
  ↓
[이벤트 루프 1 종료 시도]
  ⚠️ 이벤트 루프가 완전히 정리되지 않을 수 있음
  ↓
ManifestApp.run() 호출
  ↓
[이벤트 루프 2 시작 시도]
  ⚠️ 이전 이벤트 루프의 리소스가 남아있을 수 있음
  ⚠️ 충돌 가능성
```

### 3. 실제 발생 가능한 문제

1. **이벤트 루프 리소스 충돌**
   - 첫 번째 앱의 이벤트 루프가 완전히 정리되지 않음
   - 두 번째 앱이 시작할 때 리소스 충돌 발생 가능

2. **비동기 작업 충돌**
   - `BootstrapApp`에서 시작된 비동기 작업이 남아있을 수 있음
   - `ManifestApp`의 비동기 작업과 충돌 가능

3. **터미널 상태 충돌**
   - Textual은 터미널 상태를 관리함
   - 첫 번째 앱이 터미널 상태를 변경한 후 정리되지 않으면 두 번째 앱에 영향

---

## 현재 해결책의 한계

### 주석의 의도

```python
# This runs in its own event loop and finishes before ManifestApp starts
run_bootstrap()
```

주석은 "자체 이벤트 루프에서 실행되고 ManifestApp 시작 전에 끝난다"고 하지만, 실제로는:

1. ✅ **블로킹 실행**: `run_bootstrap()`가 완료된 후 `ManifestApp` 시작
2. ⚠️ **이벤트 루프 정리**: 완전히 정리되지 않을 수 있음
3. ⚠️ **리소스 정리**: Textual의 내부 리소스가 남아있을 수 있음

### 데모 모드 우회

현재는 키가 없으면 데모 모드로 진행하므로 문제가 드러나지 않을 수 있지만, Bootstrap UI를 실제로 사용할 때 문제가 발생할 수 있습니다.

---

## 해결 방안

### 방안 1: 별도 프로세스로 실행 (권장)

```python
# src/manifest/__main__.py
import subprocess
import sys

if __name__ == "__main__":
    config = get_config_manager()
    if not config.has_all_keys():
        # 별도 프로세스로 Bootstrap UI 실행
        result = subprocess.run([
            sys.executable, "-m", "manifest.bootstrap"
        ])
        if result.returncode != 0:
            sys.exit(1)

    # 메인 앱 실행
    app = ManifestApp()
    app.run()
```

**장점**:
- 완전히 독립된 프로세스로 실행
- 이벤트 루프 충돌 없음
- 리소스 정리 보장

**단점**:
- 프로세스 오버헤드
- 별도 진입점 필요

### 방안 2: ManifestApp 내부 위젯으로 통합 (권장)

```python
# src/manifest/ui/app.py
class ManifestApp(App):
    def compose(self) -> ComposeResult:
        # ... 기존 UI ...

        # API 키가 없으면 Bootstrap 화면 표시
        if not self.config.has_all_keys():
            yield BootstrapScreen()  # 위젯으로 통합

    async def on_mount(self) -> None:
        if not self.config.has_all_keys():
            # Bootstrap 화면에 포커스
            self.push_screen(BootstrapScreen())
```

**장점**:
- 단일 이벤트 루프 사용
- 자연스러운 화면 전환
- 리소스 충돌 없음

**단점**:
- ManifestApp 초기화 필요 (일부 리소스 낭비 가능)

### 방안 3: 이벤트 루프 명시적 정리

```python
# src/manifest/ui/bootstrap_ui.py
def run_bootstrap() -> bool:
    """Run bootstrap mode and return True if keys were configured."""
    app = BootstrapApp()
    result = app.run()

    # 이벤트 루프 명시적 정리
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 실행 중인 작업 정리
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
    except Exception:
        pass

    return result
```

**장점**:
- 최소한의 변경
- 기존 구조 유지

**단점**:
- 완전한 정리 보장 어려움
- 복잡한 비동기 작업 처리 필요

---

## 권장 해결책

**방안 2 (ManifestApp 내부 위젯으로 통합)**를 권장합니다:

1. **단일 이벤트 루프**: 충돌 없음
2. **자연스러운 UX**: 화면 전환으로 사용자 경험 개선
3. **코드 일관성**: 모든 UI가 하나의 앱에서 관리

---

## 테스트 방법

문제를 재현하려면:

```bash
# 1. API 키 제거
rm .manifest/keys.json

# 2. 앱 실행
PYTHONPATH=src python -m manifest

# 3. Bootstrap UI에서 키 입력 후 저장
# 4. ManifestApp 시작 시 오류 확인
```

예상되는 오류:
- `RuntimeError: This event loop is already running`
- `RuntimeError: There is no current event loop`
- 터미널 상태 오류
- 화면 렌더링 오류

---

## 참고

- Textual 문서: [App.run()](https://textual.textualize.io/api/app/#textual.app.App.run)
- Python asyncio: [Event Loop](https://docs.python.org/3/library/asyncio-eventloop.html)
