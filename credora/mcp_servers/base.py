"""
Base MCP Server implementation.

This module provides the abstract base class for all platform MCP servers.

Requirements: 1.2, 1.4, 6.1, 6.2, 6.3
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from credora.mcp_servers.errors import MCPError, MCPErrorType, RetryConfig


@dataclass
class Tool:
    """Represents an MCP tool definition.
    
    Attributes:
        name: Unique identifier for the tool
        description: Human-readable description of what the tool does
        input_schema: JSON Schema defining the tool's input parameters
        handler: Async function that implements the tool
    """
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable[..., Any]


@dataclass
class ToolResult:
    """Result from a tool invocation.
    
    Attributes:
        content: The result content (can be any JSON-serializable value)
        is_error: Whether this result represents an error
    """
    content: Any
    is_error: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "content": self.content,
            "isError": self.is_error,
        }


@dataclass
class MCPRequest:
    """Represents an incoming MCP JSON-RPC request.
    
    Attributes:
        jsonrpc: JSON-RPC version (should be "2.0")
        method: The method being called
        params: Optional parameters for the method
        id: Request identifier for response correlation
    """
    jsonrpc: str
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPRequest":
        """Create MCPRequest from dictionary."""
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            method=data.get("method", ""),
            params=data.get("params"),
            id=data.get("id"),
        )


@dataclass
class MCPResponse:
    """Represents an MCP JSON-RPC response.
    
    Attributes:
        jsonrpc: JSON-RPC version (always "2.0")
        result: The result if successful
        error: Error information if failed
        id: Request identifier for response correlation
    """
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        response: Dict[str, Any] = {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
        }
        if self.error is not None:
            response["error"] = self.error
        else:
            response["result"] = self.result
        return response


class BaseMCPServer(ABC):
    """
    Base class for platform MCP servers.
    
    Provides common functionality for MCP protocol handling,
    tool registration, and request/response management.
    
    Subclasses must implement _register_tools() to define their tools.
    
    Requirements: 1.2, 1.4
    """
    
    name: str = "base"
    version: str = "1.0.0"
    
    def __init__(self, retry_config: Optional[RetryConfig] = None):
        """Initialize the MCP server.
        
        Args:
            retry_config: Optional retry configuration for API calls
        """
        self._tools: Dict[str, Tool] = {}
        self._retry_config = retry_config or RetryConfig()
        self._register_tools()
    
    @abstractmethod
    def _register_tools(self) -> None:
        """Register tools for this server.
        
        Subclasses must implement this method to register their tools
        using the register_tool() method.
        """
        pass
    
    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        handler: Callable[..., Any],
    ) -> None:
        """Register a tool with this server.
        
        Args:
            name: Unique identifier for the tool
            description: Human-readable description
            input_schema: JSON Schema for input parameters
            handler: Async function implementing the tool
        """
        self._tools[name] = Tool(
            name=name,
            description=description,
            input_schema=input_schema,
            handler=handler,
        )
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List all tools exposed by this MCP server.
        
        Returns:
            List of tool definitions in MCP format
            
        Requirements: 1.2
        """
        tools = []
        for tool in self._tools.values():
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema,
            })
        return tools
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool by name with the given arguments.
        
        Args:
            name: Name of the tool to call
            arguments: Arguments to pass to the tool
            
        Returns:
            Dictionary containing either "result" or "error" key
            
        Requirements: 1.4
        """
        if name not in self._tools:
            return {
                "error": {
                    "error_type": MCPErrorType.NOT_FOUND.value,
                    "message": f"Tool not found: {name}",
                    "recoverable": False,
                }
            }
        
        tool = self._tools[name]
        
        try:
            result = await tool.handler(**arguments)
            return {"result": result}
        except MCPError as e:
            return {"error": e.to_dict()}
        except Exception as e:
            return {
                "error": {
                    "error_type": MCPErrorType.API_ERROR.value,
                    "message": str(e),
                    "recoverable": True,
                }
            }
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an incoming MCP JSON-RPC request.
        
        Args:
            request: The JSON-RPC request dictionary
            
        Returns:
            JSON-RPC response dictionary with either "result" or "error"
            
        Requirements: 1.4
        """
        try:
            mcp_request = MCPRequest.from_dict(request)
        except Exception as e:
            return MCPResponse(
                error={
                    "code": -32700,
                    "message": f"Parse error: {str(e)}",
                },
                id=request.get("id"),
            ).to_dict()
        
        # Validate JSON-RPC version
        if mcp_request.jsonrpc != "2.0":
            return MCPResponse(
                error={
                    "code": -32600,
                    "message": "Invalid Request: jsonrpc must be '2.0'",
                },
                id=mcp_request.id,
            ).to_dict()
        
        # Route to appropriate handler
        if mcp_request.method == "tools/list":
            tools = await self.list_tools()
            return MCPResponse(
                result={"tools": tools},
                id=mcp_request.id,
            ).to_dict()
        
        elif mcp_request.method == "tools/call":
            if not mcp_request.params:
                return MCPResponse(
                    error={
                        "code": -32602,
                        "message": "Invalid params: 'name' and 'arguments' required",
                    },
                    id=mcp_request.id,
                ).to_dict()
            
            tool_name = mcp_request.params.get("name", "")
            arguments = mcp_request.params.get("arguments", {})
            
            if not tool_name:
                return MCPResponse(
                    error={
                        "code": -32602,
                        "message": "Invalid params: 'name' is required",
                    },
                    id=mcp_request.id,
                ).to_dict()
            
            result = await self.call_tool(tool_name, arguments)
            
            if "error" in result:
                return MCPResponse(
                    error={
                        "code": -32000,
                        "message": result["error"].get("message", "Tool execution failed"),
                        "data": result["error"],
                    },
                    id=mcp_request.id,
                ).to_dict()
            
            return MCPResponse(
                result=result.get("result"),
                id=mcp_request.id,
            ).to_dict()
        
        elif mcp_request.method == "initialize":
            return MCPResponse(
                result={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": False},
                    },
                    "serverInfo": {
                        "name": self.name,
                        "version": self.version,
                    },
                },
                id=mcp_request.id,
            ).to_dict()
        
        else:
            return MCPResponse(
                error={
                    "code": -32601,
                    "message": f"Method not found: {mcp_request.method}",
                },
                id=mcp_request.id,
            ).to_dict()
    
    def get_tool_count(self) -> int:
        """Get the number of registered tools.
        
        Returns:
            Number of tools registered with this server
        """
        return len(self._tools)
    
    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered.
        
        Args:
            name: Name of the tool to check
            
        Returns:
            True if the tool exists, False otherwise
        """
        return name in self._tools
