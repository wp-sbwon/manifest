"""
Approver agent for final approval of Worker Squad work.

This module provides the ApproverAgent class which reviews all Worker Squad
stages (planner, coder, test, self-review) and makes a final decision to
approve or reject the work. If rejecting, provides specific feedback for
improvement.
"""
from typing import Dict, Any, Optional, List, AsyncIterator
from manifest.runtime.agent.executor import AgentExecutor
from manifest.core.state_manager import StateManager


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
        state_manager: StateManager
    ):
        """Initialize the approver agent.
        
        Args:
            agent_id: Unique identifier for this agent.
            executor: Executor instance for LLM API calls.
            state_manager: State manager for saving approval decisions.
        """
        self.agent_id = agent_id
        self.executor = executor
        self.state_manager = state_manager
        self.message_history: List[Dict[str, str]] = []
    
    async def approve(
        self,
        planner_output: str,
        coder_output: str,
        test_results: Dict[str, Any],
        self_review_result: Dict[str, Any],
        context: Dict[str, Any],
        model_config: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """Review all Worker Squad stages and make approval decision.
        
        Examines the complete workflow output: planner's plan, coder's
        implementation, test results, and self-review findings. Verifies
        that implementation matches the plan, tests pass, and quality
        standards are met.
        
        Args:
            planner_output: The original plan created by the planner.
            coder_output: Summary of what the coder implemented.
            test_results: Results from test execution (pass/fail counts, details).
            self_review_result: Findings from coder's self-review.
            context: Tiered context for additional context.
            model_config: Dictionary with provider, model, and api_key.
        
        Yields:
            Dictionaries with type "chunk" (streaming) or "complete" (finished).
            Content contains the approval decision (APPROVED/REJECTED) and
            feedback explaining the decision.
        """
        # Generate approval prompt
        prompt = self._generate_approval_prompt(
            planner_output, coder_output, test_results, self_review_result, context
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
        context: Dict[str, Any]
    ) -> str:
        """Generate a prompt for approval review.
        
        Creates a comprehensive prompt that includes all Worker Squad stage
        outputs and asks the agent to review them and make an approval decision.
        
        Args:
            planner_output: Planner's plan text.
            coder_output: Coder's implementation summary.
            test_results: Test execution results dictionary.
            self_review_result: Self-review findings dictionary.
            context: Tiered context for additional information.
        
        Returns:
            Complete prompt string for approval review.
        """
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

## CONTEXT

{context.get("tier_2", "No task-specific context")}

## YOUR TASK

1. Review all Worker Squad stages
2. Verify implementation matches the plan
3. Check test results (all tests should pass)
4. Review self-review findings
5. Make a decision: APPROVE or REJECT

If APPROVING:
- Confirm all requirements are met
- Confirm plan compliance
- Confirm tests pass

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
