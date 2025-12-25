"""Property-based tests for tool invocation logging.

**Feature: credora-cfo-agent, Property 7: Tool Invocation Logging**
**Validates: Requirements 3.6**

For any tool invocation, a corresponding log entry shall be created containing
tool_name, input_params, output, success status, and timestamp.
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime
from typing import Dict, Any

from credora.logging import (
    ToolLogger,
    log_tool_invocation,
    get_tool_logger,
    set_tool_logger,
    reset_tool_logger,
)
from credora.models import ToolLog


# Strategies for generating test data
tool_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_'),
    min_size=1,
    max_size=50,
)
agent_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_ '),
    min_size=0,
    max_size=50,
)
output_strategy = st.text(min_size=0, max_size=500)
param_value_strategy = st.one_of(
    st.text(min_size=0, max_size=100),
    st.integers(min_value=-1000000, max_value=1000000),
    st.floats(min_value=-1000000, max_value=1000000, allow_nan=False, allow_infinity=False),
    st.booleans(),
    st.none(),
)
input_params_strategy = st.dictionaries(
    keys=st.text(
        alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='_'),
        min_size=1,
        max_size=20,
    ),
    values=param_value_strategy,
    min_size=0,
    max_size=10,
)


class TestToolLoggerBasic:
    """Basic tests for ToolLogger functionality."""

    @settings(max_examples=100)
    @given(
        tool_name=tool_name_strategy,
        input_params=input_params_strategy,
        output=output_strategy,
        success=st.booleans(),
        agent_name=agent_name_strategy,
    )
    def test_log_creates_entry_with_all_fields(
        self,
        tool_name: str,
        input_params: Dict[str, Any],
        output: str,
        success: bool,
        agent_name: str,
    ):
        """
        **Feature: credora-cfo-agent, Property 7: Tool Invocation Logging**
        **Validates: Requirements 3.6**
        
        Log entry should contain tool_name, input_params, output, success, and timestamp.
        """
        logger = ToolLogger()
        
        before_log = datetime.now()
        log_entry = logger.log(
            tool_name=tool_name,
            input_params=input_params,
            output=output,
            success=success,
            agent_name=agent_name,
        )
        after_log = datetime.now()
        
        # Verify all required fields are present
        assert log_entry.tool_name == tool_name
        assert log_entry.input_params == input_params
        assert log_entry.output == output
        assert log_entry.success == success
        assert log_entry.agent_name == agent_name
        
        # Verify timestamp is set and reasonable
        assert log_entry.timestamp is not None
        assert before_log <= log_entry.timestamp <= after_log

    @settings(max_examples=100)
    @given(
        num_logs=st.integers(min_value=1, max_value=50),
    )
    def test_all_invocations_are_logged(
        self,
        num_logs: int,
    ):
        """
        **Feature: credora-cfo-agent, Property 7: Tool Invocation Logging**
        **Validates: Requirements 3.6**
        
        Every tool invocation should create a log entry.
        """
        logger = ToolLogger()
        
        for i in range(num_logs):
            logger.log(
                tool_name=f"tool_{i}",
                input_params={"index": i},
                output=f"output_{i}",
                success=True,
                agent_name="test_agent",
            )
        
        # Verify all logs were created
        assert logger.count() == num_logs
        
        # Verify we can retrieve all logs
        logs = logger.get_logs()
        assert len(logs) == num_logs


class TestLogToolInvocationDecorator:
    """
    **Feature: credora-cfo-agent, Property 7: Tool Invocation Logging**
    **Validates: Requirements 3.6**
    
    Tests for the log_tool_invocation decorator.
    """

    @settings(max_examples=100)
    @given(
        arg1=st.integers(min_value=-1000, max_value=1000),
        arg2=st.text(min_size=1, max_size=50),
    )
    def test_decorator_logs_successful_invocation(
        self,
        arg1: int,
        arg2: str,
    ):
        """Decorator should log successful tool invocations with all fields."""
        logger = ToolLogger()
        
        @log_tool_invocation(agent_name="test_agent", logger=logger)
        def test_tool(a: int, b: str) -> str:
            return f"{a}-{b}"
        
        result = test_tool(arg1, arg2)
        
        # Verify the function worked
        assert result == f"{arg1}-{arg2}"
        
        # Verify log was created
        assert logger.count() == 1
        
        log_entry = logger.get_latest(1)[0]
        assert log_entry.tool_name == "test_tool"
        assert log_entry.input_params["a"] == arg1
        assert log_entry.input_params["b"] == arg2
        assert log_entry.output == f"{arg1}-{arg2}"
        assert log_entry.success is True
        assert log_entry.agent_name == "test_agent"
        assert log_entry.timestamp is not None

    @settings(max_examples=100)
    @given(
        error_message=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
    )
    def test_decorator_logs_failed_invocation(
        self,
        error_message: str,
    ):
        """Decorator should log failed tool invocations with error info."""
        logger = ToolLogger()
        
        @log_tool_invocation(agent_name="test_agent", logger=logger)
        def failing_tool() -> str:
            raise RuntimeError(error_message)
        
        # Call should raise the exception
        with pytest.raises(RuntimeError):
            failing_tool()
        
        # But log should still be created
        assert logger.count() == 1
        
        log_entry = logger.get_latest(1)[0]
        assert log_entry.tool_name == "failing_tool"
        assert log_entry.success is False
        assert "Error" in log_entry.output
        assert log_entry.timestamp is not None

    @settings(max_examples=100)
    @given(
        num_calls=st.integers(min_value=1, max_value=20),
    )
    def test_decorator_logs_every_invocation(
        self,
        num_calls: int,
    ):
        """Decorator should create a log entry for every invocation."""
        logger = ToolLogger()
        
        @log_tool_invocation(agent_name="test_agent", logger=logger)
        def counter_tool(n: int) -> int:
            return n * 2
        
        for i in range(num_calls):
            counter_tool(i)
        
        # Verify all calls were logged
        assert logger.count() == num_calls
        
        # Verify each log has correct data
        logs = logger.get_logs()
        for i, log in enumerate(logs):
            # Logs are returned newest first
            expected_n = num_calls - 1 - i
            assert log.input_params["n"] == expected_n
            assert log.output == str(expected_n * 2)


class TestToolLoggerFiltering:
    """Tests for ToolLogger filtering capabilities."""

    @settings(max_examples=100)
    @given(
        num_success=st.integers(min_value=0, max_value=20),
        num_failure=st.integers(min_value=0, max_value=20),
    )
    def test_filter_by_success_status(
        self,
        num_success: int,
        num_failure: int,
    ):
        """Logger should correctly filter by success status."""
        logger = ToolLogger()
        
        # Log successful invocations
        for i in range(num_success):
            logger.log(
                tool_name="tool",
                input_params={},
                output="success",
                success=True,
            )
        
        # Log failed invocations
        for i in range(num_failure):
            logger.log(
                tool_name="tool",
                input_params={},
                output="failure",
                success=False,
            )
        
        # Filter by success
        success_logs = logger.get_logs(success_only=True)
        assert len(success_logs) == num_success
        assert all(l.success for l in success_logs)
        
        # Filter by failure
        failure_logs = logger.get_logs(success_only=False)
        assert len(failure_logs) == num_failure
        assert all(not l.success for l in failure_logs)

    @settings(max_examples=100)
    @given(
        tool_names=st.lists(
            st.text(
                alphabet=st.characters(whitelist_categories=('L', 'N')),
                min_size=1,
                max_size=20,
            ),
            min_size=1,
            max_size=5,
            unique=True,
        ),
    )
    def test_filter_by_tool_name(
        self,
        tool_names: list,
    ):
        """Logger should correctly filter by tool name."""
        logger = ToolLogger()
        
        # Log invocations for each tool
        for tool_name in tool_names:
            for i in range(3):
                logger.log(
                    tool_name=tool_name,
                    input_params={"i": i},
                    output=f"output_{i}",
                    success=True,
                )
        
        # Filter by each tool name
        for tool_name in tool_names:
            filtered_logs = logger.get_logs(tool_name=tool_name)
            assert len(filtered_logs) == 3
            assert all(l.tool_name == tool_name for l in filtered_logs)


class TestToolLoggerIntegration:
    """
    **Feature: credora-cfo-agent, Property 7: Tool Invocation Logging**
    **Validates: Requirements 3.6**
    
    Integration tests for tool logging.
    """

    @settings(max_examples=100)
    @given(
        operations=st.lists(
            st.tuples(
                st.text(
                    alphabet=st.characters(whitelist_categories=('L', 'N')),
                    min_size=1,
                    max_size=20,
                ),
                st.booleans(),
            ),
            min_size=1,
            max_size=30,
        ),
    )
    def test_log_entries_contain_all_required_fields(
        self,
        operations: list,
    ):
        """
        **Feature: credora-cfo-agent, Property 7: Tool Invocation Logging**
        **Validates: Requirements 3.6**
        
        Every log entry must contain tool_name, input_params, output, success, and timestamp.
        """
        logger = ToolLogger()
        
        for tool_name, success in operations:
            logger.log(
                tool_name=tool_name,
                input_params={"test": True},
                output="test output",
                success=success,
            )
        
        # Verify all logs have required fields
        logs = logger.get_logs()
        assert len(logs) == len(operations)
        
        for log in logs:
            # All required fields must be present and valid
            assert log.tool_name is not None and len(log.tool_name) > 0
            assert log.input_params is not None and isinstance(log.input_params, dict)
            assert log.output is not None and isinstance(log.output, str)
            assert log.success is not None and isinstance(log.success, bool)
            assert log.timestamp is not None and isinstance(log.timestamp, datetime)

    @settings(max_examples=100)
    @given(
        num_invocations=st.integers(min_value=1, max_value=50),
    )
    def test_timestamps_are_chronological(
        self,
        num_invocations: int,
    ):
        """Log timestamps should be in chronological order."""
        logger = ToolLogger()
        
        for i in range(num_invocations):
            logger.log(
                tool_name="tool",
                input_params={"i": i},
                output=str(i),
                success=True,
            )
        
        # Get logs (newest first)
        logs = logger.get_logs()
        
        # Verify timestamps are in reverse chronological order
        for i in range(len(logs) - 1):
            assert logs[i].timestamp >= logs[i + 1].timestamp
