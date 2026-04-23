from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
MANIFEST_PATH = BASE_DIR / "config" / "mcp_adapter_manifest.json"

VALIDATOR_COMMANDS = {
    "public_cli_contract": [sys.executable, "scripts/validate_public_cli_contract.py"],
    "private_gateway_contract": [sys.executable, "scripts/validate_private_gateway_contract.py"],
    "workspace": [sys.executable, "scripts/validate_public_cli_workspace.py"],
    "dual_output": [sys.executable, "scripts/validate_dual_output_flow.py"],
    "spec_patch": [sys.executable, "scripts/validate_spec_patch_flow.py"],
    "cli_history": [sys.executable, "scripts/validate_cli_history.py"],
    "regression_gate": [sys.executable, "scripts/run_regression_gate.py"],
}


def load_manifest() -> dict[str, Any]:
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("MCP adapter manifest must be a JSON object")
    return data


def base_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(BASE_DIR).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def resolve_base_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = (BASE_DIR / path).resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(BASE_DIR)
    except ValueError as exc:
        raise ValueError(f"Path must stay inside workspace: {value}") from exc
    return resolved


def run_command(args: list[str], *, timeout: int = 240) -> dict[str, Any]:
    result = subprocess.run(args, cwd=BASE_DIR, capture_output=True, text=True, check=False, timeout=timeout)
    return {
        "command": ["python" if item == sys.executable else item for item in args],
        "status": "passed" if result.returncode == 0 else "failed",
        "returncode": result.returncode,
        "stdout_head": (result.stdout or "").strip().splitlines()[:12],
        "stderr_head": (result.stderr or "").strip().splitlines()[:12],
    }


def mcp_tools() -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    for tool in load_manifest().get("tools", []):
        tools.append(
            {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": tool["input_schema"],
            }
        )
    return tools


def content_result(payload: dict[str, Any], *, is_error: bool = False) -> dict[str, Any]:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(payload, indent=2, ensure_ascii=False),
            }
        ],
        "isError": is_error,
    }


def call_plan_blueprint(arguments: dict[str, Any]) -> dict[str, Any]:
    input_path = base_relative(resolve_base_path(str(arguments["input_path"])))
    command = [
        sys.executable,
        "scripts/ppt_system.py",
        "blueprint",
        input_path,
        "--kind",
        str(arguments.get("kind", "auto")),
        "--approval-mode",
        str(arguments.get("approval_mode", "assistant")),
    ]
    return run_command(command)


def call_compose_spec(arguments: dict[str, Any]) -> dict[str, Any]:
    intake_path = base_relative(resolve_base_path(str(arguments["intake_path"])))
    command = [sys.executable, "scripts/ppt_system.py", "compose-spec", intake_path]
    if arguments.get("output"):
        command.extend(["--output", base_relative(resolve_base_path(str(arguments["output"])))])
    return run_command(command)


def call_build_outputs(arguments: dict[str, Any]) -> dict[str, Any]:
    spec_path = base_relative(resolve_base_path(str(arguments["spec_path"])))
    command = [sys.executable, "scripts/ppt_system.py", "build-outputs", spec_path]
    if arguments.get("validate", True):
        command.append("--validate")
    return run_command(command, timeout=300)


def call_patch_slide_slot(arguments: dict[str, Any]) -> dict[str, Any]:
    dry_run = bool(arguments.get("dry_run", False))
    output = arguments.get("output")
    if not dry_run and not output and arguments.get("confirm_write") is not True:
        return {
            "status": "rejected",
            "reason": "In-place patch requires confirm_write=true or dry_run=true.",
            "policy_summary": {
                "local_only": True,
                "destructive_confirmation_required": True,
            },
        }
    spec_path = base_relative(resolve_base_path(str(arguments["spec_path"])))
    slot_kind = str(arguments["slot_kind"])
    slot = str(arguments["slot"])
    command = [
        sys.executable,
        "scripts/ppt_system.py",
        "patch-spec",
        spec_path,
        "--slide",
        str(arguments["slide"]),
    ]
    if slot_kind == "text":
        command.extend(["--text-slot", slot, "--value", str(arguments.get("value", ""))])
    elif slot_kind == "image":
        command.extend(["--image-slot", slot, "--value", str(arguments.get("value", ""))])
    elif slot_kind == "chart":
        command.extend(["--chart-slot", slot, "--json", json.dumps(arguments.get("json_payload", {}), ensure_ascii=False)])
    elif slot_kind == "table":
        command.extend(["--table-slot", slot, "--json", json.dumps(arguments.get("json_payload", {}), ensure_ascii=False)])
    else:
        return {"status": "rejected", "reason": f"Unsupported slot_kind: {slot_kind}"}
    if output:
        command.extend(["--output", base_relative(resolve_base_path(str(output)))])
    if dry_run:
        command.append("--dry-run")
    return run_command(command)


