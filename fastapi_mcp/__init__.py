"""
FastAPI-MCP: Automatic MCP server generator for FastAPI applications.

This library provides automatic MCP (Model Context Protocol) server generation
from FastAPI applications, enabling seamless integration with AI tools and agents.

Created by Tadata Inc. (https://github.com/tadata-org)
"""

try:
    from importlib.metadata import version

    __version__ = version("fastapi-mcp")
except Exception:  # pragma: no cover
    # Fallback for local development
    __version__ = "0.0.0.dev0"  # pragma: no cover

from .server import FastApiMCP
from .types import AuthConfig, OAuthMetadata
from .errors import (
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


__all__ = [
    # Main class
    "FastApiMCP",
    # Configuration types
    "AuthConfig",
    "OAuthMetadata",
    # Error types - base class and enum
    "MCPErrorCode",
    "MCPToolError",
    # Error types - tool errors
    "ToolNotFoundError",
    "ToolExecutionError",
    "ToolTimeoutError",
    "ToolCancelledError",
    # Error types - parameter errors
    "InvalidParametersError",
    "MissingParameterError",
    # Error types - session/transport errors
    "SessionNotFoundError",
    "SessionInvalidError",
    "TransportError",
    # Error types - framework errors
    "InternalError",
    "ConfigurationError",
    # Error utilities
    "format_error_for_client",
]
