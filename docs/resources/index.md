# Resources Overview

pcp-mcp provides three MCP resources for browsing PCP data without explicit tool calls.

## What Are Resources?

MCP resources are **read-only data sources** that clients can browse or subscribe to. Unlike tools (which require explicit invocation), resources provide passive access to information.

## Available Resources

| Resource URI | Description |
|--------------|-------------|
| [`pcp://health`](health.md) | Quick system health summary |
| [`pcp://metrics/common`](catalog.md#common-metrics-catalog) | Catalog of commonly used metrics |
| [`pcp://namespaces`](catalog.md#metric-namespaces) | Live-discovered metric namespaces |

## When to Use Resources vs Tools

| Use Case | Recommended |
|----------|-------------|
| Quick health check (human-readable) | `pcp://health` resource |
| Detailed system analysis | `get_system_snapshot` tool |
| Learn what metrics exist | `pcp://metrics/common` resource |
| Explore live system capabilities | `pcp://namespaces` resource |
| Discover metrics by pattern | `search_metrics` tool |
| Fetch specific metric values | `query_metrics` tool |

## Resource Characteristics

### Read-Only

Resources never modify system state. They provide a snapshot of information at the time of access.

### Text Format

All resources return markdown-formatted text suitable for display in MCP clients or consumption by LLMs.

### Live Data

The `pcp://health` and `pcp://namespaces` resources query the live PCP system. The `pcp://metrics/common` resource returns static documentation.

## Example Workflow

1. **Browse** `pcp://namespaces` to see what's available on this system
2. **Read** `pcp://metrics/common` to understand common metric groups
3. **Use** `search_metrics` tool to find specific metrics
4. **Query** with `get_system_snapshot` or `query_metrics` for actual values

## Accessing Resources

### In Claude Desktop

Resources appear in the resources panel. Click to view content.

### Programmatically

```python
# Using FastMCP client
async with client.session() as session:
    health = await session.read_resource("pcp://health")
    print(health.contents[0].text)
```
