"""Health summary resource for quick system status."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from fastmcp import Context

from pcp_mcp.client import PCPClient
from pcp_mcp.context import get_client, get_client_for_host, get_settings
from pcp_mcp.models import CPUMetrics, LoadMetrics, MemoryMetrics
from pcp_mcp.tools.system import COUNTER_METRICS, SNAPSHOT_METRICS
from pcp_mcp.utils.builders import (
    build_cpu_metrics,
    build_load_metrics,
    build_memory_metrics,
)

if TYPE_CHECKING:
    from fastmcp import FastMCP


def _format_health_summary(
    client: PCPClient,
    cpu: CPUMetrics,
    memory: MemoryMetrics,
    load: LoadMetrics,
) -> str:
    """Format health metrics into a markdown summary."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    return f"""# System Health Summary
Host: {client.target_host}
Time: {timestamp}

## CPU
- User: {cpu.user_percent}%
- System: {cpu.system_percent}%
- Idle: {cpu.idle_percent}%
- I/O Wait: {cpu.iowait_percent}%
- CPUs: {cpu.ncpu}
- Assessment: {cpu.assessment}

## Memory
- Used: {memory.used_percent}% ({memory.used_bytes / 1e9:.1f} / {memory.total_bytes / 1e9:.1f} GB)
- Available: {memory.available_bytes / 1e9:.1f} GB
- Cached: {memory.cached_bytes / 1e9:.1f} GB
- Swap: {memory.swap_used_bytes / 1e9:.1f} GB / {memory.swap_total_bytes / 1e9:.1f} GB
- Assessment: {memory.assessment}

## Load
- 1 min: {load.load_1m}
- 5 min: {load.load_5m}
- 15 min: {load.load_15m}
- Runnable: {load.runnable}
- Processes: {load.nprocs}
- Assessment: {load.assessment}
"""


async def _fetch_health_data(client: PCPClient) -> tuple[CPUMetrics, MemoryMetrics, LoadMetrics]:
    """Fetch and build health metrics from a client."""
    metrics = SNAPSHOT_METRICS["cpu"] + SNAPSHOT_METRICS["memory"] + SNAPSHOT_METRICS["load"]
    data = await client.fetch_with_rates(metrics, COUNTER_METRICS, sample_interval=1.0)

    return (
        build_cpu_metrics(data),
        build_memory_metrics(data),
        build_load_metrics(data),
    )


def register_health_resources(mcp: FastMCP) -> None:
    """Register health resources with the MCP server."""

    @mcp.resource("pcp://health")
    async def health_summary(ctx: Context) -> str:
        """Quick system health summary for the default target host.

        Returns a text summary of CPU, memory, and load status suitable
        for quick health checks. For detailed metrics, use the
        get_system_snapshot tool instead.
        """
        client = get_client(ctx)

        try:
            cpu, memory, load = await _fetch_health_data(client)
        except Exception as e:
            return f"Error fetching health data: {e}"

        return _format_health_summary(client, cpu, memory, load)

    @mcp.resource("pcp://host/{hostname}/health")
    async def host_health_summary(ctx: Context, hostname: str) -> str:
        """System health summary for a specific host.

        Returns a text summary of CPU, memory, and load status for the
        specified hostname. Requires PCP_ALLOWED_HOSTS to be configured
        if querying hosts other than the default target.
        """
        settings = get_settings(ctx)

        if not settings.is_host_allowed(hostname):
            return (
                f"Error: Host '{hostname}' is not allowed. "
                f"Configure PCP_ALLOWED_HOSTS to permit additional hosts."
            )

        async with get_client_for_host(ctx, hostname) as client:
            try:
                cpu, memory, load = await _fetch_health_data(client)
            except Exception as e:
                return f"Error fetching health data from {hostname}: {e}"

            return _format_health_summary(client, cpu, memory, load)
