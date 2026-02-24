"""Single source for default ports, API URLs, and manifest file names."""
# Container API (launcher subprocess; tool_executor calls it)
CONTAINER_API_PORT = 4097
# Host API (runner/container → View backend)
HOST_API_PORT = 8000
DEFAULT_MANIFEST_API_BASE_URL = "http://manifest-app:8000"

# Manifest file names (relative to .manifest/)
STATE_FILE = "state.json"
AGENT_CONFIG_FILE = "agent_config.json"
DESIGN_HISTORY_FILE = "design_history.json"
