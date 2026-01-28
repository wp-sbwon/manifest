"""
View File Watcher: watch .manifest/ files for real-time View sync.

Polls key files in .manifest/ and invokes a callback when any change is
detected. Used by ManifestViewApp to refresh Task/Blueprint/Drift views
when tasks.json, blueprint_code.json, state.json, or conflicts change.
"""
from pathlib import Path
from typing import Callable, Dict, List, Optional

from manifest.core.logger import get_logger

logger = get_logger(__name__)

# Key files/dirs we watch (relative to manifest_dir)
WATCH_FILES = ("tasks.json", "state.json", "blueprint_code.json", "blueprint.json", "architecture.json")
WATCH_DIR = "conflicts"


class ViewFileWatcher:
    """Watch .manifest/ directory for file changes; callback on change."""

    def __init__(
        self,
        manifest_dir: Path,
        on_change: Callable[[List[Path]], None],
    ):
        self.manifest_dir = Path(manifest_dir).resolve()
        self.on_change = on_change
        self._last_mtimes: Dict[Path, float] = {}

    def _get_mtime(self, path: Path) -> float:
        """Return mtime of path, or 0 if missing."""
        try:
            if path.exists():
                return path.stat().st_mtime
        except OSError:
            pass
        return 0.0

    def check(self) -> List[Path]:
        """Check for changes; return list of changed paths. Calls on_change if any."""
        changed: List[Path] = []
        for name in WATCH_FILES:
            path = self.manifest_dir / name
            mtime = self._get_mtime(path)
            prev = self._last_mtimes.get(path, None)
            self._last_mtimes[path] = mtime
            if prev is not None and mtime != prev:
                changed.append(path)
            elif prev is None and mtime > 0:
                # First run: don't treat as "change"
                pass

        conflicts_dir = self.manifest_dir / WATCH_DIR
        if conflicts_dir.is_dir():
            try:
                for f in conflicts_dir.iterdir():
                    if f.is_file():
                        mtime = self._get_mtime(f)
                        prev = self._last_mtimes.get(f, None)
                        self._last_mtimes[f] = mtime
                        if prev is not None and mtime != prev:
                            changed.append(f)
            except OSError:
                pass
        else:
            key = conflicts_dir
            prev = self._last_mtimes.get(key, None)
            self._last_mtimes[key] = 0.0
            if prev is not None and prev != 0.0:
                changed.append(key)

        if changed:
            try:
                self.on_change(changed)
            except Exception as e:
                logger.debug("ViewFileWatcher on_change error: %s", e)
        return changed
