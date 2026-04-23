from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = BASE_DIR / "outputs" / "cache" / "template_index.db"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS template_slots;
        DROP TABLE IF EXISTS template_roles;
        DROP TABLE IF EXISTS template_tags;
        DROP TABLE IF EXISTS templates;

        CREATE TABLE templates(
          template_key TEXT PRIMARY KEY,
          slide_id TEXT,
          library_id TEXT,
          purpose TEXT,
          scope TEXT,
          variant TEXT,
          structure TEXT,
          density TEXT,
          visual_weight TEXT,
          content_capacity TEXT,
          footer_supported INTEGER,
          quality_score REAL,
          design_tier TEXT,
          usage_policy TEXT,
          default_rank INTEGER
        );

        CREATE TABLE template_tags(
          template_key TEXT,
          tag TEXT
        );

        CREATE TABLE template_roles(
          template_key TEXT,
          role TEXT
        );

        CREATE TABLE template_slots(
          template_key TEXT,
          slot_name TEXT,
          slot_kind TEXT,
          font_role TEXT,
          fit_strategy TEXT,
          max_chars_per_line INTEGER
        );

        CREATE INDEX idx_template_tags_tag ON template_tags(tag);
        CREATE INDEX idx_template_roles_role ON template_roles(role);
        CREATE INDEX idx_template_slots_template ON template_slots(template_key);
        """
    )


def content_capacity_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def insert_templates(conn: sqlite3.Connection, reference: dict[str, Any], design_dna: dict[str, Any]) -> None:
    dna_by_slide_id = design_dna.get("slides", {})
    for slide in reference.get("slides", []):
        slide_id = slide.get("slide_id")
        dna = dna_by_slide_id.get(slide_id, {})
        template_key = slide.get("template_key")
        conn.execute(
            """
            INSERT INTO templates(
              template_key, slide_id, library_id, purpose, scope, variant, structure,
              density, visual_weight, content_capacity, footer_supported, quality_score,
              design_tier, usage_policy, default_rank
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                template_key,
                slide_id,
                slide.get("library_id"),
                slide.get("purpose"),
                slide.get("scope"),
                slide.get("variant"),
                dna.get("structure") or slide.get("structure"),
                dna.get("density") or slide.get("density"),
                dna.get("visual_weight") or slide.get("visual_weight"),
                content_capacity_text(dna.get("content_capacity") or slide.get("content_capacity")),
                int(bool(dna.get("footer_supported", slide.get("footer_supported", False)))),
                slide.get("quality_score"),
                slide.get("design_tier"),
                slide.get("usage_policy"),
                slide.get("default_rank"),
            ),
        )
        for tag in slide.get("style_tags", []):
            conn.execute("INSERT INTO template_tags(template_key, tag) VALUES (?, ?)", (template_key, tag))
        for tone in dna.get("tone", []):
            conn.execute("INSERT INTO template_tags(template_key, tag) VALUES (?, ?)", (template_key, f"tone:{tone}"))
        for role in dna.get("story_roles", []):
            conn.execute("INSERT INTO template_roles(template_key, role) VALUES (?, ?)", (template_key, role))


def slot_rows_for_blueprint(template_key: str, blueprint: dict[str, Any]) -> list[tuple[Any, ...]]:
    rows: list[tuple[Any, ...]] = []
    slot_groups = [
        ("text", blueprint.get("editable_text_slots", [])),
        ("image", blueprint.get("editable_image_slots", [])),
        ("chart", blueprint.get("editable_chart_slots", [])),
        ("table", blueprint.get("editable_table_slots", [])),
    ]
    for slot_kind, slots in slot_groups:
        for slot in slots:
            rows.append(
                (
                    template_key,
                    slot.get("slot"),
                    slot_kind,
                    slot.get("font_role"),
                    slot.get("fit_strategy"),
                    slot.get("max_chars_per_line"),
                )
            )
    return rows


