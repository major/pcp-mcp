"""FastMCP server setup and lifespan management."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import FastMCP

from pcp_mcp.client import PCPClient
from pcp_mcp.config import PCPMCPSettings


@asynccontextmanager
async def lifespan(mcp: FastMCP) -> AsyncIterator[dict[str, Any]]:
    """Manage PCPClient lifecycle.

    Creates a PCPClient for the duration of the server's lifetime,
    making it available to all tools and resources via the context.

    Args:
        mcp: The FastMCP server instance.

    Yields:
        Context dict with client and settings.
    """
    settings = PCPMCPSettings()

    async with PCPClient(
        base_url=settings.base_url,
        target_host=settings.target_host,
        auth=settings.auth,
        timeout=settings.timeout,
    ) as client:
        yield {
            "client": client,
            "settings": settings,
        }


def create_server() -> FastMCP:
    """Create and configure the MCP server.

    Returns:
        Configured FastMCP server instance.
    """
    settings = PCPMCPSettings()

    mcp = FastMCP(
        name="pcp",
        instructions=f"""PCP MCP Server - Performance Co-Pilot Metrics

Monitoring target: {settings.target_host}
pmproxy endpoint: {settings.base_url}

Query live system metrics from Performance Co-Pilot. Use tools for specific
metric queries or browse resources for read-only data access.

Tools:
- query_metrics: Fetch specific metrics by name
- search_metrics: Find metrics matching a pattern
- describe_metric: Get metadata for a metric
- get_system_snapshot: System overview (CPU, memory, disk, network)
- get_process_top: Top processes by resource consumption

Resources:
- pcp://health - Quick system health summary
- pcp://metrics/{{pattern}} - Browse metrics matching pattern
""",
        lifespan=lifespan,
    )

    from pcp_mcp.resources import register_resources
    from pcp_mcp.tools import register_tools

    register_tools(mcp)
    register_resources(mcp)

    return mcp
