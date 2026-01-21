"""
Container Manager - Manages Docker containers for Agent Squad.
Each agent runs in its own Docker container for isolation and resource management.
"""
import asyncio
import docker
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime


class ContainerManager:
    """
    Manages Docker containers for agent execution.
    Provides container lifecycle management, monitoring, and logging.
    """
    
    def __init__(self, docker_client: Optional[docker.DockerClient] = None):
        """
        Initialize container manager.
        
        Args:
            docker_client: Optional Docker client (creates new one if not provided)
        """
        try:
            self.client = docker_client or docker.from_env()
            self.client.ping()  # Test connection
            self.docker_available = True
        except Exception as e:
            print(f"Docker not available: {e}")
            self.client = None
            self.docker_available = False
        
        self.active_containers: Dict[str, docker.models.containers.Container] = {}
        self.container_metadata: Dict[str, Dict[str, Any]] = {}
    
    def is_docker_available(self) -> bool:
        """Check if Docker is available."""
        return self.docker_available
    
    async def start_agent_container(
        self,
        task_id: str,
        agent_type: str,
        environment: Optional[Dict[str, str]] = None,
        volumes: Optional[Dict[str, Dict[str, str]]] = None,
        network: str = "manifest-network"
    ) -> Optional[str]:
        """
        Start an agent container.
        
        Args:
            task_id: Task identifier
            agent_type: Type of agent (prometheus, sisyphus, test, review)
            environment: Environment variables
            volumes: Volume mappings
            network: Docker network name
            
        Returns:
            Container ID if successful, None otherwise
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
                stderr=True
            )
            
            self.active_containers[task_id] = container
            self.container_metadata[task_id] = {
                "container_id": container.id,
                "container_name": container_name,
                "agent_type": agent_type,
                "started_at": datetime.now().isoformat(),
                "status": "running"
            }
            
            return container.id
        except Exception as e:
            print(f"Error starting container for task {task_id}: {e}")
            return None
    
    async def stop_agent_container(self, task_id: str) -> bool:
        """
        Stop an agent container.
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if container was stopped, False otherwise
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
            
            del self.active_containers[task_id]
            return True
        except Exception as e:
            print(f"Error stopping container for task {task_id}: {e}")
            return False
    
    async def get_container_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get container status.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Container status information
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
            print(f"Error getting container status for task {task_id}: {e}")
            return None
    
    def _calculate_cpu_percent(self, stats: Dict[str, Any]) -> float:
        """Calculate CPU usage percentage from Docker stats."""
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
            print(f"Error getting logs for task {task_id}: {e}")
            return []
    
    def list_active_containers(self) -> List[str]:
        """List all active container task IDs."""
        return list(self.active_containers.keys())
    
    async def cleanup_all(self):
        """Stop and remove all managed containers."""
        for task_id in list(self.active_containers.keys()):
            await self.stop_agent_container(task_id)
