"""Property-based tests for Token Store.

**Feature: platform-mcp-servers**
"""

from datetime import datetime, timedelta

import pytest
from hypothesis import given, strategies as st, settings

from credora.mcp_servers.token_store import TokenStore
from credora.mcp_servers.models.oauth import TokenData
from credora.security import TokenEncryption


# Strategy for generating valid user IDs (non-empty, non-whitespace strings)
user_id_strategy = st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != "")

# Strategy for generating valid platform names
platform_strategy = st.sampled_from(["meta", "google", "shopify"])

# Strategy for generating valid tokens (non-empty strings)
token_strategy = st.text(min_size=1, max_size=200).filter(lambda x: len(x) > 0)

# Strategy for generating valid scopes
scopes_strategy = st.lists(
    st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != ""),
    min_size=0,
    max_size=10,
)

# Strategy for generating valid platform user IDs
platform_user_id_strategy = st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != "")


# Strategy for generating valid TokenData
@st.composite
def token_data_strategy(draw):
    """Generate valid TokenData instances."""
    access_token = draw(token_strategy)
    refresh_token = draw(token_strategy)
    # Generate expiry time in the future
    hours_offset = draw(st.integers(min_value=1, max_value=720))
    expires_at = datetime.now() + timedelta(hours=hours_offset)
    scopes = draw(scopes_strategy)
    platform_user_id = draw(platform_user_id_strategy)
    
    return TokenData(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
        scopes=scopes,
        platform_user_id=platform_user_id,
    )


# Strategy for generating distinct user ID pairs
distinct_user_ids_strategy = st.tuples(
    user_id_strategy,
    user_id_strategy
).filter(lambda x: x[0].strip() != x[1].strip())


