# CLI And MCP Golden Path

The first beta path is local and file-based:

```powershell
python scripts\ppt_cli_workspace.py init --workspace .\ppt-workspace
python scripts\ppt_cli_workspace.py healthcheck --workspace .\ppt-workspace
python scripts\ppt_system.py blueprint .\ppt-workspace\intake\example.json --kind intake --approval-mode assistant
python scripts\ppt_system.py compose-spec .\ppt-workspace\intake\example.json --output .\ppt-workspace\specs\example.json
python scripts\ppt_system.py build-outputs .\ppt-workspace\specs\example.json --validate --report-dir .\ppt-workspace\reports --html-output .\ppt-workspace\html\example.html
python scripts\ppt_system.py patch-spec .\ppt-workspace\specs\example.json --slide 3 --text-slot title --value "Updated title" --dry-run
python scripts\ppt_cli_history.py history --workspace .\ppt-workspace
python scripts\ppt_cli_history.py rollback --workspace .\ppt-workspace --run-id <run-id>
```

Assistant Mode shows the ASCII structure blueprint by default and should wait for an explicit approve, revise, continue, skip, or `--build-approved` decision before final PPTX/HTML generation. Auto Mode skips the blueprint checkpoint by default unless a workflow explicitly requests it. The ASCII blueprint is not a visual preview; use HTML/PPTX preview or rendered thumbnails for visual approval.

## Commercial MVP HTML Workbench

The Commercial MVP HTML workbench is a local fixed-canvas editor surface, not a
separate renderer. From a clean checkout, use:

```powershell
python scripts\ppt_commercial_mvp_workbench.py open
```

The command returns the tracked entrypoint
`web/commercial-mvp-html-workbench/index.html`, Assistant as the default mode,
Auto as the only alternate mode, and whether the current deck is fixture-only.
The current PC-first editor shell keeps the 1600x900 canvas centered in a
measured viewport, with slide rail and inspector as supporting panels. The
toolbar exposes text role/font/size/color/bold/bullet/alignment, duplicate,
delete, z-order, align/distribute, fixed shape/image rotate/flip, shape radius,
zoom/fit, add-text, and add-shape controls. The published viewer uses the same
1600x900 object model in read-only mode: Free links show attribution and Paid
links are watermark-free.

To emit honest host-AI export hooks without claiming final files:

```powershell
python scripts\ppt_commercial_mvp_workbench.py handoff --target pdf --mode assistant --report outputs\reports\commercial_mvp_workbench_handoff_pdf.json
python scripts\ppt_commercial_mvp_workbench.py handoff --target pptx --mode auto --report outputs\reports\commercial_mvp_workbench_handoff_pptx.json
```

These reports contain sanitized work-state references and design-package safe
ids only. They must not include raw source material, local paths, raw filenames,
external document identifiers, credentials, package internals, or final PDF/PPTX binary data.

Reference Design Library, published viewer, and host-AI return scaffolds use the
same local helper:

```powershell
python scripts\ppt_commercial_mvp_workbench.py design-recipe --report outputs\reports\commercial_mvp_reference_design_recipe.json
python scripts\ppt_commercial_mvp_workbench.py viewer --plan free --report outputs\reports\commercial_mvp_published_viewer_free.json
python scripts\ppt_commercial_mvp_workbench.py viewer --plan paid --report outputs\reports\commercial_mvp_published_viewer_paid.json
python scripts\ppt_commercial_mvp_workbench.py host-return --return-kind proposal --report outputs\reports\commercial_mvp_host_ai_proposal_return.json
python scripts\ppt_commercial_mvp_workbench.py host-return --return-kind final --return-ref host-result-safe-ref-demo --report outputs\reports\commercial_mvp_host_ai_final_return.json
```

`host-return --return-kind final` must stay in `awaiting_host_ai` unless the
return ref starts with a safe host-result reference. The Reference Design
Library command emits design-only recipe payloads; it never asks the product
server to store original PPTX/PDF/HTML files or source slide content.

Style Memory, Reference Design Library, safe asset/design packages, and viewer
metadata are currently local/preview posture unless a later approved cloud work
unit connects Supabase Auth, payment, Vercel hosting, and the Cloudflare
gateway. Asset-system alignment is limited to already-approved-result safe
manifest/theme/layout/component/font/license metadata; raw reference assets,
raw paths, package internals, approval logs, and assetization workflows are not
part of the workbench or MCP handoff surface.

## Internal Full Beta Host-AI Gate

Before internal full beta, this golden path must be exercised through a named
host client, not only direct local helper scripts. The evidence must include
workbench open, PDF/PPTX handoff, Reference Design Library validation,
published viewer Free/Paid checks, proposal return handling, and final-return
guard behavior.

Reference Design Library summaries must report content-free status consistently
across CLI, MCP, UI, and reports. Current recipes may use either
`content_free_preview.placeholder_labels_only` or
`synthetic_placeholder_preview.placeholder_labels_only`; both shapes count as
content-free when the flag is true. If `content_free_only=false` is emitted for
the current content-free recipe schema, the run is blocked and must not be used
as host-AI install evidence.

## Route Matrix

| Route | Assistant Mode | Auto Mode |
| --- | --- | --- |
| `python scripts\ppt_make.py` | Natural-language first-run wrapper. It writes planning artifacts and `ppt_make_report.json`, returns `status=waiting_for_approval`, and only renders final PPTX/HTML after `--build-approved` or `--continue-build`. | Natural-language fast draft route; builds immediately. |
| `python scripts\ppt_agent.py` | Guide-packet/sparse-prompt route. It plans first by default and requires `--build-approved` for final files. | Builds two strategy-routed variants. |
| `python scripts\ppt_agent_mcp_adapter.py` | `deck_plan_compose` plans unless `build_approved=true`. | `two_variant_auto_build` renders variants. |

## Outputs

- PPTX: editable enterprise handoff.
- HTML: browser presentation and review output.
- Reports: validation, rationale, healthcheck, support, gateway summary, and audit outputs.

## MCP

MCP remains a developer-preview companion surface. It must call the same CLI/package APIs and return compact structured results, paths, and report summaries. It must not implement a separate renderer, composer, upload path, or workspace scanner.

Host-AI install testing is still local/preview unless a separate run records an
actual install against a named host client. The manifest must expose exactly the
11 tools below.

Public-repo status as of 2026-05-10: the public repo can install the older
public CLI/MCP toolset, but it does not yet contain the current Commercial MVP
HTML Workbench package or 11-tool manifest. Treat public-repo MCP install for
the Commercial MVP workbench as not ready until
`docs/COMMERCIAL_MVP_PUBLIC_REPO_MCP_INSTALL_PACKET.md` passes from a clean
public clone. A passing local clean-copy simulation may support publication
readiness, but it is still not proof that another AI can install from the
public repo.

For the intended internal install beta after publication, the host MCP config
shape is:

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

First checks in that clean clone:

```powershell
python scripts\mcp_adapter.py --list-tools
python scripts\validate_mcp_adapter.py --report outputs\reports\mcp_adapter_validation_public_repo_install.json
python scripts\ppt_commercial_mvp_workbench.py open --report outputs\reports\commercial_mvp_workbench_open_public_repo_install.json
```

Expected MCP tools are high-level wrappers such as:

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

## Public-Repo MCP Install Beta Status

Branch codex/commercial-mvp-workbench-mcp-install-beta is validated for the Commercial MVP 11-tool MCP install beta. Use the MCP server config in docs/COMMERCIAL_MVP_PUBLIC_REPO_MCP_INSTALL_PACKET.md. Public closed beta remains No-go.
