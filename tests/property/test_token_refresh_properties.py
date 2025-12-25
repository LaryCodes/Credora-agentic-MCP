"""Property-based tests for Token Refresh.

**Feature: platform-mcp-servers**
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from hypothesis import given, strategies as st, settings

from credora.mcp_servers.connection_manager import ConnectionManager
from credora.mcp_servers.errors import MCPError, MCPErrorType
from credora.mcp_servers.models.oauth import TokenData
from credora.mcp_servers.token_store import TokenStore
from credora.security import TokenEncryption


# Strategy for generating valid user IDs (non-empty, no null chars)
user_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), blacklist_characters="\x00"),
    min_size=1,
    max_size=50
).filter(lambda x: x.strip() != "")

# Strategy for non-Shopify platforms (support refresh)
refreshable_platform_strategy = st.sampled_from(["meta", "google"])

# Strategy for generating valid tokens (non-empty strings)
token_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), blacklist_characters="\x00"),
    min_size=1,
    max_size=100
).filter(lambda x: len(x) > 0)

# Strategy for generating valid platform user IDs
platform_user_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), blacklist_characters="\x00"),
    min_size=1,
    max_size=50
).filter(lambda x: x.strip() != "")


@st.composite
def expired_token_data_strategy(draw):
    """Generate TokenData instances that are expired."""
    access_token = draw(token_strategy)
    refresh_token = draw(token_strategy)
    # Generate expiry time in the past
    hours_ago = draw(st.integers(min_value=1, max_value=720))
    expires_at = datetime.now() - timedelta(hours=hours_ago)
    platform_user_id = draw(platform_user_id_strategy)
    
    return TokenData(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
        scopes=["test_scope"],
        platform_user_id=platform_user_id,
    )


@st.composite
def valid_token_data_strategy(draw):
    """Generate TokenData instances that are not expired."""
    access_token = draw(token_strategy)
    refresh_token = draw(token_strategy)
    # Generate expiry time in the future
    hours_offset = draw(st.integers(min_value=1, max_value=720))
    expires_at = datetime.now() + timedelta(hours=hours_offset)
    platform_user_id = draw(platform_user_id_strategy)
    
    return TokenData(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
        scopes=["test_scope"],
        platform_user_id=platform_user_id,
    )


class TestTokenRefreshOnExpiry:
    """
    **Feature: platform-mcp-servers, Property 5: Token Refresh on Expiry**
    **Validates: Requirements 2.4**
    
    For any expired access token with a valid refresh token, the system shall
    automatically obtain a new access token before making API requests.
    """

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=refreshable_platform_strategy,
        expired_token=expired_token_data_strategy(),
        new_access_token=token_strategy,
    )
    @pytest.mark.asyncio
    async def test_expired_token_triggers_refresh(
        self, user_id: str, platform: str, expired_token: TokenData, new_access_token: str
    ):
        """When token is expired, get_access_token should attempt refresh."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        token_store = TokenStore(encryption=encryption)
        manager = ConnectionManager(token_store=token_store)
        
        # Store the expired token
        token_store.store_token(user_id, platform, expired_token)
        
        # Create a mock for the refresh function that returns a new token
        new_token_data = TokenData(
            access_token=new_access_token,
            refresh_token=expired_token.refresh_token,
            expires_at=datetime.now() + timedelta(hours=1),
            scopes=expired_token.scopes,
            platform_user_id=expired_token.platform_user_id,
        )
        
        with patch(
            "credora.mcp_servers.connection_manager.refresh_access_token",
            new_callable=AsyncMock,
            return_value=new_token_data,
        ) as mock_refresh:
            # Get access token - should trigger refresh
            result = await manager.get_access_token(platform, user_id)
            
            # Verify refresh was called
            mock_refresh.assert_called_once()
            
            # Verify we got the new token
            assert result == new_access_token

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=refreshable_platform_strategy,
        valid_token=valid_token_data_strategy(),
    )
    @pytest.mark.asyncio
    async def test_valid_token_does_not_trigger_refresh(
        self, user_id: str, platform: str, valid_token: TokenData
    ):
        """When token is valid, get_access_token should not attempt refresh."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        token_store = TokenStore(encryption=encryption)
        manager = ConnectionManager(token_store=token_store)
        
        # Store the valid token
        token_store.store_token(user_id, platform, valid_token)
        
        with patch(
            "credora.mcp_servers.connection_manager.refresh_access_token",
            new_callable=AsyncMock,
        ) as mock_refresh:
            # Get access token - should NOT trigger refresh
            result = await manager.get_access_token(platform, user_id)
            
            # Verify refresh was NOT called
            mock_refresh.assert_not_called()
            
            # Verify we got the original token
            assert result == valid_token.access_token

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=refreshable_platform_strategy,
        expired_token=expired_token_data_strategy(),
        new_access_token=token_strategy,
    )
    @pytest.mark.asyncio
    async def test_refresh_updates_stored_token(
        self, user_id: str, platform: str, expired_token: TokenData, new_access_token: str
    ):
        """After refresh, the new token should be stored."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        token_store = TokenStore(encryption=encryption)
        manager = ConnectionManager(token_store=token_store)
        
        # Store the expired token
        token_store.store_token(user_id, platform, expired_token)
        
        # Create a mock for the refresh function
        new_token_data = TokenData(
            access_token=new_access_token,
            refresh_token=expired_token.refresh_token,
            expires_at=datetime.now() + timedelta(hours=1),
            scopes=expired_token.scopes,
            platform_user_id=expired_token.platform_user_id,
        )
        
        with patch(
            "credora.mcp_servers.connection_manager.refresh_access_token",
            new_callable=AsyncMock,
            return_value=new_token_data,
        ):
            # Trigger refresh
            await manager.get_access_token(platform, user_id)
            
            # Verify the new token is stored
            stored_token = token_store.get_token(user_id, platform)
            assert stored_token is not None
            assert stored_token.access_token == new_access_token


