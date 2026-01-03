"""Tests for the MCP error types module."""

import pytest
from fastapi_mcp.errors import (
    MCPErrorCode,
    MCPToolError,
    ToolNotFoundError,
    ToolExecutionError,
    ToolTimeoutError,
    ToolCancelledError,
    InvalidParametersError,
    MissingParameterError,
    SessionNotFoundError,
    SessionInvalidError,
    TransportError,
    InternalError,
    ConfigurationError,
    format_error_for_client,
)


class TestMCPErrorCode:
    """Tests for MCPErrorCode enum."""

    def test_error_codes_have_expected_values(self):
        """Error codes should be in expected ranges."""
        # Tool execution errors (1xxx)
        assert MCPErrorCode.TOOL_NOT_FOUND.value == 1001
        assert MCPErrorCode.TOOL_EXECUTION_FAILED.value == 1002
        assert MCPErrorCode.TOOL_TIMEOUT.value == 1003
        assert MCPErrorCode.TOOL_CANCELLED.value == 1004

        # Parameter/validation errors (2xxx)
        assert MCPErrorCode.INVALID_PARAMETERS.value == 2001
        assert MCPErrorCode.MISSING_PARAMETER.value == 2002

        # Transport/session errors (3xxx)
        assert MCPErrorCode.SESSION_NOT_FOUND.value == 3001
        assert MCPErrorCode.SESSION_INVALID.value == 3002
        assert MCPErrorCode.TRANSPORT_ERROR.value == 3003

        # Framework/internal errors (4xxx)
        assert MCPErrorCode.INTERNAL_ERROR.value == 4001
        assert MCPErrorCode.CONFIGURATION_ERROR.value == 4002


class TestMCPToolError:
    """Tests for base MCPToolError."""

    def test_basic_error(self):
        """Basic error creation."""
        error = MCPToolError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.code == MCPErrorCode.INTERNAL_ERROR
        assert error.tool_name is None

    def test_error_with_tool_name(self):
        """Error with tool name included."""
        error = MCPToolError("Failed", tool_name="my_tool")
        assert str(error) == "[my_tool] Failed"
        assert error.tool_name == "my_tool"

    def test_to_dict(self):
        """Error serialization to dict."""
        error = MCPToolError(
            "Test error",
            code=MCPErrorCode.TOOL_EXECUTION_FAILED,
            tool_name="test_tool",
        )
        result = error.to_dict()
        assert result["error"] == "Test error"
        assert result["code"] == 1002
        assert result["code_name"] == "TOOL_EXECUTION_FAILED"
        assert result["tool_name"] == "test_tool"

    def test_to_dict_without_tool_name(self):
        """Error serialization without tool name."""
        error = MCPToolError("Test error")
        result = error.to_dict()
        assert "tool_name" not in result


class TestToolNotFoundError:
    """Tests for ToolNotFoundError."""

    def test_creates_with_tool_name(self):
        """Should include tool name in message."""
        error = ToolNotFoundError("unknown_tool")
        assert str(error) == "[unknown_tool] Tool not found: unknown_tool"
        assert error.code == MCPErrorCode.TOOL_NOT_FOUND
        assert error.tool_name == "unknown_tool"


class TestToolExecutionError:
    """Tests for ToolExecutionError."""

    def test_basic_execution_error(self):
        """Basic execution error."""
        error = ToolExecutionError("Request failed", tool_name="api_call")
        assert "[api_call]" in str(error)
        assert error.code == MCPErrorCode.TOOL_EXECUTION_FAILED

    def test_execution_error_with_status_code(self):
        """Execution error with HTTP status code."""
        error = ToolExecutionError(
            "Request failed with status 500",
            tool_name="api_call",
            status_code=500,
        )
        assert error.status_code == 500
        result = error.to_dict()
        assert result["status_code"] == 500


class TestToolTimeoutError:
    """Tests for ToolTimeoutError."""

    def test_basic_timeout(self):
        """Basic timeout error."""
        error = ToolTimeoutError(tool_name="slow_tool")
        assert "[slow_tool]" in str(error)
        assert "timed out" in str(error)
        assert error.code == MCPErrorCode.TOOL_TIMEOUT

    def test_timeout_with_duration(self):
        """Timeout with specific duration."""
        error = ToolTimeoutError(tool_name="slow_tool", timeout_seconds=30.0)
        assert "30" in str(error)
        assert error.timeout_seconds == 30.0


