"""Tests for configuration."""

from __future__ import annotations

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


def test_base_url_http() -> None:
    settings = PCPMCPSettings(host="example.com", port=8080)
    assert settings.base_url == "http://example.com:8080"


def test_base_url_https() -> None:
    settings = PCPMCPSettings(host="example.com", port=443, use_tls=True)
    assert settings.base_url == "https://example.com:443"


def test_auth_none_when_no_credentials() -> None:
    settings = PCPMCPSettings()
    assert settings.auth is None


def test_auth_tuple_when_credentials_provided() -> None:
    settings = PCPMCPSettings(username="user", password="pass")
    assert settings.auth == ("user", "pass")


def test_auth_none_when_only_username() -> None:
    settings = PCPMCPSettings(username="user")
    assert settings.auth is None


def test_auth_none_when_only_password() -> None:
    settings = PCPMCPSettings(password="pass")
    assert settings.auth is None
