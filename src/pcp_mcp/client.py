"""Async client for pmproxy REST API."""

from __future__ import annotations

from typing import Self

import httpx


class PCPClient:
    """Async client for pmproxy REST API.

    Handles PMAPI context management and metric fetching via the pmproxy
    REST API endpoints.

    Args:
        base_url: Base URL for pmproxy (e.g., http://localhost:44322).
        target_host: Which pmcd host to connect to (passed as hostspec).
        auth: Optional HTTP basic auth tuple (username, password).
        timeout: Request timeout in seconds.
    """

    def __init__(
        self,
        base_url: str,
        target_host: str = "localhost",
        auth: tuple[str, str] | None = None,
        timeout: float = 30.0,
    ) -> None:
        """Initialize the PCP client."""
        self._base_url = base_url
        self._target_host = target_host
        self._auth = auth
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._context_id: int | None = None

    async def __aenter__(self) -> Self:
        """Enter async context and establish pmapi context."""
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            auth=self._auth,
            timeout=self._timeout,
        )
        resp = await self._client.get(
            "/pmapi/context",
            params={"hostspec": self._target_host},
        )
        resp.raise_for_status()
        self._context_id = resp.json()["context"]
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit async context and close httpx client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def target_host(self) -> str:
        """The pmcd host this client is connected to."""
        return self._target_host

    @property
    def context_id(self) -> int | None:
        """The pmapi context ID, or None if not connected."""
        return self._context_id

    async def fetch(self, metric_names: list[str]) -> dict:
        """Fetch current values for metrics.

        Args:
            metric_names: List of PCP metric names to fetch.

        Returns:
            Raw JSON response from pmproxy /pmapi/fetch endpoint.

        Raises:
            RuntimeError: If client is not connected.
            httpx.HTTPStatusError: If the request fails.
        """
        if self._client is None:
            raise RuntimeError("Client not connected. Use async with context.")
        resp = await self._client.get(
            "/pmapi/fetch",
            params={"context": self._context_id, "names": ",".join(metric_names)},
        )
        resp.raise_for_status()
        return resp.json()

    async def search(self, pattern: str) -> list[dict]:
        """Search for metrics matching pattern.

        Args:
            pattern: Metric name prefix to search for (e.g., "kernel.all").

        Returns:
            List of metric metadata dicts from pmproxy.

        Raises:
            RuntimeError: If client is not connected.
            httpx.HTTPStatusError: If the request fails.
        """
        if self._client is None:
            raise RuntimeError("Client not connected. Use async with context.")
        resp = await self._client.get(
            "/pmapi/metric",
            params={"context": self._context_id, "prefix": pattern},
        )
        resp.raise_for_status()
        return resp.json().get("metrics", [])

    async def describe(self, metric_name: str) -> dict:
        """Get metric metadata.

        Args:
            metric_name: Full PCP metric name.

        Returns:
            Metric metadata dict, or empty dict if not found.

        Raises:
            RuntimeError: If client is not connected.
            httpx.HTTPStatusError: If the request fails.
        """
        if self._client is None:
            raise RuntimeError("Client not connected. Use async with context.")
        resp = await self._client.get(
            "/pmapi/metric",
            params={"context": self._context_id, "names": metric_name},
        )
        resp.raise_for_status()
        metrics = resp.json().get("metrics", [])
        return metrics[0] if metrics else {}
