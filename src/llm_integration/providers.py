"""LLM provider implementations."""

import os
import time
import logging
import json
from typing import Dict, List, Optional, Any, Union, Tuple

import requests

# Import optional dependencies
try:
    import anthropic
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from src.llm_integration.base import BaseLLM
from src.config import ANTHROPIC_API_KEY, OPENAI_API_KEY

logger = logging.getLogger(__name__)


class AnthropicLLM(BaseLLM):
    """Anthropic Claude LLM integration."""
    
    def __init__(
        self,
        model_name: str = "claude-3-5-sonnet-20240620",
        api_key: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        timeout: int = 90,
        retry_max: int = 3,
        retry_delay: float = 2.0
    ):
        """Initialize the Anthropic Claude LLM.
        
        Args:
            model_name: Claude model name to use
            api_key: Anthropic API key (falls back to env var)
            temperature: Temperature parameter for generation
            max_tokens: Maximum tokens to generate in a response
            timeout: Request timeout in seconds
            retry_max: Maximum number of retries
            retry_delay: Delay between retries in seconds
        """
        super().__init__(
            model_name=model_name,
            api_key=api_key or ANTHROPIC_API_KEY,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout
        )
        
        self.retry_max = retry_max
        self.retry_delay = retry_delay
        self.client = None
        
        # Check if Anthropic is available
        if not ANTHROPIC_AVAILABLE:
            logger.warning("Anthropic Python package not installed. Install with: pip install anthropic")
            return
        
        # Initialize Anthropic client
        if not self.api_key:
            logger.warning("No Anthropic API key provided, using mock responses")
        else:
            try:
                self.client = Anthropic(api_key=self.api_key)
                logger.info(f"Initialized Anthropic Claude client with model: {model_name}")
            except Exception as e:
                logger.error(f"Error initializing Anthropic client: {str(e)}")
                self.client = None
    
    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop_sequences: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate text using Anthropic Claude.
        
        Args:
            prompt: User input prompt
            temperature: Override default temperature
            max_tokens: Override default max tokens
            stop_sequences: Optional sequences to stop generation
            system_prompt: Optional system prompt
            **kwargs: Additional parameters
            
        Returns:
            Generated text response
        """
        if not self.api_key or not self.client:
            logger.warning("No valid Anthropic client, returning mock response")
            return "This is a mock response because no valid Anthropic API key was provided."
        
        temp = temperature if temperature is not None else self.temperature
        max_tok = max_tokens if max_tokens is not None else self.max_tokens
        
        # Track token usage
        prompt_tokens = self.count_tokens(prompt)
        if system_prompt:
            prompt_tokens += self.count_tokens(system_prompt)
            
        self.total_prompt_tokens += prompt_tokens
        self.total_requests += 1
        
        # Retry logic
        for attempt in range(self.retry_max):
            try:
                # Prepare message format
                messages = [{"role": "user", "content": prompt}]
                
                # Create request parameters
                request_params = {
                    "model": self.model_name,
                    "messages": messages,
                    "max_tokens": max_tok,
                    "temperature": temp
                }
                
                # Add system prompt if provided
                if system_prompt:
                    request_params["system"] = system_prompt
                
                # Add stop sequences if provided
                if stop_sequences:
                    request_params["stop_sequences"] = stop_sequences
                
                # Make the API call
                start_time = time.time()
                response = self.client.messages.create(**request_params)
                elapsed_time = time.time() - start_time
                
                # Extract the response text
                result = response.content[0].text
                
                # Update stats
                completion_tokens = self.count_tokens(result)
                self.total_completion_tokens += completion_tokens
                
                logger.info(f"Anthropic response received in {elapsed_time:.2f}s, "
                           f"prompt: {prompt_tokens} tokens, "
                           f"completion: {completion_tokens} tokens")
                
                return result
                
            except anthropic.RateLimitError:
                logger.warning(f"Rate limit exceeded, retrying in {self.retry_delay}s (attempt {attempt+1}/{self.retry_max})")
                time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                
            except Exception as e:
                logger.error(f"Error generating text with Anthropic: {str(e)}")
                if attempt < self.retry_max - 1:
                    logger.warning(f"Retrying in {self.retry_delay}s (attempt {attempt+1}/{self.retry_max})")
                    time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    return f"Error: Failed to generate response after {self.retry_max} attempts. Last error: {str(e)}"
        
        return "Error: Failed to generate response after multiple attempts."
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using Anthropic's tokenizer."""
        if not text:
            return 0
            
        # Use a simple heuristic for Claude: ~4 chars per token
        return len(text) // 4
        
        # For more accuracy we could use:
        # return self.client.count_tokens(text)


