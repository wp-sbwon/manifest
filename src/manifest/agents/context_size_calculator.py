"""
Context size calculator for managing LLM token limits.

This module provides utilities for calculating context size in tokens,
checking against model limits, and suggesting context reduction strategies.
It helps prevent context overflow errors and optimizes token usage.
"""
import json
from typing import Dict, Any, Optional, List, Tuple
from manifest.core.logger import get_logger

logger = get_logger(__name__)


# Model token limits (approximate, in tokens). Update when adding new provider/model support.
MODEL_TOKEN_LIMITS = {
    # Anthropic Claude models
    "claude-3-opus": 200000,
    "claude-3-opus-20240229": 200000,
    "claude-3-sonnet": 200000,
    "claude-3-sonnet-20240229": 200000,
    "claude-3-haiku": 200000,
    "claude-3-haiku-20240307": 200000,
    "claude-3-5-sonnet": 200000,
    "claude-3-5-sonnet-20241022": 200000,
    "claude-3-5-haiku": 200000,
    "claude-3-5-haiku-20241022": 200000,

    # OpenAI GPT models
    "gpt-4": 128000,
    "gpt-4-turbo": 128000,
    "gpt-4-turbo-preview": 128000,
    "gpt-4-0125-preview": 128000,
    "gpt-4-1106-preview": 128000,
    "gpt-3.5-turbo": 16385,
    "gpt-3.5-turbo-16k": 16385,
    "gpt-3.5-turbo-1106": 16385,

    # Google Gemini models
    "gemini-pro": 32768,
    "gemini-pro-1.5": 2097152,  # 2M tokens
    "gemini-1.5-pro": 2097152,
    "gemini-1.5-flash": 1048576,  # 1M tokens
}

# Default token limit if model not found
DEFAULT_TOKEN_LIMIT = 100000

# Reserve tokens for response (conservative estimate)
RESPONSE_TOKEN_RESERVE = 4000

# Average characters per token (approximate, varies by language)
# Using 4 chars per token as a conservative estimate
CHARS_PER_TOKEN = 4


