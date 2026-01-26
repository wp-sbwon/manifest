"""
Unit tests for ResourceMonitor.

Tests resource monitoring, usage tracking, and limits.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from manifest.agents.resource_monitor import ResourceMonitor


@pytest.fixture
def resource_monitor():
    """Create a ResourceMonitor instance."""
    return ResourceMonitor()


def test_resource_monitor_initialization(resource_monitor):
    """Test ResourceMonitor initialization."""
    assert resource_monitor is not None
    assert resource_monitor.monitoring is False
    assert resource_monitor.resource_history == []


@pytest.mark.asyncio
async def test_start_stop(resource_monitor):
    """Test starting and stopping monitoring."""
    await resource_monitor.start()
    assert resource_monitor.monitoring is True
    
    await resource_monitor.stop()
    assert resource_monitor.monitoring is False


def test_get_current_stats(resource_monitor):
    """Test getting current stats."""
    # Initially empty
    stats = resource_monitor.get_current_stats()
    assert isinstance(stats, dict)
    
    # Add some history
    resource_monitor.resource_history.append({
        "timestamp": "2024-01-01T00:00:00",
        "system": {"cpu_percent": 50.0}
    })
    stats = resource_monitor.get_current_stats()
    assert isinstance(stats, dict)
    assert "timestamp" in stats


def test_get_container_stats(resource_monitor):
    """Test getting container stats."""
    container_id = "container-1"
    stats = resource_monitor.get_container_stats(container_id)
    assert stats is None
    
    # Add container stats
    resource_monitor.container_stats[container_id] = {
        "cpu_percent": 30.0,
        "memory_usage": 1024
    }
    stats = resource_monitor.get_container_stats(container_id)
    assert isinstance(stats, dict)
    assert stats["cpu_percent"] == 30.0


def test_get_resource_trends(resource_monitor):
    """Test getting resource trends."""
    from datetime import datetime, timedelta
    
    # Add some history with recent timestamps
    now = datetime.now()
    resource_monitor.resource_history = [
        {
            "timestamp": (now - timedelta(minutes=5)).isoformat(),
            "system": {"cpu_percent": 50.0, "memory": {"percent": 60.0}}
        },
        {
            "timestamp": (now - timedelta(minutes=2)).isoformat(),
            "system": {"cpu_percent": 55.0, "memory": {"percent": 65.0}}
        }
    ]
    
    trends = resource_monitor.get_resource_trends("system.cpu_percent", minutes=10)
    assert isinstance(trends, list)
    assert len(trends) > 0
    assert trends == [50.0, 55.0]


def test_check_thresholds(resource_monitor):
    """Test checking thresholds."""
    # Add current stats
    resource_monitor.resource_history.append({
        "timestamp": "2024-01-01T00:00:00",
        "system": {"cpu_percent": 90.0, "memory": {"percent": 70.0}}
    })
    
    thresholds = {
        "system.cpu_percent": 80.0,
        "system.memory.percent": 85.0
    }
    
    violations = resource_monitor.check_thresholds(thresholds)
    assert isinstance(violations, list)
    # CPU should be over threshold
    assert len(violations) > 0
