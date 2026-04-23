# Slide Feedback Loop

`config/slide_feedback_memory.json` is the source of truth for reusable slide-by-slide review feedback. It captures which candidate slide won, why it won, and whether a future Composer run should reuse a source slide or regenerate an editable Composer slide.

This keeps comparison feedback out of one-off manual deck edits. A future intake can match a memory by deck name, setting, or source material path, then apply the stored policy during spec composition.

Current policy rules:

- Source decks are not raw reference inputs by default. A source slide is reused only when a matched feedback memory explicitly lists it in `source_deck_policy.reuse_source_slides` or marks the slide winner as `source`.
- Composer-generated visuals should remain editable when the memory asks for editable visuals.
- Appendix-like slides should be structurally distinct from body slides when generated.
- Feedback validation is advisory to generation quality, but the memory file itself is validated by `scripts/validate_slide_feedback_memory.py` and the regression gate.

For the Korea Q2 seasonal seafood guide, the stored comparison keeps Composer slides 1, 4, 5, and 6, and reuses the V2 source slides 2, 3, 7, 8, and 9.
