"""Property-based tests for error resilience.

**Feature: credora-cfo-agent, Property 6: Error Resilience**
**Validates: Requirements 3.5**

For any tool that encounters an error during execution, the tool shall return
an error message string and the agent session shall remain active and responsive.
"""

import pytest
from hypothesis import given, strategies as st, settings
from typing import Any, Callable

from credora.errors import (
    ErrorType,
    ErrorResponse,
    create_error_response,
    error_wrapper,
    safe_tool_execution,
)


# Strategies for generating test data
error_type_strategy = st.sampled_from([e.value for e in ErrorType])
message_strategy = st.text(min_size=1, max_size=200).filter(lambda x: x.strip())
suggested_action_strategy = st.text(min_size=0, max_size=200)


class TestErrorResponseCreation:
    """Tests for ErrorResponse dataclass creation and validation."""

    @settings(max_examples=100)
    @given(
        error_type=error_type_strategy,
        message=message_strategy,
        recoverable=st.booleans(),
        suggested_action=suggested_action_strategy,
    )
    def test_error_response_creation_always_succeeds_with_valid_inputs(
        self,
        error_type: str,
        message: str,
        recoverable: bool,
        suggested_action: str,
    ):
        """ErrorResponse should be creatable with any valid inputs."""
        error = ErrorResponse(
            error_type=error_type,
            message=message,
            recoverable=recoverable,
            suggested_action=suggested_action,
        )
        
        assert error.error_type == error_type
        assert error.message == message
        assert error.recoverable == recoverable
        assert error.suggested_action == suggested_action
        assert error.timestamp is not None

    @settings(max_examples=100)
    @given(
        error_type=error_type_strategy,
        message=message_strategy,
    )
    def test_error_response_to_string_always_returns_string(
        self,
        error_type: str,
        message: str,
    ):
        """ErrorResponse.to_string() should always return a non-empty string."""
        error = ErrorResponse(error_type=error_type, message=message)
        result = error.to_string()
        
        assert isinstance(result, str)
        assert len(result) > 0
        assert error_type in result
        assert message in result

    @settings(max_examples=100)
    @given(
        error_type=error_type_strategy,
        message=message_strategy,
        recoverable=st.booleans(),
        suggested_action=suggested_action_strategy,
    )
    def test_error_response_to_dict_always_returns_dict(
        self,
        error_type: str,
        message: str,
        recoverable: bool,
        suggested_action: str,
    ):
        """ErrorResponse.to_dict() should always return a valid dictionary."""
        error = ErrorResponse(
            error_type=error_type,
            message=message,
            recoverable=recoverable,
            suggested_action=suggested_action,
        )
        result = error.to_dict()
        
        assert isinstance(result, dict)
        assert result["error_type"] == error_type
        assert result["message"] == message
        assert result["recoverable"] == recoverable
        assert result["suggested_action"] == suggested_action
        assert "timestamp" in result


class TestErrorWrapper:
    """
    **Feature: credora-cfo-agent, Property 6: Error Resilience**
    **Validates: Requirements 3.5**
    
    Tests that the error_wrapper decorator ensures tools return error messages
    instead of raising exceptions.
    """

    @settings(max_examples=100)
    @given(
        error_message=message_strategy,
    )
    def test_error_wrapper_catches_value_error_returns_string(
        self,
        error_message: str,
    ):
        """error_wrapper should catch ValueError and return error string."""
        @error_wrapper()
        def failing_tool() -> str:
            raise ValueError(error_message)
        
        result = failing_tool()
        
        # Should return a string, not raise an exception
        assert isinstance(result, str)
        assert "Error" in result
        assert "validation" in result.lower()

    @settings(max_examples=100)
    @given(
        error_message=message_strategy,
    )
    def test_error_wrapper_catches_connection_error_returns_string(
        self,
        error_message: str,
    ):
        """error_wrapper should catch ConnectionError and return error string."""
        @error_wrapper()
        def failing_tool() -> str:
            raise ConnectionError(error_message)
        
        result = failing_tool()
        
        # Should return a string, not raise an exception
        assert isinstance(result, str)
        assert "Error" in result
        assert "connection" in result.lower()

    @settings(max_examples=100)
    @given(
        error_message=message_strategy,
    )
    def test_error_wrapper_catches_timeout_error_returns_string(
        self,
        error_message: str,
    ):
        """error_wrapper should catch TimeoutError and return error string."""
        @error_wrapper()
        def failing_tool() -> str:
            raise TimeoutError(error_message)
        
        result = failing_tool()
        
        # Should return a string, not raise an exception
        assert isinstance(result, str)
        assert "Error" in result
        assert "timeout" in result.lower()

    @settings(max_examples=100)
    @given(
        error_message=message_strategy,
    )
    def test_error_wrapper_catches_permission_error_returns_string(
        self,
        error_message: str,
    ):
        """error_wrapper should catch PermissionError and return error string."""
        @error_wrapper()
        def failing_tool() -> str:
            raise PermissionError(error_message)
        
        result = failing_tool()
        
        # Should return a string, not raise an exception
        assert isinstance(result, str)
        assert "Error" in result
        assert "auth" in result.lower()

    @settings(max_examples=100)
    @given(
        error_message=message_strategy,
    )
    def test_error_wrapper_catches_generic_exception_returns_string(
        self,
        error_message: str,
    ):
        """error_wrapper should catch any Exception and return error string."""
        @error_wrapper()
        def failing_tool() -> str:
            raise RuntimeError(error_message)
        
        result = failing_tool()
        
        # Should return a string, not raise an exception
        assert isinstance(result, str)
        assert "Error" in result

    @settings(max_examples=100)
    @given(
        return_value=st.text(min_size=1, max_size=100),
    )
    def test_error_wrapper_passes_through_successful_results(
        self,
        return_value: str,
    ):
        """error_wrapper should pass through successful results unchanged."""
        @error_wrapper()
        def successful_tool() -> str:
            return return_value
        
        result = successful_tool()
        
        assert result == return_value

    @settings(max_examples=100)
    @given(
        arg1=st.integers(),
        arg2=st.text(min_size=1, max_size=50),
    )
    def test_error_wrapper_preserves_function_arguments(
        self,
        arg1: int,
        arg2: str,
    ):
        """error_wrapper should correctly pass arguments to wrapped function."""
        @error_wrapper()
        def tool_with_args(a: int, b: str) -> str:
            return f"{a}-{b}"
        
        result = tool_with_args(arg1, arg2)
        
        assert result == f"{arg1}-{arg2}"


