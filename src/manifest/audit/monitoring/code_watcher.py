"""
Update blueprint_code.json from code (extraction + opencode enricher).
"""
from pathlib import Path
from typing import Optional

from manifest.audit.blueprint.blueprint_loader import BlueprintLoader
from manifest.audit.blueprint.manifest_filenames import BLUEPRINT_CODE_FILE
from manifest.audit.blueprint.blueprint_metadata import save_blueprint_with_metadata
from manifest.audit.code.code_extractor import CodeExtractor
from manifest.audit.code.code_blueprint_builder import build_code_blueprint
from manifest.audit.entity_validation import validate_blueprint_data
from manifest.core.logger import get_logger

logger = get_logger(__name__)

CODE_EXTENSIONS = (".py",)


class CodeWatcher:
    """Update blueprint_code.json from code via extraction and opencode enricher."""

    def __init__(
        self,
        project_root: Optional[Path] = None,
        manifest_dir: Optional[Path] = None,
    ):
        self.project_root = (project_root or Path.cwd()).resolve()
        self.manifest_dir = (manifest_dir or (self.project_root / ".manifest")).resolve()
        self._last_code_mtime: Optional[float] = None

    def _max_mtime_under(self, directory: Path, extensions: tuple) -> float:
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
        design_file = self.manifest_dir / "blueprint_design.json"
        if not design_file.exists():
            logger.error("blueprint_design.json missing; bottom-up requires design")
            return False

        current_mtime = self._max_mtime_under(self.project_root, CODE_EXTENSIONS)
        if current_mtime == 0.0:
            return False
        if self._last_code_mtime is not None and current_mtime <= self._last_code_mtime:
            return False
        self._last_code_mtime = current_mtime

        try:
            design = BlueprintLoader.load_blueprint(self.manifest_dir)
            extractor = CodeExtractor(self.project_root)
            extracted = extractor.extract_project_structure(self.project_root)
            code_blueprint = build_code_blueprint(
                self.project_root, self.manifest_dir, design, extracted
            )
            valid, errors = validate_blueprint_data(code_blueprint)
            if not valid and errors:
                logger.error("Code blueprint validation failed: %s", errors)
                return False
            self.manifest_dir.mkdir(parents=True, exist_ok=True)
            blueprint_file = self.manifest_dir / BLUEPRINT_CODE_FILE
            if not save_blueprint_with_metadata(
                code_blueprint, blueprint_file, "code_extraction", True, "ast_parsing"
            ):
                return False
            logger.info("Updated %s", blueprint_file)
            return True
        except Exception as e:
            logger.error("CodeWatcher build/save failed: %s", e, exc_info=True)
            return False

    def force_extract(self) -> bool:
        prev = self._last_code_mtime
        self._last_code_mtime = None
        try:
            return self.watch_and_extract()
        finally:
            if self._last_code_mtime is None and prev is not None:
                self._last_code_mtime = prev
