"""Base agent configuration for Credora CFO system.

Provides reusable model and client setup for all agents.
"""

from openai import AsyncOpenAI
from agents import OpenAIChatCompletionsModel

from credora.config import get_api_key, get_model_config, ModelConfig


def create_openai_client() -> AsyncOpenAI:
    """Create an AsyncOpenAI client configured for Gemini.
    
    Returns:
        Configured AsyncOpenAI client.
    """
    config = get_model_config()
    return AsyncOpenAI(
        api_key=get_api_key(),
        base_url=config.base_url,
    )


def create_model(config: ModelConfig | None = None) -> OpenAIChatCompletionsModel:
    """Create an OpenAI-compatible model for use with agents.
    
    Args:
        config: Optional model configuration. Uses defaults if not provided.
        
    Returns:
        Configured OpenAIChatCompletionsModel instance.
    """
    if config is None:
        config = get_model_config()
    
    client = create_openai_client()
    
    return OpenAIChatCompletionsModel(
        model=config.model_name,
        openai_client=client,
    )


# Default model instance for convenience
def get_default_model() -> OpenAIChatCompletionsModel:
    """Get the default model instance.
    
    Returns:
        Default OpenAIChatCompletionsModel configured for Gemini.
    """
    return create_model()
