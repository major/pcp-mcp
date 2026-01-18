"""Tool registration for the PCP MCP server."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_tools(mcp: FastMCP) -> None:
    """Register all tools with the MCP server.

    Args:
        mcp: The FastMCP server instance.
    """
    from pcp_mcp.tools.metrics import register_metrics_tools

    register_metrics_tools(mcp)
