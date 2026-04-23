from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CLEANUP_PATH = BASE_DIR / "config" / "template_text_dna_cleanup.json"


def load_template_text_dna_cleanup(path: str | Path | None = None) -> dict[str, Any]:
    cleanup_path = Path(path) if path else DEFAULT_CLEANUP_PATH
    if not cleanup_path.exists():
        return {"schema_version": "1.0", "templates": {}}
    return json.loads(cleanup_path.read_text(encoding="utf-8"))


def cleanup_records_for_template(
    cleanup_config: dict[str, Any],
    *,
    template_key: str | None,
    slide_id: str | None = None,
) -> list[dict[str, Any]]:
    templates = cleanup_config.get("templates", {})
    records: list[dict[str, Any]] = []
    for key in (template_key, slide_id):
        if not key:
            continue
        entry = templates.get(key, {})
        records.extend(record for record in entry.get("cleanup_patterns", []) if isinstance(record, dict))
    return records


def cleanup_patterns_for_template(
    cleanup_config: dict[str, Any],
    *,
    template_key: str | None,
    slide_id: str | None = None,
) -> list[str]:
    patterns: list[str] = []
    seen: set[str] = set()
    for record in cleanup_records_for_template(cleanup_config, template_key=template_key, slide_id=slide_id):
        pattern = str(record.get("pattern") or "").strip()
        lowered = pattern.lower()
        if pattern and lowered not in seen:
            patterns.append(pattern)
            seen.add(lowered)
    return patterns


def slide_spec_with_text_dna_cleanup(
    slide_spec: dict[str, Any],
    resolved: dict[str, Any],
    cleanup_config: dict[str, Any],
) -> dict[str, Any]:
    patterns = cleanup_patterns_for_template(
        cleanup_config,
        template_key=resolved.get("template_key"),
        slide_id=resolved.get("slide_id"),
    )
    if not patterns:
        return slide_spec

    merged = copy.deepcopy(slide_spec)
    existing = list(merged.get("clear_residual_text_patterns", []))
    seen = {str(pattern).lower() for pattern in existing}
    for pattern in patterns:
        if pattern.lower() not in seen:
            existing.append(pattern)
            seen.add(pattern.lower())
    merged["clear_residual_text_patterns"] = existing
    return merged
