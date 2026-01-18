"""Tests for CLI entry point."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from pcp_mcp import main


class TestCLI:
    @patch("pcp_mcp.server.create_server")
    def test_main_runs_server_with_default_transport(self, mock_create_server: MagicMock) -> None:
        mock_server = MagicMock()
        mock_create_server.return_value = mock_server

        with patch("sys.argv", ["pcp-mcp"]):
            main()

        mock_create_server.assert_called_once()
        mock_server.run.assert_called_once_with(transport="stdio")

    @patch("pcp_mcp.server.create_server")
    def test_main_runs_server_with_sse_transport(self, mock_create_server: MagicMock) -> None:
        mock_server = MagicMock()
        mock_create_server.return_value = mock_server

        with patch("sys.argv", ["pcp-mcp", "--transport", "sse"]):
            main()

        mock_server.run.assert_called_once_with(transport="sse")

    @patch("pcp_mcp.server.create_server")
    def test_main_runs_server_with_streamable_http_transport(
        self, mock_create_server: MagicMock
    ) -> None:
        mock_server = MagicMock()
        mock_create_server.return_value = mock_server

        with patch("sys.argv", ["pcp-mcp", "--transport", "streamable-http"]):
            main()

        mock_server.run.assert_called_once_with(transport="streamable-http")

    @patch("pcp_mcp.server.create_server")
    def test_main_sets_target_host_env_var(self, mock_create_server: MagicMock) -> None:
        mock_server = MagicMock()
        mock_create_server.return_value = mock_server
        original_env = os.environ.get("PCP_TARGET_HOST")

        try:
            with patch("sys.argv", ["pcp-mcp", "--target-host", "remote.example.com"]):
                main()

            assert os.environ.get("PCP_TARGET_HOST") == "remote.example.com"
        finally:
            if original_env is not None:
                os.environ["PCP_TARGET_HOST"] = original_env
            elif "PCP_TARGET_HOST" in os.environ:
                del os.environ["PCP_TARGET_HOST"]

    def test_main_rejects_invalid_transport(self) -> None:
        with (
            patch("sys.argv", ["pcp-mcp", "--transport", "invalid"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 2
