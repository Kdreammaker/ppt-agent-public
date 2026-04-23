from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import platform
import re
import sys
import zipfile
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
POLICY_PATH = BASE_DIR / "config" / "local_diagnostic_support_bundle_policy.json"
DEFAULT_B49_REPORT = BASE_DIR / "outputs" / "reports" / "reference_quality_dna.json"
DEFAULT_B50_REPORT = BASE_DIR / "outputs" / "reports" / "gateway_metadata_recommendation_mock.json"
CODE_PATTERN = re.compile(r"[A-Z0-9]{4,6}(?:-[A-Z0-9]{4,6}){2,5}", re.IGNORECASE)
SECRET_PATTERN = re.compile(r"(xox[baprs]-[A-Za-z0-9_-]+|sk-[A-Za-z0-9_-]{12,}|AIza[0-9A-Za-z_-]{20,})")
ABS_PATH_PATTERN = re.compile(r"[A-Za-z]:\\[^\s\"']+")
HTML_PATTERN = re.compile(r"<(html|body|head|script|style|div|section|article)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
HTML_TAG_PATTERN = re.compile(r"</?(?:html|body|head|script|style|div|section|article)\b[^>]*>", re.IGNORECASE)
REPORT_SUMMARY_KEYS = {
    "schema_version",
    "status",
    "command",
    "summary",
    "validation_summary",
    "policy_summary",
    "artifact_paths",
    "errors",
}


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
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


def require_within_workspace(path: Path, workspace: Path, *, label: str) -> Path:
    resolved = path.resolve()
    workspace_root = workspace.resolve()
    if resolved != workspace_root and not resolved.is_relative_to(workspace_root):
        raise ValueError(f"{label} must stay inside workspace: {resolved}")
    return resolved


def resolve_output_dir(value: str | None, workspace: Path) -> Path:
    if value is None:
        return workspace / "reports" / "support_bundle"
    path = Path(value)
    if not path.is_absolute():
        path = workspace / path
    return require_within_workspace(path, workspace, label="support bundle output directory")


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def mask_code(value: str) -> str:
    compact = value.replace("-", "")
    if len(compact) < 9:
        return "****"
    return f"{compact[:4]}...{compact[-4:]}"


def scrub_string(value: str, workspace: Path) -> str:
    def replace_code(match: re.Match[str]) -> str:
        return mask_code(match.group(0))

    scrubbed = CODE_PATTERN.sub(replace_code, value)
    scrubbed = SECRET_PATTERN.sub("[REDACTED_SECRET]", scrubbed)
    scrubbed = scrubbed.replace("CONFIDENTIAL_USER_DOCUMENT_TEXT", "[REDACTED_USER_CONTENT]")
    scrubbed = scrubbed.replace("assets/slides/references/", "[REDACTED_REFERENCE_PATH]/")
    scrubbed = HTML_PATTERN.sub("[REDACTED_HTML_SNIPPET]", scrubbed)
    scrubbed = HTML_TAG_PATTERN.sub("[REDACTED_HTML_TAG]", scrubbed)
    workspace_text = workspace.as_posix()
    scrubbed = scrubbed.replace(workspace_text, "[WORKSPACE]")
    scrubbed = scrubbed.replace(str(workspace), "[WORKSPACE]")
    scrubbed = ABS_PATH_PATTERN.sub("[REDACTED_PATH]", scrubbed)
    return scrubbed


def scrub_value(value: Any, workspace: Path) -> Any:
    if isinstance(value, str):
        return scrub_string(value, workspace)
    if isinstance(value, list):
        return [scrub_value(item, workspace) for item in value[:50]]
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(token in lowered for token in ("raw", "token", "secret", "api_key", "password", "workspace_code")):
                if isinstance(item, bool) or item is None:
                    cleaned[key] = item
                    continue
                if "hash" in lowered or "mask" in lowered:
                    cleaned[key] = scrub_value(item, workspace)
                else:
                    cleaned[key] = "[REDACTED]"
                continue
            cleaned[key] = scrub_value(item, workspace)
        return cleaned
    return value


def rel_to_workspace(path: Path, workspace: Path) -> str:
    try:
        return path.resolve().relative_to(workspace.resolve()).as_posix()
    except ValueError:
        return f"[external:{stable_hash(path.resolve().as_posix())}]"


def entitlement_summary(workspace: Path) -> dict[str, Any]:
    state = load_json(workspace / ".ppt-agent" / "entitlement.json")
    response = state.get("response", {}) if isinstance(state.get("response"), dict) else {}
    return {
        "present": bool(state),
        "activation_model": state.get("activation_model"),
        "workspace_code_mask": state.get("workspace_code_mask"),
        "workspace_code_hash_present": bool(state.get("workspace_code_hash")),
        "raw_code_stored": bool(state.get("raw_code_stored", False)),
        "status": response.get("status"),
        "allowed": bool(response.get("allowed", False)),
        "entitlements": response.get("entitlements", []),
        "expires_at": response.get("expires_at"),
        "package_channel": response.get("package_channel"),
    }


def healthcheck_summary(workspace: Path) -> dict[str, Any]:
    report = load_json(workspace / ".ppt-agent" / "healthcheck.json")
    checks = report.get("checks", {}) if isinstance(report.get("checks"), dict) else {}
    return {
        "present": bool(report),
        "status": report.get("status"),
        "required_failures": report.get("required_failures", []),
        "optional_missing": report.get("optional_missing", []),
        "checks": {
            name: {
                "required": item.get("required"),
                "ok": item.get("ok"),
                "version": item.get("version"),
            }
            for name, item in checks.items()
            if isinstance(item, dict)
        },
    }


def report_summaries(workspace: Path, limit: int) -> list[dict[str, Any]]:
    reports_dir = workspace / "reports"
    summaries: list[dict[str, Any]] = []
    if not reports_dir.exists():
        return summaries
    for path in sorted(reports_dir.glob("*.json"))[:limit]:
        data = load_json(path)
        summary = {key: data.get(key) for key in REPORT_SUMMARY_KEYS if key in data}
        summaries.append(
            {
                "path": rel_to_workspace(path, workspace),
                "size_bytes": path.stat().st_size,
                "modified_at": dt.datetime.fromtimestamp(path.stat().st_mtime, dt.UTC).isoformat().replace("+00:00", "Z"),
                "summary": scrub_value(summary, workspace),
            }
        )
    return summaries


def bounded_stream(value: Any, workspace: Path, *, max_lines: int, max_chars: int) -> dict[str, Any]:
    text = scrub_string(str(value or ""), workspace)
    lines = text.splitlines()
    bounded_lines = lines[:max_lines]
    bounded = "\n".join(bounded_lines)
    truncated = len(lines) > max_lines or len(bounded) > max_chars
    if len(bounded) > max_chars:
        bounded = bounded[:max_chars]
    return {
        "text": bounded,
        "lines": len(bounded_lines),
        "truncated": truncated,
    }


def command_output_snippets(workspace: Path, policy: dict[str, Any]) -> list[dict[str, Any]]:
    snippet_policy = policy.get("command_output_snippets_policy", {})
    max_snippets = int(snippet_policy.get("max_snippets", 5))
    max_lines = int(snippet_policy.get("max_lines_per_stream", 8))
    max_chars = int(snippet_policy.get("max_chars_per_stream", 1200))
    roots = [
        workspace / ".ppt-agent" / "command_output_snippets",
        workspace / "reports" / "command_output_snippets",
    ]
    snippets: list[dict[str, Any]] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.glob("*.json")):
            if len(snippets) >= max_snippets:
                return snippets
            data = load_json(path)
            status = str(data.get("status", "unknown"))
            if snippet_policy.get("include_failed_command_snippets", True) and status not in {"failed", "error", "invalid"}:
                continue
            snippets.append(
                {
                    "path": rel_to_workspace(path, workspace),
                    "label": scrub_string(str(data.get("label", path.stem)), workspace),
                    "status": status,
                    "returncode": data.get("returncode"),
                    "stdout": bounded_stream(data.get("stdout", ""), workspace, max_lines=max_lines, max_chars=max_chars),
                    "stderr": bounded_stream(data.get("stderr", ""), workspace, max_lines=max_lines, max_chars=max_chars),
                    "redaction_summary": {
                        "workspace_codes": "masked",
                        "secrets": "redacted",
                        "absolute_paths": "redacted",
                        "raw_reference_paths": "redacted",
                        "generated_html": "redacted",
                    },
                }
            )
    return snippets


