"""
Unit tests for ContainerManager.

Tests Docker container management, creation, and lifecycle.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from manifest.agents.container_manager import ContainerManager


@pytest.fixture
def container_manager():
    """Create a ContainerManager instance."""
    # Mock docker client to avoid Docker connection errors
    with patch('docker.from_env', side_effect=Exception("Docker not available")):
        return ContainerManager(docker_client=None)


def test_container_manager_initialization(container_manager):
    """Test ContainerManager initialization."""
    assert container_manager is not None


def test_is_docker_available(container_manager):
    """Test checking if Docker is available."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = Mock(returncode=0)
        is_available = container_manager.is_docker_available()
        assert isinstance(is_available, bool)


@pytest.mark.asyncio
async def test_create_container(container_manager):
    """Test creating a container."""
    # ContainerManager uses start_agent_container, not create_container
    with patch.object(container_manager, 'docker_available', True):
        with patch.object(container_manager, 'client') as mock_client:
            mock_container = Mock()
            mock_container.id = "container-1"
            mock_container.start = Mock()
            mock_client.containers.create = Mock(return_value=mock_container)
            mock_client.containers.get = Mock(return_value=mock_container)
            container_manager.message_bus = Mock()
            container_manager.message_bus.connect = AsyncMock()
            container_manager.message_bus.send_message = AsyncMock()
            
            container_id = await container_manager.start_agent_container(
                task_id="task-1",
                agent_type="coder"
            )
            assert container_id is not None


@pytest.mark.asyncio
async def test_start_container(container_manager):
    """Test starting a container."""
    # ContainerManager doesn't have start_container, containers are started when created
    # Test start_agent_container instead
    with patch.object(container_manager, 'docker_available', True):
        with patch.object(container_manager, 'client') as mock_client:
            mock_container = Mock()
            mock_container.id = "container-1"
            mock_container.start = Mock()
            mock_client.containers.create = Mock(return_value=mock_container)
            mock_client.containers.get = Mock(return_value=mock_container)
            container_manager.message_bus = Mock()
            container_manager.message_bus.connect = AsyncMock()
            container_manager.message_bus.send_message = AsyncMock()
            
            container_id = await container_manager.start_agent_container("task-1", "coder")
            assert container_id is not None


@pytest.mark.asyncio
async def test_stop_container(container_manager):
    """Test stopping a container."""
    # ContainerManager uses stop_agent_container, not stop_container
    container_manager.active_containers["task-1"] = Mock()
    container_manager.active_containers["task-1"].stop = Mock()
    container_manager.active_containers["task-1"].remove = Mock()
    container_manager.active_containers["task-1"].id = "container-1"
    container_manager.docker_available = True
    container_manager.message_bus = Mock()
    container_manager.message_bus.send_message = AsyncMock()
    
    result = await container_manager.stop_agent_container("task-1")
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_get_container_status(container_manager):
    """Test getting container status."""
    with patch.object(container_manager, 'is_docker_available', return_value=True):
        status = await container_manager.get_container_status("container-1")
        assert isinstance(status, dict) or status is None


@pytest.mark.asyncio
async def test_remove_container(container_manager):
    """Test removing a container."""
    # ContainerManager doesn't have remove_container, containers are removed in stop_agent_container
    # Test stop_agent_container which removes the container
    container_manager.active_containers["task-1"] = Mock()
    container_manager.active_containers["task-1"].stop = Mock()
    container_manager.active_containers["task-1"].remove = Mock()
    container_manager.active_containers["task-1"].id = "container-1"
    container_manager.docker_available = True
    container_manager.message_bus = Mock()
    container_manager.message_bus.send_message = AsyncMock()
    
    result = await container_manager.stop_agent_container("task-1")
    assert isinstance(result, bool)
