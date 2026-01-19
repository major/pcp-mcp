"""Smoke tests for server startup and tool registration.

These tests verify that the server can start and tools register correctly,
catching registration-time failures like missing imports or type errors.
Does NOT require pmproxy - accesses server internals directly.
"""

import pytest

from pcp_mcp.server import create_server


class TestServerSmoke:
    """Smoke tests for server initialization and tool discovery."""

    def test_server_creates_successfully(self):
        """Server creation should not raise any exceptions."""
        server = create_server()
        assert server is not None
        assert server.name == "pcp"

    def test_tools_are_registered(self):
        """All expected tools should be registered."""
        server = create_server()
        tool_names = {t.name for t in server._tool_manager._tools.values()}

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

    def test_resources_are_registered(self):
        """All expected resources should be registered."""
        server = create_server()
        resource_uris = set(server._resource_manager._resources.keys())

        expected_resources = {
            "pcp://health",
            "pcp://metrics/common",
            "pcp://namespaces",
        }

        missing = expected_resources - resource_uris
        assert not missing, f"Missing resources: {missing}"

    def test_prompts_are_registered(self):
        """All expected prompts should be registered."""
        server = create_server()
        prompt_names = set(server._prompt_manager._prompts.keys())

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
    def test_tool_has_valid_schema(self, tool_name: str):
        """Each tool should have a valid input schema."""
        server = create_server()
        tools = {t.name: t for t in server._tool_manager._tools.values()}

        tool = tools.get(tool_name)
        assert tool is not None, f"Tool {tool_name} not found"
        assert tool.parameters is not None, f"Tool {tool_name} has no parameters schema"
