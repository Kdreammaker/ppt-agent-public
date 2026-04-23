from __future__ import annotations

import argparse
from contextlib import contextmanager
import datetime as dt
import getpass
import hashlib
import json
import os
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
CONTRACT_PATH = BASE_DIR / "config" / "workspace_code_entitlement_contract.json"
SCHEMA_VERSION = "1.0"
CODE_PATTERN = re.compile(r"^[A-Z0-9]{4,6}(?:-[A-Z0-9]{4,6}){2,5}$")


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def resolve_workspace(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    return path


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
    temp_path = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    temp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temp_path, path)


@contextmanager
def file_lock(lock_path: Path, *, timeout_seconds: float = 15.0, stale_seconds: float = 60.0):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout_seconds
    fd: int | None = None
    while fd is None:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"{os.getpid()} {utc_now()}\n".encode("utf-8"))
        except FileExistsError:
            try:
                age = time.time() - lock_path.stat().st_mtime
                if age > stale_seconds:
                    lock_path.unlink()
                    continue
            except OSError:
                continue
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Timed out waiting for usage state lock: {lock_path}")
            time.sleep(0.05)
    try:
        yield
    finally:
        if fd is not None:
            os.close(fd)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def mask_code(code: str) -> str:
    compact = code.replace("-", "")
    if len(compact) < 9 or not CODE_PATTERN.match(code.upper()):
        return "****"
    return f"{compact[:4]}...{compact[-4:]}"


def hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def hash_value(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_contract() -> dict[str, Any]:
    return load_json(CONTRACT_PATH)


def model_versions(contract: dict[str, Any]) -> dict[str, Any]:
    return dict(contract.get("model_versions", {}))


def daily_reset_at() -> str:
    now = dt.datetime.now().astimezone()
    tomorrow = now.date() + dt.timedelta(days=1)
    reset = dt.datetime.combine(tomorrow, dt.time.min, tzinfo=now.tzinfo)
    return reset.isoformat()


def usage_day_key() -> str:
    return dt.datetime.now().astimezone().date().isoformat()


def quota_policy(contract: dict[str, Any]) -> dict[str, Any]:
    return dict(contract.get("quota_policy", {}))


def default_quota_summary(contract: dict[str, Any], *, allowed: bool, daily_calls_used: int = 0) -> dict[str, Any]:
    policy = quota_policy(contract)
    daily_limit = int(policy.get("daily_call_limit", 0) or 0)
    max_activations = int(policy.get("max_activations_per_code", 0) or 0)
    remaining = max(0, daily_limit - daily_calls_used) if allowed else 0
    return {
        "max_activations": max_activations,
        "activation_count": 1 if allowed else 0,
        "active_workspace_count": 1 if allowed else 0,
        "registered_user_count": 1 if allowed else 0,
        "daily_call_limit": daily_limit,
        "daily_calls_used": daily_calls_used if allowed else 0,
        "daily_calls_remaining": remaining,
        "reset_at": daily_reset_at(),
        "reset_timezone": policy.get("daily_reset_timezone", "local_machine_timezone"),
        "user_list_visible": bool(policy.get("public_cli_can_show_user_list", False)),
    }


def enrich_response(response: dict[str, Any], contract: dict[str, Any], *, daily_calls_used: int = 0) -> dict[str, Any]:
    response = dict(response)
    response.setdefault(
        "quota_summary",
        default_quota_summary(contract, allowed=bool(response.get("allowed", False)), daily_calls_used=daily_calls_used),
    )
    response.setdefault("model_versions", model_versions(contract))
    return response


def consent_summary(workspace: Path) -> dict[str, Any]:
    consent = read_json(workspace / ".ppt-agent" / "consent.json")
    return {
        "consent_mode": consent.get("consent_mode", "unknown"),
        "upload_allowed": bool(consent.get("upload_allowed", False)),
        "telemetry_enabled": bool(consent.get("telemetry_enabled", False)),
        "learning_collection_enabled": bool(consent.get("learning_collection_enabled", False)),
        "gateway_asset_metadata_visible": bool(consent.get("gateway_asset_metadata_visible", False)),
    }


def build_request(workspace: Path, code: str, feature: str, package_version: str) -> dict[str, Any]:
    local_user = getpass.getuser() or "unknown"
    return {
        "request_id": f"ent_{uuid.uuid4().hex[:12]}",
        "cli_version": "0.1.0",
        "package_version": package_version,
        "workspace_code_hash": hash_code(code),
        "workspace_code_mask": mask_code(code),
        "workspace_instance_hash": hash_value(workspace.resolve().as_posix()),
        "local_user_hash": hash_value(local_user.lower()),
        "requested_feature": feature,
        "operating_mode": read_json(workspace / ".ppt-agent" / "config.json").get("mode", "local_only"),
        "consent_summary": consent_summary(workspace),
    }


def mock_gateway_response(request: dict[str, Any], code: str, contract: dict[str, Any]) -> dict[str, Any]:
    upper = code.upper()
    if not CODE_PATTERN.match(upper):
        return {
            "request_id": request["request_id"],
            "status": "malformed",
            "allowed": False,
            "entitlements": [],
            "expires_at": None,
            "package_channel": None,
            "feature_flags": {},
            "reason": "Workspace code format is invalid.",
        }
    if contract.get("mock_codes", {}).get("expired_contains", "EXPR") in upper:
        return {
            "request_id": request["request_id"],
            "status": "expired",
            "allowed": False,
            "entitlements": [],
            "expires_at": "2026-01-01T00:00:00Z",
            "package_channel": "invite_beta",
            "feature_flags": {},
            "reason": "Workspace code is expired.",
        }
    if contract.get("mock_codes", {}).get("denied_contains", "DENY") in upper:
        return {
            "request_id": request["request_id"],
            "status": "denied",
            "allowed": False,
            "entitlements": [],
            "expires_at": None,
            "package_channel": None,
            "feature_flags": {},
            "reason": "Workspace code is not entitled for this feature.",
        }
    if contract.get("mock_codes", {}).get("revoked_contains", "REVK") in upper:
        return {
            "request_id": request["request_id"],
            "status": "revoked",
            "allowed": False,
            "entitlements": [],
            "expires_at": None,
            "package_channel": None,
            "feature_flags": {},
            "reason": "Workspace code was revoked by the private admin system.",
        }
    if contract.get("mock_codes", {}).get("rotated_contains", "ROTA") in upper:
        return {
            "request_id": request["request_id"],
            "status": "rotated",
            "allowed": False,
            "entitlements": [],
            "expires_at": None,
            "package_channel": "invite_beta",
            "feature_flags": {},
            "reason": "Workspace code has been rotated; use the replacement code.",
        }
    if contract.get("mock_codes", {}).get("allowed_contains", "ALLOW") in upper:
        return {
            "request_id": request["request_id"],
            "status": "allowed",
            "allowed": True,
            "entitlements": list(contract.get("default_entitlements", [])),
            "expires_at": "2026-06-30T23:59:59Z",
            "package_channel": "invite_beta",
            "feature_flags": {
                "private_invite_installer": True,
                "public_thin_installer": False,
                "premium_recommendation": False,
            },
            "reason": "Workspace code is valid for invite beta.",
        }
    return {
        "request_id": request["request_id"],
        "status": "denied",
        "allowed": False,
        "entitlements": [],
        "expires_at": None,
        "package_channel": None,
        "feature_flags": {},
        "reason": "Workspace code did not match an active invite beta cohort.",
    }


def entitlement_path(workspace: Path) -> Path:
    return workspace / ".ppt-agent" / "entitlement.json"


def usage_path(workspace: Path) -> Path:
    return workspace / ".ppt-agent" / "usage.json"


def usage_lock_path(workspace: Path) -> Path:
    return workspace / ".ppt-agent" / "usage.json.lock"


def read_usage_state(workspace: Path, contract: dict[str, Any]) -> dict[str, Any]:
    state = read_json(usage_path(workspace))
    day = usage_day_key()
    if state.get("day") != day:
        state = {
            "schema_version": SCHEMA_VERSION,
            "day": day,
            "updated_at": utc_now(),
            "daily_calls_used": 0,
            "operations": {},
            "reset_at": daily_reset_at(),
            "daily_call_limit": int(quota_policy(contract).get("daily_call_limit", 0) or 0),
        }
    return state


def write_usage_state(workspace: Path, state: dict[str, Any]) -> None:
    state["updated_at"] = utc_now()
    write_json(usage_path(workspace), state)


@contextmanager
def locked_usage_state(workspace: Path, contract: dict[str, Any]):
    with file_lock(usage_lock_path(workspace)):
        state = read_usage_state(workspace, contract)
        yield state
        write_usage_state(workspace, state)


def usage_report_from_state(workspace: Path, contract: dict[str, Any], usage: dict[str, Any]) -> dict[str, Any]:
    entitlement = read_json(entitlement_path(workspace))
    response = entitlement.get("response", {})
    used = int(usage.get("daily_calls_used", 0) or 0)
    allowed = bool(response.get("allowed", False))
    summary = default_quota_summary(contract, allowed=allowed, daily_calls_used=used)
    return {
        "command": "usage",
        "status": response.get("status", "missing"),
        "allowed": allowed,
        "workspace_code_mask": entitlement.get("workspace_code_mask"),
        "quota_summary": summary,
        "model_versions": model_versions(contract),
        "artifact_paths": {"usage": ".ppt-agent/usage.json", "entitlement": ".ppt-agent/entitlement.json"},
        "policy_summary": {
            "raw_code_stored": False,
            "raw_user_identity_stored": False,
            "raw_machine_fingerprint_stored": False,
            "user_list_visible_to_public_cli": False,
        },
    }


def usage_report(workspace: Path, contract: dict[str, Any]) -> dict[str, Any]:
    with locked_usage_state(workspace, contract) as usage:
        return usage_report_from_state(workspace, contract, usage)


def command_activate(args: argparse.Namespace) -> int:
    workspace = resolve_workspace(args.workspace)
    contract = load_contract()
    request = build_request(workspace, args.workspace_code, args.feature, args.package_version)
    with locked_usage_state(workspace, contract) as usage:
        response = enrich_response(
            mock_gateway_response(request, args.workspace_code, contract),
            contract,
            daily_calls_used=int(usage.get("daily_calls_used", 0) or 0),
        )
    state = {
        "schema_version": SCHEMA_VERSION,
        "updated_at": utc_now(),
        "activation_model": contract["activation_model"],
        "workspace_code_hash": request["workspace_code_hash"],
        "workspace_code_mask": request["workspace_code_mask"],
        "raw_code_stored": False,
        "request": request,
        "response": response,
        "policy_summary": {
            "workspace_code_only": True,
            "license_key_supported": False,
            "payment_supported": False,
            "telemetry_enabled": False,
            "upload_allowed": False,
            "raw_code_storage_allowed": False,
            "raw_user_identity_storage_allowed": False,
            "raw_machine_fingerprint_storage_allowed": False,
        },
    }
    write_json(entitlement_path(workspace), state)
    summary = {
        "command": "activate",
        "status": response["status"],
        "allowed": response["allowed"],
        "workspace_code_mask": request["workspace_code_mask"],
        "entitlements": response["entitlements"],
        "expires_at": response.get("expires_at"),
        "quota_summary": response.get("quota_summary", {}),
        "model_versions": response.get("model_versions", {}),
        "artifact_paths": {"entitlement": ".ppt-agent/entitlement.json"},
        "policy_summary": state["policy_summary"],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if response["allowed"] else 2


def command_status(args: argparse.Namespace) -> int:
    workspace = resolve_workspace(args.workspace)
    state = read_json(entitlement_path(workspace))
    if not state:
        print(json.dumps({"command": "status", "status": "missing", "allowed": False}, indent=2))
        return 1
    response = state.get("response", {})
    print(
        json.dumps(
            {
                "command": "status",
                "status": response.get("status", "unknown"),
                "allowed": bool(response.get("allowed", False)),
                "workspace_code_mask": state.get("workspace_code_mask"),
                "entitlements": response.get("entitlements", []),
                "expires_at": response.get("expires_at"),
                "package_channel": response.get("package_channel"),
                "quota_summary": response.get("quota_summary", {}),
                "model_versions": response.get("model_versions", {}),
                "policy_summary": state.get("policy_summary", {}),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if response.get("allowed") else 1


def command_check(args: argparse.Namespace) -> int:
    workspace = resolve_workspace(args.workspace)
    state = read_json(entitlement_path(workspace))
    response = state.get("response", {})
    entitlements = set(response.get("entitlements", []))
    allowed = bool(response.get("allowed", False)) and args.feature in entitlements
    print(
        json.dumps(
            {
                "command": "check",
                "status": "allowed" if allowed else "denied",
                "feature": args.feature,
                "allowed": allowed,
                "workspace_code_mask": state.get("workspace_code_mask"),
                "quota_summary": response.get("quota_summary", {}),
                "model_versions": response.get("model_versions", {}),
                "policy_summary": state.get("policy_summary", {}),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if allowed else 2


def command_usage(args: argparse.Namespace) -> int:
    workspace = resolve_workspace(args.workspace)
    contract = load_contract()
    report = usage_report(workspace, contract)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report.get("allowed") else 1


def command_record_call(args: argparse.Namespace) -> int:
    workspace = resolve_workspace(args.workspace)
    contract = load_contract()
    entitlement = read_json(entitlement_path(workspace))
    response = entitlement.get("response", {})
    if not response.get("allowed", False):
        print(json.dumps({"command": "record-call", "status": "denied", "allowed": False}, indent=2))
        return 2
    with locked_usage_state(workspace, contract) as usage:
        used = int(usage.get("daily_calls_used", 0) or 0)
        daily_limit = int(quota_policy(contract).get("daily_call_limit", 0) or 0)
        if daily_limit and used >= daily_limit:
            payload = usage_report_from_state(workspace, contract, usage)
            payload.update({"command": "record-call", "status": "daily_limit_exceeded", "allowed": False})
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 2
        operation = args.operation
        operations = usage.setdefault("operations", {})
        operations[operation] = int(operations.get(operation, 0) or 0) + 1
        usage["daily_calls_used"] = used + 1
        payload = usage_report_from_state(workspace, contract, usage)
        payload.update({"command": "record-call", "status": "recorded", "operation": operation})
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Workspace-code-only entitlement helper for invite beta.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    activate = subparsers.add_parser("activate")
    activate.add_argument("--workspace", required=True)
    activate.add_argument("--workspace-code", required=True)
    activate.add_argument("--feature", default="private_package_access")
    activate.add_argument("--package-version", default="0.1.0")
    activate.set_defaults(func=command_activate)

    status = subparsers.add_parser("status")
    status.add_argument("--workspace", required=True)
    status.set_defaults(func=command_status)

    check = subparsers.add_parser("check")
    check.add_argument("--workspace", required=True)
    check.add_argument("--feature", required=True)
    check.set_defaults(func=command_check)

    usage = subparsers.add_parser("usage")
    usage.add_argument("--workspace", required=True)
    usage.set_defaults(func=command_usage)

    record_call = subparsers.add_parser("record-call")
    record_call.add_argument("--workspace", required=True)
    record_call.add_argument("--operation", default="cli_call")
    record_call.set_defaults(func=command_record_call)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