def call_validate_outputs(arguments: dict[str, Any]) -> dict[str, Any]:
    scope = str(arguments["scope"])
    if scope == "regression_gate" and arguments.get("confirm_expensive") is not True:
        return {
            "status": "rejected",
            "reason": "Full regression gate requires confirm_expensive=true.",
            "policy_summary": {
                "local_only": True,
                "expensive_confirmation_required": True,
            },
        }
    command = VALIDATOR_COMMANDS.get(scope)
    if not command:
        return {"status": "rejected", "reason": f"Unsupported validation scope: {scope}"}
    return run_command(command, timeout=900 if scope == "regression_gate" else 240)


def call_summarize_project(arguments: dict[str, Any]) -> dict[str, Any]:
    report_path = arguments.get("report_path") or "outputs/reports/dual_output_flow_validation.json"
    path = resolve_base_path(str(report_path))
    if not path.exists():
        return {"status": "missing", "report_path": base_relative(path)}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    summary = data.get("summary", data) if isinstance(data, dict) else {}
    return {
        "status": "passed",
        "report_path": base_relative(path),
        "summary": summary,
    }


TOOL_DISPATCH = {
    "plan_blueprint": call_plan_blueprint,
    "compose_spec": call_compose_spec,
    "build_outputs": call_build_outputs,
    "patch_slide_slot": call_patch_slide_slot,
    "validate_outputs": call_validate_outputs,
    "summarize_project": call_summarize_project,
}


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    handler = TOOL_DISPATCH.get(name)
    if not handler:
        return content_result({"status": "rejected", "reason": f"Unknown tool: {name}"}, is_error=True)
    try:
        payload = handler(arguments)
    except Exception as exc:
        return content_result({"status": "failed", "reason": str(exc)}, is_error=True)
    return content_result(payload, is_error=payload.get("status") in {"failed", "rejected"})


def jsonrpc_response(message_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def jsonrpc_error(message_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": message}}


def handle_jsonrpc(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    message_id = message.get("id")
    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return jsonrpc_response(
            message_id,
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "ppt-public-cli-thin-adapter", "version": "0.1.0"},
            },
        )
    if method == "tools/list":
        return jsonrpc_response(message_id, {"tools": mcp_tools()})
    if method == "tools/call":
        params = message.get("params") or {}
        return jsonrpc_response(message_id, call_tool(str(params.get("name")), params.get("arguments") or {}))
    return jsonrpc_error(message_id, -32601, f"Method not found: {method}")


def serve_stdio() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
            response = handle_jsonrpc(message)
        except Exception as exc:
            response = jsonrpc_error(None, -32603, str(exc))
        if response is not None:
            print(json.dumps(response, ensure_ascii=False), flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Thin MCP adapter spike over the public CLI commands.")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--list-tools", action="store_true")
    parser.add_argument("--call-tool", default=None)
    parser.add_argument("--arguments", default="{}")
    args = parser.parse_args(argv)
    if args.serve:
        return serve_stdio()
    if args.list_tools:
        print(json.dumps({"tools": mcp_tools()}, indent=2, ensure_ascii=False))
        return 0
    if args.call_tool:
        arguments = json.loads(args.arguments)
        if not isinstance(arguments, dict):
            raise ValueError("--arguments must be a JSON object")
        print(json.dumps(call_tool(args.call_tool, arguments), indent=2, ensure_ascii=False))
        return 0
    parser.error("Use --serve, --list-tools, or --call-tool")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
