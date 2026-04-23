from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from pathlib import Path, PureWindowsPath
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
REFERENCE_ROOT = BASE_DIR / "assets" / "slides" / "references"
DEFAULT_CURATION_ROOT = BASE_DIR / "assets" / "slides" / "categorizing"
LIBRARY_ROOT = BASE_DIR / "assets" / "slides" / "library"
ASSET_ROOTS_PATH = BASE_DIR / "config" / "ppt_asset_roots.json"
ASSET_CATALOG_PATH = BASE_DIR / "config" / "ppt_asset_catalog.json"
REFERENCE_INDEX_PATH = REFERENCE_ROOT / "index.json"

REFERENCE_GROUPS = {
    "portfolio",
    "proposal",
    "pitch_deck",
    "business_plan",
    "sales_deck",
    "report",
    "case_study",
    "company_intro",
    "research",
    "template_pack",
    "generated",
    "unknown",
}
DECK_TYPES = REFERENCE_GROUPS
SOURCE_KINDS = {"external_reference", "generated_deck", "primary_template", "unknown"}
REFERENCE_STATUSES = {"raw_unparsed", "parsed", "classified", "promoted", "archived"}
QUALITY_LABELS = {"good", "normal", "weak"}
CANDIDATE_LABELS = {"good_candidate", "normal_candidate", "weak_candidate"}
CAPTURE_DEDUPE_MODES = {"always_new", "checksum_dedupe", "skip_regression_samples"}
CURATION_BUCKETS = ["unlabeled", "good_candidate", "normal_candidate", "weak_candidate"]
ALL_QUALITY_LABELS = {"unlabeled", *CANDIDATE_LABELS, *QUALITY_LABELS}
CURATION_STAGES = {"raw", "parsed", "candidate", "finalized", "archived"}
PROMOTION_STATUSES = {"not_promoted", "candidate", "promoted", "archived"}
HUMAN_REVIEW_STATUSES = {"unreviewed", "candidate_reviewed", "approved", "rejected"}

REFERENCE_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*_[0-9]{3}$")
SLIDE_ID_RE = re.compile(r"^(?P<reference_id>[a-z][a-z0-9]*(?:_[a-z0-9]+)*_[0-9]{3})_s(?P<slide_no>[0-9]{3})$")


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def base_relative(path: Path) -> str:
    return path.resolve().relative_to(BASE_DIR).as_posix()


