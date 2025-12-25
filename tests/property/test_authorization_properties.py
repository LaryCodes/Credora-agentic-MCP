"""Property-based tests for authorization boundary enforcement.

**Feature: credora-cfo-agent**
"""

import pytest
from hypothesis import given, strategies as st, settings

from credora.tools.data_fetcher import (
    _fetch_sales_data_impl,
    _fetch_orders_impl,
    _fetch_products_impl,
    _fetch_customers_impl,
    set_state_manager as set_data_fetcher_state_manager,
    VALID_PLATFORMS,
    VALID_DATE_RANGES,
    VALID_ORDER_STATUSES,
    VALID_CUSTOMER_SEGMENTS,
)
from credora.tools.onboarding import (
    _initiate_oauth_impl,
    set_state_manager as set_onboarding_state_manager,
)
from credora.state import StateManager


def set_state_manager(manager: StateManager) -> None:
    """Set state manager for both data_fetcher and onboarding modules."""
    set_data_fetcher_state_manager(manager)
    set_onboarding_state_manager(manager)


# Strategies for generating test data
user_id_strategy = st.text(min_size=1, max_size=50).filter(lambda x: x.strip())
platform_strategy = st.sampled_from(VALID_PLATFORMS)
# For authorization tests, use only non-MCP platforms to avoid MCP connection issues
# MCP platforms (shopify, meta, google) require ConnectionManager setup
non_mcp_platform_strategy = st.sampled_from(["woocommerce"])
date_range_strategy = st.sampled_from(VALID_DATE_RANGES)
order_status_strategy = st.sampled_from(VALID_ORDER_STATUSES)
customer_segment_strategy = st.sampled_from(VALID_CUSTOMER_SEGMENTS)
limit_strategy = st.integers(min_value=1, max_value=100)


