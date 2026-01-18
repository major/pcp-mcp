"""Health summary resource for quick system status."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastmcp import Context

from pcp_mcp.context import get_client
from pcp_mcp.tools.system import (
    COUNTER_METRICS,
    SNAPSHOT_METRICS,
    _build_cpu_metrics,
    _build_load_metrics,
    _build_memory_metrics,
)

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_health_resources(mcp: FastMCP) -> None:
    """Register health resources with the MCP server."""

    @mcp.resource("pcp://health")
    async def health_summary(ctx: Context) -> str:
        """Quick system health summary.

        Returns a text summary of CPU, memory, and load status suitable
        for quick health checks. For detailed metrics, use the
        get_system_snapshot tool instead.
        """
        client = get_client(ctx)

        metrics = SNAPSHOT_METRICS["cpu"] + SNAPSHOT_METRICS["memory"] + SNAPSHOT_METRICS["load"]

        try:
            data = await client.fetch_with_rates(metrics, COUNTER_METRICS, sample_interval=1.0)
        except Exception as e:
            return f"Error fetching health data: {e}"

        cpu = _build_cpu_metrics(data)
        memory = _build_memory_metrics(data)
        load = _build_load_metrics(data)

        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

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
