from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
CONTRACT_PATH = BASE_DIR / "config" / "public_private_runtime_connector_contract.json"
MODE_POLICY_ROOT = BASE_DIR / "config" / "mode_policies"
MODE_PARITY_CONTRACT_PATH = BASE_DIR / "config" / "private_mode_parity_contract.json"
SCHEMA_VERSION = "1.0"
SUPPORTED_OPERATING_MODES = ("auto", "assistant")


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def resolve_workspace(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return path


def rel_workspace(path: Path, workspace: Path) -> str:
    try:
        return path.resolve().relative_to(workspace.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def connector_path(workspace: Path) -> Path:
    return workspace / ".ppt-agent" / "private_connector.json"


def entitlement_path(workspace: Path) -> Path:
    return workspace / ".ppt-agent" / "entitlement.json"


def request_dir(workspace: Path) -> Path:
    return workspace / ".ppt-agent" / "gateway_requests"


def contract() -> dict[str, Any]:
    return load_json(CONTRACT_PATH)


def mode_parity_contract() -> dict[str, Any]:
    return load_json(MODE_PARITY_CONTRACT_PATH)


def normalize_operating_mode(value: str | None, default: str = "auto") -> str:
    mode = (value or default or "auto").strip().lower()
    if mode not in SUPPORTED_OPERATING_MODES:
        raise ValueError(f"unsupported operating_mode: {value}")
    return mode


def mode_policy_summary(mode: str) -> dict[str, Any]:
    mode = normalize_operating_mode(mode)
    parity = mode_parity_contract().get("operating_modes", {}).get(mode, {})
    policy_ref = str(parity.get("mode_policy_file") or f"config/mode_policies/{mode}_mode_policy.json")
    policy_path = (BASE_DIR / policy_ref).resolve()
    policy = load_json(policy_path)
    return {
        "operating_mode": mode,
        "mode_policy_ref": policy_ref,
        "approval_expectation": parity.get("approval_expectation"),
        "review_behavior": parity.get("review_behavior"),
        "requires_explicit_continue_for_build": bool(parity.get("requires_explicit_continue_for_build", False)),
        "expected_report_artifacts": list(parity.get("expected_report_artifacts", [])),
        "policy_default_assumptions": list(policy.get("default_assumptions", []))[:3],
    }


def default_config(workspace: Path, args: argparse.Namespace | None = None) -> dict[str, Any]:
    cfg = contract().get("configuration", {})
    gateway_url_env = getattr(args, "gateway_url_env", None) or cfg.get("gateway_url_env", "PPT_AGENT_PRIVATE_GATEWAY_URL")
    package_repo_env = getattr(args, "private_package_repo_env", None) or cfg.get("private_package_repo_env", "PPT_AGENT_PRIVATE_PACKAGE_REPO")
    package_ref_env = getattr(args, "private_package_ref_env", None) or cfg.get("private_package_ref_env", "PPT_AGENT_PRIVATE_PACKAGE_REF")
    build_command_env = getattr(args, "private_build_command_env", None) or cfg.get("private_build_command_env", "PPT_AGENT_PRIVATE_BUILD_COMMAND_JSON")
    install_root = getattr(args, "private_package_install_root", None) or cfg.get("private_package_install_root", ".ppt-agent/private_runtime")
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "connector_enabled": bool(getattr(args, "enable", False)),
        "workspace_root": workspace.resolve().as_posix(),
        "gateway_url_env": gateway_url_env,
        "gateway_url": getattr(args, "gateway_url", None),
        "private_package_repo_env": package_repo_env,
        "private_package_repo": getattr(args, "private_package_repo", None),
        "private_package_ref_env": package_ref_env,
        "private_package_ref": getattr(args, "private_package_ref", None) or "main",
        "private_package_install_root": install_root,
        "private_build_command_env": build_command_env,
        "private_build_command_json": getattr(args, "private_build_command_json", None),
        "default_operating_mode": normalize_operating_mode(getattr(args, "default_operating_mode", None) or getattr(args, "operating_mode", None) or "auto"),
        "package_channel": getattr(args, "package_channel", None) or "invite_beta",
        "credential_policy": cfg.get("credential_policy"),
        "real_execution_enabled": False,
        "public_smoke_is_fallback_only": True,
    }


def configured_value(config: dict[str, Any], key: str, env_key: str) -> str | None:
    value = config.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    env_name = config.get(env_key)
    if isinstance(env_name, str) and env_name.strip():
        env_value = os.environ.get(env_name.strip())
        if env_value:
            return env_value
    return None


def configured_command(config: dict[str, Any]) -> list[str] | None:
    value = config.get("private_build_command_json")
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, list) and all(isinstance(item, str) and item for item in parsed):
            return parsed
        return None
    env_name = config.get("private_build_command_env")
    if isinstance(env_name, str) and env_name.strip():
        env_value = os.environ.get(env_name.strip())
        if env_value:
            try:
                parsed = json.loads(env_value)
            except json.JSONDecodeError:
                return None
            if isinstance(parsed, list) and all(isinstance(item, str) and item for item in parsed):
                return parsed
    return None


