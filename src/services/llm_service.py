"""
LLM Service - Unified interface for multiple LLM providers.

Provides a consistent API for interacting with OpenAI, Google Gemini, and
Anthropic Claude models with automatic retry logic and error handling.
"""
import time
from typing import Dict, Any, List, Optional
from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

# Import LLM provider libraries
import openai
import google.generativeai as genai
import anthropic

from ..config import get_api_key


class LLMError(Exception):
    """Generic exception for LLM-related errors."""
    
    def __init__(self, message: str, provider: str = None, original_error: Exception = None):
        self.provider = provider
        self.original_error = original_error
        super().__init__(message)


def _estimate_tokens(text: str) -> int:
    """
    Estimate token count for a piece of text.
    
    Uses rough approximation: ~4 characters per token for English text.
    
    Args:
        text: Input text to estimate tokens for
    
    Returns:
        Estimated token count
    """
    return len(text) // 4


def _count_message_tokens(messages: List[Dict[str, str]]) -> int:
    """
    Estimate total tokens in a list of messages.
    
    Args:
        messages: List of message dictionaries
    
    Returns:
        Estimated total token count
    """
    total = 0
    for msg in messages:
        total += _estimate_tokens(msg.get("content", ""))
    return total


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    retry=retry_if_exception_type((openai.RateLimitError, openai.APITimeoutError, openai.APIConnectionError)),
    reraise=True,
)
def _call_openai(
    messages: List[Dict[str, str]],
    system_prompt: Optional[str],
    temperature: float,
    max_tokens: int,
) -> Dict[str, Any]:
    """
    Call OpenAI's GPT API.
    
    Args:
        messages: List of chat messages
        system_prompt: Optional system prompt
        temperature: Sampling temperature (0-2)
        max_tokens: Maximum tokens to generate
    
    Returns:
        Standardized response dictionary
    
    Raises:
        LLMError: If API call fails after retries
    """
    try:
        api_key = get_api_key("openai")
        client = openai.OpenAI(api_key=api_key)
        
        # Convert system_prompt to first message if provided
        formatted_messages = []
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
        formatted_messages.extend(messages)
        
        start_time = time.time()
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=formatted_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        duration = time.time() - start_time
        
        content = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if response.usage else _estimate_tokens(content)
        
        logger.info(
            f"OpenAI API call successful | "
            f"tokens: {tokens_used} | "
            f"duration: {duration:.2f}s | "
            f"model: gpt-3.5-turbo"
        )
        
        return {
            "content": content,
            "provider": "openai",
            "tokens_used": tokens_used,
        }
        
    except openai.AuthenticationError as e:
        logger.error(f"OpenAI authentication failed: {e}")
        raise LLMError(
            "OpenAI authentication failed. Please check your API key.",
            provider="openai",
            original_error=e,
        )
    except (openai.RateLimitError, openai.APITimeoutError, openai.APIConnectionError) as e:
        # These are retried by tenacity
        logger.warning(f"OpenAI API error (will retry): {e}")
        raise
    except Exception as e:
        logger.error(f"OpenAI API call failed: {e}")
        raise LLMError(
            f"OpenAI API call failed: {str(e)}",
            provider="openai",
            original_error=e,
        )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    reraise=True,
)
def _call_gemini(
    messages: List[Dict[str, str]],
    system_prompt: Optional[str],
    temperature: float,
    max_tokens: int,
) -> Dict[str, Any]:
    """
    Call Google Gemini API.
    
    Args:
        messages: List of chat messages
        system_prompt: Optional system prompt
        temperature: Sampling temperature (0-1)
        max_tokens: Maximum tokens to generate
    
    Returns:
        Standardized response dictionary
    
    Raises:
        LLMError: If API call fails after retries
    """
    try:
        api_key = get_api_key("gemini")
        genai.configure(api_key=api_key)
        
        model = genai.GenerativeModel("gemini-pro")
        
        # Format messages for Gemini
        # Gemini expects a conversation history format
        # System prompt is prepended to the first user message
        conversation_text = ""
        
        if system_prompt:
            conversation_text += f"System: {system_prompt}\n\n"
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "system":
                conversation_text += f"System: {content}\n\n"
            elif role == "user":
                conversation_text += f"User: {content}\n\n"
            elif role == "assistant":
                conversation_text += f"Assistant: {content}\n\n"
        
        # Add final prompt
        conversation_text += "Assistant:"
        
        start_time = time.time()
        
        response = model.generate_content(
            conversation_text,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )
        
        duration = time.time() - start_time
        
        content = response.text
        
        # Estimate tokens (Gemini doesn't always provide token counts)
        input_tokens = _estimate_tokens(conversation_text)
        output_tokens = _estimate_tokens(content)
        tokens_used = input_tokens + output_tokens
        
        logger.info(
            f"Gemini API call successful | "
            f"tokens: {tokens_used} (estimated) | "
            f"duration: {duration:.2f}s | "
            f"model: gemini-pro"
        )
        
        return {
            "content": content,
            "provider": "gemini",
            "tokens_used": tokens_used,
        }
        
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}")
        raise LLMError(
            f"Gemini API call failed: {str(e)}",
            provider="gemini",
            original_error=e,
        )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.APITimeoutError, anthropic.APIConnectionError)),
    reraise=True,
)
def _call_claude(
    messages: List[Dict[str, str]],
    system_prompt: Optional[str],
    temperature: float,
    max_tokens: int,
) -> Dict[str, Any]:
    """
    Call Anthropic Claude API.
    
    Args:
        messages: List of chat messages
        system_prompt: Optional system prompt
        temperature: Sampling temperature (0-1)
        max_tokens: Maximum tokens to generate
    
    Returns:
        Standardized response dictionary
    
    Raises:
        LLMError: If API call fails after retries
    """
    try:
        api_key = get_api_key("claude")
        client = anthropic.Anthropic(api_key=api_key)
        
        # Filter out system messages from messages list (Claude handles system separately)
        formatted_messages = [
            msg for msg in messages
            if msg["role"] != "system"
        ]
        
        # Collect any system messages from the messages list
        system_messages = [
            msg["content"] for msg in messages
            if msg["role"] == "system"
        ]
        
        # Combine system prompt with any system messages
        final_system_prompt = None
        if system_prompt or system_messages:
            parts = []
            if system_prompt:
                parts.append(system_prompt)
            parts.extend(system_messages)
            final_system_prompt = "\n\n".join(parts)
        
        start_time = time.time()
        
        # Build kwargs for API call
        kwargs = {
            "model": "claude-3-sonnet-20240229",
            "messages": formatted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if final_system_prompt:
            kwargs["system"] = final_system_prompt
        
        response = client.messages.create(**kwargs)
        
        duration = time.time() - start_time
        
        content = response.content[0].text
        
        # Claude provides token usage
        tokens_used = response.usage.input_tokens + response.usage.output_tokens
        
        logger.info(
            f"Claude API call successful | "
            f"tokens: {tokens_used} | "
            f"duration: {duration:.2f}s | "
            f"model: claude-3-sonnet-20240229"
        )
        
        return {
            "content": content,
            "provider": "claude",
            "tokens_used": tokens_used,
        }
        
    except anthropic.AuthenticationError as e:
        logger.error(f"Claude authentication failed: {e}")
        raise LLMError(
            "Claude authentication failed. Please check your API key.",
            provider="claude",
            original_error=e,
        )
    except (anthropic.RateLimitError, anthropic.APITimeoutError, anthropic.APIConnectionError) as e:
        # These are retried by tenacity
        logger.warning(f"Claude API error (will retry): {e}")
        raise
    except Exception as e:
        logger.error(f"Claude API call failed: {e}")
        raise LLMError(
            f"Claude API call failed: {str(e)}",
            provider="claude",
            original_error=e,
        )


def llm_chat(
    provider: str,
    messages: List[Dict[str, str]],
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 500,
) -> Dict[str, Any]:
    """
    Unified interface for calling different LLM providers.
    
    This function provides a consistent API for interacting with OpenAI GPT,
    Google Gemini, and Anthropic Claude models. It handles provider-specific
    formatting, automatic retries, and error handling.
    
    Args:
        provider: LLM provider to use ("openai", "gemini", or "claude")
        messages: List of chat messages with format:
                  [{"role": "user|assistant|system", "content": "..."}]
        system_prompt: Optional system prompt to guide the model's behavior
        temperature: Sampling temperature (0-2 for OpenAI, 0-1 for others).
                    Higher values make output more random.
        max_tokens: Maximum number of tokens to generate in the response
    
    Returns:
        Dictionary containing:
            - content (str): The LLM's response text
            - provider (str): Which provider was used
            - tokens_used (int): Approximate token count
    
    Raises:
        ValueError: If provider is not one of the supported providers
        LLMError: If the API call fails after retries, or if API key is missing
    
    Examples:
        >>> response = llm_chat(
        ...     provider="openai",
        ...     messages=[{"role": "user", "content": "Hello!"}],
        ...     temperature=0.7,
        ...     max_tokens=100
        ... )
        >>> print(response["content"])
        "Hello! How can I help you today?"
        
        >>> response = llm_chat(
        ...     provider="gemini",
        ...     messages=[{"role": "user", "content": "What is AI?"}],
        ...     system_prompt="You are a helpful AI assistant."
        ... )
    """
    # Validate provider
    supported_providers = ["openai", "gemini", "claude"]
    if provider not in supported_providers:
        raise ValueError(
            f"Invalid provider: {provider}. "
            f"Must be one of: {', '.join(supported_providers)}"
        )
    
    # Validate messages
    if not messages:
        raise ValueError("messages list cannot be empty")
    
    if not isinstance(messages, list):
        raise ValueError("messages must be a list of dictionaries")
    
    for msg in messages:
        if not isinstance(msg, dict):
            raise ValueError("Each message must be a dictionary")
        if "role" not in msg or "content" not in msg:
            raise ValueError("Each message must have 'role' and 'content' keys")
        if msg["role"] not in ["user", "assistant", "system"]:
            raise ValueError("Message role must be 'user', 'assistant', or 'system'")
    
    logger.debug(
        f"Calling LLM | provider: {provider} | "
        f"messages: {len(messages)} | "
        f"temperature: {temperature} | "
        f"max_tokens: {max_tokens}"
    )
    
    # Route to appropriate provider
    try:
        if provider == "openai":
            return _call_openai(messages, system_prompt, temperature, max_tokens)
        elif provider == "gemini":
            return _call_gemini(messages, system_prompt, temperature, max_tokens)
        elif provider == "claude":
            return _call_claude(messages, system_prompt, temperature, max_tokens)
    except LLMError:
        # Re-raise LLMError as-is
        raise
    except Exception as e:
        # Wrap any other exceptions
        logger.error(f"Unexpected error calling {provider}: {e}")
        raise LLMError(
            f"Unexpected error calling {provider}: {str(e)}",
            provider=provider,
            original_error=e,
        )
