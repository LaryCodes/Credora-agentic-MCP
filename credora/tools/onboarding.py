"""Onboarding tools for collecting user business context.

Requirements: 2.3, 2.4, 2.5, 2.6
"""

from typing import List
from agents import function_tool

from credora.state import StateManager
from credora.security import encrypt_token


# Global state manager instance (can be injected for testing)
_state_manager: StateManager | None = None


def get_state_manager() -> StateManager:
    """Get or create the global state manager."""
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager()
    return _state_manager


def set_state_manager(manager: StateManager) -> None:
    """Set the state manager (for testing)."""
    global _state_manager
    _state_manager = manager


VALID_PLATFORMS = ["shopify", "woocommerce", "other"]
VALID_GOALS = ["growth", "cost_optimization", "retention", "expansion"]


def _collect_platform_type_impl(user_id: str, platform: str) -> str:
    """Internal implementation of collect_platform_type.
    
    Args:
        user_id: The unique identifier for the user
        platform: The e-commerce platform type (shopify, woocommerce, or other)
        
    Returns:
        Confirmation message or error
        
    Requirements: 2.3
    """
    if not user_id or not user_id.strip():
        return "Error: user_id is required"
    
    platform_lower = platform.lower().strip()
    if platform_lower not in VALID_PLATFORMS:
        return f"Error: Invalid platform. Please choose from: {', '.join(VALID_PLATFORMS)}"
    
    manager = get_state_manager()
    session = manager.get_session_state(user_id)
    
    # Add platform to connected platforms if not already there
    platforms = session.connected_platforms.copy()
    if platform_lower not in platforms:
        platforms.append(platform_lower)
    
    manager.update_session_state(user_id, {"connected_platforms": platforms})
    
    return f"Platform type '{platform_lower}' has been recorded for your account."


def _collect_business_goals_impl(user_id: str, goals: List[str]) -> str:
    """Internal implementation of collect_business_goals.
    
    Args:
        user_id: The unique identifier for the user
        goals: List of business goals (growth, cost_optimization, retention, expansion)
        
    Returns:
        Confirmation message or error
        
    Requirements: 2.4
    """
    if not user_id or not user_id.strip():
        return "Error: user_id is required"
    
    if not goals:
        return "Error: At least one business goal is required"
    
    # Validate and normalize goals
    normalized_goals = []
    invalid_goals = []
    
    for goal in goals:
        goal_lower = goal.lower().strip()
        if goal_lower in VALID_GOALS:
            if goal_lower not in normalized_goals:
                normalized_goals.append(goal_lower)
        else:
            invalid_goals.append(goal)
    
    if invalid_goals:
        return f"Error: Invalid goals: {', '.join(invalid_goals)}. Valid options: {', '.join(VALID_GOALS)}"
    
    if not normalized_goals:
        return f"Error: No valid goals provided. Valid options: {', '.join(VALID_GOALS)}"
    
    manager = get_state_manager()
    manager.update_session_state(user_id, {"business_goals": normalized_goals})
    
    return f"Business goals recorded: {', '.join(normalized_goals)}"


def _initiate_oauth_impl(user_id: str, platform: str) -> str:
    """Internal implementation of initiate_oauth.
    
    This is a mock implementation that simulates the OAuth flow.
    In production, this would redirect to the platform's OAuth endpoint.
    
    Args:
        user_id: The unique identifier for the user
        platform: The e-commerce platform to authenticate with
        
    Returns:
        OAuth flow status message
        
    Requirements: 2.5
    """
    if not user_id or not user_id.strip():
        return "Error: user_id is required"
    
    platform_lower = platform.lower().strip()
    if platform_lower not in VALID_PLATFORMS:
        return f"Error: Invalid platform. Please choose from: {', '.join(VALID_PLATFORMS)}"
    
    if platform_lower == "other":
        return "Error: OAuth is not available for 'other' platform type."
    
    manager = get_state_manager()
    session = manager.get_session_state(user_id)
    
    # Check if already connected
    if platform_lower in session.connected_platforms:
        return f"Platform '{platform_lower}' is already connected."
    
    # Mock OAuth flow - in production this would:
    # 1. Generate OAuth state token
    # 2. Return authorization URL
    # 3. Handle callback with auth code
    # 4. Exchange for access token
    
    # For now, simulate successful OAuth with a mock token
    mock_token = f"mock_oauth_token_{platform_lower}_{user_id}"
    encrypted_token = encrypt_token(mock_token)
    
    # Update session with new platform and encrypted token
    platforms = session.connected_platforms.copy()
    platforms.append(platform_lower)
    
    tokens = session.platform_tokens.copy()
    tokens[platform_lower] = encrypted_token
    
    manager.update_session_state(user_id, {
        "connected_platforms": platforms,
        "platform_tokens": tokens,
    })
    
    return f"OAuth authentication successful for {platform_lower}."


