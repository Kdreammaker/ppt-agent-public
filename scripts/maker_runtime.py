from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
CONTRACT_PATH = BASE_DIR / "config" / "maker_runtime_execution_contract.json"

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.normalize_slack_intake import load_json, normalize, write_json


def run(args: list[str], timeout: int = 600) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True, check=False, timeout=timeout)


def parse_json_stdout(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    data = json.loads(result.stdout)
    if not isinstance(data, dict):
        raise ValueError("stdout JSON must be an object")
    return data


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(BASE_DIR).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def write_reply(path: Path, *, request_id: str, status: str, findings: list[str], next_action: str, artifacts: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"Request `{request_id}` status: `{status}`",
        "",
        "Findings:",
    ]
    lines.extend([f"- {finding}" for finding in findings] or ["- No blocking findings recorded."])
    lines.extend(["", f"Next action: {next_action}", "", "Artifacts:"])
    for key, value in artifacts.items():
        if value:
            lines.append(f"- {key}: `{value}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def execute_maker_request(
    slack_request_path: Path,
    *,
    workspace: Path,
    project_root: Path,
    execute_private: bool,
    timeout_seconds: int = 600,
) -> dict[str, Any]:
    raw = load_json(slack_request_path)
    normalized = normalize(raw, output_root=project_root)
    request_id = str(normalized["request_id"])
    artifacts = normalized["artifact_paths"]
    write_json(Path(artifacts["request_summary"]), {"schema_version": "1.0", "request_id": request_id, "raw_summary": normalized["raw_summary"]})
    write_json(Path(artifacts["deck_intake"]), normalized["normalized_intake"])
    write_json(Path(artifacts["normalization_report"]), {key: value for key, value in normalized.items() if key != "normalized_intake"})

    reports_dir = project_root / "reports"
    specs_dir = project_root / "specs"
    reply_path = project_root / "slack_reply.md"
    runtime_report_path = reports_dir / "maker_runtime_report.json"
    spec_path = specs_dir / f"{request_id}_spec.json"
    findings: list[str] = []
    status = "blocked"
    next_action = "Fix blocked intake or connector items before requesting private build."
    build_payload: dict[str, Any] | None = None

    if normalized["status"] in {"malformed", "blocked_asset_boundary_issue"}:
        findings.extend(normalized.get("errors", []))
        findings.extend(normalized.get("blocked_asset_boundary_issues", []))
    else:
        compose = run(
            [
                sys.executable,
                "scripts/compose_deck_spec_from_intake.py",
                artifacts["deck_intake"],
                "--output",
                str(spec_path),
            ],
            timeout=timeout_seconds,
        )
        if compose.returncode != 0:
            findings.append(f"spec composition failed: {compose.stderr.strip() or compose.stdout.strip()}")
        else:
            if normalized["status"] == "needs_clarification":
                status = "needs_review"
                findings.extend(normalized.get("warnings", []))
                next_action = "Ask the user for the defaulted fields or record explicit continue/skip before unattended delivery."
            build = run(
                [
                    sys.executable,
                    "scripts/ppt_private_connector.py",
                    "build",
                    "--workspace",
                    str(workspace),
                    "--spec",
                    str(spec_path),
                    "--operating-mode",
                    str(normalized["operating_mode"]),
                    *("--execute".split() if execute_private else []),
                ],
                timeout=timeout_seconds,
            )
            if build.returncode not in (0, 2):
                findings.append(f"private build request failed: {build.stderr.strip() or build.stdout.strip()}")
            else:
                build_payload = parse_json_stdout(build)
                if build_payload.get("status") == "built":
                    status = "built"
                    next_action = "Review generated artifacts and delivery summary before external delivery."
                elif build_payload.get("status") == "ready_for_private_build_execution":
                    if status != "needs_review":
                        status = "ready_for_private_build_execution"
                        next_action = "Run with --execute after private runtime approval is recorded."
                else:
                    status = "blocked"
                    findings.extend(str(item) for item in build_payload.get("errors", []))

    reply_artifacts = {
        "normalized_intake": rel(Path(artifacts["deck_intake"])),
        "normalization_report": rel(Path(artifacts["normalization_report"])),
        "spec": rel(spec_path) if spec_path.exists() else None,
        "private_build_request_summary": build_payload.get("artifact_paths", {}).get("request_summary") if build_payload else None,
        "runtime_report": rel(runtime_report_path),
    }
    write_reply(reply_path, request_id=request_id, status=status, findings=findings, next_action=next_action, artifacts=reply_artifacts)
    report = {
        "schema_version": "1.0",
        "request_id": request_id,
        "status": status,
        "pipeline": ["slack_request", "normalize_intake", "compose_spec", "private_build", "validate", "reply"],
        "operating_mode": normalized.get("operating_mode"),
        "findings": findings,
        "next_action": next_action,
        "artifact_paths": {
            **reply_artifacts,
            "reply": rel(reply_path),
        },
        "normalization_status": normalized.get("status"),
        "private_build": build_payload,
        "policy_summary": {
            "diagnostic_only_success": False,
            "private_execution_requested": execute_private,
            "asset_boundary": "approved_manifest_or_metadata_only",
        },
    }
    write_json(runtime_report_path, report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the request-linked maker runtime path.")
    parser.add_argument("--slack-request", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--project-root", default=None)
    parser.add_argument("--execute-private", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=600)
    args = parser.parse_args(argv)

    slack_request = Path(args.slack_request)
    if not slack_request.is_absolute():
        slack_request = (BASE_DIR / slack_request).resolve()
    workspace = Path(args.workspace)
    if not workspace.is_absolute():
        workspace = (BASE_DIR / workspace).resolve()
    request_id_hint = slack_request.stem
    project_root = Path(args.project_root).resolve() if args.project_root else (BASE_DIR / "outputs" / "projects" / request_id_hint)
    report = execute_maker_request(
        slack_request,
        workspace=workspace,
        project_root=project_root,
        execute_private=args.execute_private,
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] in {"built", "ready_for_private_build_execution", "needs_review"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
