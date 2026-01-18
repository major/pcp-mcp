# PCP MCP Server - Implementation Plan

MCP server for Performance Co-Pilot (PCP) on RHEL/Fedora/CentOS systems.

## Design Philosophy

Follow the `porkbun-mcp` patterns:
- FastMCP with lifespan context management
- Pydantic models for all responses
- Tools for actions, Resources for read-only data browsing
- pydantic-settings for configuration
- Clean separation: `server.py`, `config.py`, `context.py`, `errors.py`, `models.py`
- Tools and resources in subdirectories with `__init__.py` registration

## PCP Component Architecture

Understanding how PCP components work together informed our API choice:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           PCP Architecture                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐     ┌──────────────┐     ┌─────────────────────────┐  │
│  │    pmcd     │────▶│  pmlogger    │────▶│   Archive files         │  │
│  │ (collector) │     │ (historian)  │     │ (.meta, .0, .index)     │  │
│  └──────┬──────┘     └──────────────┘     └────────────┬────────────┘  │
│         │                                              │               │
│         │                                              ▼ (requires     │
│         │                                                -t + Redis)  │
│         ▼                                     ┌─────────────────────┐  │
│  ┌──────────────┐                             │  /series/* API      │  │
│  │   pmproxy    │─────────────────────────────│  (historical data)  │  │
│  │ (REST API)   │                             └─────────────────────┘  │
│  └──────┬───────┘                                                      │
│         │                                                              │
│         ▼                                                              │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  /pmapi/* REST API  ◀── This is what pcp-mcp uses (v1)          │  │
│  │  - /pmapi/context   - Create PMAPI context                      │  │
│  │  - /pmapi/fetch     - Get current metric values                 │  │
│  │  - /pmapi/metric    - Metric metadata (names, types, units)     │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Component Roles

| Component | Purpose | Data Type |
|-----------|---------|-----------|
| **pmcd** | Metrics collector daemon, aggregates from PMDAs | Live |
| **pmlogger** | Writes binary archive files for historical analysis | Historical |
| **pmproxy** | REST API gateway, serves metrics via HTTP/JSON | Both* |

*pmproxy serves live data via `/pmapi/*`. Historical data via `/series/*` requires Redis/Valkey.

### API Choice: Why `/pmapi/*` for v1

| Approach | Live Data | Historical | Dependencies | Complexity |
|----------|-----------|------------|--------------|------------|
| **`/pmapi/*` (our choice)** | ✅ Yes | ❌ No | pmproxy only | 🟢 Low |
| `/series/*` | ✅ Yes | ✅ Yes | pmproxy + Redis/Valkey | 🟡 Medium |
| Direct pmlogger archives | ❌ No | ✅ Yes | Python PMAPI bindings | 🔴 High |
| Direct PMAPI | ✅ Yes | ❌ No | pcp-libs | 🔴 High |

### v1 vs v2 Scope

**v1 (Current Plan):** Real-time metrics via `/pmapi/*`
- ✅ No extra dependencies (pmproxy runs by default on RHEL/Fedora)
- ✅ Covers 80% of use cases ("why is my system slow *right now*?")
- ✅ Client-side rate calculation matches how PCP tools work
- ✅ Configurable target host (local or remote pmcd)

**v2 (Future):** Add historical queries via `/series/*`
- Requires Redis/Valkey setup (document as optional)
- Enables "show me CPU over the last hour" queries
- New tool: `get_metric_history(metric, start, end)`
- Keep backward compatible - historical features are additive

### Remote Host Monitoring

pmproxy acts as a **protocol proxy** - it can collect metrics from remote `pmcd` instances:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Remote Monitoring Architecture                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Option 1: Local (default)                                              │
│  ┌─────────┐     ┌───────────┐     ┌──────────┐                        │
│  │ pcp-mcp │────▶│  pmproxy  │────▶│   pmcd   │  (all on same host)    │
│  └─────────┘     └───────────┘     └──────────┘                        │
│                                                                         │
│  Option 2: Central monitoring server                                    │
│  ┌─────────┐     ┌───────────┐     ┌──────────┐                        │
│  │ pcp-mcp │────▶│  pmproxy  │────▶│   pmcd   │  webserver1            │
│  └─────────┘     │ (central) │────▶│   pmcd   │  dbserver1             │
│                  └───────────┘────▶│   pmcd   │  appserver1            │
│                                    └──────────┘                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

The `hostspec` parameter in `/pmapi/context` specifies which pmcd to connect to:

```bash
# Local (default)
curl "http://localhost:44322/pmapi/context?hostspec=localhost"

# Remote host
curl "http://localhost:44322/pmapi/context?hostspec=webserver1.example.com"
```

**Configuration:** Use `PCP_TARGET_HOST` environment variable or `--target-host` CLI flag.

**Security Note:** pmcd accepts connections from any host by default. For production,
configure access controls in `/etc/pcp/pmcd/pmcd.conf` or use firewall rules.

### Key Insight: Rate Calculation

Both `pmlogger` archives and `/pmapi/fetch` store **raw counter values** (cumulative).
PCP tools like `pmval`, `pmrep` calculate rates client-side. Our `fetch_with_rates()`
method (see "Rate Metrics Handling" section) follows this same pattern.

## Architecture

```
src/pcp_mcp/
    __init__.py          # CLI entry point (argparse)
    server.py            # FastMCP setup + lifespan
    config.py            # PCPMCPSettings (pydantic-settings)
    context.py           # get_client(), get_settings() helpers
    errors.py            # PCP error -> ToolError mapping
    models.py            # Pydantic response models
    client.py            # Async httpx wrapper for pmproxy REST API
    tools/
        __init__.py      # register_tools()
        metrics.py       # Core metric tools
        system.py        # System health tools
    resources/
        __init__.py      # register_resources()
        metrics.py       # Metric discovery resources
        health.py        # Health summary resources
```

## Anti-Sprawl Strategy: Clumped Tools

Instead of one tool per metric category, use **semantic groupings** that return
coherent "stories" about system state. The LLM can ask follow-up questions.

### Core Tools (5 total)

| Tool | Purpose | Returns |
|------|---------|---------|
| `query_metrics` | Fetch specific metrics by name | Current values for requested metrics |
| `search_metrics` | Find metrics matching a pattern | List of metric names + descriptions |
| `describe_metric` | Get metadata for a metric | Units, semantics, type, help text |
| `get_system_snapshot` | **Clumped** system overview | CPU, memory, disk, network in one call |
| `get_process_top` | Top processes by resource | CPU/memory hogs with context |

### The "Snapshot" Approach (Key Anti-Sprawl Pattern)

Instead of:
```python
# BAD: Tool sprawl
get_cpu_usage()
get_memory_usage()
get_disk_io()
get_network_io()
get_load_average()
```

Do:
```python
# GOOD: Single clumped tool
get_system_snapshot(categories: list[str] = ["cpu", "memory", "disk", "network", "load"])
```

The LLM calls ONE tool and gets a coherent picture. If it needs to drill down,
it uses `query_metrics` with specific metric names discovered from the snapshot.

### Snapshot Response Model

```python
class SystemSnapshot(BaseModel):
    """Point-in-time system health overview."""
    
    timestamp: str
    hostname: str
    
    # Each section is optional - only included if requested
    cpu: CPUMetrics | None = None
    memory: MemoryMetrics | None = None
    disk: DiskMetrics | None = None
    network: NetworkMetrics | None = None
    load: LoadMetrics | None = None

class CPUMetrics(BaseModel):
    """CPU utilization summary."""
    
    user_percent: float
    system_percent: float
    idle_percent: float
    iowait_percent: float
    ncpu: int
    # Interpretation hint for LLM
    assessment: str  # e.g., "CPU is idle", "CPU bound on user processes"

class MemoryMetrics(BaseModel):
    """Memory utilization summary."""
    
    total_bytes: int
    used_bytes: int
    free_bytes: int
    available_bytes: int
    cached_bytes: int
    buffers_bytes: int
    swap_used_bytes: int
    swap_total_bytes: int
    used_percent: float
    assessment: str  # e.g., "Memory pressure is low", "Swapping actively"
```

### Metric Name Conventions

PCP uses hierarchical metric names. Common prefixes:

| Prefix | Domain |
|--------|--------|
| `kernel.all.*` | System-wide kernel stats (load, cpu, interrupts) |
| `mem.*` | Memory (util, vmstat, slabinfo) |
| `disk.*` | Disk I/O (dev, partitions) |
| `network.*` | Network interfaces |
| `proc.*` | Per-process metrics |
| `hinv.*` | Hardware inventory (ncpu, physmem) |

### Clump Mappings

```python
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
        "kernel.all.load",  # 1, 5, 15 min (has instances)
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
```

## Resources (Read-Only Discovery)

| Resource URI | Purpose |
|--------------|---------|
| `pcp://health` | Quick system health summary (pre-computed snapshot) |
| `pcp://metrics/{pattern}` | Browse metrics matching pattern |
| `pcp://metric/{name}` | Detailed info about a specific metric |

## Configuration

```python
class PCPMCPSettings(BaseSettings):
    """PCP MCP Server configuration."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="PCP_",
        extra="ignore",
    )
    
    # pmproxy connection
    host: str = Field(default="localhost", description="pmproxy host")
    port: int = Field(default=44322, description="pmproxy port")
    use_tls: bool = Field(default=False, description="Use HTTPS")
    
    # Optional auth (if pmproxy requires it)
    username: str | None = Field(default=None, description="HTTP basic auth user")
    password: str | None = Field(default=None, description="HTTP basic auth password")
    
    @property
    def base_url(self) -> str:
        scheme = "https" if self.use_tls else "http"
        return f"{scheme}://{self.host}:{self.port}"
```

## Client Layer

Thin async wrapper around pmproxy REST API:

```python
class PCPClient:
    """Async client for pmproxy REST API."""
    
    def __init__(
        self,
        base_url: str,
        target_host: str = "localhost",
        auth: tuple[str, str] | None = None,
        timeout: float = 30.0,
    ):
        self._base_url = base_url
        self._target_host = target_host  # Which pmcd to connect to
        self._auth = auth
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._context_id: int | None = None
    
    async def __aenter__(self) -> Self:
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            auth=self._auth,
            timeout=self._timeout,
        )
        # Create pmapi context for target host
        resp = await self._client.get(
            "/pmapi/context",
            params={"hostspec": self._target_host},
        )
        resp.raise_for_status()
        self._context_id = resp.json()["context"]
        return self
    
    async def __aexit__(self, *args) -> None:
        if self._client:
            await self._client.aclose()
    
    @property
    def target_host(self) -> str:
        """The pmcd host this client is connected to."""
        return self._target_host
    
    async def fetch(self, metric_names: list[str]) -> dict:
        """Fetch current values for metrics."""
        resp = await self._client.get(
            "/pmapi/fetch",
            params={"context": self._context_id, "names": ",".join(metric_names)},
        )
        resp.raise_for_status()
        return resp.json()
    
    async def search(self, pattern: str) -> list[dict]:
        """Search for metrics matching pattern."""
        resp = await self._client.get(
            "/pmapi/metric",
            params={"context": self._context_id, "prefix": pattern},
        )
        resp.raise_for_status()
        return resp.json().get("metrics", [])
    
    async def describe(self, metric_name: str) -> dict:
        """Get metric metadata."""
        resp = await self._client.get(
            "/pmapi/metric",
            params={"context": self._context_id, "names": metric_name},
        )
        resp.raise_for_status()
        metrics = resp.json().get("metrics", [])
        return metrics[0] if metrics else {}
```

## Error Handling

```python
class PCPError(Exception):
    """Base PCP error."""
    pass

class PCPConnectionError(PCPError):
    """Cannot connect to pmproxy."""
    pass

class PCPMetricNotFoundError(PCPError):
    """Metric does not exist."""
    pass

def handle_pcp_error(e: Exception, operation: str) -> ToolError:
    """Convert PCP exceptions to MCP ToolErrors."""
    match e:
        case httpx.ConnectError():
            return ToolError(
                f"Cannot connect to pmproxy. Is it running? (systemctl start pmproxy)"
            )
        case httpx.HTTPStatusError() as he if he.response.status_code == 404:
            return ToolError(f"Metric not found during {operation}")
        case httpx.HTTPStatusError() as he:
            return ToolError(f"pmproxy error ({he.response.status_code}): {he.response.text}")
        case _:
            return ToolError(f"Error during {operation}: {e}")
```

## Dependencies

```toml
[project]
name = "pcp-mcp"
version = "0.1.0"
description = "MCP server for Performance Co-Pilot"
requires-python = ">=3.10"
dependencies = [
    "fastmcp>=2.0.0",
    "httpx>=0.27",
    "pydantic-settings>=2.0.0",
]
```

Note: Python 3.10+ (not 3.14) for broader compatibility on RHEL 8/9.

## Implementation Order

1. **Phase 1: Skeleton**
   - [ ] Project structure with pyproject.toml
   - [ ] `config.py` with PCPMCPSettings
   - [ ] `client.py` with basic PCPClient
   - [ ] `server.py` with lifespan management
   - [ ] `__init__.py` CLI entry point
   - [ ] Project scaffolding files (see below)

2. **Phase 2: Core Tools**
   - [ ] `query_metrics` - fetch arbitrary metrics
   - [ ] `search_metrics` - discover metrics by pattern
   - [ ] `describe_metric` - get metric metadata

3. **Phase 3: Clumped Tools**
   - [ ] `get_system_snapshot` - the main anti-sprawl tool
   - [ ] Response models with `assessment` fields
   - [ ] `get_process_top` - top resource consumers

4. **Phase 4: Resources**
   - [ ] `pcp://health` - quick health check
   - [ ] `pcp://metrics/{pattern}` - browsable metric discovery

5. **Phase 5: Polish**
   - [ ] Error handling refinement
   - [ ] Tests with respx mocking
   - [ ] Documentation

## Project Scaffolding (from porkbun-mcp)

Copy and adapt these files from porkbun-mcp:

### Root Files

| File | Purpose | Adaptation Needed |
|------|---------|-------------------|
| `Makefile` | Dev commands (lint, test, etc.) | Change `porkbun_mcp` → `pcp_mcp` |
| `.gitignore` | Standard Python gitignore | None |
| `renovate.json` | Automated dependency updates | None |
| `.coderabbit.yaml` | AI code review config | Update path instructions for pcp-mcp |
| `.python-version` | Python version for pyenv | None (keep 3.14) |

### GitHub Directory

```
.github/
    copilot-instructions.md    # Copilot review guidance (adapt for pcp-mcp)
    dependabot.yml             # Dependency updates
    workflows/
        ci.yml                 # Lint, typecheck, test
        codeql.yml             # Security scanning
        docs.yml               # MkDocs deployment (if using docs)
        publish.yml            # PyPI publishing on release
```

### Makefile (adapt from porkbun-mcp)

```makefile
.PHONY: all lint format format-check typecheck test test-cov check fix clean complexity

all: check

lint:
	uv run ruff check .

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

typecheck:
	uv run ty check

test:
	uv run pytest

test-cov:
	uv run pytest --cov-report=html

check: lint format-check typecheck test

fix:
	uv run ruff check --fix .
	uv run ruff format .

complexity:
	@output=$$(uv run radon cc src/pcp_mcp -n D -s); \
	if [ -n "$$output" ]; then \
		echo "$$output"; \
		echo "ERROR: Functions with complexity D or higher found"; \
		exit 1; \
	else \
		echo "Complexity check passed (no D+ functions)"; \
	fi

clean:
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov coverage.xml site
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
```

### CI Workflow (.github/workflows/ci.yml)

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
  workflow_call:

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: astral-sh/setup-uv@v7
      - run: uv sync --dev
      - run: uv run ruff check .
      - run: uv run ruff format --check .

  typecheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: astral-sh/setup-uv@v7
      - run: uv sync --dev
      - run: uv run ty check

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: astral-sh/setup-uv@v7
        with:
          python-version: "3.14"
      - run: uv sync --dev
      - run: uv run pytest --cov-report=xml
      - uses: codecov/codecov-action@v5
```

### CodeRabbit Config (.coderabbit.yaml) - Key Changes

Update path instructions for pcp-mcp patterns:

```yaml
path_instructions:
  - path: "src/pcp_mcp/**/*.py"
    instructions: |
      pcp-mcp: MCP server for Performance Co-Pilot. Python 3.10+, FastMCP 2.0+.

      INVERSION CHECKLIST - What would cause this to fail?

      MCP server failures to prevent:
      - Tools not returning proper Pydantic response models
      - Not handling httpx exceptions (convert to ToolError)
      - Blocking calls in async tool functions
      - Missing type hints or docstrings
      - Rate calculation errors (counter vs gauge metrics)

      FastMCP patterns to enforce:
      - Tools use @mcp.tool() decorator
      - Resources use @mcp.resource() decorator
      - Context accessed via ctx.request_context.lifespan_context
      - Errors raised as ToolError or ResourceError

  - path: "src/pcp_mcp/client.py"
    instructions: |
      Async httpx wrapper for pmproxy REST API.

      INVERSION: What would cause the client to fail?
      - Not creating pmapi context on __aenter__
      - Not closing httpx client on __aexit__
      - Rate calculation with wrong elapsed time
      - Not handling counter wrap-around
      - Timeout not respected

  - path: "src/pcp_mcp/tools/**/*.py"
    instructions: |
      MCP Tools - the core functionality.

      INVERSION: What would cause tools to fail?
      - Exceptions not mapped to ToolError via handle_pcp_error()
      - Missing Annotated[type, Field(...)] for parameter descriptions
      - sample_interval too short for accurate rates
      - Not awaiting async calls
