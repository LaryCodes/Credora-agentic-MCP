"""CFO Agent state management tools.

Requirements: 4.2

These tools allow the CFO Agent to access and update session state
for context management across conversations.
"""

import json
from typing import Optional
from agents import function_tool

from credora.state import StateManager
from credora.models import SessionState


# Module-level state manager instance
_state_manager: Optional[StateManager] = None


def get_state_manager() -> StateManager:
    """Get the current state manager instance.
    
    Returns:
        The StateManager instance
    """
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager()
    return _state_manager


def set_state_manager(manager: StateManager) -> None:
    """Set the state manager instance (for testing).
    
    Args:
        manager: The StateManager instance to use
    """
    global _state_manager
    _state_manager = manager


def _session_state_to_dict(state: SessionState) -> dict:
    """Convert SessionState to a JSON-serializable dictionary.
    
    Args:
        state: The SessionState to convert
        
    Returns:
        Dictionary representation of the state
    """
    return {
        "user_id": state.user_id,
        "connected_platforms": state.connected_platforms,
        "business_goals": state.business_goals,
        "completed_analyses": state.completed_analyses,
        "onboarding_complete": state.onboarding_complete,
        "last_interaction": state.last_interaction.isoformat(),
    }


@function_tool
def get_session_state(user_id: str) -> str:
    """Retrieve the current session state for a user.
    
    Use this tool to access the user's context including connected platforms,
    business goals, completed analyses, and onboarding status. This helps
    avoid asking redundant questions and maintain conversation continuity.
    
    Args:
        user_id: The unique identifier for the user
        
    Returns:
        JSON string containing the session state with fields:
        - user_id: The user's identifier
        - connected_platforms: List of connected e-commerce platforms
        - business_goals: List of user's business objectives
        - completed_analyses: List of analyses already performed
        - onboarding_complete: Whether onboarding is finished
        - last_interaction: Timestamp of last interaction
        
    Requirements: 4.2
    """
    if not user_id or not user_id.strip():
        return json.dumps({
            "error": "user_id is required and cannot be empty",
            "success": False
        })
    
    try:
        manager = get_state_manager()
        state = manager.get_session_state(user_id)
        
        result = _session_state_to_dict(state)
        result["success"] = True
        
        return json.dumps(result)
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "success": False
        })


@function_tool
def update_session_state(user_id: str, updates_json: str) -> str:
    """Update the session state for a user.
    
    Use this tool to persist changes to the user's context, such as
    recording completed analyses, updating business goals, or marking
    onboarding as complete.
    
    Args:
        user_id: The unique identifier for the user
        updates_json: JSON string containing fields to update. Valid fields:
            - connected_platforms: List of platform names
            - business_goals: List of goal strings
            - completed_analyses: List of analysis type strings
            - onboarding_complete: Boolean
            
    Returns:
        JSON string containing the updated session state or error message
        
    Requirements: 4.2
    """
    if not user_id or not user_id.strip():
        return json.dumps({
            "error": "user_id is required and cannot be empty",
            "success": False
        })
    
    try:
        updates = json.loads(updates_json)
    except json.JSONDecodeError as e:
        return json.dumps({
            "error": f"Invalid JSON in updates_json: {str(e)}",
            "success": False
        })
    
    if not isinstance(updates, dict):
        return json.dumps({
            "error": "updates_json must be a JSON object",
            "success": False
        })
    
    try:
        manager = get_state_manager()
        state = manager.update_session_state(user_id, updates)
        
        result = _session_state_to_dict(state)
        result["success"] = True
        
        return json.dumps(result)
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "success": False
        })


__all__ = [
    "get_session_state",
    "update_session_state",
    "get_state_manager",
    "set_state_manager",
]
