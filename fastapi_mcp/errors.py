"""
MCP Tool Error Types

This module provides a consistent error hierarchy for MCP tool operations.
The goal is to make errors easier to understand for clients by:

1. Categorizing errors by type (tool failures, timeouts, cancellations, framework issues)
2. Including contextual information (tool name) without exposing internal details
3. Using structured error codes that clients can programmatically handle
4. Providing consistent formatting across all error paths

Error Code Ranges:
    - 1xxx: Tool execution errors (not found, failed, timeout, cancelled)
    - 2xxx: Parameter/validation errors (invalid params, missing required)
    - 3xxx: Transport/session errors (session not found, invalid, transport failure)
    - 4xxx: Framework/internal errors (internal error, configuration error)

Usage:
    from fastapi_mcp.errors import ToolExecutionError, ToolNotFoundError

    # Raise with tool context
    raise ToolExecutionError("Request failed", tool_name="get_user", status_code=500)

    # Error message will be: "[get_user] Request failed"
"""

from enum import Enum
from typing import Optional, Any


class MCPErrorCode(Enum):
    """
    Standard error codes for MCP tool errors.

    These codes allow clients to programmatically identify error types
    without parsing error messages. The numeric ranges group related errors:

    - 1xxx: Tool execution errors
    - 2xxx: Parameter validation errors
    - 3xxx: Session/transport errors
    - 4xxx: Internal/framework errors
    """

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

    This class provides consistent error formatting that includes tool context
    (when available) while keeping the interface simple. All MCP errors inherit
    from this class, allowing clients to catch all MCP-related errors with a
    single except clause if desired.

    The error message format is: "[tool_name] message" when tool_name is provided,
    or just "message" otherwise. This makes it easy to identify which tool caused
    an error in logs and client responses.

    Attributes:
        message: The human-readable error message.
        code: The MCPErrorCode categorizing this error.
        tool_name: Optional name of the tool that caused the error.
        details: Optional additional details (for logging, not exposed to clients).
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
        """
        Format the error message for display to clients.

        Prefixes the message with [tool_name] when available to provide
        immediate context about which tool caused the error.
        """
        parts = []
        if self.tool_name:
            parts.append(f"[{self.tool_name}]")
        parts.append(self.message)
        return " ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert error to a dictionary suitable for JSON serialization.

        This is useful for APIs that need to return structured error responses.
        The dictionary includes the error code for programmatic handling.
        """
        result: dict[str, Any] = {
            "error": self.message,
            "code": self.code.value,
            "code_name": self.code.name,
        }
        if self.tool_name:
            result["tool_name"] = self.tool_name
        return result


class ToolNotFoundError(MCPToolError):
    """
    Raised when a requested tool does not exist.

    This error indicates the client requested a tool that isn't registered
    in the MCP server. Common causes include typos in tool names or
    requesting tools that have been removed or renamed.
    """

    def __init__(self, tool_name: str, *, details: Optional[str] = None):
        super().__init__(
            f"Tool not found: {tool_name}",
            code=MCPErrorCode.TOOL_NOT_FOUND,
            tool_name=tool_name,
            details=details,
        )


class ToolExecutionError(MCPToolError):
    """
    Raised when a tool fails during execution.

    This is the most common error type, covering cases where:
    - The underlying API returns an error status code (4xx, 5xx)
    - An unexpected exception occurs during tool execution
    - The tool's response cannot be processed

    The status_code attribute is included when the error originated from
    an HTTP response, helping clients understand if the issue is a client
    error (4xx) or server error (5xx).

    Attributes:
        status_code: HTTP status code if the error came from an HTTP response.
    """

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
        """Include HTTP status code in serialized output when available."""
        result = super().to_dict()
        if self.status_code is not None:
            result["status_code"] = self.status_code
        return result


class ToolTimeoutError(MCPToolError):
    """
    Raised when a tool execution times out.

    This error is raised when an asyncio.TimeoutError occurs during tool
    execution. It's distinct from ToolExecutionError to allow clients to
    implement retry logic specifically for timeout cases.

    Attributes:
        timeout_seconds: The timeout duration if known.
    """

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
    """
    Raised when a tool execution is cancelled.

    This error wraps asyncio.CancelledError to provide consistent formatting.
    Cancellation typically occurs when the client disconnects or explicitly
    cancels a request.

    Attributes:
        reason: Optional explanation for why the execution was cancelled.
    """

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
    """
    Raised when tool parameters are invalid.

    This error covers validation failures including:
    - Parameters with invalid values or types
    - Malformed parameter definitions in the OpenAPI spec
    - Unsupported parameter configurations

    Attributes:
        parameter_name: The name of the invalid parameter, if known.
    """

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
        """Include parameter name in serialized output when available."""
        result = super().to_dict()
        if self.parameter_name:
            result["parameter_name"] = self.parameter_name
        return result


class MissingParameterError(InvalidParametersError):
    """
    Raised when a required parameter is missing.

    A specialized form of InvalidParametersError for the common case
    of missing required parameters. The error message automatically
    includes the parameter name.
    """

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
    """
    Raised when a session cannot be found.

    This error occurs when a client references a session ID that doesn't
    exist or has expired. Common in SSE transport where sessions are
    established via the initial connection.

    Attributes:
        session_id: The session ID that was not found.
    """

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
    """
    Raised when a session ID is invalid.

    This error occurs when the session ID format is invalid (e.g., not a
    valid UUID). It's distinct from SessionNotFoundError which indicates
    a valid format but non-existent session.
    """

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
    """
    Raised when there's a transport-level error.

    This error covers issues with the underlying communication layer,
    such as connection failures or message delivery problems.
    """

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
    """
    Raised for internal/framework errors that shouldn't expose details.

    This error type is used when an unexpected internal error occurs.
    It separates the public-facing message from internal details to
    prevent leaking sensitive information while still allowing detailed
    logging for debugging.

    The internal_message is stored but never included in the string
    representation or serialized output.

    Attributes:
        internal_message: Detailed error info for logging only.
    """

    def __init__(
        self,
        *,
        public_message: str = "An internal error occurred",
        internal_message: Optional[str] = None,
        tool_name: Optional[str] = None,
    ):
        self._internal_message = internal_message
        super().__init__(
            public_message,
            code=MCPErrorCode.INTERNAL_ERROR,
            tool_name=tool_name,
            details=None,  # Never expose internal details to clients
        )

    @property
    def internal_message(self) -> Optional[str]:
        """
        Get the internal message for logging purposes only.

        This should never be sent to clients or included in responses.
        """
        return self._internal_message


class ConfigurationError(MCPToolError):
    """
    Raised when there's a configuration error.

    This error indicates a problem with the MCP server configuration,
    such as invalid settings or missing required configuration values.
    These errors typically occur at startup rather than during request
    processing.
    """

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

    This function provides a safe way to convert any exception to a string
    suitable for returning to clients. For MCPToolError instances, it uses
    the built-in formatting. For other exceptions, it returns a generic
    message to avoid leaking internal details.

    Args:
        error: The exception to format.
        tool_name: Optional tool name to include in the message for
            non-MCP errors.

    Returns:
        A client-safe error message string.

    Example:
        try:
            result = await execute_tool(name, args)
        except Exception as e:
            return format_error_for_client(e, tool_name=name)
    """
    if isinstance(error, MCPToolError):
        return str(error)

    # For non-MCP errors, return a generic message with tool context
    # to avoid leaking internal implementation details
    if tool_name:
        return f"[{tool_name}] Tool execution failed"
    return "Tool execution failed"
