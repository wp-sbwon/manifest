"""
Approver agent for final approval of Worker Squad work.

This module provides the ApproverAgent class which reviews all Worker Squad
stages (planner, coder, test, self-review) and makes a final decision to
approve or reject the work. If rejecting, provides specific feedback for
improvement.
"""
import json
from typing import Dict, Any, Optional, List, AsyncIterator, TYPE_CHECKING
from manifest.runtime.agent.core.executor import AgentExecutor
from manifest.core.state_manager import StateManager
from manifest.audit.code.quality_manager import CodeQualityManager

if TYPE_CHECKING:
    from manifest.runtime.router.terminal_router import TerminalRouter


APPROVER_IDENTITY = """
## APPROVER AGENT IDENTITY

**YOU ARE AN APPROVER AGENT. YOU APPROVE OR REJECT WORKER SQUAD WORK.**

Your role:
- Review Worker Squad output (Planner plan, Coder implementation, Test results, Self Review)
- Verify plan compliance
- Make final approval/rejection decision
- Provide feedback if rejecting

You do NOT:
- Write code (that's the Coder's job)
- Write tests (that's the Test agent's job)
- Plan (that's the Planner's job)

You DO:
- Review all Worker Squad stages
- Verify implementation matches plan
- Check quality and completeness
- Approve or reject with clear feedback
"""


class ApproverAgent:
    """Approver agent for final review and approval of Worker Squad work.
    
    The approver is the final gate in the Worker Squad workflow. It reviews
    all stages (planner plan, coder implementation, test results, self-review)
    and makes a decision: approve (work is complete) or reject (needs rework).
    
    If rejecting, provides specific feedback that guides the workflow back
    to the appropriate stage (usually coder) for fixes.
    
    Attributes:
        agent_id: Unique identifier for this agent instance.
        executor: AgentExecutor for making LLM API calls.
        state_manager: StateManager for persisting approval decisions.
        message_history: List of conversation messages for context.
    """
    
    def __init__(
        self,
        agent_id: str,
        executor: AgentExecutor,
        state_manager: StateManager,
        terminal_router: Optional["TerminalRouter"] = None
    ):
        """Initialize the approver agent.
        
        Args:
            agent_id: Unique identifier for this agent.
            executor: Executor instance for LLM API calls.
            state_manager: State manager for saving approval decisions.
            terminal_router: Optional terminal router for command execution.
        """
        self.agent_id = agent_id
        self.terminal_router = terminal_router
        self.executor = executor
        self.state_manager = state_manager
        self.message_history: List[Dict[str, str]] = []
        self.quality_manager = CodeQualityManager()
    
    async def approve(
        self,
        planner_output: str,
        coder_output: str,
        test_results: Dict[str, Any],
        self_review_result: Dict[str, Any],
        context: Dict[str, Any],
        model_config: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """Review all Worker Squad stages and make approval decision."""
        # Run automated quality checks
        quality_info = {}
        task_id = self.agent_id
        
        # Get files modified from coder output
        import re
        files = re.findall(r'(?:modified|changed|updated|created)\s+file[:\s]+(.+?)(?:\n|$)', coder_output, re.IGNORECASE)
        
        if files:
            quality_info["lint_results"] = {}
            quality_info["security_results"] = {}
            for f in files:
                f = f.strip()
                quality_info["lint_results"][f] = self.quality_manager.run_lint(f)
                quality_info["security_results"][f] = self.quality_manager.run_security_check(f)
        
        # Check architecture compliance if component_id is available
        component_id = context.get("component_id")
        if component_id and files:
            quality_info["architecture_compliance"] = self.quality_manager.check_architecture_compliance(files[0], component_id)

        # Generate approval prompt with quality info
        prompt = self._generate_approval_prompt(
            planner_output, coder_output, test_results, self_review_result, context, quality_info
        )
        
        # Execute agent
        async for chunk in self.executor.execute_agent(
            agent_id=self.agent_id,
            agent_type="approver",
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
    
    def _generate_approval_prompt(
        self,
        planner_output: str,
        coder_output: str,
        test_results: Dict[str, Any],
        self_review_result: Dict[str, Any],
        context: Dict[str, Any],
        quality_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a prompt for approval review."""
        prompt = f"""
{APPROVER_IDENTITY}

## PLANNER OUTPUT

{planner_output}

## CODER OUTPUT

{coder_output}

## TEST RESULTS

{test_results}

## SELF REVIEW RESULT

{self_review_result}
"""
        if quality_info:
            prompt += f"""
## AUTOMATED QUALITY CHECKS

{json.dumps(quality_info, indent=2)}
"""

        prompt += f"""
## CONTEXT

{context.get("tier_2", "No task-specific context")}

## YOUR TASK

1. Review all Worker Squad stages
2. Verify implementation matches the plan
3. Check test results (all tests should pass)
4. Review self-review findings
5. Review automated quality checks (lint, security, architecture)
6. Make a decision: APPROVE or REJECT

If APPROVING:
- Confirm all requirements are met
- Confirm plan compliance
- Confirm tests pass
- Confirm code quality standards are met

If REJECTING:
- Clearly state what is missing or incorrect
- Provide specific feedback for improvement
- Indicate which stage needs rework (usually Coder)

Output your decision in this format:
DECISION: APPROVED|REJECTED
FEEDBACK: [your feedback here]
"""
        return prompt
    
    async def _save_response(self, content: str) -> None:
        """Save approval decision to state and chat history.
        
        Writes the approver's decision and feedback to the appropriate channel
        so it can be displayed in the UI and used to determine next steps
        in the workflow.
        
        Args:
            content: The complete approval decision and feedback content.
        """
        channel = f"squad-{self.agent_id}-approver"
        self.state_manager.add_chat_message(channel, "assistant", content)
        await self.state_manager.save_state()
