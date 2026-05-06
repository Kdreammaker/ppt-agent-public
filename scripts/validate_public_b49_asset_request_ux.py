from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
REPO_REPORT_ROOT = BASE_DIR / "outputs" / "reports"
PROMPT = "Create a 4-slide planning-first presentation about an investor update."
ALLOWED_ITEM_FIELDS = {
    "request_id",
    "slide_no",
    "state",
    "asset_type",
    "required",
    "user_action",
    "user_message",
    "public_safe_reason",
}
PRIVATE_PATTERNS = {
    "private_path": re.compile(r"[A-Za-z]:\\|/Users/|/home/"),
    "drive_marker": re.compile(r"drive\.google\.com|docs\.google\.com|\bdrive[_-]?id\b", re.IGNORECASE),
    "token": re.compile(r"xox[baprs]-|sk-[A-Za-z0-9_-]{12,}|AIza[0-9A-Za-z_-]{20,}", re.IGNORECASE),
    "raw_payload_marker": re.compile(
        r"\bprivate_prompt\b|\braw_payload\b|\bsource_attachment\b|\bapproved_asset_ref\b|\bpreferred_asset_ref\b|\bunapproved_asset_records\b|\bslot_id\b",
        re.IGNORECASE,
    ),
}


def run(command: list[str], *, timeout: int = 600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=BASE_DIR, capture_output=True, text=True, check=False, timeout=timeout)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    assert_true(isinstance(payload, dict), f"{path} must contain a JSON object")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


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


def write_b49_fixture(path: Path) -> Path:
    payload = {
        "contract": "ppt-maker.b49-asset-request-summary.v0",
        "status": "internal_b49_asset_request_readiness_report",
        "summary": {"approved": 1, "requested": 1, "unknown": 1},
        "request_items": [
            {
                "request_id": "asset-request-public-approved",
                "slide_no": 1,
                "state": "approved",
                "asset_type": "hero_image",
                "required": True,
                "user_action": "no_user_action_needed",
                "user_message": "An approved visual is already available.",
                "public_safe_reason": "Approved asset is ready for this need.",
                "approved_asset_ref": r"C:\private\approved-hero.png",
            },
            {
                "request_id": "asset-request-public-requested",
                "slide_no": 2,
                "state": "requested",
                "asset_type": "supporting_image",
                "required": False,
                "user_action": "upload_or_select_recommended_asset",
                "user_message": "Upload or select a recommended supporting image.",
                "public_safe_reason": "A declared asset need has no approved asset yet.",
            },
            {
                "request_id": "asset-request-public-unknown",
                "slide_no": None,
                "state": "unknown",
                "asset_type": "unknown_asset",
                "required": False,
                "user_action": "clarify_asset_need",
                "user_message": "Clarify the missing asset need.",
                "public_safe_reason": "The asset need is incomplete or missing a usable identifier.",
                "slot_id": "SHOULD_NOT_LEAK",
            },
        ],
    }
    write_json(path, payload)
    return path


def write_malicious_b49_fixture(path: Path) -> Path:
    payload = {
        "contract": "ppt-maker.b49-asset-request-summary.v0",
        "summary": {"approved": 0, "requested": 1, "unknown": 0},
        "request_items": [
            {
                "request_id": "asset-request-public-malicious",
                "slide_no": 1,
                "state": "requested",
                "asset_type": "sk-THISSHOULDNOTLEAK123456",
                "required": False,
                "user_action": "upload_or_select_recommended_asset",
                "user_message": "Upload or select a supporting image.",
                "public_safe_reason": "A copied public field contained a token-shaped value.",
            }
        ],
    }
    write_json(path, payload)
    return path


def assert_public_safe(paths: list[Path]) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    for path in paths:
        if path.suffix.lower() == ".json":
            payload = load_json(path)
            text = json.dumps(payload.get("asset_request_summary", payload), ensure_ascii=False)
        else:
            text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in PRIVATE_PATTERNS.items():
            if pattern.search(text):
                issues.append({"path": path.as_posix(), "issue": name})
    assert_true(not issues, f"public/private scan failed: {issues[:5]}")
    return {"scanned_files": [path.as_posix() for path in paths], "issues": 0}