```

### Copilot Instructions (.github/copilot-instructions.md) - Key Changes

```markdown
## Project Context: pcp-mcp

MCP server for Performance Co-Pilot (PCP). Python 3.10+, FastMCP 2.0+.

### Tech Stack
- **MCP Framework**: FastMCP 2.0+
- **HTTP Client**: httpx (async)
- **Backend**: pmproxy REST API
- **Type checking**: ty
- **Linting/Formatting**: ruff
- **Testing**: pytest + pytest-asyncio + respx
- **Package manager**: uv

### Key Design Decisions
- Clumped tools (get_system_snapshot) instead of per-metric tools
- Client-side rate calculation for counter metrics
- Configurable target_host for remote monitoring
- Pydantic response models with assessment fields
```

## Example Usage

```bash
# Start the server (monitor localhost)
pcp-mcp

# Monitor a remote host's metrics
PCP_TARGET_HOST=webserver1.example.com pcp-mcp

# Connect to pmproxy on a different host
PCP_HOST=metrics.example.com pcp-mcp

# Monitor remote host via central pmproxy
PCP_HOST=metrics.example.com PCP_TARGET_HOST=dbserver1 pcp-mcp

# With TLS
PCP_USE_TLS=true pcp-mcp
```

### LLM Interaction Example

```
User: "Why is my system slow?"

