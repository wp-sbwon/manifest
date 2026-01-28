"""
Manifest View - 상시 시각화 전용 UI (MVP).

채팅은 OpenCode에서 하고, blueprint·구조·drift·태스크는 이 View에서 상시 표시.
MVP는 간단한 Textual 앱. 추후 Electron 앱으로 전환 예정.
"""
from manifest.view.app import ManifestViewApp

__all__ = ["ManifestViewApp"]