def gateway_request_summaries(workspace: Path, limit: int) -> list[dict[str, Any]]:
    request_dir = workspace / ".ppt-agent" / "gateway_requests"
    summaries: list[dict[str, Any]] = []
    if not request_dir.exists():
        return summaries
    for path in sorted(request_dir.glob("*.json"))[:limit]:
        data = load_json(path)
        summaries.append(
            {
                "path": rel_to_workspace(path, workspace),
                "request_type": data.get("request_type"),
                "status": data.get("status"),
                "policy_summary": scrub_value(data.get("policy_summary", {}), workspace),
            }
        )
    return summaries


def reference_quality_summary(path: Path) -> dict[str, Any]:
    data = load_json(path)
    eligible = data.get("eligible_lightweight_dna", {}) if isinstance(data.get("eligible_lightweight_dna"), dict) else {}
    inventory = data.get("reference_inventory", {}) if isinstance(data.get("reference_inventory"), dict) else {}
    summary = data.get("summary", {}) if isinstance(data.get("summary"), dict) else {}
    return {
        "present": bool(data),
        "status": data.get("status"),
        "raw_reference_count": summary.get("raw_reference_files", inventory.get("file_count")),
        "eligible_dna_count": summary.get("eligible_dna_records", eligible.get("count")),
        "quality_gap_summary": data.get("quality_gap_summary", {}),
    }


