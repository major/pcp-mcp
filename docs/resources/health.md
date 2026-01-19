# pcp://health

Quick system health summary resource.

## Overview

The `pcp://health` resource provides a human-readable system health summary covering CPU, memory, and load metrics. It's designed for quick health checks without needing to invoke tools.

## URI

```
pcp://health
```

## Output Format

Returns a markdown-formatted text summary:

```markdown
# System Health Summary
Host: localhost
Time: 2024-01-15 14:30:00 UTC

## CPU
- User: 15.2%
- System: 5.1%
- Idle: 78.5%
- I/O Wait: 1.2%
- CPUs: 8
- Assessment: Normal CPU usage

## Memory
- Used: 45.2% (7.2 / 16.0 GB)
- Available: 8.8 GB
- Cached: 4.2 GB
- Swap: 0.0 GB / 8.0 GB
- Assessment: Healthy memory usage

## Load
- 1 min: 1.25
- 5 min: 1.10
- 15 min: 0.95
- Runnable: 3
- Processes: 245
- Assessment: Normal load
```

## Metrics Included

### CPU Metrics

| Field | Description | Source Metric |
|-------|-------------|---------------|
| User | CPU time in user space (%) | `kernel.all.cpu.user` |
| System | CPU time in kernel space (%) | `kernel.all.cpu.sys` |
| Idle | CPU idle time (%) | `kernel.all.cpu.idle` |
| I/O Wait | CPU waiting for I/O (%) | `kernel.all.cpu.wait.total` |
| CPUs | Number of CPU cores | `hinv.ncpu` |
| Assessment | Interpreted status | Calculated |

### Memory Metrics

| Field | Description | Source Metric |
|-------|-------------|---------------|
| Used | Memory utilization percentage | `mem.util.used` / `mem.physmem` |
| Available | Memory available for apps | `mem.util.available` |
| Cached | Page cache size | `mem.util.cached` |
| Swap | Swap usage | `mem.util.swapFree` / `mem.util.swapTotal` |
| Assessment | Interpreted status | Calculated |

### Load Metrics

| Field | Description | Source Metric |
|-------|-------------|---------------|
| 1/5/15 min | Load averages | `kernel.all.load` |
| Runnable | Runnable processes | `kernel.all.runnable` |
| Processes | Total processes | `kernel.all.nprocs` |
| Assessment | Interpreted status (vs CPU count) | Calculated |

## How It Works

1. Fetches CPU, memory, and load metrics from PCP
2. Takes two samples (1 second apart) for rate calculation on CPU counters
3. Calculates percentages and formats values
4. Generates assessment strings based on thresholds
5. Returns formatted markdown

## Assessment Thresholds

### CPU Assessment

| Condition | Assessment |
|-----------|------------|
| User + System < 70% | Normal CPU usage |
| User + System 70-90% | Elevated CPU usage |
| User + System > 90% | High CPU usage |
| I/O Wait > 20% | High I/O wait (disk bottleneck) |

### Memory Assessment

| Condition | Assessment |
|-----------|------------|
| Used < 70% | Healthy memory usage |
| Used 70-85% | Moderate memory pressure |
| Used 85-95% | High memory usage |
| Used > 95% | Critical memory pressure |
| Swap in use | Swapping active |

### Load Assessment

| Condition | Assessment |
|-----------|------------|
| Load 1m < CPU count | Normal load |
| Load 1m = CPU count | System fully utilized |
| Load 1m > CPU count | System overloaded |
| Load increasing | Load trending up |
| Load decreasing | Load trending down |

## Use Cases

### Quick Health Check

Access `pcp://health` to get an instant overview of system status without configuring queries.

### LLM Context

The markdown format is optimized for LLM consumption. Include the health summary in prompts for context-aware responses.

### Monitoring Dashboards

Embed the health summary in dashboards or status pages for human-readable system status.

## Comparison with get_system_snapshot

| Feature | `pcp://health` | `get_system_snapshot` |
|---------|----------------|----------------------|
| Format | Markdown text | Structured JSON |
| Categories | CPU, Memory, Load only | All 5 categories |
| Customization | None | Filter by category |
| Sample interval | Fixed 1 second | Configurable |
| Best for | Human reading, LLM context | Programmatic analysis |

## Limitations

### Fixed Categories

Only includes CPU, memory, and load. For disk or network metrics, use `get_system_snapshot`.

### Fixed Sample Interval

Uses a 1-second sample interval. For busy systems, the `get_system_snapshot` tool with a longer interval may provide more stable readings.

### No Historical Data

Returns point-in-time data only. For trends, query the resource multiple times or use PCP's archiving features.

## Error Handling

If PCP is unavailable or metrics cannot be fetched, the resource returns an error message:

```markdown
Error fetching health data: Connection refused
```

## Example Usage

### Claude Desktop

1. Open the Resources panel
2. Click on `pcp://health`
3. View the formatted health summary

### MCP Client Code

```python
from fastmcp import FastMCP

async def check_health():
    async with FastMCP.connect("pcp-mcp") as client:
        async with client.session() as session:
            result = await session.read_resource("pcp://health")
            print(result.contents[0].text)
```

### Natural Language Query

```
"What's the current system health?"
```

An LLM can access this resource to provide a natural language summary of system status.
