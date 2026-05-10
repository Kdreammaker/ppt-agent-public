# Commercial MVP Internal Full Beta Runbook

Date: 2026-05-10

Scope: local/preview internal full beta rehearsal for the A.DreamMaker / PPT
Maker HTML Workbench and landing surfaces.

Authoritative decision: use
`docs/COMMERCIAL_MVP_INTERNAL_FULL_BETA_DECISION_PACKET.md`. Internal full beta
rehearsal is Go only for the local/preview Codex CLI path. Public closed beta is
No-go. The separate internal install beta where another AI clones the public
repo and attaches the 11-tool MCP package is also No-go until the public branch
is updated and clean-clone validation passes.

## Tester Setup

- This is **not** a public closed beta. It is a local/preview internal rehearsal
  to see whether testers can use the workbench before any public distribution.
- Use the local preview workbench and site only.
- Do not treat this as public launch, public closed beta, deployed hosting,
  connected OAuth/payment, external host-client install proof, or approved
  asset/design-package consumption proof.
- Record evidence under:
  `outputs/playwright/commercial-mvp-html-workbench-pre-full-beta-last-check/`
  and `outputs/reports/*pre_full_beta_last_check*.json` for the latest last
  check.

## Before Testers Start

- Confirm the latest decision is still: internal full beta local/preview
  rehearsal Go, public closed beta No-go.
