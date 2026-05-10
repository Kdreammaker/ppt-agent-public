from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT_PATH = BASE_DIR / "config" / "public_cli_command_contract.json"
DEFAULT_REPORT_JSON = BASE_DIR / "outputs" / "reports" / "public_cli_command_contract_validation.json"
DEFAULT_REPORT_MD = BASE_DIR / "outputs" / "reports" / "public_cli_command_contract_validation.md"

REQUIRED_COMMANDS = {
    "init",
    "healthcheck",
    "plan",
    "compose",
    "patch",
    "build",
    "validate",
    "assets",
    "gateway",
    "history",
    "support-bundle",
    "deliver",
}
REQUIRED_OUTPUT_ROOTS = {"intake", "specs", "pptx", "html", "reports", "previews", "local_state"}
FORBIDDEN_SUMMARY_PAYLOADS = {
    "full_spec_json",
    "full_html_document",
    "binary_pptx_content",
    "source_file_contents",
    "secrets_or_tokens",
}
REQUIRED_FIRST_RUN_CHECKS = {
    "os",
    "python",
    "path_lookup",
    "powershell",
    "python_package_pptx",
    "python_package_pillow",
    "python_package_pymupdf",
    "python_package_pydantic",
    "workspace_write",
    "mcp_adapter_policy",
}


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def base_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(BASE_DIR).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def require_non_empty_string(value: Any, label: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} must be a non-empty string")


def validate_command(command: Any, index: int) -> list[str]:
    errors: list[str] = []
    label = f"commands[{index}]"
    if not isinstance(command, dict):
        return [f"{label} must be an object"]
    name = command.get("name")
    require_non_empty_string(name, f"{label}.name", errors)
    require_non_empty_string(command.get("purpose"), f"{label}.purpose", errors)
    require_non_empty_string(command.get("current_status"), f"{label}.current_status", errors)
    if command.get("local_only_supported") is not True:
        errors.append(f"{label}.local_only_supported must be true")
    if command.get("gateway_required") is not False:
        errors.append(f"{label}.gateway_required must be false for MVP commands")
    if command.get("upload_default") is not False:
        errors.append(f"{label}.upload_default must be false")
    if command.get("telemetry_default") != "disabled":
        errors.append(f"{label}.telemetry_default must be disabled")
    mapping = command.get("implementation_mapping")
    if not isinstance(mapping, dict):
        errors.append(f"{label}.implementation_mapping must be an object")
    else:
        if not any(key in mapping for key in ("current_entrypoint", "current_entrypoints", "planned_entrypoint")):
            errors.append(f"{label}.implementation_mapping must name a current or planned entrypoint")
    for key in ("inputs", "outputs"):
        value = command.get(key)
        if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item for item in value):
            errors.append(f"{label}.{key} must be a non-empty list of strings")
    exit_codes = command.get("exit_codes")
    if not isinstance(exit_codes, dict) or "0" not in exit_codes:
        errors.append(f"{label}.exit_codes must include code 0")
    elif any(not isinstance(code, str) or not isinstance(message, str) for code, message in exit_codes.items()):
        errors.append(f"{label}.exit_codes must map string codes to string descriptions")
    if name == "build":
        outputs = set(command.get("outputs", []))
        if not any("pptx" in output for output in outputs):
            errors.append("build command must include a PPTX output")
        if not any("html" in output for output in outputs):
            errors.append("build command must include an HTML output")
    if name == "plan" and not any("ascii_blueprint" in output for output in command.get("outputs", [])):
        errors.append("plan command must include ASCII blueprint outputs")
    return errors


