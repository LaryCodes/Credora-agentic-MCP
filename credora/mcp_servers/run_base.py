"""
Base MCP Server Runner.

Provides common functionality for running MCP servers via stdio transport.

Requirements: 1.1, 1.5
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from typing import Optional, Type

from credora.mcp_servers.base import BaseMCPServer, MCPRequest, MCPResponse


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Set up logging for the MCP server.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        
    Returns:
        Configured logger instance
    """
    # Log to stderr to keep stdout clean for MCP protocol
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )
    return logging.getLogger("mcp_server")


def parse_common_args() -> argparse.Namespace:
    """Parse common command-line arguments for MCP servers.
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Run an MCP server for platform integration"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default=os.environ.get("LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )
    parser.add_argument(
        "--token-store-path",
        type=str,
        default=os.environ.get("TOKEN_STORE_PATH", ".credora/tokens"),
        help="Path to token storage directory",
    )
    return parser.parse_args()


async def read_request(reader: asyncio.StreamReader) -> Optional[dict]:
    """Read a JSON-RPC request from stdin.
    
    Args:
        reader: Async stream reader for stdin
        
    Returns:
        Parsed request dictionary or None if EOF
    """
    try:
        line = await reader.readline()
        if not line:
            return None
        return json.loads(line.decode("utf-8").strip())
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {e}"}
    except Exception as e:
        return {"error": f"Read error: {e}"}


def write_response(response: dict) -> None:
    """Write a JSON-RPC response to stdout.
    
    Args:
        response: Response dictionary to write
    """
    output = json.dumps(response) + "\n"
    sys.stdout.write(output)
    sys.stdout.flush()


async def run_server(server: BaseMCPServer, logger: logging.Logger) -> None:
    """Run the MCP server main loop.
    
    Args:
        server: The MCP server instance to run
        logger: Logger for server events
    """
    logger.info(f"Starting {server.name} MCP server v{server.version}")
    
    # Create async reader for stdin
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    
    loop = asyncio.get_event_loop()
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    
    logger.info("Server ready, waiting for requests...")
    
    while True:
        request = await read_request(reader)
        
        if request is None:
            logger.info("EOF received, shutting down")
            break
        
        if "error" in request:
            write_response({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": request["error"],
                },
                "id": None,
            })
            continue
        
        logger.debug(f"Received request: {request.get('method', 'unknown')}")
        
        try:
            response = await server.handle_request(request)
            write_response(response)
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            write_response({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}",
                },
                "id": request.get("id"),
            })


def run_mcp_server(server_class: Type[BaseMCPServer], **kwargs) -> None:
    """Main entry point for running an MCP server.
    
    Args:
        server_class: The MCP server class to instantiate
        **kwargs: Additional arguments to pass to the server constructor
    """
    args = parse_common_args()
    logger = setup_logging(args.log_level)
    
    try:
        server = server_class(**kwargs)
        asyncio.run(run_server(server, logger))
    except KeyboardInterrupt:
        logger.info("Server interrupted, shutting down")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
