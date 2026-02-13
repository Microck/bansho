from __future__ import annotations

import shlex
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any

import mcp.types as types
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.message import SessionMessage
from pydantic import AnyUrl, TypeAdapter

from mcp_sentinel.config import Settings

TransportStreams = tuple[
    MemoryObjectReceiveStream[SessionMessage | Exception],
    MemoryObjectSendStream[SessionMessage],
]

_any_url_adapter = TypeAdapter(AnyUrl)


class UpstreamConnector:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None
        self._initialize_result: types.InitializeResult | None = None

    async def initialize(self) -> types.InitializeResult:
        if self._initialize_result is not None:
            return self._initialize_result

        stack = AsyncExitStack()
        try:
            read_stream, write_stream = await stack.enter_async_context(self._open_transport())
            session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
            initialize_result = await session.initialize()
        except Exception:
            await stack.aclose()
            raise

        self._stack = stack
        self._session = session
        self._initialize_result = initialize_result
        return initialize_result

    async def aclose(self) -> None:
        if self._stack is not None:
            await self._stack.aclose()

        self._stack = None
        self._session = None
        self._initialize_result = None

    async def list_tools(
        self, params: types.PaginatedRequestParams | None = None
    ) -> types.ListToolsResult:
        session = await self._require_session()
        return await session.list_tools(params=params)

    async def call_tool(
        self, name: str, arguments: dict[str, Any] | None = None
    ) -> types.CallToolResult:
        session = await self._require_session()
        return await session.call_tool(name=name, arguments=arguments)

    async def list_resources(
        self, params: types.PaginatedRequestParams | None = None
    ) -> types.ListResourcesResult:
        session = await self._require_session()
        return await session.list_resources(params=params)

    async def read_resource(self, uri: str | AnyUrl) -> types.ReadResourceResult:
        session = await self._require_session()
        parsed_uri = _any_url_adapter.validate_python(uri)
        return await session.read_resource(parsed_uri)

    async def list_prompts(
        self, params: types.PaginatedRequestParams | None = None
    ) -> types.ListPromptsResult:
        session = await self._require_session()
        return await session.list_prompts(params=params)

    async def get_prompt(
        self, name: str, arguments: dict[str, str] | None = None
    ) -> types.GetPromptResult:
        session = await self._require_session()
        return await session.get_prompt(name=name, arguments=arguments)

    async def _require_session(self) -> ClientSession:
        if self._session is None:
            await self.initialize()

        if self._session is None:
            raise RuntimeError("Upstream session is not initialized")

        return self._session

    @asynccontextmanager
    async def _open_transport(self) -> AsyncIterator[TransportStreams]:
        if self._settings.upstream_transport == "stdio":
            server = self._build_stdio_parameters(self._settings.upstream_cmd)
            async with stdio_client(server) as streams:
                yield streams
            return

        if not self._settings.upstream_url:
            raise ValueError("UPSTREAM_URL is required when UPSTREAM_TRANSPORT=http")

        async with streamable_http_client(str(self._settings.upstream_url)) as (
            read_stream,
            write_stream,
            _,
        ):
            yield read_stream, write_stream

    @staticmethod
    def _build_stdio_parameters(command: str) -> StdioServerParameters:
        parts = shlex.split(command)
        if not parts:
            raise ValueError("UPSTREAM_CMD is required when UPSTREAM_TRANSPORT=stdio")

        return StdioServerParameters(command=parts[0], args=parts[1:])
