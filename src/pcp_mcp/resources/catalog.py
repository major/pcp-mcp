"""Catalog resources for common metrics and namespaces."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastmcp import Context

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_catalog_resources(mcp: FastMCP) -> None:
    """Register catalog resources with the MCP server.

    Args:
        mcp: The FastMCP server instance.
    """

    @mcp.resource("pcp://metrics/common")
    def common_metrics_catalog() -> str:
        """Catalog of commonly used metric groups.

        Returns a structured guide to the most useful PCP metrics organized
        by troubleshooting domain.
        """
        return """# Common PCP Metric Groups

## CPU Performance
- kernel.all.cpu.user       → User-space CPU time (counter) ⚠️
- kernel.all.cpu.sys        → Kernel CPU time (counter) ⚠️
- kernel.all.cpu.idle       → Idle CPU time (counter) ⚠️
- kernel.all.cpu.wait.total → I/O wait time (counter) ⚠️ High = disk bottleneck
- kernel.all.load           → Load average (1, 5, 15 min) [instances: 1, 5, 15]
- kernel.all.runnable       → Runnable processes (instant)
- kernel.all.nprocs         → Total processes (instant)
- hinv.ncpu                 → Number of CPUs (instant)

## Memory
- mem.physmem               → Total physical memory in KB (instant)
- mem.util.used             → Used memory in KB (instant)
- mem.util.free             → Free memory in KB (instant)
- mem.util.available        → Available for apps in KB (instant) ⭐ Use this, not "free"
- mem.util.cached           → Cached data in KB (instant)
- mem.util.bufmem           → Buffer memory in KB (instant)
- mem.util.swapTotal        → Total swap in KB (instant)
- mem.util.swapFree         → Free swap in KB (instant)
- mem.util.slab             → Kernel slab allocator in KB (instant)

## Disk I/O
- disk.all.read_bytes       → Total bytes read (counter) ⚠️
- disk.all.write_bytes      → Total bytes written (counter) ⚠️
- disk.all.read             → Total read operations (counter) ⚠️
- disk.all.write            → Total write operations (counter) ⚠️
- disk.dev.read_bytes       → Per-disk reads in bytes [instances: sda, sdb, ...] (counter) ⚠️
- disk.dev.write_bytes      → Per-disk writes in bytes [instances: sda, sdb, ...] (counter) ⚠️
- disk.dev.avactive         → Average time disk was active (instant)

## Network
- network.interface.in.bytes  → Bytes received [instances: eth0, lo, ...] (counter) ⚠️
- network.interface.out.bytes → Bytes sent [instances: eth0, lo, ...] (counter) ⚠️
- network.interface.in.packets  → Packets received [instances] (counter) ⚠️
- network.interface.out.packets → Packets sent [instances] (counter) ⚠️
- network.interface.in.errors   → Receive errors [instances] (counter) ⚠️
- network.interface.out.errors  → Transmit errors [instances] (counter) ⚠️

## Process Metrics (⚠️ Use get_process_top instead of raw queries)
- proc.psinfo.pid           → Process ID [instances: PIDs]
- proc.psinfo.cmd           → Command name [instances: PIDs]
- proc.psinfo.psargs        → Full command line [instances: PIDs]
- proc.memory.rss           → Resident set size in KB [instances: PIDs] (instant)
- proc.memory.vmsize        → Virtual memory size in KB [instances: PIDs] (instant)
- proc.psinfo.utime         → User CPU time in ms [instances: PIDs] (counter) ⚠️
- proc.psinfo.stime         → System CPU time in ms [instances: PIDs] (counter) ⚠️
- proc.io.read_bytes        → Process I/O reads in bytes [instances: PIDs] (counter) ⚠️
- proc.io.write_bytes       → Process I/O writes in bytes [instances: PIDs] (counter) ⚠️

## System Health
- kernel.all.uptime         → System uptime in seconds (instant)
- kernel.all.nusers         → Logged-in users (instant)
- pmcd.agent.status         → PMDA agent health [instances: agent names] (instant)
- pmcd.pmlogger.host        → Active pmlogger hosts [instances] (instant)

## Container Metrics (requires cgroups PMDA)
- cgroup.cpuacct.usage      → CPU usage per cgroup [instances: cgroup paths] (counter) ⚠️
- cgroup.memory.usage       → Memory usage per cgroup [instances: cgroup paths] (instant)
- cgroup.blkio.io_service_bytes → I/O per cgroup [instances: cgroup paths] (counter) ⚠️

---

## Legend
⚠️ = COUNTER METRIC - Use get_system_snapshot() or get_process_top() for rates
⭐ = Recommended over alternatives
[instances] = Returns multiple values (per-CPU, per-disk, per-process, etc.)
(instant) = Instantaneous gauge value
(counter) = Cumulative counter since boot
"""

    @mcp.resource("pcp://namespaces")
    async def metric_namespaces(ctx: Context) -> str:
        """List available PCP metric namespaces discovered from the live system.

        Queries the connected PCP server to enumerate top-level namespaces
        and active PMDAs, showing exactly what's available on this system.
        """
        from pcp_mcp.context import get_client
        from pcp_mcp.errors import handle_pcp_error

        client = await get_client(ctx)

        try:
            all_metrics = await client.search("")
            namespaces = sorted(
                {m.get("name", "").split(".")[0] for m in all_metrics if m.get("name")}
            )

            pmda_status = await client.fetch(["pmcd.agent.status"])
            active_pmdas = []
            for metric in pmda_status.get("values", []):
                for inst in metric.get("instances", []):
                    instance_id = inst.get("instance")
                    status = inst.get("value")
                    if instance_id is not None and instance_id != -1 and status == 0:
                        active_pmdas.append(str(instance_id))

        except Exception as e:
            raise handle_pcp_error(e, "discovering namespaces") from e

        output = f"""# PCP Metric Namespaces (Live Discovery)

