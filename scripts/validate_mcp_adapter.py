from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
MANIFEST_PATH = BASE_DIR / "config" / "mcp_adapter_manifest.json"
DEFAULT_REPORT = BASE_DIR / "outputs" / "reports" / "mcp_adapter_validation.json"

FORBIDDEN_TOOL_TOKENS = {"upload", "deliver", "public_share", "materialize"}
REQUIRED_TOOLS = {
    "plan_blueprint",
    "compose_spec",
    "build_outputs",
    "patch_slide_slot",
    "validate_outputs",
    "summarize_project",
    "open_html_workbench",
    "emit_workbench_handoff",
    "validate_reference_design_recipe",
    "publish_html_viewer",
    "handle_workbench_return",
}


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def run(args: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=BASE_DIR, input=input_text, capture_output=True, text=True, check=False, timeout=240)


def base_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(BASE_DIR).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def validate_manifest(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != "1.0":
        errors.append("schema_version must be 1.0")
    if data.get("canonical_engine") != "public_cli":
        errors.append("canonical_engine must be public_cli")
    policy = data.get("policy")
    if not isinstance(policy, dict):
        errors.append("policy must be an object")
        return errors
    if policy.get("adapter_shape") != "thin_wrapper_over_cli_commands":
        errors.append("adapter_shape must be thin_wrapper_over_cli_commands")
    if policy.get("local_only_default") is not True:
        errors.append("local_only_default must be true")
    if policy.get("gateway_required") is not False:
        errors.append("gateway_required must be false")
    if policy.get("upload_allowed_default") is not False:
        errors.append("upload_allowed_default must be false")
    if policy.get("telemetry_default") != "disabled":
        errors.append("telemetry_default must be disabled")

    tools = data.get("tools")
    if not isinstance(tools, list):
        return errors + ["tools must be a list"]
    max_tools = int(policy.get("max_tools", 0))
    if len(tools) > max_tools:
        errors.append(f"too many tools: {len(tools)} > {max_tools}")
    max_description = int(policy.get("max_tool_description_chars", 0))
    max_total = int(policy.get("max_total_description_chars", 0))
    total_description_chars = 0
    seen: set[str] = set()
    for index, tool in enumerate(tools):
        label = f"tools[{index}]"
        if not isinstance(tool, dict):
            errors.append(f"{label} must be an object")
            continue
        name = tool.get("name")
        description = tool.get("description")
        if not isinstance(name, str) or not name:
            errors.append(f"{label}.name must be non-empty")
            continue
        if name in seen:
            errors.append(f"duplicate tool: {name}")
        seen.add(name)
        lowered_name = name.lower()
        if any(token in lowered_name for token in FORBIDDEN_TOOL_TOKENS):
            errors.append(f"{name} includes forbidden tool family token")
        if not isinstance(description, str) or not description:
            errors.append(f"{label}.description must be non-empty")
        else:
            total_description_chars += len(description)
            if len(description) > max_description:
                errors.append(f"{name} description too long: {len(description)} > {max_description}")
        if not isinstance(tool.get("cli_mapping"), str) or not tool.get("cli_mapping"):
            errors.append(f"{label}.cli_mapping must be non-empty")
        schema = tool.get("input_schema")
        if not isinstance(schema, dict) or schema.get("type") != "object":
            errors.append(f"{label}.input_schema must be an object JSON schema")
    missing = sorted(REQUIRED_TOOLS - seen)
    extra = sorted(seen - REQUIRED_TOOLS)
    if missing:
        errors.append(f"missing required tools: {missing}")
    if extra:
        errors.append(f"unexpected tools: {extra}")
    if total_description_chars > max_total:
        errors.append(f"total tool descriptions too long: {total_description_chars} > {max_total}")
    return errors


def parse_tool_result(stdout: str) -> dict[str, Any]:
    data = json.loads(stdout)
    if not isinstance(data, dict):
        raise ValueError("tool result must be an object")
    return data


def parse_content_text(payload: dict[str, Any]) -> dict[str, Any]:
    text = payload.get("content", [{}])[0].get("text", "")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("MCP content text must be a JSON object")
    return data


def parse_stdout_head_json(result_payload: dict[str, Any]) -> dict[str, Any]:
    if isinstance(result_payload.get("stdout_json"), dict):
        return result_payload["stdout_json"]
    lines = result_payload.get("stdout_head", [])
    data = json.loads("\n".join(lines))
    if not isinstance(data, dict):
        raise ValueError("stdout_head JSON must be an object")
    return data


def reference_content_free_from_report(path: Path, *, handoff: bool = False) -> bool:
    data = load_json(path)
    if handoff:
        return data.get("envelope", {}).get("reference_design_library", {}).get("content_free_only") is True
    return data.get("summary", {}).get("content_free_only") is True


def validate_adapter_runtime() -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    checks: dict[str, Any] = {}
    list_result = run([sys.executable, "scripts/mcp_adapter.py", "--list-tools"])
    if list_result.returncode != 0:
        errors.append(f"--list-tools failed: {list_result.stderr.strip() or list_result.stdout.strip()}")
    else:
        payload = parse_tool_result(list_result.stdout)
        tools = payload.get("tools", [])
        if len(tools) != len(REQUIRED_TOOLS):
            errors.append(f"--list-tools returned {len(tools)} tools")
        checks["list_tools"] = "passed"

    validate_result = run(
        [
            sys.executable,
            "scripts/mcp_adapter.py",
            "--call-tool",
            "validate_outputs",
            "--arguments",
            "{\"scope\":\"public_cli_contract\"}",
        ]
    )
    if validate_result.returncode != 0:
        errors.append(f"validate_outputs tool failed: {validate_result.stderr.strip() or validate_result.stdout.strip()}")
    else:
        payload = parse_tool_result(validate_result.stdout)
        text = payload.get("content", [{}])[0].get("text", "")
        if "public_cli_contract=valid" not in text:
            errors.append("validate_outputs did not report public_cli_contract=valid")
        checks["validate_outputs"] = "passed"

    patch_reject = run(
        [
            sys.executable,
            "scripts/mcp_adapter.py",
            "--call-tool",
            "patch_slide_slot",
            "--arguments",
            "{\"spec_path\":\"data/specs/business_growth_review_spec.json\",\"slide\":1,\"slot_kind\":\"text\",\"slot\":\"title\",\"value\":\"Unsafe write\"}",
        ]
    )
    if patch_reject.returncode != 0:
        errors.append(f"patch rejection tool call failed: {patch_reject.stderr.strip() or patch_reject.stdout.strip()}")
    else:
        payload = parse_tool_result(patch_reject.stdout)
        text = payload.get("content", [{}])[0].get("text", "")
        if "confirm_write=true" not in text:
            errors.append("patch_slide_slot must reject in-place writes without confirm_write=true")
        checks["patch_confirmation_guard"] = "passed"

    jsonrpc_input = "\n".join(
        [
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
            "",
        ]
    )
    rpc_result = run([sys.executable, "scripts/mcp_adapter.py", "--serve"], input_text=jsonrpc_input)
    if rpc_result.returncode != 0:
        errors.append(f"stdio JSON-RPC smoke failed: {rpc_result.stderr.strip() or rpc_result.stdout.strip()}")
    else:
        lines = [json.loads(line) for line in rpc_result.stdout.splitlines() if line.strip()]
        if len(lines) != 2 or lines[0].get("result", {}).get("serverInfo", {}).get("name") != "ppt-public-cli-thin-adapter":
            errors.append("initialize response missing expected server info")
        if len(lines) < 2 or "tools" not in lines[1].get("result", {}):
            errors.append("tools/list response missing tools")
        checks["stdio_jsonrpc"] = "passed"

    reference_result = run(
        [
            sys.executable,
            "scripts/mcp_adapter.py",
            "--call-tool",
            "validate_reference_design_recipe",
            "--arguments",
            "{\"report\":\"outputs/reports/commercial_mvp_reference_design_recipe_mcp.json\"}",
        ]
    )
    if reference_result.returncode != 0:
        errors.append(f"reference design recipe tool failed: {reference_result.stderr.strip() or reference_result.stdout.strip()}")
    else:
        payload = parse_tool_result(reference_result.stdout)
        text_payload = parse_content_text(payload)
        text = payload.get("content", [{}])[0].get("text", "")
        reference_report = BASE_DIR / "outputs" / "reports" / "commercial_mvp_reference_design_recipe_mcp.json"
        if "commercial_mvp_reference_design_recipe_mcp.json" not in text:
            errors.append("reference design recipe tool did not return expected report path")
        if text_payload.get("status") != "passed" or not reference_content_free_from_report(reference_report):
            errors.append("validate_reference_design_recipe must report content_free_only=true")
        checks["reference_design_recipe"] = "passed"

    open_result = run(
        [
            sys.executable,
            "scripts/mcp_adapter.py",
            "--call-tool",
            "open_html_workbench",
            "--arguments",
            "{}",
        ]
    )
    if open_result.returncode != 0:
        errors.append(f"open HTML workbench tool failed: {open_result.stderr.strip() or open_result.stdout.strip()}")
    else:
        payload = parse_tool_result(open_result.stdout)
        text_payload = parse_content_text(payload)
        open_payload = parse_stdout_head_json(text_payload)
        if open_payload.get("reference_design_library", {}).get("content_free_only") is not True:
            errors.append("open_html_workbench must report reference_design_library.content_free_only=true")
        checks["open_html_workbench"] = "passed"

    for target in ("pdf", "pptx"):
        report_name = f"commercial_mvp_workbench_handoff_{target}_mcp.json"
        handoff_result = run(
            [
                sys.executable,
                "scripts/mcp_adapter.py",
                "--call-tool",
                "emit_workbench_handoff",
                "--arguments",
                json.dumps({"target": target, "mode": "assistant", "report": f"outputs/reports/{report_name}"}),
            ]
        )
        if handoff_result.returncode != 0:
            errors.append(f"{target} handoff tool failed: {handoff_result.stderr.strip() or handoff_result.stdout.strip()}")
        else:
            report_path = BASE_DIR / "outputs" / "reports" / report_name
            if not reference_content_free_from_report(report_path, handoff=True):
                errors.append(f"{target} MCP handoff must report reference_design_library.content_free_only=true")
            checks[f"emit_workbench_handoff_{target}"] = "passed"

    viewer_result = run(
        [
            sys.executable,
            "scripts/mcp_adapter.py",
            "--call-tool",
            "publish_html_viewer",
            "--arguments",
            "{\"plan\":\"paid\",\"report\":\"outputs/reports/commercial_mvp_published_viewer_mcp.json\"}",
        ]
    )
    if viewer_result.returncode != 0:
        errors.append(f"published viewer tool failed: {viewer_result.stderr.strip() or viewer_result.stdout.strip()}")
    else:
        payload = parse_tool_result(viewer_result.stdout)
        text = payload.get("content", [{}])[0].get("text", "")
        if "commercial_mvp_published_viewer_mcp.json" not in text:
            errors.append("published viewer tool did not return expected report path")
        checks["published_viewer"] = "passed"

    final_guard = run(
        [
            sys.executable,
            "scripts/mcp_adapter.py",
            "--call-tool",
            "handle_workbench_return",
            "--arguments",
            "{\"return_kind\":\"final\",\"return_ref\":\"unsafe-final-ref\"}",
        ]
    )
    if final_guard.returncode != 0:
        errors.append(f"host return guard tool failed: {final_guard.stderr.strip() or final_guard.stdout.strip()}")
    else:
        payload = parse_tool_result(final_guard.stdout)
        text = payload.get("content", [{}])[0].get("text", "")
        guard_report = BASE_DIR / "outputs" / "reports" / "commercial_mvp_host_ai_return_handling.json"
        guard_payload = load_json(guard_report) if guard_report.exists() else {}
        if "awaiting_host_ai" not in text or guard_payload.get("reason") != "safe_result_ref_required":
            errors.append("handle_workbench_return must block final_received without safe result ref")
        checks["host_return_final_guard"] = "passed"
    return errors, checks


def write_report(report_path: Path, errors: list[str], checks: dict[str, Any], manifest: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    description_chars = sum(len(str(tool.get("description", ""))) for tool in manifest.get("tools", []))
    payload = {
        "schema_version": "1.0",
        "status": "valid" if not errors else "invalid",
        "summary": {
            "errors": len(errors),
            "tools": len(manifest.get("tools", [])),
            "description_chars": description_chars,
            "checks": checks,
        },
        "errors": errors,
    }
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the thin MCP adapter spike.")
    parser.add_argument("--manifest", default=MANIFEST_PATH.as_posix())
    parser.add_argument("--report", default=DEFAULT_REPORT.as_posix())
    args = parser.parse_args(argv)
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = (BASE_DIR / manifest_path).resolve()
    report = Path(args.report)
    if not report.is_absolute():
        report = (BASE_DIR / report).resolve()
    manifest = load_json(manifest_path)
    errors = validate_manifest(manifest)
    runtime_errors, checks = validate_adapter_runtime()
    errors.extend(runtime_errors)
    write_report(report, errors, checks, manifest)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"mcp_adapter=valid tools={len(manifest.get('tools', []))} report={base_relative(report)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
