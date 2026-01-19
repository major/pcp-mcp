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

        assert len(result.metrics) == 2
        assert result.metrics[0].name == "kernel.all.load"
        assert result.metrics[0].value == 1.5
        assert result.metrics[0].instance == "1 minute"
        assert result.metrics[1].instance == "5 minute"

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

        assert len(result.metrics) == 1
        assert result.metrics[0].instance is None
        assert result.metrics[0].value == 8

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

        assert len(result.results) == 2
        assert result.results[0].name == "kernel.all.cpu.user"
        assert result.results[0].help_text == "User CPU time"
        assert result.results[1].help_text == "System CPU time"

    async def test_search_metrics_empty_results(
        self,
        mock_context: MagicMock,
        capture_tools,
    ) -> None:
        mock_context.request_context.lifespan_context["client"].search.return_value = []

        tools = capture_tools(register_metrics_tools)

        result = await tools["search_metrics"](mock_context, pattern="nonexistent")

        assert result.results == []

    async def test_search_metrics_raises_on_error(
        self,
        mock_context: MagicMock,
        capture_tools,
    ) -> None:
        import httpx

        mock_context.request_context.lifespan_context[
            "client"
        ].search.side_effect = httpx.ConnectError("Connection refused")

        tools = capture_tools(register_metrics_tools)

        with pytest.raises(ToolError, match="Cannot connect to pmproxy"):
            await tools["search_metrics"](mock_context, pattern="kernel")


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

    @pytest.mark.parametrize(
        ("metric_info", "expected_units"),
        [
            ({"units": "millisec"}, "millisec"),
            ({"units": "", "units-space": "Kbyte", "units-time": "sec"}, "Kbyte / sec"),
            ({"units": "", "units-count": "count"}, "count"),
            ({"units": ""}, "none"),
            ({}, "none"),
        ],
    )
    async def test_describe_metric_formats_units(
        self,
        mock_context: MagicMock,
        capture_tools,
        metric_info: dict,
        expected_units: str,
    ) -> None:
        mock_context.request_context.lifespan_context["client"].describe.return_value = {
            "name": "test.metric",
            "type": "U64",
            "sem": "counter",
            **metric_info,
        }

        tools = capture_tools(register_metrics_tools)

        result = await tools["describe_metric"](mock_context, name="test.metric")

        assert result.units == expected_units

    async def test_describe_metric_raises_on_error(
        self,
        mock_context: MagicMock,
        capture_tools,
    ) -> None:
        import httpx

        mock_context.request_context.lifespan_context[
            "client"
        ].describe.side_effect = httpx.ConnectError("Connection refused")

        tools = capture_tools(register_metrics_tools)

        with pytest.raises(ToolError, match="Cannot connect to pmproxy"):
            await tools["describe_metric"](mock_context, name="kernel.all.load")
