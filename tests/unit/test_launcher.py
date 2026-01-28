"""
Unit tests for the Manifest launcher.

Tests that the launcher builds correct opencode args, handles missing opencode,
and starts the View (when mocked).
"""
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from manifest.launcher import (
    _get_manifest_dir,
    _get_agent_name,
    _is_opencode_available,
    _start_view,
    main,
    DEFAULT_AGENT,
)


def test_get_manifest_dir():
    """_get_manifest_dir returns cwd/.manifest resolved."""
    d = _get_manifest_dir()
    assert d.name == ".manifest"
    assert d.is_absolute() or d == Path.cwd() / ".manifest"


def test_get_agent_name_default():
    """_get_agent_name returns default when no config."""
    with patch.dict(os.environ, {}, clear=False):
        if "MANIFEST_OPENCODE_AGENT" in os.environ:
            del os.environ["MANIFEST_OPENCODE_AGENT"]
    with patch("manifest.core.config.get_config_manager", side_effect=Exception("no config")):
        assert _get_agent_name() == DEFAULT_AGENT


def test_get_agent_name_from_settings():
    """_get_agent_name returns opencode.agent from config when set."""
    with patch.dict(os.environ, {}, clear=False):
        if "MANIFEST_OPENCODE_AGENT" in os.environ:
            del os.environ["MANIFEST_OPENCODE_AGENT"]
    cm = MagicMock()
    cm.get_setting.return_value = "custom-agent"
    cm.manifest_dir = Path(".manifest")
    with patch("manifest.core.config.get_config_manager", return_value=cm):
        assert _get_agent_name() == "custom-agent"


def test_get_agent_name_from_env():
    """_get_agent_name returns MANIFEST_OPENCODE_AGENT when set."""
    with patch.dict(os.environ, {"MANIFEST_OPENCODE_AGENT": "my-agent"}):
        assert _get_agent_name() == "my-agent"
    if "MANIFEST_OPENCODE_AGENT" in os.environ:
        del os.environ["MANIFEST_OPENCODE_AGENT"]


def test_is_opencode_available_mock():
    """_is_opencode_available can be mocked to True or False."""
    with patch("manifest.launcher.shutil.which", return_value="/usr/bin/opencode"):
        assert _is_opencode_available() is True
    with patch("manifest.launcher.shutil.which", return_value=None), \
         patch("manifest.launcher.subprocess.run", side_effect=FileNotFoundError):
        assert _is_opencode_available() is False


def test_main_opencode_not_found():
    """main() returns 1 and writes to stderr when opencode not found."""
    with patch("manifest.launcher._is_opencode_available", return_value=False), \
         patch("manifest.launcher._is_docker_available", return_value=True), \
         patch("manifest.launcher._start_view", return_value=None), \
         patch("sys.stderr") as mock_stderr:
        assert main() == 1
        mock_stderr.write.assert_called()
        assert "opencode" in mock_stderr.write.call_args[0][0].lower()


def test_main_docker_not_available():
    """main() does not exit when Docker not available; warns and proceeds (Docker is required but we try install/start)."""
    with patch("manifest.launcher._is_opencode_available", return_value=True), \
         patch("manifest.launcher._ensure_docker_available", return_value=False), \
         patch("manifest.launcher._start_view", return_value=None), \
         patch("manifest.launcher.run_opencode", return_value=0) as mock_run, \
         patch("sys.stderr") as mock_stderr:
        assert main() == 0
        mock_run.assert_called_once()
        mock_stderr.write.assert_called()
        msg = "".join(c[0][0] for c in mock_stderr.write.call_args_list if c[0])
        assert "docker" in msg.lower() or "warning" in msg.lower()


def test_main_calls_run_opencode():
    """main() calls run_opencode when opencode and Docker are available (mocked)."""
    with patch("manifest.launcher._is_opencode_available", return_value=True), \
         patch("manifest.launcher._ensure_docker_available", return_value=True), \
         patch("manifest.launcher._start_view", return_value=None), \
         patch("manifest.launcher.run_opencode", return_value=0) as m:
        # run_opencode normally execs and doesn't return; we mock return 0
        assert main() == 0
        m.assert_called_once()


def test_start_view_returns_popen_or_none():
    """_start_view returns Popen or None (subprocess.Popen mocked)."""
    with patch("subprocess.Popen") as mock_popen:
        mock_popen.return_value = MagicMock()
        proc = _start_view()
        assert proc is not None
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert sys.executable in call_args or "python" in str(call_args).lower()
        assert "manifest.view" in str(call_args)
