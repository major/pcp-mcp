# MCP Tools

## OVERVIEW

MCP tool implementations. Two modules: metrics (query/search/describe) and system (snapshot/top).

## STRUCTURE

```
tools/
├── __init__.py    # register_tools() → calls both modules
├── metrics.py     # query_metrics, search_metrics, describe_metric
└── system.py      # get_system_snapshot, get_process_top
```

## REGISTRATION PATTERN

```python
def register_metrics_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    async def query_metrics(
        ctx: Context,
        names: Annotated[list[str], Field(description="Metric names to fetch")],
    ) -> list[MetricValue]:
        client = get_client(ctx)
        # ...
```

## TOOL REQUIREMENTS

1. **Decorator**: `@mcp.tool()`
2. **Context**: First param is `ctx: Context`
3. **Annotations**: `Annotated[type, Field(description="...")]` for all params
4. **Return**: Pydantic model (not dict)
5. **Errors**: Wrap with `handle_pcp_error()`

## TOOLS

| Tool | Purpose | Returns |
|------|---------|---------|
| `query_metrics` | Fetch raw metric values | `list[MetricValue]` |
| `search_metrics` | Find metrics by prefix | `list[MetricSearchResult]` |
| `describe_metric` | Get metric metadata | `MetricInfo` |
| `get_system_snapshot` | System overview with rates | `SystemSnapshot` |
| `quick_health` | Fast health check (cached) | `str` (formatted summary) |
| `get_process_top` | Top N processes | `ProcessTopResult` |
| `smart_diagnose` | AI-assisted diagnosis | `str` (LLM-generated analysis) |

## ANTI-PATTERNS

- **NEVER** return raw dicts (use Pydantic models)
- **NEVER** skip `Annotated[..., Field(...)]` on params
- **NEVER** let httpx exceptions escape (wrap with `handle_pcp_error`)
- **NEVER** block async (no `time.sleep()`, use `asyncio.sleep()`)

## ADDING NEW TOOL

1. Add function in `metrics.py` or `system.py`
2. Use `@mcp.tool()` decorator
3. Add response model to `models.py` if needed
4. Register in module's `register_*_tools()` function
