from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_WORKSPACE = BASE_DIR / "outputs" / "bootstrap_smoke_workspace"
DEFAULT_REPORT = BASE_DIR / "outputs" / "reports" / "public_gate_bootstrap_validation.json"


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def base_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(BASE_DIR).as_posix()
    except ValueError:
        return resolved.as_posix()


def resolve_workspace(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = (BASE_DIR / path).resolve()
    allowed = (BASE_DIR / "outputs").resolve()
    if path.resolve() != allowed and not path.resolve().is_relative_to(allowed):
        raise ValueError(f"bootstrap workspace must stay under {allowed}: {path.resolve()}")
    return path.resolve()


def run_step(label: str, args: list[str]) -> dict[str, Any]:
    result = subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True, check=False, timeout=180)
    return {
        "label": label,
        "command": ["python" if item == sys.executable else item for item in args],
        "returncode": result.returncode,
        "status": "passed" if result.returncode == 0 else "failed",
        "stdout_head": (result.stdout or "").strip().splitlines()[:5],
        "stderr_head": (result.stderr or "").strip().splitlines()[:5],
    }


def build_report(workspace: Path, steps: list[dict[str, Any]]) -> dict[str, Any]:
    failures = [step for step in steps if step["returncode"] != 0]
    return {
        "schema_version": "1.0",
        "command": "bootstrap_public_gate_workspace",
        "status": "valid" if not failures else "invalid",
        "workspace": base_relative(workspace),
        "steps": steps,
        "summary": {
            "steps": len(steps),
            "failures": len(failures),
            "private_gateway_required": False,
            "standalone_exe_required": False,
            "public_gate_smoke_checked": True,
            "sample_fixture_smoke_checked": True,
        },
        "policy_summary": {
            "local_only_supported": True,
            "private_gateway_required": False,
            "telemetry_enabled": False,
            "upload_allowed": False,
            "public_repo_write_performed": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bootstrap a local workspace and public gate integration smoke path.")
    parser.add_argument("--workspace", default=DEFAULT_WORKSPACE.as_posix())
    parser.add_argument("--report", default=DEFAULT_REPORT.as_posix())
    parser.add_argument("--force-readme", action="store_true")
    args = parser.parse_args(argv)

    workspace = resolve_workspace(args.workspace)
    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = (BASE_DIR / report_path).resolve()

    init_command = [sys.executable, "scripts/ppt_cli_workspace.py", "init", "--workspace", workspace.as_posix()]
    if args.force_readme:
        init_command.append("--force-readme")
    steps = [
        run_step("workspace_init", init_command),
        run_step("workspace_healthcheck", [sys.executable, "scripts/ppt_cli_workspace.py", "healthcheck", "--workspace", workspace.as_posix()]),
        run_step("public_gate_dependency", [sys.executable, "scripts/validate_public_gate_toolkit_dependency.py"]),
        run_step("public_gate_sync_fixture", [sys.executable, "scripts/validate_public_gate_sync_path.py"]),
    ]
    report = build_report(workspace, steps)
    write_json(report_path, report)
    write_json(workspace / "reports" / "public_gate_bootstrap.json", report)
    if report["status"] != "valid":
        for step in steps:
            if step["returncode"] != 0:
                print(f"ERROR: {step['label']} failed: {step['stderr_head'] or step['stdout_head']}", file=sys.stderr)
        return 1
    print(f"public_gate_bootstrap=valid workspace={base_relative(workspace)} steps={len(steps)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