def assert_available(summary: dict[str, Any]) -> None:
    assert_true(summary.get("b49_asset_request_ux_enabled") is True, "B49 UX should be enabled when summary is available")
    assert_true(summary.get("status") == "available", "B49 summary should be available")
    assert_true(summary.get("metadata_only") is True, "B49 summary must remain metadata-only")
    assert_true(summary.get("renderer_behavior") == "unchanged", "renderer behavior changed")
    assert_true(summary.get("asset_insertion_behavior") == "unchanged", "asset insertion behavior changed")
    assert_true(
        summary.get("summary") == {"approved": 1, "requested": 1, "unknown": 1, "total_request_items": 3},
        "B49 public counts changed",
    )
    actions = summary.get("asset_request_actions")
    assert_true(actions.get("no_user_action_needed") == 1, "approved action count missing")
    assert_true(actions.get("upload_or_select_recommended_asset") == 1, "requested action count missing")
    assert_true(actions.get("clarify_asset_need") == 1, "unknown action count missing")
    items = summary.get("asset_request_items")
    assert_true(isinstance(items, list) and len(items) == 3, "B49 request items missing")
    states = {item.get("state"): item.get("user_action") for item in items}
    assert_true(states.get("approved") == "no_user_action_needed", "approved action mapping changed")
    assert_true(states.get("requested") == "upload_or_select_recommended_asset", "requested action mapping changed")
    assert_true(states.get("unknown") == "clarify_asset_need", "unknown action mapping changed")
    for item in items:
        assert_true(set(item) <= ALLOWED_ITEM_FIELDS, f"disallowed B49 public fields exposed: {sorted(set(item) - ALLOWED_ITEM_FIELDS)}")


def assert_unavailable(summary: dict[str, Any]) -> None:
    assert_true(summary.get("b49_asset_request_ux_enabled") is False, "B49 UX should be disabled when summary is missing")
    assert_true(summary.get("status") == "not_available", "missing B49 summary should report not_available")
    assert_true(summary.get("summary", {}).get("total_request_items") == 0, "missing B49 summary should have zero items")
    assert_true(summary.get("asset_request_items") == [], "missing B49 summary should not expose request items")


def validate_setup_available(output_root: Path, fixture: Path) -> dict[str, Any]:
    workspace = output_root / "workspace-setup-available"
    result = run(
        [
            sys.executable,
            "scripts/ppt_setup.py",
            "--workspace",
            workspace.as_posix(),
            "--force",
            "--skip-version-check",
            "--output-intent",
            "editable_office",
            "--b49-asset-request-summary",
            fixture.as_posix(),
        ],
        timeout=360,
    )
    assert_true(result.returncode == 0, result.stderr or result.stdout)
    summary_path = workspace / "outputs" / "reports" / "public_setup_summary.json"
    markdown_path = workspace / "outputs" / "reports" / "public_setup_summary.md"
    setup_report_path = workspace / "outputs" / "reports" / "ppt_setup_report.json"
    summary = load_json(summary_path)
    setup_report = load_json(setup_report_path)
    assert_available(summary["asset_request_summary"])
    assert_available(setup_report["asset_request_summary"])
    markdown = markdown_path.read_text(encoding="utf-8", errors="ignore")
    for text in ("Asset Requests", "upload_or_select_recommended_asset", "Clarify the missing asset need."):
        assert_true(text in markdown, f"setup Markdown missing {text}")
    return {"summary": summary_path.as_posix(), "markdown": markdown_path.as_posix(), "setup_report": setup_report_path.as_posix()}


def validate_make_available(output_root: Path, workspace: Path, fixture: Path) -> dict[str, Any]:
    checkpoint_id = "b49-public-ux-checkpoint"
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
            "editable_office",
            "--b49-asset-request-summary",
            fixture.as_posix(),
        ],
        timeout=420,
    )
    assert_true(checkpoint.returncode == 0, checkpoint.stderr or checkpoint.stdout)
    checkpoint_report = workspace / "outputs" / "projects" / checkpoint_id / "reports" / "ppt_make_report.json"
    checkpoint_payload = load_json(checkpoint_report)
    assert_true(checkpoint_payload.get("status") == "waiting_for_approval", "checkpoint should wait for approval")
    assert_available(checkpoint_payload["asset_request_summary"])

    approved_id = "b49-public-ux-approved"
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
            "editable_office",
            "--b49-asset-request-summary",
            fixture.as_posix(),
        ],
        timeout=600,
    )
    assert_true(approved.returncode == 0, approved.stderr or approved.stdout)
    approved_report = workspace / "outputs" / "projects" / approved_id / "reports" / "ppt_make_report.json"
    approved_payload = load_json(approved_report)
    assert_true(approved_payload.get("status") == "built", "approved build should complete")
    assert_true(approved_payload.get("artifacts", {}).get("pptx"), "approved build missing PPTX artifact")
    assert_true(approved_payload.get("artifacts", {}).get("html"), "approved build missing HTML artifact")
    assert_available(approved_payload["asset_request_summary"])
    return {"checkpoint_report": checkpoint_report.as_posix(), "approved_report": approved_report.as_posix()}


