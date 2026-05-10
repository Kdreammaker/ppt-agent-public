# Reference Pipeline Work Log

This public work log contains only public-safe Commercial MVP install-beta
coordination for this branch. Internal historical logs are intentionally not
mirrored here because they can contain machine-local paths and private evidence
references.

## 2026-05-11 Commercial MVP Public Repo MCP Install Beta Publication

Prepared the public repository branch
`codex/commercial-mvp-workbench-mcp-install-beta` for the A.DreamMaker / PPT
Maker Commercial MVP HTML Workbench and 11-tool MCP install beta.

Scope:

- Publish the Commercial MVP HTML Workbench static editor surface.
- Publish the Commercial MVP landing/account preview surface.
- Replace the legacy 6-tool MCP manifest with the current 11-tool manifest.
- Publish the thin MCP adapter and validators needed for clean-clone install
  testing.
- Keep PDF/PPTX export as host-AI handoff only; no final export success is
  claimed.
- Keep asset-system posture as ready/scaffold only; no approved package or
  approved design-package consumption is claimed.
- Keep auth/payment/deploy as preview/readiness only; no live connected flow is
  claimed.

Expected validation after push:

- workbench build passes;
- public site build passes;
- `python scripts\mcp_adapter.py --list-tools` returns exactly 11 tools;
- MCP adapter validator passes;
- workbench and public site validators pass;
- asset-system internalization validator passes;
- workbench open, PDF handoff, PPTX handoff, and final guard pass;
- browser smoke passes and proves Backspace/Delete in inspector text editing
  does not delete the selected canvas object;
- boundary scan passes.

Decision before clean public clone validation:

- Local developer rehearsal: Go.
- Public-repo MCP install beta: pending clean public clone and named MCP host
  validation.
- Internal full beta via public-repo MCP install: pending clean public clone and
  named MCP host validation.
- Public closed beta: No-go.