class TestRefreshFailureNotification:
    """
    **Feature: platform-mcp-servers, Property 6: Refresh Failure Notification**
    **Validates: Requirements 2.5, 6.5**
    
    For any token refresh that fails, the system shall return an error response
    indicating re-authentication is required.
    """

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=refreshable_platform_strategy,
        expired_token=expired_token_data_strategy(),
    )
    @pytest.mark.asyncio
    async def test_refresh_failure_returns_auth_error(
        self, user_id: str, platform: str, expired_token: TokenData
    ):
        """When refresh fails, should return AUTH_EXPIRED error."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        token_store = TokenStore(encryption=encryption)
        manager = ConnectionManager(token_store=token_store)
        
        # Store the expired token
        token_store.store_token(user_id, platform, expired_token)
        
        # Mock refresh to fail with AUTH_EXPIRED
        with patch(
            "credora.mcp_servers.connection_manager.refresh_access_token",
            new_callable=AsyncMock,
            side_effect=MCPError(
                error_type=MCPErrorType.AUTH_EXPIRED,
                message="Refresh token is invalid",
                recoverable=False,
            ),
        ):
            # Attempt to get access token - should fail
            with pytest.raises(MCPError) as exc_info:
                await manager.get_access_token(platform, user_id)
            
            # Verify error type indicates re-authentication needed
            assert exc_info.value.error_type == MCPErrorType.AUTH_EXPIRED
            assert exc_info.value.recoverable is False
            assert "re-authenticate" in exc_info.value.message.lower()

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=refreshable_platform_strategy,
        expired_token=expired_token_data_strategy(),
    )
    @pytest.mark.asyncio
    async def test_refresh_failure_includes_platform_info(
        self, user_id: str, platform: str, expired_token: TokenData
    ):
        """Refresh failure error should include platform information."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        token_store = TokenStore(encryption=encryption)
        manager = ConnectionManager(token_store=token_store)
        
        # Store the expired token
        token_store.store_token(user_id, platform, expired_token)
        
        # Mock refresh to fail
        with patch(
            "credora.mcp_servers.connection_manager.refresh_access_token",
            new_callable=AsyncMock,
            side_effect=MCPError(
                error_type=MCPErrorType.AUTH_EXPIRED,
                message="Refresh token is invalid",
                recoverable=False,
            ),
        ):
            with pytest.raises(MCPError) as exc_info:
                await manager.get_access_token(platform, user_id)
            
            # Verify platform is mentioned in error
            error = exc_info.value
            assert platform in error.message or (
                error.details and platform in str(error.details)
            )

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=refreshable_platform_strategy,
    )
    @pytest.mark.asyncio
    async def test_no_token_returns_auth_required(
        self, user_id: str, platform: str
    ):
        """When no token exists, should return AUTH_REQUIRED error."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        token_store = TokenStore(encryption=encryption)
        manager = ConnectionManager(token_store=token_store)
        
        # Don't store any token
        
        # Attempt to get access token - should fail
        with pytest.raises(MCPError) as exc_info:
            await manager.get_access_token(platform, user_id)
        
        # Verify error type indicates authentication needed
        assert exc_info.value.error_type == MCPErrorType.AUTH_REQUIRED
        assert "authenticate" in exc_info.value.message.lower()
