"""
Configuration and API key management for Manifest.

This module handles all configuration needs including API key storage,
encryption, validation, and agent model configuration. API keys are
encrypted using Fernet symmetric encryption and stored securely on disk.

The ConfigManager also supports loading API keys from environment variables
as a fallback, and can validate API keys by making test requests to the
respective providers.
"""
import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
import asyncio
import httpx
from manifest.core.logger import get_logger

logger = get_logger(__name__)

# Default settings when .manifest/settings.json is missing.
# OpenCode is the default backend; use agent.execution_backend: "direct" for direct LLM API.
# tool_approval.ask_before_tool_run: when True, state-changing tools require user approval before execution.
DEFAULT_SETTINGS = {
    "agent": {"execution_backend": "opencode"},
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
    """Manages API keys and agent configuration.

    Handles secure storage of API keys using encryption, validation of keys
    against provider APIs, and loading of agent model configurations. API
    keys are stored encrypted on disk and can also be loaded from environment
    variables.

    Attributes:
        manifest_dir: Directory where configuration files are stored.
        keys_file: Path to the encrypted keys file.
        key_file: Path to the encryption key file.
        _cipher: Fernet cipher instance for encryption/decryption.
    """

    def __init__(self, manifest_dir: Path = None):
        """Initialize the configuration manager.

        Sets up the manifest directory and loads or creates the encryption
        key needed for secure API key storage.

        Args:
            manifest_dir: Optional path to the manifest directory. Defaults
                to .manifest in the current directory.
        """
        self.manifest_dir = manifest_dir or Path(".manifest")
        self.keys_file = self.manifest_dir / "keys.json"
        self.key_file = self.manifest_dir / ".key"
        self._cipher = None
        self._load_or_create_key()
        self._ensure_default_settings()

    def _load_or_create_key(self) -> None:
        """Load the encryption key from disk or create a new one.

        If the key file exists, loads it. Otherwise, generates a new Fernet
        key and saves it to disk with restricted permissions (readable only
        by the owner).
        """
        if self.key_file.exists():
            with open(self.key_file, "rb") as f:
                key = f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, "wb") as f:
                f.write(key)
            # Make key file readable only by owner
            os.chmod(self.key_file, 0o600)
        self._cipher = Fernet(key)

    def _ensure_default_settings(self) -> None:
        """Create .manifest/settings.json with default template if it does not exist.

        Defaults use OpenCode as execution backend. Users can edit the file
        or set agent.execution_backend to \"direct\" to use direct LLM API.
        """
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

    def get_api_keys(self) -> Dict[str, Optional[str]]:
        """Get all stored API keys in decrypted form.

        Attempts to load and decrypt the keys file. If the file doesn't exist
        or decryption fails, returns a dictionary with None values for all
        providers. Also checks environment variables as a fallback.

        Returns:
            Dictionary mapping provider names to their API keys. Keys that
            aren't set will be None. Supported providers: anthropic, google,
            openai.
        """
        if not self.keys_file.exists():
            # Check environment variables as fallback
            return {
                "anthropic": os.getenv("ANTHROPIC_API_KEY") or os.getenv("anthropic_api_key"),
                "google": os.getenv("GOOGLE_API_KEY") or os.getenv("google_api_key"),
                "openai": os.getenv("OPENAI_API_KEY") or os.getenv("openai_api_key")
            }

        try:
            with open(self.keys_file, "rb") as f:
                encrypted = f.read()
            decrypted = self._cipher.decrypt(encrypted)
            stored_keys = json.loads(decrypted)

            # Merge with environment variables (env vars take precedence)
            result = {
                "anthropic": os.getenv("ANTHROPIC_API_KEY") or os.getenv("anthropic_api_key") or stored_keys.get("anthropic"),
                "google": os.getenv("GOOGLE_API_KEY") or os.getenv("google_api_key") or stored_keys.get("google"),
                "openai": os.getenv("OPENAI_API_KEY") or os.getenv("openai_api_key") or stored_keys.get("openai")
            }
            return result
        except Exception:
            # If decryption fails, try environment variables
            return {
                "anthropic": os.getenv("ANTHROPIC_API_KEY") or os.getenv("anthropic_api_key"),
                "google": os.getenv("GOOGLE_API_KEY") or os.getenv("google_api_key"),
                "openai": os.getenv("OPENAI_API_KEY") or os.getenv("openai_api_key")
            }

    def save_api_keys(self, keys: Dict[str, str]) -> bool:
        """Save API keys to disk in encrypted form.

        Encrypts the keys dictionary and writes it to the keys file. The file
        is created with restricted permissions (readable only by owner) for
        security.

        Args:
            keys: Dictionary mapping provider names to API key strings.

        Returns:
            True if save was successful, False otherwise. Errors are logged.
        """
        try:
            encrypted = self._cipher.encrypt(json.dumps(keys).encode())
            with open(self.keys_file, "wb") as f:
                f.write(encrypted)
            # Restrict file permissions for security
            os.chmod(self.keys_file, 0o600)
            return True
        except Exception as e:
            logger.error(f"Error saving keys: {e}", exc_info=True)
            return False

    def has_all_keys(self) -> bool:
        """Check if all required API keys are present.

        Returns:
            True if all three required keys (anthropic, google, openai) are
            set and non-empty, False otherwise.
        """
        keys = self.get_api_keys()
        return all(keys.get(k) for k in ["anthropic", "google", "openai"])

    async def validate_key(self, provider: str, key: str) -> bool:
        """Validate an API key by making a test request to the provider.

        Makes a minimal API call to verify the key is valid. Different
        providers use different validation approaches:
        - Anthropic: Makes a test message request (200 or 400 means valid)
        - OpenAI: Lists models endpoint (200 means valid)
        - Google: Currently just checks key is non-empty (placeholder)

        Args:
            provider: Name of the provider ("anthropic", "openai", "google").
            key: API key string to validate.

        Returns:
            True if the key appears to be valid, False otherwise. Returns
            False on any exception (network error, invalid key, etc.).
        """
        try:
            if provider == "anthropic":
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={
                            "x-api-key": key,
                            "anthropic-version": "2023-06-01",
                            "content-type": "application/json"
                        },
                        json={"model": "claude-3-sonnet-20240229", "max_tokens": 10, "messages": [{"role": "user", "content": "test"}]},
                        timeout=5.0
                    )
                    # 400 status means auth worked but request was invalid (key is valid)
                    return response.status_code in [200, 400]
            elif provider == "openai":
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "https://api.openai.com/v1/models",
                        headers={"Authorization": f"Bearer {key}"},
                        timeout=5.0
                    )
                    return response.status_code == 200
            elif provider == "google":
                # Placeholder: Google API validation not fully implemented
                # For now, just check that key is non-empty
                return len(key) > 0
            return False
        except Exception:
            # Any exception means validation failed
            return False

    async def validate_all_keys(self) -> Dict[str, bool]:
        """Validate all stored API keys.

        Checks each provider's key by making test API requests. This can
        take a few seconds as it makes network calls.

        Returns:
            Dictionary mapping provider names to validation results. True
            means the key is valid, False means it's invalid or missing.
        """
        keys = self.get_api_keys()
        results = {}
        for provider, key in keys.items():
            if key:
                results[provider] = await self.validate_key(provider, key)
            else:
                results[provider] = False
        return results

    def _load_agent_config(self) -> Dict[str, Any]:
        """Load agent configuration from the config file.

        Attempts to load agent_config.json from the manifest directory.
        If the file doesn't exist or loading fails, returns the default
        configuration instead.

        Returns:
            Dictionary containing agent model configurations and defaults.
        """
        agent_config_file = self.manifest_dir / "agent_config.json"
        if agent_config_file.exists():
            try:
                with open(agent_config_file, "r") as f:
                    return json.load(f)
            except Exception:
                # If file is corrupted, use defaults
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
        return {
            "version": "1.0",
            "agent_models": {
                "orchestrator": {
                    "provider": "anthropic",
                    "model": "claude-3-5-sonnet-20241022",
                    "use_default_key": True
                },
                "planner": {
                    "provider": "anthropic",
                    "model": "claude-3-5-sonnet-20241022",
                    "use_default_key": True
                },
                "coder": {
                    "provider": "anthropic",
                    "model": "claude-3-5-sonnet-20241022",
                    "use_default_key": True
                },
                "test": {
                    "provider": "openai",
                    "model": "gpt-4-turbo-preview",
                    "use_default_key": True
                },
                "review": {
                    "provider": "anthropic",
                    "model": "claude-3-opus-20240229",
                    "use_default_key": True
                }
            },
            "default_models": {
                "anthropic": "claude-3-5-sonnet-20241022",
                "openai": "gpt-4-turbo-preview",
                "google": "gemini-pro"
            }
        }

    def get_agent_model_config(self, agent_type: str) -> Dict[str, Any]:
        """Get the model configuration for a specific agent type.

        Loads the configuration for the agent, falling back to defaults if
        not specified. Resolves the API key from either the default keys
        or agent-specific encrypted keys, with environment variables as a
        final fallback.

        Args:
            agent_type: Type of agent (e.g., "orchestrator", "planner", "coder").

        Returns:
            Dictionary with "provider", "model", and "api_key" fields. The
            API key will be resolved from the appropriate source based on
            configuration.
        """
        agent_config = self._load_agent_config()
        agent_models = agent_config.get("agent_models", {})

        # Get agent-specific config or use defaults
        if agent_type in agent_models:
            config = agent_models[agent_type].copy()
        else:
            # No specific config for this agent, use provider defaults
            default_models = agent_config.get("default_models", {})
            provider = "anthropic"  # Default provider
            config = {
                "provider": provider,
                "model": default_models.get(provider, "claude-3-5-sonnet-20241022"),
                "use_default_key": True
            }

        # Resolve API key from appropriate source
        if config.get("use_default_key", True):
            # Use the default key for this provider
            keys = self.get_api_keys()
            provider = config["provider"]
            api_key = keys.get(provider)

            # Fallback to environment variable if not in stored keys
            if not api_key:
                env_key = os.getenv(f"{provider.upper()}_API_KEY") or os.getenv(f"{provider}_api_key")
                api_key = env_key
        else:
            # Use agent-specific key (stored encrypted in config)
            api_key = config.get("api_key")
            if api_key:
                # Decrypt the agent-specific key
                try:
                    api_key = self._cipher.decrypt(api_key.encode()).decode()
                except Exception:
                    # If decryption fails, key is invalid
                    api_key = None

        return {
            "provider": config["provider"],
            "model": config["model"],
            "api_key": api_key
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

        Saves the configuration to agent_config.json. If an agent-specific
        API key is provided and use_default_key is False, the key will be
        encrypted before storage.

        Args:
            agent_type: Type of agent to configure (e.g., "orchestrator").
            provider: LLM provider name ("anthropic", "openai", "google").
            model: Model name to use (e.g., "claude-3-5-sonnet-20241022").
            api_key: Optional agent-specific API key. Only used if
                use_default_key is False.
            use_default_key: If True, agent will use the default key for the
                provider. If False, uses the provided api_key.

        Returns:
            True if configuration was saved successfully, False otherwise.
            Errors are logged.
        """
        agent_config = self._load_agent_config()

        if "agent_models" not in agent_config:
            agent_config["agent_models"] = {}

        config = {
            "provider": provider,
            "model": model,
            "use_default_key": use_default_key
        }

        # If agent-specific key provided, encrypt and store
        if api_key and not use_default_key:
            try:
                encrypted_key = self._cipher.encrypt(api_key.encode())
                config["api_key"] = encrypted_key.decode()
            except Exception as e:
                logger.error(f"Error encrypting API key: {e}", exc_info=True)
                return False

        agent_config["agent_models"][agent_type] = config

        # Save to file
        agent_config_file = self.manifest_dir / "agent_config.json"
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
                "provider": config["provider"],
                "model": config["model"]
            }

        # Return default for anthropic
        default_models = agent_config.get("default_models", {})
        return {
            "provider": "anthropic",
            "model": default_models.get("anthropic", "claude-3-5-sonnet-20241022")
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
        except Exception:
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
            except Exception:
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
        agent_config_file = self.manifest_dir / "agent_config.json"
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
        agent_config_file = self.manifest_dir / "agent_config.json"
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
