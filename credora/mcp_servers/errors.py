"""
Error types for MCP servers.

This module defines error types and error handling utilities.

Requirements: 6.1, 6.2, 6.3
"""

import asyncio
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar, Union


class MCPErrorType(Enum):
    """Types of errors that can occur in MCP servers.
    
    Requirements: 6.1
    """
    
    AUTH_REQUIRED = "auth_required"
    AUTH_EXPIRED = "auth_expired"
    RATE_LIMITED = "rate_limited"
    API_ERROR = "api_error"
    NETWORK_ERROR = "network_error"
    INVALID_PARAMS = "invalid_params"
    NOT_FOUND = "not_found"


@dataclass
class MCPError(Exception):
    """Structured error response for MCP servers.
    
    Requirements: 6.1, 6.3
    
    Attributes:
        error_type: The type of error that occurred
        message: Human-readable error message
        recoverable: Whether the error can be recovered from (e.g., by retrying)
        retry_after: Suggested seconds to wait before retrying (for rate limits)
        details: Additional error details for debugging
    """
    
    error_type: MCPErrorType
    message: str
    recoverable: bool
    retry_after: Optional[int] = None  # Seconds
    details: Optional[Dict[str, Any]] = None
    
    def __str__(self) -> str:
        """Return string representation of the error."""
        return self.message
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON serialization.
        
        Returns:
            Dictionary with error_type, message, recoverable, and optional fields
        """
        result = {
            "error_type": self.error_type.value,
            "message": self.message,
            "recoverable": self.recoverable,
        }
        if self.retry_after is not None:
            result["retry_after"] = self.retry_after
        if self.details is not None:
            result["details"] = self.details
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPError":
        """Create MCPError from dictionary.
        
        Args:
            data: Dictionary with error fields
            
        Returns:
            MCPError instance
        """
        return cls(
            error_type=MCPErrorType(data.get("error_type", "api_error")),
            message=data.get("message", "Unknown error"),
            recoverable=data.get("recoverable", False),
            retry_after=data.get("retry_after"),
            details=data.get("details"),
        )
    
    @classmethod
    def auth_required(cls, message: str = "Authentication required", **details) -> "MCPError":
        """Create an authentication required error.
        
        Args:
            message: Error message
            **details: Additional details
            
        Returns:
            MCPError with AUTH_REQUIRED type
        """
        return cls(
            error_type=MCPErrorType.AUTH_REQUIRED,
            message=message,
            recoverable=False,
            details=details if details else None,
        )
    
    @classmethod
    def auth_expired(cls, message: str = "Authentication expired", **details) -> "MCPError":
        """Create an authentication expired error.
        
        Args:
            message: Error message
            **details: Additional details
            
        Returns:
            MCPError with AUTH_EXPIRED type
        """
        return cls(
            error_type=MCPErrorType.AUTH_EXPIRED,
            message=message,
            recoverable=False,
            details=details if details else None,
        )
    
    @classmethod
    def rate_limited(
        cls, 
        message: str = "Rate limit exceeded", 
        retry_after: Optional[int] = None,
        **details
    ) -> "MCPError":
        """Create a rate limit error.
        
        Args:
            message: Error message
            retry_after: Seconds to wait before retrying
            **details: Additional details
            
        Returns:
            MCPError with RATE_LIMITED type
        """
        return cls(
            error_type=MCPErrorType.RATE_LIMITED,
            message=message,
            recoverable=True,
            retry_after=retry_after,
            details=details if details else None,
        )
    
    @classmethod
    def api_error(cls, message: str, recoverable: bool = True, **details) -> "MCPError":
        """Create an API error.
        
        Args:
            message: Error message
            recoverable: Whether the error is recoverable
            **details: Additional details
            
        Returns:
            MCPError with API_ERROR type
        """
        return cls(
            error_type=MCPErrorType.API_ERROR,
            message=message,
            recoverable=recoverable,
            details=details if details else None,
        )
    
    @classmethod
    def network_error(cls, message: str = "Network error", **details) -> "MCPError":
        """Create a network error.
        
        Args:
            message: Error message
            **details: Additional details
            
        Returns:
            MCPError with NETWORK_ERROR type
        """
        return cls(
            error_type=MCPErrorType.NETWORK_ERROR,
            message=message,
            recoverable=True,
            details=details if details else None,
        )
    
    @classmethod
    def invalid_params(cls, message: str, **details) -> "MCPError":
        """Create an invalid parameters error.
        
        Args:
            message: Error message
            **details: Additional details
            
        Returns:
            MCPError with INVALID_PARAMS type
        """
        return cls(
            error_type=MCPErrorType.INVALID_PARAMS,
            message=message,
            recoverable=False,
            details=details if details else None,
        )
    
    @classmethod
    def not_found(cls, message: str, **details) -> "MCPError":
        """Create a not found error.
        
        Args:
            message: Error message
            **details: Additional details
            
        Returns:
            MCPError with NOT_FOUND type
        """
        return cls(
            error_type=MCPErrorType.NOT_FOUND,
            message=message,
            recoverable=False,
            details=details if details else None,
        )


@dataclass
class RetryConfig:
    """Configuration for retry logic with exponential backoff.
    
    Requirements: 6.2
    
    Attributes:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        max_delay: Maximum delay in seconds (caps exponential growth)
        exponential_base: Base for exponential backoff calculation
        jitter: Whether to add random jitter to delays
    """
    
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for a given retry attempt.
        
        The delay follows exponential backoff:
        delay = initial_delay * (exponential_base ** attempt)
        
        With optional jitter to prevent thundering herd.
        
        Args:
            attempt: The retry attempt number (0-indexed)
            
        Returns:
            Delay in seconds before the next retry
            
        Requirements: 6.2
        """
        delay = self.initial_delay * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            # Add up to 25% random jitter
            jitter_amount = delay * 0.25 * random.random()
            delay = delay + jitter_amount
        
        return delay
    
    def get_delays(self) -> list[float]:
        """Get all delay values for configured retries.
        
        Returns:
            List of delay values for each retry attempt
        """
        return [self.get_delay(i) for i in range(self.max_retries)]


