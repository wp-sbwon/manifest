"""
Tests for SettingsManager.
"""
import json
import pytest
from pathlib import Path
from manifest.core.settings_manager import SettingsManager


@pytest.fixture
def tmp_manifest_dir(tmp_path):
    """Create temporary .manifest directory."""
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir()
    return manifest_dir


@pytest.fixture
def tmp_project_root(tmp_path):
    """Create temporary project root."""
    claude_dir = tmp_path / ".claude" / "rules"
    claude_dir.mkdir(parents=True)
    return tmp_path


@pytest.fixture
def sample_agent_config(tmp_manifest_dir):
    """Create sample agent_config.json."""
    config = {
        "version": "1.0",
        "agent_models": {
            "coder": {
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
                "use_default_key": True
            }
        },
        "agent_skills": {
            "coder": ["skill1"],
            "planner": []
        }
    }
    config_file = tmp_manifest_dir / "agent_config.json"
    with open(config_file, "w") as f:
        json.dump(config, f)
    return config_file


@pytest.fixture
def sample_policy_file(tmp_project_root):
    """Create sample manifest-policy.md."""
    policy_file = tmp_project_root / ".claude" / "rules" / "manifest-policy.md"
    policy_file.write_text("# Manifest Policy\n\nTest policy content.")
    return policy_file


def test_settings_manager_init(tmp_manifest_dir, tmp_project_root):
    """Test SettingsManager initialization."""
    manager = SettingsManager(tmp_manifest_dir, tmp_project_root)
    assert manager.manifest_dir == tmp_manifest_dir
    assert manager.project_root == tmp_project_root


def test_get_api_keys(tmp_manifest_dir, tmp_project_root):
    """Test getting API keys."""
    manager = SettingsManager(tmp_manifest_dir, tmp_project_root)
    keys = manager.get_api_keys()
    assert isinstance(keys, dict)
    assert "anthropic" in keys
    assert "openai" in keys
    assert "google" in keys


def test_save_api_keys(tmp_manifest_dir, tmp_project_root):
    """Test saving API keys."""
    manager = SettingsManager(tmp_manifest_dir, tmp_project_root)
    keys = {
        "anthropic": "test-key-1",
        "openai": "test-key-2",
        "google": "test-key-3"
    }
    result = manager.save_api_keys(keys)
    assert result is True
    
    # Verify keys were saved
    loaded_keys = manager.get_api_keys()
    assert loaded_keys["anthropic"] == "test-key-1"
    assert loaded_keys["openai"] == "test-key-2"
    assert loaded_keys["google"] == "test-key-3"


def test_get_all_agent_models(tmp_manifest_dir, tmp_project_root, sample_agent_config):
    """Test getting all agent models."""
    manager = SettingsManager(tmp_manifest_dir, tmp_project_root)
    models = manager.get_all_agent_models()
    assert isinstance(models, dict)
    assert "coder" in models
    assert models["coder"]["provider"] == "anthropic"


def test_set_agent_model(tmp_manifest_dir, tmp_project_root):
    """Test setting agent model."""
    manager = SettingsManager(tmp_manifest_dir, tmp_project_root)
    result = manager.set_agent_model("coder", "openai", "gpt-4")
    assert result is True
    
    # Verify model was set
    model = manager.get_agent_model("coder")
    assert model["provider"] == "openai"
    assert model["model"] == "gpt-4"


def test_get_agent_skills(tmp_manifest_dir, tmp_project_root, sample_agent_config):
    """Test getting agent skills."""
    manager = SettingsManager(tmp_manifest_dir, tmp_project_root)
    skills = manager.get_agent_skills()
    assert isinstance(skills, dict)
    assert "coder" in skills
    assert "skill1" in skills["coder"]


def test_set_agent_skills(tmp_manifest_dir, tmp_project_root):
    """Test setting agent skills."""
    manager = SettingsManager(tmp_manifest_dir, tmp_project_root)
    result = manager.set_agent_skills("coder", ["skill1", "skill2"])
    assert result is True
    
    # Verify skills were set
    skills = manager.get_agent_skills()
    assert "skill1" in skills["coder"]
    assert "skill2" in skills["coder"]


def test_get_policy_content(tmp_manifest_dir, tmp_project_root, sample_policy_file):
    """Test getting policy content."""
    manager = SettingsManager(tmp_manifest_dir, tmp_project_root)
    content = manager.get_policy_content()
    assert "Manifest Policy" in content
    assert "Test policy content" in content


def test_save_policy_content(tmp_manifest_dir, tmp_project_root):
    """Test saving policy content."""
    manager = SettingsManager(tmp_manifest_dir, tmp_project_root)
    new_content = "# New Policy\n\nUpdated content."
    result = manager.save_policy_content(new_content)
    assert result is True
    
    # Verify content was saved
    content = manager.get_policy_content()
    assert "New Policy" in content
    assert "Updated content" in content


def test_get_agents_md_content(tmp_manifest_dir, tmp_project_root):
    """Test getting AGENTS.md content."""
    agents_md = tmp_project_root / "AGENTS.md"
    agents_md.write_text("# AGENTS.md\n\nTest content.")
    
    manager = SettingsManager(tmp_manifest_dir, tmp_project_root)
    content = manager.get_agents_md_content()
    assert "AGENTS.md" in content


def test_save_agents_md_content(tmp_manifest_dir, tmp_project_root):
    """Test saving AGENTS.md content."""
    manager = SettingsManager(tmp_manifest_dir, tmp_project_root)
    new_content = "# AGENTS.md\n\n## Skills\n\n### Skill: test"
    result = manager.save_agents_md_content(new_content)
    assert result is True
    
    # Verify content was saved
    content = manager.get_agents_md_content()
    assert "test" in content


def test_validate_settings(tmp_manifest_dir, tmp_project_root):
    """Test settings validation."""
    manager = SettingsManager(tmp_manifest_dir, tmp_project_root)
    validation = manager.validate_settings()
    assert "valid" in validation
    assert "errors" in validation
    assert "warnings" in validation
    assert isinstance(validation["errors"], list)
    assert isinstance(validation["warnings"], list)


def test_get_all_settings(tmp_manifest_dir, tmp_project_root):
    """Test getting all settings."""
    manager = SettingsManager(tmp_manifest_dir, tmp_project_root)
    all_settings = manager.get_all_settings()
    assert isinstance(all_settings, dict)
    assert "api_keys" in all_settings
    assert "agent_models" in all_settings
    assert "agent_skills" in all_settings
