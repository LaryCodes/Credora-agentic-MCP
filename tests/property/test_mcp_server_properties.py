"""Property-based tests for MCP Server base functionality.

**Feature: platform-mcp-servers**
"""

import pytest
from hypothesis import given, strategies as st, settings

from credora.mcp_servers.base import BaseMCPServer, Tool
from credora.mcp_servers.errors import MCPError, MCPErrorType


# Strategy for generating valid tool names (non-empty, alphanumeric with underscores)
tool_name_strategy = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz_0123456789"),
    min_size=1,
    max_size=50,
).filter(lambda x: x[0].isalpha())

# Strategy for generating tool descriptions
tool_description_strategy = st.text(min_size=1, max_size=200).filter(lambda x: x.strip() != "")

# Strategy for generating simple input schemas
input_schema_strategy = st.fixed_dictionaries({
    "type": st.just("object"),
    "properties": st.dictionaries(
        keys=st.text(min_size=1, max_size=20).filter(lambda x: x.isidentifier()),
        values=st.fixed_dictionaries({
            "type": st.sampled_from(["string", "number", "boolean", "integer"]),
        }),
        min_size=0,
        max_size=5,
    ),
})


class MockMCPServer(BaseMCPServer):
    """Concrete implementation of BaseMCPServer for testing."""
    
    name = "test-server"
    version = "1.0.0"
    
    def __init__(self, tools_to_register=None):
        """Initialize with optional tools to register."""
        self._tools_to_register = tools_to_register or []
        super().__init__()
    
    def _register_tools(self) -> None:
        """Register tools provided during initialization."""
        for tool_def in self._tools_to_register:
            self.register_tool(
                name=tool_def["name"],
                description=tool_def["description"],
                input_schema=tool_def["input_schema"],
                handler=tool_def["handler"],
            )


