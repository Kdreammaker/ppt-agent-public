# Component System

## Status

The previous component canvas and coordinate-layout system has been retired from the active deck generation path.

Production and sample specs now use curated PowerPoint templates with stable slot identities. The active builder supports:

- `template_slide`
- `blueprint_overlay` as a compatibility alias

Do not create new decks with `component_canvas`, `component_preset`, or deleted drawing layout names.

## Current Responsibility Split

- Designers own visual structure in `assets/slides/templates/decks/*.pptx`.
- Blueprints expose editable slots and metadata in `config/template_blueprints/`.
- Specs provide content through `text_slots`, `image_slots`, `chart_slots`, and `table_slots`.
- Python selects templates, injects slot data, and validates output.

## What Replaced Components

Repeated visual patterns should be represented as reusable template slides or template slots, not Python card/label drawing.

Examples:

- Repeated cards: create a template slide with named card slots.
- Footer text: use `slot:footer_note`.
- Page labels: use a template placeholder or a future explicit `slot:page_label`.
- Charts and tables: use named chart/table slots or validated insertion helpers.

## Historical Notes

Older docs and archived plans may mention component catalogs, layout geometry, or renderer modules. Those references describe pre-Phase-2/Phase-3 migration work and are not the active authoring model.

The current product goal is a template-first PPT authoring system where reference PPTX files and curated template libraries remain the design source of truth.
