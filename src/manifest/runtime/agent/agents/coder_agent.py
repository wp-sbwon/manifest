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
from manifest.runtime.agent.core.executor import AgentExecutor
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
        executor: AgentExecutor for making LLM API calls.
        state_manager: StateManager for persisting agent output.
        message_history: List of conversation messages for context.
        terminal_router: Optional TerminalRouter for executing commands.
    """
    
    def __init__(
        self,
        agent_id: str,
        executor: AgentExecutor,
        state_manager: StateManager,
        terminal_router: Optional["TerminalRouter"] = None,
        tool_executor: Optional[ToolExecutor] = None
    ):
        """Initialize the coder agent.
        
        Args:
            agent_id: Unique identifier for this agent.
            executor: Executor instance for LLM API calls.
            state_manager: State manager for saving agent output to channels.
            terminal_router: Optional terminal router for command execution.
            tool_executor: Optional tool executor for executing tool calls.
        """
        self.agent_id = agent_id
        self.executor = executor
        self.state_manager = state_manager
        self.terminal_router = terminal_router
        self.tool_executor = tool_executor
        self.message_history: List[Dict[str, str]] = []
        self.agent_type = "coder"
    
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
                    yield chunk
                elif chunk_type == "error":
                    yield chunk
                    return
            
            # Execute tool calls if any
            if tool_calls_in_this_round and self.tool_executor:
                # Execute all tool calls
                tool_results = await self.tool_executor.execute_tool_calls(tool_calls_in_this_round)
                
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
                break
        
        if iteration >= max_iterations:
            yield {
                "type": "error",
                "content": f"Maximum tool execution iterations ({max_iterations}) reached"
            }
    
    async def _save_response(self, content: str):
        """Save agent response to state."""
        channel = f"squad-{self.agent_id}-coder"
        self.state_manager.add_chat_message(channel, "assistant", content)
        await self.state_manager.save_state()
    
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
