"""Tests for manifest.opencode.code_blueprint_enricher."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_entity


def _valid_blueprint():
    root = {**empty_entity(PROJECT_ROOT_ID), "id": PROJECT_ROOT_ID, "children": []}
    return {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [root]}


def test_enricher_raises_on_opencode_not_found(tmp_path):
    """When opencode not on PATH, raises RuntimeError (no silent None)."""
    from manifest.opencode.code_blueprint_enricher import enrich_code_blueprint

    design = _valid_blueprint()
    draft = _valid_blueprint()
    with patch("shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="not on PATH"):
            enrich_code_blueprint(design, draft, tmp_path, tmp_path)


def test_enricher_raises_immediately_on_invalid_json(tmp_path):
    """Non-transient RuntimeError (e.g. invalid JSON) raises immediately, no retry."""
    from manifest.opencode.code_blueprint_enricher import enrich_code_blueprint

    design = _valid_blueprint()
    draft = _valid_blueprint()

    def run(cmd, **kwargs):
        out = kwargs.get("env", {}).get("MANIFEST_ENRICH_OUTPUT", "")
        if out:
            Path(out).parent.mkdir(parents=True, exist_ok=True)
            Path(out).write_text("not valid json {", encoding="utf-8")
        m = MagicMock()
        m.returncode = 0
        return m

    with patch("shutil.which", return_value="/fake/opencode"):
        with patch("subprocess.run", side_effect=run):
            with pytest.raises(RuntimeError, match="invalid JSON"):
                enrich_code_blueprint(design, draft, tmp_path, tmp_path)


def test_enricher_retries_on_exit_code_then_raises(tmp_path):
    """Transient 'exited with code' is retried; after max retries, raises."""
    from manifest.opencode.code_blueprint_enricher import enrich_code_blueprint

    design = _valid_blueprint()
    draft = _valid_blueprint()
    call_count = 0

    def run(cmd, **kwargs):
        nonlocal call_count
        call_count += 1
        raise RuntimeError("opencode enrich-code-blueprint exited with code 1. Last output: x")

    with patch("shutil.which", return_value="/fake/opencode"):
        with patch("subprocess.run", side_effect=run):
            with patch("time.sleep"):
                with pytest.raises(RuntimeError, match="exited with code"):
                    enrich_code_blueprint(design, draft, tmp_path, tmp_path)
    assert call_count == 3


def test_enricher_no_retry_on_non_transient_runtime_error(tmp_path):
    """RuntimeError without 'exited with code' raises immediately, no retry."""
    from manifest.opencode.code_blueprint_enricher import enrich_code_blueprint

    design = _valid_blueprint()
    draft = _valid_blueprint()
    call_count = 0

    def run(cmd, **kwargs):
        nonlocal call_count
        call_count += 1
        raise RuntimeError("opencode did not write enriched blueprint")

    with patch("shutil.which", return_value="/fake/opencode"):
        with patch("subprocess.run", side_effect=run):
            with pytest.raises(RuntimeError, match="did not write"):
                enrich_code_blueprint(design, draft, tmp_path, tmp_path)
    assert call_count == 1