class TestAuthorizationBoundaryEnforcement:
    """
    **Feature: credora-cfo-agent, Property 1: Authorization Boundary Enforcement**
    **Validates: Requirements 1.4, 1.6**
    
    For any user session and any data access request, if the user has not
    authorized access to a specific platform, the system shall block the
    request and return an authorization prompt instead of data.
    """

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
        date_range=date_range_strategy,
    )
    def test_fetch_sales_data_requires_authorization(
        self, user_id: str, platform: str, date_range: str
    ):
        """fetch_sales_data should block requests for unauthorized platforms."""
        # Set up fresh state manager with NO connected platforms
        manager = StateManager()
        set_state_manager(manager)
        
        result = _fetch_sales_data_impl(user_id, platform, date_range)
        
        # Should return an error, not data
        assert "Error" in result
        # Should indicate the platform is not connected
        assert "not connected" in result.lower() or "not authorized" in result.lower() or "no authorization" in result.lower()
        # Should NOT contain actual sales data
        assert "Total Revenue" not in result
        assert "Total Orders" not in result

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
        date_range=date_range_strategy,
        status=order_status_strategy,
    )
    def test_fetch_orders_requires_authorization(
        self, user_id: str, platform: str, date_range: str, status: str
    ):
        """fetch_orders should block requests for unauthorized platforms."""
        manager = StateManager()
        set_state_manager(manager)
        
        result = _fetch_orders_impl(user_id, platform, date_range, status)
        
        # Should return an error, not data
        assert "Error" in result
        # Should indicate the platform is not connected
        assert "not connected" in result.lower() or "not authorized" in result.lower() or "no authorization" in result.lower()
        # Should NOT contain actual order data
        assert "Fulfillment Rate" not in result

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
        limit=limit_strategy,
    )
    def test_fetch_products_requires_authorization(
        self, user_id: str, platform: str, limit: int
    ):
        """fetch_products should block requests for unauthorized platforms."""
        manager = StateManager()
        set_state_manager(manager)
        
        result = _fetch_products_impl(user_id, platform, limit)
        
        # Should return an error, not data
        assert "Error" in result
        # Should indicate the platform is not connected
        assert "not connected" in result.lower() or "not authorized" in result.lower() or "no authorization" in result.lower()
        # Should NOT contain actual product data
        assert "Product Catalog" not in result

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
        segment=customer_segment_strategy,
    )
    def test_fetch_customers_requires_authorization(
        self, user_id: str, platform: str, segment: str
    ):
        """fetch_customers should block requests for unauthorized platforms."""
        manager = StateManager()
        set_state_manager(manager)
        
        result = _fetch_customers_impl(user_id, platform, segment)
        
        # Should return an error, not data
        assert "Error" in result
        # Should indicate the platform is not connected
        assert "not connected" in result.lower() or "not authorized" in result.lower() or "no authorization" in result.lower()
        # Should NOT contain actual customer data
        assert "Customer Data" not in result

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        authorized_platform=platform_strategy,
        requested_platform=platform_strategy,
        date_range=date_range_strategy,
    )
    def test_cannot_access_different_platform_than_authorized(
        self, user_id: str, authorized_platform: str, requested_platform: str, date_range: str
    ):
        """User should only access platforms they have explicitly connected."""
        # Skip if same platform (that case is tested separately)
        if authorized_platform == requested_platform:
            return
        
        manager = StateManager()
        set_state_manager(manager)
        
        # Authorize one platform via OAuth
        _initiate_oauth_impl(user_id, authorized_platform)
        
        # Try to access a different platform
        result = _fetch_sales_data_impl(user_id, requested_platform, date_range)
        
        # Should return an error for the unauthorized platform
        assert "Error" in result
        assert "not connected" in result.lower() or "not authorized" in result.lower() or "no authorization" in result.lower()

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=non_mcp_platform_strategy,
        date_range=date_range_strategy,
    )
    def test_authorized_platform_allows_access(
        self, user_id: str, platform: str, date_range: str
    ):
        """User should be able to access platforms they have authorized.
        
        Note: This test uses non-MCP platforms (woocommerce) because MCP platforms
        require ConnectionManager setup which is separate from StateManager.
        """
        manager = StateManager()
        set_state_manager(manager)
        
        # Authorize the platform via OAuth
        _initiate_oauth_impl(user_id, platform)
        
        # Now fetch should succeed
        result = _fetch_sales_data_impl(user_id, platform, date_range)
        
        # Should NOT return an error
        assert "Error" not in result
        # Should contain actual sales data
        assert "Total Revenue" in result or "Sales Data" in result

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
    )
    def test_connected_without_token_blocks_access(
        self, user_id: str, platform: str
    ):
        """Platform connected but without token should block access."""
        manager = StateManager()
        set_state_manager(manager)
        
        # Manually add platform to connected list WITHOUT a token
        # This simulates a corrupted or incomplete state
        session = manager.get_session_state(user_id)
        manager.update_session_state(user_id, {
            "connected_platforms": [platform],
            "platform_tokens": {},  # No token!
        })
        
        result = _fetch_sales_data_impl(user_id, platform, "30d")
        
        # Should return an error about missing token
        assert "Error" in result
        assert "token" in result.lower() or "authorization" in result.lower()



