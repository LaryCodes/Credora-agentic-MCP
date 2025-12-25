"""
Meta Ads MCP Server Entry Point.

Run the Meta Ads MCP server for Facebook/Instagram advertising integration.

Usage:
    python -m credora.mcp_servers.run_meta_ads [--log-level LEVEL]

Environment Variables:
    META_APP_ID: Meta App ID for OAuth
    META_APP_SECRET: Meta App Secret for OAuth
    META_REDIRECT_URI: OAuth redirect URI
    TOKEN_ENCRYPTION_KEY: Key for encrypting stored tokens
    LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR)

Requirements: 1.1, 3.6
"""

import os
import sys

# Add parent directory to path for module imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from credora.mcp_servers.connection_manager import ConnectionManager
from credora.mcp_servers.meta_ads import MetaAdsMCPServer
from credora.mcp_servers.run_base import run_mcp_server
from credora.mcp_servers.token_store import TokenStore


def main() -> None:
    """Main entry point for Meta Ads MCP server."""
    # Initialize token store and connection manager
    # TokenStore uses the default encryption from security module
    token_store = TokenStore()
    connection_manager = ConnectionManager(token_store=token_store)
    
    # Run the server
    run_mcp_server(
        MetaAdsMCPServer,
        connection_manager=connection_manager,
    )


if __name__ == "__main__":
    main()
