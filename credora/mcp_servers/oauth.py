"""
OAuth handlers for MCP servers.

This module provides OAuth 2.0 authorization code flow implementation
for Meta Ads, Google Ads, and Shopify platforms.

Requirements: 2.1, 2.2, 2.4, 2.5, 2.6
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Optional
from urllib.parse import urlencode, urlparse

import httpx

from credora.mcp_servers.errors import MCPError, MCPErrorType
from credora.mcp_servers.models.oauth import OAuthConfig, TokenData, SUPPORTED_PLATFORMS


# Default scopes for each platform
DEFAULT_SCOPES: Dict[str, list] = {
    "meta": ["ads_read", "ads_management", "business_management"],
    "google": ["https://www.googleapis.com/auth/adwords"],
    "shopify": ["read_orders", "read_products", "read_customers", "read_analytics"],
}

# Platform OAuth endpoints
PLATFORM_AUTH_URLS: Dict[str, str] = {
    "meta": "https://www.facebook.com/v21.0/dialog/oauth",
    "google": "https://accounts.google.com/o/oauth2/v2/auth",
    "shopify": "https://{shop}.myshopify.com/admin/oauth/authorize",
}

PLATFORM_TOKEN_URLS: Dict[str, str] = {
    "meta": "https://graph.facebook.com/v21.0/oauth/access_token",
    "google": "https://oauth2.googleapis.com/token",
    "shopify": "https://{shop}.myshopify.com/admin/oauth/access_token",
}


def get_platform_config(platform: str) -> Optional[OAuthConfig]:
    """Get OAuth configuration for a platform from environment variables.
    
    Args:
        platform: Platform name (meta, google, shopify)
        
    Returns:
        OAuthConfig if platform is supported and configured, None otherwise
        
    Requirements: 1.5
    """
    platform_lower = platform.lower().strip()
    if platform_lower not in SUPPORTED_PLATFORMS:
        return None
    
    # Get credentials from environment
    prefix = platform_lower.upper()
    client_id = os.environ.get(f"{prefix}_CLIENT_ID", "")
    client_secret = os.environ.get(f"{prefix}_CLIENT_SECRET", "")
    redirect_uri = os.environ.get(f"{prefix}_REDIRECT_URI", "")
    
    # If no credentials configured, return None
    if not client_id or not client_secret:
        return None
    
    return OAuthConfig(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scopes=DEFAULT_SCOPES.get(platform_lower, []),
        auth_url=PLATFORM_AUTH_URLS.get(platform_lower, ""),
        token_url=PLATFORM_TOKEN_URLS.get(platform_lower, ""),
    )


def build_auth_url(
    platform: str,
    state: str,
    redirect_uri: Optional[str] = None,
    shop: Optional[str] = None,
    client_id: Optional[str] = None,
    scopes: Optional[list] = None,
) -> str:
    """
    Build OAuth authorization URL for a platform.
    
    Args:
        platform: Platform name (meta, google, shopify)
        state: State parameter for CSRF protection
        redirect_uri: Override redirect URI (required)
        shop: Shopify shop name (required for Shopify)
        client_id: Override client ID (optional, uses env var if not provided)
        scopes: Override scopes (optional, uses defaults if not provided)
    
    Returns:
        Authorization URL string
        
    Raises:
        ValueError: If platform is invalid, required params missing, or URL invalid
        
    Requirements: 2.1, 2.6, 8.2
    """
    # Validate platform
    platform_lower = platform.lower().strip() if platform else ""
    if not platform_lower or platform_lower not in SUPPORTED_PLATFORMS:
        raise ValueError(f"Invalid platform: {platform}. Must be one of: {', '.join(SUPPORTED_PLATFORMS)}")
    
    # Validate state
    if not state or not state.strip():
        raise ValueError("state parameter is required for CSRF protection")
    
    # Validate redirect_uri
    if not redirect_uri or not redirect_uri.strip():
        raise ValueError("redirect_uri is required")
    
    # Validate Shopify shop parameter
    if platform_lower == "shopify" and (not shop or not shop.strip()):
        raise ValueError("shop parameter is required for Shopify OAuth")
    
    # Get client_id from environment if not provided
    if not client_id:
        prefix = platform_lower.upper()
        client_id = os.environ.get(f"{prefix}_CLIENT_ID", "")
    
    if not client_id:
        raise ValueError(f"client_id is required. Set {platform_lower.upper()}_CLIENT_ID environment variable")
    
    # Get scopes
    platform_scopes = scopes if scopes is not None else DEFAULT_SCOPES.get(platform_lower, [])
    
    # Get base auth URL
    auth_url = PLATFORM_AUTH_URLS.get(platform_lower, "")
    if not auth_url:
        raise ValueError(f"No auth URL configured for platform: {platform_lower}")
    
    # Replace shop placeholder for Shopify
    if platform_lower == "shopify" and shop:
        auth_url = auth_url.replace("{shop}", shop.strip())
    
    # Build query parameters based on platform
    params: Dict[str, str] = {}
    
    if platform_lower == "meta":
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri.strip(),
            "state": state.strip(),
            "scope": ",".join(platform_scopes),
            "response_type": "code",
        }
    elif platform_lower == "google":
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri.strip(),
            "state": state.strip(),
            "scope": " ".join(platform_scopes),
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",
        }
    elif platform_lower == "shopify":
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri.strip(),
            "state": state.strip(),
            "scope": ",".join(platform_scopes),
        }
    
    # Build final URL
    full_url = f"{auth_url}?{urlencode(params)}"
    
    # Validate URL is HTTPS (Requirements: 7.2)
    parsed = urlparse(full_url)
    if parsed.scheme != "https":
        raise ValueError("OAuth URLs must use HTTPS")
    
    return full_url


async def exchange_code_for_token(
    platform: str,
    code: str,
    redirect_uri: str,
    shop: Optional[str] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
) -> TokenData:
    """
    Exchange authorization code for access token.
    
    Args:
        platform: Platform name
        code: Authorization code from callback
        redirect_uri: Redirect URI used in authorization
        shop: Shopify shop name (required for Shopify)
        client_id: Override client ID (optional)
        client_secret: Override client secret (optional)
    
    Returns:
        TokenData with access and refresh tokens
        
    Raises:
        ValueError: If required parameters are missing
        MCPError: If token exchange fails
        
    Requirements: 2.2
    """
    # Validate platform
    platform_lower = platform.lower().strip() if platform else ""
    if not platform_lower or platform_lower not in SUPPORTED_PLATFORMS:
        raise ValueError(f"Invalid platform: {platform}")
    
    # Validate code
    if not code or not code.strip():
        raise ValueError("Authorization code is required")
    
    # Validate redirect_uri
    if not redirect_uri or not redirect_uri.strip():
        raise ValueError("redirect_uri is required")
    
    # Validate Shopify shop parameter
    if platform_lower == "shopify" and (not shop or not shop.strip()):
        raise ValueError("shop parameter is required for Shopify")
    
    # Get credentials from environment if not provided
    prefix = platform_lower.upper()
    if not client_id:
        client_id = os.environ.get(f"{prefix}_CLIENT_ID", "")
    if not client_secret:
        client_secret = os.environ.get(f"{prefix}_CLIENT_SECRET", "")
    
    if not client_id or not client_secret:
        raise ValueError(f"OAuth credentials not configured for {platform_lower}")
    
    # Get token URL
    token_url = PLATFORM_TOKEN_URLS.get(platform_lower, "")
    if platform_lower == "shopify" and shop:
        token_url = token_url.replace("{shop}", shop.strip())
    
    # Build request based on platform
    async with httpx.AsyncClient() as client:
        try:
            if platform_lower == "meta":
                response = await client.get(
                    token_url,
                    params={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "redirect_uri": redirect_uri.strip(),
                        "code": code.strip(),
                    },
                )
            elif platform_lower == "google":
                response = await client.post(
                    token_url,
                    data={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "redirect_uri": redirect_uri.strip(),
                        "code": code.strip(),
                        "grant_type": "authorization_code",
                    },
                )
            elif platform_lower == "shopify":
                response = await client.post(
                    token_url,
                    json={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "code": code.strip(),
                    },
                )
            else:
                raise ValueError(f"Unsupported platform: {platform_lower}")
            
            response.raise_for_status()
            data = response.json()
            
            # Parse response based on platform
            access_token = data.get("access_token", "")
            refresh_token = data.get("refresh_token", "")
            expires_in = data.get("expires_in", 3600)
            
            # Meta doesn't always return refresh token
            if platform_lower == "meta" and not refresh_token:
                refresh_token = access_token  # Use access token as placeholder
            
            # Shopify tokens don't expire (use long expiry)
            if platform_lower == "shopify":
                expires_in = 365 * 24 * 3600  # 1 year
                refresh_token = access_token  # Shopify doesn't use refresh tokens
            
            # Calculate expiry time
            expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            # Get platform user ID from response
            platform_user_id = str(data.get("user_id", data.get("associated_user", {}).get("id", "unknown")))
            
            return TokenData(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                scopes=DEFAULT_SCOPES.get(platform_lower, []),
                platform_user_id=platform_user_id,
            )
            
        except httpx.HTTPStatusError as e:
            error_data = {}
            try:
                error_data = e.response.json()
            except Exception:
                pass
            
            raise MCPError(
                error_type=MCPErrorType.AUTH_REQUIRED,
                message=f"Token exchange failed: {error_data.get('error_description', str(e))}",
                recoverable=True,
                details={"platform": platform_lower, "error": error_data},
            )
        except httpx.RequestError as e:
            raise MCPError(
                error_type=MCPErrorType.NETWORK_ERROR,
                message=f"Network error during token exchange: {str(e)}",
                recoverable=True,
                details={"platform": platform_lower},
            )


async def refresh_access_token(
    platform: str,
    refresh_token: str,
    shop: Optional[str] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
) -> TokenData:
    """
    Refresh an expired access token.
    
    Args:
        platform: Platform name
        refresh_token: Refresh token
        shop: Shopify shop name (required for Shopify)
        client_id: Override client ID (optional)
        client_secret: Override client secret (optional)
    
    Returns:
        TokenData with new access token
        
    Raises:
        ValueError: If required parameters are missing
        MCPError: If refresh fails
        
    Requirements: 2.4, 2.5
    """
    # Validate platform
    platform_lower = platform.lower().strip() if platform else ""
    if not platform_lower or platform_lower not in SUPPORTED_PLATFORMS:
        raise ValueError(f"Invalid platform: {platform}")
    
    # Validate refresh_token
    if not refresh_token or not refresh_token.strip():
        raise ValueError("refresh_token is required")
    
    # Shopify tokens don't expire/refresh
    if platform_lower == "shopify":
        raise MCPError(
            error_type=MCPErrorType.AUTH_REQUIRED,
            message="Shopify tokens cannot be refreshed. Please re-authenticate.",
            recoverable=False,
            details={"platform": platform_lower},
        )
    
    # Get credentials from environment if not provided
    prefix = platform_lower.upper()
    if not client_id:
        client_id = os.environ.get(f"{prefix}_CLIENT_ID", "")
    if not client_secret:
        client_secret = os.environ.get(f"{prefix}_CLIENT_SECRET", "")
    
    if not client_id or not client_secret:
        raise ValueError(f"OAuth credentials not configured for {platform_lower}")
    
    # Get token URL
    token_url = PLATFORM_TOKEN_URLS.get(platform_lower, "")
    
    async with httpx.AsyncClient() as client:
        try:
            if platform_lower == "meta":
                # Meta uses a different endpoint for token refresh
                response = await client.get(
                    token_url,
                    params={
                        "grant_type": "fb_exchange_token",
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "fb_exchange_token": refresh_token.strip(),
                    },
                )
            elif platform_lower == "google":
                response = await client.post(
                    token_url,
                    data={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "refresh_token": refresh_token.strip(),
                        "grant_type": "refresh_token",
                    },
                )
            else:
                raise ValueError(f"Unsupported platform for refresh: {platform_lower}")
            
            response.raise_for_status()
            data = response.json()
            
            # Parse response
            access_token = data.get("access_token", "")
            new_refresh_token = data.get("refresh_token", refresh_token)  # Keep old if not returned
            expires_in = data.get("expires_in", 3600)
            
            # Calculate expiry time
            expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            return TokenData(
                access_token=access_token,
                refresh_token=new_refresh_token,
                expires_at=expires_at,
                scopes=DEFAULT_SCOPES.get(platform_lower, []),
                platform_user_id="refreshed",  # Will be updated from stored data
            )
            
        except httpx.HTTPStatusError as e:
            error_data = {}
            try:
                error_data = e.response.json()
            except Exception:
                pass
            
            # Check if this is an auth error requiring re-authentication
            error_type = error_data.get("error", "")
            if error_type in ["invalid_grant", "invalid_token"]:
                raise MCPError(
                    error_type=MCPErrorType.AUTH_EXPIRED,
                    message="Refresh token is invalid or expired. Please re-authenticate.",
                    recoverable=False,
                    details={"platform": platform_lower, "error": error_data},
                )
            
            raise MCPError(
                error_type=MCPErrorType.AUTH_REQUIRED,
                message=f"Token refresh failed: {error_data.get('error_description', str(e))}",
                recoverable=True,
                details={"platform": platform_lower, "error": error_data},
            )
        except httpx.RequestError as e:
            raise MCPError(
                error_type=MCPErrorType.NETWORK_ERROR,
                message=f"Network error during token refresh: {str(e)}",
                recoverable=True,
                details={"platform": platform_lower},
            )
