from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.reference_pipeline import (
    CANDIDATE_LABELS,
    DEFAULT_CURATION_ROOT,
    LIBRARY_ROOT,
    candidate_to_quality,
    load_json,
    update_reference_record_status,
    utc_now,
    write_json,
)


def copy_asset(source_rel: str, target_dir: Path) -> str:
    source = BASE_DIR / source_rel
    if not source.exists():
        raise FileNotFoundError(source_rel)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / source.name
    shutil.copy2(source, target)
    return target.resolve().relative_to(BASE_DIR).as_posix()


def load_library_index(quality: str) -> dict[str, Any]:
    path = LIBRARY_ROOT / quality / "index.json"
    if path.exists():
        return load_json(path)
    return {
        "schema_version": "1.0",
        "quality": quality,
        "description": f"Finalized {quality} reference slides.",
        "items": [],
    }


def write_library_readme(quality: str, index: dict[str, Any]) -> None:
    descriptions = {
        "good": "Approved high-quality classified reference slides. Items here can seed future pattern/template promotion after separate analysis.",
        "normal": "Approved normal-quality classified reference slides. Items here are useful for structure study and comparison.",
        "weak": "Approved weak-quality classified reference slides. Items here are negative examples or cautionary references.",
    }
    text = [
        f"# {quality.title()} Reference Library",
        "",
        descriptions[quality],
        "",
        f"Item count: {len(index.get('items', []))}",
        "",
        "Promotion is explicit and metadata-backed. Files in this library are not runtime templates by presence alone.",
        "",
    ]
    (LIBRARY_ROOT / quality / "README.md").write_text("\n".join(text), encoding="utf-8")


def promote_metadata_record(record: dict[str, Any], quality: str, *, dry_run: bool) -> dict[str, Any]:
    identity = record["identity"]
    slide_id = identity["slide_id"]
    quality_root = LIBRARY_ROOT / quality
    png_path = copy_asset(identity["preview_png"], quality_root / "png") if not dry_run else f"assets/slides/library/{quality}/png/{Path(identity['preview_png']).name}"
    pptx_path = copy_asset(identity["one_slide_pptx"], quality_root / "pptx") if not dry_run else f"assets/slides/library/{quality}/pptx/{Path(identity['one_slide_pptx']).name}"

    finalized = dict(record)
    finalized["identity"] = dict(identity)
    finalized["identity"]["preview_png"] = png_path
    finalized["identity"]["one_slide_pptx"] = pptx_path
    finalized["curation"] = dict(record.get("curation", {}))
    finalized["curation"].update(
        {
            "quality_label": quality,
            "candidate_bucket": None,
            "curation_stage": "finalized",
            "promotion_status": "promoted",
            "human_review_status": "approved",
            "promoted_at": utc_now(),
            "updated_at": utc_now(),
        }
    )
    metadata_path = quality_root / "metadata" / f"{slide_id}.json"
    if not dry_run:
        write_json(metadata_path, {"schema_version": "1.0", "reference_id": identity["reference_id"], "slides": [finalized]})
    return {
        "slide_id": slide_id,
        "reference_id": identity["reference_id"],
        "quality": quality,
        "preview_png": png_path,
        "one_slide_pptx": pptx_path,
        "metadata_path": metadata_path.resolve().relative_to(BASE_DIR).as_posix(),
        "promoted_at": finalized["curation"]["promoted_at"],
    }


def promote_candidates(curation_root: Path, *, dry_run: bool = False) -> dict[str, Any]:
    records_dir = curation_root / "records"
    promoted: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    indexes: dict[str, dict[str, Any]] = {}

    for metadata_path in sorted(records_dir.glob("*_slide_metadata.json")):
        metadata = load_json(metadata_path)
        for record in metadata.get("slides", []):
            curation = record.get("curation", {})
            candidate_bucket = curation.get("candidate_bucket") or curation.get("quality_label")
            if candidate_bucket not in CANDIDATE_LABELS:
                continue
            try:
                quality = candidate_to_quality(str(candidate_bucket))
                item = promote_metadata_record(record, quality, dry_run=dry_run)
            except Exception as exc:  # noqa: BLE001 - promotion should report every skipped candidate.
                skipped.append({"metadata_path": metadata_path.resolve().relative_to(BASE_DIR).as_posix(), "error": str(exc)})
                continue
            promoted.append(item)
            indexes.setdefault(quality, load_library_index(quality))
            existing = [
                old
                for old in indexes[quality].get("items", [])
                if old.get("slide_id") != item["slide_id"]
            ]
            existing.append(item)
            indexes[quality]["items"] = sorted(existing, key=lambda value: str(value.get("slide_id")))
            update_reference_record_status(item["reference_id"], "promoted")

    for quality, index in indexes.items():
        if not dry_run:
            write_json(LIBRARY_ROOT / quality / "index.json", index)
            write_library_readme(quality, index)

    # Transitional label files without metadata are reported but not promoted.
    # If a legacy candidate has already been reparsed into a canonical slide ID,
    # the legacy row keeps its review evidence without reappearing as debt.
    for label_path in sorted(records_dir.glob("*_slide_quality_labels.json")):
        deck_id = label_path.name.removesuffix("_slide_quality_labels.json")
        metadata_path = records_dir / f"{deck_id}_slide_metadata.json"
        if metadata_path.exists():
            continue
        labels = load_json(label_path)
        candidate_count = 0
        for slide in labels.get("slides", []):
            if slide.get("quality") not in CANDIDATE_LABELS:
                continue
            canonicalization = slide.get("canonicalization", {})
            if isinstance(canonicalization, dict) and canonicalization.get("status") == "canonicalized":
                continue
            candidate_count += 1
        if candidate_count:
            skipped.append(
                {
                    "label_path": label_path.resolve().relative_to(BASE_DIR).as_posix(),
                    "candidate_count": candidate_count,
                    "reason": "missing canonical slide metadata; reparse through index before promotion",
                }
            )

    return {"schema_version": "1.0", "dry_run": dry_run, "promoted": promoted, "skipped": skipped}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Promote reviewed reference candidates into finalized libraries.")
    parser.add_argument("--curation-root", default=str(DEFAULT_CURATION_ROOT))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    curation_root = Path(args.curation_root)
    if not curation_root.is_absolute():
        curation_root = (BASE_DIR / curation_root).resolve()
    payload = promote_candidates(curation_root, dry_run=args.dry_run)
    print(f"promoted={len(payload['promoted'])} skipped={len(payload['skipped'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