def metadata_recommendation_summary(path: Path) -> dict[str, Any]:
    data = load_json(path)
    mock_response = data.get("mock_response", {}) if isinstance(data.get("mock_response"), dict) else {}
    request = data.get("metadata_request", {}) if isinstance(data.get("metadata_request"), dict) else {}
    return {
        "present": bool(data),
        "status": data.get("status"),
        "gateway_call_performed": mock_response.get("gateway_call_performed"),
        "fixture_backed_only": mock_response.get("fixture_backed_only"),
        "reference_dna_summaries": len(request.get("reference_dna_summaries", [])) if isinstance(request.get("reference_dna_summaries"), list) else 0,
        "asset_intent_summaries": len(request.get("asset_intent_summaries", [])) if isinstance(request.get("asset_intent_summaries"), list) else 0,
        "policy_summary": mock_response.get("policy_summary", {}),
    }


def build_bundle(workspace: Path, *, report_limit: int, include_repo_summaries: bool) -> dict[str, Any]:
    policy = load_json(POLICY_PATH)
    config = load_json(workspace / ".ppt-agent" / "config.json")
    consent = load_json(workspace / ".ppt-agent" / "consent.json")
    bundle = {
        "schema_version": "1.0",
        "bundle_id": f"support_{dt.datetime.now(dt.UTC).strftime('%Y%m%d%H%M%S')}",
        "generated_at": utc_now(),
        "policy": {
            "policy_id": policy.get("policy_id"),
            "telemetry_collection": policy.get("principles", {}).get("telemetry_collection"),
            "automatic_upload": policy.get("principles", {}).get("automatic_upload"),
            "explicit_user_action_required": policy.get("principles", {}).get("explicit_user_action_required"),
            "allowed_artifacts": policy.get("allowed_artifacts", []),
            "forbidden_content": policy.get("forbidden_content", []),
        },
        "runtime_summary": {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform_system": platform.system(),
            "platform_release": platform.release(),
            "platform_machine": platform.machine(),
        },
        "workspace_policy_summary": {
            "workspace_name": workspace.name,
            "workspace_hash": stable_hash(workspace.resolve().as_posix()),
            "mode": config.get("mode"),
            "gateway_enabled": bool(config.get("gateway_enabled", False)),
            "upload_allowed": bool(consent.get("upload_allowed", False)),
            "telemetry_enabled": bool(consent.get("telemetry_enabled", False)),
            "learning_collection_enabled": bool(consent.get("learning_collection_enabled", False)),
            "consent_mode": consent.get("consent_mode"),
            "gateway_asset_metadata_visible": bool(consent.get("gateway_asset_metadata_visible", False)),
        },
        "entitlement_summary": entitlement_summary(workspace),
        "healthcheck_summary": healthcheck_summary(workspace),
        "validation_report_summaries": report_summaries(workspace, report_limit),
        "command_output_snippets": command_output_snippets(workspace, policy),
        "gateway_request_summaries": gateway_request_summaries(workspace, report_limit),
        "diagnostic_scope": {
            "can_diagnose": [
                "runtime and dependency readiness",
                "workspace consent and no-upload policy",
                "workspace-code entitlement status without raw code",
                "healthcheck failures and fix hints",
                "validation report status summaries",
                "metadata-only gateway request summaries",
                "reference quality DNA summary",
                "metadata recommendation mock summary",
                "bounded redacted failed command output snippets",
            ],
            "cannot_diagnose_without_user_opt_in": [
                "full source documents",
                "generated PPTX or HTML content",
                "local image/template binaries",
                "raw reference files",
                "private gateway internals",
                "unredacted terminal logs",
            ],
        },
    }
    if include_repo_summaries:
        bundle["reference_quality_summary"] = reference_quality_summary(DEFAULT_B49_REPORT)
        bundle["metadata_recommendation_summary"] = metadata_recommendation_summary(DEFAULT_B50_REPORT)
    return scrub_value(bundle, workspace)


