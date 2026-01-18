"""Pytest fixtures for pcp-mcp tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeAlias
from unittest.mock import AsyncMock, MagicMock

import pytest

from pcp_mcp.client import PCPClient
from pcp_mcp.config import PCPMCPSettings

RegisterFn: TypeAlias = Callable[[MagicMock], None]
ToolDict: TypeAlias = dict[str, Callable[..., Any]]
ResourceDict: TypeAlias = dict[str, Callable[..., Any]]


@pytest.fixture
def mock_settings() -> PCPMCPSettings:
    """Create mock settings for testing."""
    return PCPMCPSettings(
        host="localhost",
        port=44322,
        target_host="localhost",
    )


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create a mock PCPClient."""
    client = AsyncMock(spec=PCPClient)
    client.target_host = "localhost"
    client.context_id = 12345
    return client


@pytest.fixture
def mock_lifespan_context(
    mock_client: AsyncMock,
    mock_settings: PCPMCPSettings,
) -> dict[str, Any]:
    """Create mock lifespan context."""
    return {"client": mock_client, "settings": mock_settings}


@pytest.fixture
def mock_context(mock_lifespan_context: dict[str, Any]) -> MagicMock:
    """Create a mock MCP Context."""
    from fastmcp import Context

    ctx = MagicMock(spec=Context)
    ctx.request_context = MagicMock()
    ctx.request_context.lifespan_context = mock_lifespan_context
    return ctx


@pytest.fixture
def capture_tools() -> Callable[[RegisterFn], ToolDict]:
    def factory(register_fn: RegisterFn) -> ToolDict:
        tools: ToolDict = {}

        def capture_tool():
            def decorator(fn):
                tools[fn.__name__] = fn
                return fn

            return decorator

        mcp = MagicMock()
        mcp.tool = capture_tool
        register_fn(mcp)
        return tools

    return factory


@pytest.fixture
def capture_resources() -> Callable[[RegisterFn], ResourceDict]:
    def factory(register_fn: RegisterFn) -> ResourceDict:
        resources: ResourceDict = {}

        def capture_resource(uri: str):
            def decorator(fn):
                resources[uri] = fn
                return fn

            return decorator

        mcp = MagicMock()
        mcp.resource = capture_resource
        register_fn(mcp)
        return resources

    return factory
