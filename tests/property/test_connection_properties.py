"""Property-based tests for Connection Management.

**Feature: platform-mcp-servers**
"""

from datetime import datetime, timedelta

import pytest
from hypothesis import given, strategies as st, settings

from credora.mcp_servers.connection_manager import ConnectionManager
from credora.mcp_servers.models.oauth import TokenData
from credora.mcp_servers.token_store import TokenStore
from credora.security import TokenEncryption


# Strategy for generating valid user IDs (non-empty, no null chars)
user_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), blacklist_characters="\x00"),
    min_size=1,
    max_size=50
).filter(lambda x: x.strip() != "")

# Strategy for generating valid platform names
platform_strategy = st.sampled_from(["meta", "google", "shopify"])

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

# Strategy for generating distinct user ID pairs
distinct_user_ids_strategy = st.tuples(
    user_id_strategy,
    user_id_strategy
).filter(lambda x: x[0].strip() != x[1].strip())


@st.composite
def valid_token_data_strategy(draw):
    """Generate TokenData instances that are not expired."""
    access_token = draw(token_strategy)
    refresh_token = draw(token_strategy)
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


class TestDisconnectCleanup:
    """
    **Feature: platform-mcp-servers, Property 13: Disconnect Cleanup**
    **Validates: Requirements 7.4, 8.3**
    
    For any platform disconnect operation, all stored tokens for that platform
    and user shall be deleted, and subsequent token retrieval shall return None.
    """

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
        token_data=valid_token_data_strategy(),
    )
    @pytest.mark.asyncio
    async def test_disconnect_deletes_token(
        self, user_id: str, platform: str, token_data: TokenData
    ):
        """Disconnecting a platform should delete the stored token."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        token_store = TokenStore(encryption=encryption)
        manager = ConnectionManager(token_store=token_store)
        
        # Store a token
        token_store.store_token(user_id, platform, token_data)
        
        # Verify token exists
        assert token_store.get_token(user_id, platform) is not None
        
        # Disconnect the platform
        result = await manager.disconnect_platform(platform, user_id)
        
        # Verify disconnect was successful
        assert result is True
        
        # Verify token is deleted
        assert token_store.get_token(user_id, platform) is None

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
        token_data=valid_token_data_strategy(),
    )
    @pytest.mark.asyncio
    async def test_disconnect_removes_from_connections_list(
        self, user_id: str, platform: str, token_data: TokenData
    ):
        """Disconnecting a platform should remove it from connections list."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        token_store = TokenStore(encryption=encryption)
        manager = ConnectionManager(token_store=token_store)
        
        # Store a token
        token_store.store_token(user_id, platform, token_data)
        manager._store_connection_metadata(user_id, platform, token_data.platform_user_id)
        
        # Verify platform is in connections
        connections = await manager.list_connections(user_id)
        platforms = [c.platform for c in connections]
        assert platform in platforms
        
        # Disconnect the platform
        await manager.disconnect_platform(platform, user_id)
        
        # Verify platform is no longer in connections
        connections = await manager.list_connections(user_id)
        platforms = [c.platform for c in connections]
        assert platform not in platforms

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
    )
    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_returns_false(
        self, user_id: str, platform: str
    ):
        """Disconnecting a platform that doesn't exist should return False."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        token_store = TokenStore(encryption=encryption)
        manager = ConnectionManager(token_store=token_store)
        
        # Don't store any token
        
        # Disconnect should return False
        result = await manager.disconnect_platform(platform, user_id)
        
        assert result is False

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        token_data=valid_token_data_strategy(),
    )
    @pytest.mark.asyncio
    async def test_disconnect_one_platform_preserves_others(
        self, user_id: str, token_data: TokenData
    ):
        """Disconnecting one platform should not affect other platforms."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        token_store = TokenStore(encryption=encryption)
        manager = ConnectionManager(token_store=token_store)
        
        # Store tokens for all platforms
        platforms = ["meta", "google", "shopify"]
        for platform in platforms:
            token_store.store_token(user_id, platform, token_data)
            manager._store_connection_metadata(user_id, platform, token_data.platform_user_id)
        
        # Disconnect one platform
        await manager.disconnect_platform("meta", user_id)
        
        # Verify other platforms still have tokens
        assert token_store.get_token(user_id, "google") is not None
        assert token_store.get_token(user_id, "shopify") is not None
        
        # Verify disconnected platform has no token
        assert token_store.get_token(user_id, "meta") is None


