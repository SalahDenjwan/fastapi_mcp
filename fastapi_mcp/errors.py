"""
MCP Tool Error Types

This module provides a consistent error hierarchy for MCP tool operations.
All errors include context like the tool name without exposing internal details.
"""

from enum import Enum
from typing import Optional, Any


class MCPErrorCode(Enum):
    """Standard error codes for MCP tool errors."""

    # Tool execution errors (1xxx)
    TOOL_NOT_FOUND = 1001
    TOOL_EXECUTION_FAILED = 1002
    TOOL_TIMEOUT = 1003
    TOOL_CANCELLED = 1004

    # Parameter/validation errors (2xxx)
    INVALID_PARAMETERS = 2001
    MISSING_PARAMETER = 2002

    # Transport/session errors (3xxx)
    SESSION_NOT_FOUND = 3001
    SESSION_INVALID = 3002
    TRANSPORT_ERROR = 3003

    # Framework/internal errors (4xxx)
    INTERNAL_ERROR = 4001
    CONFIGURATION_ERROR = 4002


class MCPToolError(Exception):
    """
    Base exception for all MCP tool errors.

    Provides consistent error formatting with tool context.
    """

    def __init__(
        self,
        message: str,
        *,
        code: MCPErrorCode = MCPErrorCode.INTERNAL_ERROR,
        tool_name: Optional[str] = None,
        details: Optional[str] = None,
    ):
        self.message = message
        self.code = code
        self.tool_name = tool_name
        self.details = details
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format the error message for display to clients."""
        parts = []
        if self.tool_name:
            parts.append(f"[{self.tool_name}]")
        parts.append(self.message)
        return " ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """Convert error to a dictionary suitable for JSON serialization."""
        result: dict[str, Any] = {
            "error": self.message,
            "code": self.code.value,
            "code_name": self.code.name,
        }
        if self.tool_name:
            result["tool_name"] = self.tool_name
        return result


class ToolNotFoundError(MCPToolError):
    """Raised when a requested tool does not exist."""

    def __init__(self, tool_name: str, *, details: Optional[str] = None):
        super().__init__(
            f"Tool not found: {tool_name}",
            code=MCPErrorCode.TOOL_NOT_FOUND,
            tool_name=tool_name,
            details=details,
        )


class ToolExecutionError(MCPToolError):
    """Raised when a tool fails during execution."""

    def __init__(
        self,
        message: str,
        *,
        tool_name: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[str] = None,
    ):
        self.status_code = status_code
        super().__init__(
            message,
            code=MCPErrorCode.TOOL_EXECUTION_FAILED,
            tool_name=tool_name,
            details=details,
        )

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if self.status_code is not None:
            result["status_code"] = self.status_code
        return result


class ToolTimeoutError(MCPToolError):
    """Raised when a tool execution times out."""

    def __init__(
        self,
        tool_name: Optional[str] = None,
        *,
        timeout_seconds: Optional[float] = None,
        details: Optional[str] = None,
    ):
        self.timeout_seconds = timeout_seconds
        message = "Tool execution timed out"
        if timeout_seconds is not None:
            message = f"Tool execution timed out after {timeout_seconds}s"
        super().__init__(
            message,
            code=MCPErrorCode.TOOL_TIMEOUT,
            tool_name=tool_name,
            details=details,
        )


class ToolCancelledError(MCPToolError):
    """Raised when a tool execution is cancelled."""

    def __init__(
        self,
        tool_name: Optional[str] = None,
        *,
        reason: Optional[str] = None,
        details: Optional[str] = None,
    ):
        self.reason = reason
        message = "Tool execution was cancelled"
        if reason:
            message = f"Tool execution was cancelled: {reason}"
        super().__init__(
            message,
            code=MCPErrorCode.TOOL_CANCELLED,
            tool_name=tool_name,
            details=details,
        )


class InvalidParametersError(MCPToolError):
    """Raised when tool parameters are invalid."""

    def __init__(
        self,
        message: str,
        *,
        tool_name: Optional[str] = None,
        parameter_name: Optional[str] = None,
        details: Optional[str] = None,
    ):
        self.parameter_name = parameter_name
        super().__init__(
            message,
            code=MCPErrorCode.INVALID_PARAMETERS,
            tool_name=tool_name,
            details=details,
        )

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if self.parameter_name:
            result["parameter_name"] = self.parameter_name
        return result


class MissingParameterError(InvalidParametersError):
    """Raised when a required parameter is missing."""

    def __init__(
        self,
        parameter_name: str,
        *,
        tool_name: Optional[str] = None,
        details: Optional[str] = None,
    ):
        super().__init__(
            f"Missing required parameter: {parameter_name}",
            tool_name=tool_name,
            parameter_name=parameter_name,
            details=details,
        )
        self.code = MCPErrorCode.MISSING_PARAMETER


class SessionNotFoundError(MCPToolError):
    """Raised when a session cannot be found."""

    def __init__(
        self,
        session_id: Optional[str] = None,
        *,
        details: Optional[str] = None,
    ):
        self.session_id = session_id
        message = "Session not found"
        if session_id:
            message = f"Session not found: {session_id}"
        super().__init__(
            message,
            code=MCPErrorCode.SESSION_NOT_FOUND,
            details=details,
        )


class SessionInvalidError(MCPToolError):
    """Raised when a session ID is invalid."""

    def __init__(
        self,
        reason: str = "Invalid session ID",
        *,
        details: Optional[str] = None,
    ):
        super().__init__(
            reason,
            code=MCPErrorCode.SESSION_INVALID,
            details=details,
        )


class TransportError(MCPToolError):
    """Raised when there's a transport-level error."""

    def __init__(
        self,
        message: str,
        *,
        details: Optional[str] = None,
    ):
        super().__init__(
            message,
            code=MCPErrorCode.TRANSPORT_ERROR,
            details=details,
        )


class InternalError(MCPToolError):
    """Raised for internal/framework errors that shouldn't expose details."""

    def __init__(
        self,
        *,
        public_message: str = "An internal error occurred",
        internal_message: Optional[str] = None,
        tool_name: Optional[str] = None,
    ):
        # Store internal message for logging but don't expose it
        self._internal_message = internal_message
        super().__init__(
            public_message,
            code=MCPErrorCode.INTERNAL_ERROR,
            tool_name=tool_name,
            details=None,  # Never expose internal details
        )

    @property
    def internal_message(self) -> Optional[str]:
        """Get the internal message for logging purposes only."""
        return self._internal_message


class ConfigurationError(MCPToolError):
    """Raised when there's a configuration error."""

    def __init__(
        self,
        message: str,
        *,
        details: Optional[str] = None,
    ):
        super().__init__(
            message,
            code=MCPErrorCode.CONFIGURATION_ERROR,
            details=details,
        )


def format_error_for_client(error: Exception, *, tool_name: Optional[str] = None) -> str:
    """
    Format any exception as a client-safe error message.

    For MCPToolError instances, uses the built-in formatting.
    For other exceptions, returns a generic message to avoid leaking internals.
    """
    if isinstance(error, MCPToolError):
        return str(error)

    # For non-MCP errors, return a generic message with tool context
    if tool_name:
        return f"[{tool_name}] Tool execution failed"
    return "Tool execution failed"
