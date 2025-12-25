"""Property-based tests for competitor agent data isolation.

**Feature: credora-cfo-agent, Property 18: Competitor Agent Data Isolation**
**Validates: Requirements 8.4, 8.5**

For any competitor analysis operation, the Competitor Agent shall not receive
or use any user store data as input.
"""

import inspect
from typing import get_type_hints

import pytest
from hypothesis import given, strategies as st, settings

from credora.tools.competitor import (
    _search_competitor_impl,
    _analyze_competitor_pricing_impl,
    _get_market_trends_impl,
    VALID_INDUSTRIES,
)
from credora.models import SessionState, UserContext


# Strategies for generating valid competitor tool inputs
competitor_name_strategy = st.text(min_size=2, max_size=100).filter(
    lambda x: len(x.strip()) >= 2
)

competitor_url_strategy = st.sampled_from([
    "https://example.com",
    "https://competitor.com/products",
    "http://store.example.org",
]).flatmap(
    lambda base: st.text(min_size=0, max_size=50).map(
        lambda suffix: f"{base}/{suffix.replace(' ', '-')}"[:500]
    )
)

industry_strategy = st.sampled_from(VALID_INDUSTRIES)


# Strategies for generating user store data (should NOT be accepted by competitor tools)
# Use realistic user IDs that wouldn't naturally appear in public data outputs
# Format: user_<uuid-like-string> to avoid false positives from short strings
user_id_strategy = st.uuids().map(lambda u: f"user_{u}")

# Generate realistic platform tokens (long random strings)
platform_token_strategy = st.uuids().map(lambda u: f"tok_{u}_{u}")

session_state_strategy = st.builds(
    SessionState,
    user_id=user_id_strategy,
    connected_platforms=st.lists(st.sampled_from(["shopify", "woocommerce"]), max_size=3),
    platform_tokens=st.dictionaries(
        st.sampled_from(["shopify", "woocommerce"]),
        platform_token_strategy,
        max_size=2,
    ),
    business_goals=st.lists(st.sampled_from(["growth", "cost_optimization", "retention"]), max_size=3),
)

user_context_strategy = st.builds(
    UserContext,
    user_id=user_id_strategy,
    platform_type=st.sampled_from(["shopify", "woocommerce", "other"]),
    business_goals=st.lists(st.sampled_from(["growth", "cost_optimization"]), max_size=3),
    store_name=st.uuids().map(lambda u: f"store_{u}"),
)


