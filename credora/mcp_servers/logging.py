"""
Logging utilities for MCP servers with sensitive data sanitization.

This module provides logging utilities that automatically mask sensitive data
such as tokens, API keys, and PII before writing to logs.

Requirements: 6.4, 7.3
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Pattern
from threading import Lock


# Patterns for sensitive data that should be masked
SENSITIVE_PATTERNS: List[tuple[str, Pattern]] = [
    # OAuth tokens (various formats)
    ("access_token", re.compile(r'(access_token["\s:=]+)["\']?([a-zA-Z0-9_\-\.]+)["\']?', re.IGNORECASE)),
    ("refresh_token", re.compile(r'(refresh_token["\s:=]+)["\']?([a-zA-Z0-9_\-\.]+)["\']?', re.IGNORECASE)),
    ("bearer_token", re.compile(r'(Bearer\s+)([a-zA-Z0-9_\-\.]+)', re.IGNORECASE)),
    ("authorization", re.compile(r'(Authorization["\s:=]+)["\']?([a-zA-Z0-9_\-\.\s]+)["\']?', re.IGNORECASE)),
    
    # API keys
    ("api_key", re.compile(r'(api_key["\s:=]+)["\']?([a-zA-Z0-9_\-]+)["\']?', re.IGNORECASE)),
    ("apikey", re.compile(r'(apikey["\s:=]+)["\']?([a-zA-Z0-9_\-]+)["\']?', re.IGNORECASE)),
    ("secret", re.compile(r'(secret["\s:=]+)["\']?([a-zA-Z0-9_\-]+)["\']?', re.IGNORECASE)),
    ("client_secret", re.compile(r'(client_secret["\s:=]+)["\']?([a-zA-Z0-9_\-]+)["\']?', re.IGNORECASE)),
    
    # PII patterns
    ("email", re.compile(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)')),
    ("phone", re.compile(r'(\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})')),
    ("ssn", re.compile(r'(\d{3}[-\s]?\d{2}[-\s]?\d{4})')),
    ("credit_card", re.compile(r'(\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4})')),
]

# Keys that should have their values masked in dictionaries
SENSITIVE_KEYS = {
    "access_token",
    "refresh_token",
    "token",
    "api_key",
    "apikey",
    "secret",
    "client_secret",
    "password",
    "authorization",
    "auth",
    "credentials",
    "private_key",
    "secret_key",
}


def mask_value(value: str, visible_chars: int = 4) -> str:
    """Mask a sensitive value, showing only first few characters.
    
    Args:
        value: The value to mask
        visible_chars: Number of characters to show at the start
        
    Returns:
        Masked value like "abc1****"
    """
    if not value:
        return "****"
    if len(value) <= visible_chars:
        return "****"
    return value[:visible_chars] + "****"


def sanitize_string(text: str) -> str:
    """Sanitize a string by masking sensitive patterns.
    
    Args:
        text: The text to sanitize
        
    Returns:
        Text with sensitive data masked
        
    Requirements: 7.3
    """
    result = text
    
    for name, pattern in SENSITIVE_PATTERNS:
        if name in ("email", "phone", "ssn", "credit_card"):
            # For PII, replace the entire match
            result = pattern.sub(lambda m: mask_value(m.group(1)), result)
        else:
            # For tokens/keys, preserve the key name and mask the value
            result = pattern.sub(lambda m: m.group(1) + mask_value(m.group(2)), result)
    
    return result


def sanitize_dict(data: Dict[str, Any], depth: int = 0, max_depth: int = 10) -> Dict[str, Any]:
    """Sanitize a dictionary by masking sensitive values.
    
    Args:
        data: Dictionary to sanitize
        depth: Current recursion depth
        max_depth: Maximum recursion depth
        
    Returns:
        Dictionary with sensitive values masked
        
    Requirements: 7.3
    """
    if depth >= max_depth:
        return {"_truncated": "max depth reached"}
    
    result = {}
    
    for key, value in data.items():
        key_lower = key.lower()
        
        # Check if key indicates sensitive data
        if key_lower in SENSITIVE_KEYS or any(s in key_lower for s in SENSITIVE_KEYS):
            if isinstance(value, str):
                result[key] = mask_value(value)
            else:
                result[key] = "****"
        elif isinstance(value, dict):
            result[key] = sanitize_dict(value, depth + 1, max_depth)
        elif isinstance(value, list):
            result[key] = [
                sanitize_dict(item, depth + 1, max_depth) if isinstance(item, dict)
                else sanitize_string(str(item)) if isinstance(item, str)
                else item
                for item in value
            ]
        elif isinstance(value, str):
            result[key] = sanitize_string(value)
        else:
            result[key] = value
    
    return result


@dataclass
class APIErrorLog:
    """Log entry for an API error.
    
    Requirements: 6.4
    
    Attributes:
        timestamp: When the error occurred
        error_type: Type of error (from MCPErrorType)
        message: Error message
        platform: Platform where error occurred (meta, google, shopify)
        request_method: HTTP method used
        request_url: URL that was requested (sanitized)
        status_code: HTTP status code if available
        request_id: Unique request identifier
        details: Additional error details (sanitized)
    """
    timestamp: datetime
    error_type: str
    message: str
    platform: Optional[str] = None
    request_method: Optional[str] = None
    request_url: Optional[str] = None
    status_code: Optional[int] = None
    request_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "timestamp": self.timestamp.isoformat(),
            "error_type": self.error_type,
            "message": sanitize_string(self.message),
        }
        
        if self.platform:
            result["platform"] = self.platform
        if self.request_method:
            result["request_method"] = self.request_method
        if self.request_url:
            result["request_url"] = sanitize_string(self.request_url)
        if self.status_code is not None:
            result["status_code"] = self.status_code
        if self.request_id:
            result["request_id"] = self.request_id
        if self.details:
            result["details"] = sanitize_dict(self.details)
        
        return result


class MCPLogger:
    """Logger for MCP server operations with automatic sanitization.
    
    Requirements: 6.4, 7.3
    """
    
    def __init__(
        self,
        name: str = "mcp_server",
        level: int = logging.INFO,
        max_entries: int = 10000,
    ):
        """Initialize the MCP logger.
        
        Args:
            name: Logger name
            level: Logging level
            max_entries: Maximum number of error log entries to keep
        """
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)
        self._error_logs: List[APIErrorLog] = []
        self._lock = Lock()
        self._max_entries = max_entries
    
    def _add_error_log(self, log_entry: APIErrorLog) -> None:
        """Add an error log entry to the internal store."""
        with self._lock:
            self._error_logs.append(log_entry)
            if len(self._error_logs) > self._max_entries:
                self._error_logs = self._error_logs[-self._max_entries:]
    
    def log_api_error(
        self,
        error_type: str,
        message: str,
        platform: Optional[str] = None,
        request_method: Optional[str] = None,
        request_url: Optional[str] = None,
        status_code: Optional[int] = None,
        request_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> APIErrorLog:
        """Log an API error with automatic sanitization.
        
        Args:
            error_type: Type of error
            message: Error message
            platform: Platform where error occurred
            request_method: HTTP method used
            request_url: URL that was requested
            status_code: HTTP status code
            request_id: Unique request identifier
            details: Additional error details
            
        Returns:
            The created APIErrorLog entry
            
        Requirements: 6.4
        """
        log_entry = APIErrorLog(
            timestamp=datetime.now(),
            error_type=error_type,
            message=message,
            platform=platform,
            request_method=request_method,
            request_url=request_url,
            status_code=status_code,
            request_id=request_id,
            details=details,
        )
        
        self._add_error_log(log_entry)
        
        # Log to standard logger with sanitized data
        sanitized = log_entry.to_dict()
        self._logger.error(
            f"API Error [{error_type}]: {sanitize_string(message)}",
            extra={"error_details": sanitized},
        )
        
        return log_entry
    
    def log_info(self, message: str, **kwargs) -> None:
        """Log an info message with sanitization.
        
        Args:
            message: Message to log
            **kwargs: Additional context to include
        """
        sanitized_message = sanitize_string(message)
        sanitized_kwargs = sanitize_dict(kwargs) if kwargs else {}
        self._logger.info(sanitized_message, extra=sanitized_kwargs)
    
    def log_warning(self, message: str, **kwargs) -> None:
        """Log a warning message with sanitization.
        
        Args:
            message: Message to log
            **kwargs: Additional context to include
        """
        sanitized_message = sanitize_string(message)
        sanitized_kwargs = sanitize_dict(kwargs) if kwargs else {}
        self._logger.warning(sanitized_message, extra=sanitized_kwargs)
    
    def log_debug(self, message: str, **kwargs) -> None:
        """Log a debug message with sanitization.
        
        Args:
            message: Message to log
            **kwargs: Additional context to include
        """
        sanitized_message = sanitize_string(message)
        sanitized_kwargs = sanitize_dict(kwargs) if kwargs else {}
        self._logger.debug(sanitized_message, extra=sanitized_kwargs)
    
    def get_error_logs(
        self,
        platform: Optional[str] = None,
        error_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[APIErrorLog]:
        """Get error log entries with optional filtering.
        
        Args:
            platform: Filter by platform
            error_type: Filter by error type
            limit: Maximum number of entries to return
            
        Returns:
            List of matching APIErrorLog entries (newest first)
        """
        with self._lock:
            logs = list(self._error_logs)
        
        if platform:
            logs = [l for l in logs if l.platform == platform]
        
        if error_type:
            logs = [l for l in logs if l.error_type == error_type]
        
        # Return newest first
        logs = list(reversed(logs))
        
        if limit:
            logs = logs[:limit]
        
        return logs
    
    def get_latest_errors(self, count: int = 10) -> List[APIErrorLog]:
        """Get the most recent error log entries.
        
        Args:
            count: Number of entries to return
            
        Returns:
            List of most recent APIErrorLog entries
        """
        with self._lock:
            return list(reversed(self._error_logs[-count:]))
    
    def clear_error_logs(self) -> int:
        """Clear all error log entries.
        
        Returns:
            Number of entries cleared
        """
        with self._lock:
            count = len(self._error_logs)
            self._error_logs = []
            return count
    
    def error_count(self) -> int:
        """Get the total number of error log entries.
        
        Returns:
            Number of error log entries
        """
        with self._lock:
            return len(self._error_logs)


# Global logger instance
_global_mcp_logger: Optional[MCPLogger] = None
_logger_lock = Lock()


def get_mcp_logger() -> MCPLogger:
    """Get or create the global MCP logger.
    
    Returns:
        The global MCPLogger instance
    """
    global _global_mcp_logger
    with _logger_lock:
        if _global_mcp_logger is None:
            _global_mcp_logger = MCPLogger()
        return _global_mcp_logger


def set_mcp_logger(logger: MCPLogger) -> None:
    """Set the global MCP logger (for testing).
    
    Args:
        logger: The MCPLogger instance to use
    """
    global _global_mcp_logger
    with _logger_lock:
        _global_mcp_logger = logger


def reset_mcp_logger() -> None:
    """Reset the global MCP logger to a new instance."""
    global _global_mcp_logger
    with _logger_lock:
        _global_mcp_logger = MCPLogger()