# Type variable for generic return type
T = TypeVar("T")


async def retry_with_backoff(
    func: Callable[..., T],
    config: Optional[RetryConfig] = None,
    retryable_errors: Optional[tuple] = None,
    retryable_error_types: Optional[list[MCPErrorType]] = None,
    *args,
    **kwargs,
) -> T:
    """Execute a function with exponential backoff retry logic.
    
    Requirements: 6.2
    
    Args:
        func: Async function to execute
        config: Retry configuration (uses defaults if not provided)
        retryable_errors: Tuple of exception types to retry on
        retryable_error_types: List of MCPErrorType values to retry on
        *args: Positional arguments to pass to func
        **kwargs: Keyword arguments to pass to func
        
    Returns:
        Result from successful function execution
        
    Raises:
        The last exception if all retries are exhausted
    """
    config = config or RetryConfig()
    retryable_errors = retryable_errors or (MCPError,)
    retryable_error_types = retryable_error_types or [
        MCPErrorType.RATE_LIMITED,
        MCPErrorType.NETWORK_ERROR,
        MCPErrorType.API_ERROR,
    ]
    
    last_exception: Optional[Exception] = None
    
    for attempt in range(config.max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except MCPError as e:
            last_exception = e
            
            # Check if this error type is retryable
            if e.error_type not in retryable_error_types:
                raise
            
            # Check if error is marked as non-recoverable
            if not e.recoverable:
                raise
            
            # If we've exhausted retries, raise
            if attempt >= config.max_retries:
                raise
            
            # Use retry_after if provided, otherwise use exponential backoff
            if e.retry_after is not None:
                delay = float(e.retry_after)
            else:
                delay = config.get_delay(attempt)
            
            await asyncio.sleep(delay)
            
        except retryable_errors as e:
            last_exception = e
            
            # If we've exhausted retries, raise
            if attempt >= config.max_retries:
                raise
            
            delay = config.get_delay(attempt)
            await asyncio.sleep(delay)
    
    # Should not reach here, but just in case
    if last_exception:
        raise last_exception
    raise RuntimeError("Unexpected state in retry logic")


def classify_http_error(status_code: int, response_body: Optional[str] = None) -> MCPError:
    """Classify an HTTP error into an MCPError.
    
    Requirements: 6.1, 6.3
    
    Args:
        status_code: HTTP status code
        response_body: Optional response body for additional context
        
    Returns:
        Appropriate MCPError based on status code
    """
    if status_code == 401:
        return MCPError.auth_required(
            message="Authentication required",
            status_code=status_code,
        )
    elif status_code == 403:
        return MCPError.auth_expired(
            message="Access forbidden - token may be expired or revoked",
            status_code=status_code,
        )
    elif status_code == 404:
        return MCPError.not_found(
            message="Resource not found",
            status_code=status_code,
        )
    elif status_code == 429:
        return MCPError.rate_limited(
            message="Rate limit exceeded",
            retry_after=60,  # Default to 60 seconds
            status_code=status_code,
        )
    elif status_code >= 500:
        return MCPError.api_error(
            message=f"Server error (HTTP {status_code})",
            recoverable=True,
            status_code=status_code,
        )
    else:
        return MCPError.api_error(
            message=f"API error (HTTP {status_code})",
            recoverable=False,
            status_code=status_code,
        )
