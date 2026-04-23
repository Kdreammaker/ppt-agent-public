# Invite Beta Install And First Run

This beta uses the CLI as the primary product surface. In short: CLI primary surface, MCP thin adapter, no standalone exe. MCP is a thin adapter over the same CLI/package APIs. A standalone `.exe` installer is not required for this beta.

## Requirements

- Python 3.11 or newer.
- The Python packages checked by `ppt-agent healthcheck`, including `python-pptx`, `Pillow`, `PyMuPDF`, and `pydantic`.
- PowerShell on Windows for the documented command examples.
- Optional: Node.js, npx, LibreOffice, and Korean/CJK fonts for preview or local tooling workflows.

## First Run

```powershell
ppt-agent init --workspace .\ppt-workspace
ppt-agent healthcheck --workspace .\ppt-workspace
```

The healthcheck writes:

- `.ppt-agent/healthcheck.json` for tools and support.
- `reports/healthcheck.md` for human-readable setup guidance.

Local-only mode works without a workspace code. Workspace-code activation is used only for private beta entitlements such as private package access.

## Workspace Code

Workspace codes are stored locally only as a hash and mask. Raw codes should not appear in CLI output, reports, screenshots, support bundles, Slack messages, or Git.

Use the entitlement command only when private beta access is required:

```powershell
ppt-agent gateway activate --workspace .\ppt-workspace --workspace-code <workspace-code>
ppt-agent gateway status --workspace .\ppt-workspace
```

If activation is denied, expired, revoked, rotated, malformed, or unavailable, local-only CLI features should continue to work.
