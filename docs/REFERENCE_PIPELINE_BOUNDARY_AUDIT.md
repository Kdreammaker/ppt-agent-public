# Reference Pipeline Boundary Audit

Date: 2026-04-21

## Scope

This audit records the active folder contract before the reference pipeline adds canonical IDs, metadata, promotion automation, graph artifacts, pattern catalogs, and mode policies.

## Active Paths

- `assets/slides/references`: raw external and generated reference PPTX inputs. Files here are never production templates by presence alone.
- `assets/slides/categorizing`: ignored split/classification workspace for PNG previews, one-slide PPTX candidates, inventories, labels, and draft metadata.
- `assets/slides/library`: finalized `good`, `normal`, and `weak` reference records. This is a reviewed reference library, not a runtime template source.
- `assets/slides/templates/decks`: production runtime template decks selected through `config/reference_catalog.json`, `config/template_blueprints.json`, and `config/template_design_dna.json`.
- `assets/slides/templates/system_base`: split template candidates retained for search and possible promotion. These are not production templates until cataloged.

## Findings

- `graphify-out/GRAPH_REPORT.md` is absent, so architecture analysis used docs, JSON contracts, and source files.
- Raw reference PPTX files are present under `assets/slides/references`; they are intentionally gitignored.
- Existing categorizing records use the transitional `deck_id__slide_NNN` naming form.
- Production catalogs point at promoted template libraries rather than raw reference or categorizing paths.
- Legacy paths such as `assets/templates` and `outputs/reference_intake` must stay out of production configs.

## Boundary Rules

- Raw PPTX inputs must not be scanned by deck generation.
- Candidate slides must not become selectable runtime templates.
- Promotion must be explicit and metadata-backed.
- JSON contracts remain the source of truth. Rendered previews, generated decks, Graphify outputs, SQLite caches, and local raw references are derived or local artifacts.