class TestReadOnlyOperationGuarantee:
    """
    **Feature: credora-cfo-agent, Property 2: Read-Only Operation Guarantee**
    **Validates: Requirements 1.3, 1.5**
    
    For any tool invocation by any agent, the tool shall not perform write
    operations on connected e-commerce platforms. All tools shall be
    verifiably read-only.
    
    This property is validated by ensuring that:
    1. All data fetcher tools do not modify session state (except for logging)
    2. All data fetcher tools return data without side effects on the platform
    3. The state before and after tool invocation remains unchanged
    """

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
        date_range=date_range_strategy,
    )
    def test_fetch_sales_data_does_not_modify_state(
        self, user_id: str, platform: str, date_range: str
    ):
        """fetch_sales_data should not modify session state."""
        manager = StateManager()
        set_state_manager(manager)
        
        # Set up authorized platform
        _initiate_oauth_impl(user_id, platform)
        
        # Capture state before
        state_before = manager.get_session_state(user_id)
        connected_before = state_before.connected_platforms.copy()
        tokens_before = state_before.platform_tokens.copy()
        goals_before = state_before.business_goals.copy()
        
        # Execute the read operation
        _fetch_sales_data_impl(user_id, platform, date_range)
        
        # Capture state after
        state_after = manager.get_session_state(user_id)
        
        # Verify state is unchanged (except last_interaction timestamp)
        assert state_after.connected_platforms == connected_before
        assert state_after.platform_tokens == tokens_before
        assert state_after.business_goals == goals_before
        assert state_after.onboarding_complete == state_before.onboarding_complete

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
        date_range=date_range_strategy,
        status=order_status_strategy,
    )
    def test_fetch_orders_does_not_modify_state(
        self, user_id: str, platform: str, date_range: str, status: str
    ):
        """fetch_orders should not modify session state."""
        manager = StateManager()
        set_state_manager(manager)
        
        # Set up authorized platform
        _initiate_oauth_impl(user_id, platform)
        
        # Capture state before
        state_before = manager.get_session_state(user_id)
        connected_before = state_before.connected_platforms.copy()
        tokens_before = state_before.platform_tokens.copy()
        
        # Execute the read operation
        _fetch_orders_impl(user_id, platform, date_range, status)
        
        # Capture state after
        state_after = manager.get_session_state(user_id)
        
        # Verify state is unchanged
        assert state_after.connected_platforms == connected_before
        assert state_after.platform_tokens == tokens_before

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
        limit=limit_strategy,
    )
    def test_fetch_products_does_not_modify_state(
        self, user_id: str, platform: str, limit: int
    ):
        """fetch_products should not modify session state."""
        manager = StateManager()
        set_state_manager(manager)
        
        # Set up authorized platform
        _initiate_oauth_impl(user_id, platform)
        
        # Capture state before
        state_before = manager.get_session_state(user_id)
        connected_before = state_before.connected_platforms.copy()
        tokens_before = state_before.platform_tokens.copy()
        
        # Execute the read operation
        _fetch_products_impl(user_id, platform, limit)
        
        # Capture state after
        state_after = manager.get_session_state(user_id)
        
        # Verify state is unchanged
        assert state_after.connected_platforms == connected_before
        assert state_after.platform_tokens == tokens_before

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
        segment=customer_segment_strategy,
    )
    def test_fetch_customers_does_not_modify_state(
        self, user_id: str, platform: str, segment: str
    ):
        """fetch_customers should not modify session state."""
        manager = StateManager()
        set_state_manager(manager)
        
        # Set up authorized platform
        _initiate_oauth_impl(user_id, platform)
        
        # Capture state before
        state_before = manager.get_session_state(user_id)
        connected_before = state_before.connected_platforms.copy()
        tokens_before = state_before.platform_tokens.copy()
        
        # Execute the read operation
        _fetch_customers_impl(user_id, platform, segment)
        
        # Capture state after
        state_after = manager.get_session_state(user_id)
        
        # Verify state is unchanged
        assert state_after.connected_platforms == connected_before
        assert state_after.platform_tokens == tokens_before

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
    )
    def test_multiple_reads_do_not_accumulate_changes(
        self, user_id: str, platform: str
    ):
        """Multiple read operations should not accumulate state changes."""
        manager = StateManager()
        set_state_manager(manager)
        
        # Set up authorized platform
        _initiate_oauth_impl(user_id, platform)
        
        # Capture initial state
        state_initial = manager.get_session_state(user_id)
        connected_initial = state_initial.connected_platforms.copy()
        tokens_initial = state_initial.platform_tokens.copy()
        
        # Execute multiple read operations
        _fetch_sales_data_impl(user_id, platform, "30d")
        _fetch_orders_impl(user_id, platform, "30d", "all")
        _fetch_products_impl(user_id, platform, 10)
        _fetch_customers_impl(user_id, platform, "all")
        
        # Capture final state
        state_final = manager.get_session_state(user_id)
        
        # Verify state is unchanged after all operations
        assert state_final.connected_platforms == connected_initial
        assert state_final.platform_tokens == tokens_initial

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
        date_range=date_range_strategy,
    )
    def test_read_operations_are_idempotent(
        self, user_id: str, platform: str, date_range: str
    ):
        """Calling the same read operation multiple times should return same result."""
        manager = StateManager()
        set_state_manager(manager)
        
        # Set up authorized platform
        _initiate_oauth_impl(user_id, platform)
        
        # Execute the same operation multiple times
        result1 = _fetch_sales_data_impl(user_id, platform, date_range)
        result2 = _fetch_sales_data_impl(user_id, platform, date_range)
        result3 = _fetch_sales_data_impl(user_id, platform, date_range)
        
        # Results should be identical (deterministic)
        assert result1 == result2
        assert result2 == result3
