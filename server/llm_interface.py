"""
OpenAI LLM interface layer for Inspektor.
Provides abstraction over OpenAI API with retry logic, token tracking, and function calling support.
"""

from typing import List, Dict, Any, Optional, Callable
from openai import OpenAI, OpenAIError
import os
import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for LLM-related errors"""
    pass


class LLMRateLimitError(LLMError):
    """Raised when rate limit is hit"""
    pass


class LLMInterface:
    """
    Wrapper around OpenAI API with utilities for:
    - Retry logic
    - Token usage tracking
    - Function calling support
    - Error handling
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        max_retries: int = 3,
        timeout: int = 60,
    ):
        """
        Initialize OpenAI interface.

        Args:
            api_key: OpenAI API key (if None, uses OPENAI_API_KEY env var)
            model: Model name to use
            max_retries: Maximum number of retries on failure
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY must be set in environment or passed as argument")

        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout

        self.client = OpenAI(api_key=self.api_key, timeout=timeout)

        # Token usage tracking
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0

    def _retry_with_backoff(self, func: Callable) -> Callable:
        """
        Decorator to add retry logic with exponential backoff.

        Args:
            func: Function to wrap

        Returns:
            Wrapped function with retry logic
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(self.max_retries):
                try:
                    return func(*args, **kwargs)
                except OpenAIError as e:
                    # Check if it's a rate limit error
                    if "rate_limit" in str(e).lower():
                        if attempt < self.max_retries - 1:
                            wait_time = (2 ** attempt) * 1  # Exponential backoff: 1s, 2s, 4s
                            logger.warning(f"Rate limit hit, retrying in {wait_time}s...")
                            time.sleep(wait_time)
                            continue
                        else:
                            raise LLMRateLimitError("Rate limit exceeded") from e
                    else:
                        # Re-raise other errors immediately
                        raise LLMError(f"OpenAI API error: {str(e)}") from e
            raise LLMError("Max retries exceeded")

        return wrapper

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        functions: Optional[List[Dict[str, Any]]] = None,
        function_call: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create a chat completion with optional function calling.

        Args:
            messages: List of message dicts with 'role' and 'content'
            functions: Optional list of function definitions for function calling
            function_call: Optional function call mode ("auto", "none", or {"name": "function_name"})
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional OpenAI API parameters

        Returns:
            Response dict containing message, function calls, and usage info
        """
        @self._retry_with_backoff
        def _make_request():
            params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                **kwargs,
            }

            if max_tokens:
                params["max_tokens"] = max_tokens

            # Add function calling if provided
            if functions:
                params["tools"] = [
                    {"type": "function", "function": func} for func in functions
                ]
                if function_call:
                    params["tool_choice"] = function_call

            response = self.client.chat.completions.create(**params)
            return response

        try:
            response = _make_request()

            # Track token usage
            if hasattr(response, 'usage') and response.usage:
                self.total_prompt_tokens += response.usage.prompt_tokens
                self.total_completion_tokens += response.usage.completion_tokens
                self.total_tokens += response.usage.total_tokens

            # Parse response
            message = response.choices[0].message

            result = {
                "content": message.content,
                "role": message.role,
                "finish_reason": response.choices[0].finish_reason,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
            }

            # Add function/tool calls if present
            if hasattr(message, 'tool_calls') and message.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ]

            return result

        except LLMError:
            raise
        except Exception as e:
            raise LLMError(f"Unexpected error during chat completion: {str(e)}") from e

    def stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        functions: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.0,
        **kwargs,
    ):
        """
        Create a streaming chat completion.

        Args:
            messages: List of message dicts with 'role' and 'content'
            functions: Optional list of function definitions
            temperature: Sampling temperature (0-2)
            **kwargs: Additional OpenAI API parameters

        Yields:
            Chunks of the response as they arrive
        """
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
            **kwargs,
        }

        if functions:
            params["tools"] = [
                {"type": "function", "function": func} for func in functions
            ]

        try:
            stream = self.client.chat.completions.create(**params)

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except OpenAIError as e:
            raise LLMError(f"Streaming error: {str(e)}") from e

    def get_token_usage(self) -> Dict[str, int]:
        """
        Get cumulative token usage statistics.

        Returns:
            Dictionary with prompt_tokens, completion_tokens, and total_tokens
        """
        return {
            "prompt_tokens": self.total_prompt_tokens,
            "completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
        }

    def reset_token_usage(self):
        """Reset token usage counters"""
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0

    def test_connection(self) -> bool:
        """
        Test connection to OpenAI API.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = self.chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5,
            )
            return response is not None
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
