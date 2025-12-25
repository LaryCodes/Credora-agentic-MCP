"""Tool invocation logging utilities for the Credora CFO system.

Requirements: 3.6
"""

import functools
from datetime import datetime
from typing import Callable, TypeVar, Any, List, Optional, Dict
from threading import Lock

from credora.models import ToolLog


# Type variable for generic function return types
T = TypeVar('T')


class ToolLogger:
    """Thread-safe logger for tool invocations.
    
    Stores ToolLog entries for each tool invocation for auditability.
    
    Requirements: 3.6
    """
    
    def __init__(self, max_entries: int = 10000):
        """Initialize the tool logger.
        
        Args:
            max_entries: Maximum number of log entries to keep (oldest are removed)
        """
        self._logs: List[ToolLog] = []
        self._lock = Lock()
        self._max_entries = max_entries
    
    def log(
        self,
        tool_name: str,
        input_params: Dict[str, Any],
        output: str,
        success: bool,
        agent_name: str = "",
    ) -> ToolLog:
        """Log a tool invocation.
        
        Args:
            tool_name: Name of the tool that was invoked
            input_params: Dictionary of input parameters
            output: Output string from the tool
            success: Whether the tool execution was successful
            agent_name: Name of the agent that invoked the tool
            
        Returns:
            The created ToolLog entry
            
        Requirements: 3.6
        """
        log_entry = ToolLog(
            tool_name=tool_name,
            input_params=input_params,
            output=output,
            success=success,
            timestamp=datetime.now(),
            agent_name=agent_name,
        )
        
        with self._lock:
            self._logs.append(log_entry)
            # Remove oldest entries if we exceed max
            if len(self._logs) > self._max_entries:
                self._logs = self._logs[-self._max_entries:]
        
        return log_entry
    
    def get_logs(
        self,
        tool_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        success_only: Optional[bool] = None,
        limit: Optional[int] = None,
    ) -> List[ToolLog]:
        """Retrieve log entries with optional filtering.
        
        Args:
            tool_name: Filter by tool name (optional)
            agent_name: Filter by agent name (optional)
            success_only: If True, only successful; if False, only failed (optional)
            limit: Maximum number of entries to return (optional)
            
        Returns:
            List of matching ToolLog entries (newest first)
        """
        with self._lock:
            logs = list(self._logs)
        
        # Apply filters
        if tool_name is not None:
            logs = [l for l in logs if l.tool_name == tool_name]
        
        if agent_name is not None:
            logs = [l for l in logs if l.agent_name == agent_name]
        
        if success_only is not None:
            logs = [l for l in logs if l.success == success_only]
        
        # Return newest first
        logs = list(reversed(logs))
        
        if limit is not None:
            logs = logs[:limit]
        
        return logs
    
    def get_latest(self, count: int = 1) -> List[ToolLog]:
        """Get the most recent log entries.
        
        Args:
            count: Number of entries to return
            
        Returns:
            List of most recent ToolLog entries
        """
        with self._lock:
            return list(reversed(self._logs[-count:]))
    
    def clear(self) -> int:
        """Clear all log entries.
        
        Returns:
            Number of entries that were cleared
        """
        with self._lock:
            count = len(self._logs)
            self._logs = []
            return count
    
    def count(self) -> int:
        """Get the total number of log entries.
        
        Returns:
            Number of log entries
        """
        with self._lock:
            return len(self._logs)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about logged tool invocations.
        
        Returns:
            Dictionary with statistics
        """
        with self._lock:
            logs = list(self._logs)
        
        if not logs:
            return {
                "total_invocations": 0,
                "successful_invocations": 0,
                "failed_invocations": 0,
                "success_rate": 0.0,
                "tools_used": [],
                "agents_used": [],
            }
        
        successful = sum(1 for l in logs if l.success)
        failed = len(logs) - successful
        tools = list(set(l.tool_name for l in logs))
        agents = list(set(l.agent_name for l in logs if l.agent_name))
        
        return {
            "total_invocations": len(logs),
            "successful_invocations": successful,
            "failed_invocations": failed,
            "success_rate": successful / len(logs) if logs else 0.0,
            "tools_used": tools,
            "agents_used": agents,
        }


# Global logger instance
_global_logger: Optional[ToolLogger] = None
_logger_lock = Lock()


def get_tool_logger() -> ToolLogger:
    """Get or create the global tool logger.
    
    Returns:
        The global ToolLogger instance
    """
    global _global_logger
    with _logger_lock:
        if _global_logger is None:
            _global_logger = ToolLogger()
        return _global_logger


def set_tool_logger(logger: ToolLogger) -> None:
    """Set the global tool logger (for testing).
    
    Args:
        logger: The ToolLogger instance to use
    """
    global _global_logger
    with _logger_lock:
        _global_logger = logger


def reset_tool_logger() -> None:
    """Reset the global tool logger to a new instance."""
    global _global_logger
    with _logger_lock:
        _global_logger = ToolLogger()


def log_tool_invocation(
    agent_name: str = "",
    logger: Optional[ToolLogger] = None,
) -> Callable:
    """Decorator that logs tool invocations.
    
    Creates a ToolLog entry for each invocation containing tool_name,
    input_params, output, success status, and timestamp.
    
    Args:
        agent_name: Name of the agent invoking the tool
        logger: Optional ToolLogger instance (uses global if not provided)
        
    Returns:
        Decorated function
        
    Requirements: 3.6
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            tool_logger = logger or get_tool_logger()
            tool_name = func.__name__
            
            # Capture input parameters
            # Get function parameter names
            import inspect
            sig = inspect.signature(func)
            param_names = list(sig.parameters.keys())
            
            # Build input params dict
            input_params: Dict[str, Any] = {}
            for i, arg in enumerate(args):
                if i < len(param_names):
                    input_params[param_names[i]] = _serialize_param(arg)
                else:
                    input_params[f"arg_{i}"] = _serialize_param(arg)
            
            for key, value in kwargs.items():
                input_params[key] = _serialize_param(value)
            
            # Execute the function
            success = True
            output = ""
            try:
                result = func(*args, **kwargs)
                output = str(result) if result is not None else ""
                return result
            except Exception as e:
                success = False
                output = f"Error: {str(e)}"
                raise
            finally:
                # Log the invocation
                tool_logger.log(
                    tool_name=tool_name,
                    input_params=input_params,
                    output=output[:1000] if len(output) > 1000 else output,  # Truncate long outputs
                    success=success,
                    agent_name=agent_name,
                )
        
        return wrapper
    return decorator


def _serialize_param(value: Any) -> Any:
    """Serialize a parameter value for logging.
    
    Args:
        value: The value to serialize
        
    Returns:
        Serialized value (JSON-compatible)
    """
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_serialize_param(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _serialize_param(v) for k, v in value.items()}
    # For other types, convert to string
    return str(value)


__all__ = [
    "ToolLogger",
    "ToolLog",
    "get_tool_logger",
    "set_tool_logger",
    "reset_tool_logger",
    "log_tool_invocation",
]
