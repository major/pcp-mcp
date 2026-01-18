"""Diagnostic prompts for guided troubleshooting workflows."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> None:
    """Register diagnostic prompts with the MCP server.

    Args:
        mcp: The FastMCP server instance.
    """

    @mcp.prompt()
    def diagnose_slow_system() -> str:
        """Diagnose why a system is running slowly.

        Returns a structured investigation workflow to identify performance
        bottlenecks by examining CPU, memory, disk, and network metrics.
        """
        return """Investigate system slowness:

1. Get baseline: get_system_snapshot(categories=["cpu", "memory", "load", "disk", "network"])

2. Interpret the assessment fields:
   - If cpu.assessment mentions "I/O wait": Disk bottleneck (skip to step 4)
   - If cpu.assessment mentions "user/system": CPU bottleneck (go to step 3)
   - If memory.assessment mentions "swap": Memory pressure (go to step 5)
   - If load.assessment shows high load: Check load vs ncpu ratio

3. Find CPU hogs:
   - Run: get_process_top(sort_by="cpu", limit=10)
   - Identify processes with high cpu_percent
   - Note: cpu_percent > 100% means multi-threaded (e.g., 200% = 2 cores)

4. Check disk I/O bottleneck:
   - If disk.assessment shows high read/write rates
   - Run: search_metrics("disk.dev") to see per-device metrics
   - Run: get_process_top(sort_by="io", limit=10) to find I/O-heavy processes
   - Cross-check: Does kernel.all.cpu.wait.total correlate with disk activity?

5. Check memory pressure:
   - If memory.assessment indicates swapping
   - Run: get_process_top(sort_by="memory", limit=20)
   - Look for large rss_bytes processes
   - Check if swap usage is growing

6. Check network saturation:
   - If network.assessment shows high throughput
   - Run: search_metrics("network.interface") for per-interface breakdown
   - Look for interface errors or packet drops

7. Report findings:
   - Primary bottleneck (CPU/disk/memory/network)
   - Specific culprits (process names, PIDs)
   - Quantified impact (e.g., "process X using 45% CPU on 8-core system")
   - Recommendations (kill process, add RAM, optimize queries, etc.)
"""

    @mcp.prompt()
    def investigate_memory_usage() -> str:
        """Investigate memory consumption and identify memory pressure.

        Returns a workflow to analyze memory utilization, identify memory
        hogs, and distinguish between normal cache usage and actual pressure.
        """
        return """Memory investigation workflow:

1. Get memory overview:
   - Run: get_system_snapshot(categories=["memory"])
   - Read memory.assessment field for quick diagnosis

2. Interpret memory metrics:
   - mem.util.available is KEY metric (not "free"!)
   - Large cache is NORMAL (Linux uses free RAM for cache)
   - Swapping = BAD (indicates memory pressure)
   - Check used_percent vs swap usage

3. Assessment-based actions:
   - "Memory pressure" → Go to step 4
   - "Cache is large" → Normal, but check top consumers anyway (step 4)
   - "Swapping actively" → CRITICAL, go to step 4 immediately

4. Find memory consumers:
   - Run: get_process_top(sort_by="memory", limit=20)
   - Note processes with high rss_bytes
   - Calculate: rss_percent shows memory impact
   - Look for unexpected memory hogs (leaked memory, runaway processes)

5. Detailed memory breakdown:
   - Run: search_metrics("mem.util") for full breakdown
   - Check: mem.util.slab (kernel memory)
   - Check: mem.util.anonpages (process private memory)
   - Check: mem.util.swapCached (pages swapped but still in RAM)

6. NUMA systems (if applicable):
   - Run: search_metrics("mem.numa") to check per-node allocation
   - Look for imbalanced NUMA usage

7. Report:
   - Total memory: X GB
   - Used: Y% (Z GB used, W GB available)
   - Top 5 memory consumers with RSS sizes
   - Swap status: active/inactive, growth rate if swapping
   - Recommendation:
     * No pressure + large cache = Normal
     * High usage + no swap = Monitor but OK
     * Active swapping = Add RAM or reduce load
     * Single process consuming >50% = Investigate for memory leak
"""

    @mcp.prompt()
    def find_io_bottleneck() -> str:
        """Find disk I/O bottlenecks and identify processes causing high I/O.

        Returns a workflow to diagnose disk performance issues, identify
        hot devices, and find I/O-intensive processes.
        """
        return """Disk I/O investigation:

1. Get system-wide I/O snapshot:
   - Run: get_system_snapshot(categories=["disk", "cpu"])
   - Check disk.assessment for read/write rates
   - Check cpu.assessment for iowait_percent

2. Interpret I/O metrics:
   - High iowait_percent (>20%) = CPU waiting for disk
   - Read vs write imbalance may indicate backup, logging, or database queries
   - Sustained high I/O (>100 MB/s on HDD, >500 MB/s on SSD) = saturated

3. Identify hot disks:
   - Run: search_metrics("disk.dev")
   - Run: query_metrics(["disk.dev.read_bytes", "disk.dev.write_bytes"])
   - Note: These are COUNTERS, use get_system_snapshot for rates
   - Look for specific devices with disproportionate activity

4. Find I/O-heavy processes:
   - Run: get_process_top(sort_by="io", limit=10, sample_interval=2.0)
   - Note: Longer sample_interval (2-5s) gives more accurate I/O rates
   - Identify processes with high io_read_bytes_sec or io_write_bytes_sec

5. Correlate with CPU iowait:
   - If cpu.iowait_percent is high AND disk I/O is high:
     → Confirmed disk bottleneck
   - If disk I/O is high BUT iowait is low:
     → Fast storage keeping up (SSD/NVMe)
   - If iowait is high BUT disk I/O is low:
     → May be network storage (NFS) or storage controller issue

6. Check for I/O patterns:
   - Bursty I/O: Scheduled jobs, backups, log rotation
   - Sustained I/O: Database, file server, streaming
   - Random I/O: Database seeks (slow on HDD, fast on SSD)
   - Sequential I/O: Backups, large file copies

7. Advanced: Check per-partition I/O (if needed):
   - Run: search_metrics("disk.partitions")
   - Useful for systems with multiple partitions on same disk

8. Report:
   - Busiest disks by name (e.g., sda, nvme0n1)
   - Read vs write breakdown (e.g., "80% reads, 20% writes")
   - Top 3-5 processes causing I/O with rates
   - I/O pattern: bursty vs sustained, random vs sequential
   - Bottleneck severity: iowait % and queue depth
   - Recommendations:
     * High random I/O on HDD → Migrate to SSD
     * Single process saturating disk → Optimize queries/access patterns
     * Multiple processes fighting for I/O → I/O scheduler tuning or workload separation
     * Backup/batch jobs during business hours → Reschedule
"""

    @mcp.prompt()
    def analyze_cpu_usage() -> str:
        """Analyze CPU utilization patterns and identify CPU-bound processes.

        Returns a workflow to diagnose high CPU usage, distinguish between
        user-space and kernel CPU time, and identify optimization opportunities.
        """
        return """CPU usage analysis workflow:

1. Get CPU baseline:
   - Run: get_system_snapshot(categories=["cpu", "load"])
   - Read cpu.assessment for quick diagnosis
   - Note: ncpu value (number of CPUs/cores)

2. Interpret CPU metrics:
   - user_percent: Application code execution
   - system_percent: Kernel/syscall overhead
   - idle_percent: Unused CPU capacity
   - iowait_percent: CPU waiting for I/O (NOT CPU-bound if high)
   - Load average: Runnable + waiting processes (compare to ncpu)

3. CPU pattern classification:
   - High user + low system = CPU-intensive application (normal)
   - High system + low user = Kernel overhead (syscalls, context switches)
   - High iowait = NOT a CPU problem, it's disk/storage (see find_io_bottleneck)
   - Load > ncpu = More demand than capacity (may include I/O wait)

4. Find CPU hogs:
   - Run: get_process_top(sort_by="cpu", limit=15)
   - Note: cpu_percent > 100% means multi-core usage (e.g., 400% = 4 cores)
   - Identify unexpected high CPU consumers

5. Per-CPU breakdown (if needed):
   - Run: search_metrics("kernel.percpu.cpu")
   - Useful for: Thread affinity issues, interrupt handling imbalance
   - Look for: One CPU at 100% while others idle (poor parallelization)

6. Check for CPU saturation indicators:
   - Run: query_metrics(["kernel.all.runnable", "kernel.all.pswitch"])
   - High runnable count: More threads than cores (contention)
   - High pswitch (context switches): Thread thrashing

7. Distinguish workload types:
   - Compute-bound: High user%, low syscalls (scientific, encoding, crypto)
   - I/O-bound: High iowait%, moderate user% (databases, file processing)
   - System-bound: High system%, moderate user% (network servers, many syscalls)

8. Report:
   - CPU utilization breakdown: X% user, Y% system, Z% iowait, W% idle
   - Load average: 1/5/15 min values vs ncpu (e.g., "load 8.5 on 8-core = 106%")
   - Top 5 CPU consumers with cpu_percent and command names
   - CPU pattern: compute-bound / I/O-bound / system-bound
   - Saturation indicators: runnable queue, context switches
   - Recommendations:
     * Low idle + high load → Add CPU capacity or optimize hot processes
     * High iowait → Disk bottleneck, not CPU (see I/O investigation)
     * High system% → Profile syscalls, reduce I/O frequency, optimize locking
     * Single-threaded bottleneck → Parallelize if possible
     * Many small processes → Reduce process spawning overhead
"""

    @mcp.prompt()
    def check_network_performance() -> str:
        """Check network performance and identify bandwidth/error issues.

        Returns a workflow to analyze network throughput, identify saturated
        interfaces, and detect packet loss or errors.
        """
        return """Network performance investigation:

1. Get network overview:
   - Run: get_system_snapshot(categories=["network"])
   - Read network.assessment for quick diagnosis
   - Note: Rates are per-second (bytes/sec, packets/sec)

2. Interpret network metrics:
   - in_bytes_sec / out_bytes_sec: Throughput (compare to link speed)
   - in_packets_sec / out_packets_sec: Packet rate
   - Assessment field indicates saturation or errors

3. Per-interface breakdown:
   - Run: search_metrics("network.interface")
   - Run: query_metrics(["network.interface.in.bytes", "network.interface.out.bytes"])
   - Note: These are COUNTERS, use get_system_snapshot for rates
   - Identify busy interfaces vs idle interfaces (e.g., eth0 busy, lo idle)

4. Check for errors and drops:
   - Run: query_metrics(["network.interface.in.errors", "network.interface.out.errors"])
   - Run: query_metrics(["network.interface.in.drops", "network.interface.out.drops"])
   - Non-zero errors = Hardware, driver, or cable issues
   - Non-zero drops = Buffer overflow (traffic exceeds processing capacity)

5. Calculate interface saturation:
   - Compare throughput to link speed (e.g., 950 Mbps on 1 Gbps link = 95%)
   - Sustained >80% = Approaching saturation
   - Bursts >95% = Temporarily saturated

6. Find network-heavy processes (indirect):
   - PCP proc.* namespace doesn't have per-process network metrics
   - Use system tools: netstat, ss, iftop (outside PCP)
   - Or correlate: High network I/O often correlates with high CPU/disk I/O

7. Check protocol-level stats (if needed):
   - Run: search_metrics("network.tcp")
   - Run: search_metrics("network.udp")
   - Look for: Retransmissions, failed connections, buffer overflows

8. Report:
   - Per-interface throughput (e.g., "eth0: 850 Mbps in, 120 Mbps out")
   - Link utilization % (if link speed known)
   - Errors/drops: Count and affected interfaces
   - Traffic pattern: Symmetric (similar in/out) vs asymmetric (download/upload heavy)
   - Packet rate: Normal vs abnormal (tiny packets = inefficient, possible attack)
   - Recommendations:
     * High utilization + no errors → Upgrade link or load balance
     * Errors/drops present → Check cables, NIC drivers, switch ports
     * Asymmetric traffic → Normal for client (download heavy) or server (upload heavy)
     * High packet rate + low byte rate → Small packets (check for SYN flood, fragmentation)
"""