def insert_slots(conn: sqlite3.Connection, reference: dict[str, Any], blueprints: dict[str, Any]) -> None:
    template_by_slide_id = {
        slide.get("slide_id"): slide.get("template_key")
        for slide in reference.get("slides", [])
    }
    for slide_id, blueprint in blueprints.get("slides", {}).items():
        template_key = template_by_slide_id.get(slide_id) or blueprint.get("template_key")
        if not template_key:
            continue
        conn.executemany(
            """
            INSERT INTO template_slots(
              template_key, slot_name, slot_kind, font_role, fit_strategy, max_chars_per_line
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            slot_rows_for_blueprint(template_key, blueprint),
        )


def check_slot_manifest_coverage(conn: sqlite3.Connection, slot_manifest: dict[str, Any]) -> None:
    expected = {
        (entry.get("template_key"), entry.get("slot"), entry.get("slot_kind"))
        for entry in slot_manifest.get("entries", [])
    }
    actual = {
        tuple(row)
        for row in conn.execute("SELECT template_key, slot_name, slot_kind FROM template_slots").fetchall()
    }
    missing = expected - actual
    extra = actual - expected
    if missing or extra:
        raise AssertionError(
            f"template_slots do not match template_slot_name_manifest: "
            f"missing={len(missing)}, extra={len(extra)}"
        )


def build_db(output_path: Path) -> None:
    reference = load_json(BASE_DIR / "config" / "reference_catalog.json")
    blueprints = load_json(BASE_DIR / "config" / "template_blueprints.json")
    design_dna = load_json(BASE_DIR / "config" / "template_design_dna.json")
    slot_manifest = load_json(BASE_DIR / "config" / "template_slot_name_manifest.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(output_path) as conn:
        create_schema(conn)
        insert_templates(conn, reference, design_dna)
        insert_slots(conn, reference, blueprints)
        check_slot_manifest_coverage(conn, slot_manifest)
        conn.commit()


def check_db(output_path: Path) -> None:
    expected_tables = {"templates", "template_tags", "template_roles", "template_slots"}
    reference = load_json(BASE_DIR / "config" / "reference_catalog.json")
    slot_manifest = load_json(BASE_DIR / "config" / "template_slot_name_manifest.json")
    with sqlite3.connect(output_path) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        tables = {row[0] for row in rows}
        missing = expected_tables - tables
        if missing:
            raise AssertionError(f"Missing tables: {sorted(missing)}")
        template_count = conn.execute("SELECT COUNT(*) FROM templates").fetchone()[0]
        slot_count = conn.execute("SELECT COUNT(*) FROM template_slots").fetchone()[0]
        reference_count = len(reference.get("slides", []))
        expected_slot_count = len(slot_manifest.get("entries", []))
        if template_count <= 0:
            raise AssertionError("templates table has no rows")
        if slot_count <= 0:
            raise AssertionError("template_slots table has no rows")
        if template_count != reference_count:
            raise AssertionError(f"templates row count {template_count} does not match reference catalog {reference_count}")
        if slot_count != expected_slot_count:
            raise AssertionError(f"template_slots row count {slot_count} does not match slot manifest {expected_slot_count}")
        missing_selector_fields = conn.execute(
            """
            SELECT COUNT(*)
            FROM templates
            WHERE purpose IS NULL
               OR scope IS NULL
               OR density IS NULL
               OR structure IS NULL
               OR visual_weight IS NULL
            """
        ).fetchone()[0]
        if missing_selector_fields:
            raise AssertionError(f"templates missing selector/DNA fields: {missing_selector_fields}")
        tone_tag_count = conn.execute("SELECT COUNT(*) FROM template_tags WHERE tag LIKE 'tone:%'").fetchone()[0]
        if tone_tag_count <= 0:
            raise AssertionError("template_tags has no tone:* rows")
        smoke = conn.execute(
            """
            SELECT template_key
            FROM templates
            WHERE usage_policy = 'production_ready'
            ORDER BY quality_score DESC, template_key
            LIMIT 1
            """
        ).fetchone()
        if smoke is None:
            raise AssertionError("smoke query returned no production_ready template")
        print(
            json.dumps(
                {
                    "database": output_path.as_posix(),
                    "templates": template_count,
                    "template_slots": slot_count,
                    "tone_tags": tone_tag_count,
                    "smoke_template": smoke[0],
                },
                ensure_ascii=False,
            )
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the generated SQLite template index cache.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = BASE_DIR / output_path
    build_db(output_path)
    print(output_path)
    if args.check:
        check_db(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
