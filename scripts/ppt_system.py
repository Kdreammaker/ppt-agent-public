from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.build_deck import (
    build_deck_from_spec,
    resolve_path,
)
from scripts.build_deck import load_spec as load_deck_spec
from scripts.build_dual_outputs import build_dual_outputs
from scripts.build_html_deck import build_html
from scripts.deliver_project_output import DEFAULT_POLICY_PATH, deliver_project_output
from scripts.output_bundles import (
    default_project_id,
    default_run_id,
    mirror_project_outputs,
    mirror_run_outputs,
)
from scripts.reference_pipeline import (
    CAPTURE_DEDUPE_MODES,
    DEFAULT_CURATION_ROOT,
    base_relative as reference_base_relative,
    file_sha256,
    load_json,
    register_reference_file,
)
from scripts.render_ascii_blueprint import render_ascii_blueprint

GENERATED_REFERENCE_ROOT = BASE_DIR / "assets" / "slides" / "references" / "generated"


def manifest_command(args: list[str]) -> list[str]:
    normalized: list[str] = []
    for arg in args:
        if arg == sys.executable:
            normalized.append("python")
            continue
        try:
            path = Path(arg)
            if path.is_absolute() and path.resolve().is_relative_to(BASE_DIR):
                normalized.append(path.resolve().relative_to(BASE_DIR).as_posix())
                continue
        except OSError:
            pass
        normalized.append(arg)
    return normalized


def base_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(BASE_DIR).as_posix()
    except ValueError:
        return resolved.as_posix()


def run_command(args: list[str]) -> dict[str, Any]:
    print("$ " + " ".join(args), flush=True)
    subprocess.run(args, cwd=BASE_DIR, check=True)
    return {"command": manifest_command(args), "status": "passed"}


def read_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def read_delivery_policy(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"enabled": False}
    return load_json(path)


def capture_generated_reference(
    *,
    output_path: Path,
    spec_path: Path,
    project_id: str | None,
    register_index: bool = True,
    capture_dedupe_mode: str = "always_new",
    is_regression_sample: bool = False,
) -> dict[str, Any]:
    if not output_path.exists():
        raise FileNotFoundError(output_path)
    GENERATED_REFERENCE_ROOT.mkdir(parents=True, exist_ok=True)
    checksum = file_sha256(output_path)
    captured_at = dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")
    base_audit = {
        "enabled": True,
        "capture_dedupe_mode": capture_dedupe_mode,
        "source_output_path": base_relative(output_path),
        "source_spec_path": base_relative(spec_path),
        "project_id": project_id,
        "checksum": checksum,
        "captured_at": captured_at,
    }
    if capture_dedupe_mode == "skip_regression_samples" and is_regression_sample:
        return {
            **base_audit,
            "action": "skipped_regression_sample",
            "reference_id": None,
            "reference_path": None,
            "notes": "Generated reference capture skipped by policy for regression/sample build.",
        }
    if register_index:
        record = register_reference_file(
            output_path,
            group="generated",
            original_file_name=output_path.name,
            source_kind="generated_deck",
            copy_to_reference_root=True,
            capture_dedupe_mode=capture_dedupe_mode,
        )
        target = BASE_DIR / str(record["source_path"])
        reference_id = str(record["reference_id"])
        action = str(record.get("capture_action", "created_new"))
    else:
        target = GENERATED_REFERENCE_ROOT / output_path.name
        shutil.copy2(output_path, target)
        reference_id = output_path.stem
        action = "created_unregistered"

    index_path = GENERATED_REFERENCE_ROOT / "index.json"
    index = read_json_object(index_path) or {"schema_version": "1.0", "items": []}
    items = [
        item
        for item in index.get("items", [])
        if isinstance(item, dict) and item.get("reference_id") != reference_id
    ]
    items.append(
        {
            "reference_id": reference_id,
            "deck_id": target.stem,
            "deck_path": reference_base_relative(target),
            "source_output_path": base_relative(output_path),
            "source_spec_path": base_relative(spec_path),
            "project_id": project_id,
            "captured_at": captured_at,
            "status": "raw_generated_reference" if action == "created_new" else action,
            "capture_dedupe_mode": capture_dedupe_mode,
            "checksum": checksum,
            "notes": "Generated decks are raw reference inputs only. They must pass categorizing, library review, and template promotion before production use.",
        }
    )
    index = {
        "schema_version": "1.0",
        "reference_root": base_relative(GENERATED_REFERENCE_ROOT),
        "policy": "generated_decks_are_raw_reference_inputs_not_runtime_templates",
        "items": sorted(items, key=lambda item: str(item.get("reference_id", item.get("deck_id", "")))),
    }
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        **base_audit,
        "action": action,
        "reference_id": reference_id,
        "reference_path": reference_base_relative(target),
        "notes": "Generated decks are raw reference inputs only. They must pass categorizing, library review, and template promotion before production use.",
    }


