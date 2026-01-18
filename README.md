# pcp-mcp

MCP server for [Performance Co-Pilot (PCP)](https://pcp.io/) metrics.

Query system performance metrics via the Model Context Protocol - CPU, memory, disk I/O, network, processes, and more.

[![CI](https://github.com/major/pcp-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/major/pcp-mcp/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/major/pcp-mcp/branch/main/graph/badge.svg)](https://codecov.io/gh/major/pcp-mcp)
[![PyPI version](https://badge.fury.io/py/pcp-mcp.svg)](https://pypi.org/project/pcp-mcp/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚀 Installation

```bash
pip install pcp-mcp
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add pcp-mcp
```

## 📋 Requirements

- **Python**: 3.10+
- **PCP**: Performance Co-Pilot with `pmcd` and `pmproxy` running
  ```bash
  # Fedora/RHEL/CentOS
  sudo dnf install pcp
  sudo systemctl enable --now pmcd pmproxy
  
  # Ubuntu/Debian
  sudo apt install pcp
  sudo systemctl enable --now pmcd pmproxy
  ```

## ⚙️ Configuration

Configure via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `PCP_HOST` | pmproxy host | `localhost` |
| `PCP_PORT` | pmproxy port | `44322` |
| `PCP_TARGET_HOST` | Target pmcd host to monitor | `localhost` |
| `PCP_USE_TLS` | Use HTTPS for pmproxy | `false` |
| `PCP_TIMEOUT` | Request timeout (seconds) | `30` |
| `PCP_USERNAME` | HTTP basic auth user | (optional) |
| `PCP_PASSWORD` | HTTP basic auth password | (optional) |

## 🎯 Usage

### Monitor localhost (default)

```bash
pcp-mcp
```

### Monitor a remote host

```bash
PCP_TARGET_HOST=webserver1.example.com pcp-mcp
```

Or use the CLI flag:

```bash
pcp-mcp --target-host webserver1.example.com
```

### Connect to remote pmproxy

```bash
PCP_HOST=metrics.example.com pcp-mcp
```

### Use SSE transport

```bash
pcp-mcp --transport sse
```

## 🔌 MCP Client Configuration

### Claude Desktop

Add to `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "pcp": {
      "command": "pcp-mcp"
    }
  }
}
```

For remote monitoring:

```json
{
  "mcpServers": {
    "pcp": {
      "command": "pcp-mcp",
      "args": ["--target-host", "webserver1.example.com"]
    }
  }
}
```

## 🛠️ Available Tools

### System Monitoring

- **`get_system_snapshot`** - Point-in-time system overview (CPU, memory, disk, network, load)
- **`get_process_top`** - Top processes by CPU, memory, or I/O usage
- **`query_metrics`** - Fetch current values for specific PCP metrics
- **`search_metrics`** - Discover available metrics by name pattern
- **`describe_metric`** - Get detailed metadata about a metric

### Example Queries

```
"What's the current CPU usage?"
→ Uses get_system_snapshot

"Show me the top 10 processes by memory usage"
→ Uses get_process_top(sort_by="memory", limit=10)

"What metrics are available for network traffic?"
→ Uses search_metrics(pattern="network")

"Get detailed info about kernel.all.load"
→ Uses describe_metric(name="kernel.all.load")
```

## 📚 Resources

Browse metrics via MCP resources:

- `pcp://metrics` - List all available metrics (grouped by prefix)
- `pcp://system/snapshot` - Latest system snapshot
- `pcp://processes/top` - Top processes

## 💡 Use Cases

### Performance Troubleshooting

Ask Claude to:
- "Analyze current system performance and identify bottlenecks"
- "Why is my disk I/O so high?"
- "Which processes are consuming the most CPU?"

### System Monitoring

- "Give me a health check of the production server"
- "Compare CPU usage over the last minute"
- "Monitor network traffic on eth0"

### Capacity Planning

- "What's the memory utilization trend?"
- "Show me disk usage across all filesystems"
- "Analyze process resource consumption patterns"

## 🏗️ Architecture

```
┌─────────┐         ┌─────────┐          ┌─────────┐         ┌─────────┐
│   LLM   │ ◄─MCP─► │ pcp-mcp │ ◄─HTTP─► │ pmproxy │ ◄─────► │  pmcd   │
└─────────┘         └─────────┘          └─────────┘         └─────────┘
                                         (REST API)          (metrics)
```

- **pcp-mcp**: FastMCP server exposing PCP metrics via MCP tools
- **pmproxy**: PCP's REST API server (runs on port 44322 by default)
- **pmcd**: PCP metrics collector daemon
- **Remote monitoring**: Set `PCP_TARGET_HOST` to query a different pmcd instance via pmproxy

## 🔧 Development

```bash
# Install dependencies
uv sync --dev

# Run all checks
make check

# Individual commands
make lint       # ruff check
make format     # ruff format
make typecheck  # ty check
make test       # pytest with coverage
```

## 📖 Documentation

Full documentation at [https://major.github.io/pcp-mcp](https://major.github.io/pcp-mcp)

## 📄 License

MIT
