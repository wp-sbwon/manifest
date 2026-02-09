"""
Container management for agent execution (Podman via Docker-compatible API).

This module provides the ContainerManager class which manages containers
for running agents. Each agent can run in its own isolated container, providing
resource management, isolation, and monitoring capabilities. The launcher
ensures Podman is installed and running and sets DOCKER_HOST so this manager
connects to Podman's Docker-compatible API.

The container manager handles container lifecycle (start, stop, status), resource
monitoring, and inter-container communication via a message bus.
"""
import asyncio
import docker
import subprocess
import platform
import sys
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
from manifest.agents.container_communication import ContainerMessageBus, ContainerStateSync
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class ContainerManager:
    """Manages containers for isolated agent execution (Podman via Docker-compatible API).

    Handles the complete lifecycle of containers used for running agents.
    Each agent runs in its own container, providing isolation, resource limits,
    and monitoring capabilities. Connects via docker.from_env() (DOCKER_HOST
    set by launcher to Podman socket when using Podman).

    The manager maintains a message bus for inter-container communication
    and tracks container metadata for status monitoring.

    Attributes:
        client: Docker API client instance (None if container runtime unavailable).
        docker_available: Boolean indicating if the container runtime is available.
        active_containers: Dictionary mapping task IDs to container objects.
        container_metadata: Dictionary mapping task IDs to container metadata.
        message_bus: ContainerMessageBus for inter-container communication.
        _message_bus_connected: Whether the message bus is connected.
    """

    def __init__(self, docker_client: Optional[docker.DockerClient] = None, require_docker: bool = True, auto_start: bool = True):
        """Initialize the container manager.

        Attempts to connect to the container runtime (Podman when DOCKER_HOST is set)
        and verify it's available. If the runtime is not running and auto_start is True,
        attempts to start it (Docker Desktop or Podman machine/socket).

        Args:
            docker_client: Optional pre-configured Docker API client. If not
                provided, creates a new client from environment (DOCKER_HOST).
            require_docker: If True, raises exception when runtime is unavailable.
            auto_start: If True, attempts to start the runtime if not running (default: True).

        Raises:
            RuntimeError: If container runtime is required but not available and cannot be started.
        """
        self.require_docker = require_docker
        self.auto_start = auto_start

        try:
            self.client = docker_client or docker.from_env()
            self.client.ping()  # Test connection
            self.docker_available = True
            logger.info("Container runtime (Podman/Docker API) is available and connected")
        except Exception as e:
            error_msg = str(e)
            is_connection_error = "No such file or directory" in error_msg or "Connection aborted" in error_msg

            # Try to auto-start runtime if enabled (synchronous attempt)
            if auto_start and is_connection_error:
                logger.info("Container runtime not running, attempting to start automatically...")
                docker_start_attempted = self._start_docker()
                if docker_start_attempted:
                    logger.info("Container runtime start command executed. Will verify connection when needed.")
                    # Don't wait here - connection will be verified when actually needed
                    self.client = None
                    self.docker_available = False  # Will be set to True when ensure_docker_running succeeds
                else:
                    self.client = None
                    self.docker_available = False
            else:
                self.client = None
                self.docker_available = False

            # Raise exception if container runtime is required but unavailable
            if require_docker and not self.docker_available:
                if is_connection_error:
                    if auto_start:
                        logger.warning("Container runtime not running. Auto-start attempted. Will verify when needed.")
                    else:
                        raise RuntimeError(
                            "Container runtime (Podman) is not running. Start Podman (e.g. podman machine start) or set DOCKER_HOST.\n"
                            "Manifest requires a container runtime to run agents in isolated containers."
                        ) from e
                else:
                    raise RuntimeError(
                        f"Container runtime is required but not available: {error_msg}\n"
                        "Please ensure Podman (or Docker) is installed and running."
                    ) from e

        self.active_containers: Dict[str, docker.models.containers.Container] = {}
        self.container_metadata: Dict[str, Dict[str, Any]] = {}

        # Message bus for inter-container communication
        self.message_bus = ContainerMessageBus()
        self._message_bus_connected = False

    def _start_docker(self) -> bool:
        """Attempt to start the container runtime (Docker Desktop or Podman).

        Attempts to start Docker Desktop on macOS/Windows or Docker/Podman on Linux.
        When Manifest is run via the launcher, Podman is already started and DOCKER_HOST is set.

        Returns:
            True if a start was attempted, False otherwise.
        """
        system = platform.system()

        try:
            if system == "Darwin":  # macOS
                # Try to start Docker Desktop when Podman is not in use
                docker_app_paths = [
                    "/Applications/Docker.app",
                    "/Applications/Docker Desktop.app"
                ]

                for app_path in docker_app_paths:
                    if Path(app_path).exists():
                        logger.info(f"Starting Docker Desktop from {app_path}")
                        subprocess.Popen(
                            ["open", "-a", app_path],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        )
                        return True

                # If Docker Desktop not found, try docker/podman CLI
                try:
                    subprocess.run(
                        ["docker", "info"],
                        check=False,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=2
                    )
                    return True
                except:
                    logger.warning("Docker Desktop not found. Use Podman (launcher installs/starts it) or install Docker Desktop for macOS.")
                    return False

            elif system == "Linux":
                # Try to start Docker or Podman daemon/socket
                logger.info("Attempting to start container runtime (Docker or Podman)...")
                try:
                    # Check if docker/podman command exists
                    subprocess.run(
                        ["docker", "--version"],
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    # Try to start Docker or Podman service (may require sudo)
                    result = subprocess.run(
                        ["sudo", "systemctl", "start", "podman.socket"],
                        check=False,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=5
                    )
                    if result.returncode != 0:
                        result = subprocess.run(
                            ["sudo", "systemctl", "start", "docker"],
                            check=False,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            timeout=5
                        )
                    if result.returncode == 0:
                        logger.info("Container runtime (Podman/Docker) started successfully")
                        return True
                    else:
                        logger.warning("Could not start container runtime (may require sudo privileges)")
                        return False
                except FileNotFoundError:
                    logger.warning("Container runtime not installed. Install Podman or Docker Engine.")
                    return False
                except subprocess.TimeoutExpired:
                    logger.warning("Container runtime start command timed out")
                    return False

            elif system == "Windows":
                # Try to start Docker Desktop on Windows when Podman is not in use
                docker_paths = [
                    "C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe",
                    "C:\\Program Files (x86)\\Docker\\Docker\\Docker Desktop.exe"
                ]

                for docker_path in docker_paths:
                    if Path(docker_path).exists():
                        logger.info(f"Starting Docker Desktop from {docker_path}")
                        subprocess.Popen(
                            [docker_path],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        )
                        return True

                logger.warning("Docker Desktop not found. Use Podman (launcher installs/starts it) or install Docker Desktop for Windows.")
                return False
            else:
                logger.warning(f"Unsupported platform: {system}")
                return False

        except Exception as e:
            logger.error(f"Error starting container runtime: {e}", exc_info=True)
            return False

    def is_docker_available(self) -> bool:
        """Check if the container runtime (Podman/Docker API) is available and ready to use.

        Returns:
            True if the runtime is accessible and working, False otherwise.
        """
        return self.docker_available

    async def ensure_docker_running(self) -> bool:
        """Ensure the container runtime (Podman/Docker API) is running, starting it if necessary.

        Ensures the runtime is available before operations that require it.

        Returns:
            True if the container runtime is available, False otherwise.
        """
        if self.docker_available:
            return True

        if self.auto_start:
            logger.info("Container runtime not available, attempting to start...")
            if self._start_docker():
                # Wait for the runtime to start
                for attempt in range(30):  # Wait up to 30 seconds
                    await asyncio.sleep(1)
                    try:
                        self.client = docker.from_env()
                        self.client.ping()
                        self.docker_available = True
                        logger.info("Container runtime is now available")
                        return True
                    except Exception:
                        continue
                logger.warning("Container runtime did not start within timeout")
                return False
            else:
                return False

        return False

    async def start_agent_container(
        self,
        task_id: str,
        agent_type: str,
        environment: Optional[Dict[str, str]] = None,
        volumes: Optional[Dict[str, Dict[str, str]]] = None,
        network: str = "manifest-network"
    ) -> Optional[str]:
        """Start a container for an agent.

        Creates and starts a container running the agent. The container
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
            network: Container network name to connect the container to.
                Defaults to "manifest-network".

        Returns:
            Container ID string if successful, None if container runtime is unavailable
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
            True if container was found and stopped, False if container runtime is
            unavailable or container doesn't exist.
        """
        # Ensure container runtime is running before stopping container
        if not self.docker_available:
            if not await self.ensure_docker_running():
                logger.error("Cannot stop container: container runtime is not available")
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

        Queries the container runtime for the container's current state, CPU usage, memory
        usage, and other metadata. Useful for monitoring and resource tracking.

        Args:
            task_id: ID of the task whose container status to query.

        Returns:
            Dictionary containing container status, resource usage, and metadata,
            or None if container runtime is unavailable or container doesn't exist.
        """
        # Ensure container runtime is running before getting status
        if not self.docker_available:
            if not await self.ensure_docker_running():
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
        """Calculate CPU usage percentage from container stats.

        Parses container stats dictionary to compute CPU usage as a percentage.
        Returns 0.0 if calculation fails or stats are incomplete.

        Args:
            stats: Container stats dictionary from container.stats().

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
        # Ensure container runtime is running before getting logs
        if not self.docker_available:
            if not await self.ensure_docker_running():
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
        # Ensure container runtime is running before cleanup
        if not self.docker_available:
            if not await self.ensure_docker_running():
                logger.warning("Cannot cleanup containers: container runtime is not available")
                return

        for task_id in list(self.active_containers.keys()):
            await self.stop_agent_container(task_id)
