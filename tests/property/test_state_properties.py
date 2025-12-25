"""Property-based tests for state management.

**Feature: credora-cfo-agent**
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime

from credora.models import SessionState
from credora.state import StateManager


# Strategies for generating test data
user_id_strategy = st.text(min_size=1, max_size=50).filter(lambda x: x.strip())
platform_strategy = st.sampled_from(["shopify", "woocommerce", "amazon", "etsy"])
goals_strategy = st.lists(
    st.sampled_from(["growth", "cost_optimization", "retention", "expansion"]),
    min_size=0,
    max_size=4,
)


class TestStateRoundTrip:
    """
    **Feature: credora-cfo-agent, Property 8: State Persistence Round-Trip**
    **Validates: Requirements 4.1, 4.3, 4.4**
    
    For any session state update, saving the state and then retrieving it
    shall produce an equivalent state object.
    """

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platforms=st.lists(platform_strategy, min_size=0, max_size=3, unique=True),
        goals=goals_strategy,
        onboarding_complete=st.booleans(),
    )
    def test_state_round_trip_preserves_data(
        self, user_id: str, platforms: list, goals: list, onboarding_complete: bool
    ):
        """State updates should be retrievable with equivalent values."""
        manager = StateManager()
        
        # Update state with generated values
        updates = {
            "connected_platforms": platforms,
            "business_goals": goals,
            "onboarding_complete": onboarding_complete,
        }
        
        manager.update_session_state(user_id, updates)
        
        # Retrieve state
        retrieved = manager.get_session_state(user_id)
        
        # Verify round-trip preserves data
        assert retrieved.user_id == user_id
        assert retrieved.connected_platforms == platforms
        assert retrieved.business_goals == goals
        assert retrieved.onboarding_complete == onboarding_complete

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        analyses=st.lists(
            st.text(min_size=1, max_size=20).filter(lambda x: x.strip()),
            min_size=0,
            max_size=5,
        ),
    )
    def test_completed_analyses_round_trip(self, user_id: str, analyses: list):
        """Completed analyses should persist through round-trip."""
        manager = StateManager()
        
        manager.update_session_state(user_id, {"completed_analyses": analyses})
        retrieved = manager.get_session_state(user_id)
        
        assert retrieved.completed_analyses == analyses

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        token_keys=st.lists(platform_strategy, min_size=0, max_size=3, unique=True),
    )
    def test_platform_tokens_round_trip(self, user_id: str, token_keys: list):
        """Platform tokens dict should persist through round-trip."""
        manager = StateManager()
        
        # Create tokens dict
        tokens = {key: f"token_{key}_123" for key in token_keys}
        
        manager.update_session_state(user_id, {"platform_tokens": tokens})
        retrieved = manager.get_session_state(user_id)
        
        assert retrieved.platform_tokens == tokens



class TestNoRedundantQuestions:
    """
    **Feature: credora-cfo-agent, Property 9: No Redundant Questions**
    **Validates: Requirements 4.5**
    
    For any user session with stored context, the agent shall not ask for
    information that already exists in the session state.
    """

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platforms=st.lists(platform_strategy, min_size=1, max_size=3, unique=True),
    )
    def test_has_context_detects_connected_platforms(
        self, user_id: str, platforms: list
    ):
        """has_context should return True when platforms are connected."""
        manager = StateManager()
        
        manager.update_session_state(user_id, {"connected_platforms": platforms})
        
        assert manager.has_context(user_id, "connected_platforms") is True

    @settings(max_examples=100)
    @given(user_id=user_id_strategy)
    def test_has_context_returns_false_for_empty_platforms(self, user_id: str):
        """has_context should return False when platforms list is empty."""
        manager = StateManager()
        
        manager.update_session_state(user_id, {"connected_platforms": []})
        
        assert manager.has_context(user_id, "connected_platforms") is False

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        goals=st.lists(
            st.sampled_from(["growth", "cost_optimization", "retention"]),
            min_size=1,
            max_size=3,
        ),
    )
    def test_has_context_detects_business_goals(self, user_id: str, goals: list):
        """has_context should return True when business goals are set."""
        manager = StateManager()
        
        manager.update_session_state(user_id, {"business_goals": goals})
        
        assert manager.has_context(user_id, "business_goals") is True

    @settings(max_examples=100)
    @given(user_id=user_id_strategy)
    def test_has_context_returns_false_for_empty_goals(self, user_id: str):
        """has_context should return False when goals list is empty."""
        manager = StateManager()
        
        manager.update_session_state(user_id, {"business_goals": []})
        
        assert manager.has_context(user_id, "business_goals") is False

    @settings(max_examples=100)
    @given(user_id=user_id_strategy)
    def test_has_context_detects_onboarding_complete(self, user_id: str):
        """has_context should return True when onboarding is complete."""
        manager = StateManager()
        
        manager.update_session_state(user_id, {"onboarding_complete": True})
        
        assert manager.has_context(user_id, "onboarding_complete") is True

    @settings(max_examples=100)
    @given(user_id=user_id_strategy)
    def test_has_context_returns_false_for_incomplete_onboarding(self, user_id: str):
        """has_context should return False when onboarding is not complete."""
        manager = StateManager()
        
        manager.update_session_state(user_id, {"onboarding_complete": False})
        
        assert manager.has_context(user_id, "onboarding_complete") is False

    @settings(max_examples=100)
    @given(user_id=user_id_strategy)
    def test_has_context_returns_false_for_nonexistent_session(self, user_id: str):
        """has_context should return False for users without sessions."""
        manager = StateManager()
        
        # Don't create any session
        assert manager.has_context(user_id, "connected_platforms") is False
        assert manager.has_context(user_id, "business_goals") is False

    @settings(max_examples=100)
    @given(user_id=user_id_strategy)
    def test_has_context_returns_false_for_invalid_key(self, user_id: str):
        """has_context should return False for non-existent context keys."""
        manager = StateManager()
        
        manager.get_session_state(user_id)  # Create session
        
        assert manager.has_context(user_id, "nonexistent_field") is False
