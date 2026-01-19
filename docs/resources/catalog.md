# Metric Catalogs

Two resources for discovering and understanding PCP metrics.

## Common Metrics Catalog

### URI

```
pcp://metrics/common
```

### Overview

The `pcp://metrics/common` resource provides a curated guide to the most useful PCP metrics, organized by troubleshooting domain. This is static documentation—it doesn't query the live system.

### Output Format

Returns a markdown document with metrics organized by category:

```markdown
# Common PCP Metric Groups

## CPU Performance
- kernel.all.cpu.user       → User-space CPU time (counter) ⚠️
- kernel.all.cpu.sys        → Kernel CPU time (counter) ⚠️
...

## Memory
- mem.physmem               → Total physical memory in KB (instant)
- mem.util.available        → Available for apps in KB (instant) ⭐
...
```

### Metric Categories

| Category | Description | Key Metrics |
|----------|-------------|-------------|
| CPU Performance | Processor utilization | `kernel.all.cpu.*`, `kernel.all.load` |
| Memory | RAM and swap usage | `mem.physmem`, `mem.util.*` |
| Disk I/O | Storage throughput | `disk.all.*`, `disk.dev.*` |
| Network | Interface traffic | `network.interface.*` |
| Process Metrics | Per-process stats | `proc.psinfo.*`, `proc.memory.*` |
| System Health | Uptime, users, agents | `kernel.all.uptime`, `pmcd.*` |
| Container Metrics | cgroup-based stats | `cgroup.*` |

### Legend

The catalog uses symbols to indicate metric characteristics:

| Symbol | Meaning |
|--------|---------|
| ⚠️ | Counter metric—use `get_system_snapshot` for rates |
| ⭐ | Recommended over alternatives |
| `[instances]` | Returns multiple values (per-CPU, per-disk, etc.) |
| `(instant)` | Point-in-time gauge value |
| `(counter)` | Cumulative counter since boot |

### Use Cases

#### Learning PCP

New to PCP? Browse this catalog to understand what metrics are available and how they're organized.

#### Troubleshooting Reference

Quick reference for which metrics to query when investigating specific issues:

| Problem | Relevant Metrics |
|---------|------------------|
| High CPU | `kernel.all.cpu.*`, `kernel.all.load` |
| Memory pressure | `mem.util.available`, `mem.util.cached` |
| Slow disk | `disk.dev.avactive`, `disk.all.read_bytes` |
| Network issues | `network.interface.in.errors` |

#### Counter Warning

The ⚠️ symbol highlights counter metrics. Querying these with `query_metrics` returns cumulative values since boot—not useful for current activity. Use `get_system_snapshot` or `get_process_top` instead, which handle rate calculation automatically.

### Example Content

```markdown
## CPU Performance
- kernel.all.cpu.user       → User-space CPU time (counter) ⚠️
- kernel.all.cpu.sys        → Kernel CPU time (counter) ⚠️
- kernel.all.cpu.idle       → Idle CPU time (counter) ⚠️
- kernel.all.cpu.wait.total → I/O wait time (counter) ⚠️ High = disk bottleneck
- kernel.all.load           → Load average (1, 5, 15 min) [instances: 1, 5, 15]
- kernel.all.runnable       → Runnable processes (instant)
- kernel.all.nprocs         → Total processes (instant)
- hinv.ncpu                 → Number of CPUs (instant)
```

---

## Metric Namespaces

### URI

```
pcp://namespaces
```

### Overview

The `pcp://namespaces` resource queries the **live PCP system** to discover available metric namespaces and active PMDAs (Performance Metrics Domain Agents). Use this to see exactly what's available on the connected system.

### Output Format

Returns a markdown document with live-discovered data:

```markdown
# PCP Metric Namespaces (Live Discovery)

Connected to: localhost
Active PMDAs: 12
Top-level namespaces: 15

## Available Namespaces

- **kernel.***: System-wide kernel statistics (CPU, load, interrupts, uptime)
- **mem.***: Memory subsystem (physmem, swap, cache, buffers, NUMA)
- **disk.***: Disk I/O (aggregates, per-device, partitions, device mapper)
...

## Active PMDAs on This System

pmcd, proc, xfs, linux, mmv, kvm, ...
```

### Sections

#### Available Namespaces

