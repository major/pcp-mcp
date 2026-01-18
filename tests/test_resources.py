"""Tests for MCP resources."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pcp_mcp.resources.health import register_health_resources

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
