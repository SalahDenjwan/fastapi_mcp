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

    def test_error_codes_are_unique(self):
        """All error codes should have unique values."""
        values = [code.value for code in MCPErrorCode]
        assert len(values) == len(set(values)), "Error codes must be unique"


class TestMCPToolError:
    """Tests for base MCPToolError."""

    def test_basic_error(self):
        """Basic error creation."""
        error = MCPToolError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.code == MCPErrorCode.INTERNAL_ERROR
        assert error.tool_name is None
        assert error.details is None

    def test_error_with_tool_name(self):
        """Error with tool name included."""
        error = MCPToolError("Failed", tool_name="my_tool")
        assert str(error) == "[my_tool] Failed"
        assert error.tool_name == "my_tool"

    def test_error_with_all_fields(self):
        """Error with all optional fields."""
        error = MCPToolError(
            "Test error",
            code=MCPErrorCode.TOOL_EXECUTION_FAILED,
            tool_name="test_tool",
            details="Additional debug info",
        )
        assert error.message == "Test error"
        assert error.code == MCPErrorCode.TOOL_EXECUTION_FAILED
        assert error.tool_name == "test_tool"
        assert error.details == "Additional debug info"

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

    def test_error_is_exception(self):
        """MCPToolError should be a proper Exception subclass."""
        error = MCPToolError("Test")
        assert isinstance(error, Exception)

        # Should be raiseable and catchable
        with pytest.raises(MCPToolError) as exc_info:
            raise error
        assert exc_info.value is error

    def test_error_inheritance_catchable(self):
        """All MCP errors should be catchable with MCPToolError."""
        errors = [
            ToolNotFoundError("tool"),
            ToolExecutionError("failed"),
            ToolTimeoutError(),
            ToolCancelledError(),
            InvalidParametersError("bad param"),
            MissingParameterError("param"),
            SessionNotFoundError(),
            SessionInvalidError(),
            TransportError("transport issue"),
            InternalError(),
            ConfigurationError("config issue"),
        ]

        for error in errors:
            assert isinstance(error, MCPToolError)


class TestToolNotFoundError:
    """Tests for ToolNotFoundError."""

    def test_creates_with_tool_name(self):
        """Should include tool name in message."""
        error = ToolNotFoundError("unknown_tool")
        assert str(error) == "[unknown_tool] Tool not found: unknown_tool"
        assert error.code == MCPErrorCode.TOOL_NOT_FOUND
        assert error.tool_name == "unknown_tool"

    def test_with_details(self):
        """Should store details for logging."""
        error = ToolNotFoundError("missing_tool", details="Available: tool1, tool2")
        assert error.details == "Available: tool1, tool2"

    def test_to_dict_includes_tool_name(self):
        """Serialized dict should include tool name."""
        error = ToolNotFoundError("my_tool")
        result = error.to_dict()
        assert result["tool_name"] == "my_tool"
        assert result["code"] == MCPErrorCode.TOOL_NOT_FOUND.value


class TestToolExecutionError:
    """Tests for ToolExecutionError."""

    def test_basic_execution_error(self):
        """Basic execution error."""
        error = ToolExecutionError("Request failed", tool_name="api_call")
        assert "[api_call]" in str(error)
        assert error.code == MCPErrorCode.TOOL_EXECUTION_FAILED
        assert error.status_code is None

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

    def test_execution_error_without_status_code(self):
        """Execution error without status code should not include it in dict."""
        error = ToolExecutionError("Failed", tool_name="tool")
        result = error.to_dict()
        assert "status_code" not in result

    def test_client_error_status_codes(self):
        """Should handle 4xx status codes."""
        error = ToolExecutionError("Not found", tool_name="get_user", status_code=404)
        assert error.status_code == 404

    def test_server_error_status_codes(self):
        """Should handle 5xx status codes."""
        error = ToolExecutionError("Server error", tool_name="create_item", status_code=503)
        assert error.status_code == 503


class TestToolTimeoutError:
    """Tests for ToolTimeoutError."""

    def test_basic_timeout(self):
        """Basic timeout error."""
        error = ToolTimeoutError(tool_name="slow_tool")
        assert "[slow_tool]" in str(error)
        assert "timed out" in str(error)
        assert error.code == MCPErrorCode.TOOL_TIMEOUT
        assert error.timeout_seconds is None

    def test_timeout_with_duration(self):
        """Timeout with specific duration."""
        error = ToolTimeoutError(tool_name="slow_tool", timeout_seconds=30.0)
        assert "30" in str(error)
        assert error.timeout_seconds == 30.0

    def test_timeout_without_tool_name(self):
        """Timeout without tool name."""
        error = ToolTimeoutError()
        assert str(error) == "Tool execution timed out"
        assert error.tool_name is None

    def test_timeout_with_float_seconds(self):
        """Timeout with fractional seconds."""
        error = ToolTimeoutError(timeout_seconds=0.5)
        assert "0.5" in str(error)


class TestToolCancelledError:
    """Tests for ToolCancelledError."""

    def test_basic_cancellation(self):
        """Basic cancellation error."""
        error = ToolCancelledError(tool_name="running_tool")
        assert "[running_tool]" in str(error)
        assert "cancelled" in str(error)
        assert error.code == MCPErrorCode.TOOL_CANCELLED
        assert error.reason is None

    def test_cancellation_with_reason(self):
        """Cancellation with reason."""
        error = ToolCancelledError(tool_name="running_tool", reason="user request")
        assert "user request" in str(error)
        assert error.reason == "user request"

    def test_cancellation_without_tool_name(self):
        """Cancellation without tool name."""
        error = ToolCancelledError(reason="timeout")
        assert str(error) == "Tool execution was cancelled: timeout"


