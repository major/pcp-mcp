"""Core metric tools for querying PCP metrics."""

from typing import TYPE_CHECKING, Annotated

from fastmcp import Context
from pydantic import Field

from pcp_mcp.context import get_client
from pcp_mcp.models import MetricInfo, MetricSearchResult, MetricValue
from pcp_mcp.utils.extractors import extract_help_text

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_metrics_tools(mcp: FastMCP) -> None:
    """Register core metric tools with the MCP server."""

    @mcp.tool()
    async def query_metrics(
        ctx: Context,
        names: Annotated[
            list[str],
            Field(description="List of PCP metric names to fetch (e.g., ['kernel.all.load'])"),
        ],
    ) -> list[MetricValue]:
        """Fetch current values for specific PCP metrics.

        Returns the current value for each requested metric. For metrics with
        instances (e.g., per-CPU, per-disk), returns one MetricValue per instance.
        """
        from pcp_mcp.errors import handle_pcp_error

        client = get_client(ctx)

        try:
            response = await client.fetch(names)
        except Exception as e:
            raise handle_pcp_error(e, "fetching metrics") from e

        results: list[MetricValue] = []
        for metric in response.get("values", []):
            metric_name = metric.get("name", "")
            instances = metric.get("instances", [])

            for inst in instances:
                instance_name = inst.get("instance")
                value = inst.get("value")

                results.append(
                    MetricValue(
                        name=metric_name,
                        value=value,
                        instance=instance_name if instance_name != -1 else None,
                    )
                )

        return results

    @mcp.tool()
    async def search_metrics(
        ctx: Context,
        pattern: Annotated[
            str,
            Field(description="Metric name prefix to search for (e.g., 'kernel.all', 'mem')"),
        ],
    ) -> list[MetricSearchResult]:
        """Find PCP metrics matching a name pattern.

        Use this to discover available metrics before querying them.
        Returns metric names and brief descriptions.
        """
        from pcp_mcp.errors import handle_pcp_error

        client = get_client(ctx)

        try:
            metrics = await client.search(pattern)
        except Exception as e:
            raise handle_pcp_error(e, "searching metrics") from e

        return [
            MetricSearchResult(
                name=m.get("name", ""),
                help_text=extract_help_text(m),
            )
            for m in metrics
        ]

    @mcp.tool()
    async def describe_metric(
        ctx: Context,
        name: Annotated[
            str,
            Field(description="Full PCP metric name (e.g., 'kernel.all.cpu.user')"),
        ],
    ) -> MetricInfo:
        """Get detailed metadata about a PCP metric.

        Returns type, semantics, units, and help text for the metric.
        Use this to understand what a metric measures and how to interpret it.
        """
        from fastmcp.exceptions import ToolError
        from pcp_mcp.errors import handle_pcp_error

        client = get_client(ctx)

        try:
            info = await client.describe(name)
        except Exception as e:
            raise handle_pcp_error(e, "describing metric") from e

        if not info:
            raise ToolError(f"Metric not found: {name}")

        return MetricInfo(
            name=info.get("name", name),
            type=info.get("type", "unknown"),
            semantics=info.get("sem", "unknown"),
            units=_format_units(info),
            help_text=extract_help_text(info),
            indom=info.get("indom"),
        )


def _format_units(info: dict) -> str:
    """Format PCP units into a human-readable string."""
    units = info.get("units", "")
    if units:
        return units

    # Fallback: build from components if available
    parts = []
    if info.get("units-space"):
        parts.append(info["units-space"])
    if info.get("units-time"):
        parts.append(info["units-time"])
    if info.get("units-count"):
        parts.append(info["units-count"])

    return " / ".join(parts) if parts else "none"