class OpenAILLM(BaseLLM):
    """OpenAI GPT integration."""
    
    def __init__(
        self,
        model_name: str = "gpt-4o",
        api_key: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        timeout: int = 60,
        retry_max: int = 3,
        retry_delay: float = 2.0
    ):
        """Initialize the OpenAI GPT LLM.
        
        Args:
            model_name: GPT model name to use
            api_key: OpenAI API key (falls back to env var)
            temperature: Temperature parameter for generation
            max_tokens: Maximum tokens to generate in a response
            timeout: Request timeout in seconds
            retry_max: Maximum number of retries
            retry_delay: Delay between retries in seconds
        """
        super().__init__(
            model_name=model_name,
            api_key=api_key or OPENAI_API_KEY,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout
        )
        
        self.retry_max = retry_max
        self.retry_delay = retry_delay
        self.client = None
        self.tokenizer = None
        
        # Check if dependencies are available
        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI Python package not installed. Install with: pip install openai")
        
        if not TIKTOKEN_AVAILABLE:
            logger.warning("Tiktoken package not installed. Install with: pip install tiktoken")
        else:
            # Initialize tokenizer
            try:
                self.tokenizer = tiktoken.encoding_for_model(model_name)
            except KeyError:
                logger.warning(f"Model {model_name} not found in tiktoken, using cl100k_base encoding")
                try:
                    self.tokenizer = tiktoken.get_encoding("cl100k_base")
                except Exception as e:
                    logger.error(f"Error initializing tokenizer: {str(e)}")
        
        # Initialize OpenAI client
        if not self.api_key:
            logger.warning("No OpenAI API key provided, using mock responses")
        elif not OPENAI_AVAILABLE:
            logger.warning("OpenAI client not available, using mock responses")
        else:
            try:
                self.client = openai.OpenAI(api_key=self.api_key)
                logger.info(f"Initialized OpenAI client with model: {model_name}")
            except Exception as e:
                logger.error(f"Error initializing OpenAI client: {str(e)}")
                self.client = None
    
    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop_sequences: Optional[List[str]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate text using OpenAI GPT.
        
        Args:
            prompt: User input prompt
            temperature: Override default temperature
            max_tokens: Override default max tokens
            stop_sequences: Optional sequences to stop generation
            system_prompt: Optional system prompt
            **kwargs: Additional parameters
            
        Returns:
            Generated text response
        """
        if not self.api_key or not self.client:
            logger.warning("No valid OpenAI client, returning mock response")
            return "This is a mock response because no valid OpenAI API key was provided."
        
        temp = temperature if temperature is not None else self.temperature
        max_tok = max_tokens if max_tokens is not None else self.max_tokens
        
        # Track token usage
        prompt_tokens = self.count_tokens(prompt)
        if system_prompt:
            prompt_tokens += self.count_tokens(system_prompt)
            
        self.total_prompt_tokens += prompt_tokens
        self.total_requests += 1
        
        # Retry logic
        for attempt in range(self.retry_max):
            try:
                # Prepare message format
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                # Make the API call
                start_time = time.time()
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=temp,
                    max_tokens=max_tok,
                    stop=stop_sequences,
                    timeout=self.timeout
                )
                elapsed_time = time.time() - start_time
                
                # Extract the response text
                result = response.choices[0].message.content
                
                # Update stats
                usage = response.usage
                if usage:
                    self.total_prompt_tokens = usage.prompt_tokens
                    self.total_completion_tokens = usage.completion_tokens
                else:
                    completion_tokens = self.count_tokens(result)
                    self.total_completion_tokens += completion_tokens
                
                logger.info(f"OpenAI response received in {elapsed_time:.2f}s, "
                           f"prompt: {prompt_tokens} tokens, "
                           f"completion: {self.total_completion_tokens} tokens")
                
                return result
                
            except (
                requests.exceptions.RequestException,
                json.JSONDecodeError,
                KeyError,
                IndexError,
                ValueError
            ) as e:
                logger.error(f"Error generating text with OpenAI: {str(e)}")
                if attempt < self.retry_max - 1:
                    logger.warning(f"Retrying in {self.retry_delay}s (attempt {attempt+1}/{self.retry_max})")
                    time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    return f"Error: Failed to generate response after {self.retry_max} attempts. Last error: {str(e)}"
        
        return "Error: Failed to generate response after multiple attempts."
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        if not text:
            return 0
            
        if not self.tokenizer or not TIKTOKEN_AVAILABLE:
            # Fallback to character-based approximation
            return len(text) // 4
            
        try:
            return len(self.tokenizer.encode(text))
        except Exception as e:
            logger.warning(f"Error counting tokens with tiktoken: {str(e)}")
            # Fallback to character-based approximation
            return len(text) // 4
            

class MockLLM(BaseLLM):
    """Mock LLM for testing without API access."""
    
    def __init__(
        self,
        model_name: str = "mock-model",
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ):
        """Initialize the Mock LLM.
        
        Args:
            model_name: Fake model name
            temperature: Temperature parameter (not used)
            max_tokens: Maximum tokens (not used)
        """
        super().__init__(
            model_name=model_name,
            api_key="mock-key",
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        logger.info("Initialized MockLLM for testing")
        
    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop_sequences: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """Generate mock text response.
        
        Args:
            prompt: The prompt (used to create mock response)
            temperature: Not used
            max_tokens: Not used
            stop_sequences: Not used
            **kwargs: Additional parameters (not used)
            
        Returns:
            Mock generated text
        """
        # Simulate token counting
        prompt_tokens = self.count_tokens(prompt)
        self.total_prompt_tokens += prompt_tokens
        self.total_requests += 1
        
        # Create a mock response based on the prompt
        if "exabeam" in prompt.lower():
            response = "Exabeam is a security analytics platform that provides SIEM, UEBA, and SOAR capabilities."
        elif "parser" in prompt.lower():
            response = "Parsers in Exabeam extract relevant security information from log data."
        elif "mitre" in prompt.lower() or "att&ck" in prompt.lower():
            response = "The MITRE ATT&CK framework is a knowledge base of adversary tactics and techniques."
        else:
            response = "This is a mock response for testing purposes. No actual LLM was used."
            
        # Simulate completion tokens
        completion_tokens = self.count_tokens(response)
        self.total_completion_tokens += completion_tokens
        
        logger.info(f"MockLLM generated response with "
                   f"prompt: {prompt_tokens} tokens, "
                   f"completion: {completion_tokens} tokens")
        
        return response
        
    def count_tokens(self, text: str) -> int:
        """Simple token estimation for mock responses."""
        if not text:
            return 0
            
        # Simple approximation: 4 characters per token
        return len(text) // 4
        
    def validate_api_key(self) -> bool:
        """Always valid for mock."""
        return True