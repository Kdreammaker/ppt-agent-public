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
    REFERENCE_GROUPS,
    REFERENCE_INDEX_PATH,
    REFERENCE_ROOT,
    base_relative,
    file_sha256,
    infer_language,
    infer_reference_group,
    load_reference_index,
    reference_records,
    save_reference_index,
    source_kind_for_path,
    utc_now,
    validate_reference_id,
)


def next_sequence(group: str, used_ids: set[str]) -> int:
    prefix = f"{group}_"
    numbers = [
        int(reference_id.removeprefix(prefix))
        for reference_id in used_ids
        if reference_id.startswith(prefix) and reference_id.removeprefix(prefix).isdigit()
    ]
    return (max(numbers) + 1) if numbers else 1


def canonical_name(group: str, sequence: int) -> str:
    return f"{group}_{sequence:03d}.pptx"


def group_from_reference_id(reference_id: str) -> str:
    return reference_id.rsplit("_", 1)[0]


def build_existing_maps(index: dict[str, Any] | None) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], set[str]]:
    by_path: dict[str, dict[str, Any]] = {}
    by_checksum: dict[str, dict[str, Any]] = {}
    used_ids: set[str] = set()
    for record in reference_records(index):
        source_path = record.get("source_path")
        checksum = record.get("checksum")
        reference_id = record.get("reference_id")
        if isinstance(source_path, str):
            by_path[source_path] = record
        if isinstance(checksum, str):
            by_checksum[checksum] = record
        if isinstance(reference_id, str):
            used_ids.add(reference_id)
    return by_path, by_checksum, used_ids


def make_record(path: Path, group: str, sequence: int, checksum: str) -> dict[str, Any]:
    now = utc_now()
    reference_id = f"{group}_{sequence:03d}"
    _, confidence, hits = infer_reference_group(path.name, path)
    return {
        "reference_id": reference_id,
        "reference_group": group,
        "original_file_name": path.name,
        "stored_file_name": f"{reference_id}.pptx",
        "source_path": f"assets/slides/references/{reference_id}.pptx",
        "source_kind": source_kind_for_path(path),
        "deck_type_primary": group,
        "deck_type_secondary": [],
        "language": infer_language(path.name),
        "source_country": None,
        "source_locale": None,
        "design_culture": [],
        "checksum": checksum,
        "status": "raw_unparsed",
        "inference": {
            "confidence": confidence,
            "method": "filename_keyword_heuristic",
            "matched_keywords": hits,
            "requires_human_review": confidence < 0.75,
        },
        "created_at": now,
        "updated_at": now,
    }


def make_canonical_existing_record(path: Path, checksum: str) -> dict[str, Any]:
    now = utc_now()
    reference_id = path.stem
    group = group_from_reference_id(reference_id)
    if group not in REFERENCE_GROUPS:
        group = "unknown"
    _, confidence, hits = infer_reference_group(path.name, path)
    return {
        "reference_id": reference_id,
        "reference_group": group,
        "original_file_name": path.name,
        "stored_file_name": path.name,
        "source_path": base_relative(path),
        "source_kind": source_kind_for_path(path),
        "deck_type_primary": group,
        "deck_type_secondary": [],
        "language": infer_language(path.name),
        "source_country": None,
        "source_locale": None,
        "design_culture": [],
        "checksum": checksum,
        "status": "raw_unparsed",
        "inference": {
            "confidence": confidence,
            "method": "canonical_filename_existing",
            "matched_keywords": hits,
            "requires_human_review": confidence < 0.75,
        },
        "created_at": now,
        "updated_at": now,
    }


