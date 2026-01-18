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
    pass
