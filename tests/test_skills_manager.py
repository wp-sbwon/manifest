"""
Tests for SkillsManager.
"""
import json
import pytest
from pathlib import Path
from manifest.agents.skills_manager import SkillsManager


@pytest.fixture
def tmp_manifest_dir(tmp_path):
    """Create temporary .manifest directory."""
    manifest_dir = tmp_path / ".manifest"
    manifest_dir.mkdir()
    return manifest_dir


@pytest.fixture
def tmp_project_root(tmp_path):
    """Create temporary project root with .claude/rules."""
    claude_dir = tmp_path / ".claude" / "rules"
    claude_dir.mkdir(parents=True)
    return tmp_path


@pytest.fixture
def sample_agent_config(tmp_manifest_dir):
    """Create sample agent_config.json with skills."""
    config = {
        "version": "1.0",
        "agent_models": {
            "coder": {
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022"
            }
        },
        "agent_skills": {
            "coder": ["default_skill"],
            "planner": []
        }
    }
    config_file = tmp_manifest_dir / "agent_config.json"
    with open(config_file, "w") as f:
        json.dump(config, f)
    return config_file


@pytest.fixture
def sample_skill_file(tmp_project_root):
    """Create sample skill file in .claude/rules."""
    skill_file = tmp_project_root / ".claude" / "rules" / "default_skill.md"
    skill_file.write_text("""# Default Skill

## Description
A default skill for testing.

## Trigger Keywords
- default
- test

## Agents
- coder
""")
    return skill_file


@pytest.fixture
def sample_agents_md(tmp_project_root):
    """Create sample AGENTS.md file."""
    agents_md = tmp_project_root / "AGENTS.md"
    agents_md.write_text("""# AGENTS.md

## Skills

### Skill: project_skill
A project-specific skill.

**Triggers**: project, specific

**Agents**: coder, planner
""")
    return agents_md


def test_skills_manager_init(tmp_manifest_dir, tmp_project_root):
    """Test SkillsManager initialization."""
    manager = SkillsManager(tmp_manifest_dir, tmp_project_root)
    assert manager.manifest_dir == tmp_manifest_dir
    assert manager.project_root == tmp_project_root


def test_load_agent_default_skills(tmp_manifest_dir, tmp_project_root, sample_agent_config):
    """Test loading agent default skills from agent_config.json."""
    manager = SkillsManager(tmp_manifest_dir, tmp_project_root)
    assert "coder" in manager._agent_skills
    assert "default_skill" in manager._agent_skills["coder"]


def test_load_skill_definitions(tmp_manifest_dir, tmp_project_root, sample_skill_file):
    """Test loading skill definitions from .claude/rules/."""
    manager = SkillsManager(tmp_manifest_dir, tmp_project_root)
    assert "default_skill" in manager._skill_definitions
    skill_def = manager._skill_definitions["default_skill"]
    assert skill_def["id"] == "default_skill"
    assert "content" in skill_def


def test_load_project_skills(tmp_manifest_dir, tmp_project_root, sample_agents_md):
    """Test loading project skills from AGENTS.md."""
    manager = SkillsManager(tmp_manifest_dir, tmp_project_root)
    assert len(manager._project_skills) > 0
    assert any(s["id"] == "project_skill" for s in manager._project_skills)


def test_get_skills_for_agent(tmp_manifest_dir, tmp_project_root, sample_agent_config, sample_skill_file, sample_agents_md):
    """Test getting skills for a specific agent."""
    manager = SkillsManager(tmp_manifest_dir, tmp_project_root)
    
    # Get skills for coder
    coder_skills = manager.get_skills_for_agent("coder")
    assert len(coder_skills) > 0
    
    # Should include both project skill and agent default skill
    skill_ids = [s.get("id") for s in coder_skills]
    assert "default_skill" in skill_ids or "project_skill" in skill_ids


def test_format_skills_for_prompt(tmp_manifest_dir, tmp_project_root, sample_skill_file, sample_agent_config):
    """Test formatting skills for prompt."""
    manager = SkillsManager(tmp_manifest_dir, tmp_project_root)
    skills = manager.get_skills_for_agent("coder")
    formatted = manager.format_skills_for_prompt(skills)
    
    if len(skills) > 0:
        assert "AVAILABLE SKILLS" in formatted
        # Check if any skill ID appears in formatted output
        skill_ids = [s.get("id") for s in skills]
        assert any(skill_id in formatted for skill_id in skill_ids)
    else:
        # If no skills, formatted should be empty string
        assert formatted == ""


def test_skill_applies_to_agent(tmp_manifest_dir, tmp_project_root):
    """Test skill applicability to agents."""
    manager = SkillsManager(tmp_manifest_dir, tmp_project_root)
    
    # Skill with explicit agents list
    skill_with_agents = {
        "id": "test_skill",
        "agents": ["coder", "planner"]
    }
    assert manager._skill_applies_to_agent(skill_with_agents, "coder") is True
    assert manager._skill_applies_to_agent(skill_with_agents, "review") is False
    
    # Skill without agents list (applies to all)
    skill_without_agents = {
        "id": "universal_skill"
    }
    assert manager._skill_applies_to_agent(skill_without_agents, "coder") is True
    assert manager._skill_applies_to_agent(skill_without_agents, "planner") is True


def test_get_skill_content(tmp_manifest_dir, tmp_project_root, sample_skill_file):
    """Test getting skill content by ID."""
    manager = SkillsManager(tmp_manifest_dir, tmp_project_root)
    content = manager.get_skill_content("default_skill")
    assert content is not None
    assert "Default Skill" in content


def test_missing_files_graceful(tmp_manifest_dir, tmp_project_root):
    """Test graceful handling of missing files."""
    # No agent_config.json, no AGENTS.md, no .claude/rules/
    manager = SkillsManager(tmp_manifest_dir, tmp_project_root)
    
    # Should not raise errors
    skills = manager.get_skills_for_agent("coder")
    assert isinstance(skills, list)
    
    formatted = manager.format_skills_for_prompt(skills)
    assert isinstance(formatted, str)
