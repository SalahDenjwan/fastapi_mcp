"""
SSE (Server-Sent Events) transport for MCP server.

This module provides a FastAPI-native implementation of SSE message handling
for the MCP protocol. It extends the base SseServerTransport to integrate
properly with FastAPI's request/response lifecycle.

Error Handling:
    - Missing session_id -> 400 (Bad Request)
    - Invalid session_id format -> 400 (Bad Request)
    - Session not found -> 404 (Not Found)
    - Invalid JSON-RPC message -> 400 + JSON-RPC error via SSE stream
    - Message send failures -> Logged but not propagated (fire-and-forget)

The message handling uses FastAPI's BackgroundTasks to avoid blocking the
HTTP response while ensuring messages are delivered through the SSE stream.
"""

from uuid import UUID
import logging
from typing import Union

from anyio.streams.memory import MemoryObjectSendStream
from fastapi import Request, Response, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from mcp.shared.message import SessionMessage, ServerMessageMetadata
from pydantic import ValidationError
from mcp.server.sse import SseServerTransport
from mcp.types import JSONRPCMessage, JSONRPCError, ErrorData


logger = logging.getLogger(__name__)


class FastApiSseTransport(SseServerTransport):
    async def handle_fastapi_post_message(self, request: Request) -> Response:
        """
        A reimplementation of the handle_post_message method of SseServerTransport
        that integrates better with FastAPI.

        A few good reasons for doing this:
        1. Avoid mounting a whole Starlette app and instead use a more FastAPI-native
           approach. Mounting has some known issues and limitations.
        2. Avoid re-constructing the scope, receive, and send from the request, as done
           in the original implementation.
        3. Use FastAPI's native response handling mechanisms and exception patterns to
           avoid unexpected rabbit holes.

        The combination of mounting a whole Starlette app and reconstructing the scope
        and send from the request proved to be especially error-prone for us when using
        tracing tools like Sentry, which had destructive effects on the request object
        when using the original implementation.
        """

        logger.debug("Handling POST message SSE")

        session_id_param = request.query_params.get("session_id")
        if session_id_param is None:
            logger.warning("Received request without session_id")
            raise HTTPException(status_code=400, detail="Missing required parameter: session_id")

        try:
            session_id = UUID(hex=session_id_param)
            logger.debug(f"Parsed session ID: {session_id}")
        except ValueError:
            logger.warning(f"Received invalid session ID: {session_id_param}")
            raise HTTPException(status_code=400, detail="Invalid session ID format")

        writer = self._read_stream_writers.get(session_id)
        if not writer:
            logger.warning(f"Could not find session for ID: {session_id}")
            raise HTTPException(status_code=404, detail="Session not found or expired")

        body = await request.body()
        logger.debug(f"Received JSON: {body.decode()}")

        try:
            message = JSONRPCMessage.model_validate_json(body)

            logger.debug(f"Validated client message: {message}")
        except ValidationError as err:
            logger.error(f"Failed to parse message: {err}")
            # Create background task to send error
            background_tasks = BackgroundTasks()
            background_tasks.add_task(self._send_message_safely, writer, err)
            response = JSONResponse(
                content={"error": "Invalid JSON-RPC message format"},
                status_code=400,
            )
            response.background = background_tasks
            return response
        except Exception as e:
            logger.error(f"Error processing request body: {e}")
            raise HTTPException(status_code=400, detail="Failed to parse request body")

        # Create background task to send message with proper request context metadata
        background_tasks = BackgroundTasks()
        metadata = ServerMessageMetadata(request_context=request)
        session_message = SessionMessage(message, metadata=metadata)
        background_tasks.add_task(self._send_message_safely, writer, session_message)
        logger.debug("Accepting message, will send in background")

        # Return response with background task
        response = JSONResponse(content={"message": "Accepted"}, status_code=202)
        response.background = background_tasks
        return response

    async def _send_message_safely(
        self, writer: MemoryObjectSendStream[SessionMessage], message: Union[SessionMessage, ValidationError]
    ) -> None:
        """
        Send a message to the writer, avoiding ASGI race conditions.

        This method is designed to be called from a BackgroundTask. It handles
        two types of messages:
        1. SessionMessage: Forwarded directly to the SSE stream
        2. ValidationError: Converted to a JSON-RPC error and sent to the stream

        Errors during sending are logged but not propagated because:
        - The HTTP response has already been sent (202 Accepted)
        - Propagating would have no effect on the client
        - The SSE stream may have been closed by the client
        """

        try:
            logger.debug(f"Sending message to writer from background task: {message}")

            if isinstance(message, ValidationError):
                # Convert ValidationError to JSONRPCError with clear messaging
                error_data = ErrorData(
                    code=-32700,  # Parse error code in JSON-RPC
                    message="Invalid JSON-RPC message format",
                    data={"details": "The request body could not be parsed as a valid JSON-RPC message"},
                )
                json_rpc_error = JSONRPCError(
                    jsonrpc="2.0",
                    id="unknown",  # We don't know the ID from the invalid request
                    error=error_data,
                )
                error_message = SessionMessage(JSONRPCMessage(root=json_rpc_error))
                await writer.send(error_message)
            else:
                await writer.send(message)
        except Exception as e:
            # Log the error but don't propagate - the message is already being handled
            logger.error(f"Failed to send message through SSE transport: {e}")
