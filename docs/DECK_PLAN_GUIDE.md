# Deck Plan Guide

The production path is `intake -> deck_plan -> deck_spec -> render`. The deck plan is a reviewable intent artifact created before slide content is written into template slots.

## Required Artifacts

- `outputs/projects/<project_id>/plans/deck_plan.json`
- `outputs/projects/<project_id>/plans/deck-plan-markdown`
- `outputs/reports/<project_id>_plan_traceability.json`

## Public Boundary

Public plans may contain request goals, table of contents, slide messages, content budgets, public-safe asset intent summaries, assumptions, and approval state. They must not contain private prompt text, raw connector payloads, raw ranking scores, private registry paths, local absolute paths, Drive IDs, approval records, tokens, or user-upload source attachment paths.

## Mode Behavior

Auto Mode records assumptions and proceeds when the plan does not cross a blocking gate. Assistant Mode records the same plan, then requires the configured approval checkpoints before final build when review is requested.
