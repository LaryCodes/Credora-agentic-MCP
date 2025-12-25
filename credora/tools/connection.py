"""Connection management tools for CFO Agent.

Requirements: 8.1, 8.2, 8.3, 8.4

These tools allow the CFO Agent to manage platform connections,
including listing, connecting, disconnecting, and checking health.
"""

import json
from typing import Optional
from datetime import datetime

from agents import function_tool

from credora.mcp_servers.connection_manager import ConnectionManager
from credora.mcp_servers.token_store import TokenStore
from credora.security import TokenEncryption


# Module-level connection manager instance
_connection_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """Get the current connection manager instance.
    
    Returns:
        The ConnectionManager instance
    """
    global _connection_manager
    if _connection_manager is None:
        encryption = TokenEncryption(TokenEncryption.generate_key())
        token_store = TokenStore(encryption=encryption)
        _connection_manager = ConnectionManager(token_store=token_store)
    return _connection_manager


def set_connection_manager(manager: ConnectionManager) -> None:
    """Set the connection manager instance (for testing).
    
    Args:
        manager: The ConnectionManager instance to use
    """
    global _connection_manager
    _connection_manager = manager


def _connection_to_dict(connection) -> dict:
    """Convert Connection to a JSON-serializable dictionary.
    
    Args:
        connection: The Connection to convert
        
    Returns:
        Dictionary representation of the connection
    """
    return {
        "platform": connection.platform,
        "user_id": connection.user_id,
        "platform_user_id": connection.platform_user_id,
        "connected_at": connection.connected_at.isoformat(),
        "last_sync": connection.last_sync.isoformat(),
        "status": connection.status,
    }


def _connection_health_to_dict(health) -> dict:
    """Convert ConnectionHealth to a JSON-serializable dictionary.
    
    Args:
        health: The ConnectionHealth to convert
        
    Returns:
        Dictionary representation of the connection health
    """
    return {
        "platform": health.platform,
        "is_healthy": health.is_healthy,
        "token_valid": health.token_valid,
        "last_checked": health.last_checked.isoformat(),
        "error_message": health.error_message,
    }



# Supported platforms for connection
SUPPORTED_PLATFORMS = ["meta", "google", "shopify"]


def _list_connected_platforms_impl(user_id: str) -> str:
    """Internal implementation of list_connected_platforms.
    
    Lists all connected platforms for a user with their status and last sync time.
    
    Args:
        user_id: The unique identifier for the user
        
    Returns:
        JSON string containing list of connections or error message
        
    Requirements: 8.1, 8.5
    """
    if not user_id or not user_id.strip():
        return json.dumps({
            "error": "user_id is required and cannot be empty",
            "success": False
        })
    
    try:
        manager = get_connection_manager()
        # Use synchronous wrapper since the tool is synchronous
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        connections = loop.run_until_complete(manager.list_connections(user_id.strip()))
        
        connections_list = [_connection_to_dict(c) for c in connections]
        
        return json.dumps({
            "connections": connections_list,
            "total_count": len(connections_list),
            "success": True
        })
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "success": False
        })


def _initiate_platform_connection_impl(
    user_id: str,
    platform: str,
    redirect_uri: str,
    shop: Optional[str] = None
) -> str:
    """Internal implementation of initiate_platform_connection.
    
    Generates an OAuth URL to initiate platform connection.
    
    Args:
        user_id: The unique identifier for the user
        platform: The platform to connect (meta, google, shopify)
        redirect_uri: The OAuth callback URL
        shop: Shopify shop name (required for Shopify)
        
    Returns:
        JSON string containing OAuth URL or error message
        
    Requirements: 8.2
    """
    if not user_id or not user_id.strip():
        return json.dumps({
            "error": "user_id is required and cannot be empty",
            "success": False
        })
    
    if not platform or not platform.strip():
        return json.dumps({
            "error": "platform is required and cannot be empty",
            "success": False
        })
    
    platform_lower = platform.lower().strip()
    if platform_lower not in SUPPORTED_PLATFORMS:
        return json.dumps({
            "error": f"Invalid platform '{platform}'. Supported platforms: {', '.join(SUPPORTED_PLATFORMS)}",
            "success": False
        })
    
    if not redirect_uri or not redirect_uri.strip():
        return json.dumps({
            "error": "redirect_uri is required and cannot be empty",
            "success": False
        })
    
    # Shopify requires shop name
    if platform_lower == "shopify" and (not shop or not shop.strip()):
        return json.dumps({
            "error": "shop name is required for Shopify connections",
            "success": False
        })
    
    try:
        manager = get_connection_manager()
        oauth_url = manager.get_oauth_url(
            platform=platform_lower,
            user_id=user_id.strip(),
            redirect_uri=redirect_uri.strip(),
            shop=shop.strip() if shop else None
        )
        
        return json.dumps({
            "oauth_url": oauth_url,
            "platform": platform_lower,
            "message": f"Please visit the URL to authorize {platform_lower} access",
            "success": True
        })
    except ValueError as e:
        return json.dumps({
            "error": str(e),
            "success": False
        })
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "success": False
        })