class TestMCPToolExposure:
    """
    **Feature: platform-mcp-servers, Property 1: MCP Tool Exposure**
    **Validates: Requirements 1.2**
    
    For any MCP server instance, when started, the server shall expose
    a non-empty list of tools via the standard MCP protocol.
    """

    @settings(max_examples=100)
    @given(
        tool_names=st.lists(
            tool_name_strategy,
            min_size=1,
            max_size=10,
            unique=True,
        ),
    )
    @pytest.mark.asyncio
    async def test_server_exposes_registered_tools(self, tool_names):
        """Server should expose all registered tools via list_tools."""
        # Create tool definitions
        async def dummy_handler(**kwargs):
            return {"status": "ok"}
        
        tools_to_register = [
            {
                "name": name,
                "description": f"Description for {name}",
                "input_schema": {"type": "object", "properties": {}},
                "handler": dummy_handler,
            }
            for name in tool_names
        ]
        
        # Create server with tools
        server = MockMCPServer(tools_to_register=tools_to_register)
        
        # List tools
        tools = await server.list_tools()
        
        # Verify all tools are exposed
        assert len(tools) == len(tool_names)
        
        # Verify tool names match
        exposed_names = {tool["name"] for tool in tools}
        assert exposed_names == set(tool_names)

    @settings(max_examples=100)
    @given(
        tool_name=tool_name_strategy,
        tool_description=tool_description_strategy,
        input_schema=input_schema_strategy,
    )
    @pytest.mark.asyncio
    async def test_tool_definition_structure(
        self, tool_name, tool_description, input_schema
    ):
        """Each tool definition should have name, description, and inputSchema."""
        async def dummy_handler(**kwargs):
            return {"status": "ok"}
        
        tools_to_register = [
            {
                "name": tool_name,
                "description": tool_description,
                "input_schema": input_schema,
                "handler": dummy_handler,
            }
        ]
        
        server = MockMCPServer(tools_to_register=tools_to_register)
        tools = await server.list_tools()
        
        assert len(tools) == 1
        tool = tools[0]
        
        # Verify structure
        assert "name" in tool
        assert "description" in tool
        assert "inputSchema" in tool
        
        # Verify values
        assert tool["name"] == tool_name
        assert tool["description"] == tool_description
        assert tool["inputSchema"] == input_schema

    @settings(max_examples=100)
    @given(
        tool_names=st.lists(
            tool_name_strategy,
            min_size=1,
            max_size=10,
            unique=True,
        ),
    )
    @pytest.mark.asyncio
    async def test_tools_list_via_handle_request(self, tool_names):
        """tools/list request should return all registered tools."""
        async def dummy_handler(**kwargs):
            return {"status": "ok"}
        
        tools_to_register = [
            {
                "name": name,
                "description": f"Description for {name}",
                "input_schema": {"type": "object", "properties": {}},
                "handler": dummy_handler,
            }
            for name in tool_names
        ]
        
        server = MockMCPServer(tools_to_register=tools_to_register)
        
        # Make tools/list request
        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 1,
        }
        
        response = await server.handle_request(request)
        
        # Verify response structure
        assert "result" in response
        assert "tools" in response["result"]
        
        # Verify all tools are listed
        tools = response["result"]["tools"]
        assert len(tools) == len(tool_names)
        
        exposed_names = {tool["name"] for tool in tools}
        assert exposed_names == set(tool_names)

    @pytest.mark.asyncio
    async def test_server_with_no_tools_returns_empty_list(self):
        """Server with no registered tools should return empty list."""
        server = MockMCPServer(tools_to_register=[])
        
        tools = await server.list_tools()
        
        assert tools == []

    @settings(max_examples=100)
    @given(
        tool_name=tool_name_strategy,
    )
    @pytest.mark.asyncio
    async def test_has_tool_returns_true_for_registered_tool(self, tool_name):
        """has_tool should return True for registered tools."""
        async def dummy_handler(**kwargs):
            return {"status": "ok"}
        
        tools_to_register = [
            {
                "name": tool_name,
                "description": "Test tool",
                "input_schema": {"type": "object", "properties": {}},
                "handler": dummy_handler,
            }
        ]
        
        server = MockMCPServer(tools_to_register=tools_to_register)
        
        assert server.has_tool(tool_name) is True

    @settings(max_examples=100)
    @given(
        registered_name=tool_name_strategy,
        query_name=tool_name_strategy,
    )
    @pytest.mark.asyncio
    async def test_has_tool_returns_false_for_unregistered_tool(
        self, registered_name, query_name
    ):
        """has_tool should return False for unregistered tools."""
        # Skip if names happen to match
        if registered_name == query_name:
            return
        
        async def dummy_handler(**kwargs):
            return {"status": "ok"}
        
        tools_to_register = [
            {
                "name": registered_name,
                "description": "Test tool",
                "input_schema": {"type": "object", "properties": {}},
                "handler": dummy_handler,
            }
        ]
        
        server = MockMCPServer(tools_to_register=tools_to_register)
        
        assert server.has_tool(query_name) is False

    @settings(max_examples=100)
    @given(
        tool_names=st.lists(
            tool_name_strategy,
            min_size=1,
            max_size=10,
            unique=True,
        ),
    )
    @pytest.mark.asyncio
    async def test_get_tool_count_matches_registered_tools(self, tool_names):
        """get_tool_count should return the number of registered tools."""
        async def dummy_handler(**kwargs):
            return {"status": "ok"}
        
        tools_to_register = [
            {
                "name": name,
                "description": f"Description for {name}",
                "input_schema": {"type": "object", "properties": {}},
                "handler": dummy_handler,
            }
            for name in tool_names
        ]
        
        server = MockMCPServer(tools_to_register=tools_to_register)
        
        assert server.get_tool_count() == len(tool_names)



