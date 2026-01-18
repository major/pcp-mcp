"""Tests for system health tools."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastmcp.exceptions import ToolError

from pcp_mcp.tools.system import (
    COUNTER_METRICS,
    SNAPSHOT_METRICS,
    register_system_tools,
)
from pcp_mcp.utils.builders import (
    build_cpu_metrics,
    build_disk_metrics,
    build_load_metrics,
    build_memory_metrics,
    build_network_metrics,
)


class TestGetSystemSnapshot:
    async def test_returns_all_categories(
        self,
        mock_context: MagicMock,
        capture_tools,
    ) -> None:
        mock_context.request_context.lifespan_context["client"].fetch_with_rates.return_value = {
            "kernel.all.cpu.user": {"instances": {-1: 50.0}, "is_rate": True},
            "kernel.all.cpu.sys": {"instances": {-1: 20.0}, "is_rate": True},
            "kernel.all.cpu.idle": {"instances": {-1: 25.0}, "is_rate": True},
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
            "disk.all.read_bytes": {"instances": {-1: 1000000.0}, "is_rate": True},
            "disk.all.write_bytes": {"instances": {-1: 500000.0}, "is_rate": True},
            "disk.all.read": {"instances": {-1: 100.0}, "is_rate": True},
            "disk.all.write": {"instances": {-1: 50.0}, "is_rate": True},
            "network.interface.in.bytes": {
                "instances": {"eth0": 100000.0, "lo": 1000.0},
                "is_rate": True,
            },
            "network.interface.out.bytes": {
                "instances": {"eth0": 50000.0, "lo": 1000.0},
                "is_rate": True,
            },
            "network.interface.in.packets": {
                "instances": {"eth0": 1000.0, "lo": 10.0},
                "is_rate": True,
            },
            "network.interface.out.packets": {
                "instances": {"eth0": 500.0, "lo": 10.0},
                "is_rate": True,
            },
        }

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
        capture_tools,
    ) -> None:
        mock_context.request_context.lifespan_context["client"].fetch_with_rates.return_value = {
            "kernel.all.cpu.user": {"instances": {-1: 50.0}, "is_rate": True},
            "kernel.all.cpu.sys": {"instances": {-1: 20.0}, "is_rate": True},
            "kernel.all.cpu.idle": {"instances": {-1: 25.0}, "is_rate": True},
            "kernel.all.cpu.wait.total": {"instances": {-1: 5.0}, "is_rate": True},
            "hinv.ncpu": {"instances": {-1: 4}, "is_rate": False},
        }

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
        capture_tools,
    ) -> None:
        import httpx

        mock_context.request_context.lifespan_context[
            "client"
        ].fetch_with_rates.side_effect = httpx.ConnectError("Connection refused")

        tools = capture_tools(register_system_tools)

        with pytest.raises(ToolError, match="Cannot connect to pmproxy"):
            await tools["get_system_snapshot"](mock_context)


class TestGetProcessTop:
    async def test_returns_top_processes(
        self,
        mock_context: MagicMock,
        capture_tools,
    ) -> None:
        mock_context.request_context.lifespan_context["client"].fetch_with_rates.return_value = {
            "proc.psinfo.pid": {"instances": {1: 1234, 2: 5678}, "is_rate": False},
            "proc.psinfo.cmd": {"instances": {1: "python", 2: "nginx"}, "is_rate": False},
            "proc.psinfo.psargs": {
                "instances": {1: "python app.py", 2: "nginx -g daemon"},
                "is_rate": False,
            },
            "proc.memory.rss": {"instances": {1: 1000000, 2: 500000}, "is_rate": False},
            "proc.psinfo.utime": {"instances": {1: 500.0, 2: 100.0}, "is_rate": True},
            "proc.psinfo.stime": {"instances": {1: 100.0, 2: 50.0}, "is_rate": True},
        }
        mock_context.request_context.lifespan_context["client"].fetch.return_value = {
            "values": [
                {"name": "hinv.ncpu", "instances": [{"value": 4}]},
                {"name": "mem.physmem", "instances": [{"value": 16000000}]},
            ]
        }

        tools = capture_tools(register_system_tools)

        result = await tools["get_process_top"](mock_context, sort_by="cpu", limit=2)

        assert len(result.processes) == 2
        assert result.processes[0].command == "python"
        assert result.processes[0].cpu_percent is not None
        assert result.ncpu == 4
        assert result.sort_by == "cpu"


class TestBuildCPUMetrics:
    def test_normal_cpu(self) -> None:
        data = {
            "kernel.all.cpu.user": {"instances": {-1: 20.0}},
            "kernel.all.cpu.sys": {"instances": {-1: 10.0}},
            "kernel.all.cpu.idle": {"instances": {-1: 65.0}},
            "kernel.all.cpu.wait.total": {"instances": {-1: 5.0}},
            "hinv.ncpu": {"instances": {-1: 4}},
        }
        result = build_cpu_metrics(data)

        assert result.user_percent == 20.0
        assert result.system_percent == 10.0
        assert result.idle_percent == 65.0
        assert result.iowait_percent == 5.0
        assert result.ncpu == 4
        assert "normal" in result.assessment.lower()

    def test_high_iowait(self) -> None:
        data = {
            "kernel.all.cpu.user": {"instances": {-1: 10.0}},
            "kernel.all.cpu.sys": {"instances": {-1: 5.0}},
            "kernel.all.cpu.idle": {"instances": {-1: 55.0}},
            "kernel.all.cpu.wait.total": {"instances": {-1: 30.0}},
            "hinv.ncpu": {"instances": {-1: 4}},
        }
        result = build_cpu_metrics(data)

        assert "I/O wait" in result.assessment


class TestBuildMemoryMetrics:
    def test_normal_memory(self) -> None:
        data = {
            "mem.physmem": {"instances": {-1: 16000000}},
            "mem.util.used": {"instances": {-1: 8000000}},
            "mem.util.free": {"instances": {-1: 4000000}},
            "mem.util.available": {"instances": {-1: 6000000}},
            "mem.util.cached": {"instances": {-1: 2000000}},
            "mem.util.bufmem": {"instances": {-1: 1000000}},
            "mem.util.swapTotal": {"instances": {-1: 8000000}},
            "mem.util.swapFree": {"instances": {-1: 7000000}},
        }
        result = build_memory_metrics(data)

        assert result.used_percent == 50.0
        assert "normal" in result.assessment.lower()


class TestBuildLoadMetrics:
    def test_normal_load(self) -> None:
        data = {
            "kernel.all.load": {"instances": {1: 1.5, 5: 1.2, 15: 1.0}},
            "kernel.all.runnable": {"instances": {-1: 3}},
            "kernel.all.nprocs": {"instances": {-1: 200}},
            "hinv.ncpu": {"instances": {-1: 4}},
        }
        result = build_load_metrics(data)

        assert result.load_1m == 1.5
        assert result.load_5m == 1.2
        assert result.load_15m == 1.0
        assert "normal" in result.assessment.lower()

    def test_high_load(self) -> None:
        data = {
            "kernel.all.load": {"instances": {1: 10.0, 5: 8.0, 15: 6.0}},
            "kernel.all.runnable": {"instances": {-1: 15}},
            "kernel.all.nprocs": {"instances": {-1: 200}},
            "hinv.ncpu": {"instances": {-1: 4}},
        }
        result = build_load_metrics(data)

        assert "high" in result.assessment.lower() or "elevated" in result.assessment.lower()


class TestBuildDiskMetrics:
    def test_low_disk_io(self) -> None:
        data = {
            "disk.all.read_bytes": {"instances": {-1: 1000000.0}},
            "disk.all.write_bytes": {"instances": {-1: 500000.0}},
            "disk.all.read": {"instances": {-1: 100.0}},
            "disk.all.write": {"instances": {-1: 50.0}},
        }
        result = build_disk_metrics(data)

        assert result.read_bytes_per_sec == 1000000.0
        assert "low" in result.assessment.lower()


class TestBuildNetworkMetrics:
    def test_aggregates_interfaces(self) -> None:
        data = {
            "network.interface.in.bytes": {"instances": {"eth0": 100000.0, "lo": 1000.0}},
            "network.interface.out.bytes": {"instances": {"eth0": 50000.0, "lo": 1000.0}},
            "network.interface.in.packets": {"instances": {"eth0": 1000.0, "lo": 10.0}},
            "network.interface.out.packets": {"instances": {"eth0": 500.0, "lo": 10.0}},
        }
        result = build_network_metrics(data)

        assert result.in_bytes_per_sec == 101000.0
        assert result.out_bytes_per_sec == 51000.0
