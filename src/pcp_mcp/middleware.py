"""Custom middleware for pcp-mcp server."""

from __future__ import annotations

import hashlib
import time
from typing import TYPE_CHECKING, Any

from fastmcp.server.middleware import Middleware
from fastmcp.tools.tool import ToolResult

if TYPE_CHECKING:
    from fastmcp.server.middleware.middleware import CallNext, MiddlewareContext
    from mcp import types as mt


CACHEABLE_TOOLS = frozenset({"describe_metric", "search_metrics"})
DEFAULT_TTL_SECONDS = 300


class MetricCacheMiddleware(Middleware):
    """Cache responses for describe_metric and search_metrics tools.

    These tools query PCP metric metadata which changes infrequently.
    Caching reduces pmproxy load and improves LLM response times.
    """

    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        """Initialize the cache middleware.

        Args:
            ttl_seconds: Time-to-live for cached entries in seconds.
        """
        self._cache: dict[str, tuple[float, Any]] = {}
        self._ttl = ttl_seconds

    def _make_cache_key(self, tool_name: str, arguments: dict | None) -> str:
        args_str = str(sorted((arguments or {}).items()))
        return hashlib.sha256(f"{tool_name}:{args_str}".encode()).hexdigest()[:16]

    def _is_expired(self, timestamp: float) -> bool:
        return (time.time() - timestamp) > self._ttl

    def _cleanup_expired(self) -> None:
        now = time.time()
        expired_keys = [k for k, (ts, _) in self._cache.items() if (now - ts) > self._ttl]
        for key in expired_keys:
            del self._cache[key]

    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next: CallNext[mt.CallToolRequestParams, ToolResult],
    ) -> ToolResult:
        """Intercept tool calls and cache describe_metric/search_metrics responses."""
        tool_name = context.message.name
        arguments = context.message.arguments

        if tool_name not in CACHEABLE_TOOLS:
            return await call_next(context)

        if arguments and arguments.get("host"):
            return await call_next(context)

        cache_key = self._make_cache_key(tool_name, arguments)

        if cache_key in self._cache:
            timestamp, cached_result = self._cache[cache_key]
            if not self._is_expired(timestamp):
                return cached_result

        result = await call_next(context)

        self._cache[cache_key] = (time.time(), result)

        if len(self._cache) > 100:
            self._cleanup_expired()

        return result

    @property
    def cache_size(self) -> int:
        """Number of entries in the cache."""
        return len(self._cache)

    def clear_cache(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