class ContextSizeCalculator:
    """Calculates and validates context size against model limits.

    Provides methods to estimate token count, check against model limits,
    and suggest context reduction strategies when limits are exceeded.
    """

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count for a text string.

        Uses a simple heuristic: approximately 4 characters per token.
        This is a conservative estimate that works reasonably well for
        English code and text. For more accuracy, tiktoken could be used
        for OpenAI models, but this simple approach works across all models.

        Args:
            text: Text string to estimate tokens for.

        Returns:
            Estimated number of tokens.
        """
        if not text:
            return 0
        # Rough estimate: 4 characters per token
        # This is conservative and works reasonably well
        return len(text) // CHARS_PER_TOKEN

    @staticmethod
    def estimate_context_tokens(context: Dict[str, Any]) -> int:
        """Estimate total token count for a context dictionary.

        Recursively calculates tokens for all string values in the context,
        including nested dictionaries and lists.

        Args:
            context: Context dictionary to estimate tokens for.

        Returns:
            Total estimated token count.
        """
        total_tokens = 0

        def count_value(value: Any) -> int:
            """Recursively count tokens in a value."""
            if isinstance(value, str):
                return ContextSizeCalculator.estimate_tokens(value)
            elif isinstance(value, dict):
                return sum(count_value(v) for v in value.values())
            elif isinstance(value, list):
                return sum(count_value(item) for item in value)
            elif isinstance(value, (int, float, bool)) or value is None:
                # Numbers and booleans take minimal tokens
                return 1
            else:
                # Convert other types to string
                return ContextSizeCalculator.estimate_tokens(str(value))

        total_tokens = count_value(context)
        return total_tokens

    @staticmethod
    def get_model_token_limit(model: str, provider: Optional[str] = None) -> int:
        """Get token limit for a specific model.

        Args:
            model: Model name (e.g., "claude-3-opus", "gpt-4").
            provider: Optional provider name to help identify model.

        Returns:
            Token limit for the model, or default if not found.
        """
        # Try exact match first
        if model in MODEL_TOKEN_LIMITS:
            return MODEL_TOKEN_LIMITS[model]

        # Try partial match (e.g., "claude-3-opus" matches "claude-3-opus-20240229")
        for model_name, limit in MODEL_TOKEN_LIMITS.items():
            if model_name.startswith(model) or model.startswith(model_name.split("-")[0]):
                return limit

        # Try provider-based defaults
        if provider:
            if provider.lower() == "anthropic":
                return 200000  # Claude models default
            elif provider.lower() == "openai":
                if "gpt-4" in model.lower():
                    return 128000
                elif "gpt-3.5" in model.lower():
                    return 16385
            elif provider.lower() == "google":
                if "1.5" in model.lower() or "pro" in model.lower():
                    return 2097152  # Gemini 1.5 Pro
                else:
                    return 32768  # Gemini Pro

        logger.warning(f"Unknown model '{model}', using default token limit {DEFAULT_TOKEN_LIMIT}")
        return DEFAULT_TOKEN_LIMIT

    @staticmethod
    def validate_context_size(
        context: Dict[str, Any],
        model: str,
        provider: Optional[str] = None
    ) -> Dict[str, Any]:
        """Validate context size against model limits.

        Checks if the context fits within the model's token limit, accounting
        for response token reserve. Returns validation result with suggestions
        if the context is too large.

        Args:
            context: Context dictionary to validate.
            model: Model name to check limits against.
            provider: Optional provider name.

        Returns:
            Dictionary with validation result:
            {
                "valid": bool,
                "estimated_tokens": int,
                "model_limit": int,
                "available_tokens": int,
                "excess_tokens": int,
                "warnings": List[str],
                "suggestions": List[str]
            }
        """
        estimated_tokens = ContextSizeCalculator.estimate_context_tokens(context)
        model_limit = ContextSizeCalculator.get_model_token_limit(model, provider)
        available_tokens = model_limit - RESPONSE_TOKEN_RESERVE

        warnings = []
        suggestions = []

        if estimated_tokens > available_tokens:
            excess_tokens = estimated_tokens - available_tokens
            warnings.append(
                f"Context size ({estimated_tokens} tokens) exceeds available limit "
                f"({available_tokens} tokens) by {excess_tokens} tokens"
            )

            # Suggest reduction strategies
            suggestions.append("Reduce Tier 3 (code files) - extract only relevant functions/classes")
            suggestions.append("Reduce Tier 2 (blueprint) - include only relevant components")
            suggestions.append("Split task into smaller subtasks")
            suggestions.append("Use code summaries instead of full file contents")

            return {
                "valid": False,
                "estimated_tokens": estimated_tokens,
                "model_limit": model_limit,
                "available_tokens": available_tokens,
                "excess_tokens": excess_tokens,
                "warnings": warnings,
                "suggestions": suggestions
            }
        else:
            usage_percent = (estimated_tokens / available_tokens) * 100
            if usage_percent > 80:
                warnings.append(
                    f"Context size is {usage_percent:.1f}% of available limit. "
                    "Consider reducing context to leave room for response."
                )

            return {
                "valid": True,
                "estimated_tokens": estimated_tokens,
                "model_limit": model_limit,
                "available_tokens": available_tokens,
                "excess_tokens": 0,
                "warnings": warnings,
                "suggestions": []
            }

    @staticmethod
    def get_context_breakdown(context: Dict[str, Any]) -> Dict[str, int]:
        """Get token breakdown by context tier.

        Analyzes which parts of the context consume the most tokens,
        helping identify where to reduce context size.

        Args:
            context: Context dictionary to analyze.

        Returns:
            Dictionary mapping tier/component names to token counts.
        """
        breakdown = {}

        # Tier 0 (policies)
        if "tier_0" in context:
            breakdown["tier_0"] = ContextSizeCalculator.estimate_context_tokens(context["tier_0"])

        # Tier 1 (intent, architecture)
        if "tier_1" in context:
            breakdown["tier_1"] = ContextSizeCalculator.estimate_context_tokens(context["tier_1"])

        # Tier 2 (blueprint)
        if "tier_2" in context:
            breakdown["tier_2"] = ContextSizeCalculator.estimate_context_tokens(context["tier_2"])

        # Tier 3 (code files)
        if "tier_3" in context:
            breakdown["tier_3"] = ContextSizeCalculator.estimate_context_tokens(context["tier_3"])

        # Skills
        if "skills" in context:
            breakdown["skills"] = ContextSizeCalculator.estimate_context_tokens(context["skills"])

        # Task scope
        if "task_scope" in context:
            breakdown["task_scope"] = ContextSizeCalculator.estimate_context_tokens(context["task_scope"])

        return breakdown
