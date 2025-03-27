"""Factory for creating LLM instances."""

import os
import logging
from typing import Optional, Dict, Any

from src.llm_integration.base import BaseLLM
from src.llm_integration.providers import (
    AnthropicLLM, OpenAILLM, MockLLM, 
    ANTHROPIC_AVAILABLE, OPENAI_AVAILABLE
)
from src.config import LLM_MODEL, ANTHROPIC_API_KEY, OPENAI_API_KEY

logger = logging.getLogger(__name__)


def create_llm(
    provider: str,
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs
) -> BaseLLM:
    """Create an LLM instance based on the provider.
    
    Args:
        provider: LLM provider ("anthropic", "openai", or "mock")
        model_name: Optional model name (defaults to config or provider default)
        api_key: Optional API key (defaults to config or environment)
        **kwargs: Additional parameters to pass to the LLM constructor
        
    Returns:
        BaseLLM instance (falls back to MockLLM if dependencies not available)
    """
    provider = provider.lower()
    
    if provider == "anthropic":
        if not ANTHROPIC_AVAILABLE:
            logger.warning("Anthropic package not available, falling back to MockLLM. Install with: pip install anthropic")
            return MockLLM(model_name="claude-mock", **kwargs)
            
        if not model_name:
            model_name = "claude-3-5-sonnet-20240620"
            
        return AnthropicLLM(
            model_name=model_name,
            api_key=api_key,
            **kwargs
        )
    elif provider == "openai":
        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI package not available, falling back to MockLLM. Install with: pip install openai tiktoken")
            return MockLLM(model_name="gpt-mock", **kwargs)
            
        if not model_name:
            model_name = "gpt-4o"
            
        return OpenAILLM(
            model_name=model_name,
            api_key=api_key,
            **kwargs
        )
    elif provider == "mock":
        return MockLLM(
            model_name=model_name or "mock-model",
            **kwargs
        )
    else:
        logger.warning(f"Unsupported provider: {provider}, falling back to MockLLM")
        return MockLLM(model_name="fallback-mock", **kwargs)


def get_default_llm(**kwargs) -> BaseLLM:
    """Get the default LLM based on available API keys and installed packages.
    
    Args:
        **kwargs: Additional parameters to pass to the LLM constructor
        
    Returns:
        BaseLLM instance
    """
    model_name = kwargs.pop("model_name", LLM_MODEL)
    
    # Determine provider from model name
    if model_name.startswith("claude"):
        if ANTHROPIC_API_KEY and ANTHROPIC_AVAILABLE:
            return create_llm("anthropic", model_name=model_name, **kwargs)
        elif not ANTHROPIC_AVAILABLE:
            logger.warning("Anthropic package not installed but Claude model requested, falling back to mock")
            return create_llm("mock", model_name="claude-mock", **kwargs)
        else:
            logger.warning("No Anthropic API key found but Claude model requested, falling back to mock")
            return create_llm("mock", model_name="claude-mock", **kwargs)
            
    elif any(model_name.startswith(prefix) for prefix in ["gpt", "text-davinci"]):
        if OPENAI_API_KEY and OPENAI_AVAILABLE:
            return create_llm("openai", model_name=model_name, **kwargs)
        elif not OPENAI_AVAILABLE:
            logger.warning("OpenAI package not installed but GPT model requested, falling back to mock")
            return create_llm("mock", model_name="gpt-mock", **kwargs)
        else:
            logger.warning("No OpenAI API key found but GPT model requested, falling back to mock")
            return create_llm("mock", model_name="gpt-mock", **kwargs)
    
    # If model doesn't clearly indicate provider
    # Try Anthropic first if available
    if ANTHROPIC_API_KEY and ANTHROPIC_AVAILABLE:
        return create_llm("anthropic", model_name=model_name, **kwargs)
    # Then try OpenAI if available
    elif OPENAI_API_KEY and OPENAI_AVAILABLE:
        return create_llm("openai", model_name=model_name, **kwargs)
    # Otherwise use mock
    else:
        logger.warning("No usable LLM providers found, using mock LLM")
        return create_llm("mock", **kwargs)