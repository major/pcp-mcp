"""Core metric tools for querying PCP metrics."""

from typing import TYPE_CHECKING, Annotated, Optional

from fastmcp import Context
from mcp.types import ToolAnnotations
from pydantic import Field

from pcp_mcp.context import get_client_for_host
from pcp_mcp.icons import (
    ICON_INFO,
    ICON_METRICS,
    ICON_SEARCH,
    TAGS_DISCOVERY,
    TAGS_METRICS,
)
from pcp_mcp.models import (
    MetricInfo,
    MetricSearchResult,
    MetricSearchResultList,
    MetricValue,
    MetricValueList,
)
from pcp_mcp.utils.extractors import extract_help_text, format_units

if TYPE_CHECKING:
    from fastmcp import FastMCP

TOOL_ANNOTATIONS = ToolAnnotations(readOnlyHint=True, openWorldHint=True)


def register_metrics_tools(mcp: "FastMCP") -> None:
    """Register core metric tools with the MCP server."""

    @mcp.tool(
        annotations=TOOL_ANNOTATIONS,
        icons=[ICON_METRICS],
        tags=TAGS_METRICS,
    )
    async def query_metrics(
        ctx: Context,
        names: Annotated[
            list[str],
            Field(description="List of PCP metric names to fetch (e.g., ['kernel.all.load'])"),
        ],
        host: Annotated[
            Optional[str],
            Field(description="Target pmcd host to query (default: server's configured target)"),
        ] = None,
    ) -> MetricValueList:
        """Fetch current values for specific PCP metrics.

        Returns the current value for each requested metric. For metrics with
        instances (e.g., per-CPU, per-disk), returns one MetricValue per instance.

        Examples:
            query_metrics(["kernel.all.load"]) - Get load averages
            query_metrics(["mem.util.available", "mem.physmem"]) - Get memory stats
            query_metrics(["hinv.ncpu"]) - Get CPU count
            query_metrics(["kernel.all.load"], host="web1.example.com") - Query remote host

        Warning: CPU, disk, and network metrics are counters (cumulative since boot).
        Use get_system_snapshot() instead for rates.
        """
        from pcp_mcp.errors import handle_pcp_error

        async with get_client_for_host(ctx, host) as client:
            try:
                response = await client.fetch(names)
            except Exception as e:
                raise handle_pcp_error(e, "fetching metrics") from e

            results: list[MetricValue] = []
            for metric in response.get("values", []):
                metric_name = metric.get("name", "")
                instances = metric.get("instances", [])

                for inst in instances:
                    instance_id = inst.get("instance")
                    value = inst.get("value")

                    instance_name = None
                    if instance_id is not None and instance_id != -1:
                        instance_name = str(instance_id)

                    results.append(
                        MetricValue(
                            name=metric_name,
                            value=value,
                            instance=instance_name,
                        )
                    )

            return MetricValueList(metrics=results)

    @mcp.tool(
        annotations=TOOL_ANNOTATIONS,
        icons=[ICON_SEARCH],
        tags=TAGS_METRICS | TAGS_DISCOVERY,
    )
    async def search_metrics(
        ctx: Context,
        pattern: Annotated[
            str,
            Field(description="Metric name prefix to search for (e.g., 'kernel.all', 'mem')"),
        ],
        host: Annotated[
            Optional[str],
            Field(description="Target pmcd host to query (default: server's configured target)"),
        ] = None,
    ) -> MetricSearchResultList:
        """Find PCP metrics matching a name pattern.

        Use this to discover available metrics before querying them.
        Returns metric names and brief descriptions.

        Examples:
            search_metrics("kernel.all") - Find kernel-wide metrics
            search_metrics("mem.util") - Find memory utilization metrics
            search_metrics("disk.dev") - Find per-disk metrics
            search_metrics("network.interface") - Find per-interface metrics
            search_metrics("kernel", host="db1.example.com") - Search on remote host
        """
        from pcp_mcp.errors import handle_pcp_error

        async with get_client_for_host(ctx, host) as client:
            try:
                metrics = await client.search(pattern)
            except Exception as e:
                raise handle_pcp_error(e, "searching metrics") from e

            results = [
                MetricSearchResult(
                    name=m.get("name", ""),
                    help_text=extract_help_text(m),
                )
                for m in metrics
            ]
            return MetricSearchResultList(results=results)

    @mcp.tool(
        annotations=TOOL_ANNOTATIONS,
        output_schema=MetricInfo.model_json_schema(),
        icons=[ICON_INFO],
        tags=TAGS_METRICS | TAGS_DISCOVERY,
    )
    async def describe_metric(
        ctx: Context,
        name: Annotated[
            str,
            Field(description="Full PCP metric name (e.g., 'kernel.all.cpu.user')"),
        ],
        host: Annotated[
            Optional[str],
            Field(description="Target pmcd host to query (default: server's configured target)"),
        ] = None,
    ) -> MetricInfo:
        """Get detailed metadata about a PCP metric.

        Returns type, semantics, units, and help text for the metric.
        Use this to understand what a metric measures and how to interpret it.

        Examples:
            describe_metric("kernel.all.load") - Learn about load average semantics
            describe_metric("mem.util.available") - Understand available memory
            describe_metric("disk.all.read_bytes") - Check if metric is counter vs instant
            describe_metric("kernel.all.load", host="web1.example.com") - Describe on remote
        """
        from fastmcp.exceptions import ToolError

        from pcp_mcp.errors import handle_pcp_error

        async with get_client_for_host(ctx, host) as client:
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
                units=format_units(info),
                help_text=extract_help_text(info),
                indom=info.get("indom"),
            )