def normalize_references(*, dry_run: bool = False, force_rehash: bool = False) -> dict[str, Any]:
    REFERENCE_ROOT.mkdir(parents=True, exist_ok=True)
    index = load_reference_index() or {
        "schema_version": "1.0",
        "reference_root": "assets/slides/references",
        "references": [],
    }
    by_path, by_checksum, used_ids = build_existing_maps(index)
    records = reference_records(index)
    actions: list[dict[str, Any]] = []

    for path in sorted(REFERENCE_ROOT.rglob("*.pptx")):
        if path.name.startswith("~$"):
            continue
        rel = base_relative(path)
        checksum = file_sha256(path) if force_rehash or rel not in by_path else str(by_path[rel].get("checksum"))
        existing = by_path.get(rel)
        if existing:
            reference_id = str(existing.get("reference_id", ""))
            if validate_reference_id(reference_id) and not validate_reference_id(path.stem):
                target = path.with_name(f"{reference_id}.pptx")
                existing["stored_file_name"] = target.name
                existing["source_path"] = base_relative(target)
                existing["checksum"] = checksum
                existing["updated_at"] = utc_now()
                if target.exists():
                    actions.append({"action": "repoint_existing_to_canonical_copy", "from": rel, "to": base_relative(target), "reference_id": reference_id})
                else:
                    actions.append({"action": "rename_existing_to_canonical", "from": rel, "to": base_relative(target), "reference_id": reference_id})
                    if not dry_run:
                        try:
                            path.rename(target)
                        except PermissionError:
                            shutil.copy2(path, target)
                            actions[-1]["action"] = "copy_existing_after_rename_denied"
                            actions[-1]["left_original_unindexed"] = rel
                continue
            existing["stored_file_name"] = path.name
            existing["checksum"] = checksum
            existing["updated_at"] = utc_now()
            actions.append({"action": "indexed_existing", "source_path": rel, "reference_id": existing.get("reference_id")})
            continue

        checksum_match = by_checksum.get(checksum)
        if checksum_match and not (BASE_DIR / str(checksum_match.get("source_path", ""))).exists():
            checksum_match["stored_file_name"] = path.name
            checksum_match["source_path"] = rel
            checksum_match["checksum"] = checksum
            checksum_match["updated_at"] = utc_now()
            actions.append({"action": "repaired_moved_index_record", "source_path": rel, "reference_id": checksum_match.get("reference_id")})
            continue

        if validate_reference_id(path.stem):
            record = make_canonical_existing_record(path, checksum)
            if record["reference_id"] in used_ids:
                actions.append({"action": "duplicate_canonical_skipped", "source_path": rel, "reference_id": record["reference_id"]})
                continue
            records.append(record)
            used_ids.add(record["reference_id"])
            by_checksum[checksum] = record
            actions.append({"action": "index_canonical_existing", "source_path": rel, "reference_id": record["reference_id"]})
            continue

        duplicate = by_checksum.get(checksum)
        if duplicate:
            actions.append(
                {
                    "action": "duplicate_source_left_unindexed",
                    "source_path": rel,
                    "canonical_reference_id": duplicate.get("reference_id"),
                    "canonical_source_path": duplicate.get("source_path"),
                }
            )
            continue

        group, _, _ = infer_reference_group(path.name, path)
        if group not in REFERENCE_GROUPS:
            group = "unknown"
        sequence = next_sequence(group, used_ids)
        reference_id = f"{group}_{sequence:03d}"
        used_ids.add(reference_id)
        target = path.with_name(canonical_name(group, sequence))
        while target.exists() and target.resolve() != path.resolve():
            sequence += 1
            reference_id = f"{group}_{sequence:03d}"
            used_ids.add(reference_id)
            target = path.with_name(canonical_name(group, sequence))

        record = make_record(path, group, sequence, checksum)
        record["reference_id"] = reference_id
        record["stored_file_name"] = target.name
        record["source_path"] = base_relative(target)
        records.append(record)
        by_checksum[checksum] = record
        if path.resolve() != target.resolve():
            actions.append({"action": "rename", "from": base_relative(path), "to": base_relative(target), "reference_id": reference_id})
            if not dry_run:
                try:
                    path.rename(target)
                except PermissionError:
                    shutil.copy2(path, target)
                    actions[-1]["action"] = "copy_after_rename_denied"
                    actions[-1]["left_original_unindexed"] = base_relative(path)
        else:
            actions.append({"action": "index", "source_path": base_relative(path), "reference_id": reference_id})

    if not dry_run:
        save_reference_index(index, REFERENCE_INDEX_PATH)
    return {
        "schema_version": "1.0",
        "dry_run": dry_run,
        "index_path": base_relative(REFERENCE_INDEX_PATH),
        "reference_count": len(reference_records(index)),
        "actions": actions,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Normalize raw reference PPTX filenames and update references/index.json.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-rehash", action="store_true")
    args = parser.parse_args(argv)
    payload = normalize_references(dry_run=args.dry_run, force_rehash=args.force_rehash)
    print(f"reference_count={payload['reference_count']}")
    print(f"actions={len(payload['actions'])}")
    print(payload["index_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
