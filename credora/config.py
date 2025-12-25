"""Configuration for Credora CFO Agent system.

Handles LLM provider setup with OpenRouter via OpenAI-compatible interface.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ModelConfig:
    """Configuration for LLM model."""
    
    model_name: str = "nex-agi/deepseek-v3.1-nex-n1:free"
    base_url: str = "https://openrouter.ai/api/v1"
    temperature: float = 0.7
    max_tokens: int = 4096


def get_api_key() -> str:
    """Get the OpenRouter API key from environment.
    
    Returns:
        The API key string.
        
    Raises:
        ValueError: If OPENROUTER_API_KEY is not set.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY environment variable is not set. "
            "Please set it in your .env file or environment."
        )
    return api_key


def get_model_config(
    model_name: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> ModelConfig:
    """Get model configuration with optional overrides.
    
    Args:
        model_name: Override default model name.
        temperature: Override default temperature.
        max_tokens: Override default max tokens.
        
    Returns:
        ModelConfig instance with specified or default values.
    """
    config = ModelConfig()
    if model_name is not None:
        config.model_name = model_name
    if temperature is not None:
        config.temperature = temperature
    if max_tokens is not None:
        config.max_tokens = max_tokens
    return config
