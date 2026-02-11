"""
Configuration for Manifest.

Model selection and API keys are managed by OpenCode (default execution backend).
This module handles settings (settings.json), agent model config (provider/model
overrides in agent_config.json), and permissions. No API key storage or validation.
"""
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any

from manifest.core.logger import get_logger

logger = get_logger(__name__)

from manifest.core.constants import CONTAINER_API_PORT, AGENT_CONFIG_FILE

# Default settings when .manifest/settings.json is missing.
# tool_approval.ask_before_tool_run: when True, state-changing tools require user approval before execution.
DEFAULT_SETTINGS = {
    "agent": {"execution_backend": "opencode"},
    "container_api": {"port": CONTAINER_API_PORT},
    "opencode": {
        "server_host": "localhost",
        "server_port": 4096,
        "auto_start": True,
    },
    "tool_approval": {"ask_before_tool_run": False},
    "resource_limits": {
        "tokens_per_day": None,
        "model": None,
        "cost_limit": None,
    },
}


class ConfigManager:
    """Manages settings and agent model configuration.

    Handles settings.json, agent_config.json (provider/model per agent), and
    permissions. API keys are managed by OpenCode; this class does not store
    or validate keys.

    Attributes:
        manifest_dir: Directory where configuration files are stored.
    """

    def __init__(self, manifest_dir: Path = None):
        """Initialize the configuration manager.

        Args:
            manifest_dir: Optional path to the manifest directory. Defaults
                to .manifest in the current directory.
        """
        self.manifest_dir = manifest_dir or Path(".manifest")
        self._ensure_default_settings()

    def _ensure_default_settings(self) -> None:
        """Create .manifest/settings.json with default template if it does not exist."""
        settings_file = self.manifest_dir / "settings.json"
        if settings_file.exists():
            return
        try:
            self.manifest_dir.mkdir(parents=True, exist_ok=True)
            with open(settings_file, "w") as f:
                json.dump(DEFAULT_SETTINGS, f, indent=2)
            logger.debug("Created default settings.json in %s", self.manifest_dir)
        except Exception as e:
            logger.debug("Could not create default settings.json: %s", e)

    def _load_agent_config(self) -> Dict[str, Any]:
        """Load agent configuration from the config file.

        Attempts to load agent_config.json from the manifest directory.
        If the file doesn't exist or loading fails, returns the default
        configuration instead.

        Returns:
            Dictionary containing agent model configurations and defaults.
        """
        agent_config_file = self.manifest_dir / AGENT_CONFIG_FILE
        if agent_config_file.exists():
            try:
                with open(agent_config_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.debug("_load_agent_config failed, using defaults: %s", e)
                return self._default_agent_config()
        return self._default_agent_config()

    def _default_agent_config(self) -> Dict[str, Any]:
        """Return the default agent configuration structure.

        Provides sensible defaults for all agent types and provider models.
        This is used when no configuration file exists or when loading fails.

        Returns:
            Dictionary with default agent model configurations and provider
            default models.
        """
        # No hardcoded model IDs: use OpenCode's default unless user configures one.
        # Available models are defined by OpenCode/providers, not maintained by us.
        return {
            "version": "1.0",
            "agent_models": {
                "orchestrator": {"provider": "anthropic", "use_default_key": True},
                "planner": {"provider": "anthropic", "use_default_key": True},
                "coder": {"provider": "anthropic", "use_default_key": True},
                "test": {"provider": "openai", "use_default_key": True},
                "review": {"provider": "anthropic", "use_default_key": True}
            },
            "default_models": {}
        }

    def get_agent_model_config(self, agent_type: str) -> Dict[str, Any]:
        """Get the model configuration for a specific agent type.

        OpenCode manages API keys; this returns provider and model only (api_key always None).

        Args:
            agent_type: Type of agent (e.g., "orchestrator", "planner", "coder").

        Returns:
            Dictionary with "provider", "model", and "api_key" (None). OpenCode uses its own keys.
        """
        agent_config = self._load_agent_config()
        agent_models = agent_config.get("agent_models", {})

        if agent_type in agent_models:
            config = agent_models[agent_type].copy()
        else:
            default_models = agent_config.get("default_models", {}) or {}
            config = {
                "provider": "anthropic",
                "model": default_models.get("anthropic"),
            }

        return {
            "provider": config.get("provider", "anthropic"),
            "model": config.get("model"),
            "api_key": None,
        }

    def set_agent_model_config(
        self,
        agent_type: str,
        provider: str,
        model: str,
        api_key: Optional[str] = None,
        use_default_key: bool = True
    ) -> bool:
        """Set the model configuration for a specific agent type.

        Saves provider and model to agent_config.json. API keys are managed by OpenCode; api_key is ignored.

        Args:
            agent_type: Type of agent to configure (e.g., "orchestrator").
            provider: LLM provider name ("anthropic", "openai", "google").
            model: Model name to use.
            api_key: Ignored (OpenCode manages keys).
            use_default_key: Ignored (kept for signature compatibility).

        Returns:
            True if configuration was saved successfully, False otherwise.
        """
        agent_config = self._load_agent_config()

        if "agent_models" not in agent_config:
            agent_config["agent_models"] = {}

        agent_config["agent_models"][agent_type] = {
            "provider": provider,
            "model": model,
        }

        # Save to file
        agent_config_file = self.manifest_dir / AGENT_CONFIG_FILE
        try:
            self.manifest_dir.mkdir(parents=True, exist_ok=True)
            with open(agent_config_file, "w") as f:
                json.dump(agent_config, f, indent=2)
            os.chmod(agent_config_file, 0o600)
            return True
        except Exception as e:
            logger.error(f"Error saving agent config: {e}", exc_info=True)
            return False

    def get_default_model_for_agent(self, agent_type: str) -> Dict[str, str]:
        """Get default model configuration for agent type."""
        agent_config = self._load_agent_config()
        agent_models = agent_config.get("agent_models", {})

        if agent_type in agent_models:
            config = agent_models[agent_type]
            return {
                "provider": config.get("provider", "anthropic"),
                "model": config.get("model")
            }

        default_models = agent_config.get("default_models", {}) or {}
        return {
            "provider": "anthropic",
            "model": default_models.get("anthropic")
        }

    def get_agent_permissions(self, agent_type: str) -> Dict[str, Any]:
        """Get permissions for a specific agent type.

        Loads agent-specific permissions from agent_config.json. If no
        agent-specific permissions are set, returns an empty dictionary.

        Args:
            agent_type: Type of agent (e.g., "coder", "planner").

        Returns:
            Dictionary containing permission configuration for the agent.
        """
        agent_config = self._load_agent_config()
        permissions_config = agent_config.get("agent_permissions", {})
        agent_config_section = permissions_config.get("agent", {})
        return agent_config_section.get(agent_type, {})

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value by key.

        Settings are stored in a settings.json file in the manifest directory.
        Supports dot notation for nested keys (e.g., "agent.execution_backend").

        Args:
            key: Setting key, supports dot notation for nested access.
            default: Default value if setting not found.

        Returns:
            Setting value or default if not found.
        """
        settings_file = self.manifest_dir / "settings.json"
        if not settings_file.exists():
            return default

        try:
            with open(settings_file, "r") as f:
                settings = json.load(f)
        except Exception as e:
            logger.debug("get_setting load failed: %s", e)
            return default

        # Support dot notation
        keys = key.split(".")
        value = settings
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value if value is not None else default

    def set_setting(self, key: str, value: Any) -> bool:
        """Set a setting value by key.

        Settings are stored in a settings.json file in the manifest directory.
        Supports dot notation for nested keys (e.g., "agent.execution_backend").

        Args:
            key: Setting key, supports dot notation for nested access.
            value: Value to set.

        Returns:
            True if successful, False otherwise.
        """
        settings_file = self.manifest_dir / "settings.json"

        # Load existing settings
        settings = {}
        if settings_file.exists():
            try:
                with open(settings_file, "r") as f:
                    settings = json.load(f)
            except Exception as e:
                logger.debug("set_setting load failed: %s", e)
                settings = {}

        # Set nested value using dot notation
        keys = key.split(".")
        current = settings
        for k in keys[:-1]:
            if k not in current or not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value

        # Save settings
        try:
            self.manifest_dir.mkdir(parents=True, exist_ok=True)
            with open(settings_file, "w") as f:
                json.dump(settings, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving setting: {e}", exc_info=True)
            return False

    def set_agent_permissions(
        self,
        agent_type: str,
        permissions: Dict[str, Any]
    ) -> bool:
        """Set permissions for a specific agent type.

        Saves the permissions configuration to agent_config.json under
        agent_permissions.agent.{agent_type}.

        Args:
            agent_type: Type of agent to configure.
            permissions: Dictionary containing permission configuration.
                Should have a "permission" key with permission rules.

        Returns:
            True if configuration was saved successfully, False otherwise.
        """
        agent_config = self._load_agent_config()

        if "agent_permissions" not in agent_config:
            agent_config["agent_permissions"] = {}

        if "agent" not in agent_config["agent_permissions"]:
            agent_config["agent_permissions"]["agent"] = {}

        agent_config["agent_permissions"]["agent"][agent_type] = permissions

        # Save to file
        agent_config_file = self.manifest_dir / AGENT_CONFIG_FILE
        try:
            self.manifest_dir.mkdir(parents=True, exist_ok=True)
            with open(agent_config_file, "w") as f:
                json.dump(agent_config, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving agent permissions: {e}", exc_info=True)
            return False

    def get_global_permissions(self) -> Dict[str, Any]:
        """Get global permissions configuration.

        Returns:
            Dictionary containing global permission configuration.
        """
        agent_config = self._load_agent_config()
        permissions_config = agent_config.get("agent_permissions", {})
        return permissions_config.get("global", {})

    def set_global_permissions(self, permissions: Dict[str, Any]) -> bool:
        """Set global permissions configuration.

        Args:
            permissions: Dictionary containing global permission configuration.
                Should have a "permission" key with permission rules.

        Returns:
            True if configuration was saved successfully, False otherwise.
        """
        agent_config = self._load_agent_config()

        if "agent_permissions" not in agent_config:
            agent_config["agent_permissions"] = {}

        agent_config["agent_permissions"]["global"] = permissions

        # Save to file
        agent_config_file = self.manifest_dir / AGENT_CONFIG_FILE
        try:
            self.manifest_dir.mkdir(parents=True, exist_ok=True)
            with open(agent_config_file, "w") as f:
                json.dump(agent_config, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving global permissions: {e}", exc_info=True)
            return False


# Global config instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get or create the global ConfigManager instance.

    Provides a singleton pattern for accessing the configuration manager
    throughout the application. The instance is created on first call and
    reused for subsequent calls.

    Returns:
        The global ConfigManager instance.
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
