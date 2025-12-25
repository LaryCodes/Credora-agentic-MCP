"""Property-based tests for OAuth URL generation.

**Feature: platform-mcp-servers**
"""

import os
from urllib.parse import parse_qs, urlparse

import pytest
from hypothesis import given, strategies as st, settings, assume

from credora.mcp_servers.oauth import build_auth_url, DEFAULT_SCOPES
from credora.mcp_servers.connection_manager import ConnectionManager
from credora.mcp_servers.token_store import TokenStore
from credora.security import TokenEncryption


# Strategy for generating valid platform names
platform_strategy = st.sampled_from(["meta", "google", "shopify"])

# Strategy for non-Shopify platforms (don't require shop parameter)
non_shopify_platform_strategy = st.sampled_from(["meta", "google"])

# Strategy for generating valid state parameters (non-empty, no whitespace at ends)
state_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "S"), blacklist_characters="\x00"),
    min_size=1,
    max_size=100
).map(lambda x: x.strip()).filter(lambda x: len(x) > 0)

# Strategy for generating valid redirect URIs
redirect_uri_strategy = st.sampled_from([
    "https://example.com/callback",
    "https://app.credora.io/oauth/callback",
    "https://localhost:3000/auth/callback",
])

# Strategy for generating valid client IDs (no null chars, no whitespace-only)
client_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), blacklist_characters="\x00"),
    min_size=1,
    max_size=50
).filter(lambda x: x.strip() != "")

# Strategy for generating valid shop names for Shopify
shop_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="-"),
    min_size=1,
    max_size=50,
).filter(lambda x: x.strip() != "" and not x.startswith("-") and not x.endswith("-"))

# Strategy for generating valid user IDs
user_id_strategy = st.text(min_size=1, max_size=50).filter(lambda x: x.strip() != "")


class TestOAuthURLGeneration:
    """
    **Feature: platform-mcp-servers, Property 3: OAuth URL Generation**
    **Validates: Requirements 2.1, 2.6, 8.2**
    
    For any platform and user_id combination, generating an OAuth URL shall
    produce a valid URL containing the correct authorization endpoint,
    client_id, redirect_uri, and scopes.
    """

    @settings(max_examples=100)
    @given(
        platform=non_shopify_platform_strategy,
        state=state_strategy,
        redirect_uri=redirect_uri_strategy,
        client_id=client_id_strategy,
    )
    def test_oauth_url_contains_required_params(
        self, platform: str, state: str, redirect_uri: str, client_id: str
    ):
        """OAuth URL should contain client_id, redirect_uri, state, and scopes."""
        url = build_auth_url(
            platform=platform,
            state=state,
            redirect_uri=redirect_uri,
            client_id=client_id,
        )
        
        # Parse the URL
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # Verify required parameters are present
        assert "client_id" in query_params
        assert query_params["client_id"][0] == client_id
        
        assert "redirect_uri" in query_params
        assert query_params["redirect_uri"][0] == redirect_uri
        
        assert "state" in query_params
        assert query_params["state"][0] == state
        
        # Verify scopes are present
        if platform == "meta":
            assert "scope" in query_params
            scopes = query_params["scope"][0].split(",")
            for scope in DEFAULT_SCOPES["meta"]:
                assert scope in scopes
        elif platform == "google":
            assert "scope" in query_params
            scopes = query_params["scope"][0].split(" ")
            for scope in DEFAULT_SCOPES["google"]:
                assert scope in scopes

    @settings(max_examples=100)
    @given(
        platform=platform_strategy,
        state=state_strategy,
        redirect_uri=redirect_uri_strategy,
        client_id=client_id_strategy,
        shop=shop_strategy,
    )
    def test_oauth_url_uses_https(
        self, platform: str, state: str, redirect_uri: str, client_id: str, shop: str
    ):
        """OAuth URL must use HTTPS scheme (Requirements: 7.2)."""
        # Shopify requires shop parameter
        shop_param = shop if platform == "shopify" else None
        
        url = build_auth_url(
            platform=platform,
            state=state,
            redirect_uri=redirect_uri,
            client_id=client_id,
            shop=shop_param,
        )
        
        parsed = urlparse(url)
        assert parsed.scheme == "https"

    @settings(max_examples=100)
    @given(
        platform=non_shopify_platform_strategy,
        state=state_strategy,
        redirect_uri=redirect_uri_strategy,
        client_id=client_id_strategy,
    )
    def test_oauth_url_has_correct_auth_endpoint(
        self, platform: str, state: str, redirect_uri: str, client_id: str
    ):
        """OAuth URL should use the correct authorization endpoint for each platform."""
        url = build_auth_url(
            platform=platform,
            state=state,
            redirect_uri=redirect_uri,
            client_id=client_id,
        )
        
        parsed = urlparse(url)
        
        if platform == "meta":
            assert "facebook.com" in parsed.netloc
            assert "/dialog/oauth" in parsed.path
        elif platform == "google":
            assert "accounts.google.com" in parsed.netloc
            assert "/o/oauth2" in parsed.path

    @settings(max_examples=100)
    @given(
        shop=shop_strategy,
        state=state_strategy,
        redirect_uri=redirect_uri_strategy,
        client_id=client_id_strategy,
    )
    def test_shopify_oauth_url_contains_shop(
        self, shop: str, state: str, redirect_uri: str, client_id: str
    ):
        """Shopify OAuth URL should contain the shop name in the domain."""
        url = build_auth_url(
            platform="shopify",
            state=state,
            redirect_uri=redirect_uri,
            client_id=client_id,
            shop=shop,
        )
        
        parsed = urlparse(url)
        
        # Shop name should be in the domain
        assert shop in parsed.netloc
        assert "myshopify.com" in parsed.netloc

    @settings(max_examples=100)
    @given(
        platform=non_shopify_platform_strategy,
        state=state_strategy,
        redirect_uri=redirect_uri_strategy,
        client_id=client_id_strategy,
    )
    def test_oauth_url_has_response_type_code(
        self, platform: str, state: str, redirect_uri: str, client_id: str
    ):
        """OAuth URL should specify response_type=code for authorization code flow."""
        url = build_auth_url(
            platform=platform,
            state=state,
            redirect_uri=redirect_uri,
            client_id=client_id,
        )
        
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # Meta and Google should have response_type=code
        if platform in ["meta", "google"]:
            assert "response_type" in query_params
            assert query_params["response_type"][0] == "code"

    @settings(max_examples=100)
    @given(
        state=state_strategy,
        redirect_uri=redirect_uri_strategy,
        client_id=client_id_strategy,
    )
    def test_google_oauth_url_has_offline_access(
        self, state: str, redirect_uri: str, client_id: str
    ):
        """Google OAuth URL should request offline access for refresh tokens."""
        url = build_auth_url(
            platform="google",
            state=state,
            redirect_uri=redirect_uri,
            client_id=client_id,
        )
        
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # Google should have access_type=offline
        assert "access_type" in query_params
        assert query_params["access_type"][0] == "offline"


