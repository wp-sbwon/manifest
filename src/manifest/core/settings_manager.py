"""
Settings Manager - Unified interface for all Manifest settings.
Manages API keys, agent models, skills, and policy files.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from manifest.core.config import ConfigManager
from manifest.agents.skills_manager import SkillsManager


class SettingsManager:
    """Unified settings management for Manifest."""
    
    def __init__(self, manifest_dir: Path = None, project_root: Path = None):
        """
        Initialize Settings Manager.
        
        Args:
            manifest_dir: .manifest directory path
            project_root: Project root directory
        """
        self.manifest_dir = manifest_dir or Path(".manifest")
        self.project_root = project_root or Path.cwd()
        self.config_manager = ConfigManager(self.manifest_dir)
        self.skills_manager = SkillsManager(self.manifest_dir, self.project_root)
        
        # File paths
        self.policy_file = self.project_root / ".claude" / "rules" / "manifest-policy.md"
        self.agents_md_file = self.project_root / "AGENTS.md"
    
    # API Keys Management
    def get_api_keys(self) -> Dict[str, Optional[str]]:
        """Get all API keys."""
        return self.config_manager.get_api_keys()
    
    def save_api_keys(self, keys: Dict[str, str]) -> bool:
        """Save API keys."""
        return self.config_manager.save_api_keys(keys)
    
    async def validate_key(self, provider: str, key: str) -> bool:
        """Validate an API key."""
        return await self.config_manager.validate_key(provider, key)
    
    # Agent Model Configuration
    def get_all_agent_models(self) -> Dict[str, Dict[str, Any]]:
        """Get all agent model configurations."""
        agent_types = ["orchestrator", "planner", "coder", "test", "review"]
        models = {}
        for agent_type in agent_types:
            config = self.config_manager.get_agent_model_config(agent_type)
            models[agent_type] = {
                "provider": config["provider"],
                "model": config["model"],
                "use_default_key": True  # Simplified - actual config may differ
            }
        return models
    
    def get_agent_model(self, agent_type: str) -> Dict[str, Any]:
        """Get model configuration for a specific agent."""
        config = self.config_manager.get_agent_model_config(agent_type)
        return {
            "provider": config["provider"],
            "model": config["model"]
        }
    
    def set_agent_model(
        self,
        agent_type: str,
        provider: str,
        model: str,
        use_default_key: bool = True
    ) -> bool:
        """Set model configuration for an agent."""
        return self.config_manager.set_agent_model_config(
            agent_type, provider, model, None, use_default_key
        )
    
    def get_default_models(self) -> Dict[str, str]:
        """Get default models per provider."""
        agent_config = self.config_manager._load_agent_config()
        return agent_config.get("default_models", {
            "anthropic": "claude-3-5-sonnet-20241022",
            "openai": "gpt-4-turbo-preview",
            "google": "gemini-pro"
        })
    
    def set_default_model(self, provider: str, model: str) -> bool:
        """Set default model for a provider."""
        agent_config = self.config_manager._load_agent_config()
        if "default_models" not in agent_config:
            agent_config["default_models"] = {}
        agent_config["default_models"][provider] = model
        
        agent_config_file = self.manifest_dir / "agent_config.json"
        try:
            self.manifest_dir.mkdir(parents=True, exist_ok=True)
            with open(agent_config_file, "w") as f:
                json.dump(agent_config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving default models: {e}")
            return False
    
    # Agent Skills Management
    def get_agent_skills(self) -> Dict[str, List[str]]:
        """Get agent default skills."""
        return self.skills_manager._agent_skills.copy()
    
    def set_agent_skills(self, agent_type: str, skill_ids: List[str]) -> bool:
        """Set skills for an agent type."""
        agent_config = self.config_manager._load_agent_config()
        if "agent_skills" not in agent_config:
            agent_config["agent_skills"] = {}
        agent_config["agent_skills"][agent_type] = skill_ids
        
        agent_config_file = self.manifest_dir / "agent_config.json"
        try:
            self.manifest_dir.mkdir(parents=True, exist_ok=True)
            with open(agent_config_file, "w") as f:
                json.dump(agent_config, f, indent=2)
            # Reload skills manager
            self.skills_manager._load_agent_default_skills()
            return True
        except Exception as e:
            print(f"Error saving agent skills: {e}")
            return False
    
    def get_project_skills(self) -> List[Dict[str, Any]]:
        """Get project-scoped skills from AGENTS.md."""
        return self.skills_manager._project_skills.copy()
    
    def get_skill_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get all skill definitions."""
        return self.skills_manager._skill_definitions.copy()
    
    def get_skill_content(self, skill_id: str) -> Optional[str]:
        """Get content of a skill file."""
        return self.skills_manager.get_skill_content(skill_id)
    
    def save_skill_file(self, skill_id: str, content: str) -> bool:
        """Save a skill file to .claude/rules/."""
        skill_file = self.claude_rules_dir / f"{skill_id}.md"
        try:
            self.claude_rules_dir.mkdir(parents=True, exist_ok=True)
            with open(skill_file, "w", encoding="utf-8") as f:
                f.write(content)
            # Reload skill definitions
            self.skills_manager._load_skill_definitions()
            return True
        except Exception as e:
            print(f"Error saving skill file: {e}")
            return False
    
    @property
    def claude_rules_dir(self) -> Path:
        """Get .claude/rules directory."""
        return self.project_root / ".claude" / "rules"
    
    # Policy Management
    def get_policy_content(self) -> str:
        """Get manifest-policy.md content."""
        if self.policy_file.exists():
            try:
                with open(self.policy_file, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                return f"Error reading policy: {e}"
        return ""
    
    def save_policy_content(self, content: str) -> bool:
        """Save manifest-policy.md content."""
        try:
            self.policy_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.policy_file, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"Error saving policy: {e}")
            return False
    
    # AGENTS.md Management
    def get_agents_md_content(self) -> str:
        """Get AGENTS.md content."""
        if self.agents_md_file.exists():
            try:
                with open(self.agents_md_file, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                return f"Error reading AGENTS.md: {e}"
        return ""
    
    def save_agents_md_content(self, content: str) -> bool:
        """Save AGENTS.md content."""
        try:
            with open(self.agents_md_file, "w", encoding="utf-8") as f:
                f.write(content)
            # Reload project skills
            self.skills_manager._load_project_skills()
            return True
        except Exception as e:
            print(f"Error saving AGENTS.md: {e}")
            return False
    
    # Validation
    def validate_settings(self) -> Dict[str, Any]:
        """Validate all settings."""
        errors = []
        warnings = []
        
        # Validate API keys
        keys = self.get_api_keys()
        for provider, key in keys.items():
            if not key:
                warnings.append(f"API key for {provider} is not set")
        
        # Validate agent models
        models = self.get_all_agent_models()
        for agent_type, config in models.items():
            if not config.get("provider") or not config.get("model"):
                errors.append(f"Agent {agent_type} is missing provider or model")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    # Get all settings (for UI display)
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings as a dictionary."""
        return {
            "api_keys": {
                provider: key[:4] + "..." if key and len(key) > 4 else "Not set"
                for provider, key in self.get_api_keys().items()
            },
            "agent_models": self.get_all_agent_models(),
            "default_models": self.get_default_models(),
            "agent_skills": self.get_agent_skills(),
            "project_skills": self.get_project_skills(),
            "policy_exists": self.policy_file.exists(),
            "agents_md_exists": self.agents_md_file.exists()
        }
