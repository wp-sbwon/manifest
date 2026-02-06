"""
Code Watcher: watch code changes and update blueprint_code.json.

When code files change, runs CodeExtractor and writes .manifest/blueprint_code.json.
View watches that file and refreshes Blueprint/Drift views in real time.
"""
from pathlib import Path
from typing import Optional
from datetime import datetime

from manifest.audit.code.code_extractor import CodeExtractor
from manifest.core.logger import get_logger

logger = get_logger(__name__)

CODE_EXTENSIONS = (".py",)


class CodeWatcher:
    """Watch code changes and trigger blueprint_code.json update."""

    def __init__(
        self,
        project_root: Optional[Path] = None,
        manifest_dir: Optional[Path] = None,
    ):
        self.project_root = (project_root or Path.cwd()).resolve()
        self.manifest_dir = (manifest_dir or (self.project_root / ".manifest")).resolve()
        self._last_code_mtime: Optional[float] = None

    def _max_mtime_under(self, directory: Path, extensions: tuple) -> float:
        """Return the latest mtime of files under directory with given extensions."""
        try:
            max_mtime = 0.0
            for path in directory.rglob("*"):
                if path.is_file() and path.suffix in extensions:
                    if "venv" in path.parts or "__pycache__" in path.parts:
                        continue
                    if any(part.startswith(".") and part not in (".", "..") for part in path.parts):
                        continue
                    try:
                        mtime = path.stat().st_mtime
                        if mtime > max_mtime:
                            max_mtime = mtime
                    except OSError:
                        pass
            return max_mtime
        except Exception as e:
            logger.debug("CodeWatcher mtime scan failed: %s", e)
            return 0.0

    def watch_and_extract(self) -> bool:
        """Check for code changes and update blueprint_code.json if needed.

        Returns:
            True if blueprint_code.json was updated, False otherwise.
        """
        current_mtime = self._max_mtime_under(self.project_root, CODE_EXTENSIONS)
        if current_mtime == 0.0:
            return False
        if self._last_code_mtime is not None and current_mtime <= self._last_code_mtime:
            return False
        self._last_code_mtime = current_mtime

        try:
            extractor = CodeExtractor(self.project_root)
            blueprint = extractor.extract_project_structure(self.project_root)
            self.manifest_dir.mkdir(parents=True, exist_ok=True)
            from manifest.audit.blueprint.manifest_filenames import BLUEPRINT_CODE_FILE
            blueprint_file = self.manifest_dir / BLUEPRINT_CODE_FILE
            extractor.save_blueprint(blueprint, blueprint_file)
            logger.info("Updated %s from code changes", blueprint_file)
            return True
        except Exception as e:
            logger.error("CodeWatcher extract/save failed: %s", e, exc_info=True)
            return False

    def force_extract(self) -> bool:
        """Force re-extraction and update of blueprint_code.json (ignore mtime)."""
        prev = self._last_code_mtime
        self._last_code_mtime = None
        try:
            return self.watch_and_extract()
        finally:
            if self._last_code_mtime is None and prev is not None:
                self._last_code_mtime = prev
