"""Application temp directory for pipeline artifacts (enrich inputs, etc.)."""
import os
import tempfile
from pathlib import Path


def get_manifest_tmp_dir() -> Path:
    """
    Return the manifest app temp root. Prefer MANIFEST_TMP_DIR if set; otherwise
    use system temp (respects TMPDIR/TEMP/TMP) with a 'manifest' subdir.
    """
    base = os.environ.get("MANIFEST_TMP_DIR")
    if base:
        root = Path(base).resolve()
    else:
        root = Path(tempfile.gettempdir()) / "manifest"
    root.mkdir(parents=True, exist_ok=True)
    return root