class TestUserIsolation:
    """
    **Feature: platform-mcp-servers, Property 14: User Isolation**
    **Validates: Requirements 7.5**
    
    For any two distinct users, User A's platform connections and tokens
    shall not be accessible when querying with User B's user_id.
    """

    @settings(max_examples=100)
    @given(
        user_ids=distinct_user_ids_strategy,
        platform=platform_strategy,
        token_data=valid_token_data_strategy(),
    )
    @pytest.mark.asyncio
    async def test_user_a_token_not_accessible_by_user_b(
        self, user_ids, platform: str, token_data: TokenData
    ):
        """User A's tokens should not be accessible by User B."""
        user_a, user_b = user_ids
        
        encryption = TokenEncryption(TokenEncryption.generate_key())
        token_store = TokenStore(encryption=encryption)
        manager = ConnectionManager(token_store=token_store)
        
        # Store token for User A
        token_store.store_token(user_a, platform, token_data)
        manager._store_connection_metadata(user_a, platform, token_data.platform_user_id)
        
        # User B should not be able to access User A's token
        token_b = token_store.get_token(user_b, platform)
        assert token_b is None

    @settings(max_examples=100)
    @given(
        user_ids=distinct_user_ids_strategy,
        platform=platform_strategy,
        token_data=valid_token_data_strategy(),
    )
    @pytest.mark.asyncio
    async def test_user_a_connections_not_visible_to_user_b(
        self, user_ids, platform: str, token_data: TokenData
    ):
        """User A's connections should not appear in User B's list."""
        user_a, user_b = user_ids
        
        encryption = TokenEncryption(TokenEncryption.generate_key())
        token_store = TokenStore(encryption=encryption)
        manager = ConnectionManager(token_store=token_store)
        
        # Store token for User A
        token_store.store_token(user_a, platform, token_data)
        manager._store_connection_metadata(user_a, platform, token_data.platform_user_id)
        
        # User B's connections should be empty
        connections_b = await manager.list_connections(user_b)
        assert len(connections_b) == 0

    @settings(max_examples=100)
    @given(
        user_ids=distinct_user_ids_strategy,
        platform=platform_strategy,
        token_data_a=valid_token_data_strategy(),
        token_data_b=valid_token_data_strategy(),
    )
    @pytest.mark.asyncio
    async def test_users_have_independent_connections(
        self, user_ids, platform: str, token_data_a: TokenData, token_data_b: TokenData
    ):
        """Each user should have independent connections."""
        user_a, user_b = user_ids
        
        encryption = TokenEncryption(TokenEncryption.generate_key())
        token_store = TokenStore(encryption=encryption)
        manager = ConnectionManager(token_store=token_store)
        
        # Store different tokens for each user
        token_store.store_token(user_a, platform, token_data_a)
        token_store.store_token(user_b, platform, token_data_b)
        manager._store_connection_metadata(user_a, platform, token_data_a.platform_user_id)
        manager._store_connection_metadata(user_b, platform, token_data_b.platform_user_id)
        
        # Each user should get their own token
        retrieved_a = token_store.get_token(user_a, platform)
        retrieved_b = token_store.get_token(user_b, platform)
        
        assert retrieved_a is not None
        assert retrieved_b is not None
        assert retrieved_a.access_token == token_data_a.access_token
        assert retrieved_b.access_token == token_data_b.access_token

    @settings(max_examples=100)
    @given(
        user_ids=distinct_user_ids_strategy,
        platform=platform_strategy,
        token_data=valid_token_data_strategy(),
    )
    @pytest.mark.asyncio
    async def test_disconnect_user_a_does_not_affect_user_b(
        self, user_ids, platform: str, token_data: TokenData
    ):
        """Disconnecting User A should not affect User B's connections."""
        user_a, user_b = user_ids
        
        encryption = TokenEncryption(TokenEncryption.generate_key())
        token_store = TokenStore(encryption=encryption)
        manager = ConnectionManager(token_store=token_store)
        
        # Store tokens for both users
        token_store.store_token(user_a, platform, token_data)
        token_store.store_token(user_b, platform, token_data)
        manager._store_connection_metadata(user_a, platform, token_data.platform_user_id)
        manager._store_connection_metadata(user_b, platform, token_data.platform_user_id)
        
        # Disconnect User A
        await manager.disconnect_platform(platform, user_a)
        
        # User A should have no token
        assert token_store.get_token(user_a, platform) is None
        
        # User B should still have their token
        assert token_store.get_token(user_b, platform) is not None

    @settings(max_examples=100)
    @given(
        user_ids=distinct_user_ids_strategy,
        platform=platform_strategy,
        token_data=valid_token_data_strategy(),
    )
    @pytest.mark.asyncio
    async def test_connection_health_isolated_per_user(
        self, user_ids, platform: str, token_data: TokenData
    ):
        """Connection health checks should be isolated per user."""
        user_a, user_b = user_ids
        
        encryption = TokenEncryption(TokenEncryption.generate_key())
        token_store = TokenStore(encryption=encryption)
        manager = ConnectionManager(token_store=token_store)
        
        # Store token only for User A
        token_store.store_token(user_a, platform, token_data)
        manager._store_connection_metadata(user_a, platform, token_data.platform_user_id)
        
        # User A should have healthy connection
        health_a = await manager.check_connection_health(platform, user_a)
        assert health_a.is_healthy is True
        assert health_a.token_valid is True
        
        # User B should have no connection
        health_b = await manager.check_connection_health(platform, user_b)
        assert health_b.is_healthy is False
        assert health_b.token_valid is False


