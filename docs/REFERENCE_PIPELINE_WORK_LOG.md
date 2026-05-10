# Reference Pipeline Work Log

This public work log contains only public-safe Commercial MVP install-beta coordination for this branch. Internal historical logs are intentionally not mirrored here because they can contain machine-local paths and private evidence references.

## 2026-05-11 Commercial MVP Public Repo MCP Install Beta Go

Published and validated the Commercial MVP HTML Workbench / Landing / 11-tool MCP install beta candidate on public repo branch codex/commercial-mvp-workbench-mcp-install-beta.

Scope:

- Published the Commercial MVP HTML Workbench static editor surface.
- Published the Commercial MVP landing/account preview surface.
- Replaced the legacy 6-tool MCP manifest with the current 11-tool manifest.
- Published the thin MCP adapter and validators needed for clean-clone install testing.
- Kept PDF/PPTX export as host-AI handoff only; no final export success is claimed.
- Kept asset-system posture as ready/scaffold only; no approved package or approved design-package consumption is claimed.
- Kept auth/payment/deploy as preview/readiness only; no live connected flow is claimed.

Validation result:

- Workbench build passed.
- Public site build passed.
- python scripts\mcp_adapter.py --list-tools returned exactly 11 tools.
- MCP adapter validator passed.
- Workbench and public site validators passed.
- Asset-system internalization validator passed.
- Workbench open, PDF handoff, PPTX handoff, and final guard passed.
- Browser smoke passed and proved Backspace/Delete in inspector text editing does not delete the selected canvas object.
- Boundary scan passed.
- Named host MCP golden path passed through Codex CLI local stdio MCP host harness.

Decision:

- Local developer rehearsal: Go.
- Public-repo MCP install beta: Go.
- Internal full beta via public-repo MCP install: Go.
- Public closed beta: No-go.
