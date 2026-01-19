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


def test_default_allowed_hosts_is_none() -> None:
    settings = PCPMCPSettings()
    assert settings.allowed_hosts is None


class TestIsHostAllowed:
    def test_target_host_always_allowed(self) -> None:
        settings = PCPMCPSettings(target_host="myhost.example.com")
        assert settings.is_host_allowed("myhost.example.com") is True

    def test_other_host_denied_when_allowlist_is_none(self) -> None:
        settings = PCPMCPSettings(target_host="localhost")
        assert settings.is_host_allowed("attacker.example.com") is False

    def test_allowlisted_host_permitted(self) -> None:
        settings = PCPMCPSettings(
            target_host="localhost",
            allowed_hosts=["web1.example.com", "db1.example.com"],
        )
        assert settings.is_host_allowed("web1.example.com") is True
        assert settings.is_host_allowed("db1.example.com") is True

    def test_non_allowlisted_host_denied(self) -> None:
        settings = PCPMCPSettings(
            target_host="localhost",
            allowed_hosts=["web1.example.com"],
        )
        assert settings.is_host_allowed("attacker.example.com") is False

    def test_wildcard_allows_any_host(self) -> None:
        settings = PCPMCPSettings(
            target_host="localhost",
            allowed_hosts=["*"],
        )
        assert settings.is_host_allowed("any.host.anywhere.com") is True
        assert settings.is_host_allowed("192.168.1.1") is True

    def test_empty_allowlist_denies_all_except_target(self) -> None:
        settings = PCPMCPSettings(
            target_host="localhost",
            allowed_hosts=[],
        )
        assert settings.is_host_allowed("localhost") is True
        assert settings.is_host_allowed("other.host.com") is False
