from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
CONTRACT_ID = "ppt-maker.public-setup-summary.v0"
OUTPUT_INTENTS = ["design_visual", "editable_office", "balanced"]
CLASSIFICATIONS = [
    "native_editable_required",
    "editable_shape_table_allowed",
    "design_visual_allowed",
    "not_applicable",
]
PRIVATE_PATTERNS = (
    re.compile(r"[A-Za-z]:\\"),
    re.compile(r"/Users/"),
    re.compile(r"/home/"),
    re.compile(r"\bdrive[_-]?id\b", re.IGNORECASE),
    re.compile(r"\bsource_attachment\b", re.IGNORECASE),
    re.compile(r"\braw_payload\b", re.IGNORECASE),
    re.compile(r"\bprivate_prompt\b", re.IGNORECASE),
    re.compile(r"\baccess_token\b", re.IGNORECASE),
    re.compile(r"\brefresh_token\b", re.IGNORECASE),
    re.compile(r"\bapproved_asset_ref\b", re.IGNORECASE),
    re.compile(r"\bpreferred_asset_ref\b", re.IGNORECASE),
    re.compile(r"\bunapproved_asset_records\b", re.IGNORECASE),
)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    assert_true(isinstance(data, dict), f"{path} must contain a JSON object")
    return data


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def assert_public_safe(path: Path) -> None:
    text = path.read_text(encoding="utf-8-sig", errors="ignore")
    hits = [pattern.pattern for pattern in PRIVATE_PATTERNS if pattern.search(text)]
    assert_true(not hits, f"{path} contains private marker patterns: {hits}")


def run(command: list[str], *, timeout: int = 240) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=BASE_DIR, capture_output=True, text=True, check=False, timeout=timeout)


