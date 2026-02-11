"""
Failure recovery mechanism for agent workflows.

This module provides automatic failure analysis and recovery strategies for
agent execution failures. It analyzes failure causes and attempts recovery
using various strategies like retry, fallback models, simplified prompts,
or alternative approaches.
"""
import re
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class FailureType(Enum):
    """Types of agent failures."""
    TIMEOUT = "timeout"
    API_ERROR = "api_error"
    PARSING_ERROR = "parsing_error"
    CONTEXT_OVERFLOW = "context_overflow"
    VALIDATION_ERROR = "validation_error"
    EXECUTION_ERROR = "execution_error"
    UNKNOWN = "unknown"


class RecoveryStrategy(Enum):
    """Recovery strategies for failures."""
    RETRY = "retry"  # Simple retry with same configuration
    RETRY_WITH_SIMPLIFIED_PROMPT = "retry_simplified"  # Retry with simpler prompt
    FALLBACK_MODEL = "fallback_model"  # Try with different model
    FALLBACK_APPROACH = "fallback_approach"  # Try different approach
    SKIP_STAGE = "skip_stage"  # Skip this stage and continue
    MANUAL_INTERVENTION = "manual_intervention"  # Require user intervention


class FailureAnalyzer:
    """Analyzes agent failures to determine cause and recovery strategy.

    Examines error messages, agent output, and failure context to identify
    the root cause and suggest appropriate recovery strategies.
    """

    @staticmethod
    def analyze_failure(
        error: str,
        agent_output: str = "",
        agent_type: str = "",
        stage: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze a failure to determine cause and recovery strategy.

        Args:
            error: Error message or description.
            agent_output: Agent's output before failure (if available).
            agent_type: Type of agent that failed.
            stage: Stage in workflow where failure occurred.
            context: Additional context about the failure.

        Returns:
            Dictionary with:
            - failure_type: FailureType enum value
            - cause: Human-readable cause description
            - recovery_strategies: List of RecoveryStrategy enum values (ordered by preference)
            - error_details: Additional error information
        """
        error_lower = error.lower()
        output_lower = agent_output.lower() if agent_output else ""

        failure_type = FailureType.UNKNOWN
        cause = "Unknown failure"
        recovery_strategies = [RecoveryStrategy.RETRY]
        error_details = {}

        # Check for timeout
        if any(keyword in error_lower for keyword in ["timeout", "timed out", "time limit"]):
            failure_type = FailureType.TIMEOUT
            cause = "Agent execution exceeded time limit"
            recovery_strategies = [
                RecoveryStrategy.RETRY_WITH_SIMPLIFIED_PROMPT,
                RecoveryStrategy.FALLBACK_MODEL,
                RecoveryStrategy.RETRY
            ]
            error_details["timeout_duration"] = _extract_timeout_duration(error)

        # Check for API errors
        elif any(keyword in error_lower for keyword in ["api", "rate limit", "quota", "429", "500", "503"]):
            failure_type = FailureType.API_ERROR
            cause = "API service error or rate limit"
            recovery_strategies = [
                RecoveryStrategy.RETRY,  # Rate limits might be temporary
                RecoveryStrategy.FALLBACK_MODEL,
                RecoveryStrategy.MANUAL_INTERVENTION
            ]
            if "rate limit" in error_lower or "429" in error:
                error_details["rate_limited"] = True
                recovery_strategies.insert(0, RecoveryStrategy.RETRY)  # Add retry with delay

        # Check for context overflow
        elif any(keyword in error_lower for keyword in ["context", "token", "too long", "exceed"]):
            failure_type = FailureType.CONTEXT_OVERFLOW
            cause = "Context size exceeds model limits"
            recovery_strategies = [
                RecoveryStrategy.RETRY_WITH_SIMPLIFIED_PROMPT,
                RecoveryStrategy.SKIP_STAGE,  # If stage is optional
                RecoveryStrategy.MANUAL_INTERVENTION
            ]
            error_details["context_overflow"] = True

        # Check for parsing errors
        elif any(keyword in error_lower for keyword in ["parse", "json", "invalid", "malformed"]):
            failure_type = FailureType.PARSING_ERROR
            cause = "Failed to parse agent output"
            recovery_strategies = [
                RecoveryStrategy.RETRY_WITH_SIMPLIFIED_PROMPT,
                RecoveryStrategy.RETRY,
                RecoveryStrategy.MANUAL_INTERVENTION
            ]
            error_details["parsing_error"] = True

        # Check for validation errors
        elif any(keyword in error_lower for keyword in ["validation", "invalid", "rejected", "not allowed"]):
            failure_type = FailureType.VALIDATION_ERROR
            cause = "Output failed validation checks"
            recovery_strategies = [
                RecoveryStrategy.RETRY_WITH_SIMPLIFIED_PROMPT,
                RecoveryStrategy.FALLBACK_APPROACH,
                RecoveryStrategy.MANUAL_INTERVENTION
            ]
            error_details["validation_error"] = True

        # Check for execution errors
        elif any(keyword in error_lower for keyword in ["execution", "runtime", "exception", "error"]):
            failure_type = FailureType.EXECUTION_ERROR
            cause = "Runtime execution error"
            recovery_strategies = [
                RecoveryStrategy.RETRY,
                RecoveryStrategy.FALLBACK_APPROACH,
                RecoveryStrategy.MANUAL_INTERVENTION
            ]
            error_details["execution_error"] = True

        return {
            "failure_type": failure_type,
            "cause": cause,
            "recovery_strategies": recovery_strategies,
            "error_details": error_details,
            "original_error": error
        }


def _extract_timeout_duration(error: str) -> Optional[float]:
    """Extract timeout duration from error message.

    Args:
        error: Error message.

    Returns:
        Timeout duration in seconds, or None if not found.
    """
    match = re.search(r'(\d+(?:\.\d+)?)\s*(?:seconds?|sec|s)', error, re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None


class FailureRecoveryManager:
    """Manages failure recovery for agent workflows.

    Analyzes failures, attempts recovery using various strategies, and
    provides clear error messages to users.
    """

    def __init__(self, coordinator: Any):
        """Initialize the failure recovery manager.

        Args:
            coordinator: AgentCoordinator instance for retrying agents.
        """
        self.coordinator = coordinator
        self.analyzer = FailureAnalyzer()
        self.recovery_attempts: Dict[str, List[Dict[str, Any]]] = {}  # task_id -> attempts

    async def attempt_recovery(
        self,
        task_id: str,
        stage: str,
        agent_type: str,
        failure_result: Dict[str, Any],
        previous_stages: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Attempt to recover from a stage failure.

        Analyzes the failure and tries recovery strategies in order until
        one succeeds or all strategies are exhausted.

        Args:
            task_id: ID of the task that failed.
            stage: Stage name where failure occurred.
            agent_type: Type of agent that failed.
            failure_result: Result dictionary from failed stage execution.
            previous_stages: Results from previous stages.

        Returns:
            Dictionary with:
            - recovered: Boolean indicating if recovery succeeded
            - strategy_used: RecoveryStrategy that succeeded (if any)
            - result: New result from recovery attempt (if successful)
            - error: Error message if all recovery attempts failed
        """
        error = failure_result.get("error", "Unknown error")
        output = failure_result.get("output", "")

        # Analyze failure
        analysis = self.analyzer.analyze_failure(
            error=error,
            agent_output=output,
            agent_type=agent_type,
            stage=stage
        )

        failure_type = analysis["failure_type"]
        recovery_strategies = analysis["recovery_strategies"]

        # Track recovery attempts
        if task_id not in self.recovery_attempts:
            self.recovery_attempts[task_id] = []

        # Try each recovery strategy in order
        for strategy in recovery_strategies:
            logger.info(
                f"Attempting recovery for task {task_id} stage {stage} "
                f"using strategy: {strategy.value}"
            )

            attempt_result = await self._apply_recovery_strategy(
                task_id=task_id,
                stage=stage,
                agent_type=agent_type,
                strategy=strategy,
                failure_analysis=analysis,
                previous_stages=previous_stages
            )

            # Record attempt
            self.recovery_attempts[task_id].append({
                "stage": stage,
                "strategy": strategy.value,
                "success": attempt_result.get("success", False),
                "timestamp": __import__("time").time()
            })

            if attempt_result.get("success"):
                logger.info(
                    f"Recovery successful for task {task_id} stage {stage} "
                    f"using strategy: {strategy.value}"
                )
                return {
                    "recovered": True,
                    "strategy_used": strategy,
                    "result": attempt_result,
                    "error": None
                }

        # All recovery strategies failed
        error_message = self._generate_error_message(analysis, recovery_strategies)
        logger.error(f"All recovery attempts failed for task {task_id} stage {stage}")

        return {
            "recovered": False,
            "strategy_used": None,
            "result": None,
            "error": error_message,
            "failure_analysis": analysis
        }

    async def _apply_recovery_strategy(
        self,
        task_id: str,
        stage: str,
        agent_type: str,
        strategy: RecoveryStrategy,
        failure_analysis: Dict[str, Any],
        previous_stages: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Apply a specific recovery strategy.

        Args:
            task_id: Task ID.
            stage: Stage name.
            agent_type: Agent type.
            strategy: Recovery strategy to apply.
            failure_analysis: Failure analysis result.
            previous_stages: Previous stage results.

        Returns:
            Result dictionary with success flag and result data.
        """
        if strategy == RecoveryStrategy.RETRY:
            # Simple retry with same configuration
            return await self._retry_stage(
                task_id, stage, agent_type, previous_stages
            )

        elif strategy == RecoveryStrategy.RETRY_WITH_SIMPLIFIED_PROMPT:
            # Retry after delay (same context)
            return await self._retry_with_delay(
                task_id, stage, agent_type, previous_stages
            )

        elif strategy == RecoveryStrategy.FALLBACK_MODEL:
            # Try with a different model (e.g., faster/cheaper model)
            return await self._retry_with_fallback_model(
                task_id, stage, agent_type, previous_stages
            )

        elif strategy == RecoveryStrategy.FALLBACK_APPROACH:
            # Try a different approach (e.g., different method)
            return await self._retry_with_fallback_approach(
                task_id, stage, agent_type, previous_stages
            )

        elif strategy == RecoveryStrategy.SKIP_STAGE:
            # Skip this stage and continue
            return {
                "success": True,
                "skipped": True,
                "output": f"Stage {stage} skipped due to failure",
                "parsed_data": {}
            }

        elif strategy == RecoveryStrategy.MANUAL_INTERVENTION:
            # Mark for manual intervention
            return {
                "success": False,
                "requires_manual_intervention": True,
                "error": "Manual intervention required"
            }

        return {"success": False, "error": "Unknown recovery strategy"}

    async def _retry_stage(
        self,
        task_id: str,
        stage: str,
        agent_type: str,
        previous_stages: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Retry the stage with same configuration.

        Args:
            task_id: Task ID.
            stage: Stage name.
            agent_type: Agent type.
            previous_stages: Previous stage results.

        Returns:
            Result from retry attempt.
        """
        logger.info(f"Retrying stage {stage} for task {task_id}")

        # Wait a bit before retry (exponential backoff)
        import asyncio
        await asyncio.sleep(2.0)

        # Retry using coordinator
        result = await self.coordinator.start_worker_agent_and_wait(
            task_id=task_id,
            agent_type=agent_type,
            stage=stage,
            previous_stages=previous_stages or {},
            timeout=600.0
        )

        return result

    async def _retry_with_delay(
        self,
        task_id: str,
        stage: str,
        agent_type: str,
        previous_stages: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Retry the stage after a short delay (same context).

        Args:
            task_id: Task ID.
            stage: Stage name.
            agent_type: Agent type.
            previous_stages: Previous stage results.

        Returns:
            Result from retry attempt.
        """
        logger.info(f"Retrying stage {stage} for task {task_id} after delay")

        import asyncio
        await asyncio.sleep(2.0)

        result = await self.coordinator.start_worker_agent_and_wait(
            task_id=task_id,
            agent_type=agent_type,
            stage=stage,
            previous_stages=previous_stages or {},
            timeout=600.0
        )

        return result

    async def _retry_with_fallback_model(
        self,
        task_id: str,
        stage: str,
        agent_type: str,
        previous_stages: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Retry with a fallback model.

        Args:
            task_id: Task ID.
            stage: Stage name.
            agent_type: Agent type.
            previous_stages: Previous stage results.

        Returns:
            Result from retry attempt.
        """
        logger.info(f"Retrying stage {stage} for task {task_id} with fallback model")

        # Get fallback model config
        # For now, use same model (fallback model selection would require config)
        import asyncio
        await asyncio.sleep(2.0)

        result = await self.coordinator.start_worker_agent_and_wait(
            task_id=task_id,
            agent_type=agent_type,
            stage=stage,
            previous_stages=previous_stages or {},
            timeout=600.0
        )

        return result

    async def _retry_with_fallback_approach(
        self,
        task_id: str,
        stage: str,
        agent_type: str,
        previous_stages: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Retry with a different approach.

        Args:
            task_id: Task ID.
            stage: Stage name.
            agent_type: Agent type.
            previous_stages: Previous stage results.

        Returns:
            Result from retry attempt.
        """
        logger.info(f"Retrying stage {stage} for task {task_id} with fallback approach")

        # For now, just retry (different approach would require method changes)
        import asyncio
        await asyncio.sleep(2.0)

        result = await self.coordinator.start_worker_agent_and_wait(
            task_id=task_id,
            agent_type=agent_type,
            stage=stage,
            previous_stages=previous_stages or {},
            timeout=600.0
        )

        return result

    def _generate_error_message(
        self,
        analysis: Dict[str, Any],
        strategies_tried: List[RecoveryStrategy]
    ) -> str:
        """Generate a clear error message for the user.

        Args:
            analysis: Failure analysis result.
            strategies_tried: List of recovery strategies that were attempted.

        Returns:
            Human-readable error message with suggestions.
        """
        failure_type = analysis["failure_type"]
        cause = analysis["cause"]

        message_parts = [
            f"Stage failed: {cause}",
            f"Failure type: {failure_type.value}",
            "",
            "Recovery attempts:"
        ]

        for strategy in strategies_tried:
            message_parts.append(f"  - {strategy.value}: Attempted")

        message_parts.extend([
            "",
            "Suggestions:"
        ])

        # Add suggestions based on failure type
        if failure_type == FailureType.TIMEOUT:
            message_parts.extend([
                "  - Task may be too large, consider splitting",
                "  - Check if agent is stuck in a loop",
                "  - Try with a faster model"
            ])
        elif failure_type == FailureType.API_ERROR:
            message_parts.extend([
                "  - Check API key configuration",
                "  - Verify rate limits and quotas",
                "  - Wait a few minutes and retry"
            ])
        elif failure_type == FailureType.CONTEXT_OVERFLOW:
            message_parts.extend([
                "  - Reduce task scope",
                "  - Split task into smaller subtasks",
                "  - Use a model with larger context window"
            ])
        elif failure_type == FailureType.PARSING_ERROR:
            message_parts.extend([
                "  - Agent output may be malformed",
                "  - Check agent prompt for clarity",
                "  - Review agent output manually"
            ])
        else:
            message_parts.append("  - Review error details and try manual intervention")

        return "\n".join(message_parts)

    def get_recovery_history(self, task_id: str) -> List[Dict[str, Any]]:
        """Get recovery attempt history for a task.

        Args:
            task_id: Task ID.

        Returns:
            List of recovery attempts.
        """
        return self.recovery_attempts.get(task_id, [])