def install_root_path(workspace: Path, config: dict[str, Any]) -> Path:
    configured = str(config.get("private_package_install_root") or ".ppt-agent/private_runtime")
    path = Path(configured)
    if not path.is_absolute():
        path = workspace / path
    return path.resolve()


def default_html_output_path(workspace: Path, spec: Path, output: Path | None) -> Path:
    if output:
        if output.parent.name.casefold() == "decks":
            return (output.parent.parent / "html" / output.stem / "index.html").resolve()
        return (output.parent / output.stem / "index.html").resolve()
    return (workspace / "outputs" / "html" / spec.stem / "index.html").resolve()


def maybe_parse_json_text(value: str) -> dict[str, Any] | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def private_execution_summary(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return {
        "returncode": result.returncode,
        "stdout_captured": bool(result.stdout),
        "stderr_captured": bool(result.stderr),
        "output_omitted": True,
        "omission_reason": "private runtime stdout/stderr may contain secrets, local paths, or generated content",
    }


def ensure_path_inside_workspace(path: Path, workspace: Path) -> None:
    try:
        path.resolve().relative_to(workspace.resolve())
    except ValueError as exc:
        raise ValueError(f"path must stay inside workspace: {path}") from exc


def render_command_template(
    command: list[str],
    *,
    workspace: Path,
    spec: Path,
    output: Path | None,
    html_output: Path | None,
    request_summary: Path,
    capability: str,
    operating_mode: str,
) -> list[str]:
    replacements = {
        "{workspace}": workspace.resolve().as_posix(),
        "{spec}": spec.resolve().as_posix(),
        "{output}": output.resolve().as_posix() if output else "",
        "{html_output}": html_output.resolve().as_posix() if html_output else "",
        "{request_summary}": request_summary.resolve().as_posix(),
        "{capability}": capability,
        "{operating_mode}": operating_mode,
    }
    rendered: list[str] = []
    for item in command:
        value = item
        for token, replacement in replacements.items():
            value = value.replace(token, replacement)
        if value:
            rendered.append(value)
    return rendered


def entitlement_summary(workspace: Path) -> dict[str, Any]:
    entitlement = read_json(entitlement_path(workspace))
    response = entitlement.get("response", {}) if isinstance(entitlement.get("response"), dict) else {}
    entitlements = response.get("entitlements", [])
    return {
        "status": response.get("status", "missing"),
        "allowed": bool(response.get("allowed", False)),
        "workspace_code_mask": entitlement.get("workspace_code_mask"),
        "entitlements": entitlements if isinstance(entitlements, list) else [],
        "package_channel": response.get("package_channel"),
    }


def consent_summary(workspace: Path) -> dict[str, Any]:
    consent = read_json(workspace / ".ppt-agent" / "consent.json")
    return {
        "gateway_enabled": bool(consent.get("gateway_enabled", False) or read_json(workspace / ".ppt-agent" / "config.json").get("gateway_enabled", False)),
        "metadata_visible": bool(consent.get("gateway_asset_metadata_visible", False)),
        "file_upload_allowed": bool(consent.get("file_upload_allowed", consent.get("upload_allowed", False))),
        "final_artifact_upload_allowed": bool(consent.get("final_artifact_upload_allowed", False)),
        "full_content_upload_allowed": bool(consent.get("full_content_upload_allowed", False)),
        "telemetry_enabled": bool(consent.get("telemetry_enabled", False)),
        "learning_collection_enabled": bool(consent.get("learning_collection_enabled", False)),
    }


def run_command(args: list[str], timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True, check=False, timeout=timeout)


def gh_summary(private_repo: str | None = None) -> dict[str, Any]:
    gh_path = shutil.which("gh")
    summary: dict[str, Any] = {
        "available": gh_path is not None,
        "path": gh_path,
        "authenticated": False,
        "private_repo_configured": bool(private_repo),
        "private_repo_accessible": None,
    }
    if not gh_path:
        return summary
    auth = run_command(["gh", "auth", "status"])
    auth_text = (auth.stdout + "\n" + auth.stderr).replace("\r", "")
    summary["authenticated"] = auth.returncode == 0
    summary["auth_account"] = "configured" if "Logged in" in auth_text else "unknown"
    if private_repo:
        repo = run_command(["gh", "repo", "view", private_repo, "--json", "nameWithOwner,visibility"])
        summary["private_repo_accessible"] = repo.returncode == 0
        if repo.returncode == 0:
            try:
                repo_data = json.loads(repo.stdout)
            except json.JSONDecodeError:
                repo_data = {}
            summary["private_repo"] = repo_data.get("nameWithOwner", private_repo)
            summary["private_repo_visibility"] = repo_data.get("visibility", "unknown")
    return summary


def build_status(workspace: Path, *, include_github: bool = False) -> dict[str, Any]:
    config = read_json(connector_path(workspace))
    if not config:
        config = default_config(workspace)
    entitlement = entitlement_summary(workspace)
    consent = consent_summary(workspace)
    gateway = configured_value(config, "gateway_url", "gateway_url_env")
    private_repo = configured_value(config, "private_package_repo", "private_package_repo_env")
    install_root = install_root_path(workspace, config)
    private_command = configured_command(config)
    default_operating_mode = normalize_operating_mode(str(config.get("default_operating_mode") or "auto"))
    private_package_installed = install_root.exists()
    entitlements = set(entitlement.get("entitlements", []))
    private_build_entitled = entitlement.get("allowed") is True and "private_package_access" in entitlements
    package_install_ready = bool(config.get("connector_enabled")) and private_build_entitled and bool(private_repo)
    private_build_request_ready = bool(config.get("connector_enabled")) and private_build_entitled and bool(gateway or private_repo or private_package_installed)
    private_build_execution_ready = private_build_request_ready and bool(private_command)
    payload = {
        "command": "status",
        "status": "ready" if private_build_execution_ready else ("configured" if private_build_request_ready else "not_ready"),
        "workspace_root": workspace.resolve().as_posix(),
        "connector_enabled": bool(config.get("connector_enabled")),
        "gateway_endpoint_configured": bool(gateway),
        "private_package_repo_configured": bool(private_repo),
        "private_package_install_root": rel_workspace(install_root, workspace),
        "private_package_installed": private_package_installed,
        "private_build_command_configured": bool(private_command),
        "default_operating_mode": default_operating_mode,
        "package_channel": config.get("package_channel", "invite_beta"),
        "private_package_ref_configured": bool(config.get("private_package_ref")),
        "mode_policy_summary": {
            "auto": mode_policy_summary("auto"),
            "assistant": mode_policy_summary("assistant"),
        },
        "capability_summary": {
            "private_package_install": {
                "expected_user_value": "install or update the private runtime package needed for production-quality PPT generation",
                "entitled": private_build_entitled,
                "ready": package_install_ready,
                "public_repo_contains_private_assets": False,
            },
            "private_template_library_build": {
                "expected_user_value": "full template-library based high-quality PPT generation",
                "entitled": private_build_entitled,
                "ready_for_request": private_build_request_ready,
                "ready_for_execution": private_build_execution_ready,
                "public_repo_contains_private_assets": False,
                "fallback": "public_smoke_blank_spec",
            },
        },
        "entitlement_summary": entitlement,
        "consent_summary": consent,
        "policy_summary": {
            "public_smoke_is_fallback_only": bool(config.get("public_smoke_is_fallback_only", True)),
            "real_execution_enabled": bool(config.get("real_execution_enabled", False)),
            "raw_workspace_code_stored": False,
            "tokens_printed": False,
            "private_templates_in_public_repo": False,
            "file_upload_allowed": consent.get("file_upload_allowed", False),
            "telemetry_enabled": consent.get("telemetry_enabled", False),
        },
    }
    if include_github:
        payload["github_cli"] = gh_summary(private_repo)
    return payload


def command_configure(args: argparse.Namespace) -> int:
    workspace = resolve_workspace(args.workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    current = read_json(connector_path(workspace))
    config = default_config(workspace, args)
    if current and not args.reset:
        preserved = dict(current)
        preserved.update({key: value for key, value in config.items() if value is not None})
        preserved["updated_at"] = utc_now()
        config = preserved
    write_json(connector_path(workspace), config)
    payload = build_status(workspace, include_github=args.github_check)
    payload.update({"command": "configure", "artifact_paths": {"connector": rel_workspace(connector_path(workspace), workspace)}})
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def command_status(args: argparse.Namespace) -> int:
    workspace = resolve_workspace(args.workspace)
    payload = build_status(workspace, include_github=args.github_check)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def command_preflight(args: argparse.Namespace) -> int:
    workspace = resolve_workspace(args.workspace)
    status = build_status(workspace, include_github=args.github_check)
    request_id = f"private_{uuid.uuid4().hex[:12]}"
    capability = args.capability
    operating_mode = normalize_operating_mode(args.operating_mode, str(status.get("default_operating_mode") or "auto"))
    mode_summary = mode_policy_summary(operating_mode)
    capability_status = status.get("capability_summary", {}).get(capability, {})
    errors: list[str] = []
    if not status.get("connector_enabled"):
        errors.append("private connector is not enabled")
    if not capability_status.get("entitled"):
        errors.append(f"workspace is not entitled for {capability}")
    if not (status.get("gateway_endpoint_configured") or status.get("private_package_repo_configured")):
        errors.append("private gateway endpoint or private package repo is not configured")
    if args.execute:
        errors.append("real private execution is blocked in this public-safe connector until a production gateway/package service is deployed")

    decision = "ready_for_operator_review" if not errors else "blocked"
    request = {
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "generated_at": utc_now(),
        "capability": capability,
        "operating_mode": operating_mode,
        "approval_expectation": mode_summary.get("approval_expectation"),
        "mode_policy_ref": mode_summary.get("mode_policy_ref"),
        "mode_report_artifacts": mode_summary.get("expected_report_artifacts"),
        "dry_run": not args.execute,
        "decision": decision,
        "errors": errors,
        "allowed_public_request_fields": contract().get("allowed_public_request_fields", []),
        "status_summary": status,
        "forbidden_payloads": contract().get("forbidden_public_payloads", []),
        "operator_next_step": "Use the private gateway/package service after entitlement and approval." if not errors else "Fix blocked preflight items before requesting private capability.",
    }
    report_path = request_dir(workspace) / f"{request_id}.json"
    write_json(report_path, request)
    payload = {
        "command": "preflight",
        "status": decision,
        "request_id": request_id,
        "capability": capability,
        "errors": errors,
        "artifact_paths": {"request_summary": rel_workspace(report_path, workspace)},
        "mode_policy_summary": mode_summary,
        "policy_summary": {
            "local_summary_only": True,
            "network_call_performed": False,
            "tokens_printed": False,
            "private_assets_materialized": False,
            "real_execution_blocked": bool(args.execute),
        },
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if not errors and not args.execute else 2


def command_install(args: argparse.Namespace) -> int:
    workspace = resolve_workspace(args.workspace)
    status = build_status(workspace, include_github=args.github_check)
    config = read_json(connector_path(workspace))
    if not config:
        config = default_config(workspace)
    install_root = install_root_path(workspace, config)
    request_id = f"install_{uuid.uuid4().hex[:12]}"
    errors: list[str] = []
    install_capability = status.get("capability_summary", {}).get("private_package_install", {})
    private_repo = configured_value(config, "private_package_repo", "private_package_repo_env")
    private_ref = configured_value(config, "private_package_ref", "private_package_ref_env") or "main"
    try:
        ensure_path_inside_workspace(install_root, workspace)
    except ValueError as exc:
        errors.append(str(exc))
    if not install_capability.get("ready"):
        errors.append("workspace is not ready to install the private runtime package")
    if not private_repo:
        errors.append("private package repository is not configured")
    if args.execute:
        gh_path = shutil.which("gh")
        if not gh_path:
            errors.append("GitHub CLI is required for private package installation")
        if install_root.exists() and any(install_root.iterdir()):
            errors.append("private runtime install path already exists and is not empty")

    decision = "ready_for_private_runtime_install" if not errors else "blocked"
    request = {
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "generated_at": utc_now(),
        "capability": "private_package_install",
        "dry_run": not args.execute,
        "decision": decision,
        "errors": errors,
        "private_repo_configured": bool(private_repo),
        "private_ref_configured": bool(private_ref),
        "install_root": rel_workspace(install_root, workspace),
        "status_summary": status,
        "forbidden_payloads": contract().get("forbidden_public_payloads", []),
    }
    report_path = request_dir(workspace) / f"{request_id}.json"
    write_json(report_path, request)

    executed = False
    if args.execute and not errors:
        install_root.parent.mkdir(parents=True, exist_ok=True)
        clone = run_command(["gh", "repo", "clone", str(private_repo), str(install_root)])
        if clone.returncode != 0:
            errors.append(f"private package clone failed: {clone.stderr.strip() or clone.stdout.strip()}")
        else:
            checkout = subprocess.run(["git", "checkout", str(private_ref)], cwd=install_root, capture_output=True, text=True, check=False, timeout=60)
            if checkout.returncode != 0:
                errors.append(f"private package checkout failed: {checkout.stderr.strip() or checkout.stdout.strip()}")
            else:
                executed = True

    if errors:
        request["decision"] = "blocked"
        request["errors"] = errors
        write_json(report_path, request)

    payload = {
        "command": "install",
        "status": "installed" if executed else decision,
        "request_id": request_id,
        "errors": errors,
        "artifact_paths": {
            "request_summary": rel_workspace(report_path, workspace),
            "install_root": rel_workspace(install_root, workspace),
        },
        "policy_summary": {
            "network_call_performed": executed,
            "tokens_printed": False,
            "raw_workspace_code_stored": False,
            "private_assets_committed_to_public_repo": False,
        },
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if not errors and (not args.execute or executed) else 2


def command_build(args: argparse.Namespace) -> int:
    workspace = resolve_workspace(args.workspace)
    spec = Path(args.spec)
    if not spec.is_absolute():
        spec = (BASE_DIR / spec).resolve()
    output = Path(args.output).resolve() if args.output else None
    html_output = Path(args.html_output).resolve() if args.html_output else default_html_output_path(workspace, spec, output)
    status = build_status(workspace, include_github=args.github_check)
    config = read_json(connector_path(workspace))
    if not config:
        config = default_config(workspace)
    private_command = configured_command(config)
    operating_mode = normalize_operating_mode(args.operating_mode, str(config.get("default_operating_mode") or "auto"))
    mode_summary = mode_policy_summary(operating_mode)
    request_id = f"build_{uuid.uuid4().hex[:12]}"
    report_path = request_dir(workspace) / f"{request_id}.json"
    build_capability = status.get("capability_summary", {}).get("private_template_library_build", {})
    errors: list[str] = []
    if not spec.exists():
        errors.append(f"spec does not exist: {spec}")
    if not build_capability.get("ready_for_request"):
        errors.append("workspace is not ready to request a private template-library build")
    if args.execute and not private_command:
        errors.append("private build command is not configured")
    if args.execute and status.get("policy_summary", {}).get("file_upload_allowed"):
        errors.append("file upload is not supported by this local private package connector path")

    decision = "ready_for_private_build_execution" if not errors else "blocked"
    request = {
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "generated_at": utc_now(),
        "capability": "private_template_library_build",
        "operating_mode": operating_mode,
        "approval_expectation": mode_summary.get("approval_expectation"),
        "mode_policy_ref": mode_summary.get("mode_policy_ref"),
        "mode_report_artifacts": mode_summary.get("expected_report_artifacts"),
        "dry_run": not args.execute,
        "decision": decision,
        "errors": errors,
        "spec_path": spec.as_posix(),
        "output_path": output.as_posix() if output else None,
        "html_output_path": html_output.as_posix(),
        "status_summary": status,
        "forbidden_payloads": contract().get("forbidden_public_payloads", []),
        "operator_next_step": "Run with --execute after the private runtime package sets a private build command." if not errors and not args.execute else None,
    }
    write_json(report_path, request)

    executed = False
    private_result: dict[str, Any] | None = None
    private_payload: dict[str, Any] | None = None
    if args.execute and not errors and private_command:
        rendered = render_command_template(
            private_command,
            workspace=workspace,
            spec=spec,
            output=output,
            html_output=html_output,
            request_summary=report_path,
            capability="private_template_library_build",
            operating_mode=operating_mode,
        )
        result = run_command(rendered, timeout=args.timeout_seconds)
        executed = result.returncode == 0
        private_payload = maybe_parse_json_text(result.stdout)
        private_result = private_execution_summary(result)
        if result.returncode != 0:
            errors.append("private build command failed")

    if errors:
        request["decision"] = "blocked"
        request["errors"] = errors
        write_json(report_path, request)

    payload = {
        "command": "build",
        "status": "built" if executed else decision,
        "request_id": request_id,
        "errors": errors,
        "artifact_paths": {
            "request_summary": rel_workspace(report_path, workspace),
            "html_output": rel_workspace(html_output, workspace),
        },
        "mode_policy_summary": mode_summary,
        "private_result": private_result,
        "policy_summary": {
            "private_command_executed": executed,
            "tokens_printed": False,
            "raw_workspace_code_stored": False,
            "public_repo_contains_private_assets": False,
            "public_smoke_is_fallback_only": True,
            "raw_private_payload_omitted": True,
        },
    }
    if isinstance(private_payload, dict):
        private_artifacts = private_payload.get("artifact_paths", {})
        if isinstance(private_artifacts, dict):
            for key, value in private_artifacts.items():
                if isinstance(value, str) and value:
                    payload["artifact_paths"][key] = rel_workspace(Path(value), workspace)
                else:
                    payload["artifact_paths"][key] = value
        if isinstance(private_payload.get("validation_summary"), dict):
            payload["validation_summary"] = private_payload["validation_summary"]
        if isinstance(private_payload.get("policy_summary"), dict):
            payload["private_policy_summary"] = private_payload["policy_summary"]
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if not errors and (not args.execute or executed) else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Public-safe connector for private PPT capabilities.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    configure = subparsers.add_parser("configure")
    configure.add_argument("--workspace", required=True)
    configure.add_argument("--enable", action="store_true")
    configure.add_argument("--gateway-url-env", default=None)
    configure.add_argument("--gateway-url", default=None)
    configure.add_argument("--private-package-repo-env", default=None)
    configure.add_argument("--private-package-repo", default=None)
    configure.add_argument("--private-package-ref-env", default=None)
    configure.add_argument("--private-package-ref", default=None)
    configure.add_argument("--private-package-install-root", default=None)
    configure.add_argument("--private-build-command-env", default=None)
    configure.add_argument("--private-build-command-json", default=None)
    configure.add_argument("--default-operating-mode", choices=SUPPORTED_OPERATING_MODES, default="auto")
    configure.add_argument("--package-channel", default="invite_beta")
    configure.add_argument("--github-check", action="store_true")
    configure.add_argument("--reset", action="store_true")
    configure.set_defaults(func=command_configure)

    status = subparsers.add_parser("status")
    status.add_argument("--workspace", required=True)
    status.add_argument("--github-check", action="store_true")
    status.set_defaults(func=command_status)

    preflight = subparsers.add_parser("preflight")
    preflight.add_argument("--workspace", required=True)
    preflight.add_argument("--capability", default="private_template_library_build", choices=sorted(contract().get("capabilities", {}).keys()))
    preflight.add_argument("--operating-mode", choices=SUPPORTED_OPERATING_MODES, default=None)
    preflight.add_argument("--github-check", action="store_true")
    preflight.add_argument("--execute", action="store_true")
    preflight.set_defaults(func=command_preflight)

    install = subparsers.add_parser("install")
    install.add_argument("--workspace", required=True)
    install.add_argument("--github-check", action="store_true")
    install.add_argument("--execute", action="store_true")
    install.set_defaults(func=command_install)

    build = subparsers.add_parser("build")
    build.add_argument("--workspace", required=True)
    build.add_argument("--spec", required=True)
    build.add_argument("--output", default=None)
    build.add_argument("--html-output", default=None)
    build.add_argument("--operating-mode", choices=SUPPORTED_OPERATING_MODES, default=None)
    build.add_argument("--github-check", action="store_true")
    build.add_argument("--execute", action="store_true")
    build.add_argument("--timeout-seconds", type=int, default=600)
    build.set_defaults(func=command_build)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