Connected to: {client.target_host}
Active PMDAs: {len(active_pmdas)}
Top-level namespaces: {len(namespaces)}

## Available Namespaces

"""

        namespace_docs = {
            "kernel": "System-wide kernel statistics (CPU, load, interrupts, uptime)",
            "mem": "Memory subsystem (physmem, swap, cache, buffers, NUMA)",
            "disk": "Disk I/O (aggregates, per-device, partitions, device mapper)",
            "network": "Network interfaces and protocols (TCP, UDP, IP)",
            "proc": "Per-process metrics ⚠️ Use get_process_top instead of raw queries",
            "hinv": "Hardware inventory (ncpu, physmem, architecture - static info)",
            "pmcd": "PCP daemon health (agent status, clients, control)",
            "pmproxy": "pmproxy daemon metrics (if pmproxy PMDA loaded)",
            "cgroup": "Container/cgroup metrics (CPU, memory, I/O per cgroup)",
            "containers": "Container metrics (Docker, Podman via PMDA)",
            "filesys": "Filesystem metrics (capacity, used, free per mount point)",
            "nfs": "NFS version-agnostic metrics",
            "nfs3": "NFSv3 client and server metrics",
            "nfs4": "NFSv4 client and server metrics",
            "swap": "Swap device metrics (activity per swap device)",
            "quota": "Filesystem quota metrics",
            "xfs": "XFS filesystem-specific metrics",
            "btrfs": "Btrfs filesystem-specific metrics",
            "zfs": "ZFS filesystem-specific metrics",
            "kvm": "KVM hypervisor metrics (guest VMs)",
            "libvirt": "libvirt virtualization metrics",
            "redis": "Redis server metrics (via redis PMDA)",
            "postgresql": "PostgreSQL database metrics (via postgresql PMDA)",
            "mysql": "MySQL database metrics (via mysql PMDA)",
            "nginx": "nginx web server metrics",
            "apache": "Apache web server metrics",
            "haproxy": "HAProxy load balancer metrics",
            "elasticsearch": "Elasticsearch metrics",
            "mongodb": "MongoDB metrics",
            "bcc": "eBPF-based advanced profiling (BPF PMDA - requires kernel 4.1+)",
            "hotproc": "Hot process tracking (automatically tracks top resource consumers)",
            "mmv": "Memory-mapped value metrics (custom app instrumentation)",
            "sysfs": "Linux sysfs metrics",
            "event": "System event tracing",
            "ipc": "Inter-process communication metrics (SysV IPC)",
            "jbd2": "JBD2 journal metrics (ext4 filesystem journaling)",
            "rpc": "RPC statistics",
            "acct": "Process accounting metrics",
            "fchost": "Fibre Channel host metrics",
            "tape": "Tape device metrics",
            "hyperv": "Hyper-V guest metrics",
        }

        for ns in namespaces:
            doc = namespace_docs.get(ns, "Namespace provided by PMDA (no built-in description)")
            output += f"- **{ns}.***: {doc}\n"

        output += f"""
## Active PMDAs on This System

{", ".join(active_pmdas) if active_pmdas else "Unable to enumerate PMDAs"}

Status 0 = Running, non-zero = Error

## Namespace Categories

### Core System (always available)
kernel, mem, disk, network, proc, hinv, pmcd

### Filesystems
filesys, xfs, btrfs, zfs, quota, swap

### Virtualization
kvm, libvirt, containers, cgroup, hyperv

### Databases
redis, postgresql, mysql, elasticsearch, mongodb

### Web Servers
nginx, apache, haproxy

### Advanced
bcc (eBPF), hotproc (auto-tracking), mmv (custom metrics), event (tracing)

## Discovery Workflow

1. **Explore a namespace**: search_metrics("{namespaces[0] if namespaces else "kernel"}")
2. **Count metrics in namespace**: search_metrics("disk") to see all disk.* metrics
3. **Get metric details**: describe_metric("full.metric.name")
4. **Query specific metrics**: query_metrics(["name1", "name2"])

## Navigation Strategy

**Top-down** (recommended for troubleshooting):
  1. Start with get_system_snapshot() → Identifies problem domain
  2. Drill into relevant namespace (e.g., "disk" issue → search_metrics("disk.dev"))
  3. Query specific metrics with query_metrics([...])

**Bottom-up** (exploring new system):
  1. Browse this pcp://namespaces resource → See what's available
  2. search_metrics("interesting.namespace") → Explore subtree
  3. describe_metric("full.name") → Understand semantics
"""
        return output