def write_markdown(path: Path, bundle: dict[str, Any]) -> None:
    policy = bundle["policy"]
    workspace = bundle["workspace_policy_summary"]
    entitlement = bundle["entitlement_summary"]
    health = bundle["healthcheck_summary"]
    lines = [
        "# Local Diagnostic Support Bundle",
        "",
        f"- bundle_id: {bundle['bundle_id']}",
        f"- generated_at: {bundle['generated_at']}",
        f"- telemetry_collection: {policy['telemetry_collection']}",
        f"- automatic_upload: {policy['automatic_upload']}",
        f"- workspace_name: {workspace['workspace_name']}",
        f"- mode: {workspace['mode']}",
        f"- consent_mode: {workspace['consent_mode']}",
        f"- entitlement_status: {entitlement.get('status')}",
        f"- entitlement_allowed: {entitlement.get('allowed')}",
        f"- healthcheck_status: {health.get('status')}",
        f"- validation_report_summaries: {len(bundle.get('validation_report_summaries', []))}",
        f"- command_output_snippets: {len(bundle.get('command_output_snippets', []))}",
        f"- gateway_request_summaries: {len(bundle.get('gateway_request_summaries', []))}",
        "",
        "## Privacy",
        "",
        "- No telemetry is collected.",
        "- No automatic upload is performed.",
        "- Raw workspace codes, local file contents, generated decks, generated HTML, image binaries, template binaries, private docs, and tokens are excluded.",
    ]
    if "reference_quality_summary" in bundle:
        ref = bundle["reference_quality_summary"]
        lines.extend(
            [
                "",
                "## Reference Quality Summary",
                "",
                f"- raw_reference_count: {ref.get('raw_reference_count')}",
                f"- eligible_dna_count: {ref.get('eligible_dna_count')}",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def create_zip(zip_path: Path, files: list[Path]) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in files:
            archive.write(file, arcname=file.name)


def validate_bundle_payload(bundle: dict[str, Any]) -> list[str]:
    serialized = json.dumps(bundle, ensure_ascii=False)
    errors: list[str] = []
    if CODE_PATTERN.search(serialized):
        errors.append("raw workspace-code-shaped token leaked")
    for token in ("xoxb-", "sk-", "AIza", "assets/slides/references/", "<html", "PK\x03\x04"):
        if token in serialized:
            errors.append(f"forbidden token leaked: {token!r}")
    if bundle.get("workspace_policy_summary", {}).get("upload_allowed") is not False:
        errors.append("upload_allowed must remain false in support bundle summary")
    if bundle.get("workspace_policy_summary", {}).get("telemetry_enabled") is not False:
        errors.append("telemetry_enabled must remain false in support bundle summary")
    if bundle.get("entitlement_summary", {}).get("raw_code_stored") is not False:
        errors.append("raw_code_stored must be false")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a local, sanitized diagnostic support bundle.")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--output-dir")
    parser.add_argument("--report-limit", type=int, default=20)
    parser.add_argument("--include-repo-summaries", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    workspace = resolve_workspace(args.workspace)
    output_dir = resolve_output_dir(args.output_dir, workspace)
    output_dir.mkdir(parents=True, exist_ok=True)

    bundle = build_bundle(workspace, report_limit=args.report_limit, include_repo_summaries=args.include_repo_summaries)
    errors = validate_bundle_payload(bundle) if args.check else []
    bundle["validation_summary"] = {
        "status": "valid" if not errors else "invalid",
        "errors": errors,
        "raw_code_leaks": 0 if not any("workspace" in error or "code" in error for error in errors) else 1,
    }
    json_path = output_dir / "support_bundle.json"
    md_path = output_dir / "support_bundle.md"
    zip_path = output_dir / "support_bundle.zip"
    write_json(json_path, bundle)
    write_markdown(md_path, bundle)
    create_zip(zip_path, [json_path, md_path])
    summary = {
        "command": "support-bundle",
        "status": bundle["validation_summary"]["status"],
        "artifact_paths": {
            "support_bundle_json": json_path.as_posix(),
            "support_bundle_md": md_path.as_posix(),
            "support_bundle_zip": zip_path.as_posix(),
        },
        "validation_summary": bundle["validation_summary"],
        "policy_summary": {
            "telemetry_collection": "disabled",
            "automatic_upload": False,
            "raw_code_included": False,
            "local_file_contents_included": False,
        },
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
