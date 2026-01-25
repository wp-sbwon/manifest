"""
Agent Runner - Entry point for agents running in containers.
Initializes the agent environment and executes the agent mission.
"""
import asyncio
import argparse
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from manifest.core.state_manager import StateManager
from manifest.core.config import get_config_manager
from manifest.agents.context_provider import ContextProvider
from manifest.agents.container_communication import ContainerMessageBus, ContainerStateSync
from manifest.runtime.agent.core.manager import AgentManager
from manifest.runtime.agent.core.executor import AgentExecutor
from manifest.runtime.permissions.permission_manager import PermissionManager
from manifest.runtime.router.terminal_router import TerminalRouter
from manifest.runtime.tools.tool_executor import ToolExecutor
from manifest.runtime.tools.file_manager import FileManager
from manifest.core.logger import get_logger

logger = get_logger(__name__)


async def run_agent(task_id: str, agent_type: str):
    """
    Run an agent in a container environment.
    
    Args:
        task_id: ID of the task to work on.
        agent_type: Type of agent to run.
    """
    logger.info(f"Starting agent runner for task {task_id}, type {agent_type}")
    
    # Initialize core components
    manifest_dir = Path("/app/.manifest")
    state_manager = StateManager(manifest_dir)
    config_manager = get_config_manager()
    
    # Initialize communication
    # In a container, the base_url should point to the host machine or main app container
    # Defaulting to manifest-app which should be defined in the docker network
    base_url = os.environ.get("MANIFEST_API_URL", "http://manifest-app:8000")
    message_bus = ContainerMessageBus(base_url=base_url, agent_id=task_id)
    await message_bus.connect()
    
    state_sync = ContainerStateSync(state_manager, message_bus)
    await state_sync.start()
    
    # Initialize agent components
    from manifest.agents.task_scoper import TaskScoper
    task_scoper = TaskScoper(manifest_dir)
    context_provider = ContextProvider(manifest_dir, task_scoper)
    
    executor = AgentExecutor(state_manager, config_manager)
    agent_manager = AgentManager(executor, state_manager)

    # Initialize PermissionManager for this agent type
    permission_manager = PermissionManager(
        config_manager=config_manager,
        agent_type=agent_type
    )
    
    # Initialize TerminalRouter with permission checking
    terminal_router = TerminalRouter(
        working_dir=Path("/app"),
        permission_manager=permission_manager,
        agent_type=agent_type
    )
    
    # Initialize FileManager with permission checking
    file_manager = FileManager(
        working_dir=Path("/app"),
        permission_manager=permission_manager,
        agent_type=agent_type
    )
    
    # Initialize ToolExecutor
    tool_executor = ToolExecutor(
        terminal_router=terminal_router,
        file_manager=file_manager
    )
    
    try:
        # Get context for the agent
        # The context might be passed via environment variables or fetched from state
        context = context_provider.get_worker_context(task_id, agent_type)
        model_config = config_manager.get_agent_model_config(agent_type)
        
        # Update status to active
        await message_bus.send_message(
            topic="agent-status",
            message={
                "task_id": task_id,
                "agent_type": agent_type,
                "status": "active",
                "timestamp": __import__("datetime").datetime.now().isoformat()
            }
        )
        
        # Create and run agent with terminal router and tool executor
        agent_dict = await agent_manager.create_agent(
            agent_type=agent_type,
            context=context,
            model_config=model_config,
            task_id=task_id,
            terminal_router=terminal_router,
            tool_executor=tool_executor
        )
        if not agent_dict:
            raise ValueError(f"Failed to create agent of type {agent_type}")
        
        # Get the actual agent instance
        agent = agent_dict.get("instance")
        if not agent:
            raise ValueError(f"Agent instance not found for type {agent_type}")
            
        # Execute agent mission
        # Note: This part depends on how different agent types are executed.
        # For now, we assume a generic execution pattern.
        logger.info(f"Executing agent {agent_type} for task {task_id}")
        
        # Get task description from context
        task_description = context.get("task_description", "No description provided")
        
        # Execution logic based on agent type
        if agent_type == "planner":
            async for chunk in agent.plan(task_description, context, model_config):
                if chunk.get("type") == "complete":
                    logger.info(f"Planner completed for task {task_id}")
        elif agent_type == "coder":
            task_scope = context.get("task_scope", {})
            async for chunk in agent.implement(task_description, context, task_scope, model_config):
                if chunk.get("type") == "complete":
                    logger.info(f"Coder completed for task {task_id}")
        elif agent_type == "test":
            # Test agent might have different methods based on stage
            stage = os.environ.get("AGENT_STAGE", "test")
            if stage == "tdd_test":
                async for chunk in agent.write_tdd_tests(task_id, context, model_config):
                    pass
            else:
                async for chunk in agent.run_tests(task_id, context, model_config):
                    pass
        # Add other agent types as needed...
        
        # Mark as completed
        await message_bus.send_message(
            topic="agent-status",
            message={
                "task_id": task_id,
                "agent_type": agent_type,
                "status": "completed",
                "timestamp": __import__("datetime").datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error running agent: {e}", exc_info=True)
        # Report failure
        await message_bus.send_message(
            topic="agent-status",
            message={
                "task_id": task_id,
                "agent_type": agent_type,
                "status": "failed",
                "error": str(e),
                "timestamp": __import__("datetime").datetime.now().isoformat()
            }
        )
    finally:
        # Cleanup
        await state_sync.stop()
        await message_bus.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manifest Agent Runner")
    parser.add_argument("--task-id", required=True, help="Task ID to work on")
    parser.add_argument("--agent-type", required=True, help="Type of agent to run")
    
    args = parser.parse_args()
    
    asyncio.run(run_agent(args.task_id, args.agent_type))
