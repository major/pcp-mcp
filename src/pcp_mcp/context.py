"""Context helpers for safe lifespan context access."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastmcp import Context
from fastmcp.exceptions import ToolError

if TYPE_CHECKING:
    from pcp_mcp.client import PCPClient
    from pcp_mcp.config import PCPMCPSettings


class ClientManager:
    """Manages multiple PCP client connections to different hosts.

    Maintains a cache of active clients per host and provides methods to
    get or create clients for specific hosts.
    """

    def __init__(
        self,
        base_url: str,
        default_target_host: str,
        auth: tuple[str, str] | None = None,
        timeout: float = 30.0,
    ) -> None:
        """Initialize the client manager.

        Args:
            base_url: Base URL for pmproxy.
            default_target_host: Default host to monitor.
            auth: Optional HTTP basic auth tuple.
            timeout: Request timeout in seconds.
        """
        self._base_url = base_url
        self._default_target_host = default_target_host
        self._auth = auth
        self._timeout = timeout
        self._clients: dict[str, PCPClient] = {}
        self._default_client: PCPClient | None = None

    async def get_client(self, target_host: str | None = None) -> PCPClient:
        """Get or create a client for the specified host.

        Args:
            target_host: Host to connect to. If None, uses default.

        Returns:
            PCPClient instance for the specified host.

        Raises:
            Exception: If client creation or connection fails.
        """
        # Import locally to avoid circular dependency
        from pcp_mcp.client import PCPClient

        host = target_host or self._default_target_host

        # Return cached client if available
        if host == self._default_target_host and self._default_client:
            return self._default_client

        if host in self._clients:
            return self._clients[host]

        # Create new client
        client = PCPClient(
            base_url=self._base_url,
            target_host=host,
            auth=self._auth,
            timeout=self._timeout,
        )
        
        try:
            await client.__aenter__()
        except Exception:
            # Ensure we clean up the client if connection fails
            await client.__aexit__(None, None, None)
            raise

        # Cache the client
        if host == self._default_target_host:
            self._default_client = client
        else:
            self._clients[host] = client

        return client

    async def close_all(self) -> None:
        """Close all managed client connections.
        
        Attempts to close all clients, collecting any exceptions that occur.
        """
        exceptions = []
        
        if self._default_client:
            try:
                await self._default_client.__aexit__(None, None, None)
            except Exception as e:
                exceptions.append(e)
            finally:
                self._default_client = None

        for client in self._clients.values():
            try:
                await client.__aexit__(None, None, None)
            except Exception as e:
                exceptions.append(e)
        self._clients.clear()
        
        # If any exceptions occurred, raise the first one
        if exceptions:
            raise exceptions[0]


def _validate_context(ctx: Context) -> None:
    """Validate context has lifespan_context available.

    Args:
        ctx: MCP context.

    Raises:
        ToolError: If context is not available.
    """
    if ctx.request_context is None or ctx.request_context.lifespan_context is None:
        raise ToolError("Server context not available")


async def get_client(ctx: Context, target_host: str | None = None) -> PCPClient:
    """Get PCPClient from context for the specified host.

    Args:
        ctx: MCP context.
        target_host: Optional target host. If None, uses default configured host.

    Returns:
        The PCPClient instance for the specified host.

    Raises:
        ToolError: If context is not available.
    """
    _validate_context(ctx)
    manager: ClientManager = ctx.request_context.lifespan_context["client_manager"]
    return await manager.get_client(target_host)


def get_settings(ctx: Context) -> PCPMCPSettings:
    """Get settings from context.

    Args:
        ctx: MCP context.

    Returns:
        The PCPMCPSettings instance.

    Raises:
        ToolError: If context is not available.
    """
    _validate_context(ctx)
    return ctx.request_context.lifespan_context["settings"]
