"""Tests for manifest.opencode.layer_writer."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from manifest.audit.entity_schema import PROJECT_ROOT_ID, empty_entity
from manifest.io.blueprint_io import save_blueprint
from manifest.opencode.layer_writer import (
    build_layer_writer_context,
    merge_children_into_blueprint,
    try_spawn_next_layer,
    write_blueprint_layer,
    _path_from_root,
    _sibling_ids,
)


@pytest.fixture
def tmp_manifest(tmp_path):
    """Create manifest dir with root-only blueprint and minimal PRD."""
    (tmp_path / "prd.json").write_text(
        json.dumps({"title": "Test", "sections": [{"id": "s1", "name": "Section 1"}]}),
        encoding="utf-8",
    )
    root = {
        **empty_entity(PROJECT_ROOT_ID),
        "id": PROJECT_ROOT_ID,
        "children": [],
        "intent": {"narrative": {"role": "Root", "mission": "Test mission"}},
    }
    blueprint = {"version": "1.0", "root_id": PROJECT_ROOT_ID, "entities": [root]}
    save_blueprint(tmp_path, blueprint)
    return tmp_path


def test_path_from_root_single():
    bp = {"entities": [{**empty_entity(PROJECT_ROOT_ID), "id": PROJECT_ROOT_ID, "children": ["a"]}, {**empty_entity("a"), "id": "a", "children": []}]}
    assert _path_from_root(bp, PROJECT_ROOT_ID) == [PROJECT_ROOT_ID]
    assert _path_from_root(bp, "a") == [PROJECT_ROOT_ID, "a"]


def test_path_from_root_nested():
    bp = {
        "entities": [
            {**empty_entity(PROJECT_ROOT_ID), "id": PROJECT_ROOT_ID, "children": ["parent"]},
            {**empty_entity("parent"), "id": "parent", "children": ["child"]},
            {**empty_entity("child"), "id": "child", "children": []},
        ]
    }
    assert _path_from_root(bp, "child") == [PROJECT_ROOT_ID, "parent", "child"]


def test_sibling_ids():
    bp = {
        "entities": [
            {**empty_entity(PROJECT_ROOT_ID), "id": PROJECT_ROOT_ID, "children": ["a", "b", "c"]},
            {**empty_entity("a"), "id": "a", "children": []},
            {**empty_entity("b"), "id": "b", "children": []},
            {**empty_entity("c"), "id": "c", "children": []},
        ]
    }
    assert set(_sibling_ids(bp, "a")) == {"b", "c"}
    assert set(_sibling_ids(bp, "b")) == {"a", "c"}


def test_build_layer_writer_context_root(tmp_manifest):
    ctx = build_layer_writer_context(tmp_manifest, PROJECT_ROOT_ID, 0)
    assert ctx["layer_index"] == 0
    assert ctx["parent_entity"]["id"] == PROJECT_ROOT_ID
    assert ctx["blueprint_excerpt"]["path_from_root"] == [PROJECT_ROOT_ID]
    assert ctx["blueprint_excerpt"]["sibling_ids"] == []
    assert ctx["prd_excerpt"]["title"] == "Test"


def test_build_layer_writer_context_missing_parent(tmp_manifest):
    with pytest.raises(ValueError, match="not found"):
        build_layer_writer_context(tmp_manifest, "nonexistent", 1)


def test_merge_children_into_blueprint(tmp_manifest):
    children = [
        {**empty_entity("child1"), "id": "child1", "children": []},
        {**empty_entity("child2"), "id": "child2", "children": []},
    ]
    assert merge_children_into_blueprint(tmp_manifest, PROJECT_ROOT_ID, children)

    from manifest.io.blueprint_io import load_blueprint
    bp = load_blueprint(tmp_manifest)
    root = next(e for e in bp["entities"] if e["id"] == PROJECT_ROOT_ID)
    assert set(root["children"]) == {"child1", "child2"}
    ids = {e["id"] for e in bp["entities"]}
    assert "child1" in ids and "child2" in ids


def test_write_blueprint_layer_stub_returns_empty(tmp_manifest):
    """Stub mode returns empty children without calling opencode."""
    ctx = {"layer_index": 1, "parent_entity": {"id": "p"}, "prd_excerpt": {}, "blueprint_excerpt": {}}
    with patch.dict("os.environ", {"MANIFEST_LAYER_WRITER_STUB": "1"}):
        result = write_blueprint_layer(ctx, tmp_manifest.parent, tmp_manifest)
    assert result["children"] == []


def test_write_blueprint_layer_returns_new_dicts_not_mutated(tmp_manifest):
    """When opencode returns children in stdout, we build new dicts instead of mutating parsed objects."""
    from unittest.mock import MagicMock

    ctx = {"layer_index": 1, "parent_entity": {"id": "p"}, "prd_excerpt": {}, "blueprint_excerpt": {}}
    # opencode --format json stdout: one text part with children JSON
    payload = json.dumps({"children": [{"id": "c1", "intent": {}}]})
    opencode_stdout = json.dumps({"type": "text", "part": {"text": payload}}) + "\n"
    mock_result = MagicMock(returncode=0, stdout=opencode_stdout, stderr="")

    with patch("shutil.which", return_value="/fake/opencode"):
        with patch("manifest.opencode.layer_writer.subprocess.run", return_value=mock_result):
            result = write_blueprint_layer(ctx, tmp_manifest.parent, tmp_manifest)
    assert len(result["children"]) == 1
    assert result["children"][0]["id"] == "c1"


def test_try_spawn_next_layer_max_depth_logs(tmp_manifest, caplog):
    """When max_depth reached, logs and returns empty (no spawn)."""
    children = [{**empty_entity("c1"), "id": "c1"}]
    with patch("subprocess.Popen"):
        out = try_spawn_next_layer(
            tmp_manifest, tmp_manifest.parent, "root", 0, children, max_depth=0
        )
    assert out == []
    assert "max_depth" in caplog.text or "layer" in caplog.text.lower()


def test_try_spawn_next_layer_spawns_subprocess(tmp_manifest):
    """Spawn calls Popen with script, manifest-dir, parent, layer."""
    children = [{**empty_entity("c1"), "id": "c1"}]
    with patch("subprocess.Popen") as mock_popen:
        try_spawn_next_layer(tmp_manifest, tmp_manifest.parent, "root", 0, children)
    mock_popen.assert_called()
    call_args = mock_popen.call_args[0][0]
    assert "--parent" in call_args
    assert "c1" in call_args
    assert "--layer" in call_args
    assert "1" in call_args
