from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from system.guide_packet import build_auto_variants, build_from_guide_packet, compose_guide_packet_from_intent, json_dump, load_guide_packet, plan_from_guide_packet, safe_rel
from system.strategy_router import run_sparse_request_pipeline


TOOLS: list[dict[str, Any]] = [
    {
        "name": "mode_choice",
        "description": "Explain Assistant mode and Auto mode selection without reading private files.",
        "input_schema": {"type": "object", "properties": {"interactive": {"type": "boolean"}}},
    },
    {
        "name": "guide_packet_intake",
        "description": "Validate guide-data.public.json and return a structured public-safe summary.",
        "input_schema": {"type": "object", "required": ["guide_path"], "properties": {"guide_path": {"type": "string"}}},
    },
    {
        "name": "sparse_request_intake",
        "description": "Create public-safe request-intake.json, source-summary.json, intent-profile.json, and routing-report.json from a sparse request.",
        "input_schema": {
            "type": "object",
            "required": ["prompt", "project_id"],
            "properties": {
                "prompt": {"type": "string"},
                "project_id": {"type": "string"},
                "mode": {"type": "string", "enum": ["assistant", "auto"]},
                "output_root": {"type": "string"},
                "source": {"type": "array", "items": {"type": "string"}},
                "search_topic": {"type": "array", "items": {"type": "string"}}
            },
        },
    },
    {
        "name": "intent_strategy_compose",
        "description": "Run sparse intake, bounded intent classification, registry strategy routing, and write a schema-valid guide-data.public.json.",
        "input_schema": {
            "type": "object",
            "required": ["prompt", "project_id"],
            "properties": {
                "prompt": {"type": "string"},
                "project_id": {"type": "string"},
                "mode": {"type": "string", "enum": ["assistant", "auto"]},
                "output_root": {"type": "string"},
                "project_name": {"type": "string"}
            },
        },
    },
    {
        "name": "deck_plan_compose",
        "description": "Build Assistant-mode planning artifacts by default; final PPTX requires build_approved=true.",
        "input_schema": {
            "type": "object",
            "required": ["guide_path"],
            "properties": {
                "guide_path": {"type": "string"},
                "project_id": {"type": "string"},
                "output_root": {"type": "string"},
                "build_approved": {"type": "boolean"},
            },
        },
    },
    {
        "name": "two_variant_auto_build",
        "description": "Build two distinct Auto-mode PPTX variants plus comparison and recommendation reports.",
        "input_schema": {
            "type": "object",
            "required": ["guide_path"],
            "properties": {
                "guide_path": {"type": "string"},
                "routing_report_path": {"type": "string"},
                "project_id": {"type": "string"},
                "output_root": {"type": "string"},
            },
        },
    },
    {
        "name": "qa_validation",
        "description": "Return final QA artifact paths and status for a local project directory.",
        "input_schema": {"type": "object", "required": ["project_dir"], "properties": {"project_dir": {"type": "string"}}},
    },
    {
        "name": "project_summary",
        "description": "Return public-safe artifact paths for a generated project.",
        "input_schema": {"type": "object", "required": ["project_dir"], "properties": {"project_dir": {"type": "string"}}},
    },
]


def response(payload: Any, request_id: Any = None) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": payload}