def _disconnect_platform_impl(user_id: str, platform: str) -> str:
    """Internal implementation of disconnect_platform.
    
    Disconnects a platform and revokes access by deleting stored tokens.
    
    Args:
        user_id: The unique identifier for the user
        platform: The platform to disconnect (meta, google, shopify)
        
    Returns:
        JSON string containing result or error message
        
    Requirements: 8.3
    """
    if not user_id or not user_id.strip():
        return json.dumps({
            "error": "user_id is required and cannot be empty",
            "success": False
        })
    
    if not platform or not platform.strip():
        return json.dumps({
            "error": "platform is required and cannot be empty",
            "success": False
        })
    
    platform_lower = platform.lower().strip()
    if platform_lower not in SUPPORTED_PLATFORMS:
        return json.dumps({
            "error": f"Invalid platform '{platform}'. Supported platforms: {', '.join(SUPPORTED_PLATFORMS)}",
            "success": False
        })
    
    try:
        manager = get_connection_manager()
        # Use synchronous wrapper since the tool is synchronous
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            manager.disconnect_platform(platform_lower, user_id.strip())
        )
        
        if result:
            return json.dumps({
                "platform": platform_lower,
                "message": f"Successfully disconnected {platform_lower}",
                "success": True
            })
        else:
            return json.dumps({
                "platform": platform_lower,
                "message": f"No connection found for {platform_lower}",
                "success": True
            })
    except ValueError as e:
        return json.dumps({
            "error": str(e),
            "success": False
        })
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "success": False
        })


def _check_platform_health_impl(user_id: str, platform: str) -> str:
    """Internal implementation of check_platform_health.
    
    Checks the health of a platform connection including token validity.
    
    Args:
        user_id: The unique identifier for the user
        platform: The platform to check (meta, google, shopify)
        
    Returns:
        JSON string containing health status or error message
        
    Requirements: 8.4
    """
    if not user_id or not user_id.strip():
        return json.dumps({
            "error": "user_id is required and cannot be empty",
            "success": False
        })
    
    if not platform or not platform.strip():
        return json.dumps({
            "error": "platform is required and cannot be empty",
            "success": False
        })
    
    platform_lower = platform.lower().strip()
    if platform_lower not in SUPPORTED_PLATFORMS:
        return json.dumps({
            "error": f"Invalid platform '{platform}'. Supported platforms: {', '.join(SUPPORTED_PLATFORMS)}",
            "success": False
        })
    
    try:
        manager = get_connection_manager()
        # Use synchronous wrapper since the tool is synchronous
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        health = loop.run_until_complete(
            manager.check_connection_health(platform_lower, user_id.strip())
        )
        
        result = _connection_health_to_dict(health)
        result["success"] = True
        
        return json.dumps(result)
    except ValueError as e:
        return json.dumps({
            "error": str(e),
            "success": False
        })
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "success": False
        })



# Decorated tools for agent use
@function_tool
def list_connected_platforms(user_id: str) -> str:
    """List all connected platforms for a user.
    
    Use this tool to see which advertising and e-commerce platforms
    the user has connected to Credora. Returns connection status
    and last sync time for each platform.
    
    Args:
        user_id: The unique identifier for the user
        
    Returns:
        JSON string containing:
        - connections: List of connected platforms with details
        - total_count: Number of connected platforms
        - success: Whether the operation succeeded
        
    Requirements: 8.1, 8.5
    """
    return _list_connected_platforms_impl(user_id)


@function_tool
def initiate_platform_connection(
    user_id: str,
    platform: str,
    redirect_uri: str,
    shop: str = ""
) -> str:
    """Initiate OAuth connection for a platform.
    
    Use this tool to generate an OAuth authorization URL that the user
    can visit to connect their platform account. Supported platforms
    are Meta Ads, Google Ads, and Shopify.
    
    Args:
        user_id: The unique identifier for the user
        platform: The platform to connect (meta, google, shopify)
        redirect_uri: The OAuth callback URL
        shop: Shopify shop name (required for Shopify only, leave empty for other platforms)
        
    Returns:
        JSON string containing:
        - oauth_url: URL for user to authorize access
        - platform: The platform being connected
        - message: Instructions for the user
        - success: Whether the operation succeeded
        
    Requirements: 8.2
    """
    return _initiate_platform_connection_impl(user_id, platform, redirect_uri, shop if shop else None)


@function_tool
def disconnect_platform(user_id: str, platform: str) -> str:
    """Disconnect a platform and revoke access.
    
    Use this tool to disconnect a user's platform account from Credora.
    This will delete all stored tokens and revoke access to the platform.
    
    Args:
        user_id: The unique identifier for the user
        platform: The platform to disconnect (meta, google, shopify)
        
    Returns:
        JSON string containing:
        - platform: The platform that was disconnected
        - message: Result message
        - success: Whether the operation succeeded
        
    Requirements: 8.3
    """
    return _disconnect_platform_impl(user_id, platform)


@function_tool
def check_platform_health(user_id: str, platform: str) -> str:
    """Check the health of a platform connection.
    
    Use this tool to verify that a platform connection is healthy
    and the OAuth token is still valid. This helps identify
    connections that need re-authentication.
    
    Args:
        user_id: The unique identifier for the user
        platform: The platform to check (meta, google, shopify)
        
    Returns:
        JSON string containing:
        - platform: The platform checked
        - is_healthy: Whether the connection is healthy
        - token_valid: Whether the OAuth token is valid
        - last_checked: Timestamp of the health check
        - error_message: Error details if unhealthy
        - success: Whether the operation succeeded
        
    Requirements: 8.4
    """
    return _check_platform_health_impl(user_id, platform)


__all__ = [
    # Decorated tools for agent use
    "list_connected_platforms",
    "initiate_platform_connection",
    "disconnect_platform",
    "check_platform_health",
    # Internal implementations for testing
    "_list_connected_platforms_impl",
    "_initiate_platform_connection_impl",
    "_disconnect_platform_impl",
    "_check_platform_health_impl",
    # Utilities
    "get_connection_manager",
    "set_connection_manager",
    "SUPPORTED_PLATFORMS",
]
