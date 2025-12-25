"""Property-based tests for onboarding functionality.

**Feature: credora-cfo-agent**
"""

import pytest
from hypothesis import given, strategies as st, settings

from credora.tools.onboarding import (
    _collect_platform_type_impl,
    _collect_business_goals_impl,
    _initiate_oauth_impl,
    _complete_onboarding_impl,
    get_state_manager,
    set_state_manager,
    VALID_PLATFORMS,
    VALID_GOALS,
)
from credora.state import StateManager


# Strategies for generating test data
user_id_strategy = st.text(min_size=1, max_size=50).filter(lambda x: x.strip())
platform_strategy = st.sampled_from(VALID_PLATFORMS)
goals_strategy = st.lists(
    st.sampled_from(VALID_GOALS),
    min_size=1,
    max_size=4,
    unique=True,
)


class TestIncrementalQuestioning:
    """
    **Feature: credora-cfo-agent, Property 3: Incremental Questioning**
    **Validates: Requirements 2.2**
    
    For any onboarding interaction, each agent response shall contain at most
    one question or request for information, never multiple questions in a
    single response.
    
    This property is validated by ensuring that each onboarding tool:
    1. Collects exactly one piece of information per call
    2. Returns a single, focused response
    3. Does not ask for additional information in its response
    """

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
    )
    def test_collect_platform_type_single_response(self, user_id: str, platform: str):
        """collect_platform_type should return a single focused response."""
        # Set up fresh state manager for each test
        manager = StateManager()
        set_state_manager(manager)
        
        result = _collect_platform_type_impl(user_id, platform)
        
        # Response should not contain question marks (no follow-up questions)
        # A confirmation message should not ask for more info
        assert "?" not in result or "Error" in result
        
        # Response should be a single statement, not multiple requests
        # Count sentences by periods (excluding common abbreviations)
        sentences = [s.strip() for s in result.split(".") if s.strip()]
        # Allow up to 2 sentences (confirmation + optional context)
        assert len(sentences) <= 2

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        goals=goals_strategy,
    )
    def test_collect_business_goals_single_response(self, user_id: str, goals: list):
        """collect_business_goals should return a single focused response."""
        manager = StateManager()
        set_state_manager(manager)
        
        result = _collect_business_goals_impl(user_id, goals)
        
        # Response should not contain question marks asking for more info
        assert "?" not in result or "Error" in result
        
        # Response should be focused on confirming the goals collected
        sentences = [s.strip() for s in result.split(".") if s.strip()]
        assert len(sentences) <= 2

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=st.sampled_from(["shopify", "woocommerce"]),  # OAuth-capable platforms
    )
    def test_initiate_oauth_single_response(self, user_id: str, platform: str):
        """initiate_oauth should return a single focused response."""
        manager = StateManager()
        set_state_manager(manager)
        
        result = _initiate_oauth_impl(user_id, platform)
        
        # Response should not ask follow-up questions
        assert "?" not in result or "Error" in result
        
        # Response should be a single status message
        sentences = [s.strip() for s in result.split(".") if s.strip()]
        assert len(sentences) <= 2

    @settings(max_examples=100)
    @given(user_id=user_id_strategy)
    def test_complete_onboarding_incomplete_single_error(self, user_id: str):
        """complete_onboarding with missing data should return single error."""
        manager = StateManager()
        set_state_manager(manager)
        
        # Don't set up any data - should fail with missing info
        result = _complete_onboarding_impl(user_id)
        
        # Should indicate what's missing without asking multiple questions
        assert "incomplete" in result.lower() or "missing" in result.lower()
        
        # Should not contain multiple question marks
        question_count = result.count("?")
        assert question_count <= 1

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
        goals=goals_strategy,
    )
    def test_complete_onboarding_success_single_summary(
        self, user_id: str, platform: str, goals: list
    ):
        """complete_onboarding with all data should return single summary."""
        manager = StateManager()
        set_state_manager(manager)
        
        # Set up complete onboarding data
        _collect_platform_type_impl(user_id, platform)
        _collect_business_goals_impl(user_id, goals)
        
        result = _complete_onboarding_impl(user_id)
        
        # Should be a summary, not asking for more info
        assert "complete" in result.lower()
        
        # Should not ask follow-up questions in the summary
        # (questions in summary would violate incremental questioning)
        question_count = result.count("?")
        assert question_count == 0