class TestTokenStorageRoundTrip:
    """
    **Feature: platform-mcp-servers, Property 4: Token Storage Round-Trip**
    **Validates: Requirements 2.2, 2.3, 7.1**
    
    For any valid token data, storing and then retrieving the token shall
    produce equivalent token data with the access_token decrypted correctly.
    """

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
        token_data=token_data_strategy(),
    )
    def test_store_then_get_returns_equivalent_token(
        self, user_id: str, platform: str, token_data: TokenData
    ):
        """Storing then retrieving a token should return equivalent data."""
        # Use a fresh encryption key for each test
        encryption = TokenEncryption(TokenEncryption.generate_key())
        store = TokenStore(encryption=encryption)
        
        # Store the token
        store.store_token(user_id, platform, token_data)
        
        # Retrieve the token
        retrieved = store.get_token(user_id, platform)
        
        # Verify retrieved token is not None
        assert retrieved is not None
        
        # Verify all fields match
        assert retrieved.access_token == token_data.access_token
        assert retrieved.refresh_token == token_data.refresh_token
        assert retrieved.expires_at == token_data.expires_at
        assert retrieved.scopes == token_data.scopes
        assert retrieved.platform_user_id == token_data.platform_user_id

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
        token_data=token_data_strategy(),
    )
    def test_tokens_are_encrypted_in_storage(
        self, user_id: str, platform: str, token_data: TokenData
    ):
        """Tokens should be stored in encrypted form, not plaintext."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        store = TokenStore(encryption=encryption)
        
        # Store the token
        store.store_token(user_id, platform, token_data)
        
        # Access internal storage directly to verify encryption
        user_id_clean = user_id.strip()
        platform_lower = platform.lower().strip()
        
        stored_data = store._tokens[user_id_clean][platform_lower]
        
        # Stored access_token should not equal plaintext
        assert stored_data["access_token"] != token_data.access_token
        
        # Stored refresh_token should not equal plaintext
        assert stored_data["refresh_token"] != token_data.refresh_token
        
        # Stored tokens should be detected as encrypted
        assert encryption.is_encrypted(stored_data["access_token"])
        assert encryption.is_encrypted(stored_data["refresh_token"])

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
    )
    def test_get_nonexistent_token_returns_none(
        self, user_id: str, platform: str
    ):
        """Getting a token that doesn't exist should return None."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        store = TokenStore(encryption=encryption)
        
        # Try to get a token that was never stored
        retrieved = store.get_token(user_id, platform)
        
        assert retrieved is None

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
        token_data=token_data_strategy(),
    )
    def test_delete_removes_token(
        self, user_id: str, platform: str, token_data: TokenData
    ):
        """Deleting a token should remove it from storage."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        store = TokenStore(encryption=encryption)
        
        # Store the token
        store.store_token(user_id, platform, token_data)
        
        # Verify it exists
        assert store.get_token(user_id, platform) is not None
        
        # Delete the token
        result = store.delete_token(user_id, platform)
        
        # Verify deletion was successful
        assert result is True
        
        # Verify token no longer exists
        assert store.get_token(user_id, platform) is None

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
    )
    def test_delete_nonexistent_returns_false(
        self, user_id: str, platform: str
    ):
        """Deleting a token that doesn't exist should return False."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        store = TokenStore(encryption=encryption)
        
        # Try to delete a token that was never stored
        result = store.delete_token(user_id, platform)
        
        assert result is False

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        token_data=token_data_strategy(),
    )
    def test_list_platforms_returns_stored_platforms(
        self, user_id: str, token_data: TokenData
    ):
        """list_platforms should return all platforms with stored tokens."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        store = TokenStore(encryption=encryption)
        
        # Store tokens for multiple platforms
        platforms = ["meta", "google", "shopify"]
        for platform in platforms:
            store.store_token(user_id, platform, token_data)
        
        # List platforms
        listed = store.list_platforms(user_id)
        
        # Verify all platforms are listed
        assert set(listed) == set(platforms)

    @settings(max_examples=100)
    @given(user_id=user_id_strategy)
    def test_list_platforms_empty_for_new_user(self, user_id: str):
        """list_platforms should return empty list for user with no tokens."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        store = TokenStore(encryption=encryption)
        
        # List platforms for user with no tokens
        listed = store.list_platforms(user_id)
        
        assert listed == []

    @settings(max_examples=100)
    @given(
        user_ids=distinct_user_ids_strategy,
        platform=platform_strategy,
        token_data=token_data_strategy(),
    )
    def test_user_isolation_tokens_not_shared(
        self, user_ids, platform: str, token_data: TokenData
    ):
        """Tokens stored for one user should not be accessible by another user."""
        user_a, user_b = user_ids
        
        encryption = TokenEncryption(TokenEncryption.generate_key())
        store = TokenStore(encryption=encryption)
        
        # Store token for user A
        store.store_token(user_a, platform, token_data)
        
        # User B should not be able to access user A's token
        retrieved_by_b = store.get_token(user_b, platform)
        
        assert retrieved_by_b is None

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
        token_data1=token_data_strategy(),
        token_data2=token_data_strategy(),
    )
    def test_overwrite_token_replaces_previous(
        self, user_id: str, platform: str, token_data1: TokenData, token_data2: TokenData
    ):
        """Storing a token for existing user/platform should overwrite."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        store = TokenStore(encryption=encryption)
        
        # Store first token
        store.store_token(user_id, platform, token_data1)
        
        # Store second token (overwrite)
        store.store_token(user_id, platform, token_data2)
        
        # Retrieved token should be the second one
        retrieved = store.get_token(user_id, platform)
        
        assert retrieved is not None
        assert retrieved.access_token == token_data2.access_token
        assert retrieved.refresh_token == token_data2.refresh_token

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        token_data=token_data_strategy(),
    )
    def test_platform_case_insensitive(
        self, user_id: str, token_data: TokenData
    ):
        """Platform names should be case-insensitive."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        store = TokenStore(encryption=encryption)
        
        # Store with uppercase
        store.store_token(user_id, "META", token_data)
        
        # Retrieve with lowercase
        retrieved = store.get_token(user_id, "meta")
        
        assert retrieved is not None
        assert retrieved.access_token == token_data.access_token

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
        token_data=token_data_strategy(),
    )
    def test_has_token_returns_true_when_exists(
        self, user_id: str, platform: str, token_data: TokenData
    ):
        """has_token should return True when token exists."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        store = TokenStore(encryption=encryption)
        
        # Store token
        store.store_token(user_id, platform, token_data)
        
        # Check existence
        assert store.has_token(user_id, platform) is True

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        platform=platform_strategy,
    )
    def test_has_token_returns_false_when_not_exists(
        self, user_id: str, platform: str
    ):
        """has_token should return False when token doesn't exist."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        store = TokenStore(encryption=encryption)
        
        # Check existence without storing
        assert store.has_token(user_id, platform) is False

    @settings(max_examples=100)
    @given(
        user_id=user_id_strategy,
        token_data=token_data_strategy(),
    )
    def test_clear_user_tokens_removes_all(
        self, user_id: str, token_data: TokenData
    ):
        """clear_user_tokens should remove all tokens for a user."""
        encryption = TokenEncryption(TokenEncryption.generate_key())
        store = TokenStore(encryption=encryption)
        
        # Store tokens for multiple platforms
        platforms = ["meta", "google", "shopify"]
        for platform in platforms:
            store.store_token(user_id, platform, token_data)
        
        # Clear all tokens
        count = store.clear_user_tokens(user_id)
        
        # Verify count matches
        assert count == len(platforms)
        
        # Verify all tokens are gone
        assert store.list_platforms(user_id) == []
