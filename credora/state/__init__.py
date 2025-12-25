"""State management for session persistence.

Requirements: 4.1, 4.2, 4.3, 4.4, 8.2
"""

from datetime import datetime
from typing import Dict, Optional
from copy import deepcopy

from credora.models import SessionState
from credora.security import get_user_isolation


class StateManager:
    """Manages session state with in-memory storage.
    
    Provides get, update, and clear operations for user sessions.
    Designed to be upgradeable to persistent storage later.
    Enforces user data isolation boundaries.
    
    Requirements: 4.1, 4.2, 4.3, 4.4, 8.2
    """
    
    def __init__(self):
        self._sessions: Dict[str, SessionState] = {}
    
    def _validate_user_id(self, user_id: str) -> None:
        """Validate user_id and enforce isolation boundaries.
        
        Args:
            user_id: The user identifier to validate
            
        Raises:
            ValueError: If user_id is invalid
            
        Requirements: 8.2
        """
        if not user_id or not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("user_id is required and cannot be empty")
        
        # Register with isolation tracker
        isolation = get_user_isolation()
        isolation.validate_user_id(user_id)
    
    def get_session_state(self, user_id: str) -> SessionState:
        """Retrieve session state for a user.
        
        If no session exists, creates a new one.
        Enforces user data isolation - users can only access their own sessions.
        
        Args:
            user_id: The unique identifier for the user
            
        Returns:
            SessionState for the user
            
        Requirements: 4.2, 8.2
        """
        self._validate_user_id(user_id)
        
        if user_id not in self._sessions:
            self._sessions[user_id] = SessionState(user_id=user_id)
            # Register session ownership with isolation tracker
            isolation = get_user_isolation()
            isolation.register_data_ownership(user_id, f"session:{user_id}")
        
        return deepcopy(self._sessions[user_id])
    
    def update_session_state(self, user_id: str, updates: Dict) -> SessionState:
        """Update session state with new values.
        
        Enforces user data isolation - users can only update their own sessions.
        
        Args:
            user_id: The unique identifier for the user
            updates: Dictionary of field names to new values
            
        Returns:
            Updated SessionState
            
        Requirements: 4.1, 4.3, 4.4, 8.2
        """
        self._validate_user_id(user_id)

        # Get or create session
        if user_id not in self._sessions:
            self._sessions[user_id] = SessionState(user_id=user_id)
            # Register session ownership with isolation tracker
            isolation = get_user_isolation()
            isolation.register_data_ownership(user_id, f"session:{user_id}")
        
        session = self._sessions[user_id]
        
        # Apply updates to valid fields
        valid_fields = {
            "connected_platforms",
            "platform_tokens", 
            "business_goals",
            "completed_analyses",
            "onboarding_complete",
            "last_interaction",
        }
        
        for key, value in updates.items():
            if key in valid_fields:
                setattr(session, key, value)
        
        # Always update last_interaction
        session.last_interaction = datetime.now()
        
        return deepcopy(session)
    
    def clear_session(self, user_id: str) -> bool:
        """Clear all session data for a user.
        
        Enforces user data isolation - users can only clear their own sessions.
        
        Args:
            user_id: The unique identifier for the user
            
        Returns:
            True if session was cleared, False if no session existed
            
        Requirements: 8.2, 8.3
        """
        self._validate_user_id(user_id)
        
        if user_id in self._sessions:
            del self._sessions[user_id]
            # Remove session ownership from isolation tracker
            isolation = get_user_isolation()
            isolation.remove_data_ownership(user_id, f"session:{user_id}")
            return True
        return False
    
    def has_context(self, user_id: str, context_key: str) -> bool:
        """Check if a specific context exists in session state.
        
        Used to avoid redundant questions (Requirement 4.5).
        Enforces user data isolation.
        
        Args:
            user_id: The unique identifier for the user
            context_key: The context field to check
            
        Returns:
            True if context exists and is non-empty
            
        Requirements: 4.5, 8.2
        """
        self._validate_user_id(user_id)
        
        if user_id not in self._sessions:
            return False
        
        session = self._sessions[user_id]
        
        if not hasattr(session, context_key):
            return False
        
        value = getattr(session, context_key)
        
        # Check for non-empty values
        if value is None:
            return False
        if isinstance(value, (list, dict, str)) and len(value) == 0:
            return False
        if isinstance(value, bool):
            return value
        
        return True
    
    def get_session_for_user_only(self, requesting_user_id: str, target_user_id: str) -> Optional[SessionState]:
        """Get session state only if requesting user matches target user.
        
        This method enforces strict user data isolation by ensuring
        a user can only access their own session data.
        
        Args:
            requesting_user_id: The user making the request
            target_user_id: The user whose session is being requested
            
        Returns:
            SessionState if user has access, None otherwise
            
        Requirements: 8.2
        """
        self._validate_user_id(requesting_user_id)
        self._validate_user_id(target_user_id)
        
        # Strict isolation: users can only access their own data
        if requesting_user_id != target_user_id:
            return None
        
        return self.get_session_state(requesting_user_id)
    
    def verify_user_isolation(self, user_id_a: str, user_id_b: str) -> bool:
        """Verify that two users have completely isolated session data.
        
        Args:
            user_id_a: First user
            user_id_b: Second user
            
        Returns:
            True if users have isolated data (no cross-access possible)
            
        Requirements: 8.2
        """
        self._validate_user_id(user_id_a)
        self._validate_user_id(user_id_b)
        
        if user_id_a == user_id_b:
            return True  # Same user, isolation is trivially satisfied
        
        # Check that neither user can access the other's session
        session_a = self.get_session_for_user_only(user_id_a, user_id_b)
        session_b = self.get_session_for_user_only(user_id_b, user_id_a)
        
        # Both should be None (no cross-access)
        return session_a is None and session_b is None


__all__ = ["StateManager"]
