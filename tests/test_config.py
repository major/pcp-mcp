"""Tests for configuration."""

from __future__ import annotations

import pytest

from pcp_mcp.config import PCPMCPSettings


def test_default_settings() -> None:
    settings = PCPMCPSettings()
    assert settings.host == "localhost"
    assert settings.port == 44322
    assert settings.target_host == "localhost"
    assert settings.use_tls is False
    assert settings.timeout == 30.0
    assert settings.username is None
    assert settings.password is None


@pytest.mark.parametrize(
    ("host", "port", "use_tls", "expected_url"),
    [
        ("example.com", 8080, False, "http://example.com:8080"),
        ("example.com", 443, True, "https://example.com:443"),
    ],
)
def test_base_url(
    host: str,
    port: int,
    use_tls: bool,
    expected_url: str,
) -> None:
    settings = PCPMCPSettings(host=host, port=port, use_tls=use_tls)
    assert settings.base_url == expected_url


@pytest.mark.parametrize(
    ("username", "password", "expected_auth"),
    [
        (None, None, None),
        ("user", None, None),
        (None, "pass", None),
        ("user", "pass", ("user", "pass")),
    ],
)
def test_auth_combinations(
    username: str | None,
    password: str | None,
    expected_auth: tuple[str, str] | None,
) -> None:
    settings = PCPMCPSettings(username=username, password=password)
    assert settings.auth == expected_auth
