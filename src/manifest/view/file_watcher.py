"""
Invoke callback when .manifest/ files change. Uses filesystem events.
"""
import threading
from pathlib import Path
from typing import Callable, List, Optional, Set

from manifest.audit.blueprint.manifest_filenames import (
    BLUEPRINT_CODE_FILE,
    BLUEPRINT_DESIGN_FILE,
    BLUEPRINT_VIEW_FILE,
)
from manifest.core.constants import STATE_FILE, DESIGN_HISTORY_FILE
from manifest.core.logger import get_logger

logger = get_logger(__name__)

WATCH_FILES = (STATE_FILE, BLUEPRINT_CODE_FILE, BLUEPRINT_DESIGN_FILE, BLUEPRINT_VIEW_FILE, DESIGN_HISTORY_FILE)
WATCH_DIR = "conflicts"

DEBOUNCE_SECONDS = 0.15


class ViewFileWatcher:
    """Invoke callback when files in .manifest/ change."""

    def __init__(
        self,
        manifest_dir: Path,
        on_change: Callable[[List[Path]], None],
    ):
        self.manifest_dir = Path(manifest_dir).resolve()
        self.on_change = on_change
        self._observer = None
        self._lock = threading.Lock()
        self._collected: Set[Path] = set()
        self._debounce_timer: Optional[threading.Timer] = None

    def _watched_paths(self) -> Set[Path]:
        out: Set[Path] = set()
        for name in WATCH_FILES:
            out.add(self.manifest_dir / name)
        out.add(self.manifest_dir / WATCH_DIR)
        return out

    def _is_watched(self, path: Path) -> bool:
        try:
            path = path.resolve()
        except OSError:
            return False
        if path in self._watched_paths():
            return True
        try:
            path.relative_to(self.manifest_dir / WATCH_DIR)
            return True
        except ValueError:
            pass
        return False

    def _schedule_callback(self) -> None:
        with self._lock:
            if not self._collected:
                return
            paths = list(self._collected)
            self._collected.clear()
            self._debounce_timer = None
        try:
            self.on_change(paths)
        except Exception as e:
            logger.debug("ViewFileWatcher on_change error: %s", e)

    def _debounce(self, path: Path) -> None:
        with self._lock:
            self._collected.add(path)
            if self._debounce_timer is not None:
                self._debounce_timer.cancel()
            self._debounce_timer = threading.Timer(DEBOUNCE_SECONDS, self._schedule_callback)
            self._debounce_timer.daemon = True
            self._debounce_timer.start()

    def start(self) -> None:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent

        class Handler(FileSystemEventHandler):
            def __init__(self, outer: ViewFileWatcher):
                self._outer = outer

            def _handle(self, event: object) -> None:
                if getattr(event, "is_directory", False):
                    return
                src = getattr(event, "src_path", None)
                if not src:
                    return
                path = Path(src).resolve()
                if self._outer._is_watched(path):
                    self._outer._debounce(path)

            def on_modified(self, event: FileModifiedEvent) -> None:
                self._handle(event)

            def on_created(self, event: FileCreatedEvent) -> None:
                self._handle(event)

        self._observer = Observer()
        self._observer.schedule(Handler(self), str(self.manifest_dir), recursive=True)
        self._observer.start()

    def stop(self) -> None:
        with self._lock:
            if self._debounce_timer is not None:
                self._debounce_timer.cancel()
                self._debounce_timer = None
            self._collected.clear()
        if self._observer is not None:
            try:
                self._observer.stop()
                self._observer.join(timeout=2.0)
            except Exception as e:
                logger.debug("ViewFileWatcher stop: %s", e)
            self._observer = None
