"""
Coder agent for code implementation.

This module provides the CoderAgent class which implements code based on
planner plans and task requirements. The coder agent receives scoped context
(Tier 0, 2-3) and implements code within the allowed boundaries.

The coder can also perform self-review to verify its implementation complies
with the original plan.
"""
import json
from typing import Dict, Any, Optional, List, AsyncIterator, TYPE_CHECKING
from manifest.runtime.agent.core.base_executor import BaseAgentExecutor
from manifest.runtime.agent.prompts.coder_prompt import get_coder_prompt
from manifest.core.state_manager import StateManager
from manifest.runtime.tools.tool_executor import ToolExecutor
from manifest.runtime.tools.tool_definitions import get_tool_definitions

if TYPE_CHECKING:
    from manifest.runtime.router.terminal_router import TerminalRouter


class CoderAgent:
    """Coder agent for implementing code based on plans.

    The coder agent receives a task description, planner's plan, and scoped
    context, then implements the code to fulfill the requirements. It works
    within task boundaries to ensure it only modifies allowed files and
    components.

    Attributes:
        agent_id: Unique identifier for this agent instance.
        executor: Backend executor for LLM and tool execution.
        state_manager: StateManager for persisting agent output.
        message_history: List of conversation messages for context.
        terminal_router: Optional TerminalRouter for executing commands.
    """

    def __init__(
        self,
        agent_id: str,
        executor: BaseAgentExecutor,
        state_manager: StateManager,
        terminal_router: Optional["TerminalRouter"] = None,
        tool_executor: Optional[ToolExecutor] = None
    ):
        """Initialize the coder agent.

        Args:
            agent_id: Unique identifier for this agent.
            executor: Executor instance for LLM API calls.
            state_manager: State manager for saving agent output to channels.
            terminal_router: Optional; tool_executor preferred for commands.
            tool_executor: Optional tool executor for executing tool calls.
                This is the primary way to execute commands and file operations.
        """
        self.agent_id = agent_id
        self.executor = executor
        self.state_manager = state_manager
        self.terminal_router = terminal_router
        self.tool_executor = tool_executor
        self.message_history: List[Dict[str, str]] = []
        self.agent_type = "coder"
        self.message_bus = None  # Will be set by agent_bridge when agent is registered
        self._implementation_status: Optional[Dict[str, Any]] = None  # Store implementation status

        # Track tool execution results for completion detection
        self.tool_execution_summary: Dict[str, Any] = {
            "modified_files": [],
            "executed_commands": [],
            "read_files": [],
            "errors": [],
            "total_tool_calls": 0
        }

    async def implement(
        self,
        task_description: str,
        context: Dict[str, Any],
        task_scope: Optional[Dict[str, Any]],
        model_config: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """Implement code for a task based on the planner's plan.

        Generates a coder-specific prompt with task description, context,
        and scope boundaries, then executes the agent with tool use support.
        Handles tool execution loop: LLM generates tool calls, we execute them,
        and feed results back to LLM until completion.

        Args:
            task_description: Description of what needs to be implemented.
            context: Tiered context dictionary (Tier 0, 2-3 for workers).
            task_scope: Dictionary defining what files/components can be
                modified. Includes allowed_files, allowed_components, etc.
            model_config: Dictionary with provider, model, and api_key.

        Yields:
            Dictionaries with type "chunk" (streaming), "tool_use", "tool_result",
            or "complete" (finished).
        """
        # Generate prompt
        prompt = get_coder_prompt(
            task_description=task_description,
            context=context,
            task_scope=task_scope,
            available_tools=context.get("available_tools", [])
        )

        # Get tool definitions
        tools = get_tool_definitions()

        # Reset tool execution summary for this implementation
        self.tool_execution_summary = {
            "modified_files": [],
            "executed_commands": [],
            "read_files": [],
            "errors": [],
            "total_tool_calls": 0
        }

        # Tool execution loop
        max_iterations = 10  # Prevent infinite loops
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Execute agent with tools
            tool_calls_in_this_round = []
            full_response = ""

            async for chunk in self.executor.execute_agent(
                agent_id=self.agent_id,
                agent_type="coder",
                prompt=prompt if iteration == 1 else None,  # Only send prompt on first iteration
                model_config=model_config,
                context=context,
                message_history=self.message_history,
                tools=tools
            ):
                chunk_type = chunk.get("type")

                if chunk_type == "chunk":
                    content = chunk.get("content", "")
                    full_response += content
                    yield chunk
                elif chunk_type == "tool_use" or chunk_type == "tool_use_start":
                    # Collect tool calls
                    tool_call = chunk.get("tool_call")
                    if tool_call:
                        tool_calls_in_this_round.append(tool_call)
                        yield chunk
                elif chunk_type == "tool_use_complete":
                    # All tool calls collected
                    tool_calls = chunk.get("tool_calls", [])
                    tool_calls_in_this_round.extend(tool_calls)
                    yield chunk
                elif chunk_type == "complete":
                    full_response = chunk.get("content", full_response)
                    # Save complete response to message history
                    if full_response:
                        if not self.message_history or self.message_history[-1]["role"] != "assistant":
                            self.message_history.append({"role": "assistant", "content": full_response})
                        else:
                            self.message_history[-1]["content"] = full_response
                    # Store implementation status for message responses
                    self._implementation_status = {
                        "tool_execution_summary": self.tool_execution_summary.copy(),
                        "modified_files": self.tool_execution_summary.get("modified_files", []),
                        "executed_commands": self.tool_execution_summary.get("executed_commands", []),
                        "agent_id": self.agent_id,
                        "timestamp": __import__("time").time()
                    }

                    # Yield complete chunk for UI display with tool_execution_summary
                    # This summary will be used by next stages (test, debug) to know what was modified
                    complete_chunk = chunk.copy()
                    complete_chunk["tool_execution_summary"] = self.tool_execution_summary.copy()
                    yield complete_chunk
                elif chunk_type == "error":
                    # Include tool execution summary in error
                    error_chunk = chunk.copy()
                    error_chunk["tool_execution_summary"] = self.tool_execution_summary.copy()
                    yield error_chunk
                    return

            # Execute tool calls if any
            if tool_calls_in_this_round and self.tool_executor:
                # Track tool execution
                self.tool_execution_summary["total_tool_calls"] += len(tool_calls_in_this_round)

                # Execute all tool calls
                tool_results = await self.tool_executor.execute_tool_calls(tool_calls_in_this_round)

                # Parse tool results to track what was done
                for i, tool_call in enumerate(tool_calls_in_this_round):
                    tool_name = tool_call.get("name", "unknown")
                    tool_input = tool_call.get("input", {})
                    tool_result = tool_results[i] if i < len(tool_results) else {}

                    # Track file modifications
                    if tool_name == "edit" or tool_name == "write":
                        file_path = tool_input.get("file_path", "unknown")
                        if file_path not in self.tool_execution_summary["modified_files"]:
                            self.tool_execution_summary["modified_files"].append(file_path)

                    # Track file reads
                    elif tool_name == "read":
                        file_path = tool_input.get("file_path", "unknown")
                        if file_path not in self.tool_execution_summary["read_files"]:
                            self.tool_execution_summary["read_files"].append(file_path)

                    # Track command executions
                    elif tool_name == "bash":
                        command = tool_input.get("command", "unknown")
                        args = tool_input.get("args", [])
                        full_command = f"{command} {' '.join(args) if args else ''}".strip()
                        self.tool_execution_summary["executed_commands"].append(full_command)

                    # Track errors and permission issues
                    if tool_result.get("error"):
                        error_info = {
                            "tool": tool_name,
                            "error": tool_result.get("error"),
                            "file_path": tool_input.get("file_path") if tool_name in ["edit", "write", "read"] else None
                        }
                        # Track permission issues separately
                        if tool_result.get("permission_denied"):
                            error_info["permission_denied"] = True
                        if tool_result.get("permission_required"):
                            error_info["permission_required"] = True
                            error_info["permission_details"] = tool_result.get("permission_details", {})
                        self.tool_execution_summary["errors"].append(error_info)

                    # Track validation results
                    validation = tool_result.get("validated", {})
                    if not validation.get("success"):
                        # Add validation errors to summary
                        validation_errors = validation.get("validation_errors", [])
                        for val_error in validation_errors:
                            if val_error not in [e.get("error") for e in self.tool_execution_summary["errors"]]:
                                self.tool_execution_summary["errors"].append({
                                    "tool": tool_name,
                                    "error": f"Validation failed: {val_error}",
                                    "file_path": tool_input.get("file_path") if tool_name in ["edit", "write", "read"] else None
                                })

                    # Track validation warnings
                    validation_warnings = validation.get("warnings", [])
                    if validation_warnings:
                        if "validation_warnings" not in self.tool_execution_summary:
                            self.tool_execution_summary["validation_warnings"] = []
                        self.tool_execution_summary["validation_warnings"].extend(validation_warnings)

                # Format tool results for Anthropic API (tool_result content blocks)
                provider = model_config.get("provider", "anthropic")

                if provider == "anthropic":
                    # Anthropic format: tool_result content blocks
                    for result in tool_results:
                        tool_id = result.get("tool_call_id", "unknown")
                        tool_name = result.get("tool_name", "unknown")
                        tool_result = result.get("result")
                        error = result.get("error")

                        if error:
                            tool_result_content = f"Error: {error}"
                        else:
                            # Format result as JSON string
                            tool_result_content = json.dumps(tool_result, indent=2) if tool_result else "null"

                        # Add tool_result to message history in Anthropic format
                        self.message_history.append({
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": tool_id,
                                    "content": tool_result_content
                                }
                            ]
                        })

                        # Yield tool result for UI
                        yield {
                            "type": "tool_result",
                            "tool_call_id": tool_id,
                            "tool_name": tool_name,
                            "result": tool_result,
                            "error": error
                        }
                else:
                    # OpenAI format: function role messages
                    for result in tool_results:
                        tool_id = result.get("tool_call_id", "unknown")
                        tool_name = result.get("tool_name", "unknown")
                        tool_result = result.get("result")
                        error = result.get("error")

                        if error:
                            tool_result_content = f"Error: {error}"
                        else:
                            tool_result_content = json.dumps(tool_result, indent=2) if tool_result else "null"

                        self.message_history.append({
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "name": tool_name,
                            "content": tool_result_content
                        })

                        yield {
                            "type": "tool_result",
                            "tool_call_id": tool_id,
                            "tool_name": tool_name,
                            "result": tool_result,
                            "error": error
                        }

                # Continue loop to get LLM response to tool results
                # Update prompt to None so we just continue conversation
                prompt = None
            else:
                # No tool calls, we're done
                if full_response:
                    await self._save_response(full_response)
                    # Yield final complete chunk with tool_execution_summary
                    yield {
                        "type": "complete",
                        "content": full_response,
                        "tool_execution_summary": self.tool_execution_summary.copy()
                    }
                break

        if iteration >= max_iterations:
            yield {
                "type": "error",
                "content": f"Maximum tool execution iterations ({max_iterations}) reached",
                "tool_execution_summary": self.tool_execution_summary.copy()
            }

    async def _save_response(self, content: str):
        """Save agent response to state. No-op; state saved by bridge.

        Args:
            content: The complete agent output content.
        """
        # State saving is handled by agent_bridge._handle_agent_chunk()
        pass

    async def self_review(
        self,
        planner_plan: str,
        implementation_summary: str,
        context: Dict[str, Any],
        model_config: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Self-review implementation against plan.

        Args:
            planner_plan: Planner's plan
            implementation_summary: Summary of implementation
            context: Tiered context
            model_config: Model configuration

        Yields:
            Self-review output chunks
        """
        # Generate self-review prompt
        prompt = self._generate_self_review_prompt(planner_plan, implementation_summary, context)

        # Execute agent
        async for chunk in self.executor.execute_agent(
            agent_id=self.agent_id,
            agent_type="coder",
            prompt=prompt,
            model_config=model_config,
            context=context,
            message_history=self.message_history
        ):
            # Save to message history
            if chunk.get("type") == "chunk":
                if not self.message_history or self.message_history[-1]["role"] != "assistant":
                    self.message_history.append({"role": "assistant", "content": ""})
                self.message_history[-1]["content"] += chunk.get("content", "")
            elif chunk.get("type") == "complete":
                # Save complete response
                await self._save_response(chunk.get("content", ""))

            yield chunk

    async def handle_message(self, message: "AgentMessage") -> None:
        """Handle incoming messages from other agents.

        Supports request-response pattern for agent-to-agent communication.
        Coder can respond to requests for implementation status, modified files, etc.

        Args:
            message: AgentMessage instance containing message details.
        """
        from manifest.agents.agent_message_bus import AgentMessage, MessageType
        from manifest.core.logger import get_logger

        logger = get_logger(__name__)

        if message.message_type == MessageType.REQUEST:
            # Handle request messages
            subject = message.subject.lower()
            content = message.content or {}

            if subject in ("implementation_status", "get_status", "status"):
                # Respond with implementation status
                response_content = {
                    "status": self._implementation_status or {},
                    "has_implementation": self._implementation_status is not None,
                    "agent_id": self.agent_id
                }
                if self.message_bus:
                    await self.message_bus.respond(
                        from_agent_id=self.agent_id,
                        correlation_id=(message.correlation_id or message.message_id),
                        content=response_content,
                        success=True
                    )

            elif subject in ("modified_files", "get_files", "files"):
                # Respond with list of modified files
                modified_files = []
                if self._implementation_status:
                    modified_files = self._implementation_status.get("modified_files", [])

                response_content = {
                    "modified_files": modified_files,
                    "agent_id": self.agent_id
                }
                if self.message_bus:
                    await self.message_bus.respond(
                        from_agent_id=self.agent_id,
                        correlation_id=(message.correlation_id or message.message_id),
                        content=response_content,
                        success=True
                    )

            elif subject in ("tool_summary", "get_tool_summary"):
                # Respond with tool execution summary
                tool_summary = {}
                if self._implementation_status:
                    tool_summary = self._implementation_status.get("tool_execution_summary", {})

                response_content = {
                    "tool_summary": tool_summary,
                    "agent_id": self.agent_id
                }
                if self.message_bus:
                    await self.message_bus.respond(
                        from_agent_id=self.agent_id,
                        correlation_id=(message.correlation_id or message.message_id),
                        content=response_content,
                        success=True
                    )

            else:
                # Unknown request - respond with error
                if self.message_bus:
                    await self.message_bus.respond(
                        from_agent_id=self.agent_id,
                        correlation_id=(message.correlation_id or message.message_id),
                        content={"error": f"Unknown request subject: {subject}"},
                        success=False
                    )

        elif message.message_type == MessageType.NOTIFICATION:
            # Handle notifications (one-way messages)
            logger.debug(f"Coder {self.agent_id} received notification: {message.subject}")

    def _generate_self_review_prompt(
        self,
        planner_plan: str,
        implementation_summary: str,
        context: Dict[str, Any]
    ) -> str:
        """Generate a prompt for self-review mode.

        Creates a prompt that asks the coder to compare its implementation
        against the planner's plan and identify any discrepancies.

        Args:
            planner_plan: The original plan to compare against.
            implementation_summary: Summary of what was implemented.
            context: Tiered context for additional information.

        Returns:
            Complete prompt string for self-review.
        """
        prompt = f"""
## SELF REVIEW MODE

You are reviewing your own implementation against the Planner's plan.

## PLANNER'S PLAN

{planner_plan}

## YOUR IMPLEMENTATION

{implementation_summary}

## CONTEXT

{context.get("tier_2", "No task-specific context")}

## YOUR TASK

1. Compare your implementation with the Planner's plan
2. Identify any differences or deviations
3. Verify all plan requirements are met
4. Check for any missing features or functionality
5. Assess plan compliance

Output your review in this format:
PLAN_COMPLIANCE: COMPLIANT|NON_COMPLIANT
DIFFERENCES:
- [difference 1]
- [difference 2]
MISSING_FEATURES:
- [missing feature 1]
- [missing feature 2]
FINDINGS:
- [finding 1]
- [finding 2]
"""
        return prompt
