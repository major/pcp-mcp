"""Configuration for the PCP MCP server."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PCPMCPSettings(BaseSettings):
    """Configuration for the PCP MCP server.

    Attributes:
        host: pmproxy host.
        port: pmproxy port.
        use_tls: Use HTTPS for pmproxy connection.
        timeout: Request timeout in seconds.
        target_host: Target pmcd host to monitor (can be remote hostname).
        username: HTTP basic auth user.
        password: HTTP basic auth password.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="PCP_",
        extra="ignore",
    )

    host: str = Field(default="localhost", description="pmproxy host")
    port: int = Field(default=44322, description="pmproxy port")
    use_tls: bool = Field(default=False, description="Use HTTPS for pmproxy connection")
    timeout: float = Field(default=30.0, description="Request timeout in seconds")
    target_host: str = Field(
        default="localhost",
        description="Target pmcd host to monitor (can be remote hostname)",
    )
    username: str | None = Field(default=None, description="HTTP basic auth user")
    password: str | None = Field(default=None, description="HTTP basic auth password")

    @property
    def base_url(self) -> str:
        """URL for connecting to pmproxy."""
        scheme = "https" if self.use_tls else "http"
        return f"{scheme}://{self.host}:{self.port}"

    @property
    def auth(self) -> tuple[str, str] | None:
        """Auth tuple for httpx, or None if no auth configured."""
        if self.username and self.password:
            return (self.username, self.password)
        return None
