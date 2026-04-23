# Template Index DB

The template index DB is a generated SQLite cache for fast template lookup and agent-friendly inspection.

JSON and sharded config remain the source of truth:

- `config/reference_catalog.json`
- `config/template_blueprints.json`
- `config/template_design_dna.json`
- `config/template_slot_name_manifest.json`

The DB must not become the canonical template registry in this phase. Normal deck builds should continue to read the JSON config directly.

## Migration Trigger

Keep SQLite as a generated cache until one of these is true:

- The reviewed production template library grows beyond roughly 300 slides.
- Selector/rationale builds spend meaningful time repeatedly parsing JSON metadata.
- Assistant-mode tooling needs repeated ad hoc queries across template purpose, scope, tone, density, visual weight, and slot fields.

Even then, JSON remains the source of truth. CI should rebuild the DB from JSON and compare row counts before runtime selection depends on it.

## Build

```powershell
python scripts/build_template_index_db.py --output outputs/cache/template_index.db --check
```

The default output path is:

```text
outputs/cache/template_index.db
```

`outputs/` is ignored by git, so generated DB files are local artifacts only.

## Tables

- `templates`: one row per reference catalog template with Design DNA fields merged where available.
- `template_tags`: style tags and tone tags for filtering.
- `template_roles`: reserved for future story-arc roles.
- `template_slots`: editable text, image, and chart slots from blueprint metadata, checked against `config/template_slot_name_manifest.json`.

## Check Mode

`--check` confirms:

- expected tables exist
- `templates` row count matches `config/reference_catalog.json`
- `template_slots` row count matches `config/template_slot_name_manifest.json`
- selector/DNA fields such as purpose, scope, density, structure, and visual weight are populated
- tone tags are present for future mode-policy and assistant-mode queries
- a production-ready template lookup returns at least one result

This prepares the system for larger template libraries without changing runtime selection behavior yet.