# Strategy for generating a subset of platforms
platforms_subset_strategy = st.lists(
    platform_strategy,
    min_size=0,
    max_size=3,
    unique=True
)


class TestConnectionListCompleteness:
    """
    **Feature: platform-mcp-servers, Property 15: Connection List Completeness**
    **Validates: Requirements 8.1, 8.5**
    
    For any user with connected platforms, listing connections shall return
    all connected platforms with status and last_sync timestamp.
    """

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platforms=platforms_subset_strategy,
        token_data=valid_token_data_strategy(),
    )
    @pytest.mark.asyncio
    async def test_list_returns_all_connected_platforms(
        self, user_id: str, platforms: list, token_data: TokenData
    ):
        """Listing connections should return all connected platforms."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        token_store = TokenStore(encryption=encryption)
        manager = ConnectionManager(token_store=token_store)
        
        # Store tokens for each platform
        for platform in platforms:
            token_store.store_token(user_id, platform, token_data)
            manager._store_connection_metadata(user_id, platform, token_data.platform_user_id)
        
        # List connections
        connections = await manager.list_connections(user_id)
        
        # Verify all platforms are returned
        returned_platforms = {c.platform for c in connections}
        expected_platforms = set(platforms)
        
        assert returned_platforms == expected_platforms

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
        token_data=valid_token_data_strategy(),
    )
    @pytest.mark.asyncio
    async def test_connection_has_status_field(
        self, user_id: str, platform: str, token_data: TokenData
    ):
        """Each connection should have a status field."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        token_store = TokenStore(encryption=encryption)
        manager = ConnectionManager(token_store=token_store)
        
        # Store a token
        token_store.store_token(user_id, platform, token_data)
        manager._store_connection_metadata(user_id, platform, token_data.platform_user_id)
        
        # List connections
        connections = await manager.list_connections(user_id)
        
        # Verify status field exists and is valid
        assert len(connections) == 1
        connection = connections[0]
        assert hasattr(connection, 'status')
        assert connection.status in {"active", "expired", "error"}

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
        token_data=valid_token_data_strategy(),
    )
    @pytest.mark.asyncio
    async def test_connection_has_last_sync_timestamp(
        self, user_id: str, platform: str, token_data: TokenData
    ):
        """Each connection should have a last_sync timestamp."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        token_store = TokenStore(encryption=encryption)
        manager = ConnectionManager(token_store=token_store)
        
        # Store a token
        token_store.store_token(user_id, platform, token_data)
        manager._store_connection_metadata(user_id, platform, token_data.platform_user_id)
        
        # List connections
        connections = await manager.list_connections(user_id)
        
        # Verify last_sync field exists and is a datetime
        assert len(connections) == 1
        connection = connections[0]
        assert hasattr(connection, 'last_sync')
        assert isinstance(connection.last_sync, datetime)

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
    )
    @pytest.mark.asyncio
    async def test_empty_list_for_no_connections(
        self, user_id: str
    ):
        """User with no connections should get empty list."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        token_store = TokenStore(encryption=encryption)
        manager = ConnectionManager(token_store=token_store)
        
        # Don't store any tokens
        
        # List connections
        connections = await manager.list_connections(user_id)
        
        # Should be empty
        assert len(connections) == 0

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
        token_data=valid_token_data_strategy(),
    )
    @pytest.mark.asyncio
    async def test_connection_count_matches_stored_platforms(
        self, user_id: str, platform: str, token_data: TokenData
    ):
        """Connection count should match number of stored platforms."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        token_store = TokenStore(encryption=encryption)
        manager = ConnectionManager(token_store=token_store)
        
        # Store tokens for all platforms
        all_platforms = ["meta", "google", "shopify"]
        for p in all_platforms:
            token_store.store_token(user_id, p, token_data)
            manager._store_connection_metadata(user_id, p, token_data.platform_user_id)
        
        # List connections
        connections = await manager.list_connections(user_id)
        
        # Count should match
        assert len(connections) == len(all_platforms)


class TestConnectionHealthCheck:
    """
    **Feature: platform-mcp-servers, Property 16: Connection Health Check**
    **Validates: Requirements 8.4**
    
    For any connected platform, checking connection health shall return
    a ConnectionHealth object with is_healthy, token_valid, and last_checked fields.
    """

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
        token_data=valid_token_data_strategy(),
    )
    @pytest.mark.asyncio
    async def test_health_check_returns_is_healthy_field(
        self, user_id: str, platform: str, token_data: TokenData
    ):
        """Health check should return is_healthy field."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        token_store = TokenStore(encryption=encryption)
        manager = ConnectionManager(token_store=token_store)
        
        # Store a token
        token_store.store_token(user_id, platform, token_data)
        manager._store_connection_metadata(user_id, platform, token_data.platform_user_id)
        
        # Check health
        health = await manager.check_connection_health(platform, user_id)
        
        # Verify is_healthy field exists and is boolean
        assert hasattr(health, 'is_healthy')
        assert isinstance(health.is_healthy, bool)

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
        token_data=valid_token_data_strategy(),
    )
    @pytest.mark.asyncio
    async def test_health_check_returns_token_valid_field(
        self, user_id: str, platform: str, token_data: TokenData
    ):
        """Health check should return token_valid field."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        token_store = TokenStore(encryption=encryption)
        manager = ConnectionManager(token_store=token_store)
        
        # Store a token
        token_store.store_token(user_id, platform, token_data)
        manager._store_connection_metadata(user_id, platform, token_data.platform_user_id)
        
        # Check health
        health = await manager.check_connection_health(platform, user_id)
        
        # Verify token_valid field exists and is boolean
        assert hasattr(health, 'token_valid')
        assert isinstance(health.token_valid, bool)

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
        token_data=valid_token_data_strategy(),
    )
    @pytest.mark.asyncio
    async def test_health_check_returns_last_checked_field(
        self, user_id: str, platform: str, token_data: TokenData
    ):
        """Health check should return last_checked field."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        token_store = TokenStore(encryption=encryption)
        manager = ConnectionManager(token_store=token_store)
        
        # Store a token
        token_store.store_token(user_id, platform, token_data)
        manager._store_connection_metadata(user_id, platform, token_data.platform_user_id)
        
        # Check health
        health = await manager.check_connection_health(platform, user_id)
        
        # Verify last_checked field exists and is datetime
        assert hasattr(health, 'last_checked')
        assert isinstance(health.last_checked, datetime)

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
        token_data=valid_token_data_strategy(),
    )
    @pytest.mark.asyncio
    async def test_valid_token_shows_healthy(
        self, user_id: str, platform: str, token_data: TokenData
    ):
        """Valid (non-expired) token should show healthy connection."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        token_store = TokenStore(encryption=encryption)
        manager = ConnectionManager(token_store=token_store)
        
        # Store a valid token (not expired)
        token_store.store_token(user_id, platform, token_data)
        manager._store_connection_metadata(user_id, platform, token_data.platform_user_id)
        
        # Check health
        health = await manager.check_connection_health(platform, user_id)
        
        # Should be healthy
        assert health.is_healthy is True
        assert health.token_valid is True
        assert health.error_message is None

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
    )
    @pytest.mark.asyncio
    async def test_no_connection_shows_unhealthy(
        self, user_id: str, platform: str
    ):
        """No connection should show unhealthy status."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        token_store = TokenStore(encryption=encryption)
        manager = ConnectionManager(token_store=token_store)
        
        # Don't store any token
        
        # Check health
        health = await manager.check_connection_health(platform, user_id)
        
        # Should be unhealthy
        assert health.is_healthy is False
        assert health.token_valid is False
        assert health.error_message is not None

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
        token_data=valid_token_data_strategy(),
    )
    @pytest.mark.asyncio
    async def test_expired_token_shows_unhealthy(
        self, user_id: str, platform: str, token_data: TokenData
    ):
        """Expired token should show unhealthy connection."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        token_store = TokenStore(encryption=encryption)
        manager = ConnectionManager(token_store=token_store)
        
        # Create an expired token
        expired_token = TokenData(
            access_token=token_data.access_token,
            refresh_token=token_data.refresh_token,
            expires_at=datetime.now() - timedelta(hours=1),  # Expired
            scopes=token_data.scopes,
            platform_user_id=token_data.platform_user_id,
        )
        
        # Store the expired token
        token_store.store_token(user_id, platform, expired_token)
        manager._store_connection_metadata(user_id, platform, expired_token.platform_user_id)
        
        # Check health
        health = await manager.check_connection_health(platform, user_id)
        
        # Should be unhealthy due to expired token
        assert health.is_healthy is False
        assert health.token_valid is False
        assert health.error_message is not None
