"""Tests for core metric tools."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastmcp.exceptions import ToolError

from pcp_mcp.tools.metrics import register_metrics_tools


class TestQueryMetrics:
    async def test_query_metrics_returns_values(
        self,
        mock_context: MagicMock,
        capture_tools,
    ) -> None:
        mock_context.request_context.lifespan_context["client"].fetch.return_value = {
            "values": [
                {
                    "name": "kernel.all.load",
                    "instances": [
                        {"instance": "1 minute", "value": 1.5},
                        {"instance": "5 minute", "value": 1.2},
                    ],
                }
            ]
        }

        tools = capture_tools(register_metrics_tools)

        result = await tools["query_metrics"](mock_context, names=["kernel.all.load"])

        assert len(result) == 2
        assert result[0].name == "kernel.all.load"
        assert result[0].value == 1.5
        assert result[0].instance == "1 minute"
        assert result[1].instance == "5 minute"

    async def test_query_metrics_handles_no_instance(
        self,
        mock_context: MagicMock,
        capture_tools,
    ) -> None:
        mock_context.request_context.lifespan_context["client"].fetch.return_value = {
            "values": [
                {
                    "name": "hinv.ncpu",
                    "instances": [{"instance": -1, "value": 8}],
                }
            ]
        }

        tools = capture_tools(register_metrics_tools)

        result = await tools["query_metrics"](mock_context, names=["hinv.ncpu"])

        assert len(result) == 1
        assert result[0].instance is None
        assert result[0].value == 8

    async def test_query_metrics_raises_on_error(
        self,
        mock_context: MagicMock,
        capture_tools,
    ) -> None:
        import httpx

        mock_context.request_context.lifespan_context[
            "client"
        ].fetch.side_effect = httpx.ConnectError("Connection refused")

        tools = capture_tools(register_metrics_tools)

        with pytest.raises(ToolError, match="Cannot connect to pmproxy"):
            await tools["query_metrics"](mock_context, names=["kernel.all.load"])


class TestSearchMetrics:
    async def test_search_metrics_returns_results(
        self,
        mock_context: MagicMock,
        capture_tools,
    ) -> None:
        mock_context.request_context.lifespan_context["client"].search.return_value = [
            {"name": "kernel.all.cpu.user", "text-oneline": "User CPU time"},
            {"name": "kernel.all.cpu.sys", "text-help": "System CPU time"},
        ]

        tools = capture_tools(register_metrics_tools)

        result = await tools["search_metrics"](mock_context, pattern="kernel.all.cpu")

        assert len(result) == 2
        assert result[0].name == "kernel.all.cpu.user"
        assert result[0].help_text == "User CPU time"
        assert result[1].help_text == "System CPU time"

    async def test_search_metrics_empty_results(
        self,
        mock_context: MagicMock,
        capture_tools,
    ) -> None:
        mock_context.request_context.lifespan_context["client"].search.return_value = []

        tools = capture_tools(register_metrics_tools)

        result = await tools["search_metrics"](mock_context, pattern="nonexistent")

        assert result == []


class TestDescribeMetric:
    async def test_describe_metric_returns_info(
        self,
        mock_context: MagicMock,
        capture_tools,
    ) -> None:
        mock_context.request_context.lifespan_context["client"].describe.return_value = {
            "name": "kernel.all.cpu.user",
            "type": "U64",
            "sem": "counter",
            "units": "millisec",
            "text-help": "Time spent in user mode",
        }

        tools = capture_tools(register_metrics_tools)

        result = await tools["describe_metric"](mock_context, name="kernel.all.cpu.user")

        assert result.name == "kernel.all.cpu.user"
        assert result.type == "U64"
        assert result.semantics == "counter"
        assert result.units == "millisec"
        assert result.help_text == "Time spent in user mode"

    async def test_describe_metric_not_found(
        self,
        mock_context: MagicMock,
        capture_tools,
    ) -> None:
        mock_context.request_context.lifespan_context["client"].describe.return_value = {}

        tools = capture_tools(register_metrics_tools)

        with pytest.raises(ToolError, match="Metric not found"):
            await tools["describe_metric"](mock_context, name="nonexistent.metric")

    async def test_describe_metric_formats_units_fallback(
        self,
        mock_context: MagicMock,
        capture_tools,
    ) -> None:
        mock_context.request_context.lifespan_context["client"].describe.return_value = {
            "name": "disk.all.read_bytes",
            "type": "U64",
            "sem": "counter",
            "units": "",
            "units-space": "Kbyte",
            "units-time": "sec",
        }

        tools = capture_tools(register_metrics_tools)

        result = await tools["describe_metric"](mock_context, name="disk.all.read_bytes")

        assert result.units == "Kbyte / sec"