def error(message: str, request_id: Any = None) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": message}}


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "mode_choice":
        return {
            "assistant": "Plan first, generate machine artifacts, optionally create HTML guide evidence, then build.",
            "auto": "Build two distinct PPTX variants, comparison report, recommendation, and QA without approval checkpoints.",
            "default": "assistant",
        }
    if name == "guide_packet_intake":
        packet, path, _ = load_guide_packet(arguments["guide_path"])
        return {
            "status": "pass",
            "guide_path": safe_rel(path),
            "project_name": packet.guide_identity.project_name,
            "slide_count": packet.guide_identity.slide_count,
            "layout_archetypes": sorted({item.id for item in packet.layout_archetypes}),
        }
    if name in {"sparse_request_intake", "intent_strategy_compose"}:
        output_root = Path(arguments.get("output_root", BASE_DIR / "outputs" / "projects")).resolve()
        project_dir = output_root / arguments["project_id"]
        artifacts = run_sparse_request_pipeline(
            arguments["prompt"],
            project_dir,
            mode=arguments.get("mode", "assistant"),
            explicit_sources=arguments.get("source", []),
            search_topics=arguments.get("search_topic", []),
            project_name=arguments.get("project_name"),
        )
        result = {
            "status": "written",
            "project_dir": safe_rel(project_dir),
            "artifacts": {
                "request_intake": safe_rel(project_dir / "request-intake.json"),
                "source_summary": safe_rel(project_dir / "source-summary.json"),
                "intent_profile": safe_rel(project_dir / "intent-profile.json"),
                "routing_report": safe_rel(project_dir / "routing-report.json"),
            },
            "selected_strategy_pair": {
                "variant_a": artifacts["routing_report"]["selected"]["variant_a"]["strategy_id"],
                "variant_b": artifacts["routing_report"]["selected"]["variant_b"]["strategy_id"],
            },
        }
        if name == "intent_strategy_compose":
            packet = compose_guide_packet_from_intent(
                artifacts["intent_profile"],
                artifacts["source_summary"],
                artifacts["routing_report"],
                request_intake=artifacts["request_intake"],
                project_name=arguments.get("project_name"),
            )
            guide_path = project_dir / "intake" / "guide-data.public.json"
            json_dump(guide_path, packet)
            result["artifacts"]["guide_packet"] = safe_rel(guide_path)
        return result
    if name == "deck_plan_compose":
        if arguments.get("build_approved") is True:
            return build_from_guide_packet(
                arguments["guide_path"],
                mode="assistant",
                output_root=arguments.get("output_root", BASE_DIR / "outputs" / "projects"),
                project_id=arguments.get("project_id"),
                html_guide_requested=True,
            )
        return plan_from_guide_packet(
            arguments["guide_path"],
            mode="assistant",
            output_root=arguments.get("output_root", BASE_DIR / "outputs" / "projects"),
            project_id=arguments.get("project_id"),
            html_guide_requested=True,
        )
    if name == "two_variant_auto_build":
        return build_auto_variants(
            arguments["guide_path"],
            output_root=arguments.get("output_root", BASE_DIR / "outputs" / "projects"),
            project_id=arguments.get("project_id"),
            routing_report_path=arguments.get("routing_report_path"),
        )
    if name in {"qa_validation", "project_summary"}:
        project_dir = Path(arguments["project_dir"]).resolve()
        if not project_dir.exists():
            raise FileNotFoundError(safe_rel(project_dir))
        files = [
            "generated.pptx",
            "deck-plan.json",
            "renderer-contract.json",
            "guide-compliance-report.json",
            "final-qa.json",
            "used-assets-report.json",
            "html-guide-render-report.json",
            "variant-comparison-report.json",
            "auto-mode-recommendation.md",
        ]
        existing = {name: safe_rel(project_dir / name) for name in files if (project_dir / name).exists()}
        qa_path = project_dir / "final-qa.json"
        qa_status = None
        if qa_path.exists():
            qa_status = json.loads(qa_path.read_text(encoding="utf-8")).get("status")
        return {"status": qa_status or "available", "project_dir": safe_rel(project_dir), "artifacts": existing}
    raise ValueError(f"Unknown tool: {name}")


def handle(message: dict[str, Any]) -> dict[str, Any]:
    method = message.get("method")
    request_id = message.get("id")
    try:
        if method == "tools/list":
            return response({"tools": TOOLS}, request_id)
        if method == "tools/call":
            params = message.get("params", {})
            result = call_tool(params["name"], params.get("arguments", {}))
            return response({"content": [{"type": "json", "json": result}]}, request_id)
        return error(f"Unsupported method: {method}", request_id)
    except Exception as exc:
        return error(str(exc), request_id)


def serve() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
            print(json.dumps(handle(message), ensure_ascii=False), flush=True)
        except Exception as exc:
            print(json.dumps(error(str(exc)), ensure_ascii=False), flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generic public-safe MCP adapter for the PPT agent.")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--list-tools", action="store_true")
    args = parser.parse_args(argv)
    if args.list_tools:
        print(json.dumps({"tools": TOOLS}, indent=2, ensure_ascii=False))
        return 0
    if args.serve:
        return serve()
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