def is_base_relative_path(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    if "\\" in value:
        return False
    if Path(value).is_absolute() or PureWindowsPath(value).is_absolute():
        return False
    if PureWindowsPath(value).drive:
        return False
    return ".." not in Path(value).parts


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_text(value: str) -> str:
    return value.casefold().replace("_", " ").replace("-", " ")


def has_hangul(value: str) -> bool:
    return any("\uac00" <= char <= "\ud7a3" for char in value)


def infer_reference_group(file_name: str, source_path: Path) -> tuple[str, float, list[str]]:
    text = normalize_text(file_name)
    rules = [
        ("generated", 0.95, ["generated", "template slide sample"]),
        ("portfolio", 0.86, ["portfolio", "포트폴리오"]),
        ("proposal", 0.84, ["proposal", "제안"]),
        ("pitch_deck", 0.82, ["pitch", "investor", "투자"]),
        ("business_plan", 0.84, ["business plan", "사업계획"]),
        ("sales_deck", 0.78, ["sales", "marketing", "영업", "마케팅"]),
        ("report", 0.76, ["report", "성과", "보고"]),
        ("case_study", 0.78, ["case study", "case", "사례"]),
        ("company_intro", 0.76, ["company intro", "회사소개", "기업 소개", "기업"]),
        ("research", 0.76, ["research", "paper", "리서치", "연구"]),
        ("template_pack", 0.66, ["template", "album", "style", "chart", "process", "guide", "ppt", "layout"]),
    ]
    if "generated" in [part.casefold() for part in source_path.parts]:
        return "generated", 0.98, ["source_path contains generated"]
    for group, confidence, keywords in rules:
        hits = [keyword for keyword in keywords if keyword in text]
        if hits:
            return group, confidence, hits
    return "unknown", 0.2, []


def infer_language(file_name: str) -> str | None:
    if has_hangul(file_name):
        return "ko"
    if any("a" <= char.casefold() <= "z" for char in file_name):
        return "en"
    return None


def source_kind_for_path(path: Path) -> str:
    if "generated" in [part.casefold() for part in path.parts]:
        return "generated_deck"
    if path.name.casefold() == "template.pptx":
        return "primary_template"
    return "external_reference"


def canonical_slide_id(reference_id: str, slide_no: int) -> str:
    return f"{reference_id}_s{slide_no:03d}"


def parse_slide_id(slide_id: str) -> tuple[str, int] | None:
    match = SLIDE_ID_RE.match(slide_id)
    if not match:
        return None
    return match.group("reference_id"), int(match.group("slide_no"))


def slide_no_from_asset_stem(asset_stem: str) -> int:
    parsed = parse_slide_id(asset_stem)
    if parsed:
        return parsed[1]
    if "__slide_" in asset_stem:
        return int(asset_stem.rsplit("__slide_", 1)[1])
    if "_slide_" in asset_stem:
        return int(asset_stem.rsplit("_slide_", 1)[1])
    raise ValueError(f"Cannot infer slide number from asset stem: {asset_stem}")


def load_reference_index(index_path: Path = REFERENCE_INDEX_PATH) -> dict[str, Any] | None:
    if not index_path.exists():
        return None
    return load_json(index_path)


def reference_records(index: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not index:
        return []
    records = index.get("references", [])
    return records if isinstance(records, list) else []


def save_reference_index(index: dict[str, Any], index_path: Path = REFERENCE_INDEX_PATH) -> None:
    index["references"] = sorted(
        reference_records(index),
        key=lambda item: (str(item.get("reference_group", "")), str(item.get("reference_id", ""))),
    )
    write_json(index_path, index)


def next_reference_sequence(group: str, records: list[dict[str, Any]]) -> int:
    prefix = f"{group}_"
    numbers = [
        int(reference_id.removeprefix(prefix))
        for record in records
        for reference_id in [str(record.get("reference_id", ""))]
        if reference_id.startswith(prefix) and reference_id.removeprefix(prefix).isdigit()
    ]
    return (max(numbers) + 1) if numbers else 1


def find_reference_record_by_checksum(
    group: str,
    checksum: str,
    records: list[dict[str, Any]],
) -> dict[str, Any] | None:
    for record in records:
        if record.get("reference_group") == group and record.get("checksum") == checksum:
            source_path = record.get("source_path")
            if isinstance(source_path, str) and (BASE_DIR / source_path).exists():
                return record
    return None


def register_reference_file(
    source_path: Path,
    *,
    group: str = "generated",
    original_file_name: str | None = None,
    source_kind: str = "generated_deck",
    copy_to_reference_root: bool = True,
    capture_dedupe_mode: str = "always_new",
    index_path: Path = REFERENCE_INDEX_PATH,
) -> dict[str, Any]:
    if group not in REFERENCE_GROUPS:
        raise ValueError(f"Unsupported reference group: {group}")
    if source_kind not in SOURCE_KINDS:
        raise ValueError(f"Unsupported source kind: {source_kind}")
    if capture_dedupe_mode not in CAPTURE_DEDUPE_MODES:
        raise ValueError(f"Unsupported capture dedupe mode: {capture_dedupe_mode}")
    source_path = source_path.resolve()
    if not source_path.exists():
        raise FileNotFoundError(source_path)
    if source_path.suffix.lower() != ".pptx":
        raise ValueError(f"Expected a .pptx file: {source_path}")

    source_checksum = file_sha256(source_path)
    index = load_reference_index(index_path) or {
        "schema_version": "1.0",
        "reference_root": "assets/slides/references",
        "references": [],
    }
    records = reference_records(index)
    if capture_dedupe_mode == "checksum_dedupe":
        existing = find_reference_record_by_checksum(group, source_checksum, records)
        if existing:
            now = utc_now()
            existing["updated_at"] = now
            existing["last_seen_at"] = now
            existing["capture_count"] = int(existing.get("capture_count", 1)) + 1
            existing["capture_dedupe_mode"] = capture_dedupe_mode
            save_reference_index(index, index_path)
            result = dict(existing)
            result["capture_action"] = "reused_existing"
            return result

    sequence = next_reference_sequence(group, records)
    reference_id = f"{group}_{sequence:03d}"
    target = (REFERENCE_ROOT / group / f"{reference_id}.pptx") if copy_to_reference_root else source_path
    while target.exists() and target.resolve() != source_path:
        sequence += 1
        reference_id = f"{group}_{sequence:03d}"
        target = (REFERENCE_ROOT / group / f"{reference_id}.pptx") if copy_to_reference_root else source_path

    if copy_to_reference_root:
        target.parent.mkdir(parents=True, exist_ok=True)
        if source_path.resolve() != target.resolve():
            import shutil

            shutil.copy2(source_path, target)

    checksum = file_sha256(target)
    _, confidence, hits = infer_reference_group(original_file_name or source_path.name, target)
    now = utc_now()
    record = {
        "reference_id": reference_id,
        "reference_group": group,
        "original_file_name": original_file_name or source_path.name,
        "stored_file_name": target.name,
        "source_path": base_relative(target),
        "source_kind": source_kind,
        "deck_type_primary": group,
        "deck_type_secondary": [],
        "language": infer_language(original_file_name or source_path.name),
        "source_country": None,
        "source_locale": None,
        "design_culture": [],
        "checksum": checksum,
        "status": "raw_unparsed",
        "capture_count": 1,
        "last_seen_at": now,
        "capture_dedupe_mode": capture_dedupe_mode,
        "inference": {
            "confidence": confidence,
            "method": "generated_output_capture" if group == "generated" else "manual_reference_registration",
            "matched_keywords": hits,
            "requires_human_review": confidence < 0.75,
        },
        "created_at": now,
        "updated_at": now,
    }
    records.append(record)
    save_reference_index(index, index_path)
    result = dict(record)
    result["capture_action"] = "created_new"
    return result


def find_reference_record_for_path(source: Path, index: dict[str, Any] | None = None) -> dict[str, Any] | None:
    index = index if index is not None else load_reference_index()
    source = source.resolve()
    for record in reference_records(index):
        source_path = record.get("source_path")
        if not isinstance(source_path, str):
            continue
        candidate = (BASE_DIR / source_path).resolve()
        if candidate == source:
            return record
        if record.get("stored_file_name") == source.name and candidate.exists() and candidate.samefile(source):
            return record
    return None


def find_reference_record(reference_id: str, index: dict[str, Any] | None = None) -> dict[str, Any] | None:
    for record in reference_records(index if index is not None else load_reference_index()):
        if record.get("reference_id") == reference_id:
            return record
    return None


def update_reference_record_status(
    reference_id: str,
    status: str,
    *,
    index_path: Path = REFERENCE_INDEX_PATH,
) -> bool:
    if status not in REFERENCE_STATUSES:
        raise ValueError(f"Unsupported reference status: {status}")
    index = load_reference_index(index_path)
    if not index:
        return False
    now = utc_now()
    changed = False
    for record in reference_records(index):
        if record.get("reference_id") == reference_id:
            record["status"] = status
            record["updated_at"] = now
            changed = True
    if changed:
        save_reference_index(index, index_path)
    return changed


def validate_reference_id(value: Any) -> bool:
    return isinstance(value, str) and bool(REFERENCE_ID_RE.match(value))


def validate_slide_id(value: Any) -> bool:
    return isinstance(value, str) and bool(SLIDE_ID_RE.match(value))


def candidate_to_quality(label: str) -> str:
    if label == "good_candidate":
        return "good"
    if label == "normal_candidate":
        return "normal"
    if label == "weak_candidate":
        return "weak"
    raise ValueError(f"Unsupported candidate label: {label}")


def quality_to_candidate(label: str) -> str:
    if label not in QUALITY_LABELS:
        raise ValueError(f"Unsupported quality label: {label}")
    return f"{label}_candidate"
