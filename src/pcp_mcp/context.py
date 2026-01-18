"""Context helpers for safe lifespan context access."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastmcp import Context
from fastmcp.exceptions import ToolError

if TYPE_CHECKING:
    from pcp_mcp.client import PCPClient
    from pcp_mcp.config import PCPMCPSettings


def _validate_context(ctx: Context) -> None:
    """Validate context has lifespan_context available.

    Args:
        ctx: MCP context.

    Raises:
        ToolError: If context is not available.
    """
    if ctx.request_context is None or ctx.request_context.lifespan_context is None:
        raise ToolError("Server context not available")


def get_client(ctx: Context) -> PCPClient:
    """Get PCPClient from context.

    Args:
        ctx: MCP context.

    Returns:
        The PCPClient instance.

    Raises:
        ToolError: If context is not available.
    """
    _validate_context(ctx)
    return ctx.request_context.lifespan_context["client"]


def get_settings(ctx: Context) -> PCPMCPSettings:
    """Get settings from context.

    Args:
        ctx: MCP context.

    Returns:
        The PCPMCPSettings instance.

    Raises:
        ToolError: If context is not available.
    """
    _validate_context(ctx)
    return ctx.request_context.lifespan_context["settings"]