def validate_summary(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    assert_public_safe(path)
    assert_true(payload.get("contract") == CONTRACT_ID, f"{path} contract mismatch")
    assert_true(payload.get("status") == "ready", f"{path} status changed")

    intents = payload.get("output_intent_options")
    assert_true(isinstance(intents, dict), f"{path} missing output intent options")
    assert_true(intents.get("available") == OUTPUT_INTENTS, f"{path} output intent options changed")
    assert_true(intents.get("default") == "balanced", f"{path} default output intent changed")
    assert_true(
        intents.get("behavior") == "explanatory_metadata_only_no_renderer_change",
        f"{path} output intent must remain explanatory",
    )

    checkpoint = payload.get("one_slide_sample_checkpoint")
    assert_true(isinstance(checkpoint, dict), f"{path} missing one-slide sample checkpoint")
    assert_true(checkpoint.get("recommended") is True, f"{path} sample checkpoint should be recommended")
    assert_true(
        checkpoint.get("requires_explicit_approval_before_full_build") is True,
        f"{path} sample checkpoint should require approval",
    )

    knowledge = payload.get("uploaded_knowledge_assets_summary")
    assert_true(isinstance(knowledge, dict), f"{path} missing uploaded knowledge/assets summary")
    assert_true(knowledge.get("counts_only") is True, f"{path} knowledge/assets summary must be counts-only")
    assert_true(knowledge.get("raw_sources_included") is False, f"{path} raw sources must not be included")
    asset_state = knowledge.get("asset_state_summary")
    assert_true(isinstance(asset_state, dict), f"{path} missing asset state counts")
    for key in ("approved", "requested", "unknown"):
        assert_true(isinstance(asset_state.get(key), int), f"{path} asset count {key} must be integer")

    roles = payload.get("editable_output_roles")
    assert_true(isinstance(roles, dict), f"{path} missing editable output roles")
    assert_true(roles.get("pptx") == "native_editable_primary_output", f"{path} PPTX role changed")
    assert_true(roles.get("html") == "review_or_presentation_companion", f"{path} HTML role changed")
    assert_true(roles.get("shared_ir_role") == "read_only_explanation_and_qa", f"{path} shared IR role changed")
    assert_true(roles.get("html_screenshot_used_in_pptx") is False, f"{path} screenshot policy changed")

    readiness = payload.get("editable_chart_table_readiness")
    assert_true(isinstance(readiness, dict), f"{path} missing editable chart/table readiness")
    assert_true(readiness.get("classification_values") == CLASSIFICATIONS, f"{path} classification values changed")
    counts = readiness.get("classification_counts")
    assert_true(isinstance(counts, dict), f"{path} missing classification counts")
    for key in CLASSIFICATIONS:
        assert_true(isinstance(counts.get(key), int), f"{path} classification count {key} must be integer")
    assert_true(readiness.get("summary_only") is True, f"{path} readiness must remain summary-only")
    assert_true(
        readiness.get("native_chart_table_rendering_enabled") is False,
        f"{path} must not enable native chart/table rendering",
    )

    hygiene = payload.get("public_private_hygiene")
    assert_true(isinstance(hygiene, dict), f"{path} missing public/private hygiene")
    assert_true(not any(hygiene.values()), f"{path} hygiene booleans must remain false")
    non_goals = payload.get("non_goals")
    assert_true(isinstance(non_goals, dict), f"{path} missing non-goals")
    assert_true(not any(non_goals.values()), f"{path} non-goals must remain false")
    return {
        "path": path.as_posix(),
        "asset_state_summary": asset_state,
        "classification_counts": counts,
    }


def write_fixture(root: Path) -> tuple[Path, Path]:
    setup = {
        "contract": "ppt-maker.setup-ux-summary.v0",
        "output_intent_options": {"available": OUTPUT_INTENTS, "default": "balanced"},
        "one_slide_sample_review_checkpoint": {
            "recommended": True,
            "requires_explicit_approval_before_full_build": True,
            "private_prompt": "SHOULD_NOT_LEAK",
        },
        "uploaded_knowledge_assets_summary": {
            "reference_file_count": 3,
            "asset_state_summary": {"approved": 1, "requested": 2, "unknown": 1},
            "raw_payload": {"private": True},
            "source_attachment": r"C:\private\source.pdf",
        },
        "editable_output_explanation": {
            "pptx": "native_editable_primary_output",
            "html": "review_or_presentation_companion",
            "shared_ir_role": "read_only_explanation_and_qa",
            "html_screenshot_used_in_pptx": False,
        },
    }
    readiness = {
        "contract": "ppt-maker.editable-office-readiness.v0",
        "diagnostics_summary": {
            "candidate_count": 4,
            "classification_counts": {
                "native_editable_required": 1,
                "editable_shape_table_allowed": 1,
                "design_visual_allowed": 1,
                "not_applicable": 2,
            },
        },
        "approved_asset_ref": r"C:\private\approved.png",
        "drive_id": "SHOULD_NOT_LEAK",
    }
    setup_path = root / "fixture_setup_ux_summary.json"
    readiness_path = root / "fixture_editable_office_readiness.json"
    write_json(setup_path, setup)
    write_json(readiness_path, readiness)
    return setup_path, readiness_path


def validate_setup_wrapper(output_root: Path) -> dict[str, Any]:
    workspace = output_root / "workspace"
    result = run(
        [
            sys.executable,
            "scripts/ppt_setup.py",
            "--workspace",
            workspace.as_posix(),
            "--force",
            "--skip-version-check",
        ],
        timeout=360,
    )
    assert_true(result.returncode == 0, result.stderr or result.stdout)
    report = workspace / "outputs" / "reports" / "public_setup_summary.json"
    setup_report = load_json(workspace / "outputs" / "reports" / "ppt_setup_report.json")
    assert_true(setup_report.get("setup_summary") == "outputs/reports/public_setup_summary.json", "setup report missing setup summary path")
    return validate_summary(report)


def validate_fixture_export(output_root: Path) -> dict[str, Any]:
    fixture_root = output_root / "fixture"
    setup_path, readiness_path = write_fixture(fixture_root)
    output = output_root / "fixture_public_setup_summary.json"
    result = run(
        [
            sys.executable,
            "scripts/build_public_setup_summary.py",
            "--setup-ux-summary",
            setup_path.as_posix(),
            "--editable-office-readiness",
            readiness_path.as_posix(),
            "--output",
            output.as_posix(),
        ]
    )
    assert_true(result.returncode == 0, result.stderr or result.stdout)
    summary = validate_summary(output)
    assert_true(
        summary["asset_state_summary"] == {"approved": 1, "requested": 2, "unknown": 1},
        "fixture asset-state counts were not preserved",
    )
    assert_true(
        summary["classification_counts"]["native_editable_required"] == 1
        and summary["classification_counts"]["not_applicable"] == 2,
        "fixture classification counts were not preserved",
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate public setup summary generation.")
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args(argv)
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    result = {
        "status": "pass",
        "setup_wrapper": validate_setup_wrapper(output_root / "setup-wrapper"),
        "fixture_export": validate_fixture_export(output_root / "fixture-export"),
        "public_private_scan": {
            "scanned_files": [
                (output_root / "setup-wrapper" / "workspace" / "outputs" / "reports" / "public_setup_summary.json").as_posix(),
                (output_root / "fixture-export" / "fixture_public_setup_summary.json").as_posix(),
            ],
            "issues": 0,
        },
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
