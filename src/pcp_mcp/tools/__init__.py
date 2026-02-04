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
    from pcp_mcp.tools.metrics import (
        describe_metric,
        query_metrics,
        search_metrics,
    )
    from pcp_mcp.tools.system import register_system_tools

    mcp.add_tool(query_metrics)
    mcp.add_tool(search_metrics)
    mcp.add_tool(describe_metric)
    register_system_tools(mcp)
