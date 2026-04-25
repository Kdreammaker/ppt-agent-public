# Auto Mode Playbook

Auto Mode is a plan-first, non-interruptive production path. It creates a deck plan, records assumptions, composes a spec from that plan, renders, reviews, and revises within a bounded pass count.

Public files define stages, artifact names, and blocking categories only. Private prompt wording, ranking weights, template decisions, and asset backend execution stay outside the public repository.

## Required Runtime Evidence

- `deck_plan_ref`
- `assumptions_ref`
- `stage_artifacts`
- `revision_decision`

## Blocking Conditions

Auto Mode may proceed without user interruption unless intake validation, query governance, rendering, quality review, or delivery gates block the run.
