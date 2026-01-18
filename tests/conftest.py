"""Pytest fixtures for pcp-mcp tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeAlias
from unittest.mock import AsyncMock, MagicMock

import pytest

from pcp_mcp.client import PCPClient
from pcp_mcp.config import PCPMCPSettings

RegisterFn: TypeAlias = Callable[[MagicMock], None]
ToolDict: TypeAlias = dict[str, Callable[..., Any]]
ResourceDict: TypeAlias = dict[str, Callable[..., Any]]


# =============================================================================
# Metric Data Factories - Use these to build test data without duplication
# =============================================================================


@pytest.fixture
def cpu_metrics_data() -> Callable[..., dict]:
    """Factory for CPU metrics data with configurable values."""

    def _make(
        user: float = 20.0,
        sys: float = 10.0,
        idle: float = 65.0,
        iowait: float = 5.0,
        ncpu: int = 4,
    ) -> dict:
        return {
            "kernel.all.cpu.user": {"instances": {-1: user}},
            "kernel.all.cpu.sys": {"instances": {-1: sys}},
            "kernel.all.cpu.idle": {"instances": {-1: idle}},
            "kernel.all.cpu.wait.total": {"instances": {-1: iowait}},
            "hinv.ncpu": {"instances": {-1: ncpu}},
        }

    return _make


@pytest.fixture
def memory_metrics_data() -> Callable[..., dict]:
    """Factory for memory metrics data with configurable values."""

    def _make(
        physmem: int = 16_000_000,
        free: int = 4_000_000,
        available: int = 6_000_000,
        cached: int = 2_000_000,
        bufmem: int = 1_000_000,
        swap_total: int = 8_000_000,
        swap_free: int = 7_000_000,
    ) -> dict:
        return {
            "mem.physmem": {"instances": {-1: physmem}},
            "mem.util.free": {"instances": {-1: free}},
            "mem.util.available": {"instances": {-1: available}},
            "mem.util.cached": {"instances": {-1: cached}},
            "mem.util.bufmem": {"instances": {-1: bufmem}},
            "mem.util.swapTotal": {"instances": {-1: swap_total}},
            "mem.util.swapFree": {"instances": {-1: swap_free}},
        }

    return _make


@pytest.fixture
def load_metrics_data() -> Callable[..., dict]:
    """Factory for load metrics data with configurable values."""

    def _make(
        load_1m: float = 1.5,
        load_5m: float = 1.2,
        load_15m: float = 1.0,
        runnable: int = 3,
        nprocs: int = 200,
        ncpu: int = 4,
    ) -> dict:
        return {
            "kernel.all.load": {"instances": {1: load_1m, 5: load_5m, 15: load_15m}},
            "kernel.all.runnable": {"instances": {-1: runnable}},
            "kernel.all.nprocs": {"instances": {-1: nprocs}},
            "hinv.ncpu": {"instances": {-1: ncpu}},
        }

    return _make


@pytest.fixture
def disk_metrics_data() -> Callable[..., dict]:
    """Factory for disk metrics data with configurable values."""

    def _make(
        read_bytes: float = 1_000_000.0,
        write_bytes: float = 500_000.0,
        reads: float = 100.0,
        writes: float = 50.0,
    ) -> dict:
        return {
            "disk.all.read_bytes": {"instances": {-1: read_bytes}},
            "disk.all.write_bytes": {"instances": {-1: write_bytes}},
            "disk.all.read": {"instances": {-1: reads}},
            "disk.all.write": {"instances": {-1: writes}},
        }

    return _make


@pytest.fixture
def network_metrics_data() -> Callable[..., dict]:
    """Factory for network metrics data with configurable values."""

    def _make(
        in_bytes: dict | None = None,
        out_bytes: dict | None = None,
        in_packets: dict | None = None,
        out_packets: dict | None = None,
    ) -> dict:
        return {
            "network.interface.in.bytes": {
                "instances": in_bytes or {"eth0": 100_000.0, "lo": 1_000.0}
            },
            "network.interface.out.bytes": {
                "instances": out_bytes or {"eth0": 50_000.0, "lo": 1_000.0}
            },
            "network.interface.in.packets": {
                "instances": in_packets or {"eth0": 1_000.0, "lo": 10.0}
            },
            "network.interface.out.packets": {
                "instances": out_packets or {"eth0": 500.0, "lo": 10.0}
            },
        }

    return _make


@pytest.fixture
def process_metrics_data() -> Callable[..., dict]:
    """Factory for process metrics data with configurable values."""

    def _make(
        processes: list[dict] | None = None,
    ) -> dict:
        if processes is None:
            processes = [
                {
                    "inst": 1,
                    "pid": 1234,
                    "cmd": "python",
                    "args": "python app.py",
                    "rss": 1_000_000,
                },
                {"inst": 2, "pid": 5678, "cmd": "nginx", "args": "nginx -g daemon", "rss": 500_000},
            ]

        return {
            "proc.psinfo.pid": {"instances": {p["inst"]: p["pid"] for p in processes}},
            "proc.psinfo.cmd": {"instances": {p["inst"]: p["cmd"] for p in processes}},
            "proc.psinfo.psargs": {"instances": {p["inst"]: p["args"] for p in processes}},
            "proc.memory.rss": {"instances": {p["inst"]: p["rss"] for p in processes}},
            "proc.psinfo.utime": {
                "instances": {p["inst"]: p.get("utime", 100.0) for p in processes}
            },
            "proc.psinfo.stime": {
                "instances": {p["inst"]: p.get("stime", 50.0) for p in processes}
            },
            "proc.io.read_bytes": {
                "instances": {p["inst"]: p.get("io_read", 1000.0) for p in processes}
            },
            "proc.io.write_bytes": {
                "instances": {p["inst"]: p.get("io_write", 500.0) for p in processes}
            },
        }

    return _make


@pytest.fixture
def full_system_snapshot_data(
    cpu_metrics_data,
    memory_metrics_data,
    load_metrics_data,
    disk_metrics_data,
    network_metrics_data,
) -> Callable[..., dict]:
    """Factory for full system snapshot data combining all metric types."""

    def _make(**overrides) -> dict:
        data = {}
        data.update(cpu_metrics_data())
        data.update(memory_metrics_data())
        data.update(load_metrics_data())
        data.update(disk_metrics_data())
        data.update(network_metrics_data())
        for key, value in overrides.items():
            if key in data:
                data[key] = value
        return data

    return _make


@pytest.fixture
def pmproxy_fetch_response() -> Callable[..., dict]:
    """Factory for pmproxy fetch API response format."""

    def _make(
        values: list[dict],
        timestamp_s: int = 1000,
        timestamp_us: int = 0,
    ) -> dict:
        return {
            "timestamp": {"s": timestamp_s, "us": timestamp_us},
            "values": values,
        }

    return _make


@pytest.fixture
def mock_settings() -> PCPMCPSettings:
    """Create mock settings for testing."""
    return PCPMCPSettings(
        host="localhost",
        port=44322,
        target_host="localhost",
    )


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create a mock PCPClient."""
    client = AsyncMock(spec=PCPClient)
    client.target_host = "localhost"
    client.context_id = 12345
    return client


