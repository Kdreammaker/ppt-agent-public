# LLM Summarization Guardrail

Implementation status: implemented as an opt-in mockable provider path with an optional OpenAI Responses API adapter. Deterministic cutoff remains the default and the regression gate explicitly disables LLM summarization.

This design keeps the current deterministic cutoff behavior as the default fallback while adding an optional LLM summarization step for over-budget template text slots.

## Goal

When a `text_slots` value exceeds the slot budget, the deck builder should try to produce a shorter meaning-preserving summary before falling back to deterministic truncation.

The guardrail must never allow an LLM response to bypass the same slot budget checks that protect generated decks today.

## Current Behavior

`system/template_engine.py` resolves a slot budget with `slot_text_budget()` and enforces it in `coerce_text_to_slot_budget()`.

If text exceeds `max_chars_per_line * max_lines`, the current code truncates the value, appends `...`, and records an overflow event with:

- `slot`
- `budget`
- `original_chars`
- `truncated_chars`
- `original_preview`
- `truncated_text`
- slide and template metadata added by `render_template_slide()`

## Proposed Flow

1. Resolve the slot budget from the template blueprint plus `slot_overrides`.
2. If text already fits, write it unchanged.
3. If text exceeds budget and LLM summarization is disabled, use the existing deterministic cutoff.
4. If LLM summarization is enabled, send a constrained summarization request with:
   - original text
   - hard character budget
   - slot name
   - slide/template context
   - instruction to preserve numbers, names, dates, and product terms
5. Validate the LLM output locally before writing it:
   - must be non-empty
   - must be within budget
   - must not introduce unsupported line breaks for the slot strategy
   - must preserve protected tokens when the slot defines them
6. If validation passes, write the LLM summary.
7. If the LLM is unavailable, invalid, empty, too long, or times out, use the existing deterministic cutoff.
8. Record the outcome in the overflow event.

## Event Schema Extension

Extend each overflow event with these optional fields:

- `resolution`: `llm_summary`, `deterministic_cutoff`, or `unchanged`
- `llm_attempted`: boolean
- `llm_used`: boolean
- `llm_model`: model identifier when available
- `llm_latency_ms`: integer when available
- `fallback_reason`: short machine-readable reason when deterministic cutoff is used after an LLM attempt
- `summary_chars`: final written character count

Existing fields should remain stable so current reports and regression checks continue to work.

## Configuration

Use an explicit opt-in configuration so CI and local deterministic runs remain stable:

- Environment variable: `PPTX_ENABLE_LLM_SUMMARY=1`
- Optional timeout: `PPTX_LLM_SUMMARY_TIMEOUT_MS`, default `3000`
- Mock all slots for local verification: `PPTX_LLM_SUMMARY_MOCK_TEXT`
- Mock per slot for local verification: `PPTX_LLM_SUMMARY_MOCK_JSON`
- Provider selection: `PPTX_LLM_SUMMARY_PROVIDER=mock` or `PPTX_LLM_SUMMARY_PROVIDER=openai`
- OpenAI model override: `PPTX_LLM_SUMMARY_MODEL`
- OpenAI endpoint override: `PPTX_OPENAI_RESPONSES_URL`

When the environment variable is absent, the behavior must match the current deterministic path.

Provider note: the OpenAI adapter is still fully behind the same local validation interface. Missing credentials, HTTP errors, timeout, empty output, protected-token loss, line-break violations, or over-budget output all fall back to deterministic cutoff.

## Implementation Touchpoints

- Add a small summarization provider interface near `system/template_engine.py` or in a new `system/text_summarizer.py`.
- Keep `coerce_text_to_slot_budget()` as the final enforcement point.
- Add a pre-cutoff hook that can return a candidate summary before deterministic truncation.
- Update text overflow reports to include the extended event fields.
- Update `scripts/run_regression_gate.py` to keep asserting the deterministic baseline with LLM summarization disabled.
- Keep runtime smoke coverage in `scripts/test_llm_summary_guardrail.py`.

## Local Verification

Run the guardrail unit smoke:

```powershell
python scripts/test_llm_summary_guardrail.py
```

Run a mocked enabled deck build:

```powershell
$env:PPTX_ENABLE_LLM_SUMMARY='1'
$env:PPTX_LLM_SUMMARY_MOCK_JSON='{"title":"Budget-valid summary"}'
python scripts/build_deck.py data/specs/report_auto_selection_sample.json
```

## Acceptance Criteria

- With LLM summarization disabled, regression output is unchanged.
- With LLM summarization enabled and a valid summary returned, over-budget text is replaced by a budget-valid summary.
- If the LLM returns text over budget, empty text, or an error, the deterministic cutoff is used.
- Overflow reports identify whether the LLM was attempted and whether the final text came from summary or cutoff.
- No generated deck writes over-budget text into a template slot.