def validate_missing_summary(output_root: Path) -> dict[str, Any]:
    workspace = output_root / "workspace-missing"
    setup = run(
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
    assert_true(setup.returncode == 0, setup.stderr or setup.stdout)
    setup_summary = load_json(workspace / "outputs" / "reports" / "public_setup_summary.json")
    setup_report = load_json(workspace / "outputs" / "reports" / "ppt_setup_report.json")
    assert_unavailable(setup_summary["asset_request_summary"])
    assert_unavailable(setup_report["asset_request_summary"])

    project_id = "b49-public-ux-missing"
    make = run(
        [
            sys.executable,
            "scripts/ppt_make.py",
            PROMPT,
            "--workspace",
            workspace.as_posix(),
            "--mode",
            "assistant",
            "--project-id",
            project_id,
            "--skip-version-check",
        ],
        timeout=420,
    )
    assert_true(make.returncode == 0, make.stderr or make.stdout)
    make_report = load_json(workspace / "outputs" / "projects" / project_id / "reports" / "ppt_make_report.json")
    assert_unavailable(make_report["asset_request_summary"])
    return {"workspace": workspace.as_posix()}


def validate_malicious_public_field_blocked(output_root: Path) -> dict[str, Any]:
    fixture = write_malicious_b49_fixture(output_root / "fixtures" / "malicious_b49_asset_request_summary.json")
    workspace = output_root / "workspace-malicious"
    result = run(
        [
            sys.executable,
            "scripts/ppt_setup.py",
            "--workspace",
            workspace.as_posix(),
            "--force",
            "--skip-version-check",
            "--b49-asset-request-summary",
            fixture.as_posix(),
        ],
        timeout=360,
    )
    assert_true(result.returncode != 0, "setup accepted a token-shaped B49 public field")
    return {"status": "blocked", "returncode": result.returncode}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate public B49 asset request UX exposure.")
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args(argv)
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    before_reports = repo_report_snapshot()

    fixture = write_b49_fixture(output_root / "fixtures" / "b49_asset_request_summary.json")
    setup_available = validate_setup_available(output_root, fixture)
    make_available = validate_make_available(output_root, output_root / "workspace-setup-available", fixture)
    missing = validate_missing_summary(output_root)
    malicious = validate_malicious_public_field_blocked(output_root)

    public_paths = [
        Path(setup_available["summary"]),
        Path(setup_available["markdown"]),
        Path(setup_available["setup_report"]),
        Path(make_available["checkpoint_report"]),
        Path(make_available["approved_report"]),
        Path(missing["workspace"]) / "outputs" / "reports" / "public_setup_summary.json",
        Path(missing["workspace"]) / "outputs" / "reports" / "public_setup_summary.md",
        Path(missing["workspace"]) / "outputs" / "reports" / "ppt_setup_report.json",
        Path(missing["workspace"]) / "outputs" / "projects" / "b49-public-ux-missing" / "reports" / "ppt_make_report.json",
    ]
    changes = repo_report_changes(before_reports)
    assert_true(not changes, f"repo checkout outputs/reports changed during validation: {changes}")
    result = {
        "status": "pass",
        "available_summary": {"setup": setup_available, "make": make_available},
        "missing_summary": missing,
        "malicious_public_field_blocked": malicious,
        "public_private_scan": assert_public_safe(public_paths),
        "repo_report_leak_scan": {"repo_report_root": REPO_REPORT_ROOT.as_posix(), "changed_files": []},
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
