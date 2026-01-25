"""
Debug agent for analyzing and fixing bugs.

This module provides the DebugAgent class which analyzes test failures and
error messages to identify root causes and propose fixes. The debug agent
can read files and analyze code to understand issues, then provide clear
instructions for the coder to implement fixes.
"""
import json
from typing import Dict, Any, Optional, List, AsyncIterator, TYPE_CHECKING
from manifest.runtime.agent.core.executor import AgentExecutor
from manifest.core.state_manager import StateManager
from manifest.runtime.tools.tool_executor import ToolExecutor
from manifest.runtime.tools.tool_definitions import get_tool_definitions

if TYPE_CHECKING:
    from manifest.runtime.router.terminal_router import TerminalRouter


DEBUG_IDENTITY = """
## DEBUG AGENT IDENTITY

**YOU ARE A DEBUG AGENT. YOU ANALYZE BUGS AND FIX THEM.**

Your role:
- Analyze test failures and error messages
- Identify root causes of bugs
- Propose fixes
- Guide Coder agent to implement fixes

You do NOT:
- Write code directly (that's the Coder's job)
- Skip analysis (always understand the problem first)

You DO:
- Analyze error messages and stack traces
- Identify root causes
- Propose specific fixes
- Provide clear instructions to Coder
"""


class DebugAgent:
    """Debug agent for analyzing bugs and proposing fixes.
    
    When tests fail, the debug agent analyzes the error messages and test
    results to identify root causes. It provides specific fix instructions
    for the coder agent to implement. The debug agent doesn't write code
    itself - it analyzes and guides.
    
    Attributes:
        agent_id: Unique identifier for this agent instance.
        executor: AgentExecutor for making LLM API calls.
        state_manager: StateManager for persisting debug analysis.
        message_history: List of conversation messages for context.
    """
    
    def __init__(
        self,
        agent_id: str,
        executor: AgentExecutor,
        state_manager: StateManager,
        terminal_router: Optional["TerminalRouter"] = None,
        tool_executor: Optional[ToolExecutor] = None
    ):
        """Initialize the debug agent.
        
        Args:
            agent_id: Unique identifier for this agent.
            executor: Executor instance for LLM API calls.
            state_manager: State manager for saving debug analysis.
            terminal_router: Optional terminal router for command execution.
            tool_executor: Optional tool executor for executing tool calls.
        """
        self.agent_id = agent_id
        self.executor = executor
        self.state_manager = state_manager
        self.terminal_router = terminal_router
        self.tool_executor = tool_executor
        self.message_history: List[Dict[str, str]] = []
        self.agent_type = "debug"
        
        # Track tool execution results
        self.tool_execution_summary: Dict[str, Any] = {
            "modified_files": [],
            "executed_commands": [],
            "read_files": [],
            "errors": [],
            "total_tool_calls": 0
        }
    
    async def debug(
        self,
        test_results: Dict[str, Any],
        error_messages: List[str],
        context: Dict[str, Any],
        model_config: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """Analyze test failures and propose fixes.
        
        Examines test results and error messages to understand what went
        wrong and why. Provides specific instructions for fixing the issues.
        The analysis is streamed in real-time and saved to state.
        
        Args:
            test_results: Dictionary containing test execution results
                including pass/fail counts and details.
            error_messages: List of error message strings from failed tests.
            context: Tiered context for understanding the codebase.
            model_config: Dictionary with provider, model, and api_key.
        
        Yields:
            Dictionaries with type "chunk" (streaming) or "complete" (finished).
            Content contains root cause analysis and fix instructions.
        """
        # Generate debug prompt
        prompt = self._generate_debug_prompt(test_results, error_messages, context)
        
        # Execute agent
        async for chunk in self.executor.execute_agent(
            agent_id=self.agent_id,
            agent_type="debug",
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
    
    def _generate_debug_prompt(
        self,
        test_results: Dict[str, Any],
        error_messages: List[str],
        context: Dict[str, Any]
    ) -> str:
        """Generate a prompt for debugging test failures.
        
        Creates a prompt that includes test results, error messages, and
        context to help the agent analyze what went wrong and propose fixes.
        
        Args:
            test_results: Test execution results dictionary.
            error_messages: List of error messages from failed tests.
            context: Tiered context for code understanding.
        
        Returns:
            Complete prompt string for debugging.
        """
        errors_text = "\n".join([f"- {msg}" for msg in error_messages])
        
        prompt = f"""
{DEBUG_IDENTITY}

## TEST RESULTS

{test_results}

## ERROR MESSAGES

{errors_text}

## CONTEXT

{context.get("tier_2", "No task-specific context")}

## YOUR TASK

1. Analyze the error messages and test results
2. Identify the root cause of each failure
3. Propose specific fixes
4. Provide clear instructions for the Coder agent to implement the fixes

Focus on:
- Understanding what went wrong
- Why it went wrong
- How to fix it
- What the Coder should change
"""
        return prompt
    
    async def _save_response(self, content: str) -> None:
        """Save debug analysis to state and chat history.
        
        Note: State saving is handled by agent_bridge._handle_agent_chunk()
        to avoid duplicate saves. This method is kept for backward compatibility.
        
        Args:
            content: The complete debug analysis content.
        """
        # State saving is handled by agent_bridge._handle_agent_chunk()
        # This method is kept for backward compatibility but does nothing
        pass