def is_regression_sample_build(*, spec_path: Path, output_path: Path, project_id: str | None) -> bool:
    tokens = {
        spec_path.stem.casefold(),
        output_path.stem.casefold(),
        (project_id or "").casefold(),
    }
    return any("sample" in token or "regression" in token for token in tokens)



def command_validate_intake(args: argparse.Namespace) -> int:
    command = [sys.executable, "scripts/validate_deck_intake.py"]
    command.extend(args.paths)
    run_command(command)
    return 0


def command_compose_spec(args: argparse.Namespace) -> int:
    if args.direct_intake:
        command = [sys.executable, "scripts/compose_deck_spec_from_intake.py", args.intake_path]
        if args.output:
            command.extend(["--output", args.output])
        run_command(command)
        return 0

    intake_path = Path(args.intake_path)
    intake_stem = intake_path.stem
    plan_output = args.plan_output or f"outputs/projects/{intake_stem}/plans/deck_plan.json"
    plan_command = [sys.executable, "scripts/compose_deck_plan_from_intake.py", args.intake_path, "--output", plan_output]
    if args.operating_mode:
        plan_command.extend(["--operating-mode", args.operating_mode])
    run_command(plan_command)
    spec_command = [sys.executable, "scripts/compose_deck_spec_from_plan.py", plan_output]
    if args.output:
        spec_command.extend(["--output", args.output])
    if args.report_dir:
        spec_command.extend(["--report-dir", args.report_dir])
    run_command(spec_command)
    return 0


def command_build(args: argparse.Namespace) -> int:
    spec_path = Path(args.spec_path).resolve()
    spec, spec_dir = load_deck_spec(spec_path)
    output_path = resolve_path(spec_dir, spec["output_path"])
    delivery_policy_path = Path(args.delivery_policy).resolve()
    delivery_policy = read_delivery_policy(delivery_policy_path)
    delivery_enabled = bool(delivery_policy.get("enabled")) and not args.no_delivery
    reference_policy = delivery_policy.get("reference_learning_loop", {})
    if not isinstance(reference_policy, dict):
        reference_policy = {}
    capture_dedupe_mode = args.reference_capture_mode or str(reference_policy.get("capture_dedupe_mode", "always_new"))
    if capture_dedupe_mode not in CAPTURE_DEDUPE_MODES:
        raise ValueError(f"Unsupported reference capture mode: {capture_dedupe_mode}")
    run_id = args.run_id
    if args.auto_run_id:
        run_id = default_run_id(output_path)
    project_id = args.project_id
    if args.auto_project or delivery_enabled:
        project_id = spec.get("project_id") or default_project_id(output_path)
    output = build_deck_from_spec(spec_path)
    print(output)

    validation_results: list[dict[str, Any]] = []
    if args.validate:
        stem = output.stem
        validation_results.append(run_command([sys.executable, "scripts/validate_pptx_package.py", output.as_posix()]))
        validation_results.append(
            run_command(
                [
                    sys.executable,
                    "scripts/validate_visual_smoke.py",
                    output.as_posix(),
                    f"outputs/reports/{stem}_visual_smoke.json",
                    "--spec",
                    spec_path.relative_to(BASE_DIR).as_posix() if spec_path.is_relative_to(BASE_DIR) else spec_path.as_posix(),
                    "--keep-images",
                ]
            )
        )
        validation_results.append(
            run_command(
                [
                    sys.executable,
                    "scripts/validate_design_quality.py",
                    output.as_posix(),
                    f"outputs/reports/{stem}_quality.json",
                    "--template-spec",
                    spec_path.relative_to(BASE_DIR).as_posix() if spec_path.is_relative_to(BASE_DIR) else spec_path.as_posix(),
                ]
            )
        )
        validation_results.append(
            run_command([sys.executable, "scripts/validate_deck_design_review.py", output.as_posix()])
        )
    reference_capture: dict[str, Any] | None = None
    capture_enabled = not args.no_reference_capture and bool(reference_policy.get("capture_completed_decks", True))
    if capture_enabled:
        reference_capture = capture_generated_reference(
            output_path=output,
            spec_path=spec_path,
            project_id=project_id,
            register_index=bool(reference_policy.get("register_captured_decks", True)),
            capture_dedupe_mode=capture_dedupe_mode,
            is_regression_sample=is_regression_sample_build(spec_path=spec_path, output_path=output, project_id=project_id),
        )
        print(json.dumps({"reference_capture": reference_capture}, ensure_ascii=False))
        should_parse_reference = args.parse_captured_reference or bool(reference_policy.get("parse_captured_decks_by_default", False))
        reference_path_value = reference_capture.get("reference_path")
        if should_parse_reference and reference_capture.get("action") == "created_new" and reference_path_value:
            from scripts.parse_reference_deck import parse_reference_deck

            reference_path = BASE_DIR / str(reference_path_value)
            parsed = parse_reference_deck(reference_path, DEFAULT_CURATION_ROOT, force=False)
            print(json.dumps({"parsed_reference": parsed.get("reference_id", reference_path.stem)}, ensure_ascii=False))
        elif should_parse_reference:
            print(json.dumps({"parsed_reference": None, "reason": reference_capture.get("action")}, ensure_ascii=False))
    if run_id:
        manifest = mirror_run_outputs(
            run_id=run_id,
            spec_path=spec_path,
            output_path=output,
            validation_results=validation_results,
        )
        print(manifest)
    if project_id:
        manifest = mirror_project_outputs(
            project_id=project_id,
            spec_path=spec_path,
            output_path=output,
            validation_results=validation_results,
            reference_capture=reference_capture,
        )
        print(manifest)
        if delivery_enabled:
            delivery_manifest = deliver_project_output(
                manifest,
                policy_path=delivery_policy_path,
                drive_link=args.drive_link,
                drive_file_id=args.drive_file_id,
                share_permission_confirmed=args.share_permission_confirmed,
                slack_destination=args.slack_destination,
                slack_sent=args.slack_sent,
            )
            print(delivery_manifest["local"]["delivery_manifest_path"])
    return 0


