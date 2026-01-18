# Getting Started

## Installation

### Install pcp-mcp

Install from PyPI:

```bash
pip install pcp-mcp
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add pcp-mcp
```

### Install Performance Co-Pilot

**Fedora/RHEL/CentOS:**

```bash
sudo dnf install pcp
sudo systemctl enable --now pmproxy
```

**Ubuntu/Debian:**

```bash
sudo apt install pcp
sudo systemctl enable --now pmproxy
```

**Verify PCP is running:**

```bash
# Check pmcd (metrics collector)
systemctl status pmcd

# Check pmproxy (REST API server)
systemctl status pmproxy

# Test REST API
curl http://localhost:44322/pmapi/context
```

## Configuration

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

### Example Configurations

**Default (monitor localhost):**

```bash
pcp-mcp
```

**Monitor a remote host:**

```bash
PCP_TARGET_HOST=webserver1.example.com pcp-mcp
```

Or use the CLI flag:

```bash
pcp-mcp --target-host webserver1.example.com
```

**Connect to remote pmproxy:**

```bash
PCP_HOST=metrics.example.com pcp-mcp
```

## MCP Client Setup

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

Restart Claude Desktop to load the server.

### Other MCP Clients

pcp-mcp supports both stdio (default) and SSE transports:

```bash
# stdio (default)
pcp-mcp

# SSE transport
pcp-mcp --transport sse
```

## Verify Setup

Once configured, ask your LLM:

```
"What's the current system load?"
```

If everything is working, you'll get CPU, memory, disk, and network metrics from PCP.