class TestToolResponseConsistency:
    """
    **Feature: platform-mcp-servers, Property 2: Tool Response Consistency**
    **Validates: Requirements 1.4**
    
    For any MCP tool invocation with valid parameters, the response shall be
    valid JSON containing either a "result" or "error" field.
    """

    @settings(max_examples=100)
    @given(
        tool_name=tool_name_strategy,
        return_value=st.one_of(
            st.none(),
            st.booleans(),
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.text(max_size=100),
            st.dictionaries(
                keys=st.text(min_size=1, max_size=20).filter(lambda x: x.isidentifier()),
                values=st.text(max_size=50),
                max_size=5,
            ),
            st.lists(st.integers(), max_size=10),
        ),
    )
    @pytest.mark.asyncio
    async def test_successful_tool_call_returns_result(self, tool_name, return_value):
        """Successful tool calls should return response with 'result' key."""
        async def handler(**kwargs):
            return return_value
        
        tools_to_register = [
            {
                "name": tool_name,
                "description": "Test tool",
                "input_schema": {"type": "object", "properties": {}},
                "handler": handler,
            }
        ]
        
        server = MockMCPServer(tools_to_register=tools_to_register)
        
        response = await server.call_tool(tool_name, {})
        
        # Response must have either 'result' or 'error'
        assert "result" in response or "error" in response
        
        # For successful calls, should have 'result'
        assert "result" in response
        assert response["result"] == return_value

    @settings(max_examples=100)
    @given(
        tool_name=tool_name_strategy,
        error_message=st.text(min_size=1, max_size=100).filter(lambda x: x.strip() != ""),
    )
    @pytest.mark.asyncio
    async def test_mcp_error_returns_error_response(self, tool_name, error_message):
        """Tool calls that raise MCPError should return response with 'error' key."""
        async def handler(**kwargs):
            raise MCPError(
                error_type=MCPErrorType.API_ERROR,
                message=error_message,
                recoverable=True,
            )
        
        tools_to_register = [
            {
                "name": tool_name,
                "description": "Test tool",
                "input_schema": {"type": "object", "properties": {}},
                "handler": handler,
            }
        ]
        
        server = MockMCPServer(tools_to_register=tools_to_register)
        
        response = await server.call_tool(tool_name, {})
        
        # Response must have 'error' key
        assert "error" in response
        assert "result" not in response
        
        # Error should have required fields
        error = response["error"]
        assert "error_type" in error
        assert "message" in error
        assert "recoverable" in error

    @settings(max_examples=100)
    @given(
        tool_name=tool_name_strategy,
        error_message=st.text(min_size=1, max_size=100).filter(lambda x: x.strip() != ""),
    )
    @pytest.mark.asyncio
    async def test_generic_exception_returns_error_response(self, tool_name, error_message):
        """Tool calls that raise generic exceptions should return error response."""
        async def handler(**kwargs):
            raise ValueError(error_message)
        
        tools_to_register = [
            {
                "name": tool_name,
                "description": "Test tool",
                "input_schema": {"type": "object", "properties": {}},
                "handler": handler,
            }
        ]
        
        server = MockMCPServer(tools_to_register=tools_to_register)
        
        response = await server.call_tool(tool_name, {})
        
        # Response must have 'error' key
        assert "error" in response
        assert "result" not in response

    @settings(max_examples=100)
    @given(
        nonexistent_name=tool_name_strategy,
    )
    @pytest.mark.asyncio
    async def test_nonexistent_tool_returns_error(self, nonexistent_name):
        """Calling a nonexistent tool should return error response."""
        server = MockMCPServer(tools_to_register=[])
        
        response = await server.call_tool(nonexistent_name, {})
        
        # Response must have 'error' key
        assert "error" in response
        assert "result" not in response
        
        # Error should indicate tool not found
        error = response["error"]
        assert error["error_type"] == MCPErrorType.NOT_FOUND.value

    @settings(max_examples=100)
    @given(
        tool_name=tool_name_strategy,
        arguments=st.dictionaries(
            keys=st.text(min_size=1, max_size=20).filter(lambda x: x.isidentifier()),
            values=st.one_of(
                st.none(),
                st.booleans(),
                st.integers(),
                st.text(max_size=50),
            ),
            max_size=5,
        ),
    )
    @pytest.mark.asyncio
    async def test_tool_call_via_handle_request_returns_valid_json_rpc(
        self, tool_name, arguments
    ):
        """tools/call via handle_request should return valid JSON-RPC response."""
        async def handler(**kwargs):
            return {"received": kwargs}
        
        tools_to_register = [
            {
                "name": tool_name,
                "description": "Test tool",
                "input_schema": {"type": "object", "properties": {}},
                "handler": handler,
            }
        ]
        
        server = MockMCPServer(tools_to_register=tools_to_register)
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
            "id": 1,
        }
        
        response = await server.handle_request(request)
        
        # Response must be valid JSON-RPC
        assert "jsonrpc" in response
        assert response["jsonrpc"] == "2.0"
        assert "id" in response
        
        # Response must have either 'result' or 'error'
        assert "result" in response or "error" in response

    @settings(max_examples=100)
    @given(
        request_id=st.one_of(
            st.integers(),
            st.text(min_size=1, max_size=50),
            st.none(),
        ),
    )
    @pytest.mark.asyncio
    async def test_response_preserves_request_id(self, request_id):
        """Response should preserve the request ID."""
        async def handler(**kwargs):
            return {"status": "ok"}
        
        tools_to_register = [
            {
                "name": "test_tool",
                "description": "Test tool",
                "input_schema": {"type": "object", "properties": {}},
                "handler": handler,
            }
        ]
        
        server = MockMCPServer(tools_to_register=tools_to_register)
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "test_tool",
                "arguments": {},
            },
            "id": request_id,
        }
        
        response = await server.handle_request(request)
        
        assert response["id"] == request_id

    @pytest.mark.asyncio
    async def test_invalid_jsonrpc_version_returns_error(self):
        """Invalid JSON-RPC version should return error."""
        server = MockMCPServer(tools_to_register=[])
        
        request = {
            "jsonrpc": "1.0",  # Invalid version
            "method": "tools/list",
            "id": 1,
        }
        
        response = await server.handle_request(request)
        
        assert "error" in response
        assert response["error"]["code"] == -32600

    @pytest.mark.asyncio
    async def test_unknown_method_returns_error(self):
        """Unknown method should return method not found error."""
        server = MockMCPServer(tools_to_register=[])
        
        request = {
            "jsonrpc": "2.0",
            "method": "unknown/method",
            "id": 1,
        }
        
        response = await server.handle_request(request)
        
        assert "error" in response
        assert response["error"]["code"] == -32601

    @pytest.mark.asyncio
    async def test_tools_call_without_params_returns_error(self):
        """tools/call without params should return error."""
        server = MockMCPServer(tools_to_register=[])
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "id": 1,
        }
        
        response = await server.handle_request(request)
        
        assert "error" in response
        assert response["error"]["code"] == -32602

    @pytest.mark.asyncio
    async def test_tools_call_without_name_returns_error(self):
        """tools/call without tool name should return error."""
        server = MockMCPServer(tools_to_register=[])
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "arguments": {},
            },
            "id": 1,
        }
        
        response = await server.handle_request(request)
        
        assert "error" in response
        assert response["error"]["code"] == -32602

    @pytest.mark.asyncio
    async def test_initialize_returns_server_info(self):
        """initialize method should return server info."""
        server = MockMCPServer(tools_to_register=[])
        
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": 1,
        }
        
        response = await server.handle_request(request)
        
        assert "result" in response
        result = response["result"]
        assert "protocolVersion" in result
        assert "capabilities" in result
        assert "serverInfo" in result
        assert result["serverInfo"]["name"] == "test-server"
