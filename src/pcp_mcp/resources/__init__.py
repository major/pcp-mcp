"""Resource registration for the PCP MCP server."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_resources(mcp: FastMCP) -> None:
    """Register all resources with the MCP server.

    Args:
        mcp: The FastMCP server instance.
    """
    from pcp_mcp.resources.catalog import register_catalog_resources
    from pcp_mcp.resources.health import register_health_resources
    from pcp_mcp.resources.metrics import register_metrics_resources

    register_health_resources(mcp)
    register_metrics_resources(mcp)
    register_catalog_resources(mcp)
