"""Tests for context helper functions."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastmcp import Context
from fastmcp.exceptions import ToolError

from pcp_mcp.context import get_client, get_settings


class TestGetClient:
    def test_returns_client_from_valid_context(self, mock_context: MagicMock) -> None:
        client = get_client(mock_context)
        assert client is mock_context.request_context.lifespan_context["client"]

    def test_raises_tool_error_when_request_context_is_none(self) -> None:
        ctx = MagicMock(spec=Context)
        ctx.request_context = None

        with pytest.raises(ToolError, match="Server context not available"):
            get_client(ctx)

    def test_raises_tool_error_when_lifespan_context_is_none(self) -> None:
        ctx = MagicMock(spec=Context)
        ctx.request_context = MagicMock()
        ctx.request_context.lifespan_context = None

        with pytest.raises(ToolError, match="Server context not available"):
            get_client(ctx)


class TestGetSettings:
    def test_returns_settings_from_valid_context(self, mock_context: MagicMock) -> None:
        settings = get_settings(mock_context)
        assert settings is mock_context.request_context.lifespan_context["settings"]

    def test_raises_tool_error_when_request_context_is_none(self) -> None:
        ctx = MagicMock(spec=Context)
        ctx.request_context = None

        with pytest.raises(ToolError, match="Server context not available"):
            get_settings(ctx)

    def test_raises_tool_error_when_lifespan_context_is_none(self) -> None:
        ctx = MagicMock(spec=Context)
        ctx.request_context = MagicMock()
        ctx.request_context.lifespan_context = None

        with pytest.raises(ToolError, match="Server context not available"):
            get_settings(ctx)
