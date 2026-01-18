"""Tests for MCP resources."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pcp_mcp.resources.health import register_health_resources
from pcp_mcp.resources.metrics import register_metrics_resources

if TYPE_CHECKING:
    from unittest.mock import MagicMock


class TestHealthResource:
    async def test_returns_health_summary(
        self,
        mock_context: MagicMock,
        capture_resources,
    ) -> None:
        mock_context.request_context.lifespan_context["client"].fetch_with_rates.return_value = {
            "kernel.all.cpu.user": {"instances": {-1: 20.0}, "is_rate": True},
            "kernel.all.cpu.sys": {"instances": {-1: 10.0}, "is_rate": True},
            "kernel.all.cpu.idle": {"instances": {-1: 65.0}, "is_rate": True},
            "kernel.all.cpu.wait.total": {"instances": {-1: 5.0}, "is_rate": True},
            "hinv.ncpu": {"instances": {-1: 4}, "is_rate": False},
            "mem.physmem": {"instances": {-1: 16000000}, "is_rate": False},
            "mem.util.used": {"instances": {-1: 8000000}, "is_rate": False},
            "mem.util.free": {"instances": {-1: 4000000}, "is_rate": False},
            "mem.util.available": {"instances": {-1: 6000000}, "is_rate": False},
            "mem.util.cached": {"instances": {-1: 2000000}, "is_rate": False},
            "mem.util.bufmem": {"instances": {-1: 1000000}, "is_rate": False},
            "mem.util.swapTotal": {"instances": {-1: 8000000}, "is_rate": False},
            "mem.util.swapFree": {"instances": {-1: 7000000}, "is_rate": False},
            "kernel.all.load": {
                "instances": {"1 minute": 1.5, "5 minute": 1.2, "15 minute": 1.0},
                "is_rate": False,
            },
            "kernel.all.runnable": {"instances": {-1: 3}, "is_rate": False},
            "kernel.all.nprocs": {"instances": {-1: 200}, "is_rate": False},
        }

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
        capture_resources,
    ) -> None:
        mock_context.request_context.lifespan_context[
            "client"
        ].fetch_with_rates.side_effect = Exception("Connection failed")

        resources = capture_resources(register_health_resources)

        result = await resources["pcp://health"](mock_context)

        assert "Error" in result
        assert "Connection failed" in result


class TestMetricsResource:
    async def test_browse_metrics(
        self,
        mock_context: MagicMock,
        capture_resources,
    ) -> None:
        mock_context.request_context.lifespan_context["client"].search.return_value = [
            {"name": "kernel.all.cpu.user", "text-oneline": "User CPU time"},
            {"name": "kernel.all.cpu.sys", "text-oneline": "System CPU time"},
        ]

        resources = capture_resources(register_metrics_resources)

        result = await resources["pcp://metrics/{pattern}"](mock_context, pattern="kernel.all.cpu")

        assert "kernel.all.cpu.user" in result
        assert "kernel.all.cpu.sys" in result
        assert "User CPU time" in result

    async def test_browse_metrics_empty(
        self,
        mock_context: MagicMock,
        capture_resources,
    ) -> None:
        mock_context.request_context.lifespan_context["client"].search.return_value = []

        resources = capture_resources(register_metrics_resources)

        result = await resources["pcp://metrics/{pattern}"](mock_context, pattern="nonexistent")

        assert "No metrics found" in result

    async def test_metric_detail(
        self,
        mock_context: MagicMock,
        capture_resources,
    ) -> None:
        mock_context.request_context.lifespan_context["client"].describe.return_value = {
            "name": "kernel.all.cpu.user",
            "type": "U64",
            "sem": "counter",
            "units": "millisec",
            "text-help": "Time spent in user mode",
        }

        resources = capture_resources(register_metrics_resources)

        result = await resources["pcp://metric/{name}"](mock_context, name="kernel.all.cpu.user")

        assert "kernel.all.cpu.user" in result
        assert "U64" in result
        assert "counter" in result
        assert "millisec" in result
        assert "Time spent in user mode" in result

    async def test_metric_detail_not_found(
        self,
        mock_context: MagicMock,
        capture_resources,
    ) -> None:
        mock_context.request_context.lifespan_context["client"].describe.return_value = {}

        resources = capture_resources(register_metrics_resources)

        result = await resources["pcp://metric/{name}"](mock_context, name="nonexistent")

        assert "not found" in result.lower()
