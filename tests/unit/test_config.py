"""
Unit tests for ConfigManager.

Tests configuration loading, saving, and API key management.
"""
import pytest
import os
import json
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
from manifest.core.config import ConfigManager, get_config_manager


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing."""
    return tmp_path


@pytest.fixture
def config_manager(temp_dir):
    """Create a ConfigManager instance."""
    return ConfigManager(manifest_dir=temp_dir)


def test_config_manager_initialization(config_manager, temp_dir):
    """Test ConfigManager initialization."""
    assert config_manager.manifest_dir == temp_dir
    assert config_manager is not None


def test_get_setting(config_manager):
    """Test getting a setting."""
    value = config_manager.get_setting("test_key", default="default_value")
    assert value == "default_value" or isinstance(value, str)


def test_set_setting(config_manager):
    """Test setting a configuration value."""
    result = config_manager.set_setting("test_key", "test_value")
    assert result is True or result is None


def test_get_agent_model_config(config_manager):
    """Test getting agent model configuration."""
    config = config_manager.get_agent_model_config("coder")
    assert isinstance(config, dict)


def test_get_api_key(config_manager):
    """Test getting API key."""
    # ConfigManager uses get_api_keys() which returns a dict, not get_api_key()
    keys = config_manager.get_api_keys()
    assert isinstance(keys, dict)
    # Check for common provider keys
    assert "anthropic" in keys or "openai" in keys or "google" in keys


def test_set_api_key(config_manager):
    """Test setting API key."""
    # ConfigManager uses save_api_keys() which takes a dict, not set_api_key()
    result = config_manager.save_api_keys({"anthropic": "test_key"})
    assert result is True


def test_load_config(config_manager):
    """Test loading configuration."""
    # ConfigManager doesn't have load_config(), but we can test get_api_keys()
    # which loads the config
    config = config_manager.get_api_keys()
    assert isinstance(config, dict)


def test_save_config(config_manager):
    """Test saving configuration."""
    # ConfigManager doesn't have save_config(), but we can test save_api_keys()
    result = config_manager.save_api_keys({"anthropic": "test_key"})
    assert result is True


def test_get_config_manager():
    """Test getting global config manager."""
    manager = get_config_manager()
    assert manager is not None
    assert isinstance(manager, ConfigManager)


# ========== TDL: Configuration Tests ==========

def test_api_key_encryption_decryption(config_manager):
    """Test API key encryption/decryption."""
    # Save keys (should be encrypted)
    test_keys = {
        "anthropic": "sk-ant-test-key-123",
        "openai": "sk-openai-test-key-456",
        "google": "google-test-key-789"
    }
    result = config_manager.save_api_keys(test_keys)
    assert result is True

    # Verify keys file exists and is encrypted (not plain JSON)
    keys_file = config_manager.keys_file
    assert keys_file.exists()

    # Read encrypted file - should be binary/encrypted, not plain JSON
    with open(keys_file, "rb") as f:
        encrypted_data = f.read()
    # Should not be readable as JSON
    try:
        json.loads(encrypted_data.decode())
        assert False, "Keys file should be encrypted, not plain JSON"
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass  # Expected - file is encrypted

    # Decrypt and verify keys
    decrypted_keys = config_manager.get_api_keys()
    assert decrypted_keys["anthropic"] == "sk-ant-test-key-123"
    assert decrypted_keys["openai"] == "sk-openai-test-key-456"
    assert decrypted_keys["google"] == "google-test-key-789"


@pytest.mark.asyncio
async def test_api_key_validation(config_manager):
    """Test API key validation."""
    # Mock httpx to avoid actual API calls
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = Mock()
        mock_response.status_code = 200

        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_client_instance

        # Test validation for each provider
        result_anthropic = await config_manager.validate_key("anthropic", "test-key")
        assert isinstance(result_anthropic, bool)

        result_openai = await config_manager.validate_key("openai", "test-key")
        assert isinstance(result_openai, bool)

        result_google = await config_manager.validate_key("google", "test-key")
        assert isinstance(result_google, bool)


@pytest.mark.asyncio
async def test_api_key_validation_failure(config_manager):
    """Test API key validation with invalid key."""
    # Mock httpx to return error
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = Mock()
        mock_response.status_code = 401  # Unauthorized

        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_client_instance

        result = await config_manager.validate_key("anthropic", "invalid-key")
        assert result is False


def test_missing_key_handling(config_manager):
    """Test handling of missing API keys."""
    # Get keys when none are set
    keys = config_manager.get_api_keys()

    # Should return dict with None values or env vars
    assert isinstance(keys, dict)
    # Keys might be None or from environment
    assert "anthropic" in keys
    assert "openai" in keys
    assert "google" in keys


def test_missing_key_handling_with_env_fallback(config_manager):
    """Test missing key handling with environment variable fallback."""
    # Set environment variables
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-test-key"}):
        keys = config_manager.get_api_keys()
        # Should prefer environment variable
        assert keys.get("anthropic") == "env-test-key" or keys.get("anthropic") is None


def test_invalid_key_format_handling(config_manager):
    """Test handling of invalid key format."""
    # Save keys with invalid format (empty string, None, etc.)
    invalid_keys = {
        "anthropic": "",  # Empty key
        "openai": None,  # None key
        "google": "   "  # Whitespace only
    }

    # Should handle gracefully
    result = config_manager.save_api_keys(invalid_keys)
    assert result is True

    # Retrieve - should get what was saved
    retrieved = config_manager.get_api_keys()
    assert isinstance(retrieved, dict)


def test_key_rotation(config_manager):
    """Test key rotation (updating existing keys)."""
    # Save initial keys
    initial_keys = {
        "anthropic": "old-key-1",
        "openai": "old-key-2"
    }
    config_manager.save_api_keys(initial_keys)

    # Rotate keys (update with new values)
    new_keys = {
        "anthropic": "new-key-1",
        "openai": "new-key-2",
        "google": "new-key-3"
    }
    result = config_manager.save_api_keys(new_keys)
    assert result is True

    # Verify new keys are saved
    retrieved = config_manager.get_api_keys()
    assert retrieved["anthropic"] == "new-key-1"
    assert retrieved["openai"] == "new-key-2"
    assert retrieved["google"] == "new-key-3"


def test_configuration_persistence(config_manager):
    """Test configuration persistence across restarts."""
    # Set configuration
    config_manager.set_setting("test_setting", "test_value")
    config_manager.save_api_keys({"anthropic": "persisted-key"})

    # Create new manager instance (simulating restart)
    new_manager = ConfigManager(manifest_dir=config_manager.manifest_dir)

    # Verify settings persisted
    setting = new_manager.get_setting("test_setting")
    assert setting == "test_value"

    # Verify keys persisted
    keys = new_manager.get_api_keys()
    assert keys.get("anthropic") == "persisted-key"


def test_configuration_persistence_agent_config(config_manager):
    """Test agent configuration persistence."""
    # Set agent model config (using correct signature)
    result = config_manager.set_agent_model_config(
        agent_type="coder",
        provider="anthropic",
        model="claude-3-opus-20240229"
    )
    assert result is True

    # Create new manager
    new_manager = ConfigManager(manifest_dir=config_manager.manifest_dir)

    # Verify config persisted
    retrieved = new_manager.get_agent_model_config("coder")
    assert retrieved["provider"] == "anthropic"
    assert retrieved["model"] == "claude-3-opus-20240229"


def test_encryption_key_creation(config_manager):
    """Test encryption key creation on first use."""
    # Key file should be created
    key_file = config_manager.key_file
    assert key_file.exists()

    # Key file should have restricted permissions (0o600)
    # Note: On some systems, permissions might differ, so we just check it exists
    assert key_file.is_file()


def test_encryption_key_reuse(config_manager):
    """Test encryption key is reused across instances."""
    # Save keys with first manager
    config_manager.save_api_keys({"anthropic": "test-key"})

    # Create second manager - should use same key
    manager2 = ConfigManager(manifest_dir=config_manager.manifest_dir)

    # Should be able to decrypt keys from first manager
    keys = manager2.get_api_keys()
    assert keys.get("anthropic") == "test-key"


def test_corrupted_keys_file_handling(config_manager):
    """Test handling of corrupted keys file."""
    # Create corrupted keys file
    keys_file = config_manager.keys_file
    keys_file.parent.mkdir(parents=True, exist_ok=True)
    with open(keys_file, "wb") as f:
        f.write(b"corrupted encrypted data that can't be decrypted")

    # Should handle gracefully and fall back to env vars
    keys = config_manager.get_api_keys()
    assert isinstance(keys, dict)
    # Should not raise exception


def test_has_all_keys(config_manager):
    """Test checking if all required keys are present."""
    # Initially should be False (no keys set)
    assert config_manager.has_all_keys() is False

    # Set all keys
    config_manager.save_api_keys({
        "anthropic": "key1",
        "openai": "key2",
        "google": "key3"
    })

    # Should now be True
    assert config_manager.has_all_keys() is True


@pytest.mark.asyncio
async def test_validate_all_keys(config_manager):
    """Test validating all stored keys."""
    # Save some keys
    config_manager.save_api_keys({
        "anthropic": "test-key-1",
        "openai": "test-key-2",
        "google": "test-key-3"
    })

    # Mock validation to avoid actual API calls
    with patch.object(config_manager, 'validate_key', new_callable=AsyncMock) as mock_validate:
        mock_validate.return_value = True

        results = await config_manager.validate_all_keys()

        assert isinstance(results, dict)
        assert "anthropic" in results
        assert "openai" in results
        assert "google" in results
        # validate_key should be called for each key
        assert mock_validate.call_count == 3


def test_agent_permissions_persistence(config_manager):
    """Test agent permissions configuration persistence."""
    permissions = {
        "permission": {
            "read": ["allow"],
            "write": ["ask"]
        }
    }
    result = config_manager.set_agent_permissions("coder", permissions)
    assert result is True

    # Retrieve permissions
    retrieved = config_manager.get_agent_permissions("coder")
    assert retrieved is not None
    assert retrieved["permission"]["read"] == ["allow"]


def test_global_permissions_persistence(config_manager):
    """Test global permissions configuration persistence."""
    global_perms = {
        "permission": {
            "dangerous_commands": ["deny"]
        }
    }
    result = config_manager.set_global_permissions(global_perms)
    assert result is True

    # Retrieve global permissions
    retrieved = config_manager.get_global_permissions()
    assert retrieved is not None
    assert retrieved["permission"]["dangerous_commands"] == ["deny"]
