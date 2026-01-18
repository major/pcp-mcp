"""System health tools for clumped metric queries."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Annotated, Literal

from fastmcp import Context
from pydantic import Field

from pcp_mcp.context import get_client
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


def register_system_tools(mcp: FastMCP) -> None:
    """Register system health tools with the MCP server."""

    @mcp.tool()
    async def get_system_snapshot(
        ctx: Context,
        categories: Annotated[
            list[str] | None,
            Field(
                default=None,
                description="Categories to include: cpu, memory, disk, network, load",
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
    ) -> SystemSnapshot:
        """Get a point-in-time system health overview.

        Returns CPU, memory, disk I/O, network I/O, and load metrics in a single
        call. For rate metrics (CPU %, disk I/O, network throughput), takes two
        samples to calculate per-second rates.
        """
        from pcp_mcp.errors import handle_pcp_error

        client = get_client(ctx)

        if categories is None:
            categories = ["cpu", "memory", "disk", "network", "load"]

        all_metrics: list[str] = []
        for cat in categories:
            if cat in SNAPSHOT_METRICS:
                all_metrics.extend(SNAPSHOT_METRICS[cat])

        try:
            data = await client.fetch_with_rates(
                all_metrics,
                COUNTER_METRICS,
                sample_interval,
            )
        except Exception as e:
            raise handle_pcp_error(e, "fetching system snapshot") from e

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

        return snapshot

    @mcp.tool()
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
    ) -> ProcessTopResult:
        """Get top processes by resource consumption.

        For CPU and I/O, takes two samples to calculate rates. Memory is instantaneous.
        Returns the top N processes sorted by the requested resource.
        """
        client = get_client(ctx)

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

        try:
            proc_data = await client.fetch_with_rates(all_metrics, counter_metrics, sample_interval)
            sys_data = await client.fetch(system_metrics)
        except Exception as e:
            raise handle_pcp_error(e, "fetching process data") from e

        ncpu = get_scalar_value(sys_data, "hinv.ncpu", 1)
        total_mem = get_scalar_value(sys_data, "mem.physmem", 1) * 1024

        processes = build_process_list(proc_data, sort_by, total_mem, ncpu)
        processes.sort(key=lambda p: get_sort_key(p, sort_by), reverse=True)
        processes = processes[:limit]

        assessment = assess_processes(processes, sort_by, ncpu)

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
