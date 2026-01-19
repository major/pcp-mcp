"""Tests for MCP prompts."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import pytest

from pcp_mcp.prompts import register_prompts


@pytest.fixture
def capture_prompts() -> Callable[[Callable[[MagicMock], None]], dict[str, Callable[..., Any]]]:
    def factory(register_fn: Callable[[MagicMock], None]) -> dict[str, Callable[..., Any]]:
        prompts: dict[str, Callable[..., Any]] = {}

        def capture_prompt(**_kwargs):
            def decorator(fn):
                prompts[fn.__name__] = fn
                return fn

            return decorator

        mcp = MagicMock()
        mcp.prompt = capture_prompt
        register_fn(mcp)
        return prompts

    return factory


class TestRegisterPrompts:
    def test_registers_all_prompts(self, capture_prompts) -> None:
        prompts = capture_prompts(register_prompts)

        expected_prompts = {
            "diagnose_slow_system",
            "investigate_memory_usage",
            "find_io_bottleneck",
            "analyze_cpu_usage",
            "check_network_performance",
        }
        assert set(prompts.keys()) == expected_prompts


class TestPromptContent:
    @pytest.mark.parametrize(
        ("prompt_name", "expected_keywords"),
        [
            (
                "diagnose_slow_system",
                ["get_system_snapshot", "get_process_top", "cpu", "memory", "disk"],
            ),
            (
                "investigate_memory_usage",
                ["memory", "swap", "mem.util", "rss_bytes", "get_process_top"],
            ),
            (
                "find_io_bottleneck",
                ["disk", "iowait", "disk.dev", "read", "write", "get_system_snapshot"],
            ),
            (
                "analyze_cpu_usage",
                ["cpu", "user", "system", "idle", "load", "kernel.percpu.cpu"],
            ),
            (
                "check_network_performance",
                ["network", "throughput", "interface", "packets", "errors"],
            ),
        ],
    )
    def test_prompt_contains_expected_keywords(
        self, capture_prompts, prompt_name: str, expected_keywords: list[str]
    ) -> None:
        prompts = capture_prompts(register_prompts)
        content = prompts[prompt_name]()

        for keyword in expected_keywords:
            assert keyword.lower() in content.lower(), f"'{keyword}' not found in {prompt_name}"