def _complete_onboarding_impl(user_id: str) -> str:
    """Internal implementation of complete_onboarding.
    
    Validates that all required information has been collected and marks
    onboarding as complete.
    
    Args:
        user_id: The unique identifier for the user
        
    Returns:
        Summary of collected information or error if incomplete
        
    Requirements: 2.6
    """
    if not user_id or not user_id.strip():
        return "Error: user_id is required"
    
    manager = get_state_manager()
    session = manager.get_session_state(user_id)
    
    # Check for required information
    missing = []
    
    if not session.connected_platforms:
        missing.append("platform type")
    
    if not session.business_goals:
        missing.append("business goals")
    
    if missing:
        return f"Onboarding incomplete. Missing: {', '.join(missing)}."
    
    # Mark onboarding as complete
    manager.update_session_state(user_id, {"onboarding_complete": True})
    
    # Generate summary
    platforms_str = ", ".join(session.connected_platforms)
    goals_str = ", ".join(session.business_goals)
    
    summary = f"""Onboarding complete! Here's a summary of your setup:

- Connected platforms: {platforms_str}
- Business goals: {goals_str}

Your virtual CFO is now ready to help you analyze your business data."""
    
    return summary


# Decorated tools for agent use
@function_tool
def collect_platform_type(user_id: str, platform: str) -> str:
    """Collect and store the user's e-commerce platform type.
    
    Args:
        user_id: The unique identifier for the user
        platform: The e-commerce platform type (shopify, woocommerce, or other)
        
    Returns:
        Confirmation message or error
    """
    return _collect_platform_type_impl(user_id, platform)


@function_tool
def collect_business_goals(user_id: str, goals: List[str]) -> str:
    """Collect and store the user's primary business goals.
    
    Args:
        user_id: The unique identifier for the user
        goals: List of business goals (growth, cost_optimization, retention, expansion)
        
    Returns:
        Confirmation message or error
    """
    return _collect_business_goals_impl(user_id, goals)


@function_tool
def initiate_oauth(user_id: str, platform: str) -> str:
    """Initiate OAuth authentication flow for a platform.
    
    Args:
        user_id: The unique identifier for the user
        platform: The e-commerce platform to authenticate with
        
    Returns:
        OAuth flow status message
    """
    return _initiate_oauth_impl(user_id, platform)


@function_tool
def complete_onboarding(user_id: str) -> str:
    """Complete the onboarding process and summarize collected information.
    
    Args:
        user_id: The unique identifier for the user
        
    Returns:
        Summary of collected information or error if incomplete
    """
    return _complete_onboarding_impl(user_id)


__all__ = [
    # Decorated tools for agent use
    "collect_platform_type",
    "collect_business_goals",
    "initiate_oauth",
    "complete_onboarding",
    # Internal implementations for testing
    "_collect_platform_type_impl",
    "_collect_business_goals_impl",
    "_initiate_oauth_impl",
    "_complete_onboarding_impl",
    # Utilities
    "get_state_manager",
    "set_state_manager",
    "VALID_PLATFORMS",
    "VALID_GOALS",
]
