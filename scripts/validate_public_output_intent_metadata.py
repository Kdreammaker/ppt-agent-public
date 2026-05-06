from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_INTENTS = ("design_visual", "editable_office", "balanced")
PROMPT = "Create a 4-slide planning-first presentation about a neighborhood composting pilot."
REPO_REPORT_ROOT = BASE_DIR / "outputs" / "reports"


def run(command: list[str], *, timeout: int = 600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=BASE_DIR, capture_output=True, text=True, check=False, timeout=timeout)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    assert_true(isinstance(data, dict), f"{path} must contain an object")
    return data


def repo_report_snapshot() -> dict[str, tuple[int, int]]:
    if not REPO_REPORT_ROOT.exists():
        return {}
    snapshot: dict[str, tuple[int, int]] = {}
    for path in REPO_REPORT_ROOT.rglob("*"):
        if path.is_file():
            stat = path.stat()
            snapshot[path.relative_to(REPO_REPORT_ROOT).as_posix()] = (stat.st_size, stat.st_mtime_ns)
    return snapshot


def repo_report_changes(before: dict[str, tuple[int, int]]) -> list[str]:
    after = repo_report_snapshot()
    return sorted(name for name, state in after.items() if before.get(name) != state)


def validate_setup(workspace: Path, intent: str) -> dict[str, Any]:
    result = run(
        [
            sys.executable,
            "scripts/ppt_setup.py",
            "--workspace",
            workspace.as_posix(),
            "--force",
            "--skip-version-check",
            "--output-intent",
            intent,
        ],
        timeout=360,
    )
    assert_true(result.returncode == 0, result.stderr or result.stdout)
    report_path = workspace / "outputs" / "reports" / "ppt_setup_report.json"
    setup_summary_path = workspace / "outputs" / "reports" / "public_setup_summary.json"
    setup_summary_md = workspace / "outputs" / "reports" / "public_setup_summary.md"
    report = load_json(report_path)
    setup_summary = load_json(setup_summary_path)
    markdown = setup_summary_md.read_text(encoding="utf-8", errors="ignore")
    assert_true(report.get("output_intent") == intent, f"setup report selected intent mismatch for {intent}")
    intents = setup_summary.get("output_intent_options")
    assert_true(isinstance(intents, dict), "setup summary missing output intent options")
    assert_true(intents.get("default") == "balanced", "setup summary default intent changed")
    assert_true(intents.get("selected") == intent, f"setup summary selected intent mismatch for {intent}")
    assert_true(f"Selected: `{intent}`" in markdown, f"setup Markdown missing selected intent {intent}")
    commands = report.get("next_commands", {}).get("natural_language_public")
    assert_true(isinstance(commands, dict), "setup report missing public make commands")
    for key in ("assistant_checkpoint", "assistant_final_after_review", "auto_fast_draft"):
        assert_true(f"--output-intent {intent}" in str(commands.get(key, "")), f"{key} missing selected intent {intent}")
    return {
        "setup_report": report_path.as_posix(),
        "public_setup_summary": setup_summary_path.as_posix(),
        "public_setup_summary_md": setup_summary_md.as_posix(),
        "selected_output_intent": intent,
    }


def validate_make_report(report_path: Path, *, intent: str, expected_status: str, should_build: bool) -> dict[str, Any]:
    report = load_json(report_path)
    assert_true(report.get("status") == expected_status, f"{report_path} status mismatch: {report.get('status')}")
    assert_true(report.get("output_intent") == intent, f"{report_path} selected output intent mismatch")
    metadata = report.get("output_intent_metadata")
    assert_true(isinstance(metadata, dict), f"{report_path} missing output intent metadata")
    assert_true(metadata.get("available") == list(OUTPUT_INTENTS), f"{report_path} output intent options changed")
    assert_true(metadata.get("default") == "balanced", f"{report_path} default intent changed")
    assert_true(metadata.get("selected") == intent, f"{report_path} metadata selected intent mismatch")
    assert_true(
        metadata.get("behavior") == "metadata_only_no_renderer_change",
        f"{report_path} output intent must remain metadata-only",
    )
    artifacts = report.get("artifacts")
    assert_true(isinstance(artifacts, dict), f"{report_path} missing artifacts")
    if should_build:
        assert_true(isinstance(artifacts.get("pptx"), str) and Path(artifacts["pptx"]).exists(), "approved build missing PPTX")
        assert_true(isinstance(artifacts.get("html"), str) and Path(artifacts["html"]).exists(), "approved build missing HTML")
    else:
        assert_true(artifacts.get("pptx") is None, "checkpoint should not expose PPTX")
        assert_true(artifacts.get("html") is None, "checkpoint should not expose HTML")
    return {"report": report_path.as_posix(), "status": expected_status, "selected_output_intent": intent}


