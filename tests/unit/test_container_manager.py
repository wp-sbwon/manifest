"""
Tests for Container Manager.
"""
import pytest
from manifest.agents.container_manager import ContainerManager


def test_container_manager_init():
    """Test ContainerManager initialization."""
    manager = ContainerManager()

    # Should initialize even if Docker is not available
    assert manager is not None
    assert isinstance(manager.is_docker_available(), bool)


def test_container_manager_no_docker():
    """Test ContainerManager when Docker is not available."""
    manager = ContainerManager(docker_client=None)

    # Should handle gracefully
    assert manager.is_docker_available() is False
    assert len(manager.list_active_containers()) == 0


@pytest.mark.asyncio
async def test_start_container_no_docker():
    """Test starting container when Docker is not available."""
    manager = ContainerManager(docker_client=None)

    container_id = await manager.start_agent_container(
        task_id="test-task",
        agent_type="test"
    )

    assert container_id is None


@pytest.mark.asyncio
async def test_stop_container_no_docker():
    """Test stopping container when Docker is not available."""
    manager = ContainerManager(docker_client=None)

    success = await manager.stop_agent_container("test-task")
    assert success is False


@pytest.mark.asyncio
async def test_get_container_status_no_docker():
    """Test getting container status when Docker is not available."""
    manager = ContainerManager(docker_client=None)

    status = await manager.get_container_status("test-task")
    assert status is None


@pytest.mark.asyncio
async def test_list_active_containers():
    """Test listing active containers."""
    manager = ContainerManager(docker_client=None)

    containers = manager.list_active_containers()
    assert isinstance(containers, list)
    assert len(containers) == 0


@pytest.mark.asyncio
async def test_cleanup_all():
    """Test cleaning up all containers."""
    manager = ContainerManager(docker_client=None)

    # Should not raise exception even with no Docker
    await manager.cleanup_all()
