# Commercial MVP Public Repo MCP Install Packet

Date: 2026-05-11

Scope: A.DreamMaker / PPT Maker Commercial MVP HTML Workbench public-repo and MCP-style installation readiness.

## Current Decision

- Local developer rehearsal: Go.
- Public-repo MCP install beta: Go.
- Internal full beta via public-repo MCP install: Go.
- Public closed beta: No-go.

This Go decision is limited to the public-repo MCP install beta. It does not claim deployed hosting, DNS, OAuth/account, payment, production database, real PDF/PPTX final export, approved asset/design-package consumption, or public closed beta readiness.

## Public Repo Reference

- Public repo: `Kdreammaker/ppt-agent-public`
- Public branch: `codex/commercial-mvp-workbench-mcp-install-beta`
- Candidate publication commit: `2b156389a643798ddf4722f81b062fc198f682b8`

## Install Commands

```powershell
git clone https://github.com/Kdreammaker/ppt-agent-public.git
cd ppt-agent-public
git checkout codex/commercial-mvp-workbench-mcp-install-beta
python -m pip install -r requirements.txt
```

Build the workbench and public site:

```powershell
cd web\commercial-mvp-html-workbench
npm run build
cd ..\commercial-mvp-site
npm run build
cd ..\..
```

## MCP Server Config

```json
{
  "mcpServers": {
    "adreammaker-ppt-workbench": {
      "command": "python",
      "args": ["scripts/mcp_adapter.py", "--serve"],
      "cwd": "<path-to-cloned-repo>"
    }
  }
}
```

## Required First Checks

```powershell
python scripts\mcp_adapter.py --list-tools
python scripts\validate_mcp_adapter.py --report outputs\reports\mcp_adapter_validation_public_repo_clean_clone.json
python scripts\validate_commercial_mvp_html_workbench.py --report outputs\reports\commercial_mvp_html_workbench_validation_public_repo_clean_clone.json
python scripts\validate_commercial_mvp_public_site.py --report outputs\reports\commercial_mvp_public_site_validation_public_repo_clean_clone.json
python scripts\validate_commercial_mvp_asset_system_internalization.py --report outputs\reports\commercial_mvp_asset_system_internalization_public_repo_clean_clone.json
python scripts\ppt_commercial_mvp_workbench.py open --report outputs\reports\commercial_mvp_workbench_open_public_repo_clean_clone.json
python scripts\ppt_commercial_mvp_workbench.py handoff --target pdf --mode assistant --report outputs\reports\commercial_mvp_workbench_handoff_pdf_public_repo_clean_clone.json
python scripts\ppt_commercial_mvp_workbench.py handoff --target pptx --mode auto --report outputs\reports\commercial_mvp_workbench_handoff_pptx_public_repo_clean_clone.json
python scripts\ppt_commercial_mvp_workbench.py host-return --return-kind final --report outputs\reports\commercial_mvp_host_ai_final_guard_public_repo_clean_clone.json
powershell -ExecutionPolicy Bypass -File scripts\run_commercial_mvp_html_workbench_browser_smoke.ps1 -Suffix public_repo_clean_clone
python scripts\validate_commercial_mvp_internal_full_beta_boundary_scan.py --report outputs\reports\commercial_mvp_boundary_scan_public_repo_clean_clone.json
```

Expected MCP tools:

- `plan_blueprint`
- `compose_spec`
- `build_outputs`
- `patch_slide_slot`
- `validate_outputs`
- `summarize_project`
- `open_html_workbench`
- `emit_workbench_handoff`
- `validate_reference_design_recipe`
- `publish_html_viewer`
- `handle_workbench_return`

## Named Host Evidence

Named host used for install proof: Codex CLI local stdio MCP host harness.

Minimum host path validated:

- `tools/list` returned 11 tools.
- `open_html_workbench` returned the local workbench entrypoint.
- `emit_workbench_handoff` passed for PDF.
- `emit_workbench_handoff` passed for PPTX.
- `validate_reference_design_recipe` passed and stayed content-free.
- `publish_html_viewer` passed for Free.
- `publish_html_viewer` passed for Paid.
- `handle_workbench_return` with `return_kind=final` and no safe result ref stayed `awaiting_host_ai`.

## Honesty Boundaries

- PDF/PPTX export remains handoff/awaiting-host-AI only unless a real safe final result reference exists.
- Asset-system posture remains asset-system-ready/scaffold only; no approved package or approved design-package consumption is claimed.
- Landing/account/payment/deploy surfaces are preview/local only; no live connected flow is claimed.
- Benchmark files are quality references only and are not included as raw files in this branch.
- Public closed beta remains No-go.
