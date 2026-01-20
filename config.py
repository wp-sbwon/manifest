"""
Configuration and API key management for Manifest.
Handles API key bootstrap mode and validation.
"""
import json
import os
from pathlib import Path
from typing import Optional, Dict
from cryptography.fernet import Fernet
import asyncio
import httpx


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
            print(f"Error saving keys: {e}")
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


# Global config instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get or create the global config manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager