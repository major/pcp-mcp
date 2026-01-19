"""Pydantic response models for strict output schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MetricValue(BaseModel):
    """A single metric value from PCP."""

    name: str = Field(description="Full metric name")
    value: float | int | str | None = Field(description="Metric value")
    units: str | None = Field(default=None, description="Unit of measurement")
    semantics: str | None = Field(default=None, description="counter, instant, or discrete")
    instance: str | None = Field(default=None, description="Instance name if per-instance metric")


class MetricInfo(BaseModel):
    """Metadata about a PCP metric."""

    name: str = Field(description="Full metric name")
    type: str = Field(description="Data type (u32, u64, float, string, etc.)")
    semantics: str = Field(description="counter, instant, or discrete")
    units: str = Field(description="Unit of measurement")
    help_text: str | None = Field(default=None, description="Metric help text")
    indom: str | None = Field(default=None, description="Instance domain if per-instance")


class MetricSearchResult(BaseModel):
    """Result from searching for metrics."""

    name: str = Field(description="Full metric name")
    help_text: str | None = Field(default=None, description="Brief description")


class MetricValueList(BaseModel):
    """Container for a list of metric values (MCP requires object return types)."""

    metrics: list[MetricValue] = Field(description="List of metric values")


class MetricSearchResultList(BaseModel):
    """Container for metric search results (MCP requires object return types)."""

    results: list[MetricSearchResult] = Field(description="List of matching metrics")


class InstancedMetric(BaseModel):
    """Metric with per-instance values (e.g., per-CPU, per-disk)."""

    name: str = Field(description="Metric name")
    instances: dict[str, float | int] = Field(
        description="Per-instance values, e.g., {'cpu0': 15.2, 'sda': 1000}"
    )
    aggregate: float | None = Field(
        default=None, description="Optional rollup (sum/avg) for quick reference"
    )


class CPUMetrics(BaseModel):
    """CPU utilization summary."""

    user_percent: float = Field(description="User CPU time percentage")
    system_percent: float = Field(description="System CPU time percentage")
    idle_percent: float = Field(description="Idle CPU time percentage")
    iowait_percent: float = Field(description="I/O wait percentage")
    ncpu: int = Field(description="Number of CPUs")
    assessment: str = Field(description="Brief interpretation of CPU state")


class MemoryMetrics(BaseModel):
    """Memory utilization summary."""

    total_bytes: int = Field(description="Total physical memory")
    used_bytes: int = Field(description="Used memory")
    free_bytes: int = Field(description="Free memory")
    available_bytes: int = Field(description="Available memory for applications")
    cached_bytes: int = Field(description="Cached memory")
    buffers_bytes: int = Field(description="Buffer memory")
    swap_used_bytes: int = Field(description="Used swap space")
    swap_total_bytes: int = Field(description="Total swap space")
    used_percent: float = Field(description="Memory usage percentage")
    assessment: str = Field(description="Brief interpretation of memory state")


class DiskMetrics(BaseModel):
    """Disk I/O summary."""

    read_bytes_per_sec: float = Field(description="Read throughput in bytes/sec")
    write_bytes_per_sec: float = Field(description="Write throughput in bytes/sec")
    reads_per_sec: float = Field(description="Read operations per second")
    writes_per_sec: float = Field(description="Write operations per second")
    assessment: str = Field(description="Brief interpretation of disk I/O state")


class NetworkMetrics(BaseModel):
    """Network I/O summary."""

    in_bytes_per_sec: float = Field(description="Inbound throughput in bytes/sec")
    out_bytes_per_sec: float = Field(description="Outbound throughput in bytes/sec")
    in_packets_per_sec: float = Field(description="Inbound packets per second")
    out_packets_per_sec: float = Field(description="Outbound packets per second")
    assessment: str = Field(description="Brief interpretation of network state")


class LoadMetrics(BaseModel):
    """System load summary."""

    load_1m: float = Field(description="1-minute load average")
    load_5m: float = Field(description="5-minute load average")
    load_15m: float = Field(description="15-minute load average")
    runnable: int = Field(description="Number of runnable processes")
    nprocs: int = Field(description="Total number of processes")
    assessment: str = Field(description="Brief interpretation of load state")


class SystemSnapshot(BaseModel):
    """Point-in-time system health overview."""

    timestamp: str = Field(description="ISO8601 timestamp")
    hostname: str = Field(description="Target host name")
    cpu: CPUMetrics | None = Field(default=None, description="CPU metrics if requested")
    memory: MemoryMetrics | None = Field(default=None, description="Memory metrics if requested")
    disk: DiskMetrics | None = Field(default=None, description="Disk I/O metrics if requested")
    network: NetworkMetrics | None = Field(
        default=None, description="Network I/O metrics if requested"
    )
    load: LoadMetrics | None = Field(default=None, description="Load metrics if requested")


class ProcessInfo(BaseModel):
    """A process with resource consumption details."""

    pid: int = Field(description="Process ID")
    command: str = Field(description="Command name")
    cmdline: str = Field(description="Full command line (truncated)")
    cpu_percent: float | None = Field(default=None, description="CPU usage percentage")
    rss_bytes: int = Field(description="Resident set size in bytes")
    rss_percent: float = Field(description="RSS as percentage of total memory")
    io_read_bytes_per_sec: float | None = Field(default=None, description="Read bytes/sec")
    io_write_bytes_per_sec: float | None = Field(default=None, description="Write bytes/sec")


class ProcessTopResult(BaseModel):
    """Top processes by resource consumption."""

    timestamp: str = Field(description="ISO8601 timestamp")
    hostname: str = Field(description="Target host name")
    sort_by: str = Field(description="Resource used for sorting")
    sample_interval: float = Field(description="Sampling interval used")
    processes: list[ProcessInfo] = Field(description="Top processes sorted by requested resource")
    total_memory_bytes: int = Field(description="Total system memory")
    ncpu: int = Field(description="Number of CPUs")
    assessment: str = Field(description="Brief interpretation of top processes")


class DiagnosisResult(BaseModel):
    """LLM-powered system diagnosis."""

    timestamp: str = Field(description="ISO8601 timestamp")
    hostname: str = Field(description="Target host name")
    diagnosis: str = Field(description="LLM-generated analysis of system health")
    severity: str = Field(description="Severity level: healthy, warning, or critical")
    recommendations: list[str] = Field(description="Actionable recommendations")