@pytest.fixture
def mock_lifespan_context(
    mock_client: AsyncMock,
    mock_settings: PCPMCPSettings,
) -> dict[str, Any]:
    """Create mock lifespan context."""
    return {"client": mock_client, "settings": mock_settings}


@pytest.fixture
def mock_context(mock_lifespan_context: dict[str, Any]) -> MagicMock:
    """Create a mock MCP Context."""
    from fastmcp import Context

    ctx = MagicMock(spec=Context)
    ctx.request_context = MagicMock()
    ctx.request_context.lifespan_context = mock_lifespan_context
    return ctx


@pytest.fixture
def capture_tools() -> Callable[[RegisterFn], ToolDict]:
    def factory(register_fn: RegisterFn) -> ToolDict:
        tools: ToolDict = {}

        def capture_tool():
            def decorator(fn):
                tools[fn.__name__] = fn
                return fn

            return decorator

        mcp = MagicMock()
        mcp.tool = capture_tool
        register_fn(mcp)
        return tools

    return factory


@pytest.fixture
def capture_resources() -> Callable[[RegisterFn], ResourceDict]:
    def factory(register_fn: RegisterFn) -> ResourceDict:
        resources: ResourceDict = {}

        def capture_resource(uri: str):
            def decorator(fn):
                resources[uri] = fn
                return fn

            return decorator

        mcp = MagicMock()
        mcp.resource = capture_resource
        register_fn(mcp)
        return resources

    return factory


@pytest.fixture
def namespace_search_response() -> Callable[..., list[dict]]:
    def _make(namespaces: list[str] | None = None) -> list[dict]:
        if namespaces is None:
            namespaces = ["kernel.all.load", "kernel.all.cpu.user", "mem.physmem", "disk.all.read"]
        return [{"name": ns} for ns in namespaces]

    return _make


@pytest.fixture
def pmda_status_response() -> Callable[..., dict]:
    def _make(pmdas: list[tuple[str | int, int]] | None = None) -> dict:
        if pmdas is None:
            pmdas = [("linux", 0), ("pmcd", 0)]
        return {
            "values": [
                {
                    "name": "pmcd.agent.status",
                    "instances": [{"instance": name, "value": status} for name, status in pmdas],
                }
            ]
        }

    return _make
