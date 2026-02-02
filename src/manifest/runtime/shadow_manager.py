"""
Shadow process management for isolated agent execution.

This module provides the ShadowManager class which executes agents in separate
Python processes for isolation. Shadow processes allow real-time output
streaming, process monitoring, and safe execution without blocking the main
process.

Shadow processes are useful when you want complete isolation between agent
executions or need to stream output in real-time to the UI.
"""
import asyncio
import json
import subprocess
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional, AsyncIterator, Callable, Awaitable, List
from datetime import datetime
from dataclasses import dataclass, field
from manifest.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ShadowProcess:
    """Represents a shadow process running an agent.

    Contains all information about a shadow process including its subprocess
    handle, status, timing, and output. Used for tracking and monitoring
    agent execution in isolated processes.

    Attributes:
        process_id: Unique identifier for this shadow process.
        task_id: ID of the task the agent is working on.
        agent_type: Type of agent running in the process.
        process: Subprocess.Popen handle for the running process.
        status: Current status. Values: "running", "completed", "failed", "cancelled".
        start_time: ISO timestamp when the process started.
        end_time: ISO timestamp when the process ended (None if still running).
        output_channel: Channel name for streaming output to UI.
        returncode: Process exit code (None if still running).
        stdout: Collected standard output text.
        stderr: Collected standard error text.
        sandbox_dir: Optional path to temporary sandbox directory.
    """
    process_id: str
    task_id: str
    agent_type: str
    process: asyncio.subprocess.Process
    status: str = "running"  # running, completed, failed, cancelled
    start_time: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    end_time: Optional[str] = None
    output_channel: str = ""
    returncode: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    sandbox_dir: Optional[Path] = None


