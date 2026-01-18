"""Tests for MCP resources."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest
from fastmcp.exceptions import ToolError

from pcp_mcp.resources.catalog import register_catalog_resources
from pcp_mcp.resources.health import register_health_resources

if TYPE_CHECKING:
    from unittest.mock import MagicMock


class TestHealthResource:
    async def test_returns_health_summary(
        self,
        mock_context: MagicMock,
        mock_client: MagicMock,
        capture_resources,
        full_system_snapshot_data,
    ) -> None:
        mock_client.fetch_with_rates.return_value = full_system_snapshot_data()

        resources = capture_resources(register_health_resources)
        result = await resources["pcp://health"](mock_context)

        assert "System Health Summary" in result
        assert "CPU" in result
        assert "Memory" in result
        assert "Load" in result
        assert "localhost" in result

    async def test_handles_error(
        self,
        mock_context: MagicMock,
        mock_client: MagicMock,
        capture_resources,
    ) -> None:
        mock_client.fetch_with_rates.side_effect = Exception("Connection failed")

        resources = capture_resources(register_health_resources)
        result = await resources["pcp://health"](mock_context)

        assert "Error" in result
        assert "Connection failed" in result


class TestCommonMetricsCatalog:
    @pytest.mark.parametrize(
        "expected_content",
        [
            "Common PCP Metric Groups",
            "kernel.all.cpu.user",
            "mem.physmem",
            "disk.all.read_bytes",
            "Legend",
        ],
    )
    def test_contains_expected_sections(self, capture_resources, expected_content: str) -> None:
        resources = capture_resources(register_catalog_resources)
        result = resources["pcp://metrics/common"]()
        assert expected_content in result


class TestMetricNamespaces:
    async def test_returns_live_discovery(
        self,
        mock_context: MagicMock,
        mock_client: MagicMock,
        capture_resources,
        namespace_search_response,
        pmda_status_response,
    ) -> None:
        mock_client.search.return_value = namespace_search_response()
        mock_client.fetch.return_value = pmda_status_response()

        resources = capture_resources(register_catalog_resources)
        result = await resources["pcp://namespaces"](mock_context)

        assert "PCP Metric Namespaces (Live Discovery)" in result
        assert "kernel" in result
        assert "mem" in result
        assert "disk" in result
        assert "Active PMDAs" in result

    async def test_handles_connection_error(
        self,
        mock_context: MagicMock,
        mock_client: MagicMock,
        capture_resources,
    ) -> None:
        mock_client.search.side_effect = httpx.ConnectError("Connection refused")

        resources = capture_resources(register_catalog_resources)

        with pytest.raises(ToolError, match="Cannot connect to pmproxy"):
            await resources["pcp://namespaces"](mock_context)

    @pytest.mark.parametrize(
        ("pmdas", "expected_count"),
        [
            ([("linux", 0), ("pmcd", 0)], 2),
            ([("linux", 0), ("broken", 1)], 1),
            ([("linux", 0), (-1, 0)], 1),
            ([], 0),
        ],
    )
    async def test_filters_pmdas_by_status(
        self,
        mock_context: MagicMock,
        mock_client: MagicMock,
        capture_resources,
        namespace_search_response,
        pmda_status_response,
        pmdas: list[tuple],
        expected_count: int,
    ) -> None:
        mock_client.search.return_value = namespace_search_response(["kernel.all.load"])
        mock_client.fetch.return_value = pmda_status_response(pmdas)

        resources = capture_resources(register_catalog_resources)
        result = await resources["pcp://namespaces"](mock_context)

        assert "Active PMDAs:" in result
        if expected_count == 0:
            assert "Unable to enumerate PMDAs" in result
