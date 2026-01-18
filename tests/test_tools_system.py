"""Tests for system health tools."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest
from fastmcp.exceptions import ToolError

from pcp_mcp.tools.system import register_system_tools


class TestGetSystemSnapshot:
    async def test_returns_all_categories(
        self,
        mock_context: MagicMock,
        mock_client: MagicMock,
        capture_tools,
        full_system_snapshot_data,
    ) -> None:
        mock_client.fetch_with_rates.return_value = full_system_snapshot_data()

        tools = capture_tools(register_system_tools)
        result = await tools["get_system_snapshot"](mock_context)

        assert result.cpu is not None
        assert result.memory is not None
        assert result.load is not None
        assert result.disk is not None
        assert result.network is not None
        assert result.hostname == "localhost"

    async def test_returns_subset_categories(
        self,
        mock_context: MagicMock,
        mock_client: MagicMock,
        capture_tools,
        cpu_metrics_data,
    ) -> None:
        mock_client.fetch_with_rates.return_value = cpu_metrics_data()

        tools = capture_tools(register_system_tools)
        result = await tools["get_system_snapshot"](mock_context, categories=["cpu"])

        assert result.cpu is not None
        assert result.memory is None
        assert result.load is None
        assert result.disk is None
        assert result.network is None

    async def test_handles_error(
        self,
        mock_context: MagicMock,
        mock_client: MagicMock,
        capture_tools,
    ) -> None:
        mock_client.fetch_with_rates.side_effect = httpx.ConnectError("Connection refused")

        tools = capture_tools(register_system_tools)

        with pytest.raises(ToolError, match="Cannot connect to pmproxy"):
            await tools["get_system_snapshot"](mock_context)


class TestGetProcessTop:
    @pytest.fixture
    def system_info_response(self) -> dict:
        return {
            "values": [
                {"name": "hinv.ncpu", "instances": [{"value": 4}]},
                {"name": "mem.physmem", "instances": [{"value": 16000000}]},
            ]
        }

    @pytest.mark.parametrize(
        ("sort_by", "expected_field"),
        [
            ("cpu", "cpu_percent"),
            ("memory", "rss_bytes"),
            ("io", "io_read_bytes_per_sec"),
        ],
    )
    async def test_returns_top_processes_sorted(
        self,
        mock_context: MagicMock,
        mock_client: MagicMock,
        capture_tools,
        process_metrics_data,
        system_info_response: dict,
        sort_by: str,
        expected_field: str,
    ) -> None:
        mock_client.fetch_with_rates.return_value = process_metrics_data()
        mock_client.fetch.return_value = system_info_response

        tools = capture_tools(register_system_tools)
        result = await tools["get_process_top"](mock_context, sort_by=sort_by, limit=2)

        assert len(result.processes) == 2
        assert result.sort_by == sort_by
        assert result.ncpu == 4
        assert getattr(result.processes[0], expected_field) is not None

    async def test_handles_error(
        self,
        mock_context: MagicMock,
        mock_client: MagicMock,
        capture_tools,
    ) -> None:
        mock_client.fetch_with_rates.side_effect = httpx.ConnectError("Connection refused")

        tools = capture_tools(register_system_tools)

        with pytest.raises(ToolError, match="Cannot connect to pmproxy"):
            await tools["get_process_top"](mock_context)
