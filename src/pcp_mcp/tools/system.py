"""System health tools for clumped metric queries."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Literal

from fastmcp import Context
from pydantic import Field

from pcp_mcp.context import get_client
from pcp_mcp.errors import handle_pcp_error
from pcp_mcp.models import (
    CPUMetrics,
    DiskMetrics,
    LoadMetrics,
    MemoryMetrics,
    NetworkMetrics,
    ProcessInfo,
    ProcessTopResult,
    SystemSnapshot,
)

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
            timestamp=datetime.now(UTC).isoformat(),
            hostname=client.target_host,
        )

        if "cpu" in categories:
            snapshot.cpu = _build_cpu_metrics(data)
        if "memory" in categories:
            snapshot.memory = _build_memory_metrics(data)
        if "load" in categories:
            snapshot.load = _build_load_metrics(data)
        if "disk" in categories:
            snapshot.disk = _build_disk_metrics(data)
        if "network" in categories:
            snapshot.network = _build_network_metrics(data)

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

        try:
            proc_data = await client.fetch_with_rates(all_metrics, counter_metrics, sample_interval)
            sys_data = await client.fetch(system_metrics)
        except Exception as e:
            raise handle_pcp_error(e, "fetching process data") from e

        ncpu = _get_scalar_value(sys_data, "hinv.ncpu", 1)
        total_mem = _get_scalar_value(sys_data, "mem.physmem", 1) * 1024

        processes = _build_process_list(proc_data, sort_by, total_mem, ncpu)
        processes.sort(key=lambda p: _get_sort_key(p, sort_by), reverse=True)
        processes = processes[:limit]

        assessment = _assess_processes(processes, sort_by, ncpu)

        return ProcessTopResult(
            timestamp=datetime.now(UTC).isoformat(),
            hostname=client.target_host,
            sort_by=sort_by,
            sample_interval=sample_interval,
            processes=processes,
            total_memory_bytes=int(total_mem),
            ncpu=ncpu,
            assessment=assessment,
        )


def _get_first_value(data: dict, metric: str, default: float = 0.0) -> float:
    """Get first instance value from fetched data."""
    metric_data = data.get(metric, {})
    instances = metric_data.get("instances", {})
    if instances:
        return float(next(iter(instances.values()), default))
    return default


def _get_scalar_value(response: dict, metric: str, default: int = 0) -> int:
    """Get scalar value from raw fetch response."""
    for v in response.get("values", []):
        if v.get("name") == metric:
            instances = v.get("instances", [])
            if instances:
                return int(instances[0].get("value", default))
    return default


def _sum_instances(data: dict, metric: str) -> float:
    """Sum all instance values for a metric."""
    metric_data = data.get(metric, {})
    instances = metric_data.get("instances", {})
    return sum(float(v) for v in instances.values())


def _build_cpu_metrics(data: dict) -> CPUMetrics:
    """Build CPU metrics from fetched data."""
    user = _get_first_value(data, "kernel.all.cpu.user")
    sys = _get_first_value(data, "kernel.all.cpu.sys")
    idle = _get_first_value(data, "kernel.all.cpu.idle")
    iowait = _get_first_value(data, "kernel.all.cpu.wait.total")
    ncpu = int(_get_first_value(data, "hinv.ncpu", 1))

    total = user + sys + idle + iowait
    if total > 0:
        user_pct = (user / total) * 100
        sys_pct = (sys / total) * 100
        idle_pct = (idle / total) * 100
        iowait_pct = (iowait / total) * 100
    else:
        user_pct = sys_pct = idle_pct = iowait_pct = 0.0

    if iowait_pct > 20:
        assessment = "High I/O wait - system is disk bound"
    elif idle_pct < 10:
        assessment = "CPU is saturated"
    elif user_pct > 70:
        assessment = "CPU bound on user processes"
    elif sys_pct > 30:
        assessment = "High system/kernel CPU usage"
    else:
        assessment = "CPU utilization is normal"

    return CPUMetrics(
        user_percent=round(user_pct, 1),
        system_percent=round(sys_pct, 1),
        idle_percent=round(idle_pct, 1),
        iowait_percent=round(iowait_pct, 1),
        ncpu=ncpu,
        assessment=assessment,
    )


def _build_memory_metrics(data: dict) -> MemoryMetrics:
    """Build memory metrics from fetched data."""
    total = int(_get_first_value(data, "mem.physmem")) * 1024
    used = int(_get_first_value(data, "mem.util.used")) * 1024
    free = int(_get_first_value(data, "mem.util.free")) * 1024
    available = int(_get_first_value(data, "mem.util.available")) * 1024
    cached = int(_get_first_value(data, "mem.util.cached")) * 1024
    buffers = int(_get_first_value(data, "mem.util.bufmem")) * 1024
    swap_total = int(_get_first_value(data, "mem.util.swapTotal")) * 1024
    swap_free = int(_get_first_value(data, "mem.util.swapFree")) * 1024
    swap_used = swap_total - swap_free

    used_pct = (used / total * 100) if total > 0 else 0.0

    if swap_used > swap_total * 0.5:
        assessment = "Heavy swap usage - memory pressure"
    elif used_pct > 90:
        assessment = "Memory usage is critical"
    elif used_pct > 75:
        assessment = "Memory usage is elevated"
    else:
        assessment = "Memory utilization is normal"

    return MemoryMetrics(
        total_bytes=total,
        used_bytes=used,
        free_bytes=free,
        available_bytes=available,
        cached_bytes=cached,
        buffers_bytes=buffers,
        swap_used_bytes=swap_used,
        swap_total_bytes=swap_total,
        used_percent=round(used_pct, 1),
        assessment=assessment,
    )


def _build_load_metrics(data: dict) -> LoadMetrics:
    """Build load metrics from fetched data."""
    load_data = data.get("kernel.all.load", {}).get("instances", {})

    load_1m = float(load_data.get("1 minute", load_data.get(1, 0.0)))
    load_5m = float(load_data.get("5 minute", load_data.get(5, 0.0)))
    load_15m = float(load_data.get("15 minute", load_data.get(15, 0.0)))

    runnable = int(_get_first_value(data, "kernel.all.runnable"))
    nprocs = int(_get_first_value(data, "kernel.all.nprocs"))
    ncpu = int(_get_first_value(data, "hinv.ncpu", 1))

    if load_1m > ncpu * 2:
        assessment = f"Load is very high ({load_1m:.1f} vs {ncpu} CPUs)"
    elif load_1m > ncpu:
        assessment = f"Load is elevated ({load_1m:.1f} > {ncpu} CPUs)"
    else:
        assessment = "Load is normal"

    return LoadMetrics(
        load_1m=round(load_1m, 2),
        load_5m=round(load_5m, 2),
        load_15m=round(load_15m, 2),
        runnable=runnable,
        nprocs=nprocs,
        assessment=assessment,
    )


def _build_disk_metrics(data: dict) -> DiskMetrics:
    """Build disk I/O metrics from fetched data."""
    read_bytes = _get_first_value(data, "disk.all.read_bytes")
    write_bytes = _get_first_value(data, "disk.all.write_bytes")
    reads = _get_first_value(data, "disk.all.read")
    writes = _get_first_value(data, "disk.all.write")

    if read_bytes > 100_000_000 or write_bytes > 100_000_000:
        assessment = (
            f"Heavy disk I/O ({read_bytes / 1e6:.0f} MB/s read, {write_bytes / 1e6:.0f} MB/s write)"
        )
    elif read_bytes > 10_000_000 or write_bytes > 10_000_000:
        assessment = "Moderate disk activity"
    else:
        assessment = "Disk I/O is low"

    return DiskMetrics(
        read_bytes_per_sec=round(read_bytes, 1),
        write_bytes_per_sec=round(write_bytes, 1),
        reads_per_sec=round(reads, 1),
        writes_per_sec=round(writes, 1),
        assessment=assessment,
    )


def _build_network_metrics(data: dict) -> NetworkMetrics:
    """Build network I/O metrics from fetched data."""
    in_bytes = _sum_instances(data, "network.interface.in.bytes")
    out_bytes = _sum_instances(data, "network.interface.out.bytes")
    in_packets = _sum_instances(data, "network.interface.in.packets")
    out_packets = _sum_instances(data, "network.interface.out.packets")

    total_throughput = in_bytes + out_bytes
    if total_throughput > 100_000_000:
        assessment = f"High network throughput ({total_throughput / 1e6:.0f} MB/s)"
    elif total_throughput > 10_000_000:
        assessment = "Moderate network activity"
    else:
        assessment = "Network I/O is low"

    return NetworkMetrics(
        in_bytes_per_sec=round(in_bytes, 1),
        out_bytes_per_sec=round(out_bytes, 1),
        in_packets_per_sec=round(in_packets, 1),
        out_packets_per_sec=round(out_packets, 1),
        assessment=assessment,
    )


def _build_process_list(data: dict, sort_by: str, total_mem: float, ncpu: int) -> list[ProcessInfo]:
    """Build list of ProcessInfo from fetched data."""
    pid_data = data.get("proc.psinfo.pid", {}).get("instances", {})
    cmd_data = data.get("proc.psinfo.cmd", {}).get("instances", {})
    args_data = data.get("proc.psinfo.psargs", {}).get("instances", {})
    rss_data = data.get("proc.memory.rss", {}).get("instances", {})

    utime_data = data.get("proc.psinfo.utime", {}).get("instances", {})
    stime_data = data.get("proc.psinfo.stime", {}).get("instances", {})
    io_read_data = data.get("proc.io.read_bytes", {}).get("instances", {})
    io_write_data = data.get("proc.io.write_bytes", {}).get("instances", {})

    processes: list[ProcessInfo] = []

    for inst_id in pid_data:
        pid = int(pid_data.get(inst_id, 0))
        if pid <= 0:
            continue

        cmd = str(cmd_data.get(inst_id, "unknown"))
        cmdline = str(args_data.get(inst_id, cmd))[:200]
        rss = int(rss_data.get(inst_id, 0)) * 1024
        rss_pct = (rss / total_mem * 100) if total_mem > 0 else 0.0

        cpu_pct = None
        if sort_by == "cpu" or utime_data:
            utime = float(utime_data.get(inst_id, 0))
            stime = float(stime_data.get(inst_id, 0))
            cpu_pct = (utime + stime) / 10.0

        io_read = None
        io_write = None
        if sort_by == "io" or io_read_data:
            io_read = float(io_read_data.get(inst_id, 0))
            io_write = float(io_write_data.get(inst_id, 0))

        processes.append(
            ProcessInfo(
                pid=pid,
                command=cmd,
                cmdline=cmdline,
                cpu_percent=round(cpu_pct, 1) if cpu_pct is not None else None,
                rss_bytes=rss,
                rss_percent=round(rss_pct, 1),
                io_read_bytes_per_sec=round(io_read, 1) if io_read is not None else None,
                io_write_bytes_per_sec=round(io_write, 1) if io_write is not None else None,
            )
        )

    return processes


def _get_sort_key(proc: ProcessInfo, sort_by: str) -> float:
    """Get sort key value for a process."""
    if sort_by == "cpu":
        return proc.cpu_percent or 0.0
    elif sort_by == "memory":
        return float(proc.rss_bytes)
    elif sort_by == "io":
        return (proc.io_read_bytes_per_sec or 0.0) + (proc.io_write_bytes_per_sec or 0.0)
    return 0.0


def _assess_processes(processes: list[ProcessInfo], sort_by: str, ncpu: int) -> str:
    """Generate assessment string for top processes."""
    if not processes:
        return "No processes found"

    top = processes[0]
    if sort_by == "cpu":
        if top.cpu_percent and top.cpu_percent > ncpu * 100 * 0.5:
            return f"{top.command} is CPU-bound ({top.cpu_percent:.0f}%)"
        return f"Top CPU: {top.command} ({top.cpu_percent:.0f}%)"
    elif sort_by == "memory":
        return f"Top memory: {top.command} ({top.rss_percent:.1f}%)"
    elif sort_by == "io":
        total_io = (top.io_read_bytes_per_sec or 0) + (top.io_write_bytes_per_sec or 0)
        return f"Top I/O: {top.command} ({total_io / 1e6:.1f} MB/s)"
    return f"Top process: {top.command}"