class TestInvalidParametersError:
    """Tests for InvalidParametersError."""

    def test_basic_invalid_params(self):
        """Basic invalid parameters error."""
        error = InvalidParametersError("Invalid value for parameter", tool_name="my_tool")
        assert error.code == MCPErrorCode.INVALID_PARAMETERS
        assert error.parameter_name is None

    def test_with_parameter_name(self):
        """Invalid parameters with specific parameter name."""
        error = InvalidParametersError(
            "Must be positive",
            tool_name="my_tool",
            parameter_name="count",
        )
        assert error.parameter_name == "count"
        result = error.to_dict()
        assert result["parameter_name"] == "count"

    def test_without_parameter_name(self):
        """Invalid parameters without parameter name should not include it in dict."""
        error = InvalidParametersError("Bad params", tool_name="tool")
        result = error.to_dict()
        assert "parameter_name" not in result


class TestMissingParameterError:
    """Tests for MissingParameterError."""

    def test_missing_parameter(self):
        """Missing parameter error."""
        error = MissingParameterError("user_id", tool_name="get_user")
        assert "user_id" in str(error)
        assert "Missing required parameter" in str(error)
        assert error.code == MCPErrorCode.MISSING_PARAMETER
        assert error.parameter_name == "user_id"

    def test_inherits_from_invalid_parameters(self):
        """Should inherit from InvalidParametersError."""
        error = MissingParameterError("param")
        assert isinstance(error, InvalidParametersError)

    def test_to_dict_includes_parameter_name(self):
        """Serialized dict should include parameter name."""
        error = MissingParameterError("item_id", tool_name="get_item")
        result = error.to_dict()
        assert result["parameter_name"] == "item_id"
        assert result["code"] == MCPErrorCode.MISSING_PARAMETER.value


class TestSessionNotFoundError:
    """Tests for SessionNotFoundError."""

    def test_basic_session_not_found(self):
        """Basic session not found error."""
        error = SessionNotFoundError()
        assert "Session not found" in str(error)
        assert error.code == MCPErrorCode.SESSION_NOT_FOUND
        assert error.session_id is None

    def test_session_not_found_with_id(self):
        """Session not found with specific ID."""
        error = SessionNotFoundError(session_id="abc123")
        assert "abc123" in str(error)
        assert error.session_id == "abc123"

    def test_no_tool_name(self):
        """Session errors don't have tool names."""
        error = SessionNotFoundError()
        assert error.tool_name is None


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

    def test_with_details(self):
        """Transport error with details."""
        error = TransportError("Connection failed", details="Host unreachable")
        assert error.details == "Host unreachable"


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
        assert "internal_message" not in result

    def test_default_public_message(self):
        """Default public message should be generic."""
        error = InternalError(internal_message="secret details")
        assert "internal error" in str(error).lower()

    def test_details_always_none(self):
        """Details should always be None to prevent leaking."""
        error = InternalError(
            public_message="Error",
            internal_message="Secret",
        )
        assert error.details is None

    def test_with_tool_name(self):
        """Internal error can include tool name."""
        error = InternalError(
            public_message="Error",
            internal_message="Crash",
            tool_name="buggy_tool",
        )
        assert "[buggy_tool]" in str(error)
        assert "Crash" not in str(error)


class TestConfigurationError:
    """Tests for ConfigurationError."""

    def test_configuration_error(self):
        """Configuration error."""
        error = ConfigurationError("Missing API key")
        assert "Missing API key" in str(error)
        assert error.code == MCPErrorCode.CONFIGURATION_ERROR

    def test_with_details(self):
        """Configuration error with details."""
        error = ConfigurationError("Invalid config", details="Expected dict, got list")
        assert error.details == "Expected dict, got list"


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

    def test_formats_all_mcp_error_types(self):
        """Should format all MCPToolError subclasses correctly."""
        errors_and_expected = [
            (ToolNotFoundError("tool"), "Tool not found"),
            (ToolExecutionError("exec failed"), "exec failed"),
            (ToolTimeoutError(), "timed out"),
            (ToolCancelledError(), "cancelled"),
            (InvalidParametersError("bad"), "bad"),
            (MissingParameterError("x"), "Missing"),
            (SessionNotFoundError(), "Session not found"),
            (SessionInvalidError(), "Invalid session"),
            (TransportError("conn"), "conn"),
            (InternalError(), "internal error"),
            (ConfigurationError("cfg"), "cfg"),
        ]

        for error, expected_substr in errors_and_expected:
            result = format_error_for_client(error)
            assert expected_substr.lower() in result.lower(), f"Expected '{expected_substr}' in '{result}'"

    def test_does_not_leak_exception_traceback(self):
        """Generic exceptions should not leak traceback info."""
        try:
            raise ValueError("secret: password=123")
        except ValueError as e:
            result = format_error_for_client(e)
            assert "secret" not in result
            assert "password" not in result
            assert "123" not in result


class TestErrorChaining:
    """Tests for error chaining and exception hierarchy."""

    def test_can_chain_exceptions(self):
        """MCP errors should support exception chaining."""
        original = ValueError("Original cause")
        error = ToolExecutionError("Wrapper", tool_name="tool")

        try:
            try:
                raise original
            except ValueError:
                raise error from original
        except ToolExecutionError as e:
            assert e.__cause__ is original

    def test_catch_by_base_class(self):
        """Should be able to catch all MCP errors with base class."""
        errors = [
            ToolNotFoundError("t"),
            ToolExecutionError("e"),
            InvalidParametersError("p"),
        ]

        for error in errors:
            try:
                raise error
            except MCPToolError as e:
                assert e is error  # Caught correctly
            except Exception:
                pytest.fail(f"Should have caught {type(error).__name__} as MCPToolError")
