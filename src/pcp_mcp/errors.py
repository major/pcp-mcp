"""Error mapping from httpx to MCP ToolErrors."""

from __future__ import annotations

import httpx
from fastmcp.exceptions import ToolError


class PCPError(Exception):
    """Base PCP error."""


class PCPConnectionError(PCPError):
    """Cannot connect to pmproxy."""


class PCPMetricNotFoundError(PCPError):
    """Metric does not exist."""


def handle_pcp_error(e: Exception, operation: str) -> ToolError:
    """Convert PCP/httpx exceptions to MCP ToolErrors.

    Args:
        e: The exception to convert.
        operation: Description of the operation that failed.

    Returns:
        A ToolError with an appropriate message.
    """
    match e:
        case httpx.ConnectError():
            return ToolError("Cannot connect to pmproxy. Is it running? (systemctl start pmproxy)")
        case httpx.HTTPStatusError() as he if he.response.status_code == 400:
            return ToolError(f"Bad request during {operation}: {he.response.text}")
        case httpx.HTTPStatusError() as he if he.response.status_code == 404:
            return ToolError(f"Metric not found during {operation}")
        case httpx.HTTPStatusError() as he:
            return ToolError(f"pmproxy error ({he.response.status_code}): {he.response.text}")
        case httpx.TimeoutException():
            return ToolError(f"Request timed out during {operation}")
        case PCPConnectionError():
            return ToolError(str(e))
        case PCPMetricNotFoundError():
            return ToolError(f"Metric not found: {e}")
        case _:
            return ToolError(f"Error during {operation}: {e}")
