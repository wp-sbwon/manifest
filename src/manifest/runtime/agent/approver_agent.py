"""
Approver Agent - Approves worker squad work.
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
    """
    Approver agent - Worker Squad final approver.
    Reviews all stages and approves or rejects work.
    """
    
    def __init__(
        self,
        agent_id: str,
        executor: AgentExecutor,
        state_manager: StateManager
    ):
        """
        Initialize Approver agent.
        
        Args:
            agent_id: Agent identifier
            executor: Agent executor for LLM calls
            state_manager: State manager
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
        """
        Review and approve/reject Worker Squad work.
        
        Args:
            planner_output: Planner's plan
            coder_output: Coder's implementation summary
            test_results: Test execution results
            self_review_result: Self review findings
            context: Tiered context
            model_config: Model configuration
            
        Yields:
            Approval decision output chunks
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
        """Generate approval prompt."""
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
    
    async def _save_response(self, content: str):
        """Save agent response to state."""
        channel = f"squad-{self.agent_id}-approver"
        self.state_manager.add_chat_message(channel, "assistant", content)
        await self.state_manager.save_state()
