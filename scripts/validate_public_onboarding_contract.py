from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
PROMPT = "Create a 5-slide planning-first presentation about a city library after-hours study-space pilot."
STALE_COMMANDS = [("ppt-" + "agent " + suffix) for suffix in ["healthcheck", "plan", "compose", "build", "validate"]]
REPO_REPORT_ROOT = BASE_DIR / "outputs" / "reports"


def run(command: list[str], *, timeout: int = 420) -> subprocess.CompletedProcess[str]:
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
        if not path.is_file():
            continue
        stat = path.stat()
        snapshot[path.relative_to(REPO_REPORT_ROOT).as_posix()] = (stat.st_size, stat.st_mtime_ns)
    return snapshot


def repo_report_changes(before: dict[str, tuple[int, int]]) -> list[str]:
    after = repo_report_snapshot()
    changes: list[str] = []
    for name, state in after.items():
        if before.get(name) != state:
            changes.append(name)
    return sorted(changes)


def assert_existing_artifact_paths(report_path: Path, required: list[str]) -> dict[str, str | None]:
    report = load_json(report_path)
    artifacts = report.get("artifacts")
    assert_true(isinstance(artifacts, dict), f"{report_path} missing artifacts object")
    checked: dict[str, str | None] = {}
    for name in required:
        value = artifacts.get(name)
        assert_true(isinstance(value, str) and value.strip(), f"{report_path} artifact {name} must be a usable path")
        path = Path(value)
        assert_true(path.is_absolute(), f"{report_path} artifact {name} is not absolute: {value}")
        assert_true(path.exists(), f"{report_path} artifact {name} does not exist: {value}")
        checked[name] = path.as_posix()
    for name, value in artifacts.items():
        if value is None:
            checked[name] = None
            continue
        if isinstance(value, str):
            path = Path(value)
            assert_true(path.is_absolute(), f"{report_path} artifact {name} is not absolute: {value}")
            assert_true(path.exists(), f"{report_path} artifact {name} does not exist: {value}")
            checked[name] = path.as_posix()
    return checked


def validate_setup_contract(workspace: Path) -> dict[str, Any]:
    result = run([sys.executable, "scripts/ppt_setup.py", "--workspace", workspace.as_posix(), "--force"])
    assert_true(result.returncode == 0, result.stderr or result.stdout)
    report_path = workspace / "outputs" / "reports" / "ppt_setup_report.json"
    report = load_json(report_path)
    commands = report.get("next_commands", {}).get("natural_language_public")
    assert_true(isinstance(commands, dict), "natural_language_public must be structured commands")
    checkpoint = str(commands.get("assistant_checkpoint", ""))
    approved = str(commands.get("assistant_final_after_review", ""))
    assert_true("--mode assistant" in checkpoint, "missing Assistant checkpoint command")
    assert_true("--build-approved" not in checkpoint and "--continue-build" not in checkpoint, "checkpoint command should not pre-approve build")
    assert_true("--build-approved" in approved or "--continue-build" in approved, "missing approved continuation command")
    readme = (workspace / "README.md").read_text(encoding="utf-8")
    hits = [item for item in STALE_COMMANDS if item in readme]
    assert_true(not hits, f"generated README references unavailable commands: {hits}")
    assert_true("Route Matrix" in readme, "generated README missing route matrix")
    return {"workspace": workspace.as_posix(), "setup_report": report_path.as_posix()}


def validate_assistant_checkpoint(workspace: Path) -> dict[str, Any]:
    project_id = "public-onboarding-assistant-checkpoint"
    project_dir = workspace / "outputs" / "projects" / project_id
    result = run(
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
        ]
    )
    assert_true(result.returncode == 0, result.stderr or result.stdout)
    report_path = project_dir / "reports" / "ppt_make_report.json"
    report = load_json(report_path)
    assert_true(report.get("status") == "waiting_for_approval", f"unexpected Assistant status: {report.get('status')}")
    assert_true((project_dir / "plans" / "deck_plan.json").exists(), "missing deck_plan.json")
    assert_true((project_dir / "plans" / "draft_design_brief.md").exists(), "missing draft_design_brief.md")
    assert_true(not (workspace / "outputs" / "decks" / f"{project_id}.pptx").exists(), "Assistant checkpoint created PPTX")
    assert_true(not (workspace / "outputs" / "html" / project_id / "index.html").exists(), "Assistant checkpoint created HTML")
    artifacts = assert_existing_artifact_paths(report_path, ["intake", "deck_plan", "draft_design_brief", "spec", "report"])
    assert_true(artifacts.get("pptx") is None, "Assistant checkpoint report should not include a PPTX path")
    assert_true(artifacts.get("html") is None, "Assistant checkpoint report should not include an HTML path")
    return {"project_id": project_id, "status": report.get("status"), "report": report_path.as_posix()}


