# HTML Final Output Track

Date: 2026-04-22

B32 makes HTML a first-class final output path for browser sharing and presentation. It does not replace PPTX generation, and it does not make HTML the preferred human-editable artifact.

## Output Roles

- PPTX: primary local editable deck output and compatibility artifact.
- Google Slides: preferred collaborative human-editable output when a deck is imported or shared through Drive by explicit workflow.
- HTML: final browser/share/presentation output for review, lightweight delivery, and browser-native QA.
- PDF: fixed-layout review/export derivative, usually produced from PPTX by LibreOffice.
- PNG: slide preview and visual QA derivative, usually produced from rendered PDF pages.

## Contract

The HTML builder reads a validated deck spec and writes:

```text
outputs/html/<deck_id>/index.html
outputs/html/<deck_id>/html_manifest.json
```

The generated `index.html` is a single-file output with inline CSS and JavaScript. It declares:

- `<meta name="ppt-output-role" content="final_html">`
- `data-output-role="final_html"`
- `data-slide-count="<n>"`
- `data-source-spec="<repo-relative spec path>"`

The manifest declares `output_role: final_html`, the source spec path, the HTML path, slide count, asset policy, and the intended role split between browser delivery and editable outputs.

## Current Implementation

Use:

```powershell
python scripts/build_html_deck.py data/specs/business_growth_review_spec.json
python scripts/validate_html_output.py outputs/html/business_growth_review/index.html --manifest outputs/html/business_growth_review/html_manifest.json
```

Or through the wrapper:

```powershell
python scripts/ppt_system.py html data/specs/business_growth_review_spec.json --validate
```

The renderer currently starts from the deck spec rather than rendered slide images. It preserves slide order, major text slots, chart/table slot data, image placeholder intent, and icon intent metadata in a browser presentation shell. A later shared intermediate layout model can replace this without changing the public output contract.

## Browser Validation

Focused browser validation can capture a Chromium screenshot with Playwright:

```powershell
python scripts/validate_html_output.py outputs/html/business_growth_review/index.html --manifest outputs/html/business_growth_review/html_manifest.json --browser-screenshot --screenshot-path outputs/playwright/html_validation/business_growth_review.png
```

The regression gate runs the fast structural validation path so HTML remains covered without making every gate depend on browser startup.

## Guardrails

- Do not weaken PPTX package, visual smoke, design quality, or delivery gates.
- Do not depend on remote scripts, fonts, or images for generated HTML.
- Do not expose raw external asset workspace paths.
- Keep local image/font/template use opt-in through future workspace consent work.
- Treat HTML as final browser output, not as the source of truth for editable deck authoring.
