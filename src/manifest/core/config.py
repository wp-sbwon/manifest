"""
Configuration and API key management for Manifest.
Handles API key bootstrap mode and validation.
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


class ConfigManager:
    """Manages API keys and configuration."""
    
    def __init__(self, manifest_dir: Path = None):
        self.manifest_dir = manifest_dir or Path(".manifest")
        self.keys_file = self.manifest_dir / "keys.json"
        self.key_file = self.manifest_dir / ".key"
        self._cipher = None
        self._load_or_create_key()
    
    def _load_or_create_key(self):
        """Load encryption key or create a new one."""
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
    
    def get_api_keys(self) -> Dict[str, Optional[str]]:
        """Get all API keys (decrypted)."""
        if not self.keys_file.exists():
            return {
                "anthropic": None,
                "google": None,
                "openai": None
            }
        
        try:
            with open(self.keys_file, "rb") as f:
                encrypted = f.read()
            decrypted = self._cipher.decrypt(encrypted)
            return json.loads(decrypted)
        except Exception:
            return {
                "anthropic": None,
                "google": None,
                "openai": None
            }
    
    def save_api_keys(self, keys: Dict[str, str]) -> bool:
        """Save API keys (encrypted)."""
        try:
            encrypted = self._cipher.encrypt(json.dumps(keys).encode())
            with open(self.keys_file, "wb") as f:
                f.write(encrypted)
            os.chmod(self.keys_file, 0o600)
            return True
        except Exception as e:
            logger.error(f"Error saving keys: {e}", exc_info=True)
            return False
    
    def has_all_keys(self) -> bool:
        """Check if all required API keys are present."""
        keys = self.get_api_keys()
        return all(keys.get(k) for k in ["anthropic", "google", "openai"])
    
    async def validate_key(self, provider: str, key: str) -> bool:
        """Validate an API key by making a test request."""
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
                    return response.status_code in [200, 400]  # 400 means auth worked, just bad request
            elif provider == "openai":
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "https://api.openai.com/v1/models",
                        headers={"Authorization": f"Bearer {key}"},
                        timeout=5.0
                    )
                    return response.status_code == 200
            elif provider == "google":
                # Google API validation - simplified check
                return len(key) > 0  # Placeholder - implement actual Google API validation
            return False
        except Exception:
            return False
    
    async def validate_all_keys(self) -> Dict[str, bool]:
        """Validate all stored API keys."""
        keys = self.get_api_keys()
        results = {}
        for provider, key in keys.items():
            if key:
                results[provider] = await self.validate_key(provider, key)
            else:
                results[provider] = False
        return results
    
    def _load_agent_config(self) -> Dict[str, Any]:
        """Load agent configuration from agent_config.json."""
        agent_config_file = self.manifest_dir / "agent_config.json"
        if agent_config_file.exists():
            try:
                with open(agent_config_file, "r") as f:
                    return json.load(f)
            except Exception:
                return self._default_agent_config()
        return self._default_agent_config()
    
    def _default_agent_config(self) -> Dict[str, Any]:
        """Return default agent configuration."""
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
        """Get model configuration for an agent type."""
        agent_config = self._load_agent_config()
        agent_models = agent_config.get("agent_models", {})
        
        # Get agent-specific config or use defaults
        if agent_type in agent_models:
            config = agent_models[agent_type].copy()
        else:
            # Use default for provider (default to anthropic)
            default_models = agent_config.get("default_models", {})
            provider = "anthropic"  # Default provider
            config = {
                "provider": provider,
                "model": default_models.get(provider, "claude-3-5-sonnet-20241022"),
                "use_default_key": True
            }
        
        # Resolve API key
        if config.get("use_default_key", True):
            # Use default key from keys.json
            keys = self.get_api_keys()
            provider = config["provider"]
            api_key = keys.get(provider)
            
            # Fallback to environment variable
            if not api_key:
                env_key = os.getenv(f"{provider.upper()}_API_KEY") or os.getenv(f"{provider}_api_key")
                api_key = env_key
        else:
            # Use agent-specific key (stored in config, encrypted)
            api_key = config.get("api_key")
            if api_key:
                # Decrypt if needed
                try:
                    api_key = self._cipher.decrypt(api_key.encode()).decode()
                except Exception:
                    pass
        
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
        """Set model configuration for an agent type."""
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
                print(f"Error encrypting API key: {e}")
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


# Global config instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get or create the global config manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager