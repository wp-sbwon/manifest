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
    """Non-transient RuntimeError (e.g. invalid JSON from opencode stdout) raises immediately, no retry."""
    from manifest.opencode.code_blueprint_enricher import enrich_code_blueprint

    design = _valid_blueprint()
    draft = _valid_blueprint()

    # opencode --format json stdout: one text part with invalid JSON
    bad_stdout = '{"type":"text","part":{"text":"not valid json {"}}\n'
    mock_result = MagicMock(returncode=0, stdout=bad_stdout, stderr="")

    with patch("shutil.which", return_value="/fake/opencode"):
        with patch("manifest.opencode.code_blueprint_enricher.subprocess.run", return_value=mock_result):
            with pytest.raises(RuntimeError, match="invalid JSON"):
                enrich_code_blueprint(design, draft, tmp_path, tmp_path)


def test_enricher_retries_on_exit_code_then_raises(tmp_path):
    """Transient 'exited with code' is retried; after max retries, raises."""
    from manifest.opencode.code_blueprint_enricher import enrich_code_blueprint

    design = _valid_blueprint()
    draft = _valid_blueprint()
    mock_result = MagicMock(returncode=1, stdout="err", stderr="")

    with patch("shutil.which", return_value="/fake/opencode"):
        with patch("manifest.opencode.code_blueprint_enricher.subprocess.run", return_value=mock_result) as mock_run:
            with patch("time.sleep"):
                with pytest.raises(RuntimeError, match="exited with code"):
                    enrich_code_blueprint(design, draft, tmp_path, tmp_path)
    assert mock_run.call_count == 3


def test_enricher_no_retry_on_non_transient_runtime_error(tmp_path):
    """RuntimeError without 'exited with code' (e.g. no response) raises immediately, no retry."""
    from manifest.opencode.code_blueprint_enricher import enrich_code_blueprint

    design = _valid_blueprint()
    draft = _valid_blueprint()
    # opencode returns success but no text parts -> "No response from opencode"
    mock_result = MagicMock(returncode=0, stdout="\n", stderr="")

    with patch("shutil.which", return_value="/fake/opencode"):
        with patch("manifest.opencode.code_blueprint_enricher.subprocess.run", return_value=mock_result) as mock_run:
            with pytest.raises(RuntimeError, match="No response"):
                enrich_code_blueprint(design, draft, tmp_path, tmp_path)
    assert mock_run.call_count == 1
