"""
Docker container management for agent execution.

This module provides the ContainerManager class which manages Docker containers
for running agents. Each agent can run in its own isolated container, providing
resource management, isolation, and monitoring capabilities.

The container manager handles container lifecycle (start, stop, status), resource
monitoring, and inter-container communication via a message bus.
"""
import asyncio
import docker
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
from manifest.agents.container_communication import ContainerMessageBus, ContainerStateSync
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class ContainerManager:
    """Manages Docker containers for isolated agent execution.
    
    Handles the complete lifecycle of Docker containers used for running
    agents. Each agent runs in its own container, providing isolation,
    resource limits, and monitoring capabilities.
    
    The manager maintains a message bus for inter-container communication
    and tracks container metadata for status monitoring.
    
    Attributes:
        client: Docker client instance (None if Docker unavailable).
        docker_available: Boolean indicating if Docker is available.
        active_containers: Dictionary mapping task IDs to container objects.
        container_metadata: Dictionary mapping task IDs to container metadata.
        message_bus: ContainerMessageBus for inter-container communication.
        _message_bus_connected: Whether the message bus is connected.
    """
    
    def __init__(self, docker_client: Optional[docker.DockerClient] = None):
        """Initialize the container manager.
        
        Attempts to connect to Docker and verify it's available. If Docker
        is not available, the manager will operate in a degraded mode where
        container operations return None.
        
        Args:
            docker_client: Optional pre-configured Docker client. If not
                provided, creates a new client from environment.
        """
        try:
            self.client = docker_client or docker.from_env()
            self.client.ping()  # Test connection
            self.docker_available = True
        except Exception as e:
            logger.warning(f"Docker not available: {e}", exc_info=True)
            self.client = None
            self.docker_available = False
        
        self.active_containers: Dict[str, docker.models.containers.Container] = {}
        self.container_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Message bus for inter-container communication
        self.message_bus = ContainerMessageBus()
        self._message_bus_connected = False
    
    def is_docker_available(self) -> bool:
        """Check if Docker is available and ready to use.
        
        Returns:
            True if Docker daemon is accessible and working, False otherwise.
        """
        return self.docker_available
    
    async def start_agent_container(
        self,
        task_id: str,
        agent_type: str,
        environment: Optional[Dict[str, str]] = None,
        volumes: Optional[Dict[str, Dict[str, str]]] = None,
        network: str = "manifest-network"
    ) -> Optional[str]:
        """Start a Docker container for an agent.
        
        Creates and starts a Docker container running the agent. The container
        is configured with the appropriate environment variables, volume mounts,
        and network settings. If a container with the same name already exists
        and is running, returns its ID.
        
        Args:
            task_id: ID of the task the agent will work on.
            agent_type: Type of agent (e.g., "coder", "planner", "test").
            environment: Optional dictionary of environment variables to set
                in the container.
            volumes: Optional dictionary of volume mappings (host path to
                container path).
            network: Docker network name to connect the container to.
                Defaults to "manifest-network".
        
        Returns:
            Container ID string if successful, None if Docker is unavailable
            or container creation fails.
        """
        if not self.docker_available:
            return None
        
        container_name = f"manifest-agent-{task_id}-{agent_type}"
        
        # Default environment
        env = {
            "PYTHONUNBUFFERED": "1",
            "PYTHONPATH": "/app/src",
            "AGENT_TYPE": agent_type,
            "AGENT_MODE": "container",
            "TASK_ID": task_id,
            **(environment or {})
        }
        
        # Default volumes (mount current directory)
        vol = volumes or {
            str(Path.cwd().absolute()): {
                "bind": "/app",
                "mode": "rw"
            }
        }
        
        try:
            # Check if container already exists
            try:
                existing = self.client.containers.get(container_name)
                if existing.status == "running":
                    self.active_containers[task_id] = existing
                    self.container_metadata[task_id] = {
                        "container_id": existing.id,
                        "container_name": container_name,
                        "agent_type": agent_type,
                        "started_at": datetime.now().isoformat(),
                        "status": "running"
                    }
                    return existing.id
                else:
                    existing.remove()
            except docker.errors.NotFound:
                pass
            
            # Create and start container
            container = self.client.containers.run(
                image="manifest-agent:latest",  # Will be built from Dockerfile.agent
                name=container_name,
                command=["python", "-m", "manifest.agents.runner", "--task-id", task_id, "--agent-type", agent_type],
                environment=env,
                volumes=vol,
                network=network,
                detach=True,
                remove=False,
                stdout=True,
                stderr=True,
                # Resource limits
                mem_limit="1g",
                cpu_period=100000,
                cpu_quota=50000  # 50% CPU limit
            )
            
            self.active_containers[task_id] = container
            self.container_metadata[task_id] = {
                "container_id": container.id,
                "container_name": container_name,
                "agent_type": agent_type,
                "started_at": datetime.now().isoformat(),
                "status": "running"
            }
            
            # Connect message bus if not connected
            if not self._message_bus_connected:
                await self.message_bus.connect()
                self._message_bus_connected = True
            
            # Notify other containers about new agent
            await self.message_bus.send_message(
                topic="agent-started",
                message={
                    "task_id": task_id,
                    "agent_type": agent_type,
                    "container_id": container.id
                }
            )
            
            return container.id
        except Exception as e:
            logger.error(f"Error starting container for task {task_id}: {e}", exc_info=True)
            return None
    
    async def stop_agent_container(self, task_id: str) -> bool:
        """Stop and remove an agent container.
        
        Stops the running container and removes it. Also notifies other
        containers via the message bus that this agent has stopped.
        
        Args:
            task_id: ID of the task whose container should be stopped.
        
        Returns:
            True if container was found and stopped, False if Docker is
            unavailable or container doesn't exist.
        """
        if not self.docker_available:
            return False
        
        if task_id not in self.active_containers:
            return False
        
        try:
            container = self.active_containers[task_id]
            container.stop(timeout=10)
            container.remove()
            
            if task_id in self.container_metadata:
                self.container_metadata[task_id]["status"] = "stopped"
                self.container_metadata[task_id]["stopped_at"] = datetime.now().isoformat()
            
            # Notify other containers about agent stop
            await self.message_bus.send_message(
                topic="agent-stopped",
                message={
                    "task_id": task_id,
                    "container_id": container.id if container else None
                }
            )
            
            del self.active_containers[task_id]
            return True
        except Exception as e:
            logger.error(f"Error stopping container for task {task_id}: {e}", exc_info=True)
            return False
    
    async def get_container_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get current status and resource usage of a container.
        
        Queries Docker for the container's current state, CPU usage, memory
        usage, and other metadata. Useful for monitoring and resource tracking.
        
        Args:
            task_id: ID of the task whose container status to query.
        
        Returns:
            Dictionary containing container status, resource usage, and metadata,
            or None if Docker is unavailable or container doesn't exist.
        """
        if not self.docker_available:
            return None
        
        if task_id not in self.active_containers:
            return None
        
        try:
            container = self.active_containers[task_id]
            container.reload()  # Refresh container state
            
            stats = container.stats(stream=False)
            
            return {
                "container_id": container.id,
                "status": container.status,
                "started_at": container.attrs.get("State", {}).get("StartedAt"),
                "cpu_usage": self._calculate_cpu_percent(stats),
                "memory_usage": stats.get("memory_stats", {}).get("usage", 0),
                "memory_limit": stats.get("memory_stats", {}).get("limit", 0),
                "metadata": self.container_metadata.get(task_id, {})
            }
        except Exception as e:
            logger.error(f"Error getting container status for task {task_id}: {e}", exc_info=True)
            return None
    
    def _calculate_cpu_percent(self, stats: Dict[str, Any]) -> float:
        """Calculate CPU usage percentage from Docker container stats.
        
        Parses Docker stats dictionary to compute CPU usage as a percentage.
        Returns 0.0 if calculation fails or stats are incomplete.
        
        Args:
            stats: Docker container stats dictionary from container.stats().
        
        Returns:
            CPU usage percentage as a float, or 0.0 if calculation fails.
        """
        try:
            cpu_delta = stats.get("cpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0)
            system_delta = stats.get("cpu_stats", {}).get("system_cpu_usage", 0)
            
            if system_delta == 0:
                return 0.0
            
            cpu_percent = (cpu_delta / system_delta) * 100.0
            return round(cpu_percent, 2)
        except Exception:
            return 0.0
    
    async def get_container_logs(
        self,
        task_id: str,
        tail: int = 100,
        follow: bool = False
    ) -> List[str]:
        """
        Get container logs.
        
        Args:
            task_id: Task identifier
            tail: Number of lines to retrieve
            follow: Whether to follow logs (stream)
            
        Returns:
            List of log lines
        """
        if not self.docker_available:
            return []
        
        if task_id not in self.active_containers:
            return []
        
        try:
            container = self.active_containers[task_id]
            logs = container.logs(tail=tail, follow=follow)
            
            if isinstance(logs, bytes):
                return logs.decode('utf-8', errors='replace').split('\n')
            else:
                # Generator for streaming
                async def log_stream():
                    async for line in logs:
                        yield line.decode('utf-8', errors='replace')
                return log_stream()
        except Exception as e:
            logger.error(f"Error getting logs for task {task_id}: {e}", exc_info=True)
            return []
    
    def list_active_containers(self) -> List[str]:
        """List all active container task IDs."""
        return list(self.active_containers.keys())
    
    async def cleanup_all(self):
        """Stop and remove all managed containers."""
        for task_id in list(self.active_containers.keys()):
            await self.stop_agent_container(task_id)