class TestToolCancelledError:
    """Tests for ToolCancelledError."""

    def test_basic_cancellation(self):
        """Basic cancellation error."""
        error = ToolCancelledError(tool_name="running_tool")
        assert "[running_tool]" in str(error)
        assert "cancelled" in str(error)
        assert error.code == MCPErrorCode.TOOL_CANCELLED

    def test_cancellation_with_reason(self):
        """Cancellation with reason."""
        error = ToolCancelledError(tool_name="running_tool", reason="user request")
        assert "user request" in str(error)


class TestInvalidParametersError:
    """Tests for InvalidParametersError."""

    def test_basic_invalid_params(self):
        """Basic invalid parameters error."""
        error = InvalidParametersError("Invalid value for parameter", tool_name="my_tool")
        assert error.code == MCPErrorCode.INVALID_PARAMETERS

    def test_with_parameter_name(self):
        """Invalid parameters with specific parameter name."""
        error = InvalidParametersError(
            "Must be positive",
            tool_name="my_tool",
            parameter_name="count",
        )
        result = error.to_dict()
        assert result["parameter_name"] == "count"


class TestMissingParameterError:
    """Tests for MissingParameterError."""

    def test_missing_parameter(self):
        """Missing parameter error."""
        error = MissingParameterError("user_id", tool_name="get_user")
        assert "user_id" in str(error)
        assert error.code == MCPErrorCode.MISSING_PARAMETER
        assert error.parameter_name == "user_id"


class TestSessionNotFoundError:
    """Tests for SessionNotFoundError."""

    def test_basic_session_not_found(self):
        """Basic session not found error."""
        error = SessionNotFoundError()
        assert "Session not found" in str(error)
        assert error.code == MCPErrorCode.SESSION_NOT_FOUND

    def test_session_not_found_with_id(self):
        """Session not found with specific ID."""
        error = SessionNotFoundError(session_id="abc123")
        assert "abc123" in str(error)


class TestSessionInvalidError:
    """Tests for SessionInvalidError."""

    def test_basic_session_invalid(self):
        """Basic session invalid error."""
        error = SessionInvalidError()
        assert "Invalid session ID" in str(error)
        assert error.code == MCPErrorCode.SESSION_INVALID

    def test_session_invalid_with_reason(self):
        """Session invalid with custom reason."""
        error = SessionInvalidError("Session ID must be a UUID")
        assert "UUID" in str(error)


class TestTransportError:
    """Tests for TransportError."""

    def test_transport_error(self):
        """Basic transport error."""
        error = TransportError("Connection lost")
        assert "Connection lost" in str(error)
        assert error.code == MCPErrorCode.TRANSPORT_ERROR


class TestInternalError:
    """Tests for InternalError."""

    def test_internal_error_hides_details(self):
        """Internal error should not expose internal details."""
        error = InternalError(
            public_message="Something went wrong",
            internal_message="NullPointerException at line 42",
        )
        # Public message visible
        assert str(error) == "Something went wrong"
        # Internal message accessible for logging
        assert error.internal_message == "NullPointerException at line 42"
        # Internal message not in dict
        result = error.to_dict()
        assert "NullPointerException" not in str(result)

    def test_default_public_message(self):
        """Default public message should be generic."""
        error = InternalError(internal_message="secret details")
        assert "internal error" in str(error).lower()


class TestConfigurationError:
    """Tests for ConfigurationError."""

    def test_configuration_error(self):
        """Configuration error."""
        error = ConfigurationError("Missing API key")
        assert "Missing API key" in str(error)
        assert error.code == MCPErrorCode.CONFIGURATION_ERROR


class TestFormatErrorForClient:
    """Tests for format_error_for_client function."""

    def test_formats_mcp_error(self):
        """Should use MCPToolError's built-in formatting."""
        error = ToolExecutionError("Failed", tool_name="my_tool")
        result = format_error_for_client(error)
        assert "[my_tool]" in result
        assert "Failed" in result

    def test_formats_generic_exception_without_tool(self):
        """Should return generic message for non-MCP errors."""
        error = ValueError("Internal details")
        result = format_error_for_client(error)
        assert "Tool execution failed" in result
        assert "Internal details" not in result

    def test_formats_generic_exception_with_tool(self):
        """Should include tool name for non-MCP errors."""
        error = RuntimeError("Crash")
        result = format_error_for_client(error, tool_name="broken_tool")
        assert "[broken_tool]" in result
        assert "Crash" not in result
