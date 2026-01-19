"""Tests for system health tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, call

import httpx
import pytest
from fastmcp.exceptions import ToolError

from pcp_mcp.models import DiagnosisResult
from pcp_mcp.tools.system import (
    _build_fallback_diagnosis,
    _format_snapshot_for_llm,
    register_system_tools,
)


class TestGetSystemSnapshot:
    async def test_returns_all_categories(
        self,
        mock_context: MagicMock,
        capture_tools,
        full_system_snapshot_data,
    ) -> None:
        mock_context.request_context.lifespan_context[
            "client"
        ].fetch_with_rates.return_value = full_system_snapshot_data()

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
        cpu_metrics_data,
    ) -> None:
        mock_context.request_context.lifespan_context[
            "client"
        ].fetch_with_rates.return_value = cpu_metrics_data()

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
        mock_context.request_context.lifespan_context[
            "client"
        ].fetch_with_rates.side_effect = httpx.ConnectError("Connection refused")

        tools = capture_tools(register_system_tools)

        with pytest.raises(ToolError, match="Cannot connect to pmproxy"):
            await tools["get_system_snapshot"](mock_context)

    async def test_reports_progress(
        self,
        mock_context: MagicMock,
        capture_tools,
        full_system_snapshot_data,
    ) -> None:
        mock_context.request_context.lifespan_context[
            "client"
        ].fetch_with_rates.return_value = full_system_snapshot_data()
        mock_context.report_progress = AsyncMock()

        tools = capture_tools(register_system_tools)
        await tools["get_system_snapshot"](mock_context)

        assert mock_context.report_progress.call_count >= 2
        calls = mock_context.report_progress.call_args_list
        assert calls[-1] == call(100, 100, "Complete")


class TestQuickHealth:
    async def test_returns_only_cpu_and_memory(
        self,
        mock_context: MagicMock,
        capture_tools,
        cpu_metrics_data,
        memory_metrics_data,
    ) -> None:
        combined_data = {**cpu_metrics_data(), **memory_metrics_data()}
        mock_context.request_context.lifespan_context[
            "client"
        ].fetch_with_rates.return_value = combined_data

        tools = capture_tools(register_system_tools)
        result = await tools["quick_health"](mock_context)

        assert result.cpu is not None
        assert result.memory is not None
        assert result.load is None
        assert result.disk is None
        assert result.network is None

    async def test_uses_shorter_sample_interval(
        self,
        mock_context: MagicMock,
        capture_tools,
        cpu_metrics_data,
        memory_metrics_data,
    ) -> None:
        combined_data = {**cpu_metrics_data(), **memory_metrics_data()}
        mock_context.request_context.lifespan_context[
            "client"
        ].fetch_with_rates.return_value = combined_data

        tools = capture_tools(register_system_tools)
        await tools["quick_health"](mock_context)

        call_args = mock_context.request_context.lifespan_context[
            "client"
        ].fetch_with_rates.call_args
        sample_interval_arg = call_args[0][2]
        assert sample_interval_arg == 0.5


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
        capture_tools,
        process_metrics_data,
        system_info_response: dict,
        sort_by: str,
        expected_field: str,
    ) -> None:
        mock_context.request_context.lifespan_context[
            "client"
        ].fetch_with_rates.return_value = process_metrics_data()
        mock_context.request_context.lifespan_context[
            "client"
        ].fetch.return_value = system_info_response

        tools = capture_tools(register_system_tools)
        result = await tools["get_process_top"](mock_context, sort_by=sort_by, limit=2)

        assert len(result.processes) == 2
        assert result.sort_by == sort_by
        assert result.ncpu == 4
        assert getattr(result.processes[0], expected_field) is not None

    async def test_handles_error(
        self,
        mock_context: MagicMock,
        capture_tools,
    ) -> None:
        mock_context.request_context.lifespan_context[
            "client"
        ].fetch_with_rates.side_effect = httpx.ConnectError("Connection refused")

        tools = capture_tools(register_system_tools)

        with pytest.raises(ToolError, match="Cannot connect to pmproxy"):
            await tools["get_process_top"](mock_context)

    async def test_reports_progress(
        self,
        mock_context: MagicMock,
        capture_tools,
        process_metrics_data,
    ) -> None:
        mock_context.request_context.lifespan_context[
            "client"
        ].fetch_with_rates.return_value = process_metrics_data()
        mock_context.request_context.lifespan_context["client"].fetch.return_value = {
            "values": [
                {"name": "hinv.ncpu", "instances": [{"value": 4}]},
                {"name": "mem.physmem", "instances": [{"value": 16000000}]},
            ]
        }
        mock_context.report_progress = AsyncMock()

        tools = capture_tools(register_system_tools)
        await tools["get_process_top"](mock_context)

        assert mock_context.report_progress.call_count >= 2
        calls = mock_context.report_progress.call_args_list
        assert calls[-1] == call(100, 100, "Complete")


class TestSmartDiagnose:
    async def test_returns_llm_diagnosis(
        self,
        mock_context: MagicMock,
        capture_tools,
        cpu_metrics_data,
        memory_metrics_data,
        load_metrics_data,
    ) -> None:
        combined_data = {
            **cpu_metrics_data(),
            **memory_metrics_data(),
            **load_metrics_data(),
        }
        mock_context.request_context.lifespan_context[
            "client"
        ].fetch_with_rates.return_value = combined_data

        llm_result = DiagnosisResult(
            timestamp="ignored",
            hostname="ignored",
            diagnosis="System is healthy with normal resource usage.",
            severity="healthy",
            recommendations=["Continue monitoring"],
        )
        mock_sampling_result = MagicMock()
        mock_sampling_result.result = llm_result
        mock_context.sample = AsyncMock(return_value=mock_sampling_result)

        tools = capture_tools(register_system_tools)
        result = await tools["smart_diagnose"](mock_context)

        assert result.severity == "healthy"
        assert "healthy" in result.diagnosis.lower()
        assert result.hostname == "localhost"
        mock_context.sample.assert_called_once()

    async def test_uses_fallback_when_llm_fails(
        self,
        mock_context: MagicMock,
        capture_tools,
        cpu_metrics_data,
        memory_metrics_data,
        load_metrics_data,
    ) -> None:
        combined_data = {
            **cpu_metrics_data(idle=5.0),
            **memory_metrics_data(physmem=16_000_000, available=800_000, free=500_000),
            **load_metrics_data(load_1m=16.0),
        }
        mock_context.request_context.lifespan_context[
            "client"
        ].fetch_with_rates.return_value = combined_data
        mock_context.sample = AsyncMock(side_effect=RuntimeError("LLM not available"))

        tools = capture_tools(register_system_tools)
        result = await tools["smart_diagnose"](mock_context)

        assert result.severity == "critical"
        assert result.hostname == "localhost"
        assert len(result.recommendations) > 0

    async def test_handles_connection_error(
        self,
        mock_context: MagicMock,
        capture_tools,
    ) -> None:
        mock_context.request_context.lifespan_context[
            "client"
        ].fetch_with_rates.side_effect = httpx.ConnectError("Connection refused")

        tools = capture_tools(register_system_tools)

        with pytest.raises(ToolError, match="Cannot connect to pmproxy"):
            await tools["smart_diagnose"](mock_context)


class TestFormatSnapshotForLlm:
    def test_formats_all_sections(self, full_system_snapshot_data) -> None:
        from pcp_mcp.models import SystemSnapshot
        from pcp_mcp.utils.builders import (
            build_cpu_metrics,
            build_load_metrics,
            build_memory_metrics,
        )

        data = full_system_snapshot_data()
        snapshot = SystemSnapshot(
            timestamp="2025-01-18T12:00:00Z",
            hostname="testhost",
            cpu=build_cpu_metrics(data),
            memory=build_memory_metrics(data),
            load=build_load_metrics(data),
        )

        result = _format_snapshot_for_llm(snapshot)

        assert "testhost" in result
        assert "CPU:" in result
        assert "Memory:" in result
        assert "Load:" in result

    def test_handles_partial_snapshot(self) -> None:
        from pcp_mcp.models import SystemSnapshot

        snapshot = SystemSnapshot(
            timestamp="2025-01-18T12:00:00Z",
            hostname="testhost",
        )

        result = _format_snapshot_for_llm(snapshot)

        assert "testhost" in result
        assert "CPU:" not in result


class TestBuildFallbackDiagnosis:
    @pytest.mark.parametrize(
        ("cpu_idle", "mem_used", "load_1m", "ncpu", "expected_severity"),
        [
            (80.0, 50.0, 1.0, 4, "healthy"),
            (25.0, 50.0, 1.0, 4, "warning"),
            (5.0, 50.0, 1.0, 4, "critical"),
            (80.0, 80.0, 1.0, 4, "warning"),
            (80.0, 95.0, 1.0, 4, "critical"),
            (80.0, 50.0, 12.0, 4, "critical"),
        ],
    )
    def test_severity_levels(
        self,
        cpu_idle: float,
        mem_used: float,
        load_1m: float,
        ncpu: int,
        expected_severity: str,
    ) -> None:
        from pcp_mcp.models import (
            CPUMetrics,
            LoadMetrics,
            MemoryMetrics,
            SystemSnapshot,
        )

        snapshot = SystemSnapshot(
            timestamp="2025-01-18T12:00:00Z",
            hostname="testhost",
            cpu=CPUMetrics(
                user_percent=100 - cpu_idle - 5,
                system_percent=5.0,
                idle_percent=cpu_idle,
                iowait_percent=0.0,
                ncpu=ncpu,
                assessment="test",
            ),
            memory=MemoryMetrics(
                total_bytes=16 * 1024**3,
                used_bytes=int(16 * 1024**3 * mem_used / 100),
                free_bytes=int(16 * 1024**3 * (100 - mem_used) / 100),
                available_bytes=int(16 * 1024**3 * (100 - mem_used) / 100),
                cached_bytes=0,
                buffers_bytes=0,
                swap_used_bytes=0,
                swap_total_bytes=0,
                used_percent=mem_used,
                assessment="test",
            ),
            load=LoadMetrics(
                load_1m=load_1m,
                load_5m=load_1m,
                load_15m=load_1m,
                runnable=1,
                nprocs=100,
                assessment="test",
            ),
        )

        result = _build_fallback_diagnosis(snapshot)

        assert result.severity == expected_severity
        assert result.hostname == "testhost"
        assert len(result.recommendations) > 0