class TestOnboardingDataCompleteness:
    """
    **Feature: credora-cfo-agent, Property 4: Onboarding Data Completeness**
    **Validates: Requirements 2.3, 2.4**
    
    For any completed onboarding session, the session state shall contain both
    platform_type and business_goals fields with non-empty values.
    """

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
        goals=goals_strategy,
    )
    def test_completed_onboarding_has_platform(
        self, user_id: str, platform: str, goals: list
    ):
        """Completed onboarding should have platform_type in session state."""
        manager = StateManager()
        set_state_manager(manager)
        
        # Complete the onboarding flow
        _collect_platform_type_impl(user_id, platform)
        _collect_business_goals_impl(user_id, goals)
        result = _complete_onboarding_impl(user_id)
        
        # Verify onboarding completed successfully
        assert "complete" in result.lower()
        
        # Verify platform is stored
        session = manager.get_session_state(user_id)
        assert len(session.connected_platforms) > 0
        assert platform in session.connected_platforms

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
        goals=goals_strategy,
    )
    def test_completed_onboarding_has_business_goals(
        self, user_id: str, platform: str, goals: list
    ):
        """Completed onboarding should have business_goals in session state."""
        manager = StateManager()
        set_state_manager(manager)
        
        # Complete the onboarding flow
        _collect_platform_type_impl(user_id, platform)
        _collect_business_goals_impl(user_id, goals)
        result = _complete_onboarding_impl(user_id)
        
        # Verify onboarding completed successfully
        assert "complete" in result.lower()
        
        # Verify goals are stored
        session = manager.get_session_state(user_id)
        assert len(session.business_goals) > 0
        # All provided goals should be stored (normalized to lowercase)
        for goal in goals:
            assert goal.lower() in session.business_goals

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
        goals=goals_strategy,
    )
    def test_completed_onboarding_marks_complete_flag(
        self, user_id: str, platform: str, goals: list
    ):
        """Completed onboarding should set onboarding_complete to True."""
        manager = StateManager()
        set_state_manager(manager)
        
        # Complete the onboarding flow
        _collect_platform_type_impl(user_id, platform)
        _collect_business_goals_impl(user_id, goals)
        _complete_onboarding_impl(user_id)
        
        # Verify onboarding_complete flag is set
        session = manager.get_session_state(user_id)
        assert session.onboarding_complete is True

    @settings(max_examples=100)
    @given(user_id=user_id_strategy)
    def test_incomplete_onboarding_missing_platform_fails(self, user_id: str):
        """Onboarding without platform should fail completeness check."""
        manager = StateManager()
        set_state_manager(manager)
        
        # Only set goals, not platform
        _collect_business_goals_impl(user_id, ["growth"])
        result = _complete_onboarding_impl(user_id)
        
        # Should indicate incomplete
        assert "incomplete" in result.lower() or "missing" in result.lower()
        
        # onboarding_complete should remain False
        session = manager.get_session_state(user_id)
        assert session.onboarding_complete is False

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
    )
    def test_incomplete_onboarding_missing_goals_fails(
        self, user_id: str, platform: str
    ):
        """Onboarding without business goals should fail completeness check."""
        manager = StateManager()
        set_state_manager(manager)
        
        # Only set platform, not goals
        _collect_platform_type_impl(user_id, platform)
        result = _complete_onboarding_impl(user_id)
        
        # Should indicate incomplete
        assert "incomplete" in result.lower() or "missing" in result.lower()
        
        # onboarding_complete should remain False
        session = manager.get_session_state(user_id)
        assert session.onboarding_complete is False

    @settings(max_examples=100)
    @given(user_id=user_id_strategy)
    def test_incomplete_onboarding_missing_both_fails(self, user_id: str):
        """Onboarding without any data should fail completeness check."""
        manager = StateManager()
        set_state_manager(manager)
        
        # Don't set anything
        result = _complete_onboarding_impl(user_id)
        
        # Should indicate incomplete
        assert "incomplete" in result.lower() or "missing" in result.lower()
        
        # onboarding_complete should remain False
        session = manager.get_session_state(user_id)
        assert session.onboarding_complete is False
