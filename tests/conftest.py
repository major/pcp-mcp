"""Pytest fixtures for pcp-mcp tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from pcp_mcp.client import PCPClient
from pcp_mcp.config import PCPMCPSettings


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
