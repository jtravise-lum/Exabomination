"""Base classes for LLM integration."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union

logger = logging.getLogger(__name__)


class BaseLLM(ABC):
    """Base class for LLM integration.
    
    This abstract class defines the common interface for all LLM providers,
    allowing for easy switching between different models.
    """
    
    def __init__(
        self, 
        model_name: str,
        api_key: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        timeout: int = 60
    ):
        """Initialize the base LLM.
        
        Args:
            model_name: Name of the model to use
            api_key: API key for the provider (optional, can use env var)
            temperature: Temperature parameter for generation
            max_tokens: Maximum tokens to generate in a response
            timeout: Request timeout in seconds
        """
        self.model_name = model_name
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        
        # Statistics
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_requests = 0
        
        logger.info(f"Initialized {self.__class__.__name__} with model: {model_name}")
    
    @abstractmethod
    def generate(
        self, 
        prompt: str, 
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop_sequences: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Generate text based on the provided prompt.
        
        Args:
            prompt: The input prompt for the model
            temperature: Override the default temperature
            max_tokens: Override the default max tokens
            stop_sequences: Optional sequences to stop generation
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Generated text response
        """
        pass
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in the given text.
        
        Args:
            text: The text to count tokens for
            
        Returns:
            Number of tokens
        """
        pass
    
    def get_token_usage(self) -> Dict[str, int]:
        """Get token usage statistics.
        
        Returns:
            Dictionary with token usage statistics
        """
        return {
            "prompt_tokens": self.total_prompt_tokens,
            "completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
            "requests": self.total_requests
        }
    
    def reset_token_usage(self) -> None:
        """Reset token usage statistics."""
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_requests = 0
    
    def validate_api_key(self) -> bool:
        """Check if the API key is valid.
        
        Returns:
            True if valid, False otherwise
        """
        return bool(self.api_key)