class ShadowManager:
    """
    Manages shadow processes for agent execution.

    Shadow processes run agents in isolation, allowing:
    - Real-time output streaming to views
    - Process monitoring and management
    - Safe execution without blocking main process
    """

    def __init__(
        self,
        working_dir: Optional[Path] = None,
        manifest_dir: Optional[Path] = None
    ):
        """
        Initialize Shadow Manager.

        Args:
            working_dir: Working directory for shadow processes
            manifest_dir: Manifest directory for state/config access
        """
        self.working_dir = working_dir or Path.cwd()
        self.manifest_dir = manifest_dir or Path(".manifest")

        # Active shadow processes
        self._active_processes: Dict[str, ShadowProcess] = {}

        # Output callbacks: process_id -> callback
        self._output_callbacks: Dict[str, Callable[[str, str], Awaitable[None]]] = {}

    async def start_shadow_agent(
        self,
        task_id: str,
        agent_type: str,
        context: Dict[str, Any],
        model_config: Dict[str, Any],
        stage: Optional[str] = None,
        output_callback: Optional[Callable[[str, str], Awaitable[None]]] = None,
        use_sandbox: bool = True
    ) -> str:
        """
        Start an agent in a shadow process.

        Args:
            task_id: Task ID
            agent_type: Agent type (orchestrator, planner, coder, etc.)
            context: Agent context
            model_config: Model configuration
            stage: Optional stage (tdd_test, test, etc.)
            output_callback: Optional callback for output streaming
            use_sandbox: Whether to use a temporary sandbox directory

        Returns:
            Process ID
        """
        process_id = f"shadow-{task_id}-{agent_type}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        output_channel = f"shadow-{task_id}-{agent_type}"

        # Setup sandbox if requested
        sandbox_dir = None
        if use_sandbox:
            sandbox_dir = self._setup_sandbox(process_id)
            cwd = str(sandbox_dir)
        else:
            cwd = str(self.working_dir)

        # Prepare agent execution script
        script_path = self._create_agent_script(
            process_id, task_id, agent_type, context, model_config, stage
        )

        # Start shadow process
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            str(script_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=self._prepare_env()
        )

        # Create shadow process record
        shadow_process = ShadowProcess(
            process_id=process_id,
            task_id=task_id,
            agent_type=agent_type,
            process=process,
            output_channel=output_channel,
            sandbox_dir=sandbox_dir
        )

        self._active_processes[process_id] = shadow_process

        # Register output callback
        if output_callback:
            self._output_callbacks[process_id] = output_callback

        # Start monitoring process output
        asyncio.create_task(self._monitor_process(process_id, shadow_process))

        return process_id

    def _setup_sandbox(self, process_id: str) -> Path:
        """Create a temporary sandbox directory and copy codebase."""
        import shutil
        import tempfile

        temp_dir = Path(tempfile.gettempdir()) / "manifest_sandbox" / process_id
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Copy necessary files (exclude .git, venv, etc.)
        ignore_patterns = shutil.ignore_patterns('.git', 'venv', '__pycache__', '.pytest_cache', '*.pyc')

        # Copy src and .manifest
        for item in ['src', '.manifest', 'requirements.txt', 'pyproject.toml']:
            src_path = self.working_dir / item
            if src_path.exists():
                if src_path.is_dir():
                    shutil.copytree(src_path, temp_dir / item, ignore=ignore_patterns)
                else:
                    shutil.copy2(src_path, temp_dir / item)

        return temp_dir

    def get_sandbox_diff(self, process_id: str) -> str:
        """Get diff between sandbox and original codebase."""
        if process_id not in self._active_processes:
            return ""

        shadow_process = self._active_processes[process_id]
        if not shadow_process.sandbox_dir:
            return ""

        # Use git diff or a simple file comparison
        try:
            import subprocess
            result = subprocess.run(
                ["diff", "-r", str(self.working_dir / "src"), str(shadow_process.sandbox_dir / "src")],
                capture_output=True,
                text=True
            )
            return result.stdout
        except Exception as e:
            logger.error(f"Error getting sandbox diff: {e}")
            return ""

    def promote_shadow_changes(self, process_id: str) -> bool:
        """Apply changes from sandbox to main codebase."""
        if process_id not in self._active_processes:
            return False

        shadow_process = self._active_processes[process_id]
        if not shadow_process.sandbox_dir:
            return False

        import shutil
        try:
            # Copy src back to main codebase
            shutil.copytree(
                shadow_process.sandbox_dir / "src",
                self.working_dir / "src",
                dirs_exist_ok=True
            )
            return True
        except Exception as e:
            logger.error(f"Error promoting shadow changes: {e}")
            return False

    async def _monitor_process(
        self,
        process_id: str,
        shadow_process: ShadowProcess
    ) -> None:
        """Monitor a shadow process and stream its output."""
        process = shadow_process.process
        output_callback = self._output_callbacks.get(process_id)

        stdout_lines = []
        stderr_lines = []

        try:
            # Read stdout and stderr concurrently
            async def read_stdout():
                if process.stdout:
                    async for line in process.stdout:
                        decoded = line.decode('utf-8', errors='replace')
                        stdout_lines.append(decoded)
                        if output_callback:
                            await output_callback(shadow_process.output_channel, decoded)

            async def read_stderr():
                if process.stderr:
                    async for line in process.stderr:
                        decoded = line.decode('utf-8', errors='replace')
                        stderr_lines.append(decoded)
                        if output_callback:
                            await output_callback(shadow_process.output_channel, f"[stderr] {decoded}")

            await asyncio.gather(read_stdout(), read_stderr())
            await process.wait()

            shadow_process.returncode = process.returncode
            shadow_process.stdout = "".join(stdout_lines)
            shadow_process.stderr = "".join(stderr_lines)
            shadow_process.end_time = datetime.utcnow().isoformat()

            if process.returncode == 0:
                shadow_process.status = "completed"
            else:
                shadow_process.status = "failed"

        except Exception as e:
            shadow_process.status = "failed"
            shadow_process.stderr += f"\nError monitoring process: {str(e)}"
            if output_callback:
                await output_callback(
                    shadow_process.output_channel,
                    f"[error] Process monitoring failed: {str(e)}\n"
                )
        finally:
            pass

    def _create_agent_script(
        self,
        process_id: str,
        task_id: str,
        agent_type: str,
        context: Dict[str, Any],
        model_config: Dict[str, Any],
        stage: Optional[str]
    ) -> Path:
        """Create a Python script to run the agent in shadow process."""
        script_dir = self.manifest_dir / "shadow_scripts"
        script_dir.mkdir(parents=True, exist_ok=True)

        script_path = script_dir / f"{process_id}.py"

        script_content = f'''"""
Shadow Agent Script - Auto-generated
Process ID: {process_id}
Task ID: {task_id}
Agent Type: {agent_type}
Stage: {stage or "default"}
"""
import sys
import json
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from manifest.core.state_manager import StateManager
from manifest.core.config import ConfigManager
from manifest.runtime.agent.core.manager import AgentManager
from manifest.runtime.agent.core.executor_factory import ExecutorFactory

async def main():
    """Run agent in shadow process. Uses OpenCode for LLM execution."""
    manifest_dir = Path("{self.manifest_dir}")

    state_manager = StateManager(manifest_dir)
    config_manager = ConfigManager(manifest_dir)
    executor = ExecutorFactory.create_executor(config_manager, state_manager)
    agent_manager = AgentManager(state_manager, executor=executor)

    # Load context and model config
    context = {json.dumps(context)}
    model_config = {json.dumps(model_config)}

    # Create agent
    agent = await agent_manager.create_agent(
        agent_type="{agent_type}",
        context=context,
        model_config=model_config,
        task_id="{task_id}"
    )

    if not agent or not agent.get("instance"):
        print(f"Failed to create agent: {agent_type}")
        sys.exit(1)

    agent_instance = agent["instance"]

    # Execute agent based on type and stage
    try:
        if "{agent_type}" == "test":
            if "{stage}" == "tdd_test":
                async for chunk in agent_instance.write_tdd_tests("{task_id}", context, model_config):
                    if chunk.get("type") == "chunk":
                        print(chunk.get("content", ""), end="", flush=True)
                    elif chunk.get("type") == "complete":
                        print(chunk.get("content", ""), flush=True)
            else:
                async for chunk in agent_instance.run_tests("{task_id}", context, model_config):
                    if chunk.get("type") == "chunk":
                        print(chunk.get("content", ""), end="", flush=True)
                    elif chunk.get("type") == "complete":
                        print(chunk.get("content", ""), flush=True)
        elif "{agent_type}" == "coder":
            task_description = context.get("task_description", "Implement task")
            task_scope = context.get("task_scope", {{}})
            async for chunk in agent_instance.implement(task_description, context, task_scope, model_config):
                if chunk.get("type") == "chunk":
                    print(chunk.get("content", ""), end="", flush=True)
                elif chunk.get("type") == "complete":
                    print(chunk.get("content", ""), flush=True)
        elif "{agent_type}" == "planner":
            task_description = context.get("task_description", "Plan task")
            async for chunk in agent_instance.plan(task_description, context, model_config):
                if chunk.get("type") == "chunk":
                    print(chunk.get("content", ""), end="", flush=True)
                elif chunk.get("type") == "complete":
                    print(chunk.get("content", ""), flush=True)
        elif "{agent_type}" == "orchestrator":
            async for chunk in agent_instance.coordinate(
                mission_description=context.get("mission_description", ""),
                context=context,
                model_config=model_config
            ):
                if chunk.get("type") == "chunk":
                    print(chunk.get("content", ""), end="", flush=True)
                elif chunk.get("type") == "complete":
                    print(chunk.get("content", ""), flush=True)
        else:
            async for chunk in agent_instance.execute("{task_id}", context, model_config):
                if chunk.get("type") == "chunk":
                    print(chunk.get("content", ""), end="", flush=True)
                elif chunk.get("type") == "complete":
                    print(chunk.get("content", ""), flush=True)
    except Exception as e:
        print(f"Agent execution failed: {{str(e)}}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
'''
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)
        return script_path

    def _prepare_env(self) -> Dict[str, str]:
        """Prepare environment variables for shadow process."""
        return dict(os.environ)

    async def stop_shadow_process(self, process_id: str) -> bool:
        """Stop a shadow process."""
        if process_id not in self._active_processes:
            return False

        shadow_process = self._active_processes[process_id]
        process = shadow_process.process

        try:
            process.terminate()
            await asyncio.wait_for(process.wait(), timeout=5.0)
            shadow_process.status = "cancelled"
            shadow_process.end_time = datetime.utcnow().isoformat()
            return True
        except Exception as e:
            logger.error(f"Error stopping shadow process {process_id}: {e}")
            return False

    def get_process_status(self, process_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a shadow process."""
        if process_id not in self._active_processes:
            return None

        shadow_process = self._active_processes[process_id]

        return {
            "process_id": shadow_process.process_id,
            "task_id": shadow_process.task_id,
            "agent_type": shadow_process.agent_type,
            "status": shadow_process.status,
            "start_time": shadow_process.start_time,
            "end_time": shadow_process.end_time,
            "returncode": shadow_process.returncode,
            "output_channel": shadow_process.output_channel,
            "stdout_length": len(shadow_process.stdout),
            "stderr_length": len(shadow_process.stderr),
            "has_sandbox": shadow_process.sandbox_dir is not None
        }

    def list_active_processes(self) -> List[Dict[str, Any]]:
        """List all active shadow processes."""
        return [
            self.get_process_status(process_id)
            for process_id in self._active_processes.keys()
        ]

    async def cleanup_completed_processes(self, max_age_hours: int = 24):
        """Clean up completed processes older than max_age_hours."""
        from datetime import timedelta
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)

        to_remove = []
        for process_id, shadow_process in self._active_processes.items():
            if shadow_process.status in ("completed", "failed", "cancelled"):
                if shadow_process.end_time:
                    end_time = datetime.fromisoformat(shadow_process.end_time)
                    if end_time < cutoff_time:
                        to_remove.append(process_id)

        for process_id in to_remove:
            del self._active_processes[process_id]
            if process_id in self._output_callbacks:
                del self._output_callbacks[process_id]
