# Changelog

All notable changes to this project will be documented in this file.

This project uses [Semantic Versioning](https://semver.org/) and [Conventional Commits](https://www.conventionalcommits.org/).

<!-- version list -->

## v0.1.0 (2026-01-18)

Initial release of pcp-mcp.

### Features

- MCP server for Performance Co-Pilot metrics via pmproxy REST API
- System monitoring tools: `get_system_snapshot`, `get_process_top`
- Metric tools: `query_metrics`, `search_metrics`, `describe_metric`
- MCP resources: `pcp://health`, `pcp://metrics/common`, `pcp://namespaces`
- Remote host monitoring via `PCP_TARGET_HOST` or `--target-host`
- Host allowlist for SSRF protection (`PCP_ALLOWED_HOSTS`)
- TLS support with configurable verification
- HTTP basic authentication support
- FastMCP 2.0+ features: tool annotations, caching, progress reporting
