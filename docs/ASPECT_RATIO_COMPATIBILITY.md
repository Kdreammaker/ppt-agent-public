# Aspect Ratio Compatibility

Date: 2026-04-19

## Current Status

Production support is currently verified for `16:9` template-first decks.

The current curated template libraries under `assets/slides/templates/decks/` are audited by:

```powershell
python scripts/inspect_template_aspect_ratios.py
```

The audit writes:

- `outputs/reports/template_aspect_ratio_audit.json`
- `outputs/reports/template_aspect_ratio_audit.md`

Responsive/aspect-aware blueprint readiness is documented in `docs/RESPONSIVE_BLUEPRINT_CONTRACT.md` and audited by:

```powershell
python scripts/analyze_responsive_blueprint_readiness.py
```

That diagnostic writes:

- `outputs/reports/responsive_blueprint_readiness.json`
- `outputs/reports/responsive_blueprint_readiness.md`

## 16:9 Policy

`16:9` is supported when both conditions are true:

- curated template libraries are `16:9`
- generated decks render as `16:9`

The current deck builder uses a fixed `13.33 x 7.5` inch canvas, which matches widescreen `16:9`.

The regression gate includes a runtime smoke test that confirms `16:9` remains accepted and `4:3` requests fail fast until dedicated assets exist.

## 4:3 Policy

`4:3` should be treated as unsupported for production unless dedicated `4:3` template libraries and aspect-specific blueprints exist.

Do not claim `4:3` compatibility by stretching, cropping, or resizing existing `16:9` templates. That can corrupt composition, slot geometry, and visual smoke expectations.

If a caller requests `4:3` before dedicated support exists, the production behavior should fail fast with a clear message:

```text
4:3 output requires dedicated 4:3 template libraries and aspect-specific blueprints.
```

## Required Work For Real 4:3 Support

Real `4:3` support requires:

- curated `4:3` source PPTX libraries
- aspect-ratio-aware template selection
- blueprint bounds generated from the `4:3` libraries
- separate visual smoke baselines or previews
- explicit regression coverage for at least one `4:3` deck

Until then, the system should preserve high-quality `16:9` output instead of producing distorted `4:3` decks.

## 9:16 Policy

`9:16` vertical output is also unsupported for production. It requires dedicated vertical templates, typography/density rules, aspect-specific blueprints, and separate visual baselines. Do not infer `9:16` support from any future `4:3` work.
