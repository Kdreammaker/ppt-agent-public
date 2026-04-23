from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from system.deck_models import DeckSpec


def utc_stamp() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")


def base_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(BASE_DIR).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_json_value(value: str, label: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must be valid JSON: {exc}") from exc


def ensure_slide(data: dict[str, Any], slide_number: int) -> dict[str, Any]:
    slides = data.get("slides")
    if not isinstance(slides, list):
        raise ValueError("spec.slides must be a list")
    if slide_number < 1 or slide_number > len(slides):
        raise ValueError(f"slide must be between 1 and {len(slides)}")
    slide = slides[slide_number - 1]
    if not isinstance(slide, dict):
        raise ValueError(f"slides[{slide_number}] must be an object")
    return slide


def ensure_dict(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if value is None:
        value = {}
        parent[key] = value
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object")
    return value


def ensure_list(parent: dict[str, Any], key: str) -> list[Any]:
    value = parent.get(key)
    if value is None:
        value = []
        parent[key] = value
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list")
    return value


def operation_count(args: argparse.Namespace) -> int:
    return sum(
        1
        for condition in (
            args.text_slot is not None,
            args.image_slot is not None,
            args.chart_slot is not None,
            args.table_slot is not None,
            args.speaker_note is not None,
            args.report_note is not None,
        )
        if condition
    )


def apply_patch_operation(data: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    if operation_count(args) != 1:
        raise ValueError("Exactly one patch operation must be provided")
    slide = ensure_slide(data, args.slide)
    before: Any = None
    after: Any = None
    operation: str
    slot: str | None = None

    if args.text_slot is not None:
        slots = ensure_dict(slide, "text_slots")
        slot = args.text_slot
        before = slots.get(slot)
        after = args.value
        if after is None:
            raise ValueError("--value is required for --text-slot")
        slots[slot] = after
        operation = "set_text_slot"
    elif args.image_slot is not None:
        slots = ensure_dict(slide, "image_slots")
        slot = args.image_slot
        before = slots.get(slot)
        after = args.value
        if after is None:
            raise ValueError("--value is required for --image-slot")
        slots[slot] = after
        operation = "set_image_slot"
    elif args.chart_slot is not None:
        slots = ensure_dict(slide, "chart_slots")
        slot = args.chart_slot
        before = slots.get(slot)
        after = parse_json_value(args.json_value or "", "--json")
        slots[slot] = after
        operation = "set_chart_slot"
    elif args.table_slot is not None:
        slots = ensure_dict(slide, "table_slots")
        slot = args.table_slot
        before = slots.get(slot)
        after = parse_json_value(args.json_value or "", "--json")
        slots[slot] = after
        operation = "set_table_slot"
    elif args.speaker_note is not None:
        notes = ensure_list(slide, "speaker_notes")
        before = list(notes)
        notes.append(args.speaker_note)
        after = list(notes)
        operation = "append_speaker_note"
    elif args.report_note is not None:
        notes = ensure_list(slide, "report_notes")
        before = list(notes)
        notes.append(args.report_note)
        after = list(notes)
        operation = "append_report_note"
    else:
        raise ValueError("No operation provided")
    return {
        "operation": operation,
        "slide": args.slide,
        "slot": slot,
        "before": before,
        "after": after,
    }


def validate_spec(data: dict[str, Any]) -> None:
    DeckSpec.model_validate(data)


def report_paths(spec_path: Path, report_dir: Path) -> tuple[Path, Path]:
    return report_dir / f"{spec_path.stem}_patch_summary.json", report_dir / f"{spec_path.stem}_patch_summary.md"


def write_reports(payload: dict[str, Any], report_json: Path, report_md: Path) -> None:
    write_json(report_json, payload)
    lines = [
        "# Deck Spec Patch Summary",
        "",
        f"- status: {payload['status']}",
        f"- operation: {payload['patch']['operation']}",
        f"- slide: {payload['patch']['slide']}",
        f"- slot: {payload['patch'].get('slot')}",
        f"- source: {payload['source_path']}",
        f"- output: {payload['output_path']}",
        f"- changed: {payload['changed']}",
    ]
    report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def patch_spec_file(
    spec_path: Path,
    args: argparse.Namespace,
    *,
    output_path: Path | None = None,
    backup_dir: Path | None = None,
    report_dir: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    spec_path = spec_path.resolve()
    original_data = load_json(spec_path)
    patched_data = copy.deepcopy(original_data)
    before_hash = file_sha256(spec_path)
    patch_record = apply_patch_operation(patched_data, args)
    validate_spec(patched_data)

    target_path = output_path.resolve() if output_path else spec_path
    backup_path: Path | None = None
    changed = original_data != patched_data
    if not dry_run:
        if target_path == spec_path:
            backup_root = backup_dir.resolve() if backup_dir else BASE_DIR / "outputs" / "spec_patch_backups"
            backup_path = backup_root / f"{spec_path.stem}_{utc_stamp()}{spec_path.suffix}"
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(spec_path, backup_path)
        write_json(target_path, patched_data)
    report_root = report_dir.resolve() if report_dir else BASE_DIR / "outputs" / "reports"
    report_json, report_md = report_paths(target_path, report_root)
    payload = {
        "schema_version": "1.0",
        "command": "patch_deck_spec",
        "status": "passed",
        "source_path": base_relative(spec_path),
        "output_path": base_relative(target_path),
        "backup_path": base_relative(backup_path) if backup_path else None,
        "dry_run": dry_run,
        "changed": changed,
        "source_sha256_before": before_hash,
        "output_sha256_after": file_sha256(target_path) if target_path.exists() and not dry_run else None,
        "patch": patch_record,
        "validation_summary": {
            "schema_valid": True,
            "full_spec_echoed": False,
        },
    }
    write_reports(payload, report_json, report_md)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Patch one slide/slot in a deck spec without rewriting it by hand.")
    parser.add_argument("spec_path")
    parser.add_argument("--slide", type=int, required=True)
    parser.add_argument("--text-slot", default=None)
    parser.add_argument("--image-slot", default=None)
    parser.add_argument("--chart-slot", default=None)
    parser.add_argument("--table-slot", default=None)
    parser.add_argument("--speaker-note", default=None)
    parser.add_argument("--report-note", default=None)
    parser.add_argument("--value", default=None)
    parser.add_argument("--json", dest="json_value", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--backup-dir", default=None)
    parser.add_argument("--report-dir", default=None)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = patch_spec_file(
            Path(args.spec_path),
            args,
            output_path=Path(args.output) if args.output else None,
            backup_dir=Path(args.backup_dir) if args.backup_dir else None,
            report_dir=Path(args.report_dir) if args.report_dir else None,
            dry_run=args.dry_run,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
