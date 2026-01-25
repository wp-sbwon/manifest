"""
Tool Call Parser for extracting tool calls from LLM responses.

This module parses tool calls from LLM API responses,
supporting both Anthropic Claude's tool_use format and OpenAI's
function calling format.
"""
import json
from typing import Dict, Any, List, Optional
from manifest.core.logger import get_logger

logger = get_logger(__name__)


class ToolCallParser:
    """Parses tool calls from LLM responses.
    
    Supports multiple formats:
    - Anthropic Claude: tool_use blocks in streaming responses
    - OpenAI: function_call in streaming responses
    - Fallback: Markdown code blocks with JSON tool calls
    """
    
    @staticmethod
    def parse_anthropic_tool_use(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse Anthropic tool_use block.
        
        Args:
            data: JSON data from Anthropic API response.
            
        Returns:
            Parsed tool call dict with 'id', 'name', 'input', or None if not a tool_use.
        """
        if data.get("type") == "tool_use":
            return {
                "id": data.get("id"),
                "name": data.get("name"),
                "input": data.get("input", {})
            }
        return None
    
    @staticmethod
    def parse_openai_function_call(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse OpenAI function_call.
        
        Args:
            data: JSON data from OpenAI API response.
            
        Returns:
            Parsed tool call dict with 'id', 'name', 'input', or None if not a function_call.
        """
        choices = data.get("choices", [])
        if not choices:
            return None
        
        delta = choices[0].get("delta", {})
        function_call = delta.get("function_call")
        
        if function_call:
            # OpenAI function calls come in parts (name, then arguments)
            name = function_call.get("name")
            arguments_str = function_call.get("arguments", "")
            
            if name:
                try:
                    arguments = json.loads(arguments_str) if arguments_str else {}
                except json.JSONDecodeError:
                    arguments = {}
                
                return {
                    "id": f"openai_{id(function_call)}",
                    "name": name,
                    "input": arguments
                }
        
        return None
    
    @staticmethod
    def parse_from_text(text: str) -> List[Dict[str, Any]]:
        """Parse tool calls from markdown code blocks in text.
        
        Fallback method for extracting tool calls from text responses
        that contain JSON in markdown code blocks.
        
        Args:
            text: Text response that may contain tool calls.
            
        Returns:
            List of parsed tool call dicts.
        """
        tool_calls = []
        
        # Look for JSON code blocks
        import re
        pattern = r'```(?:json)?\s*(\{.*?"type"\s*:\s*"tool_use".*?\})\s*```'
        matches = re.findall(pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                data = json.loads(match)
                tool_call = ToolCallParser.parse_anthropic_tool_use(data)
                if tool_call:
                    tool_calls.append(tool_call)
            except json.JSONDecodeError:
                continue
        
        return tool_calls
    
    @staticmethod
    def parse_streaming_response(
        provider: str,
        data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Parse tool call from streaming response data.
        
        Args:
            provider: Provider name ("anthropic" or "openai").
            data: JSON data from streaming response.
            
        Returns:
            Parsed tool call dict or None.
        """
        if provider == "anthropic":
            # Check for content_block_start with tool_use
            if data.get("type") == "content_block_start":
                block = data.get("content_block", {})
                if block.get("type") == "tool_use":
                    return {
                        "id": block.get("id"),
                        "name": block.get("name"),
                        "input": block.get("input", {})
                    }
            # Check for tool_use block directly
            return ToolCallParser.parse_anthropic_tool_use(data)
        elif provider == "openai":
            return ToolCallParser.parse_openai_function_call(data)
        
        return None
    
    @staticmethod
    def extract_tool_results_from_response(
        provider: str,
        response_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Extract tool use blocks from complete response.
        
        For Anthropic, looks for tool_use blocks in the response.
        For OpenAI, looks for function_call in choices.
        
        Args:
            provider: Provider name.
            response_data: Complete response data from API.
            
        Returns:
            List of tool call dicts.
        """
        tool_calls = []
        
        if provider == "anthropic":
            # Anthropic response structure
            content = response_data.get("content", [])
            for block in content:
                if block.get("type") == "tool_use":
                    tool_call = ToolCallParser.parse_anthropic_tool_use(block)
                    if tool_call:
                        tool_calls.append(tool_call)
        
        elif provider == "openai":
            # OpenAI response structure
            choices = response_data.get("choices", [])
            for choice in choices:
                message = choice.get("message", {})
                function_call = message.get("function_call")
                if function_call:
                    name = function_call.get("name")
                    arguments_str = function_call.get("arguments", "")
                    try:
                        arguments = json.loads(arguments_str) if arguments_str else {}
                    except json.JSONDecodeError:
                        arguments = {}
                    
                    tool_calls.append({
                        "id": f"openai_{id(function_call)}",
                        "name": name,
                        "input": arguments
                    })
        
        return tool_calls