def command_html(args: argparse.Namespace) -> int:
    html_path, manifest_path = build_html(
        Path(args.spec_path).resolve(),
        Path(args.output).resolve() if args.output else None,
    )
    print(html_path)
    print(manifest_path)
    if args.validate:
        command = [
            sys.executable,
            "scripts/validate_html_output.py",
            html_path.as_posix(),
            "--manifest",
            manifest_path.as_posix(),
        ]
        if args.browser_screenshot:
            command.append("--browser-screenshot")
        run_command(command)
    return 0


def command_build_outputs(args: argparse.Namespace) -> int:
    payload = build_dual_outputs(
        Path(args.spec_path).resolve(),
        validate=args.validate,
        report_dir=Path(args.report_dir).resolve() if args.report_dir else None,
        html_output=Path(args.html_output).resolve() if args.html_output else None,
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def command_blueprint(args: argparse.Namespace) -> int:
    md_path, json_path, payload = render_ascii_blueprint(
        Path(args.input_path).resolve(),
        kind=args.kind,
        approval_mode=args.approval_mode,
        output_md=Path(args.output_md).resolve() if args.output_md else None,
        output_json=Path(args.output_json).resolve() if args.output_json else None,
    )
    print(md_path)
    print(json_path)
    print(
        "ascii_blueprint="
        f"slides={payload['summary']['slide_count']} "
        f"images={payload['summary']['image_placeholders']} "
        f"charts={payload['summary']['chart_placeholders']} "
        f"tables={payload['summary']['table_placeholders']}"
    )
    return 0


def command_patch_spec(args: argparse.Namespace) -> int:
    command = [
        sys.executable,
        "scripts/patch_deck_spec.py",
        args.spec_path,
        "--slide",
        str(args.slide),
    ]
    for option, value in (
        ("--text-slot", args.text_slot),
        ("--image-slot", args.image_slot),
        ("--chart-slot", args.chart_slot),
        ("--table-slot", args.table_slot),
        ("--speaker-note", args.speaker_note),
        ("--report-note", args.report_note),
        ("--value", args.value),
        ("--json", args.json_value),
        ("--output", args.output),
        ("--backup-dir", args.backup_dir),
        ("--report-dir", args.report_dir),
    ):
        if value is not None:
            command.extend([option, value])
    if args.dry_run:
        command.append("--dry-run")
    run_command(command)
    return 0


def command_gate(_: argparse.Namespace) -> int:
    run_command([sys.executable, "scripts/run_regression_gate.py"])
    return 0


def command_aspect_audit(_: argparse.Namespace) -> int:
    run_command([sys.executable, "scripts/inspect_template_aspect_ratios.py"])
    return 0


def command_summary(args: argparse.Namespace) -> int:
    paths = [
        BASE_DIR / "outputs" / "reports" / "template_aspect_ratio_audit.json",
        BASE_DIR / "outputs" / "reports" / "deck_design_review.json",
        BASE_DIR / "outputs" / "reports" / "template_slot_name_audit.json",
    ]
    for path in paths:
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        print(path.relative_to(BASE_DIR).as_posix())
        print(json.dumps(data.get("summary", data), indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Template-first PPT authoring system wrapper.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_intake = subparsers.add_parser("validate-intake")
    validate_intake.add_argument("paths", nargs="*")
    validate_intake.set_defaults(func=command_validate_intake)

    compose_spec = subparsers.add_parser("compose-spec")
    compose_spec.add_argument("intake_path")
    compose_spec.add_argument("--output", default=None)
    compose_spec.add_argument("--plan-output", default=None)
    compose_spec.add_argument("--report-dir", default=None)
    compose_spec.add_argument("--operating-mode", choices=["auto", "assistant"], default=None)
    compose_spec.add_argument("--direct-intake", action="store_true", help="Compatibility path that skips deck plan creation.")
    compose_spec.set_defaults(func=command_compose_spec)

    build = subparsers.add_parser("build")
    build.add_argument("spec_path")
    build.add_argument("--run-id", default=None)
    build.add_argument("--auto-run-id", action="store_true")
    build.add_argument("--project-id", default=None)
    build.add_argument("--auto-project", action="store_true")
    build.add_argument("--validate", action="store_true")
    build.add_argument("--no-reference-capture", action="store_true")
    build.add_argument("--reference-capture-mode", choices=sorted(CAPTURE_DEDUPE_MODES), default=None)
    build.add_argument("--parse-captured-reference", action="store_true")
    build.add_argument("--no-delivery", action="store_true")
    build.add_argument("--delivery-policy", default=DEFAULT_POLICY_PATH.as_posix())
    build.add_argument("--drive-link", default=None)
    build.add_argument("--drive-file-id", default=None)
    build.add_argument("--share-permission-confirmed", action="store_true")
    build.add_argument("--slack-destination", default=None)
    build.add_argument("--slack-sent", action="store_true")
    build.set_defaults(func=command_build)

    html = subparsers.add_parser("html")
    html.add_argument("spec_path")
    html.add_argument("--output", default=None)
    html.add_argument("--validate", action="store_true")
    html.add_argument("--browser-screenshot", action="store_true")
    html.set_defaults(func=command_html)

    build_outputs = subparsers.add_parser("build-outputs")
    build_outputs.add_argument("spec_path")
    build_outputs.add_argument("--validate", action="store_true")
    build_outputs.add_argument("--report-dir", default=None)
    build_outputs.add_argument("--html-output", default=None)
    build_outputs.set_defaults(func=command_build_outputs)

    blueprint = subparsers.add_parser("blueprint")
    blueprint.add_argument("input_path")
    blueprint.add_argument("--kind", choices=["auto", "spec", "intake"], default="auto")
    blueprint.add_argument("--approval-mode", choices=["assistant", "auto"], default="assistant")
    blueprint.add_argument("--output-md", default=None)
    blueprint.add_argument("--output-json", default=None)
    blueprint.set_defaults(func=command_blueprint)

    patch_spec = subparsers.add_parser("patch-spec")
    patch_spec.add_argument("spec_path")
    patch_spec.add_argument("--slide", type=int, required=True)
    patch_spec.add_argument("--text-slot", default=None)
    patch_spec.add_argument("--image-slot", default=None)
    patch_spec.add_argument("--chart-slot", default=None)
    patch_spec.add_argument("--table-slot", default=None)
    patch_spec.add_argument("--speaker-note", default=None)
    patch_spec.add_argument("--report-note", default=None)
    patch_spec.add_argument("--value", default=None)
    patch_spec.add_argument("--json", dest="json_value", default=None)
    patch_spec.add_argument("--output", default=None)
    patch_spec.add_argument("--backup-dir", default=None)
    patch_spec.add_argument("--report-dir", default=None)
    patch_spec.add_argument("--dry-run", action="store_true")
    patch_spec.set_defaults(func=command_patch_spec)

    gate = subparsers.add_parser("gate")
    gate.set_defaults(func=command_gate)

    aspect_audit = subparsers.add_parser("aspect-audit")
    aspect_audit.set_defaults(func=command_aspect_audit)

    summary = subparsers.add_parser("summary")
    summary.set_defaults(func=command_summary)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