class TestCompetitorDataIsolation:
    """
    **Feature: credora-cfo-agent, Property 18: Competitor Agent Data Isolation**
    **Validates: Requirements 8.4, 8.5**
    
    For any competitor analysis operation, the Competitor Agent shall not
    receive or use any user store data as input.
    """

    def test_search_competitor_signature_excludes_user_data(self):
        """search_competitor should not accept user store data parameters."""
        sig = inspect.signature(_search_competitor_impl)
        param_names = set(sig.parameters.keys())
        
        # These parameter names would indicate user store data is being passed
        forbidden_params = {
            "user_id", "session", "session_state", "user_context",
            "store_data", "user_data", "platform_token", "sales_data",
            "orders", "products", "customers", "revenue", "metrics",
        }
        
        intersection = param_names & forbidden_params
        assert len(intersection) == 0, (
            f"search_competitor should not accept user data params: {intersection}"
        )

    def test_analyze_competitor_pricing_signature_excludes_user_data(self):
        """analyze_competitor_pricing should not accept user store data parameters."""
        sig = inspect.signature(_analyze_competitor_pricing_impl)
        param_names = set(sig.parameters.keys())
        
        forbidden_params = {
            "user_id", "session", "session_state", "user_context",
            "store_data", "user_data", "platform_token", "sales_data",
            "orders", "products", "customers", "revenue", "metrics",
            "user_pricing", "store_pricing",
        }
        
        intersection = param_names & forbidden_params
        assert len(intersection) == 0, (
            f"analyze_competitor_pricing should not accept user data params: {intersection}"
        )

    def test_get_market_trends_signature_excludes_user_data(self):
        """get_market_trends should not accept user store data parameters."""
        sig = inspect.signature(_get_market_trends_impl)
        param_names = set(sig.parameters.keys())
        
        forbidden_params = {
            "user_id", "session", "session_state", "user_context",
            "store_data", "user_data", "platform_token", "sales_data",
            "orders", "products", "customers", "revenue", "metrics",
        }
        
        intersection = param_names & forbidden_params
        assert len(intersection) == 0, (
            f"get_market_trends should not accept user data params: {intersection}"
        )

    @settings(max_examples=100)
    @given(competitor_name=competitor_name_strategy)
    def test_search_competitor_output_contains_public_data_notice(
        self, competitor_name: str
    ):
        """search_competitor output should indicate data is from public sources."""
        result = _search_competitor_impl(competitor_name)
        
        # Skip error responses
        if result.startswith("Error:"):
            return
        
        # Output should indicate public data only
        assert "public" in result.lower() or "Public" in result, (
            "search_competitor output should indicate data is from public sources"
        )

    @settings(max_examples=100)
    @given(competitor_url=competitor_url_strategy)
    def test_analyze_competitor_pricing_output_contains_public_data_notice(
        self, competitor_url: str
    ):
        """analyze_competitor_pricing output should indicate data is from public sources."""
        result = _analyze_competitor_pricing_impl(competitor_url)
        
        # Skip error responses
        if result.startswith("Error:"):
            return
        
        # Output should indicate public data only
        assert "public" in result.lower() or "Public" in result, (
            "analyze_competitor_pricing output should indicate data is from public sources"
        )

    @settings(max_examples=100)
    @given(industry=industry_strategy)
    def test_get_market_trends_output_contains_public_data_notice(
        self, industry: str
    ):
        """get_market_trends output should indicate data is from public sources."""
        result = _get_market_trends_impl(industry)
        
        # Skip error responses
        if result.startswith("Error:"):
            return
        
        # Output should indicate public data only
        assert "public" in result.lower() or "Public" in result, (
            "get_market_trends output should indicate data is from public sources"
        )

    @settings(max_examples=100)
    @given(
        competitor_name=competitor_name_strategy,
        session_state=session_state_strategy,
    )
    def test_search_competitor_output_excludes_user_identifiers(
        self, competitor_name: str, session_state: SessionState
    ):
        """search_competitor output should not contain user-specific identifiers."""
        result = _search_competitor_impl(competitor_name)
        
        # Skip error responses
        if result.startswith("Error:"):
            return
        
        # Output should not contain user's ID or platform tokens
        assert session_state.user_id not in result, (
            "search_competitor output should not contain user_id"
        )
        for token in session_state.platform_tokens.values():
            assert token not in result, (
                "search_competitor output should not contain platform tokens"
            )

    @settings(max_examples=100)
    @given(
        competitor_url=competitor_url_strategy,
        session_state=session_state_strategy,
    )
    def test_analyze_competitor_pricing_output_excludes_user_identifiers(
        self, competitor_url: str, session_state: SessionState
    ):
        """analyze_competitor_pricing output should not contain user-specific identifiers."""
        result = _analyze_competitor_pricing_impl(competitor_url)
        
        # Skip error responses
        if result.startswith("Error:"):
            return
        
        # Output should not contain user's ID or platform tokens
        assert session_state.user_id not in result, (
            "analyze_competitor_pricing output should not contain user_id"
        )
        for token in session_state.platform_tokens.values():
            assert token not in result, (
                "analyze_competitor_pricing output should not contain platform tokens"
            )

    @settings(max_examples=100)
    @given(
        industry=industry_strategy,
        session_state=session_state_strategy,
    )
    def test_get_market_trends_output_excludes_user_identifiers(
        self, industry: str, session_state: SessionState
    ):
        """get_market_trends output should not contain user-specific identifiers."""
        result = _get_market_trends_impl(industry)
        
        # Skip error responses
        if result.startswith("Error:"):
            return
        
        # Output should not contain user's ID or platform tokens
        assert session_state.user_id not in result, (
            "get_market_trends output should not contain user_id"
        )
        for token in session_state.platform_tokens.values():
            assert token not in result, (
                "get_market_trends output should not contain platform tokens"
            )

    def test_competitor_tools_only_accept_string_inputs(self):
        """All competitor tools should only accept simple string inputs, not complex user data types."""
        tools = [
            ("search_competitor", _search_competitor_impl),
            ("analyze_competitor_pricing", _analyze_competitor_pricing_impl),
            ("get_market_trends", _get_market_trends_impl),
        ]
        
        # Types that would indicate user store data
        forbidden_types = {SessionState, UserContext, dict, list}
        
        for tool_name, tool_func in tools:
            hints = get_type_hints(tool_func)
            sig = inspect.signature(tool_func)
            
            for param_name, param in sig.parameters.items():
                # Check type hints if available
                if param_name in hints:
                    param_type = hints[param_name]
                    assert param_type not in forbidden_types, (
                        f"{tool_name} parameter '{param_name}' should not accept "
                        f"complex type {param_type} that could contain user data"
                    )
                
                # Check annotation if available
                if param.annotation != inspect.Parameter.empty:
                    assert param.annotation not in forbidden_types, (
                        f"{tool_name} parameter '{param_name}' should not accept "
                        f"complex type {param.annotation} that could contain user data"
                    )

