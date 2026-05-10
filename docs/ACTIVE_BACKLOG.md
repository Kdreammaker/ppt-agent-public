# Active Backlog

This public backlog is the public-safe coordination entrypoint for the
Commercial MVP HTML Workbench MCP install beta branch.

## Current Public Test Branch

- `codex/commercial-mvp-workbench-mcp-install-beta`

## Current Decision

- Local developer rehearsal: Go.
- Public-repo MCP install beta: pending clean public clone and named MCP host validation on this branch.
- Internal full beta via public-repo MCP install: pending the same branch validation.
- Public closed beta: No-go.

## Public Install Candidate Scope

This branch is intended to publish the public-safe Commercial MVP HTML
Workbench, public landing preview, and 11-tool MCP adapter candidate so another
AI can clone the public repo and attach it as a local stdio MCP server.

Included candidate families:

- `web/commercial-mvp-html-workbench/`
- `web/commercial-mvp-site/`
- `config/mcp_adapter_manifest.json`
- `scripts/mcp_adapter.py`
- Commercial MVP workbench, MCP, browser smoke, public site, asset-system, and boundary validators
- `system/commercial_mvp_web_site.py`
- Commercial MVP public-safe docs, specs, runbooks, and golden-path notes

Excluded from the public candidate:

- local scratch plans and logs
- local environment files
- local browser automation caches
- private connector state
- credentials or private prompts
- raw source payloads
- raw benchmark/sample files
- broad local evidence outputs
- machine-local workspace state

## Remaining Gate Before Go

The branch can become Go only after:

1. the public branch is pushed;
2. a fresh public clone of this branch passes builds, validators, browser smoke,
   and boundary scan;
3. the fresh clone lists exactly 11 MCP tools; and
4. a named MCP host runs the minimum golden path from the fresh clone.

`PLAN.md` is not a source of truth and is not part of the public install beta.
