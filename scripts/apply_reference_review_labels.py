from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.reference_pipeline import (  # noqa: E402
    CANDIDATE_LABELS,
    DEFAULT_CURATION_ROOT,
    QUALITY_LABELS,
    candidate_to_quality,
    load_json,
    parse_slide_id,
    quality_to_candidate,
    utc_now,
    write_json,
)
from scripts.sync_reference_quality_buckets import BUCKETS, base_relative, sync_reference_quality_buckets  # noqa: E402
from scripts.validate_reference_curation import validate_label_file  # noqa: E402

DEFAULT_LABEL_INPUT = DEFAULT_CURATION_ROOT / "records" / "reference_review_labels.json"


@dataclass(frozen=True)
class ReviewLabel:
    slide_id: str
    quality_label: str
    intent: str | None
    notes: str | None
    reviewer: str
    review_confidence: float | None

    @property
    def target_quality(self) -> str:
        return candidate_to_quality(self.quality_label)


@dataclass(frozen=True)
class LabelTarget:
    request: ReviewLabel
    label_path: Path
    asset_stem: str
    png_path: Path
    pptx_path: Path
    png_target: Path
    pptx_target: Path
    metadata_path: Path | None


def normalize_quality_label(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("quality_label must be a non-empty string")
    if value in CANDIDATE_LABELS:
        return value
    if value in QUALITY_LABELS:
        return quality_to_candidate(value)
    raise ValueError(f"Unsupported quality_label: {value!r}")


def as_optional_string(value: Any, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string or null")
    return value


def as_optional_confidence(value: Any) -> float | None:
    if value is None:
        return None
    if not isinstance(value, int | float) or not 0 <= float(value) <= 1:
        raise ValueError("review_confidence must be a number between 0 and 1")
    return float(value)


def load_review_labels(path: Path) -> list[ReviewLabel]:
    payload = load_json(path)
    rows = payload.get("labels", payload.get("reviews", payload.get("slides")))
    if not isinstance(rows, list):
        raise ValueError("label input must contain a labels, reviews, or slides list")
    labels: list[ReviewLabel] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"labels[{index}] must be an object")
        slide_id = row.get("slide_id")
        if not isinstance(slide_id, str) or not parse_slide_id(slide_id):
            raise ValueError(f"labels[{index}].slide_id must be a canonical slide ID")
        if slide_id in seen:
            raise ValueError(f"Duplicate slide_id in input: {slide_id}")
        seen.add(slide_id)
        reviewer = row.get("reviewer")
        if not isinstance(reviewer, str) or not reviewer:
            raise ValueError(f"labels[{index}].reviewer must be a non-empty string")
        quality_label = normalize_quality_label(row.get("quality_label", row.get("label", row.get("quality"))))
        labels.append(
            ReviewLabel(
                slide_id=slide_id,
                quality_label=quality_label,
                intent=as_optional_string(row.get("intent"), f"labels[{index}].intent"),
                notes=as_optional_string(row.get("notes"), f"labels[{index}].notes"),
                reviewer=reviewer,
                review_confidence=as_optional_confidence(row.get("review_confidence")),
            )
        )
    return labels


def find_label_record(curation_root: Path, slide_id: str) -> tuple[Path, dict[str, Any]]:
    matches: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted((curation_root / "records").glob("*_slide_quality_labels.json")):
        data = load_json(path)
        for slide in data.get("slides", []):
            if isinstance(slide, dict) and slide.get("slide_id") == slide_id:
                matches.append((path, slide))
    if not matches:
        raise ValueError(f"Slide ID not found in curation label files: {slide_id}")
    if len(matches) > 1:
        paths = ", ".join(path.relative_to(BASE_DIR).as_posix() for path, _ in matches)
        raise ValueError(f"Slide ID appears in multiple label files: {slide_id}: {paths}")
    return matches[0]


def find_single_asset(curation_root: Path, kind: str, asset_stem: str, suffix: str) -> Path:
    matches = [curation_root / kind / bucket / f"{asset_stem}{suffix}" for bucket in BUCKETS]
    existing = [path for path in matches if path.exists()]
    if not existing:
        raise FileNotFoundError(f"Missing {kind} asset for {asset_stem}")
    if len(existing) > 1:
        rels = ", ".join(path.relative_to(BASE_DIR).as_posix() for path in existing)
        raise ValueError(f"Asset exists in multiple {kind} buckets for {asset_stem}: {rels}")
    return existing[0]


def resolve_targets(curation_root: Path, reviews: list[ReviewLabel]) -> list[LabelTarget]:
    targets: list[LabelTarget] = []
    for request in reviews:
        label_path, label_record = find_label_record(curation_root, request.slide_id)
        asset_stem = str(label_record.get("asset_stem") or request.slide_id)
        png_path = find_single_asset(curation_root, "png", asset_stem, ".png")
        pptx_path = find_single_asset(curation_root, "pptx", asset_stem, ".pptx")
        png_target = curation_root / "png" / request.quality_label / f"{asset_stem}.png"
        pptx_target = curation_root / "pptx" / request.quality_label / f"{asset_stem}.pptx"
        parsed = parse_slide_id(request.slide_id)
        reference_id = parsed[0] if parsed else str(label_record.get("reference_id", ""))
        metadata_path = curation_root / "records" / f"{reference_id}_slide_metadata.json"
        targets.append(
            LabelTarget(
                request=request,
                label_path=label_path,
                asset_stem=asset_stem,
                png_path=png_path,
                pptx_path=pptx_path,
                png_target=png_target,
                pptx_target=pptx_target,
                metadata_path=metadata_path if metadata_path.exists() else None,
            )
        )
    return targets


def move_asset(source: Path, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() == target.resolve():
        return target
    if target.exists():
        raise FileExistsError(target)
    shutil.move(str(source), str(target))
    return target


def apply_review_fields_to_label_file(label_path: Path, requests: dict[str, ReviewLabel]) -> None:
    data = load_json(label_path)
    changed = False
    for slide in data.get("slides", []):
        if not isinstance(slide, dict):
            continue
        request = requests.get(str(slide.get("slide_id")))
        if not request:
            continue
        slide["quality"] = request.quality_label
        slide["status"] = "candidate"
        slide["intent"] = request.intent
        slide["notes"] = request.notes
        slide["reviewer"] = request.reviewer
        if request.review_confidence is not None:
            slide["review_confidence"] = request.review_confidence
        slide["reviewed_at"] = utc_now()
        changed = True
    if changed:
        write_json(label_path, data)


def apply_review_fields_to_metadata(metadata_path: Path, requests: dict[str, ReviewLabel]) -> None:
    data = load_json(metadata_path)
    changed = False
    for slide in data.get("slides", []):
        if not isinstance(slide, dict):
            continue
        identity = slide.get("identity", {})
        request = requests.get(str(identity.get("slide_id")))
        if not request:
            continue
        curation = dict(slide.get("curation", {}))
        curation.update(
            {
                "quality_label": request.quality_label,
                "candidate_bucket": request.quality_label,
                "curation_stage": "candidate",
                "promotion_status": "candidate",
                "human_review_status": "candidate_reviewed",
                "final_quality_target": request.target_quality,
                "review_intent": request.intent,
                "review_notes": request.notes,
                "reviewer": request.reviewer,
                "updated_at": utc_now(),
            }
        )
        if request.review_confidence is not None:
            curation["review_confidence"] = request.review_confidence
        slide["curation"] = curation
        changed = True
    if changed:
        data["updated_at"] = utc_now()
        write_json(metadata_path, data)


def apply_review_labels(
    input_path: Path,
    *,
    curation_root: Path = DEFAULT_CURATION_ROOT,
    dry_run: bool = False,
) -> dict[str, Any]:
    curation_root = curation_root.resolve()
    reviews = load_review_labels(input_path)
    targets = resolve_targets(curation_root, reviews)

    if dry_run:
        return {
            "schema_version": "1.0",
            "dry_run": True,
            "applied": [
                {
                    "slide_id": target.request.slide_id,
                    "quality_label": target.request.quality_label,
                    "png_target": base_relative(target.png_target),
                    "pptx_target": base_relative(target.pptx_target),
                }
                for target in targets
            ],
        }

    for target in targets:
        move_asset(target.png_path, target.png_target)
        move_asset(target.pptx_path, target.pptx_target)

    sync_reference_quality_buckets(curation_root)

    requests_by_slide = {review.slide_id: review for review in reviews}
    label_paths = sorted({target.label_path for target in targets})
    metadata_paths = sorted({target.metadata_path for target in targets if target.metadata_path})
    for path in label_paths:
        apply_review_fields_to_label_file(path, requests_by_slide)
    for path in metadata_paths:
        apply_review_fields_to_metadata(path, requests_by_slide)

    errors: list[str] = []
    for path in label_paths:
        errors.extend(validate_label_file(path))
    if errors:
        raise ValueError("; ".join(errors))

    return {
        "schema_version": "1.0",
        "dry_run": False,
        "applied": [
            {
                "slide_id": target.request.slide_id,
                "quality_label": target.request.quality_label,
                "png_path": base_relative(target.png_target),
                "pptx_path": base_relative(target.pptx_target),
                "label_file": base_relative(target.label_path),
                "metadata_file": base_relative(target.metadata_path) if target.metadata_path else None,
            }
            for target in targets
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply batch review labels to reference curation assets.")
    parser.add_argument("label_input", nargs="?", default=DEFAULT_LABEL_INPUT.as_posix())
    parser.add_argument("--curation-root", default=DEFAULT_CURATION_ROOT.as_posix())
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    input_path = Path(args.label_input)
    if not input_path.is_absolute():
        input_path = (BASE_DIR / input_path).resolve()
    curation_root = Path(args.curation_root)
    if not curation_root.is_absolute():
        curation_root = (BASE_DIR / curation_root).resolve()

    try:
        payload = apply_review_labels(input_path, curation_root=curation_root, dry_run=args.dry_run)
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
