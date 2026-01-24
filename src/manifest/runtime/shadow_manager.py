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
from pathlib import Path
from typing import Dict, Any, Optional, AsyncIterator, Callable, Awaitable
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
    """
    process_id: str
    task_id: str
    agent_type: str
    process: subprocess.Popen
    status: str = "running"  # running, completed, failed, cancelled
    start_time: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    end_time: Optional[str] = None
    output_channel: str = ""
    returncode: Optional[int] = None
    stdout: str = ""
    stderr: str = ""


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
        output_callback: Optional[Callable[[str, str], Awaitable[None]]] = None
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
                Callback signature: async def callback(channel: str, content: str)
            
        Returns:
            Process ID
        """
        process_id = f"shadow-{task_id}-{agent_type}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        output_channel = f"shadow-{task_id}-{agent_type}"
        
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
            cwd=str(self.working_dir),
            env=self._prepare_env()
        )
        
        # Create shadow process record
        shadow_process = ShadowProcess(
            process_id=process_id,
            task_id=task_id,
            agent_type=agent_type,
            process=process,
            output_channel=output_channel
        )
        
        self._active_processes[process_id] = shadow_process
        
        # Register output callback
        if output_callback:
            self._output_callbacks[process_id] = output_callback
        
        # Start monitoring process output
        asyncio.create_task(self._monitor_process(process_id, shadow_process))
        
        return process_id
    
    async def _monitor_process(
        self,
        process_id: str,
        shadow_process: ShadowProcess
    ) -> None:
        """Monitor a shadow process and stream its output.
        
        Reads stdout and stderr concurrently, streams output to the callback
        if registered, and updates the shadow process status when the process
        completes or fails.
        
        Args:
            process_id: ID of the shadow process to monitor.
            shadow_process: ShadowProcess dataclass containing process information.
        """
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
                        # Stream to callback if available
                        if output_callback:
                            await output_callback(shadow_process.output_channel, decoded)
            
            async def read_stderr():
                if process.stderr:
                    async for line in process.stderr:
                        decoded = line.decode('utf-8', errors='replace')
                        stderr_lines.append(decoded)
                        # Stream stderr as well
                        if output_callback:
                            await output_callback(shadow_process.output_channel, f"[stderr] {decoded}")
            
            # Read both streams concurrently
            await asyncio.gather(
                read_stdout(),
                read_stderr()
            )
            
            # Wait for process to complete
            await process.wait()
            
            # Update shadow process status
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
            # Clean up
            if process_id in self._active_processes:
                # Keep process record for status queries
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
        """
        Create a Python script to run the agent in shadow process.
        
        Returns:
            Path to the created script
        """
        script_dir = self.manifest_dir / "shadow_scripts"
        script_dir.mkdir(parents=True, exist_ok=True)
        
        script_path = script_dir / f"{process_id}.py"
        
        # Create script content
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
from manifest.runtime.agent.manager import AgentManager
from manifest.runtime.agent.executor import AgentExecutor
from manifest.runtime.hooks.prompt_hooks import HookManager, VisualRealityHook
from manifest.audit.blueprint_synchronizer import BlueprintSynchronizer

async def main():
    """Run agent in shadow process."""
    manifest_dir = Path("{self.manifest_dir}")
    working_dir = Path("{self.working_dir}")
    
    # Initialize managers
    state_manager = StateManager(manifest_dir)
    config_manager = ConfigManager(manifest_dir)
    
    # Initialize hook manager
    hook_manager = HookManager()
    blueprint_synchronizer = BlueprintSynchronizer()
    visual_reality_hook = VisualRealityHook(state_manager, blueprint_synchronizer)
    hook_manager.register_hook(visual_reality_hook)
    
    # Initialize agent executor
    executor = AgentExecutor(config_manager, state_manager, hook_manager=hook_manager)
    
    # Initialize agent manager
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
        logger.error(f"Failed to create agent: {agent_type}")
        sys.exit(1)
    
    agent_instance = agent["instance"]
    channel = f"shadow-{task_id}-{agent_type}"
    
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
            async for chunk in agent_instance.code("{task_id}", context, model_config):
                if chunk.get("type") == "chunk":
                    print(chunk.get("content", ""), end="", flush=True)
                elif chunk.get("type") == "complete":
                    print(chunk.get("content", ""), flush=True)
        elif "{agent_type}" == "planner":
            async for chunk in agent_instance.plan("{task_id}", context, model_config):
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
            # Generic agent execution
            async for chunk in agent_instance.execute("{task_id}", context, model_config):
                if chunk.get("type") == "chunk":
                    print(chunk.get("content", ""), end="", flush=True)
                elif chunk.get("type") == "complete":
                    print(chunk.get("content", ""), flush=True)
    except Exception as e:
        logger.error(f"Agent execution failed: {str(e)}", exc_info=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
'''
        
        # Write script
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)
        
        return script_path
    
    def _prepare_env(self) -> Dict[str, str]:
        """Prepare environment variables for shadow process."""
        env = dict(os.environ)
        # Add any necessary environment variables
        return env
    
    async def stop_shadow_process(self, process_id: str) -> bool:
        """
        Stop a shadow process.
        
        Args:
            process_id: Process ID
            
        Returns:
            True if stopped successfully
        """
        if process_id not in self._active_processes:
            return False
        
        shadow_process = self._active_processes[process_id]
        process = shadow_process.process
        
        try:
            if process.returncode is None:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutExpired:
                    process.kill()
                    await process.wait()
                
                shadow_process.status = "cancelled"
                shadow_process.end_time = datetime.utcnow().isoformat()
                return True
        except Exception as e:
            logger.error(f"Error stopping shadow process {process_id}: {e}", exc_info=True)
            return False
    
    def get_process_status(self, process_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a shadow process.
        
        Args:
            process_id: Process ID
            
        Returns:
            Process status dict or None if not found
        """
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
            "stderr_length": len(shadow_process.stderr)
        }
    
    def list_active_processes(self) -> List[Dict[str, Any]]:
        """List all active shadow processes."""
        return [
            self.get_process_status(process_id)
            for process_id in self._active_processes.keys()
        ]
    
    async def cleanup_completed_processes(self, max_age_hours: int = 24):
        """
        Clean up completed processes older than max_age_hours.
        
        Args:
            max_age_hours: Maximum age in hours for completed processes
        """
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


# Import os for environment
import os
from typing import List
