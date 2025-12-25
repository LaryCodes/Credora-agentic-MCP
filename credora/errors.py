"""Error handling utilities for the Credora CFO system.

Requirements: 3.5
"""

import functools
import time
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, TypeVar, Any, Optional, Union
from enum import Enum


class ErrorType(str, Enum):
    """Types of errors that can occur in the system."""
    TOOL_FAILURE = "tool_failure"
    AUTH_ERROR = "auth_error"
    RATE_LIMIT = "rate_limit"
    VALIDATION = "validation"
    CONNECTION = "connection"
    TIMEOUT = "timeout"


@dataclass
class ErrorResponse:
    """Structured error response for tool failures.
    
    Requirements: 3.5
    """
    error_type: str  # "tool_failure" | "auth_error" | "rate_limit" | "validation" | "connection" | "timeout"
    message: str  # User-friendly message
    recoverable: bool = True
    suggested_action: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    original_error: Optional[str] = None
    
    def __post_init__(self):
        if not self.error_type or not self.error_type.strip():
            raise ValueError("error_type is required and cannot be empty")
        if not self.message or not self.message.strip():
            raise ValueError("message is required and cannot be empty")
        # Validate error_type is one of the known types
        valid_types = [e.value for e in ErrorType]
        if self.error_type not in valid_types:
            raise ValueError(f"error_type must be one of: {', '.join(valid_types)}")
    
    def to_string(self) -> str:
        """Convert error response to user-friendly string."""
        result = f"Error ({self.error_type}): {self.message}"
        if self.suggested_action:
            result += f"\nSuggested action: {self.suggested_action}"
        return result
    
    def to_dict(self) -> dict:
        """Convert error response to dictionary."""
        return {
            "error_type": self.error_type,
            "message": self.message,
            "recoverable": self.recoverable,
            "suggested_action": self.suggested_action,
            "timestamp": self.timestamp.isoformat(),
            "original_error": self.original_error,
        }


# Type variable for generic function return types
T = TypeVar('T')


def create_error_response(
    error_type: Union[ErrorType, str],
    message: str,
    recoverable: bool = True,
    suggested_action: str = "",
    original_error: Optional[Exception] = None,
) -> ErrorResponse:
    """Factory function to create ErrorResponse objects.
    
    Args:
        error_type: Type of error (ErrorType enum or string)
        message: User-friendly error message
        recoverable: Whether the error is recoverable
        suggested_action: Suggested action for the user
        original_error: Original exception if any
        
    Returns:
        ErrorResponse object
    """
    type_str = error_type.value if isinstance(error_type, ErrorType) else error_type
    original_str = str(original_error) if original_error else None
    
    return ErrorResponse(
        error_type=type_str,
        message=message,
        recoverable=recoverable,
        suggested_action=suggested_action,
        original_error=original_str,
    )


def error_wrapper(
    default_error_type: Union[ErrorType, str] = ErrorType.TOOL_FAILURE,
    recoverable: bool = True,
    suggested_action: str = "Please try again or contact support.",
) -> Callable:
    """Decorator that wraps tool functions with error handling.
    
    Catches exceptions and returns structured ErrorResponse objects
    instead of raising exceptions, keeping the agent session active.
    
    Args:
        default_error_type: Default error type for unhandled exceptions
        recoverable: Whether errors from this tool are recoverable
        suggested_action: Default suggested action for errors
        
    Returns:
        Decorated function
        
    Requirements: 3.5
    """
    def decorator(func: Callable[..., T]) -> Callable[..., Union[T, str]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Union[T, str]:
            try:
                return func(*args, **kwargs)
            except ValueError as e:
                error = create_error_response(
                    ErrorType.VALIDATION,
                    f"Validation error: {str(e)}",
                    recoverable=True,
                    suggested_action="Please check your input parameters.",
                    original_error=e,
                )
                return error.to_string()
            except ConnectionError as e:
                error = create_error_response(
                    ErrorType.CONNECTION,
                    f"Connection error: {str(e)}",
                    recoverable=True,
                    suggested_action="Please check your network connection and try again.",
                    original_error=e,
                )
                return error.to_string()
            except TimeoutError as e:
                error = create_error_response(
                    ErrorType.TIMEOUT,
                    f"Operation timed out: {str(e)}",
                    recoverable=True,
                    suggested_action="Please try again. The operation may take longer than expected.",
                    original_error=e,
                )
                return error.to_string()
            except PermissionError as e:
                error = create_error_response(
                    ErrorType.AUTH_ERROR,
                    f"Authorization error: {str(e)}",
                    recoverable=True,
                    suggested_action="Please check your permissions or re-authenticate.",
                    original_error=e,
                )
                return error.to_string()
            except Exception as e:
                type_str = default_error_type.value if isinstance(default_error_type, ErrorType) else default_error_type
                error = create_error_response(
                    type_str,
                    f"An error occurred: {str(e)}",
                    recoverable=recoverable,
                    suggested_action=suggested_action,
                    original_error=e,
                )
                return error.to_string()
        return wrapper
    return decorator


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    retryable_exceptions: tuple = (ConnectionError, TimeoutError),
) -> Callable:
    """Decorator that implements retry logic with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff calculation
        retryable_exceptions: Tuple of exception types that should trigger retry
        
    Returns:
        Decorated function
        
    Requirements: 3.5
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        # Calculate delay with exponential backoff
                        delay = min(
                            base_delay * (exponential_base ** attempt),
                            max_delay
                        )
                        time.sleep(delay)
                    else:
                        # Max retries reached, raise the exception
                        raise
            
            # This should not be reached, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected state in retry logic")
        
        return wrapper
    return decorator


def async_retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    retryable_exceptions: tuple = (ConnectionError, TimeoutError),
) -> Callable:
    """Async decorator that implements retry logic with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff calculation
        retryable_exceptions: Tuple of exception types that should trigger retry
        
    Returns:
        Decorated async function
        
    Requirements: 3.5
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        # Calculate delay with exponential backoff
                        delay = min(
                            base_delay * (exponential_base ** attempt),
                            max_delay
                        )
                        await asyncio.sleep(delay)
                    else:
                        # Max retries reached, raise the exception
                        raise
            
            # This should not be reached, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected state in retry logic")
        
        return wrapper
    return decorator


def safe_tool_execution(
    func: Callable[..., T],
    *args: Any,
    default_return: Optional[str] = None,
    **kwargs: Any,
) -> Union[T, str]:
    """Execute a tool function safely, catching any exceptions.
    
    This is a utility function for one-off safe execution without
    needing to decorate the function.
    
    Args:
        func: The function to execute
        *args: Positional arguments to pass to the function
        default_return: Default return value if an error occurs
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        Function result or error message string
        
    Requirements: 3.5
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        error = create_error_response(
            ErrorType.TOOL_FAILURE,
            f"Tool execution failed: {str(e)}",
            recoverable=True,
            suggested_action="Please try again or contact support.",
            original_error=e,
        )
        if default_return is not None:
            return default_return
        return error.to_string()


__all__ = [
    "ErrorType",
    "ErrorResponse",
    "create_error_response",
    "error_wrapper",
    "retry_with_backoff",
    "async_retry_with_backoff",
    "safe_tool_execution",
]