- Build the workbench and landing once.
- Run the one-command browser smoke runner from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_commercial_mvp_html_workbench_browser_smoke.ps1 -Suffix pre_full_beta_last_check
```

- Confirm the runner reports `commercial_mvp_html_workbench_browser_smoke=valid`.
- Open the gallery and dashboard:
  `outputs/playwright/commercial-mvp-html-workbench-pre-full-beta-last-check/index-pre_full_beta_last_check.html`
  and
  `outputs/playwright/commercial-mvp-html-workbench-pre-full-beta-last-check/go-no-go-dashboard-pre_full_beta_last_check.html`.
- Confirm payment, login, deployment, external host-client install, and approved
  design-package/asset consumption are still described as preview or not proven.
- If a tester wants to connect another AI through MCP, use only the local
  workspace during this rehearsal and label it
  `local_preview_internal_workspace_mcp`. Do not call it a public-repo install
  until `docs/COMMERCIAL_MVP_PUBLIC_REPO_MCP_INSTALL_PACKET.md` is satisfied
  from a clean public clone.
- If the next tester is expected to install from the public repo, stop and use
  the public install packet instead. That path is currently
  `publication_pending`, not Go.

## Stop Criteria

- P1: tester cannot open the workbench, cannot interact with the canvas, or sees
  private paths, token-like values, raw benchmark/source content, raw image URLs, external document identifiers,
  fake final export success, or approved package consumption claims.
- P2: core editing, drawer, viewer, language, or export handoff flows are
  confusing or broken enough that most testers cannot complete a scenario.
- P3: visible copy or layout friction that does not block task completion. Keep
  it in backlog unless multiple testers hit the same friction.

Examples:

- P1 example: Export says a real PDF/PPTX was completed even though no host-AI
  result reference exists.
- P1 example: A local file path, token-like value, raw benchmark text, raw image
  URL, or external document identifier appears in the UI, report, or handoff summary.
- P2 example: a tester cannot close a drawer with Escape, cannot return focus,
  or cannot continue editing after closing it.
- P2 example: generated IR/Sales/Portfolio states do not load or appear to
  overwrite the sample deck boundary.
- P3 example: a label is understandable but awkward, or a control needs clearer
  wording after tester feedback.

## Minimum Notes During Testing

For every issue, record only these fields unless more detail is needed:

- Scenario name.
- Severity: P1, P2, or P3.
- What the tester tried.
- What happened.
- Browser width and language.
- Screenshot path or report path.
- Whether it affects export honesty, private data, benchmark content,
  asset-system claims, login/payment/deploy preview honesty, or normal editing.

## Tester Task Checklist

| Scenario | Success criteria | Record on failure |
| --- | --- | --- |
| Open generated IR, Sales, and Portfolio work-states | Each state loads through the generated work-state path, shows `fixture=false` in evidence, keeps safe design/theme/export/asset summaries, and does not replace fixture metadata with benchmark/source content. | Family name, visible error, report path, screenshot, whether fixture/source markers appeared. |
| Master Style apply, lock, reset | Tester can preview/apply deck-level style, lock style changes, and reset to baseline without using the right inspector. | Which control failed, current lock state, selected slide/object, screenshot. |
| Reference Design Library apply and reset | IR/Sales/Portfolio recipe cards are understandable; applying/resetting changes only content-free recipe/style references and never source text, coordinates, filenames, screenshots, or image URLs. | Recipe family, before/after copy, any source-like content shown, screenshot. |
| Style Memory save/delete/restore posture | Tester can see Style Memory, reset it, delete it, and understand it is separate from undo/redo and AI revision memory. | Action taken, expected vs actual copy, whether deletion/reset was confirmed. |
| Direct text edit, move, resize, align, arrange, z-order | Double-click text editing commits; objects move and resize; duplicate/delete works; multi-select align/distribute works; bring forward/send backward works. | Object type, slide number, action, expected vs actual geometry, screenshot. |
| Shape/image rotation, flip, radius | Shape/image rotation and flip work; shape radius can be changed; text boxes remain rotation-disabled. | Object type, transform attempted, actual transform/style shown. |
| PDF/PPTX export handoff | Export status moves from `handoff_ready` to `handoff_sent` / `awaiting_host_ai`; no final success or real file claim appears without a safe host-AI final result reference. | Target PDF/PPTX, status text, any final/downloaded/completed wording, report path. |
| Free/Paid published viewer | Viewer is read-only, scales without clipping at narrow and desktop widths, Free shows attribution/watermark posture, Paid is watermark-free. | Plan, viewport width, clipping/scroll state, watermark/read-only evidence. |
| KO/EN language switch | KO chrome has Korean copy without raw status slugs; EN chrome has English copy without Korean leftovers. | Surface, language, untranslated/raw text, screenshot. |
| Landing/account/payment preview copy | Landing and account surfaces describe local preview/auth/payment honestly; no real connected signup, OAuth, billing, or production payment is implied. | Page, copy that implied live behavior, screenshot. |

## Issue Template

- Severity: P1 / P2 / P3
- Scenario:
- Steps:
- Expected:
- Actual:
- Screenshot/report path:
- Browser width:
- Locale:
- Work-state family, if relevant:
- Export target/status, if relevant:
- Boundary concern: export honesty / benchmark content / asset-system claim /
  private path or token / auth-payment preview / other

## Current Rehearsal Decision

- Internal full beta local/preview rehearsal: Go if the latest
  `pre_full_beta_last_check` evidence has no open P1/P2.
- Public closed beta: No-go until deployment, DNS, OAuth/account/payment,
  external host-client install or deployed remote host evidence, approved
  asset/design-package consumption evidence, and stronger commercial deck
  quality evidence are separately approved and recorded.

## End Of Test Decision

- Keep internal full beta Go if testers can complete the checklist and no open
  P1/P2 remains.
- Change internal full beta to No-go if any P1 remains, or if a P2 blocks
  repeated completion of a core scenario.
- Keep public closed beta No-go unless a separate approved work unit proves live
  hosting, DNS, OAuth/account/payment, external host-client or deployed host
  integration, approved asset/design-package consumption, and commercial deck
  quality.
- Record P3 issues in `docs/ACTIVE_BACKLOG.md` or
  `docs/REFERENCE_PIPELINE_WORK_LOG.md` only when they are repeated or likely to
  affect the next tester group.

## MCP-Style Local Rehearsal Note

For internal rehearsal only, an AI host may point an MCP stdio config at the
local workspace:

```json
{
  "mcpServers": {
    "adreammaker-ppt-workbench": {
      "command": "python",
      "args": ["scripts/mcp_adapter.py", "--serve"],
      "cwd": "<local-internal-workspace>"
    }
  }
}
```

Before using it, run:

```powershell
python scripts\mcp_adapter.py --list-tools
python scripts\validate_mcp_adapter.py --report outputs\reports\mcp_adapter_validation_local_mcp_rehearsal.json
```

Expected: 11 tools. If the host sees only the older 6-tool manifest, it is
pointing at the public repo or an outdated checkout rather than the current
local Commercial MVP package.

## Public-Repo Install Beta Note

Do not use this runbook alone to start the public-repo install beta. That beta
requires:

- a reviewed public-safe candidate file list;
- commit/push approval and public test branch publication;
- clean public clone validation using the commands in
  `docs/COMMERCIAL_MVP_PUBLIC_REPO_MCP_INSTALL_PACKET.md`; and
- a named external AI host install record after publication.

Until those exist, the decision is:

- local developer rehearsal: Go if no open P1/P2 exists;
- public-repo MCP install beta: No-go, candidate/publication pending;
- public closed beta: No-go.
