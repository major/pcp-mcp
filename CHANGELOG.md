# Changelog

All notable changes to this project will be documented in this file.

This project uses [Semantic Versioning](https://semver.org/) and [Conventional Commits](https://www.conventionalcommits.org/).

<!-- version list -->

## v1.0.0 (2026-01-19)

### Bug Fixes

- Add type assertions to narrow context types for ty check
  ([`3ddcc27`](https://github.com/major/pcp-mcp/commit/3ddcc27b14007b43fa4aa78f3042839932ffdb69))

- Disable build in semantic-release, use pypi job instead
  ([`5f6d978`](https://github.com/major/pcp-mcp/commit/5f6d9781e7db6a160ef8aa79ebbb822438e58b4e))

- Remove 'from __future__ import annotations' from tools modules
  ([`e8d90c6`](https://github.com/major/pcp-mcp/commit/e8d90c65661b85a0ea5e6319a45cfa6327668f0f))

- **ci**: Pass CODECOV_TOKEN to codecov action
  ([`7013aaf`](https://github.com/major/pcp-mcp/commit/7013aaf4d13433bc2b244ea4d689397f8744a9cb))

- **security**: Add host allowlist to prevent SSRF via host parameter
  ([#12](https://github.com/major/pcp-mcp/pull/12),
  [`7dc11d2`](https://github.com/major/pcp-mcp/commit/7dc11d294e243da15e472856e0624bff30756032))

- **tools**: Resolve Pydantic annotation evaluation error
  ([`1b1615d`](https://github.com/major/pcp-mcp/commit/1b1615d473d869236db1a84ddb94a9c34d52a121))

### Features

- Add audit logging middleware for MCP requests ([#14](https://github.com/major/pcp-mcp/pull/14),
  [`8199e7e`](https://github.com/major/pcp-mcp/commit/8199e7e1e98f50a4b2f7b788f50c6cc69cf14bc1))

- Add automated semantic versioning and PEP 561 typed package support
  ([`4093790`](https://github.com/major/pcp-mcp/commit/40937908e25908432f1fe43ce00ee056d260c95d))

- Add caching middleware for metric metadata tools ([#17](https://github.com/major/pcp-mcp/pull/17),
  [`22f35a2`](https://github.com/major/pcp-mcp/commit/22f35a2cc5c44a51283b25f0bf900a2b13b9fa1f))

- Add FastMCP 2.0 features (icons, caching, sampling)
  ([#17](https://github.com/major/pcp-mcp/pull/17),
  [`22f35a2`](https://github.com/major/pcp-mcp/commit/22f35a2cc5c44a51283b25f0bf900a2b13b9fa1f))

- Add FastMCP progress reporting and resource templates
  ([#15](https://github.com/major/pcp-mcp/pull/15),
  [`30a0c72`](https://github.com/major/pcp-mcp/commit/30a0c72b4d15fa3c52eb9ba669ccb68f1cdad3da))

- Add icons and tags to MCP tools, resources, and prompts
  ([#17](https://github.com/major/pcp-mcp/pull/17),
  [`22f35a2`](https://github.com/major/pcp-mcp/commit/22f35a2cc5c44a51283b25f0bf900a2b13b9fa1f))

- Add MCP tool annotations for read-only and open-world hints
  ([#16](https://github.com/major/pcp-mcp/pull/16),
  [`441401f`](https://github.com/major/pcp-mcp/commit/441401fb95675a20cdb9eb27cfe7d9246978ce7d))

- Add MCP tool annotations, structured logging, and output schemas
  ([#16](https://github.com/major/pcp-mcp/pull/16),
  [`441401f`](https://github.com/major/pcp-mcp/commit/441401fb95675a20cdb9eb27cfe7d9246978ce7d))

- Add output schemas to MCP tools for LLM introspection
  ([#16](https://github.com/major/pcp-mcp/pull/16),
  [`441401f`](https://github.com/major/pcp-mcp/commit/441401fb95675a20cdb9eb27cfe7d9246978ce7d))

- Add progress reporting to system tools ([#15](https://github.com/major/pcp-mcp/pull/15),
  [`30a0c72`](https://github.com/major/pcp-mcp/commit/30a0c72b4d15fa3c52eb9ba669ccb68f1cdad3da))

- Add quick_health tool for fast CPU/memory checks ([#17](https://github.com/major/pcp-mcp/pull/17),
  [`22f35a2`](https://github.com/major/pcp-mcp/commit/22f35a2cc5c44a51283b25f0bf900a2b13b9fa1f))

- Add resource templates for per-host health and metric info
  ([#15](https://github.com/major/pcp-mcp/pull/15),
  [`30a0c72`](https://github.com/major/pcp-mcp/commit/30a0c72b4d15fa3c52eb9ba669ccb68f1cdad3da))

- Add smart_diagnose tool with LLM sampling ([#17](https://github.com/major/pcp-mcp/pull/17),
  [`22f35a2`](https://github.com/major/pcp-mcp/commit/22f35a2cc5c44a51283b25f0bf900a2b13b9fa1f))

- Upgrade to StructuredLoggingMiddleware for better observability
  ([#16](https://github.com/major/pcp-mcp/pull/16),
  [`441401f`](https://github.com/major/pcp-mcp/commit/441401fb95675a20cdb9eb27cfe7d9246978ce7d))

- **context**: Add get_client_for_host async context manager
  ([`17c46a3`](https://github.com/major/pcp-mcp/commit/17c46a3e07d9b33b7b9971fea0868aae79e764d8))

- **security**: Add TLS verification configuration options
  ([#13](https://github.com/major/pcp-mcp/pull/13),
  [`1c8a307`](https://github.com/major/pcp-mcp/commit/1c8a307b9f744c0dd9d1f2114ab286dc2c5fcfdf))

- **tools**: Add host param to metric tools
  ([`fff887d`](https://github.com/major/pcp-mcp/commit/fff887d307ca7cf052a97c08ab7d87e9db0817d3))

- **tools**: Add host param to system tools
  ([`dc077a2`](https://github.com/major/pcp-mcp/commit/dc077a2ae542b421b3950076395fc62d5326960d))


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
