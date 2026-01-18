"""Error handling decorators for MCP tools."""

from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any


def handle_pcp_errors(operation: str) -> Callable:
    """Decorator to convert PCP exceptions to ToolError.

    Args:
        operation: Description of the operation (e.g., "fetching metrics").

    Returns:
        Decorated async function that handles PCP errors.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            from pcp_mcp.errors import handle_pcp_error

            try:
                return await func(*args, **kwargs)
            except Exception as e:
                raise handle_pcp_error(e, operation) from e

        return wrapper

    return decorator


__all__ = ["handle_pcp_errors"]
