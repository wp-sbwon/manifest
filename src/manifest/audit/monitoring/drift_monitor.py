"""
Drift Monitor: drift detection driven by task done or commit.

Integrates with CodeWatcher: call check_and_update() to refresh blueprint_code.json
from code. View runs it once on mount and when a task becomes completed; commits
trigger run_bottom_up_docs (which also updates blueprint_code.json). No timer interval.
"""
from pathlib import Path
from typing import Optional, Callable

from manifest.audit.monitoring.code_watcher import CodeWatcher
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class DriftMonitor:
    """Monitor drift in real-time by driving CodeWatcher."""

    def __init__(
        self,
        project_root: Optional[Path] = None,
        manifest_dir: Optional[Path] = None,
        on_drift_updated: Optional[Callable[[], None]] = None,
    ):
        self.project_root = (project_root or Path.cwd()).resolve()
        self.manifest_dir = (manifest_dir or (self.project_root / ".manifest")).resolve()
        self._code_watcher = CodeWatcher(
            project_root=self.project_root,
            manifest_dir=self.manifest_dir,
        )
        self.on_drift_updated = on_drift_updated
        self._running = False

    def check_and_update(self) -> bool:
        """Check for code changes and update blueprint_code.json if needed.

        When blueprint_code.json is updated, View's file watcher will
        detect the change and refresh Blueprint/Drift views.

        Returns:
            True if blueprint_code.json was updated, False otherwise.
        """
        updated = self._code_watcher.watch_and_extract()
        if updated and self.on_drift_updated:
            try:
                self.on_drift_updated()
            except Exception as e:
                logger.debug("DriftMonitor on_drift_updated callback error: %s", e)
        return updated

    def start_monitoring(self, interval_seconds: float = 10.0):
        """Start periodic drift monitoring.

        Call check_and_update() on the given interval. Intended to be
        used with a scheduler (e.g. set_interval in View) or background
        thread; this method only sets _running and does not block.
        """
        self._running = True
        logger.info(
            "DriftMonitor started (interval=%.1fs); use check_and_update() on a timer",
            interval_seconds,
        )

    def stop_monitoring(self) -> None:
        """Stop periodic monitoring."""
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running
