"""
Default path helpers and path validation.

Single place for manifest_dir / project_root defaults and for validating
that user- or config-derived paths stay under an allowed base.
"""
from pathlib import Path
from typing import Optional


def default_manifest_dir(manifest_dir: Optional[Path] = None) -> Path:
    """Return manifest_dir if set, else .manifest under cwd. Always resolved."""
    if manifest_dir is not None:
        return Path(manifest_dir).resolve()
    return (Path.cwd() / ".manifest").resolve()


def is_path_under_base(path: Path, base: Path) -> bool:
    """Return True if resolved path is under base (or equal). Rejects escapes like .. and symlinks outside base."""
    try:
        resolved = path.resolve()
        base_resolved = base.resolve()
        resolved.relative_to(base_resolved)
        return True
    except (OSError, RuntimeError, ValueError):
        return False
