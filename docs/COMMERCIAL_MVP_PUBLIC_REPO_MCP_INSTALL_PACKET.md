# Commercial MVP Public Repo MCP Install Packet

Date: 2026-05-10

Scope: A.DreamMaker / PPT Maker Commercial MVP HTML Workbench public-repo and
MCP-style installation readiness.

## Current Decision

The current public repository can be used for the existing public PPT CLI and
legacy thin MCP adapter, but it is **not yet sufficient** to install and run the
Commercial MVP HTML Workbench as the current 11-tool MCP-style beta package.

Reason:

- The public repo branch is reachable.
- The public repo `codex/phase17-render-stability` branch still exposes the
  older 6-tool `config/mcp_adapter_manifest.json`.
- The public repo branch does not contain the current
  `web/commercial-mvp-html-workbench/` surface or the internal full-beta
  runbook.
- The local internal workspace has the current 11-tool workbench/MCP package,
  but those changes are still local/ahead/dirty and have not been published to
  the public repo.

Therefore:

- Existing public CLI install: **possible**.
- Existing public MCP adapter install: **possible for legacy public CLI tools**.
- Commercial MVP HTML Workbench install from public repo: **not yet possible**.
- Commercial MVP 11-tool MCP-style install from public repo: **not yet
  possible**.

The current local workspace is now treated as a **public-install candidate**
only. It may be packaged, reviewed, committed, pushed to a public test branch,
and then validated from a clean public clone, but it must not be described as
public-repo installable before those publication and clean-clone steps happen.

## Internal Install Beta Label

Use this label for the intended next beta, after publication:

`internal_install_beta_public_repo_mcp`

This is different from:

- `internal_full_beta_rehearsal_local_preview_codex_cli`, which means a tester
  uses the same local developer workspace; and
- public closed beta, which requires deployed hosting, DNS, OAuth/account,
  payment, external host-client evidence, and approved asset/design-package
  consumption evidence.

Current status:

- Local developer rehearsal: possible.
- Local public-install candidate: **candidate ready, publication pending**.
- Public-repo MCP install beta: No-go until a reviewed candidate is committed,
  pushed to a public branch, and a clean public clone passes the gate.
- Public closed beta: No-go.

Latest local candidate evidence:

- `outputs/reports/commercial_mvp_public_repo_mcp_install_candidate.json`
- `outputs/reports/mcp_adapter_validation_public_install_candidate.json`
- `outputs/reports/commercial_mvp_html_workbench_browser_smoke_public_install_candidate.json`
- `outputs/playwright/commercial-mvp-html-workbench-public-install-candidate/`

Latest clean-copy simulation evidence:

- `outputs/public-install-candidate-clean-copy-20260510-232155/`
- `outputs/public-install-candidate-clean-copy-20260510-232155/outputs/reports/mcp_adapter_validation_clean_copy_public_install_candidate.json`
- `outputs/public-install-candidate-clean-copy-20260510-232155/outputs/reports/commercial_mvp_html_workbench_browser_smoke_clean_copy_public_install_candidate.json`
- `outputs/public-install-candidate-clean-copy-20260510-232155/outputs/playwright/commercial-mvp-html-workbench-clean-copy-public-install-candidate/`

The clean-copy simulation passed, but it is not a clean public clone and does
not prove the public branch is installable.

## Required Before Public Repo MCP Install

Before another AI can install and use the Commercial MVP workbench from the
public repo as an MCP-style local server, prepare a reviewed public-safe commit
or release branch that explicitly includes:

- `web/commercial-mvp-html-workbench/`
- `web/commercial-mvp-site/`
- `config/mcp_adapter_manifest.json`
- `scripts/mcp_adapter.py`
- `scripts/validate_mcp_adapter.py`
- `scripts/ppt_commercial_mvp_workbench.py`
- `scripts/validate_commercial_mvp_html_workbench.py`
- `scripts/validate_commercial_mvp_html_workbench_browser_smoke.js`
- `scripts/run_commercial_mvp_html_workbench_browser_smoke.ps1`
- `scripts/import_commercial_mvp_reference_designs.py`
- `scripts/validate_commercial_mvp_asset_system_internalization.py`
- `scripts/validate_commercial_mvp_cloud_oauth_readiness.py`
- `scripts/validate_commercial_mvp_internal_full_beta_boundary_scan.py`
- `system/commercial_mvp_web_site.py`
- Commercial MVP public-safe docs/specs/runbooks named in the decision packet.

Do not include:

- `PLAN.md`
- local scratch logs
- private connector state
- credentials
- raw benchmark/source content
- private asset/package internals
- generated local workspace state that contains user-machine paths
- `.env*`
- `.playwright-cli/` or `.playwright-mcp/` unless replaced by documented
  dependency setup
- `outputs/` evidence, except deliberately selected public-safe summary reports
- raw benchmark/sample files or copied benchmark/sample business copy

`PLAN.md` remains local scratch and is not a durable source of truth.

## Clean Install Commands For Another AI

After the reviewed branch has been published, a tester should start from a new
folder and run:

```powershell
git clone https://github.com/Kdreammaker/ppt-agent-public.git
cd ppt-agent-public
git checkout <public-test-branch>
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The workbench and landing builds use Node but currently have no external npm
package dependencies:

```powershell
cd web\commercial-mvp-html-workbench
npm run build
cd ..\commercial-mvp-site
npm run build
cd ..\..
```

For browser smoke, install Playwright in the clean checkout or point the runner
at an equivalent documented Node module location. A normal public checkout
should not require checked-in `.playwright-cli/` or `.playwright-mcp/` folders:

```powershell
npm install --no-save playwright
powershell -ExecutionPolicy Bypass -File scripts\run_commercial_mvp_html_workbench_browser_smoke.ps1 -Suffix public_repo_install
```

If `npm install --no-save playwright` is not acceptable for the host
environment, record that environment-specific setup as the blocker rather than
claiming the browser smoke passed.

## Minimum Public-Repo Validation Gate

After the reviewed public-safe candidate is published to a public branch, a
clean public clone must pass:

```powershell
python scripts\mcp_adapter.py --list-tools
python scripts\validate_mcp_adapter.py --report outputs\reports\mcp_adapter_validation_public_repo_install.json
python scripts\validate_commercial_mvp_html_workbench.py --report outputs\reports\commercial_mvp_html_workbench_validation_public_repo_install.json
python scripts\validate_commercial_mvp_public_site.py --report outputs\reports\commercial_mvp_public_site_validation_public_repo_install.json
python scripts\ppt_commercial_mvp_workbench.py open --report outputs\reports\commercial_mvp_workbench_open_public_repo_install.json
python scripts\ppt_commercial_mvp_workbench.py handoff --target pdf --mode assistant --report outputs\reports\commercial_mvp_workbench_handoff_pdf_public_repo_install.json
python scripts\ppt_commercial_mvp_workbench.py handoff --target pptx --mode auto --report outputs\reports\commercial_mvp_workbench_handoff_pptx_public_repo_install.json
python scripts\ppt_commercial_mvp_workbench.py host-return --return-kind final --report outputs\reports\commercial_mvp_host_ai_final_guard_public_repo_install.json
powershell -ExecutionPolicy Bypass -File scripts\run_commercial_mvp_html_workbench_browser_smoke.ps1 -Suffix public_repo_install
python scripts\validate_commercial_mvp_internal_full_beta_boundary_scan.py --report outputs\reports\commercial_mvp_boundary_scan_public_repo_install.json
```

Expected results:

- MCP manifest exposes 11 tools.
- `python scripts\mcp_adapter.py --list-tools` lists exactly the 11 tools in
  this packet.
- `open_html_workbench` returns a local workbench entrypoint.
- PDF/PPTX handoff stays honest and does not claim final export success.
- Host-AI final guard stays `awaiting_host_ai` without a safe final result
  reference.
- Asset-system posture stays `asset-system-ready`, not approved package
  consumed.
- Public/private boundary scan finds no benchmark/source/private leakage.

## MCP-Style Install Shape For Another AI

Once the public branch contains the current Commercial MVP package and the clean
clone gate passes, another AI can use the repo as a local stdio MCP server with
this shape:

```json
{
  "mcpServers": {
    "adreammaker-ppt-workbench": {
      "command": "python",
      "args": ["scripts/mcp_adapter.py", "--serve"],
      "cwd": "<path-to-cloned-ppt-agent-public>"
    }
  }
}
```

Recommended first checks from the host AI:

```powershell
python scripts\mcp_adapter.py --list-tools
python scripts\validate_mcp_adapter.py --report outputs\reports\mcp_adapter_validation_host_ai_install.json
python scripts\ppt_commercial_mvp_workbench.py open --report outputs\reports\commercial_mvp_workbench_open_host_ai_install.json
python scripts\ppt_commercial_mvp_workbench.py handoff --target pdf --mode assistant --report outputs\reports\commercial_mvp_workbench_handoff_pdf_host_ai_install.json
python scripts\ppt_commercial_mvp_workbench.py handoff --target pptx --mode auto --report outputs\reports\commercial_mvp_workbench_handoff_pptx_host_ai_install.json
python scripts\ppt_commercial_mvp_workbench.py host-return --return-kind final --report outputs\reports\commercial_mvp_host_ai_final_guard_host_ai_install.json
```

Expected tool family after publication:

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

## Interim Local-Only Option

Before publication to the public repo, another AI can only use the Commercial
MVP workbench if it is pointed at this local internal workspace or a private
bundle that contains the same files. That is not a public-repo install and must
be labeled:

`local_preview_internal_workspace_mcp`

It is acceptable for internal full beta rehearsal, but it is not proof of a
public installable package.

## Local Candidate Clean-Copy Simulation

A local clean-copy simulation may be used before publication to catch missing
candidate files. It is still not public-repo install evidence. The simulation
must:

- copy only the reviewed public-safe candidate paths into a fresh folder under
  `outputs/`;
- exclude `.git`, `.env*`, `.playwright-*`, `PLAN.md`, local logs, raw
  benchmark/sample files, private connector state, and generated evidence;
- run the same list-tools, validator, handoff, final guard, browser smoke, and
  boundary-scan commands from inside that clean copy; and
- write a public-safe summary report back to
  `outputs/reports/commercial_mvp_public_repo_mcp_install_candidate.json`.

If the simulation passes, the correct decision is:

`local_public_install_candidate_ready_publication_pending`

Do not shorten this to public-repo install Go until the public branch is
actually updated and a clean public clone passes.

## Honesty Boundaries

The MCP-style install must not imply:

- public closed beta readiness;
- deployed hosting;
- real OAuth/account/payment;
- real PDF/PPTX final export completion;
- approved asset/design-package consumption;
- benchmark/sample content reuse;
- external host-client proof unless a named host client actually installed and
  ran the public branch.