def validate_assistant_approved(workspace: Path) -> dict[str, Any]:
    project_id = "public-onboarding-assistant-approved"
    project_dir = workspace / "outputs" / "projects" / project_id
    result = run(
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
            project_id,
        ],
        timeout=600,
    )
    assert_true(result.returncode == 0, result.stderr or result.stdout)
    report_path = project_dir / "reports" / "ppt_make_report.json"
    report = load_json(report_path)
    assert_true(report.get("status") == "built", f"approved Assistant did not build: {report.get('status')}")
    pptx = workspace / "outputs" / "decks" / f"{project_id}.pptx"
    html = workspace / "outputs" / "html" / project_id / "index.html"
    assert_true(pptx.exists(), "approved Assistant did not create PPTX")
    assert_true(html.exists(), "approved Assistant did not create HTML")
    assert_existing_artifact_paths(report_path, ["intake", "deck_plan", "draft_design_brief", "spec", "pptx", "html", "report"])
    return {"project_id": project_id, "status": report.get("status"), "pptx": pptx.as_posix(), "html": html.as_posix()}


def validate_stale_command_scan(workspace: Path) -> dict[str, Any]:
    paths = [
        BASE_DIR / "README.md",
        BASE_DIR / "skills" / "ppt-agent" / "SKILL.md",
        BASE_DIR / "docs" / "beta" / "CLI_MCP_GOLDEN_PATH.md",
        BASE_DIR / "scripts" / "ppt_cli_workspace.py",
        workspace / "README.md",
    ]
    hits: list[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for command in STALE_COMMANDS:
            if command in text:
                hits.append(f"{path.as_posix()}: {command}")
    assert_true(not hits, f"stale unavailable command references found: {hits}")
    return {"checked": [path.as_posix() for path in paths], "hits": 0}


def validate_public_private_scan(output_root: Path) -> dict[str, Any]:
    patterns = {
        "drive_marker": re.compile(r"drive\.google\.com|docs\.google\.com|\bdrive[_-]?id\b", re.IGNORECASE),
        "token": re.compile(r"xox[baprs]-|sk-[A-Za-z0-9_-]{12,}|AIza[0-9A-Za-z_-]{20,}", re.IGNORECASE),
        "unsafe_package_path": re.compile(r"\.\./packages|\./packages|/packages|packages\\|[A-Za-z]:\\.*packages", re.IGNORECASE),
    }
    issues: list[dict[str, str]] = []
    for path in output_root.rglob("*.json"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in patterns.items():
            if pattern.search(text):
                issues.append({"path": path.as_posix(), "issue": name})
    assert_true(not issues, f"public/private scan failed: {issues[:5]}")
    return {"scanned_root": output_root.as_posix(), "issues": 0}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate public link-only onboarding contract.")
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args(argv)
    output_root = Path(args.output_root).resolve()
    workspace = output_root / "workspace"
    output_root.mkdir(parents=True, exist_ok=True)
    before_reports = repo_report_snapshot()
    result = {
        "status": "pass",
        "setup_contract": validate_setup_contract(workspace),
        "assistant_checkpoint": validate_assistant_checkpoint(workspace),
        "assistant_approved": validate_assistant_approved(workspace),
        "stale_command_scan": validate_stale_command_scan(workspace),
        "public_private_scan": validate_public_private_scan(output_root),
    }
    changes = repo_report_changes(before_reports)
    assert_true(not changes, f"repo checkout outputs/reports changed during smoke: {changes}")
    result["repo_report_leak_scan"] = {"repo_report_root": REPO_REPORT_ROOT.as_posix(), "changed_files": []}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
