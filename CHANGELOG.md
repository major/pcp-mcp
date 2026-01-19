# Changelog

All notable changes to this project will be documented in this file.

This project uses [Semantic Versioning](https://semver.org/) and [Conventional Commits](https://www.conventionalcommits.org/).

## Unreleased

### Feat

- add automated semantic versioning and PEP 561 typed package support
- add FastMCP 2.0 features (icons, caching, sampling) (#17)
- add MCP tool annotations, structured logging, and output schemas (#16)
- add FastMCP progress reporting and resource templates (#15)
- add audit logging middleware for MCP requests (#14)
- **security**: add TLS verification configuration options (#13)
- **tools**: add host param to system tools
- **tools**: add host param to metric tools
- **context**: add get_client_for_host async context manager

### Fix

- disable build in semantic-release, use pypi job instead
- add type assertions to narrow context types for ty check
- **security**: add host allowlist to prevent SSRF via host parameter (#12)
- **tools**: resolve Pydantic annotation evaluation error
- remove 'from __future__ import annotations' from tools modules
- **ci**: pass CODECOV_TOKEN to codecov action

### Refactor

- align Claude code review with project guidelines
- use @computed_field for settings properties (#21)
- use cachetools TTLCache for metric caching (#19)
- remove unused handle_pcp_errors decorator (#18)

## v0.1.0 (2026-01-18)

### Feat

- add guided diagnostic prompts for common troubleshooting workflows
- add browsable catalogs for common metrics and namespaces
- add comprehensive LLM guidance to MCP server instructions
- add MCP resources for health and metric discovery
- add clumped system tools (snapshot, process top)
- add fetch_with_rates for counter metric rate calculation
- add snapshot and process response models
- add core metric tools (query, search, describe)
- add tools and resources registration stubs
- add core MCP server framework
- add project configuration and build setup

### Fix

- **docs**: correct module references in API docs
- use Python 3.10 compatible imports for Self and UTC
- add future annotations for Python <3.14 compatibility
- calculate actual memory usage excluding cache/buffers
- handle both float and dict timestamp formats
- use integer keys for load metric instances
- convert instance IDs to strings in query_metrics
- handle pmproxy context expiration with auto-retry
