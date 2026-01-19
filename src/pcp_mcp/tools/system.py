"""System health tools for clumped metric queries."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Annotated, Literal, Optional

from fastmcp import Context
from mcp.types import ToolAnnotations
from pydantic import Field

from pcp_mcp.context import get_client_for_host
from pcp_mcp.icons import (
    ICON_HEALTH,
    ICON_PROCESS,
    ICON_SYSTEM,
    TAGS_HEALTH,
    TAGS_PROCESS,
    TAGS_SYSTEM,
)
from pcp_mcp.models import ProcessTopResult, SystemSnapshot
from pcp_mcp.utils.builders import (
    assess_processes,
    build_cpu_metrics,
    build_disk_metrics,
    build_load_metrics,
    build_memory_metrics,
    build_network_metrics,
    build_process_list,
    get_sort_key,
)
from pcp_mcp.utils.extractors import get_scalar_value

if TYPE_CHECKING:
    from fastmcp import FastMCP

TOOL_ANNOTATIONS = ToolAnnotations(readOnlyHint=True, openWorldHint=True)

SNAPSHOT_METRICS = {
    "cpu": [
        "kernel.all.cpu.user",
        "kernel.all.cpu.sys",
        "kernel.all.cpu.idle",
        "kernel.all.cpu.wait.total",
        "hinv.ncpu",
    ],
    "memory": [
        "mem.physmem",
        "mem.util.used",
        "mem.util.free",
        "mem.util.available",
        "mem.util.cached",
        "mem.util.bufmem",
        "mem.util.swapTotal",
        "mem.util.swapFree",
    ],
    "load": [
        "kernel.all.load",
        "kernel.all.runnable",
        "kernel.all.nprocs",
        "hinv.ncpu",
    ],
    "disk": [
        "disk.all.read_bytes",
        "disk.all.write_bytes",
        "disk.all.read",
        "disk.all.write",
    ],
    "network": [
        "network.interface.in.bytes",
        "network.interface.out.bytes",
        "network.interface.in.packets",
        "network.interface.out.packets",
    ],
}

COUNTER_METRICS = {
    "kernel.all.cpu.user",
    "kernel.all.cpu.sys",
    "kernel.all.cpu.idle",
    "kernel.all.cpu.wait.total",
    "disk.all.read_bytes",
    "disk.all.write_bytes",
    "disk.all.read",
    "disk.all.write",
    "network.interface.in.bytes",
    "network.interface.out.bytes",
    "network.interface.in.packets",
    "network.interface.out.packets",
}

PROCESS_METRICS = {
    "cpu": ["proc.psinfo.utime", "proc.psinfo.stime"],
    "memory": ["proc.memory.rss"],
    "io": ["proc.io.read_bytes", "proc.io.write_bytes"],
    "info": ["proc.psinfo.pid", "proc.psinfo.cmd", "proc.psinfo.psargs"],
}


async def _fetch_system_snapshot(
    ctx: Context,
    categories: list[str],
    sample_interval: float,
    host: str | None,
) -> SystemSnapshot:
    """Core logic for fetching a system snapshot."""
    from pcp_mcp.errors import handle_pcp_error

    all_metrics: list[str] = []
    for cat in categories:
        if cat in SNAPSHOT_METRICS:
            all_metrics.extend(SNAPSHOT_METRICS[cat])

    async def report_progress(current: float, total: float, message: str) -> None:
        await ctx.report_progress(current, total, message)

    async with get_client_for_host(ctx, host) as client:
        try:
            data = await client.fetch_with_rates(
                all_metrics,
                COUNTER_METRICS,
                sample_interval,
                progress_callback=report_progress,
            )
        except Exception as e:
            raise handle_pcp_error(e, "fetching system snapshot") from e

        await ctx.report_progress(95, 100, "Building snapshot...")

        snapshot = SystemSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            hostname=client.target_host,
        )

        if "cpu" in categories:
            snapshot.cpu = build_cpu_metrics(data)
        if "memory" in categories:
            snapshot.memory = build_memory_metrics(data)
        if "load" in categories:
            snapshot.load = build_load_metrics(data)
        if "disk" in categories:
            snapshot.disk = build_disk_metrics(data)
        if "network" in categories:
            snapshot.network = build_network_metrics(data)

        await ctx.report_progress(100, 100, "Complete")
        return snapshot


def register_system_tools(mcp: FastMCP) -> None:
    """Register system health tools with the MCP server."""

    @mcp.tool(
        annotations=TOOL_ANNOTATIONS,
        output_schema=SystemSnapshot.model_json_schema(),
        icons=[ICON_SYSTEM],
        tags=TAGS_SYSTEM,
    )
    async def get_system_snapshot(
        ctx: Context,
        categories: Annotated[
            Optional[list[str]],
            Field(
                default=None,
                description=(
                    "Categories to include: cpu, memory, disk, network, load. "
                    "Defaults to all five if not specified."
                ),
            ),
        ] = None,
        sample_interval: Annotated[
            float,
            Field(
                default=1.0,
                ge=0.1,
                le=10.0,
                description="Seconds between samples for rate calculation",
            ),
        ] = 1.0,
        host: Annotated[
            Optional[str],
            Field(description="Target pmcd host to query (default: server's configured target)"),
        ] = None,
    ) -> SystemSnapshot:
        """Get a point-in-time system health overview.

        Returns CPU, memory, disk I/O, network I/O, and load metrics in a single
        call. For rate metrics (CPU %, disk I/O, network throughput), takes two
        samples to calculate per-second rates.

        Use this tool FIRST for system troubleshooting. It automatically handles
        counter-to-rate conversion. Do NOT use query_metrics() for CPU, disk, or
        network counters - those return raw cumulative values since boot.

        Examples:
            get_system_snapshot() - Quick health check (all categories)
            get_system_snapshot(categories=["cpu", "memory"]) - CPU and memory only
            get_system_snapshot(categories=["cpu", "load"]) - CPU and load averages
            get_system_snapshot(categories=["disk", "network"]) - I/O analysis
            get_system_snapshot(host="web1.example.com") - Query remote host
        """
        if categories is None:
            categories = ["cpu", "memory", "disk", "network", "load"]
        return await _fetch_system_snapshot(ctx, categories, sample_interval, host)

    @mcp.tool(
        annotations=TOOL_ANNOTATIONS,
        output_schema=SystemSnapshot.model_json_schema(),
        icons=[ICON_HEALTH],
        tags=TAGS_HEALTH,
    )
    async def quick_health(
        ctx: Context,
        host: Annotated[
            Optional[str],
            Field(description="Target pmcd host to query (default: server's configured target)"),
        ] = None,
    ) -> SystemSnapshot:
        """Fast system health check returning only CPU and memory metrics.

        Use this for rapid status checks when you don't need disk/network/load
        details. Uses a shorter sample interval (0.5s) for faster results.

        Examples:
            quick_health() - Fast health check on default host
            quick_health(host="web1.example.com") - Fast check on remote host
        """
        return await _fetch_system_snapshot(ctx, ["cpu", "memory"], 0.5, host)

    @mcp.tool(
        annotations=TOOL_ANNOTATIONS,
        output_schema=ProcessTopResult.model_json_schema(),
        icons=[ICON_PROCESS],
        tags=TAGS_PROCESS,
    )
    async def get_process_top(
        ctx: Context,
        sort_by: Annotated[
            Literal["cpu", "memory", "io"],
            Field(description="Resource to sort by"),
        ] = "cpu",
        limit: Annotated[
            int,
            Field(default=10, ge=1, le=50, description="Number of processes to return"),
        ] = 10,
        sample_interval: Annotated[
            float,
            Field(
                default=1.0,
                ge=0.5,
                le=5.0,
                description="Seconds to sample for CPU/IO rates",
            ),
        ] = 1.0,
        host: Annotated[
            Optional[str],
            Field(description="Target pmcd host to query (default: server's configured target)"),
        ] = None,
    ) -> ProcessTopResult:
        """Get top processes by resource consumption.

        For CPU and I/O, takes two samples to calculate rates. Memory is instantaneous.
        Returns the top N processes sorted by the requested resource.

        Examples:
            get_process_top() - Top 10 by CPU (default)
            get_process_top(sort_by="memory", limit=20) - Top 20 memory consumers
            get_process_top(sort_by="io", sample_interval=2.0) - Top I/O with longer sample
            get_process_top(host="db1.example.com") - Query remote host
        """
        all_metrics = (
            PROCESS_METRICS["info"] + PROCESS_METRICS["memory"] + PROCESS_METRICS.get(sort_by, [])
        )
        if sort_by == "cpu":
            all_metrics.extend(PROCESS_METRICS["cpu"])
        elif sort_by == "io":
            all_metrics.extend(PROCESS_METRICS["io"])

        all_metrics = list(set(all_metrics))
        system_metrics = ["hinv.ncpu", "mem.physmem"]

        counter_metrics = {
            "proc.psinfo.utime",
            "proc.psinfo.stime",
            "proc.io.read_bytes",
            "proc.io.write_bytes",
        }

        from pcp_mcp.errors import handle_pcp_error

        async def report_progress(current: float, total: float, message: str) -> None:
            await ctx.report_progress(current, total, message)

        async with get_client_for_host(ctx, host) as client:
            try:
                proc_data = await client.fetch_with_rates(
                    all_metrics, counter_metrics, sample_interval, progress_callback=report_progress
                )
                sys_data = await client.fetch(system_metrics)
            except Exception as e:
                raise handle_pcp_error(e, "fetching process data") from e

            await ctx.report_progress(92, 100, "Processing results...")

            ncpu = get_scalar_value(sys_data, "hinv.ncpu", 1)
            total_mem = get_scalar_value(sys_data, "mem.physmem", 1) * 1024

            processes = build_process_list(proc_data, sort_by, total_mem, ncpu)
            processes.sort(key=lambda p: get_sort_key(p, sort_by), reverse=True)
            processes = processes[:limit]

            assessment = assess_processes(processes, sort_by, ncpu)

            await ctx.report_progress(100, 100, "Complete")
            return ProcessTopResult(
                timestamp=datetime.now(timezone.utc).isoformat(),
                hostname=client.target_host,
                sort_by=sort_by,
                sample_interval=sample_interval,
                processes=processes,
                total_memory_bytes=int(total_mem),
                ncpu=ncpu,
                assessment=assessment,
            )
