"""
Resource Monitor - Monitors system and container resources.
Tracks CPU, memory, network usage for agents and containers.
"""
import asyncio
import psutil
from typing import Dict, Any, Optional, List
from datetime import datetime
import docker
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class ResourceMonitor:
    """
    Monitors resource usage for agents and containers.
    Tracks CPU, memory, network, and disk usage.
    """
    
    def __init__(self, docker_client: Optional[docker.DockerClient] = None):
        """
        Initialize resource monitor.
        
        Args:
            docker_client: Optional Docker client for container monitoring
        """
        self.docker_client = docker_client
        self.monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self.resource_history: List[Dict[str, Any]] = []
        self.container_stats: Dict[str, Dict[str, Any]] = {}
    
    async def start(self, interval: float = 10.0):
        """
        Start resource monitoring.
        
        Args:
            interval: Monitoring interval in seconds
        """
        if self.monitoring:
            return
        
        self.monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(interval))
    
    async def stop(self):
        """Stop resource monitoring."""
        self.monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
    
    async def _monitor_loop(self, interval: float):
        """Main monitoring loop."""
        while self.monitoring:
            try:
                await asyncio.sleep(interval)
                
                # Monitor system resources
                system_stats = await self._get_system_stats()
                
                # Monitor container resources
                container_stats = await self._get_container_stats()
                
                # Store history
                snapshot = {
                    "timestamp": datetime.now().isoformat(),
                    "system": system_stats,
                    "containers": container_stats
                }
                
                self.resource_history.append(snapshot)
                
                # Keep only last 100 snapshots
                if len(self.resource_history) > 100:
                    self.resource_history = self.resource_history[-100:]
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in resource monitor loop: {e}", exc_info=True)
    
    async def _get_system_stats(self) -> Dict[str, Any]:
        """Get system-wide resource statistics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "percent": memory.percent
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent
                }
            }
        except Exception as e:
            logger.error(f"Error getting system stats: {e}", exc_info=True)
            return {}
    
    async def _get_container_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get resource statistics for containers."""
        if not self.docker_client:
            return {}
        
        stats = {}
        
        try:
            containers = self.docker_client.containers.list(all=True)
            
            for container in containers:
                try:
                    container_stats = container.stats(stream=False)
                    
                    # Calculate CPU usage
                    cpu_delta = container_stats.get("cpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0)
                    system_cpu_delta = container_stats.get("cpu_stats", {}).get("system_cpu_usage", 0)
                    cpu_percent = 0.0
                    
                    if system_cpu_delta > 0:
                        cpu_percent = (cpu_delta / system_cpu_delta) * 100.0
                    
                    # Get memory stats
                    memory_stats = container_stats.get("memory_stats", {})
                    memory_usage = memory_stats.get("usage", 0)
                    memory_limit = memory_stats.get("limit", 0)
                    memory_percent = 0.0
                    
                    if memory_limit > 0:
                        memory_percent = (memory_usage / memory_limit) * 100.0
                    
                    stats[container.id] = {
                        "name": container.name,
                        "status": container.status,
                        "cpu_percent": cpu_percent,
                        "memory": {
                            "usage": memory_usage,
                            "limit": memory_limit,
                            "percent": memory_percent
                        },
                        "network": container_stats.get("networks", {})
                    }
                    
                    self.container_stats[container.id] = stats[container.id]
                    
                except Exception as e:
                    logger.error(f"Error getting stats for container {container.id}: {e}", exc_info=True)
        
        except Exception as e:
            logger.error(f"Error getting container stats: {e}", exc_info=True)
        
        return stats
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Get current resource statistics."""
        if not self.resource_history:
            return {}
        
        return self.resource_history[-1]
    
    def get_container_stats(self, container_id: str) -> Optional[Dict[str, Any]]:
        """Get stats for a specific container."""
        return self.container_stats.get(container_id)
    
    def get_resource_trends(
        self,
        metric: str,
        minutes: int = 10
    ) -> List[float]:
        """
        Get resource trends over time.
        
        Args:
            metric: Metric name (e.g., "system.cpu_percent", "system.memory.percent")
            minutes: Number of minutes to look back
            
        Returns:
            List of metric values
        """
        cutoff_time = datetime.now().timestamp() - (minutes * 60)
        
        values = []
        for snapshot in self.resource_history:
            timestamp = datetime.fromisoformat(snapshot["timestamp"]).timestamp()
            if timestamp < cutoff_time:
                continue
            
            # Navigate metric path
            parts = metric.split(".")
            value = snapshot
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    value = None
                    break
            
            if value is not None:
                values.append(float(value))
        
        return values
    
    def check_thresholds(
        self,
        thresholds: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Check if any metrics exceed thresholds.
        
        Args:
            thresholds: Dict of metric -> threshold value
            
        Returns:
            List of threshold violations
        """
        violations = []
        current = self.get_current_stats()
        
        if not current:
            return violations
        
        for metric, threshold in thresholds.items():
            parts = metric.split(".")
            value = current
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    value = None
                    break
            
            if value is not None and float(value) > threshold:
                violations.append({
                    "metric": metric,
                    "value": value,
                    "threshold": threshold,
                    "timestamp": current.get("timestamp")
                })
        
        return violations
