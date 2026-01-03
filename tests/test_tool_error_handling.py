"""
Tests for tool execution error handling in server.py.

These tests verify that different error conditions during tool execution
are properly caught and converted to the appropriate MCP error types.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI

from fastapi_mcp import FastApiMCP
from fastapi_mcp.errors import (
    ToolNotFoundError,
    ToolExecutionError,
    ToolTimeoutError,
    ToolCancelledError,
    InvalidParametersError,
)


@pytest.fixture
def mcp(simple_fastapi_app: FastAPI):
    """Create an MCP instance using the shared simple_fastapi_app fixture."""
    return FastApiMCP(simple_fastapi_app)


class TestToolNotFound:
    """Tests for unknown tool handling."""

    @pytest.mark.asyncio
    async def test_unknown_tool_raises_tool_not_found(self, mcp):
        """Requesting an unknown tool should raise ToolNotFoundError."""
        mock_client = AsyncMock()

        with pytest.raises(ToolNotFoundError) as exc_info:
            await mcp._execute_api_tool(
                client=mock_client,
                tool_name="nonexistent_tool",
                arguments={},
                operation_map=mcp.operation_map,
            )

        assert exc_info.value.tool_name == "nonexistent_tool"
        assert "Tool not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_tool_not_found_error_format(self, mcp):
        """ToolNotFoundError should have correct format."""
        mock_client = AsyncMock()

        try:
            await mcp._execute_api_tool(
                client=mock_client,
                tool_name="missing_tool",
                arguments={},
                operation_map=mcp.operation_map,
            )
        except ToolNotFoundError as e:
            # Should include tool name in message
            assert "[missing_tool]" in str(e)
            # Should have correct error code
            assert e.code.value == 1001


class TestHttpStatusErrors:
    """Tests for HTTP status code handling."""

    @pytest.mark.asyncio
    async def test_4xx_raises_tool_execution_error(self, mcp):
        """4xx responses should raise ToolExecutionError with status code."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = '{"detail": "Not found"}'
        mock_response.json.return_value = {"detail": "Not found"}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with pytest.raises(ToolExecutionError) as exc_info:
            await mcp._execute_api_tool(
                client=mock_client,
                tool_name="get_item",
                arguments={"item_id": 999},
                operation_map=mcp.operation_map,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.tool_name == "get_item"
        assert "404" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_5xx_raises_tool_execution_error(self, mcp):
        """5xx responses should raise ToolExecutionError with status code."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.json.return_value = {"error": "Internal error"}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with pytest.raises(ToolExecutionError) as exc_info:
            await mcp._execute_api_tool(
                client=mock_client,
                tool_name="get_item",
                arguments={"item_id": 1},
                operation_map=mcp.operation_map,
            )

        assert exc_info.value.status_code == 500
        assert "[get_item]" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_various_error_status_codes(self, mcp):
        """Test various error status codes are properly captured."""
        test_cases = [
            (400, "Bad Request"),
            (401, "Unauthorized"),
            (403, "Forbidden"),
            (404, "Not Found"),
            (422, "Unprocessable Entity"),
            (500, "Internal Server Error"),
            (502, "Bad Gateway"),
            (503, "Service Unavailable"),
        ]

        for status_code, _ in test_cases:
            mock_response = MagicMock()
            mock_response.status_code = status_code
            mock_response.text = f"Error {status_code}"
            mock_response.json.return_value = {"error": f"Error {status_code}"}

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response

            with pytest.raises(ToolExecutionError) as exc_info:
                await mcp._execute_api_tool(
                    client=mock_client,
                    tool_name="get_item",
                    arguments={"item_id": 1},
                    operation_map=mcp.operation_map,
                )

            assert exc_info.value.status_code == status_code


class TestAsyncErrors:
    """Tests for async error handling (timeout, cancellation)."""

    @pytest.mark.asyncio
    async def test_timeout_raises_tool_timeout_error(self, mcp):
        """asyncio.TimeoutError should be converted to ToolTimeoutError."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = asyncio.TimeoutError()

        with pytest.raises(ToolTimeoutError) as exc_info:
            await mcp._execute_api_tool(
                client=mock_client,
                tool_name="get_item",
                arguments={"item_id": 1},
                operation_map=mcp.operation_map,
            )

        assert exc_info.value.tool_name == "get_item"
        assert "timed out" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_cancellation_raises_tool_cancelled_error(self, mcp):
        """asyncio.CancelledError should be converted to ToolCancelledError."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = asyncio.CancelledError()

        with pytest.raises(ToolCancelledError) as exc_info:
            await mcp._execute_api_tool(
                client=mock_client,
                tool_name="get_item",
                arguments={"item_id": 1},
                operation_map=mcp.operation_map,
            )

        assert exc_info.value.tool_name == "get_item"
        assert "cancelled" in str(exc_info.value).lower()


class TestUnexpectedErrors:
    """Tests for unexpected/generic error handling."""

    @pytest.mark.asyncio
    async def test_unexpected_error_wrapped_in_tool_execution_error(self, mcp):
        """Unexpected exceptions should be wrapped in ToolExecutionError."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = RuntimeError("Unexpected failure")

        with pytest.raises(ToolExecutionError) as exc_info:
            await mcp._execute_api_tool(
                client=mock_client,
                tool_name="get_item",
                arguments={"item_id": 1},
                operation_map=mcp.operation_map,
            )

        # Should wrap the error
        assert exc_info.value.tool_name == "get_item"
        # Original error should be chained
        assert exc_info.value.__cause__ is not None

    @pytest.mark.asyncio
    async def test_unexpected_error_does_not_leak_details(self, mcp):
        """Unexpected exceptions should not leak internal details."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = RuntimeError("secret_password=12345")

        with pytest.raises(ToolExecutionError) as exc_info:
            await mcp._execute_api_tool(
                client=mock_client,
                tool_name="get_item",
                arguments={"item_id": 1},
                operation_map=mcp.operation_map,
            )

        # The string representation should not contain the secret
        error_str = str(exc_info.value)
        assert "secret_password" not in error_str
        assert "12345" not in error_str


class TestMcpErrorsReraised:
    """Tests that MCP errors are re-raised as-is."""

    @pytest.mark.asyncio
    async def test_tool_not_found_not_wrapped(self, mcp):
        """ToolNotFoundError should not be wrapped again."""
        # This is tested implicitly - calling with unknown tool
        mock_client = AsyncMock()

        with pytest.raises(ToolNotFoundError):
            await mcp._execute_api_tool(
                client=mock_client,
                tool_name="unknown",
                arguments={},
                operation_map=mcp.operation_map,
            )

    @pytest.mark.asyncio
    async def test_tool_execution_error_not_wrapped(self, mcp):
        """ToolExecutionError raised during execution should not be wrapped."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Error"
        mock_response.json.return_value = {"error": "Error"}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        with pytest.raises(ToolExecutionError) as exc_info:
            await mcp._execute_api_tool(
                client=mock_client,
                tool_name="get_item",
                arguments={"item_id": 1},
                operation_map=mcp.operation_map,
            )

        # Should not have a cause (not wrapped)
        assert exc_info.value.__cause__ is None


class TestInvalidHttpMethod:
    """Tests for unsupported HTTP method handling."""

    @pytest.mark.asyncio
    async def test_unsupported_method_raises_invalid_parameters(self, mcp):
        """Unsupported HTTP method should raise InvalidParametersError."""
        # Create a mock operation with an unsupported method
        mock_operation_map = {
            "custom_tool": {
                "path": "/custom",
                "method": "OPTIONS",  # Not supported
                "parameters": [],
            }
        }

        mock_client = AsyncMock()

        with pytest.raises(InvalidParametersError) as exc_info:
            await mcp._execute_api_tool(
                client=mock_client,
                tool_name="custom_tool",
                arguments={},
                operation_map=mock_operation_map,
            )

        assert "OPTIONS" in str(exc_info.value)


class TestSuccessfulExecution:
    """Tests for successful tool execution (no errors)."""

    @pytest.mark.asyncio
    async def test_successful_get_request(self, mcp):
        """Successful GET request should return content without error."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"id": 1, "name": "Test"}'
        mock_response.json.return_value = {"id": 1, "name": "Test"}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        result = await mcp._execute_api_tool(
            client=mock_client,
            tool_name="get_item",
            arguments={"item_id": 1},
            operation_map=mcp.operation_map,
        )

        assert len(result) == 1
        assert "Test" in result[0].text

    @pytest.mark.asyncio
    async def test_successful_post_request(self, mcp):
        """Successful POST request should return content without error."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.text = '{"id": 1}'
        mock_response.json.return_value = {"id": 1}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        result = await mcp._execute_api_tool(
            client=mock_client,
            tool_name="create_item",
            arguments={"item": {"name": "New"}},
            operation_map=mcp.operation_map,
        )

        assert len(result) == 1


class TestJsonDecodeHandling:
    """Tests for JSON decode error handling."""

    @pytest.mark.asyncio
    async def test_non_json_response_handled_gracefully(self, mcp):
        """Non-JSON response should be handled without error."""
        import json

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Plain text response"
        # Use json.JSONDecodeError which is what the code catches
        mock_response.json.side_effect = json.JSONDecodeError("No JSON", "", 0)

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response

        result = await mcp._execute_api_tool(
            client=mock_client,
            tool_name="get_item",
            arguments={"item_id": 1},
            operation_map=mcp.operation_map,
        )

        # Should fall back to text
        assert len(result) == 1
        assert "Plain text response" in result[0].text