class TestSafeToolExecution:
    """
    **Feature: credora-cfo-agent, Property 6: Error Resilience**
    **Validates: Requirements 3.5**
    
    Tests that safe_tool_execution ensures tools return error messages
    instead of raising exceptions.
    """

    @settings(max_examples=100)
    @given(
        error_message=message_strategy,
    )
    def test_safe_tool_execution_catches_exceptions(
        self,
        error_message: str,
    ):
        """safe_tool_execution should catch exceptions and return error string."""
        def failing_tool() -> str:
            raise RuntimeError(error_message)
        
        result = safe_tool_execution(failing_tool)
        
        # Should return a string, not raise an exception
        assert isinstance(result, str)
        assert "Error" in result

    @settings(max_examples=100)
    @given(
        return_value=st.text(min_size=1, max_size=100),
    )
    def test_safe_tool_execution_passes_through_successful_results(
        self,
        return_value: str,
    ):
        """safe_tool_execution should pass through successful results."""
        def successful_tool() -> str:
            return return_value
        
        result = safe_tool_execution(successful_tool)
        
        assert result == return_value

    @settings(max_examples=100)
    @given(
        default_return=st.text(min_size=1, max_size=100),
    )
    def test_safe_tool_execution_uses_default_return_on_error(
        self,
        default_return: str,
    ):
        """safe_tool_execution should use default_return when error occurs."""
        def failing_tool() -> str:
            raise RuntimeError("test error")
        
        result = safe_tool_execution(failing_tool, default_return=default_return)
        
        assert result == default_return


class TestErrorResilienceIntegration:
    """
    **Feature: credora-cfo-agent, Property 6: Error Resilience**
    **Validates: Requirements 3.5**
    
    Integration tests verifying that error handling keeps the system responsive.
    """

    @settings(max_examples=100)
    @given(
        num_failures=st.integers(min_value=1, max_value=10),
    )
    def test_multiple_failures_do_not_crash_system(
        self,
        num_failures: int,
    ):
        """Multiple tool failures should not crash the system."""
        @error_wrapper()
        def failing_tool(iteration: int) -> str:
            raise RuntimeError(f"Failure {iteration}")
        
        results = []
        for i in range(num_failures):
            result = failing_tool(i)
            results.append(result)
        
        # All results should be error strings
        assert len(results) == num_failures
        assert all(isinstance(r, str) for r in results)
        assert all("Error" in r for r in results)

    @settings(max_examples=100)
    @given(
        success_indices=st.lists(
            st.integers(min_value=0, max_value=9),
            min_size=0,
            max_size=10,
            unique=True,
        ),
    )
    def test_mixed_success_and_failure_handled_correctly(
        self,
        success_indices: list,
    ):
        """System should handle mixed success and failure correctly."""
        @error_wrapper()
        def mixed_tool(index: int, should_succeed: bool) -> str:
            if should_succeed:
                return f"Success {index}"
            raise RuntimeError(f"Failure {index}")
        
        results = []
        for i in range(10):
            should_succeed = i in success_indices
            result = mixed_tool(i, should_succeed)
            results.append((i, result, should_succeed))
        
        # Verify results match expectations
        for i, result, should_succeed in results:
            assert isinstance(result, str)
            if should_succeed:
                assert f"Success {i}" == result
            else:
                assert "Error" in result