LLM calls: get_system_snapshot(categories=["cpu", "memory", "load", "disk"])

Response:
{
  "timestamp": "2024-01-15T10:30:00Z",
  "hostname": "webserver1",
  "cpu": {
    "user_percent": 15.2,
    "system_percent": 5.1,
    "idle_percent": 10.5,
    "iowait_percent": 69.2,
    "ncpu": 8,
    "assessment": "High I/O wait - system is disk bound"
  },
  "memory": {
    "used_percent": 45.0,
    "assessment": "Memory utilization is normal"
  },
  "load": {
    "load_1m": 12.5,
    "load_5m": 10.2,
    "load_15m": 8.1,
    "assessment": "Load is elevated (1.5x CPU count)"
  },
  "disk": {
    "read_bytes_sec": 150000000,
    "write_bytes_sec": 5000000,
    "assessment": "Heavy read I/O (150 MB/s reads)"
  }
}

LLM: "Your system is slow due to high disk I/O. The CPU is spending 69% of 
      its time waiting for disk operations, with 150 MB/s of read activity. 
      This suggests either heavy database queries, log processing, or 
      insufficient disk caching. Would you like me to identify which 
      processes are causing the I/O?"
```

## Design Decisions (Resolved)

### Q1: Historical Data → **Skip for v1**

Time-series queries add complexity (Redis dependency, `/series/*` endpoints). The current
design gives "right now" answers which covers 80% of troubleshooting use cases. Add
`get_metric_history(metric, start, end)` in v2 if users need it.

### Q2: Per-Process Metrics → **Separate tool + optional drill-down**

The `proc.*` namespace is massive. Solution:
- `get_process_top` handles "what's hogging resources?" (top N by CPU/memory/IO)
- Optional future: `get_process_detail(pid)` for deep dive on a specific process

### Q3: Instance Handling → **Consistent `instances` dict pattern**

```python
class InstancedMetric(BaseModel):
    """Metric with per-instance values (e.g., per-CPU, per-disk)."""
    
    name: str = Field(description="Metric name")
    instances: dict[str, float] = Field(
        description="Per-instance values, e.g., {'cpu0': 15.2, 'sda': 1000}"
    )
    aggregate: float | None = Field(
        default=None,
        description="Optional rollup (sum/avg) for quick reference"
    )
```

This handles per-CPU, per-disk, per-interface cleanly. The `aggregate` field lets the
LLM get a quick answer while still having per-instance detail available.

### Q4: Custom PMDAs → **Skip for v1**

Keep `search_metrics` generic - it'll find PMDA-provided metrics anyway. No need for
explicit PMDA management tools.

---

## Rate Metrics Handling (Critical for disk/network)

PCP counters (bytes, packets) are **cumulative**. For meaningful rates, we need delta/time.

### The Problem

`/pmapi/fetch` returns raw counter values, not rates:
```json
{"disk.all.read_bytes": 123456789}  // Cumulative since boot
```

### Solution: Client-Side Rate Calculation

pmproxy's `/pmapi/derive` with `rate(expr)` is elegant but adds API complexity. Instead,
we'll do **client-side calculation** with two samples:

```python
async def fetch_with_rates(
    self,
    metric_names: list[str],
    sample_interval: float = 1.0,
) -> dict[str, MetricValue]:
    """Fetch metrics, calculating rates for counters.
    
    Takes two samples separated by `sample_interval` seconds.
    Counter metrics are converted to per-second rates.
    Gauge metrics return the second sample's value.
    """
    t1 = await self.fetch(metric_names)
    await asyncio.sleep(sample_interval)
    t2 = await self.fetch(metric_names)
    
    elapsed = t2["timestamp"] - t1["timestamp"]
    
    results = {}
    for metric in metric_names:
        v1, v2 = t1["values"][metric], t2["values"][metric]
        if is_counter_metric(metric):
            # Rate = delta / elapsed
            results[metric] = (v2 - v1) / elapsed
        else:
            results[metric] = v2
    
    return results
```

### Identifying Counter Metrics

PCP metrics have semantics (counter vs instant). We can:
1. Check `/pmapi/metric` response for `sem: "counter"`, OR
2. Maintain a known-counters list for snapshot metrics (simpler)

```python
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
```

### Impact on `get_system_snapshot`

Add `sample_interval` parameter (default 1.0s):

```python
async def get_system_snapshot(
    ctx: Context,
    categories: Annotated[
        list[str],
        Field(default=["cpu", "memory", "disk", "network", "load"])
    ],
    sample_interval: Annotated[
        float,
        Field(default=1.0, ge=0.1, le=10.0, description="Seconds between samples for rate calculation")
    ] = 1.0,
) -> SystemSnapshot:
    """Get a point-in-time system health overview.
    
    For rate metrics (CPU %, disk I/O, network throughput), takes two samples
    separated by `sample_interval` seconds to calculate per-second rates.
    """
```

---

## `get_process_top` Specification

### Purpose

Identify top resource consumers by CPU, memory, or I/O. Answers "what's eating my resources?"

### PCP Metrics Used

```python
PROCESS_TOP_METRICS = {
    "cpu": [
        "proc.psinfo.utime",    # User CPU time (counter, ms)
        "proc.psinfo.stime",    # System CPU time (counter, ms)
    ],
    "memory": [
        "proc.memory.rss",      # Resident set size (bytes)
        "proc.memory.vmsize",   # Virtual memory size (bytes)
    ],
    "io": [
        "proc.io.read_bytes",   # Bytes read (counter)
        "proc.io.write_bytes",  # Bytes written (counter)
    ],
    # Always fetch for context:
    "info": [
        "proc.psinfo.pid",
        "proc.psinfo.cmd",      # Command name
        "proc.psinfo.psargs",   # Full command line
    ],
}
```

**Note**: Instances are PIDs. The instance domain maps PID → process info.

### Tool Signature

```python
@mcp.tool()
async def get_process_top(
    ctx: Context,
    sort_by: Annotated[
        Literal["cpu", "memory", "io"],
        Field(description="Resource to sort by")
    ] = "cpu",
    limit: Annotated[
        int,
        Field(default=10, ge=1, le=50, description="Number of processes to return")
    ] = 10,
    sample_interval: Annotated[
        float,
        Field(default=1.0, ge=0.5, le=5.0, description="Seconds to sample for CPU/IO rates")
    ] = 1.0,
) -> ProcessTopResult:
    """Get top processes by resource consumption.
    
    For CPU and I/O, takes two samples to calculate rates. Memory is instantaneous.
    """
```

### Response Model

```python
class ProcessInfo(BaseModel):
    """A process with resource consumption details."""
    
    pid: int = Field(description="Process ID")
    command: str = Field(description="Command name")
    cmdline: str = Field(description="Full command line (truncated)")
    
    # CPU (only populated if sort_by="cpu" or for top results)
    cpu_percent: float | None = Field(default=None, description="CPU usage %")
    
    # Memory
    rss_bytes: int = Field(description="Resident set size in bytes")
    rss_percent: float = Field(description="RSS as % of total memory")
    
    # I/O (only populated if sort_by="io")
    io_read_bytes_sec: float | None = Field(default=None, description="Read bytes/sec")
    io_write_bytes_sec: float | None = Field(default=None, description="Write bytes/sec")


class ProcessTopResult(BaseModel):
    """Top processes by resource consumption."""
    
    timestamp: str = Field(description="ISO8601 timestamp")
    hostname: str = Field(description="Host name")
    sort_by: str = Field(description="Resource used for sorting")
    sample_interval: float = Field(description="Sampling interval used")
    
    processes: list[ProcessInfo] = Field(description="Top processes, sorted by requested resource")
    
    # System context
    total_memory_bytes: int = Field(description="Total system memory")
    ncpu: int = Field(description="Number of CPUs")
    
    assessment: str = Field(
        description="Brief interpretation, e.g., 'firefox using 45% of memory'"
    )
```

### Example Output

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "hostname": "webserver1",
  "sort_by": "cpu",
  "sample_interval": 1.0,
  "processes": [
    {
      "pid": 12345,
      "command": "python",
      "cmdline": "python /app/worker.py --threads=8",
      "cpu_percent": 156.2,
      "rss_bytes": 2147483648,
      "rss_percent": 12.5
    },
    {
      "pid": 6789,
      "command": "postgres",
      "cmdline": "postgres: worker process",
      "cpu_percent": 45.3,
      "rss_bytes": 536870912,
      "rss_percent": 3.1
    }
  ],
  "total_memory_bytes": 17179869184,
  "ncpu": 8,
  "assessment": "python worker is CPU-bound (156% = 1.5 cores). postgres is active but moderate."
}
```

---

## Updated Configuration

Add timeout and target host for pmproxy requests:

```python
class PCPMCPSettings(BaseSettings):
    """PCP MCP Server configuration."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="PCP_",
        extra="ignore",
    )
    
    # pmproxy connection (where pmproxy is running)
    host: str = Field(default="localhost", description="pmproxy host")
    port: int = Field(default=44322, description="pmproxy port")
    use_tls: bool = Field(default=False, description="Use HTTPS for pmproxy connection")
    timeout: float = Field(default=30.0, description="Request timeout in seconds")
    
    # Target host (which pmcd to collect metrics from, passed as hostspec)
    target_host: str = Field(
        default="localhost",
        description="Target pmcd host to monitor (can be remote hostname)"
    )
    
    # Optional auth (if pmproxy requires it)
    username: str | None = Field(default=None, description="HTTP basic auth user")
    password: str | None = Field(default=None, description="HTTP basic auth password")
    
    @property
    def base_url(self) -> str:
        """URL for connecting to pmproxy."""
        scheme = "https" if self.use_tls else "http"
        return f"{scheme}://{self.host}:{self.port}"
    
    @property
    def auth(self) -> tuple[str, str] | None:
        """Auth tuple for httpx, or None if no auth configured."""
        if self.username and self.password:
            return (self.username, self.password)
        return None
```

**Environment variables:**
- `PCP_HOST` - pmproxy hostname (default: localhost)
- `PCP_PORT` - pmproxy port (default: 44322)
- `PCP_TARGET_HOST` - pmcd host to monitor (default: localhost)
- `PCP_USE_TLS` - use HTTPS (default: false)
- `PCP_TIMEOUT` - request timeout in seconds (default: 30)

---

## Lessons from porkbun-mcp

Patterns to replicate exactly:

### 1. Lifespan Context (dict, not class)

```python
@asynccontextmanager
async def lifespan(mcp: FastMCP) -> AsyncIterator[dict[str, Any]]:
    settings = PCPMCPSettings()
    async with PCPClient(
        base_url=settings.base_url,
        target_host=settings.target_host,
        auth=settings.auth,
        timeout=settings.timeout,
    ) as client:
        yield {"client": client, "settings": settings}
```

### 2. Context Helpers with Null Checks

```python
def get_client(ctx: Context) -> PCPClient:
    if ctx.request_context is None or ctx.request_context.lifespan_context is None:
        raise ToolError("Server context not available")
    return ctx.request_context.lifespan_context["client"]

def get_settings(ctx: Context) -> PCPMCPSettings:
    if ctx.request_context is None or ctx.request_context.lifespan_context is None:
        raise ToolError("Server context not available")
    return ctx.request_context.lifespan_context["settings"]
```

### 3. Tool Parameter Annotations

```python
@mcp.tool()
async def query_metrics(
    ctx: Context,
    names: Annotated[list[str], Field(description="Metric names to fetch")],
) -> list[MetricValue]:
```

### 4. Test Fixtures (conftest.py)

```python
@pytest.fixture
def mock_lifespan_context(mock_client, mock_settings) -> dict[str, Any]:
    return {"client": mock_client, "settings": mock_settings}

@pytest.fixture
def mock_context(mock_lifespan_context) -> MagicMock:
    ctx = MagicMock(spec=Context)
    ctx.request_context = MagicMock()
    ctx.request_context.lifespan_context = mock_lifespan_context
    return ctx
```

### 5. Error Handling with Match

```python
def handle_pcp_error(e: Exception, operation: str) -> ToolError:
    match e:
        case httpx.ConnectError():
            return ToolError("Cannot connect to pmproxy. Is it running?")
        case httpx.HTTPStatusError() as he if he.response.status_code == 404:
            return ToolError(f"Metric not found during {operation}")
        case _:
            return ToolError(f"Error during {operation}: {e}")
