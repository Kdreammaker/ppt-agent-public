from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.reference_pipeline import (
    CANDIDATE_LABELS,
    candidate_to_quality,
    load_json,
    update_reference_record_status,
    utc_now,
    write_json,
)

BUCKETS = [
    "unlabeled",
    "good_candidate",
    "normal_candidate",
    "weak_candidate",
]


def base_relative(path: Path) -> str:
    return path.resolve().relative_to(BASE_DIR).as_posix()


def scan_png_buckets(deck_dir: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    conflicts: list[str] = []
    for bucket in BUCKETS:
        bucket_dir = deck_dir / "png" / bucket
        bucket_dir.mkdir(parents=True, exist_ok=True)
        for path in sorted(bucket_dir.glob("*.png")):
            asset_stem = path.stem
            existing = found.get(asset_stem)
            if existing and existing != bucket:
                conflicts.append(f"{path.name} is in both {existing} and {bucket}")
            found[asset_stem] = bucket
    if conflicts:
        raise ValueError("; ".join(conflicts))
    return found


def sync_pptx_to_bucket(deck_dir: Path, asset_stem: str, bucket: str) -> Path:
    filename = f"{asset_stem}.pptx"
    target = deck_dir / "pptx" / bucket / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    current = None
    for candidate_bucket in BUCKETS:
        candidate = deck_dir / "pptx" / candidate_bucket / filename
        if candidate.exists():
            current = candidate
            break
    if current is None:
        raise FileNotFoundError(f"Missing one-slide PPTX: {filename}")
    if current.resolve() != target.resolve():
        if target.exists():
            target.unlink()
        shutil.move(str(current), str(target))
    return target


def sync_reference_quality_buckets(deck_dir: Path) -> dict[str, Any]:
    deck_dir = deck_dir.resolve()
    records_dir = deck_dir / "records"
    inventories = sorted(records_dir.glob("*_slide_inventory.json"))
    if not inventories:
        raise FileNotFoundError(f"Missing slide inventory files under: {records_dir}")
    png_buckets = scan_png_buckets(deck_dir)

    synced: list[dict[str, Any]] = []
    summaries: dict[str, int] = {bucket: 0 for bucket in BUCKETS}
    for inventory_path in inventories:
        inventory = load_json(inventory_path)
        updated_slides: list[dict[str, Any]] = []
        for slide in inventory.get("slides", []):
            asset_stem = str(slide.get("asset_stem") or Path(slide["preview_png"]).stem)
            png_bucket = png_buckets.get(asset_stem, "unlabeled")
            pptx_path = sync_pptx_to_bucket(deck_dir, asset_stem, png_bucket)
            png_path = deck_dir / "png" / png_bucket / f"{asset_stem}.png"
            status = "candidate" if png_bucket.endswith("_candidate") else "unlabeled"
            updated = dict(slide)
            updated.update(
                {
                    "quality": png_bucket,
                    "status": status,
                    "preview_png": base_relative(png_path),
                    "one_slide_pptx": base_relative(pptx_path),
                }
            )
            updated_slides.append(updated)
            summaries[png_bucket] += 1

        payload = dict(inventory)
        payload["slides"] = updated_slides
        payload["summary"] = {
            bucket: sum(1 for slide in updated_slides if slide["quality"] == bucket)
            for bucket in BUCKETS
        }
        output_path = records_dir / f"{payload['deck_id']}_slide_quality_labels.json"
        write_json(output_path, payload)
        metadata_path = records_dir / f"{payload['deck_id']}_slide_metadata.json"
        if metadata_path.exists():
            sync_slide_metadata(metadata_path, updated_slides)
        if any(slide["quality"] in CANDIDATE_LABELS for slide in updated_slides):
            update_reference_record_status(str(payload["deck_id"]), "classified")
        synced.append({"deck_id": payload.get("deck_id"), "summary": payload.get("summary", {})})

    return {"schema_version": "1.0", "summary": summaries, "decks": synced}


def sync_slide_metadata(metadata_path: Path, label_slides: list[dict[str, Any]]) -> None:
    metadata = load_json(metadata_path)
    by_stem = {
        str(slide.get("asset_stem") or Path(str(slide.get("preview_png", ""))).stem): slide
        for slide in label_slides
    }
    for slide_record in metadata.get("slides", []):
        identity = slide_record.get("identity", {})
        asset_stem = str(identity.get("asset_stem") or identity.get("slide_id"))
        label = by_stem.get(asset_stem)
        if not label:
            continue
        quality = str(label.get("quality", "unlabeled"))
        candidate_bucket = quality if quality in CANDIDATE_LABELS else None
        curation_stage = "candidate" if candidate_bucket else "parsed"
        human_review_status = "candidate_reviewed" if candidate_bucket else "unreviewed"
        promotion_status = "candidate" if candidate_bucket else "not_promoted"
        curation = dict(slide_record.get("curation", {}))
        curation.update(
            {
                "quality_label": quality,
                "candidate_bucket": candidate_bucket,
                "curation_stage": curation_stage,
                "promotion_status": promotion_status,
                "human_review_status": human_review_status,
                "updated_at": utc_now(),
            }
        )
        if candidate_bucket:
            curation["final_quality_target"] = candidate_to_quality(candidate_bucket)
        slide_record["curation"] = curation
        identity["preview_png"] = label.get("preview_png")
        identity["one_slide_pptx"] = label.get("one_slide_pptx")
        slide_record["identity"] = identity
    metadata["updated_at"] = utc_now()
    write_json(metadata_path, metadata)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sync PNG quality buckets to matching one-slide PPTX files and labels JSON.")
    parser.add_argument("curation_deck_dir")
    args = parser.parse_args(argv)

    deck_dir = Path(args.curation_deck_dir)
    if not deck_dir.is_absolute():
        deck_dir = (BASE_DIR / deck_dir).resolve()
    payload = sync_reference_quality_buckets(deck_dir)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