class TestConnectionManagerOAuthURL:
    """
    **Feature: platform-mcp-servers, Property 3: OAuth URL Generation (via ConnectionManager)**
    **Validates: Requirements 2.1, 2.6, 8.2**
    
    Tests OAuth URL generation through the ConnectionManager interface.
    """

    @settings(max_examples=100)
    @given(
        platform=non_shopify_platform_strategy,
        user_id=user_id_strategy,
        redirect_uri=redirect_uri_strategy,
        client_id=client_id_strategy,
    )
    def test_connection_manager_generates_valid_oauth_url(
        self, platform: str, user_id: str, redirect_uri: str, client_id: str
    ):
        """ConnectionManager should generate valid OAuth URLs with state parameter."""
        # Set up environment variable for client_id
        env_key = f"{platform.upper()}_CLIENT_ID"
        original_value = os.environ.get(env_key)
        os.environ[env_key] = client_id
        
        try:
            encryption = TokenEncryption(TokenEncryption.generate_key())
            token_store = TokenStore(encryption=encryption)
            manager = ConnectionManager(token_store=token_store)
            
            url = manager.get_oauth_url(
                platform=platform,
                user_id=user_id,
                redirect_uri=redirect_uri,
            )
            
            # Parse the URL
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            
            # Verify URL is HTTPS
            assert parsed.scheme == "https"
            
            # Verify required parameters
            assert "client_id" in query_params
            assert "redirect_uri" in query_params
            assert "state" in query_params
            
            # State should be non-empty (generated by ConnectionManager)
            assert len(query_params["state"][0]) > 0
            
        finally:
            # Restore original environment
            if original_value is not None:
                os.environ[env_key] = original_value
            elif env_key in os.environ:
                del os.environ[env_key]

    @settings(max_examples=100)
    @given(
        platform=non_shopify_platform_strategy,
        user_id=user_id_strategy,
        redirect_uri=redirect_uri_strategy,
        client_id=client_id_strategy,
    )
    def test_connection_manager_stores_state_for_verification(
        self, platform: str, user_id: str, redirect_uri: str, client_id: str
    ):
        """ConnectionManager should store state for later verification."""
        # Set up environment variable for client_id
        env_key = f"{platform.upper()}_CLIENT_ID"
        original_value = os.environ.get(env_key)
        os.environ[env_key] = client_id
        
        try:
            encryption = TokenEncryption(TokenEncryption.generate_key())
            token_store = TokenStore(encryption=encryption)
            manager = ConnectionManager(token_store=token_store)
            
            url = manager.get_oauth_url(
                platform=platform,
                user_id=user_id,
                redirect_uri=redirect_uri,
            )
            
            # Extract state from URL
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            state = query_params["state"][0]
            
            # Verify state can be verified
            state_data = manager.verify_state(state)
            assert state_data is not None
            assert state_data["user_id"] == user_id.strip()
            assert state_data["platform"] == platform.lower()
            assert state_data["redirect_uri"] == redirect_uri.strip()
            
            # State should be consumed (one-time use)
            assert manager.verify_state(state) is None
            
        finally:
            # Restore original environment
            if original_value is not None:
                os.environ[env_key] = original_value
            elif env_key in os.environ:
                del os.environ[env_key]
