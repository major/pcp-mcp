"""Tests for multi-host functionality."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from pcp_mcp.context import ClientManager
from pcp_mcp.tools.metrics import register_metrics_tools
from pcp_mcp.tools.system import register_system_tools


class TestMultiHost:
    """Tests for multi-host support."""

    @pytest.fixture
    def second_mock_client(self) -> AsyncMock:
        """Create a second mock PCPClient for remote host."""
        from pcp_mcp.client import PCPClient

        client = AsyncMock(spec=PCPClient)
        client.target_host = "remote.example.com"
        client.context_id = 67890
        return client

    @pytest.fixture
    def multi_host_client_manager(
        self,
        mock_client: AsyncMock,
        second_mock_client: AsyncMock,
    ) -> AsyncMock:
        """Create a mock ClientManager that returns different clients per host."""
        manager = AsyncMock(spec=ClientManager)

        async def get_client_side_effect(target_host: str | None = None):
            if target_host == "remote.example.com":
                return second_mock_client
            return mock_client

        manager.get_client = AsyncMock(side_effect=get_client_side_effect)
        return manager

    @pytest.fixture
    def multi_host_context(
        self,
        multi_host_client_manager: AsyncMock,
        mock_settings,
    ) -> MagicMock:
        """Create a mock context with multi-host client manager."""
        from fastmcp import Context

        ctx = MagicMock(spec=Context)
        ctx.request_context = MagicMock()
        ctx.request_context.lifespan_context = {
            "client_manager": multi_host_client_manager,
            "settings": mock_settings,
        }
        return ctx

    async def test_query_metrics_default_host(
        self,
        multi_host_context: MagicMock,
        mock_client: AsyncMock,
        capture_tools,
    ) -> None:
        """Test query_metrics without host parameter uses default host."""
        mock_client.fetch.return_value = {
            "values": [
                {
                    "name": "kernel.all.load",
                    "instances": [{"instance": -1, "value": 1.5}],
                }
            ]
        }

        tools = capture_tools(register_metrics_tools)
        result = await tools["query_metrics"](multi_host_context, names=["kernel.all.load"])

        assert len(result) == 1
        assert result[0].value == 1.5
        # Verify get_client was called without target_host (None)
        multi_host_context.request_context.lifespan_context[
            "client_manager"
        ].get_client.assert_called_once_with(None)

    async def test_query_metrics_remote_host(
        self,
        multi_host_context: MagicMock,
        second_mock_client: AsyncMock,
        capture_tools,
    ) -> None:
        """Test query_metrics with host parameter queries remote host."""
        second_mock_client.fetch.return_value = {
            "values": [
                {
                    "name": "kernel.all.load",
                    "instances": [{"instance": -1, "value": 2.5}],
                }
            ]
        }

        tools = capture_tools(register_metrics_tools)
        result = await tools["query_metrics"](
            multi_host_context,
            names=["kernel.all.load"],
            host="remote.example.com",
        )

        assert len(result) == 1
        assert result[0].value == 2.5
        # Verify get_client was called with remote host
        multi_host_context.request_context.lifespan_context[
            "client_manager"
        ].get_client.assert_called_with("remote.example.com")

    async def test_get_system_snapshot_default_host(
        self,
        multi_host_context: MagicMock,
        mock_client: AsyncMock,
        capture_tools,
        cpu_metrics_data,
    ) -> None:
        """Test get_system_snapshot without host parameter uses default host."""
        mock_client.fetch_with_rates.return_value = cpu_metrics_data()

        tools = capture_tools(register_system_tools)
        result = await tools["get_system_snapshot"](
            multi_host_context,
            categories=["cpu"],
        )

        assert result.hostname == "localhost"
        assert result.cpu is not None
        # Verify get_client was called without target_host (None)
        multi_host_context.request_context.lifespan_context[
            "client_manager"
        ].get_client.assert_called_once_with(None)

    async def test_get_system_snapshot_remote_host(
        self,
        multi_host_context: MagicMock,
        second_mock_client: AsyncMock,
        capture_tools,
        cpu_metrics_data,
    ) -> None:
        """Test get_system_snapshot with host parameter queries remote host."""
        # Provide full CPU data: user=40, sys=20, idle=30, iowait=10
        # Percentages: 40%, 20%, 30%, 10%
        second_mock_client.fetch_with_rates.return_value = cpu_metrics_data(
            user=40.0,
            sys=20.0,
            idle=30.0,
            iowait=10.0,
        )

        tools = capture_tools(register_system_tools)
        result = await tools["get_system_snapshot"](
            multi_host_context,
            categories=["cpu"],
            host="remote.example.com",
        )

        assert result.hostname == "remote.example.com"
        assert result.cpu is not None
        assert result.cpu.user_percent == 40.0
        assert result.cpu.system_percent == 20.0
        # Verify get_client was called with remote host
        multi_host_context.request_context.lifespan_context[
            "client_manager"
        ].get_client.assert_called_with("remote.example.com")

    async def test_search_metrics_remote_host(
        self,
        multi_host_context: MagicMock,
        second_mock_client: AsyncMock,
        capture_tools,
    ) -> None:
        """Test search_metrics with host parameter queries remote host."""
        second_mock_client.search.return_value = [
            {"name": "kernel.all.cpu.user", "text-oneline": "User CPU time"},
        ]

        tools = capture_tools(register_metrics_tools)
        result = await tools["search_metrics"](
            multi_host_context,
            pattern="kernel.all",
            host="remote.example.com",
        )

        assert len(result) == 1
        assert result[0].name == "kernel.all.cpu.user"
        # Verify get_client was called with remote host
        multi_host_context.request_context.lifespan_context[
            "client_manager"
        ].get_client.assert_called_with("remote.example.com")

    async def test_describe_metric_remote_host(
        self,
        multi_host_context: MagicMock,
        second_mock_client: AsyncMock,
        capture_tools,
    ) -> None:
        """Test describe_metric with host parameter queries remote host."""
        second_mock_client.describe.return_value = {
            "name": "kernel.all.cpu.user",
            "type": "U64",
            "sem": "counter",
            "units": "millisec",
        }

        tools = capture_tools(register_metrics_tools)
        result = await tools["describe_metric"](
            multi_host_context,
            name="kernel.all.cpu.user",
            host="remote.example.com",
        )

        assert result.name == "kernel.all.cpu.user"
        # Verify get_client was called with remote host
        multi_host_context.request_context.lifespan_context[
            "client_manager"
        ].get_client.assert_called_with("remote.example.com")

    async def test_get_process_top_remote_host(
        self,
        multi_host_context: MagicMock,
        second_mock_client: AsyncMock,
        capture_tools,
        process_metrics_data,
    ) -> None:
        """Test get_process_top with host parameter queries remote host."""
        second_mock_client.fetch_with_rates.return_value = process_metrics_data()
        second_mock_client.fetch.return_value = {
            "values": [
                {"name": "hinv.ncpu", "instances": [{"value": 8}]},
                {"name": "mem.physmem", "instances": [{"value": 32000000}]},
            ]
        }

        tools = capture_tools(register_system_tools)
        result = await tools["get_process_top"](
            multi_host_context,
            host="remote.example.com",
        )

        assert result.hostname == "remote.example.com"
        assert result.ncpu == 8
        # Verify get_client was called with remote host
        multi_host_context.request_context.lifespan_context[
            "client_manager"
        ].get_client.assert_called_with("remote.example.com")