def validate_make(workspace: Path, intent: str) -> dict[str, Any]:
    checkpoint_id = f"output-intent-{intent}-checkpoint"
    checkpoint = run(
        [
            sys.executable,
            "scripts/ppt_make.py",
            PROMPT,
            "--workspace",
            workspace.as_posix(),
            "--mode",
            "assistant",
            "--project-id",
            checkpoint_id,
            "--skip-version-check",
            "--output-intent",
            intent,
        ],
        timeout=420,
    )
    assert_true(checkpoint.returncode == 0, checkpoint.stderr or checkpoint.stdout)
    checkpoint_report = workspace / "outputs" / "projects" / checkpoint_id / "reports" / "ppt_make_report.json"
    checkpoint_result = validate_make_report(
        checkpoint_report,
        intent=intent,
        expected_status="waiting_for_approval",
        should_build=False,
    )

    approved_id = f"output-intent-{intent}-approved"
    approved = run(
        [
            sys.executable,
            "scripts/ppt_make.py",
            PROMPT,
            "--workspace",
            workspace.as_posix(),
            "--mode",
            "assistant",
            "--build-approved",
            "--project-id",
            approved_id,
            "--skip-version-check",
            "--output-intent",
            intent,
        ],
        timeout=600,
    )
    assert_true(approved.returncode == 0, approved.stderr or approved.stdout)
    approved_report = workspace / "outputs" / "projects" / approved_id / "reports" / "ppt_make_report.json"
    approved_result = validate_make_report(
        approved_report,
        intent=intent,
        expected_status="built",
        should_build=True,
    )
    return {"checkpoint": checkpoint_result, "approved": approved_result}


def validate_invalid_intent(output_root: Path) -> dict[str, Any]:
    workspace = output_root / "workspace-invalid"
    setup = run(
        [
            sys.executable,
            "scripts/ppt_setup.py",
            "--workspace",
            workspace.as_posix(),
            "--force",
            "--skip-version-check",
            "--output-intent",
            "invalid_intent",
        ],
        timeout=120,
    )
    assert_true(setup.returncode != 0, "ppt_setup accepted invalid output intent")
    make = run(
        [
            sys.executable,
            "scripts/ppt_make.py",
            PROMPT,
            "--workspace",
            workspace.as_posix(),
            "--mode",
            "assistant",
            "--skip-version-check",
            "--output-intent",
            "invalid_intent",
        ],
        timeout=120,
    )
    assert_true(make.returncode != 0, "ppt_make accepted invalid output intent")
    return {"status": "pass", "setup_returncode": setup.returncode, "make_returncode": make.returncode}


def validate_public_private_scan(output_root: Path) -> dict[str, Any]:
    patterns = {
        "drive_marker": re.compile(r"drive\.google\.com|docs\.google\.com|\bdrive[_-]?id\b", re.IGNORECASE),
        "token": re.compile(r"xox[baprs]-|sk-[A-Za-z0-9_-]{12,}|AIza[0-9A-Za-z_-]{20,}", re.IGNORECASE),
        "unsafe_package_path": re.compile(r"\.\./packages|\./packages|/packages|packages\\|[A-Za-z]:\\.*packages", re.IGNORECASE),
        "raw_payload_marker": re.compile(r"\bprivate_prompt\b|\braw_payload\b", re.IGNORECASE),
    }
    issues: list[dict[str, str]] = []
    for path in output_root.rglob("*.json"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in patterns.items():
            if pattern.search(text):
                issues.append({"path": path.as_posix(), "issue": name})
    for path in output_root.rglob("*.md"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in patterns.items():
            if pattern.search(text):
                issues.append({"path": path.as_posix(), "issue": name})
    assert_true(not issues, f"public/private scan failed: {issues[:5]}")
    return {"scanned_root": output_root.as_posix(), "issues": 0}


def validate_readme_output_intent_sequence() -> dict[str, Any]:
    text = (BASE_DIR / "README.md").read_text(encoding="utf-8", errors="ignore")
    checkpoint = (
        'python scripts\\ppt_make.py "Make a 6 slide executive market review for AI launch priorities" '
        '--workspace "<workspace>" --mode assistant --output-intent design_visual'
    )
    approved = (
        'python scripts\\ppt_make.py "Make a 6 slide executive market review for AI launch priorities" '
        '--workspace "<workspace>" --mode assistant --build-approved --output-intent design_visual'
    )
    assert_true(checkpoint in text, "README checkpoint example missing design_visual output intent")
    assert_true(approved in text, "README approved build example does not preserve design_visual output intent")
    assert_true(text.index(checkpoint) < text.index(approved), "README approved example should follow checkpoint example")
    return {"status": "pass", "checkpoint_intent": "design_visual", "approved_intent": "design_visual"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate public output intent metadata across setup and make flows.")
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args(argv)
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    before_reports = repo_report_snapshot()
    valid: dict[str, Any] = {}
    for intent in OUTPUT_INTENTS:
        workspace = output_root / f"workspace-{intent}"
        valid[intent] = {
            "setup": validate_setup(workspace, intent),
            "make": validate_make(workspace, intent),
        }
    changes = repo_report_changes(before_reports)
    assert_true(not changes, f"repo checkout outputs/reports changed during validation: {changes}")
    result = {
        "status": "pass",
        "readme_output_intent_sequence": validate_readme_output_intent_sequence(),
        "valid_intents": valid,
        "invalid_intent_rejected": validate_invalid_intent(output_root / "invalid-intent"),
        "public_private_scan": validate_public_private_scan(output_root),
        "repo_report_leak_scan": {"repo_report_root": REPO_REPORT_ROOT.as_posix(), "changed_files": []},
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
