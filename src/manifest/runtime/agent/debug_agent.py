"""
Debug Agent - Analyzes and fixes bugs.
"""
from typing import Dict, Any, Optional, List, AsyncIterator
from manifest.runtime.agent.executor import AgentExecutor
from manifest.core.state_manager import StateManager


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
    """
    Debug agent - Bug analyzer and fixer.
    Analyzes test failures and guides Coder to fix bugs.
    """
    
    def __init__(
        self,
        agent_id: str,
        executor: AgentExecutor,
        state_manager: StateManager
    ):
        """
        Initialize Debug agent.
        
        Args:
            agent_id: Agent identifier
            executor: Agent executor for LLM calls
            state_manager: State manager
        """
        self.agent_id = agent_id
        self.executor = executor
        self.state_manager = state_manager
        self.message_history: List[Dict[str, str]] = []
    
    async def debug(
        self,
        test_results: Dict[str, Any],
        error_messages: List[str],
        context: Dict[str, Any],
        model_config: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Analyze bugs and propose fixes.
        
        Args:
            test_results: Test execution results
            error_messages: List of error messages
            context: Tiered context
            model_config: Model configuration
            
        Yields:
            Debug analysis output chunks
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
        """Generate debug prompt."""
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
    
    async def _save_response(self, content: str):
        """Save agent response to state."""
        channel = f"squad-{self.agent_id}-debug"
        self.state_manager.add_chat_message(channel, "assistant", content)
        await self.state_manager.save_state()
