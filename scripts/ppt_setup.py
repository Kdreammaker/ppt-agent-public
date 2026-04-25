from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "1.0"


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def resolve_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return path


def workspace_from_args(args: argparse.Namespace) -> Path:
    if args.target:
        return resolve_path(args.target) / "workspace"
    if args.workspace:
        return resolve_path(args.workspace)
    return BASE_DIR.parent / "workspace"


def rel_workspace(path: Path, workspace: Path) -> str:
    try:
        return path.resolve().relative_to(workspace.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sanitized_command(command: list[str]) -> list[str]:
    sanitized: list[str] = []
    hide_next = False
    secret_flags = {"--workspace-code", "--private-build-command-json"}
    for item in command:
        if hide_next:
            sanitized.append("<redacted>")
            hide_next = False
            continue
        sanitized.append("python" if item == sys.executable else item)
        if item in secret_flags:
            hide_next = True
    return sanitized


def run_step(label: str, command: list[str], *, timeout: int = 240) -> dict[str, Any]:
    result = subprocess.run(command, cwd=BASE_DIR, capture_output=True, text=True, check=False, timeout=timeout)
    payload = {
        "label": label,
        "command": sanitized_command(command),
        "returncode": result.returncode,
        "status": "passed" if result.returncode == 0 else "failed",
        "stdout_tail": result.stdout[-4000:],
        "stderr_tail": result.stderr[-4000:],
    }
    parsed = maybe_json(result.stdout)
    if parsed:
        payload["stdout_json"] = parsed
    return payload


def maybe_json(stdout: str) -> dict[str, Any]:
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def env_has_value(name: str | None) -> bool:
    return bool(name and os.environ.get(name))


def connector_config_args(args: argparse.Namespace, workspace: Path) -> list[str]:
    private_repo = args.private_package_repo
    if not private_repo and args.auto_private_defaults and (args.enable_private or args.workspace_code):
        private_repo = "Kdreammaker/template-based-ppt-system-with-ai"
    private_ref = args.private_package_ref
    if not private_ref and args.auto_private_defaults and (args.enable_private or args.workspace_code):
        private_ref = "codex/project-scoped-output"
    command = [
        sys.executable,
        "scripts/ppt_private_connector.py",
        "configure",
        "--workspace",
        workspace.as_posix(),
        "--enable",
        "--default-operating-mode",
        args.default_operating_mode,
    ]
    if private_repo:
        command.extend(["--private-package-repo", private_repo])
    elif args.private_package_repo_env:
        command.extend(["--private-package-repo-env", args.private_package_repo_env])
    if private_ref:
        command.extend(["--private-package-ref", private_ref])
    elif args.private_package_ref_env:
        command.extend(["--private-package-ref-env", args.private_package_ref_env])
    if args.private_package_install_root:
        command.extend(["--private-package-install-root", args.private_package_install_root])
    if args.private_build_command_json:
        command.extend(["--private-build-command-json", args.private_build_command_json])
    elif args.private_build_command_env:
        command.extend(["--private-build-command-env", args.private_build_command_env])
    if args.github_check:
        command.append("--github-check")
    if args.reset_connector:
        command.append("--reset")
    return command


def dependency_step(args: argparse.Namespace) -> dict[str, Any]:
    check = "import pptx, PIL, fitz, pydantic"
    result = subprocess.run([sys.executable, "-c", check], cwd=BASE_DIR, capture_output=True, text=True, check=False, timeout=60)
    if result.returncode == 0:
        return {
            "label": "dependency_check",
            "command": ["python", "-c", check],
            "returncode": 0,
            "status": "passed",
            "stdout_tail": "",
            "stderr_tail": "",
            "installed": False,
        }
    if args.skip_dependency_install:
        return {
            "label": "dependency_check",
            "command": ["python", "-c", check],
            "returncode": result.returncode,
            "status": "failed",
            "stdout_tail": result.stdout[-1200:],
            "stderr_tail": result.stderr[-1200:],
            "installed": False,
        }
    install = run_step(
        "dependency_install",
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        timeout=600,
    )
    install["installed"] = install["returncode"] == 0
    return install


def command_setup(args: argparse.Namespace) -> int:
    workspace = workspace_from_args(args)
    steps: list[dict[str, Any]] = []
    errors: list[str] = []
    should_configure_private = False

    steps.append(dependency_step(args))
    if steps[-1]["returncode"] != 0:
        errors.append("dependency installation/check failed")

    if not args.skip_version_check:
        version_command = [sys.executable, "scripts/ppt_version_check.py"]
        if args.workspace:
            version_command.extend(["--workspace", workspace.as_posix()])
        if args.skip_remote_version_check:
            version_command.append("--skip-remote")
        steps.append(run_step("version_check", version_command, timeout=90))

    install_command = [sys.executable, "scripts/ppt_install.py"]
    if args.target:
        install_command.extend(["--target", resolve_path(args.target).as_posix()])
    else:
        install_command.extend(["--workspace", workspace.as_posix()])
    if args.force:
        install_command.append("--force")
    steps.append(run_step("install_workspace", install_command))

    if steps[-1]["returncode"] != 0:
        errors.append("workspace install failed")
    else:
        if args.workspace_code:
            steps.append(
                run_step(
                    "activate_entitlement",
                    [
                        sys.executable,
                        "scripts/ppt_workspace_entitlement.py",
                        "activate",
                        "--workspace",
                        workspace.as_posix(),
                        "--workspace-code",
                        args.workspace_code,
                    ],
                )
            )
            if steps[-1]["returncode"] != 0:
                errors.append("workspace entitlement activation failed")

        should_configure_private = (
            args.enable_private
            or bool(args.workspace_code)
            or bool(args.private_package_repo)
            or env_has_value(args.private_package_repo_env)
            or bool(args.private_build_command_json)
            or env_has_value(args.private_build_command_env)
            or bool(args.private_package_install_root)
        )
        if should_configure_private:
            steps.append(run_step("configure_private_connector", connector_config_args(args, workspace)))
            if steps[-1]["returncode"] != 0:
                errors.append("private connector configuration failed")

            if args.install_private_runtime and not errors:
                install_private = run_step(
                    "install_private_runtime",
                    [
                        sys.executable,
                        "scripts/ppt_private_connector.py",
                        "install",
                        "--workspace",
                        workspace.as_posix(),
                        "--execute",
                        *(["--github-check"] if args.github_check else []),
                    ],
                    timeout=600,
                )
                steps.append(install_private)
                if install_private["returncode"] != 0:
                    errors.append("private runtime install failed or needs authenticated private repo access")

        steps.append(
            run_step(
                "connector_status",
                [
                    sys.executable,
                    "scripts/ppt_private_connector.py",
                    "status",
                    "--workspace",
                    workspace.as_posix(),
                    *(["--github-check"] if args.github_check else []),
                ],
            )
        )
        if should_configure_private and steps[-1]["returncode"] != 0:
            errors.append("private connector status is not ready")

    status_payload = steps[-1].get("stdout_json", {}) if steps else {}
    private_execution_ready = bool(
        status_payload.get("capability_summary", {})
        .get("private_template_library_build", {})
        .get("ready_for_execution", False)
    )
    private_request_ready = bool(
        status_payload.get("capability_summary", {})
        .get("private_template_library_build", {})
        .get("ready_for_request", False)
    )
    if should_configure_private and not private_request_ready:
        if "private connector status is not ready" not in errors:
            errors.append("private connector status is not ready")
    report = {
        "schema_version": SCHEMA_VERSION,
        "command": "ppt_setup",
        "generated_at": utc_now(),
        "status": "ready" if not errors else "needs_attention",
        "workspace_root": workspace.resolve().as_posix(),
        "private_requested": should_configure_private,
        "private_status": status_payload.get("status"),
        "private_execution_ready": private_execution_ready,
        "private_request_ready": private_request_ready,
        "default_operating_mode": status_payload.get("default_operating_mode", args.default_operating_mode),
        "errors": errors,
        "steps": steps,
        "next_commands": {
            "natural_language_public": f'python scripts/ppt_make.py "Make a 6-slide executive growth review" --workspace "{workspace.as_posix()}" --mode assistant',
            "natural_language_private": f'python scripts/ppt_make.py "Make a production-ready executive growth review" --workspace "{workspace.as_posix()}" --mode assistant --production private --execute-private',
            "doctor": f'python scripts/ppt_private_connector.py status --workspace "{workspace.as_posix()}" --github-check',
        },
        "policy_summary": {
            "raw_workspace_code_stored": False,
            "tokens_printed": False,
            "private_assets_copied_into_public_repo": False,
            "local_paths_allowed_only_in_workspace_reports": True,
        },
    }
    report_path = workspace / "outputs" / "reports" / "ppt_setup_report.json"
    write_json(report_path, report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "workspace": workspace.as_posix(),
                "private_status": report["private_status"],
                "private_request_ready": report["private_request_ready"],
                "private_execution_ready": report["private_execution_ready"],
                "report": rel_workspace(report_path, workspace),
                "next_commands": report["next_commands"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if not errors else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="One-command public workspace setup plus optional private connector configuration.")
    parser.add_argument("--target", help="Install root that will contain ppt-agent-public/ and workspace/.")
    parser.add_argument("--workspace", help="Workspace path for an already-cloned public repo.")
    parser.add_argument("--force", action="store_true", help="Overwrite workspace-local bootstrap files.")
    parser.add_argument("--workspace-code", default=os.environ.get("PPT_AGENT_WORKSPACE_CODE"), help="Workspace entitlement code. Can also be supplied by PPT_AGENT_WORKSPACE_CODE.")
    parser.add_argument("--enable-private", action="store_true", help="Enable the private connector using supplied args or environment defaults.")
    parser.add_argument("--auto-private-defaults", action=argparse.BooleanOptionalAction, default=True, help="Use the default private repo/ref when private setup is requested and explicit values are absent.")
    parser.add_argument("--install-private-runtime", action=argparse.BooleanOptionalAction, default=True, help="Clone/install the private runtime when private setup is requested and the repo is accessible.")
    parser.add_argument("--private-package-repo", default=os.environ.get("PPT_AGENT_PRIVATE_PACKAGE_REPO"))
    parser.add_argument("--private-package-repo-env", default="PPT_AGENT_PRIVATE_PACKAGE_REPO")
    parser.add_argument("--private-package-ref", default=os.environ.get("PPT_AGENT_PRIVATE_PACKAGE_REF"))
    parser.add_argument("--private-package-ref-env", default="PPT_AGENT_PRIVATE_PACKAGE_REF")
    parser.add_argument("--private-package-install-root", default=os.environ.get("PPT_AGENT_PRIVATE_PACKAGE_INSTALL_ROOT"))
    parser.add_argument("--private-build-command-json", default=os.environ.get("PPT_AGENT_PRIVATE_BUILD_COMMAND_JSON"))
    parser.add_argument("--private-build-command-env", default="PPT_AGENT_PRIVATE_BUILD_COMMAND_JSON")
    parser.add_argument("--default-operating-mode", choices=["auto", "assistant"], default="assistant")
    parser.add_argument("--github-check", action="store_true")
    parser.add_argument("--reset-connector", action="store_true")
    parser.add_argument("--skip-dependency-install", action="store_true")
    parser.add_argument("--skip-version-check", action="store_true")
    parser.add_argument("--skip-remote-version-check", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    return command_setup(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