Lists all top-level metric namespaces discovered from the live system, with descriptions:

| Namespace | Description |
|-----------|-------------|
| `kernel.*` | System-wide kernel statistics |
| `mem.*` | Memory subsystem |
| `disk.*` | Disk I/O metrics |
| `network.*` | Network interfaces and protocols |
| `proc.*` | Per-process metrics |
| `hinv.*` | Hardware inventory (static info) |
| `pmcd.*` | PCP daemon health |
| `cgroup.*` | Container/cgroup metrics |
| `filesys.*` | Filesystem capacity metrics |

#### Active PMDAs

Shows which PMDAs are running on the system. PMDAs are plugins that provide metrics from different sources:

| PMDA | Provides |
|------|----------|
| `linux` | Core Linux kernel metrics |
| `proc` | Process metrics |
| `xfs` | XFS filesystem metrics |
| `kvm` | KVM virtualization metrics |
| `redis` | Redis server metrics |
| `postgresql` | PostgreSQL database metrics |

#### Namespace Categories

Groups namespaces by function:

- **Core System**: `kernel`, `mem`, `disk`, `network`, `proc`, `hinv`, `pmcd`
- **Filesystems**: `filesys`, `xfs`, `btrfs`, `zfs`, `quota`, `swap`
- **Virtualization**: `kvm`, `libvirt`, `containers`, `cgroup`, `hyperv`
- **Databases**: `redis`, `postgresql`, `mysql`, `elasticsearch`, `mongodb`
- **Web Servers**: `nginx`, `apache`, `haproxy`
- **Advanced**: `bcc` (eBPF), `hotproc`, `mmv`, `event`

#### Discovery Workflow

The resource includes a recommended workflow:

1. **Explore a namespace**: `search_metrics("kernel")`
2. **Count metrics**: `search_metrics("disk")` to see all `disk.*` metrics
3. **Get details**: `describe_metric("full.metric.name")`
4. **Query values**: `query_metrics(["name1", "name2"])`

### Use Cases

#### New System Discovery

When connecting to an unfamiliar system, browse `pcp://namespaces` to understand what's available:

```
"What metrics can I query on this system?"
→ Access pcp://namespaces
```

#### PMDA Verification

Check if expected PMDAs are active:

```
"Is the PostgreSQL PMDA running?"
→ Access pcp://namespaces, check Active PMDAs section
```

#### Capability Assessment

Different systems have different PMDAs installed. This resource shows exactly what's available on the target system.

### Live vs Static

| Resource | Data Source | Updates |
|----------|-------------|---------|
| `pcp://metrics/common` | Static documentation | Never (hardcoded) |
| `pcp://namespaces` | Live PCP query | Every access |

### Error Handling

If the PCP connection fails:

```markdown
Error discovering namespaces: Connection refused
```

### Example Usage

#### Exploring a New System

```python
# See what's available
namespaces = await session.read_resource("pcp://namespaces")
print(namespaces.contents[0].text)

# Found "redis" namespace - explore it
redis_metrics = await search_metrics(ctx, pattern="redis")
```

#### Verifying PMDA Installation

```
User: "Can I monitor PostgreSQL with this PCP installation?"

LLM accesses pcp://namespaces, checks for "postgresql" in Active PMDAs
→ "Yes, the postgresql PMDA is active. You can query metrics like..."
```

---

## Comparison

| Feature | `pcp://metrics/common` | `pcp://namespaces` |
|---------|------------------------|-------------------|
| Data source | Static | Live query |
| Purpose | Learning reference | System discovery |
| Content | Curated common metrics | All available namespaces |
| Updates | Manual (code changes) | Real-time |
| Use case | "What metrics exist in PCP?" | "What's on THIS system?" |

## Best Practices

### Start with Namespaces

On a new system, first access `pcp://namespaces` to see what's available, then use `pcp://metrics/common` as a reference for understanding specific metrics.

### Use Common Catalog for Learning

The common metrics catalog explains what each metric measures and warns about counter semantics—essential knowledge before querying.

### Combine with Tools

1. Browse `pcp://namespaces` → See available namespaces
2. Read `pcp://metrics/common` → Understand metric semantics
3. Use `search_metrics` → Find specific metrics
4. Use `describe_metric` → Get detailed metadata
5. Use `get_system_snapshot` or `query_metrics` → Get values
