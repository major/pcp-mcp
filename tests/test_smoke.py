"""Smoke tests for server startup and tool registration.

These tests verify that the server can start and tools can be invoked,
catching registration-time failures like missing imports or type errors.
"""

import pytest
from fastmcp import Client

from pcp_mcp.server import create_server


class TestServerSmoke:
    """Smoke tests for server initialization and tool discovery."""

    async def test_server_creates_successfully(self):
        """Server creation should not raise any exceptions."""
        server = create_server()
        assert server is not None
        assert server.name == "pcp"

    async def test_tools_are_registered(self):
        """All expected tools should be discoverable via MCP client."""
        server = create_server()

        async with Client(server) as client:
            tools = await client.list_tools()

        tool_names = {tool.name for tool in tools}

        # Core tools that must always be present
        expected_tools = {
            "query_metrics",
            "search_metrics",
            "describe_metric",
            "get_system_snapshot",
            "get_process_top",
            "quick_health",
            "smart_diagnose",
        }

        missing = expected_tools - tool_names
        assert not missing, f"Missing tools: {missing}"

    async def test_resources_are_registered(self):
        """All expected resources should be discoverable via MCP client."""
        server = create_server()

        async with Client(server) as client:
            resources = await client.list_resources()

        resource_uris = {str(r.uri) for r in resources}

        # Core resources that must always be present
        expected_resources = {
            "pcp://health",
            "pcp://metrics/common",
            "pcp://namespaces",
        }

        missing = expected_resources - resource_uris
        assert not missing, f"Missing resources: {missing}"

    async def test_prompts_are_registered(self):
        """All expected prompts should be discoverable via MCP client."""
        server = create_server()

        async with Client(server) as client:
            prompts = await client.list_prompts()

        prompt_names = {p.name for p in prompts}

        # Core prompts that must always be present
        expected_prompts = {
            "diagnose_slow_system",
            "investigate_memory_usage",
            "find_io_bottleneck",
            "analyze_cpu_usage",
            "check_network_performance",
        }

        missing = expected_prompts - prompt_names
        assert not missing, f"Missing prompts: {missing}"

    @pytest.mark.parametrize(
        "tool_name",
        [
            "query_metrics",
            "search_metrics",
            "describe_metric",
            "get_system_snapshot",
            "get_process_top",
            "quick_health",
            "smart_diagnose",
        ],
    )
    async def test_tool_has_valid_schema(self, tool_name: str):
        """Each tool should have a valid input schema."""
        server = create_server()

        async with Client(server) as client:
            tools = await client.list_tools()

        tool = next((t for t in tools if t.name == tool_name), None)
        assert tool is not None, f"Tool {tool_name} not found"
        assert tool.inputSchema is not None, f"Tool {tool_name} has no input schema"
        assert tool.inputSchema.get("type") == "object", f"Tool {tool_name} schema is not object"
