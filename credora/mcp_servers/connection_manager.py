"""
Connection Manager for MCP servers.

This module handles OAuth flows and token management for all platforms.

Requirements: 2.1, 2.2, 2.4, 2.5, 2.6, 7.4, 7.5, 8.1, 8.2, 8.3, 8.4, 8.5
"""

import secrets
from datetime import datetime
from typing import Dict, List, Optional

from credora.mcp_servers.errors import MCPError, MCPErrorType
from credora.mcp_servers.models.oauth import (
    Connection,
    ConnectionHealth,
    TokenData,
    SUPPORTED_PLATFORMS,
)
from credora.mcp_servers.oauth import (
    build_auth_url,
    exchange_code_for_token,
    refresh_access_token,
)
from credora.mcp_servers.token_store import TokenStore


class ConnectionManager:
    """
    Manages platform connections and OAuth tokens.
    
    Handles OAuth URL generation, callback processing, token refresh,
    and connection lifecycle management.
    
    Requirements: 2.1, 2.2, 2.4, 2.5, 2.6, 7.4, 7.5, 8.1, 8.2, 8.3, 8.4, 8.5
    """
    
    def __init__(self, token_store: Optional[TokenStore] = None):
        """Initialize the connection manager.
        
        Args:
            token_store: Optional TokenStore instance. Creates new one if not provided.
        """
        self.token_store = token_store or TokenStore()
        # Store connection metadata (connected_at, last_sync) per user/platform
        self._connection_metadata: Dict[str, Dict[str, dict]] = {}
        # Store pending OAuth states for CSRF protection
        self._pending_states: Dict[str, dict] = {}
    
    def _validate_platform(self, platform: str) -> str:
        """Validate and normalize platform name.
        
        Args:
            platform: Platform name to validate
            
        Returns:
            Normalized platform name (lowercase)
            
        Raises:
            ValueError: If platform is invalid
        """
        if not platform or not platform.strip():
            raise ValueError("platform is required and cannot be empty")
        
        platform_lower = platform.lower().strip()
        if platform_lower not in SUPPORTED_PLATFORMS:
            raise ValueError(
                f"Invalid platform: {platform}. Must be one of: {', '.join(SUPPORTED_PLATFORMS)}"
            )
        return platform_lower
    
    def _validate_user_id(self, user_id: str) -> str:
        """Validate and normalize user ID.
        
        Args:
            user_id: User ID to validate
            
        Returns:
            Normalized user ID (stripped)
            
        Raises:
            ValueError: If user_id is invalid
        """
        if not user_id or not user_id.strip():
            raise ValueError("user_id is required and cannot be empty")
        return user_id.strip()
    
    def _get_metadata_key(self, user_id: str, platform: str) -> str:
        """Generate metadata storage key."""
        return f"{user_id}:{platform}"
    
    def _store_connection_metadata(
        self, user_id: str, platform: str, platform_user_id: str
    ) -> None:
        """Store connection metadata for a user/platform.
        
        Args:
            user_id: User identifier
            platform: Platform name
            platform_user_id: Platform-specific user ID
        """
        user_id = self._validate_user_id(user_id)
        platform = self._validate_platform(platform)
        
        if user_id not in self._connection_metadata:
            self._connection_metadata[user_id] = {}
        
        now = datetime.now()
        self._connection_metadata[user_id][platform] = {
            "platform_user_id": platform_user_id,
            "connected_at": now,
            "last_sync": now,
        }
    
    def _update_last_sync(self, user_id: str, platform: str) -> None:
        """Update last_sync timestamp for a connection."""
        user_id = self._validate_user_id(user_id)
        platform = self._validate_platform(platform)
        
        if user_id in self._connection_metadata:
            if platform in self._connection_metadata[user_id]:
                self._connection_metadata[user_id][platform]["last_sync"] = datetime.now()
    
    def _delete_connection_metadata(self, user_id: str, platform: str) -> bool:
        """Delete connection metadata for a user/platform.
        
        Returns:
            True if metadata was deleted, False if it didn't exist
        """
        user_id = self._validate_user_id(user_id)
        platform = self._validate_platform(platform)
        
        if user_id not in self._connection_metadata:
            return False
        
        if platform not in self._connection_metadata[user_id]:
            return False
        
        del self._connection_metadata[user_id][platform]
        
        # Clean up empty user entry
        if not self._connection_metadata[user_id]:
            del self._connection_metadata[user_id]
        
        return True
    
    def get_oauth_url(
        self,
        platform: str,
        user_id: str,
        redirect_uri: str,
        shop: Optional[str] = None,
    ) -> str:
        """Generate OAuth authorization URL for a platform.
        
        Args:
            platform: Platform name (meta, google, shopify)
            user_id: User identifier for state tracking
            redirect_uri: OAuth callback URL
            shop: Shopify shop name (required for Shopify)
            
        Returns:
            OAuth authorization URL
            
        Raises:
            ValueError: If parameters are invalid
            
        Requirements: 2.1, 2.6, 8.2
        """
        platform = self._validate_platform(platform)
        user_id = self._validate_user_id(user_id)
        
        if not redirect_uri or not redirect_uri.strip():
            raise ValueError("redirect_uri is required")
        
        # Generate secure state parameter
        state = secrets.token_urlsafe(32)
        
        # Store state for verification during callback
        self._pending_states[state] = {
            "user_id": user_id,
            "platform": platform,
            "redirect_uri": redirect_uri.strip(),
            "shop": shop.strip() if shop else None,
            "created_at": datetime.now(),
        }
        
        # Build and return OAuth URL
        return build_auth_url(
            platform=platform,
            state=state,
            redirect_uri=redirect_uri.strip(),
            shop=shop,
        )
    
    def verify_state(self, state: str) -> Optional[dict]:
        """Verify OAuth state parameter and return associated data.
        
        Args:
            state: State parameter from OAuth callback
            
        Returns:
            State data dict if valid, None if invalid
        """
        if not state or state not in self._pending_states:
            return None
        
        state_data = self._pending_states.pop(state)
        return state_data
    
    async def handle_oauth_callback(
        self,
        platform: str,
        code: str,
        user_id: str,
        redirect_uri: str,
        shop: Optional[str] = None,
    ) -> bool:
        """Handle OAuth callback and store tokens.
        
        Args:
            platform: Platform name
            code: Authorization code from callback
            user_id: User identifier
            redirect_uri: Redirect URI used in authorization
            shop: Shopify shop name (required for Shopify)
            
        Returns:
            True if tokens were successfully stored
            
        Raises:
            ValueError: If parameters are invalid
            MCPError: If token exchange fails
            
        Requirements: 2.2
        """
        platform = self._validate_platform(platform)
        user_id = self._validate_user_id(user_id)
        
        if not code or not code.strip():
            raise ValueError("Authorization code is required")
        
        if not redirect_uri or not redirect_uri.strip():
            raise ValueError("redirect_uri is required")
        
        # Exchange code for tokens
        token_data = await exchange_code_for_token(
            platform=platform,
            code=code.strip(),
            redirect_uri=redirect_uri.strip(),
            shop=shop,
        )
        
        # Store tokens securely
        self.token_store.store_token(user_id, platform, token_data)
        
        # Store connection metadata
        self._store_connection_metadata(user_id, platform, token_data.platform_user_id)
        
        return True
    
    async def get_access_token(
        self,
        platform: str,
        user_id: str,
        shop: Optional[str] = None,
    ) -> str:
        """Get a valid access token, refreshing if necessary.
        
        Args:
            platform: Platform name
            user_id: User identifier
            shop: Shopify shop name (required for Shopify refresh)
            
        Returns:
            Valid access token
            
        Raises:
            ValueError: If parameters are invalid
            MCPError: If no token exists or refresh fails
            
        Requirements: 2.4
        """
        platform = self._validate_platform(platform)
        user_id = self._validate_user_id(user_id)
        
        # Get stored token
        token_data = self.token_store.get_token(user_id, platform)
        
        if token_data is None:
            raise MCPError(
                error_type=MCPErrorType.AUTH_REQUIRED,
                message=f"No connection found for platform: {platform}. Please authenticate.",
                recoverable=False,
                details={"platform": platform, "user_id": user_id},
            )
        
        # Check if token is expired
        if token_data.is_expired():
            # Attempt to refresh
            new_token = await self.refresh_token(platform, user_id, shop)
            return new_token
        
        # Update last sync time
        self._update_last_sync(user_id, platform)
        
        return token_data.access_token
    
    async def refresh_token(
        self,
        platform: str,
        user_id: str,
        shop: Optional[str] = None,
    ) -> str:
        """Refresh an expired access token.
        
        Args:
            platform: Platform name
            user_id: User identifier
            shop: Shopify shop name (required for Shopify)
            
        Returns:
            New access token
            
        Raises:
            ValueError: If parameters are invalid
            MCPError: If refresh fails
            
        Requirements: 2.4, 2.5
        """
        platform = self._validate_platform(platform)
        user_id = self._validate_user_id(user_id)
        
        # Get stored token
        token_data = self.token_store.get_token(user_id, platform)
        
        if token_data is None:
            raise MCPError(
                error_type=MCPErrorType.AUTH_REQUIRED,
                message=f"No connection found for platform: {platform}. Please authenticate.",
                recoverable=False,
                details={"platform": platform, "user_id": user_id},
            )
        
        try:
            # Attempt to refresh the token
            new_token_data = await refresh_access_token(
                platform=platform,
                refresh_token=token_data.refresh_token,
                shop=shop,
            )
            
            # Preserve platform_user_id from original token
            new_token_data = TokenData(
                access_token=new_token_data.access_token,
                refresh_token=new_token_data.refresh_token,
                expires_at=new_token_data.expires_at,
                scopes=new_token_data.scopes,
                platform_user_id=token_data.platform_user_id,
            )
            
            # Store the new token
            self.token_store.store_token(user_id, platform, new_token_data)
            
            # Update last sync time
            self._update_last_sync(user_id, platform)
            
            return new_token_data.access_token
            
        except MCPError as e:
            # Re-raise with additional context about re-authentication
            if e.error_type in (MCPErrorType.AUTH_EXPIRED, MCPErrorType.AUTH_REQUIRED):
                raise MCPError(
                    error_type=MCPErrorType.AUTH_EXPIRED,
                    message=f"Token refresh failed for {platform}. Please re-authenticate.",
                    recoverable=False,
                    details={"platform": platform, "user_id": user_id, "original_error": e.message},
                )
            raise
    
    async def disconnect_platform(self, platform: str, user_id: str) -> bool:
        """Disconnect a platform and delete stored tokens.
        
        Args:
            platform: Platform name
            user_id: User identifier
            
        Returns:
            True if disconnection was successful
            
        Raises:
            ValueError: If parameters are invalid
            
        Requirements: 7.4, 8.3
        """
        platform = self._validate_platform(platform)
        user_id = self._validate_user_id(user_id)
        
        # Delete token from store
        token_deleted = self.token_store.delete_token(user_id, platform)
        
        # Delete connection metadata
        metadata_deleted = self._delete_connection_metadata(user_id, platform)
        
        return token_deleted or metadata_deleted
    
    async def list_connections(self, user_id: str) -> List[Connection]:
        """List all platform connections for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of Connection objects for connected platforms
            
        Raises:
            ValueError: If user_id is invalid
            
        Requirements: 8.1, 8.5
        """
        user_id = self._validate_user_id(user_id)
        
        connections = []
        
        # Get all platforms with stored tokens
        platforms = self.token_store.list_platforms(user_id)
        
        for platform in platforms:
            # Get token to check status
            token_data = self.token_store.get_token(user_id, platform)
            
            if token_data is None:
                continue
            
            # Determine connection status
            if token_data.is_expired():
                status = "expired"
            else:
                status = "active"
            
            # Get metadata
            metadata = {}
            if user_id in self._connection_metadata:
                metadata = self._connection_metadata[user_id].get(platform, {})
            
            connected_at = metadata.get("connected_at", datetime.now())
            last_sync = metadata.get("last_sync", datetime.now())
            platform_user_id = metadata.get("platform_user_id", token_data.platform_user_id)
            
            connections.append(
                Connection(
                    platform=platform,
                    user_id=user_id,
                    platform_user_id=platform_user_id,
                    connected_at=connected_at,
                    last_sync=last_sync,
                    status=status,
                )
            )
        
        return connections
    
    async def get_platform_metadata(
        self,
        platform: str,
        user_id: str,
        key: str,
    ) -> Optional[str]:
        """Get platform-specific metadata for a connection.
        
        Args:
            platform: Platform name
            user_id: User identifier
            key: Metadata key to retrieve
            
        Returns:
            Metadata value if found, None otherwise
            
        Raises:
            ValueError: If parameters are invalid
        """
        platform = self._validate_platform(platform)
        user_id = self._validate_user_id(user_id)
        
        if user_id not in self._connection_metadata:
            return None
        
        if platform not in self._connection_metadata[user_id]:
            return None
        
        return self._connection_metadata[user_id][platform].get(key)
    
    async def set_platform_metadata(
        self,
        platform: str,
        user_id: str,
        key: str,
        value: str,
    ) -> None:
        """Set platform-specific metadata for a connection.
        
        Args:
            platform: Platform name
            user_id: User identifier
            key: Metadata key to set
            value: Metadata value
            
        Raises:
            ValueError: If parameters are invalid
        """
        platform = self._validate_platform(platform)
        user_id = self._validate_user_id(user_id)
        
        if user_id not in self._connection_metadata:
            self._connection_metadata[user_id] = {}
        
        if platform not in self._connection_metadata[user_id]:
            self._connection_metadata[user_id][platform] = {}
        
        self._connection_metadata[user_id][platform][key] = value
    
    async def check_connection_health(
        self,
        platform: str,
        user_id: str,
    ) -> ConnectionHealth:
        """Check the health of a platform connection.
        
        Args:
            platform: Platform name
            user_id: User identifier
            
        Returns:
            ConnectionHealth object with health status
            
        Raises:
            ValueError: If parameters are invalid
            
        Requirements: 8.4
        """
        platform = self._validate_platform(platform)
        user_id = self._validate_user_id(user_id)
        
        now = datetime.now()
        
        # Get stored token
        token_data = self.token_store.get_token(user_id, platform)
        
        if token_data is None:
            return ConnectionHealth(
                platform=platform,
                is_healthy=False,
                token_valid=False,
                last_checked=now,
                error_message="No connection found. Please authenticate.",
            )
        
        # Check if token is expired
        token_valid = not token_data.is_expired()
        
        if not token_valid:
            return ConnectionHealth(
                platform=platform,
                is_healthy=False,
                token_valid=False,
                last_checked=now,
                error_message="Token has expired. Please re-authenticate or refresh.",
            )
        
        # Token is valid, connection is healthy
        return ConnectionHealth(
            platform=platform,
            is_healthy=True,
            token_valid=True,
            last_checked=now,
            error_message=None,
        )
