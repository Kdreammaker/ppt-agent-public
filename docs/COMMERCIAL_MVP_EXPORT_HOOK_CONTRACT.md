# Commercial MVP Export Hook Contract

## Purpose

This contract defines how `Export PDF` and `Export PPTX` work in the Commercial
MVP. These buttons are host-AI handoff hooks. They are not local fake export
completion buttons.

## User Intent

When the user clicks `Export PDF` or `Export PPTX`, they are asking host AI to
create the final deliverable from the current edited work.

PPT Maker's job is to prepare a safe request, track status honestly, and present
the result or blocker.

## Required Request Envelope

The handoff envelope must include:

- envelope version.
- target export kind: `pdf` or `pptx`.
- safe project id/label.
- safe deck id/label.
- selected slide id or all-slides scope.
- Assistant/Auto mode.
- design-guide version.
- sanitized work-state reference or compact sanitized work state.
- sanitized operation summary.
- proposal statuses where relevant.
- quality requirements.
- account/credit/entitlement posture where needed.
- asset-system request posture where needed.

## Forbidden Envelope Content

The envelope must not include:

- raw prompt text unless explicitly allowed for local-only debug.
- private source text.
- local paths.
- raw filenames.
- Drive/Docs IDs or URLs.
- package internals.
- credentials or token-like values, service keys, DB URLs, or connection strings.
- raw browser DOM dumps.
- encoded asset assets.
- private image URLs.
- backend chain-of-thought.
- full binary PPTX/PDF content.

## Status Model

Allowed user-facing states:

- `handoff_ready`
- `handoff_sent`
- `awaiting_host_ai`
- `proposal_ready`
- `blocked`
- `final_received`

Blocked or rejected states must explain the blocker in public-safe language.

Do not show `complete` unless an actual final PDF/PPTX result has been received
or a real host-AI result reference exists.

## Proposal Handling

Host AI may return a bounded proposal rather than a final file. PPT Maker may:

- preview the proposal.
- apply a bounded patch.
- reject the proposal.
- mark the request blocked.

Proposal application must mutate the local work state and append a sanitized
operation summary. Rejection must not mutate the work state.

## Evidence

Each export-hook smoke must prove:

- PDF and PPTX buttons are visible.
- each button creates an envelope with the correct target export kind.
- forbidden fields are absent.
- status transitions are honest.
- blocked state does not expose private values.
- fake fixture completion is not presented as a real final deliverable.

## Acceptance

The hook is acceptable only when a browser smoke can click both export buttons
and verify the status flow without claiming final output unless a real result
exists.
