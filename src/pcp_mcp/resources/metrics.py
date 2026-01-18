"""Metric discovery resources for browsing available metrics."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastmcp import Context

from pcp_mcp.context import get_client

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_metrics_resources(mcp: FastMCP) -> None:
    """Register metrics resources with the MCP server."""

    @mcp.resource("pcp://metrics/{pattern}")
    async def browse_metrics(ctx: Context, pattern: str) -> str:
        """Browse PCP metrics matching a pattern.

        Returns a formatted list of metric names and descriptions matching
        the given pattern prefix. Use this to discover available metrics
        before querying them with the query_metrics tool.

        Examples:
        - pcp://metrics/kernel.all - Kernel-wide stats
        - pcp://metrics/mem - Memory metrics
        - pcp://metrics/disk - Disk I/O metrics
        - pcp://metrics/network - Network metrics
        - pcp://metrics/proc - Per-process metrics
        """
        client = get_client(ctx)

        try:
            metrics = await client.search(pattern)
        except Exception as e:
            return f"Error searching metrics: {e}"

        if not metrics:
            return f"No metrics found matching pattern: {pattern}"

        lines = [f"# Metrics matching '{pattern}'", ""]

        for m in metrics[:50]:
            name = m.get("name", "unknown")
            help_text = m.get("text-oneline") or m.get("text-help", "")
            if help_text:
                lines.append(f"- **{name}**: {help_text}")
            else:
                lines.append(f"- **{name}**")

        if len(metrics) > 50:
            lines.append(f"\n... and {len(metrics) - 50} more metrics")

        return "\n".join(lines)

    @mcp.resource("pcp://metric/{name}")
    async def metric_detail(ctx: Context, name: str) -> str:
        """Get detailed information about a specific PCP metric.

        Returns type, semantics, units, instance domain, and help text
        for the specified metric.
        """
        client = get_client(ctx)

        try:
            info = await client.describe(name)
        except Exception as e:
            return f"Error describing metric: {e}"

        if not info:
            return f"Metric not found: {name}"

        metric_type = info.get("type", "unknown")
        semantics = info.get("sem", "unknown")
        units = info.get("units", "none")
        indom = info.get("indom", "none")
        help_text = info.get("text-help") or info.get("text-oneline", "No description available")

        return f"""# {name}

## Metadata
- **Type**: {metric_type}
- **Semantics**: {semantics}
- **Units**: {units}
- **Instance Domain**: {indom}

## Description
{help_text}

## Usage
To fetch current values:
```
Use the query_metrics tool with names=["{name}"]
```
"""