def validate_contract(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != "1.0":
        errors.append("schema_version must be '1.0'")
    if data.get("contract_id") != "public_cli_mvp_command_contract":
        errors.append("contract_id must be public_cli_mvp_command_contract")
    principles = data.get("principles")
    if not isinstance(principles, dict):
        errors.append("principles must be an object")
    else:
        if principles.get("canonical_engine") != "public_cli":
            errors.append("principles.canonical_engine must be public_cli")
        if principles.get("mcp_policy") != "thin_adapter_after_cli_contract_stabilizes":
            errors.append("principles.mcp_policy must defer MCP to a thin adapter")
        if principles.get("local_only_default") is not True:
            errors.append("principles.local_only_default must be true")
        if principles.get("gateway_enabled_default") is not False:
            errors.append("principles.gateway_enabled_default must be false")
        if principles.get("upload_allowed_default") is not False:
            errors.append("principles.upload_allowed_default must be false")
        if principles.get("telemetry_default") != "disabled":
            errors.append("principles.telemetry_default must be disabled")

    workspace_outputs = data.get("workspace_outputs")
    if not isinstance(workspace_outputs, dict):
        errors.append("workspace_outputs must be an object")
    else:
        missing_roots = sorted(REQUIRED_OUTPUT_ROOTS - set(workspace_outputs))
        if missing_roots:
            errors.append(f"workspace_outputs missing roots: {missing_roots}")
        for key, value in workspace_outputs.items():
            if key in REQUIRED_OUTPUT_ROOTS and (not isinstance(value, str) or Path(value).is_absolute()):
                errors.append(f"workspace_outputs.{key} must be a relative path string")

    summary_contract = data.get("machine_summary_contract")
    if not isinstance(summary_contract, dict):
        errors.append("machine_summary_contract must be an object")
    else:
        if summary_contract.get("format") != "json":
            errors.append("machine_summary_contract.format must be json")
        if not isinstance(summary_contract.get("max_summary_chars"), int) or summary_contract["max_summary_chars"] > 4000:
            errors.append("machine_summary_contract.max_summary_chars must be an integer <= 4000")
        forbidden = set(summary_contract.get("must_not_include", []))
        missing_forbidden = sorted(FORBIDDEN_SUMMARY_PAYLOADS - forbidden)
        if missing_forbidden:
            errors.append(f"machine_summary_contract.must_not_include missing: {missing_forbidden}")

    first_run = data.get("first_run_healthcheck")
    if not isinstance(first_run, dict):
        errors.append("first_run_healthcheck must be an object")
    else:
        if first_run.get("standalone_exe_required") is not False:
            errors.append("first_run_healthcheck.standalone_exe_required must be false")
        if first_run.get("minimum_python") != "3.11":
            errors.append("first_run_healthcheck.minimum_python must be 3.11")
        missing_checks = sorted(REQUIRED_FIRST_RUN_CHECKS - set(first_run.get("required_checks", [])))
        if missing_checks:
            errors.append(f"first_run_healthcheck.required_checks missing: {missing_checks}")
        if first_run.get("mcp_setup_policy") != "same_cli_package_api_same_local_consent_no_upload":
            errors.append("first_run_healthcheck.mcp_setup_policy must preserve CLI/MCP consent boundary")

    commands = data.get("commands")
    if not isinstance(commands, list):
        return errors + ["commands must be a list"]
    seen: set[str] = set()
    for index, command in enumerate(commands):
        errors.extend(validate_command(command, index))
        if isinstance(command, dict) and isinstance(command.get("name"), str):
            name = command["name"]
            if name in seen:
                errors.append(f"duplicate command: {name}")
            seen.add(name)
    missing_commands = sorted(REQUIRED_COMMANDS - seen)
    extra_commands = sorted(seen - REQUIRED_COMMANDS)
    if missing_commands:
        errors.append(f"missing required commands: {missing_commands}")
    if extra_commands:
        errors.append(f"unexpected commands: {extra_commands}")

    mcp_policy = data.get("mcp_adapter_policy")
    if not isinstance(mcp_policy, dict):
        errors.append("mcp_adapter_policy must be an object")
    else:
        if mcp_policy.get("status") != "deferred_until_cli_contract_stabilizes":
            errors.append("mcp_adapter_policy.status must defer MCP")
        if mcp_policy.get("first_allowed_backlog_item") != "B43":
            errors.append("mcp_adapter_policy.first_allowed_backlog_item must be B43")
        forbidden = set(mcp_policy.get("forbidden_in_mvp", []))
        for required in ("parallel_renderer_logic", "parallel_composer_logic", "default_content_upload"):
            if required not in forbidden:
                errors.append(f"mcp_adapter_policy.forbidden_in_mvp missing {required}")
    return errors


def write_report(data: dict[str, Any], errors: list[str], report_json: Path, report_md: Path) -> None:
    report_json.parent.mkdir(parents=True, exist_ok=True)
    commands = data.get("commands", [])
    payload = {
        "schema_version": "1.0",
        "status": "valid" if not errors else "invalid",
        "summary": {
            "errors": len(errors),
            "commands": len(commands) if isinstance(commands, list) else 0,
            "required_commands": sorted(REQUIRED_COMMANDS),
            "mcp_first_allowed_backlog_item": data.get("mcp_adapter_policy", {}).get("first_allowed_backlog_item"),
        },
        "errors": errors,
        "contract_path": base_relative(DEFAULT_CONTRACT_PATH),
    }
    report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# Public CLI Command Contract Validation",
        "",
        f"- status: {payload['status']}",
        f"- commands: {payload['summary']['commands']}",
        f"- errors: {payload['summary']['errors']}",
        f"- MCP first allowed backlog item: {payload['summary']['mcp_first_allowed_backlog_item']}",
    ]
    if errors:
        lines.append("")
        lines.append("## Errors")
        lines.extend(f"- {error}" for error in errors)
    report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the public CLI MVP command contract.")
    parser.add_argument("--contract", default=DEFAULT_CONTRACT_PATH.as_posix())
    parser.add_argument("--report-json", default=DEFAULT_REPORT_JSON.as_posix())
    parser.add_argument("--report-md", default=DEFAULT_REPORT_MD.as_posix())
    args = parser.parse_args(argv)
    contract_path = Path(args.contract)
    if not contract_path.is_absolute():
        contract_path = (BASE_DIR / contract_path).resolve()
    report_json = Path(args.report_json)
    if not report_json.is_absolute():
        report_json = (BASE_DIR / report_json).resolve()
    report_md = Path(args.report_md)
    if not report_md.is_absolute():
        report_md = (BASE_DIR / report_md).resolve()
    data = load_json(contract_path)
    errors = validate_contract(data)
    write_report(data, errors, report_json, report_md)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"public_cli_contract=valid commands={len(data.get('commands', []))} path={base_relative(contract_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
