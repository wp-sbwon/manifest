"""
Unit tests for context_provider.py
"""
import pytest
import json
from pathlib import Path
from manifest.agents.context_provider import ContextProvider
from manifest.agents.task_scoper import TaskScoper


@pytest.fixture
def temp_manifest_dir(tmp_path):
    """Create temporary manifest directory with test data."""
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir()
    
    # Create blueprint.json
    blueprint = {
        "version": "1.0",
        "zones": {},
        "components": [
            {"id": "comp-1", "name": "TestComponent"}
        ],
        "contracts": []
    }
    with open(manifest_dir / "blueprint.json", "w") as f:
        json.dump(blueprint, f)
    
    # Create intent.json
    intent = {
        "version": "1.0",
        "sprint": "Test Sprint",
        "features": []
    }
    with open(manifest_dir / "intent.json", "w") as f:
        json.dump(intent, f)
    
    # Create architecture.json
    architecture = {
        "version": "1.0",
        "features": [],
        "requirements": [],
        "goals": []
    }
    with open(manifest_dir / "architecture.json", "w") as f:
        json.dump(architecture, f)
    
    # Create policy file
    policy_dir = tmp_path / ".claude" / "rules"
    policy_dir.mkdir(parents=True)
    with open(policy_dir / "manifest-policy.md", "w") as f:
        f.write("# Test Policy\n\nTest content")
    
    return manifest_dir


def test_context_provider_init(temp_manifest_dir):
    """Test ContextProvider initialization."""
    provider = ContextProvider(temp_manifest_dir)
    assert provider.manifest_dir == temp_manifest_dir


def test_get_orchestrator_context(temp_manifest_dir):
    """Test getting orchestrator context."""
    provider = ContextProvider(temp_manifest_dir)
    context = provider.get_orchestrator_context()
    
    assert context["tier"] == "orchestrator"
    assert "tier_0" in context
    assert "tier_1" in context
    assert "intent" in context["tier_1"]
    assert "architecture" in context["tier_1"]


def test_get_worker_context(temp_manifest_dir):
    """Test getting worker context."""
    provider = ContextProvider(temp_manifest_dir)
    context = provider.get_worker_context("task-1", "sisyphus")
    
    assert context["tier"] == "worker"
    assert context["task_id"] == "task-1"
    assert context["agent_type"] == "sisyphus"
    assert "tier_0" in context
    assert "tier_2" in context
    assert "tier_3" in context
    assert "task_scope" in context


def test_load_tier_0(temp_manifest_dir, tmp_path):
    """Test loading Tier 0 (policy)."""
    import os
    # ContextProvider uses Path(".claude/rules/manifest-policy.md") which is relative to CWD
    # So we need to change to tmp_path directory
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        provider = ContextProvider(temp_manifest_dir)
        tier_0 = provider._load_tier_0()
        
        assert tier_0["source"] == ".claude/rules/manifest-policy.md"
        assert "content" in tier_0
        assert "Test content" in tier_0["content"]
    finally:
        os.chdir(original_cwd)


def test_get_context_summary(temp_manifest_dir):
    """Test getting context summary."""
    provider = ContextProvider(temp_manifest_dir)
    context = provider.get_orchestrator_context()
    summary = provider.get_context_summary(context)
    
    assert "tier" in summary
    assert summary["tier"] == "orchestrator"