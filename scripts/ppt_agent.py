from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from system.guide_packet import (
    DEFAULT_PROJECTS_DIR,
    build_auto_variants,
    build_from_guide_packet,
    compose_guide_packet_from_intent,
    compose_default_packet_from_prompt,
    export_guide_packet_schema,
    json_dump,
    load_guide_packet,
    load_routed_strategy_pair,
    plan_from_guide_packet,
    safe_rel,
)
from system.strategy_router import run_sparse_request_pipeline


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def command_make(args: argparse.Namespace) -> int:
    guide_path = args.guide_packet or args.guide_bundle
    sparse_artifacts: dict[str, Any] | None = None
    if not guide_path:
        if not args.prompt:
            raise SystemExit("make requires --guide-bundle/--guide-packet or --prompt")
        output_root = Path(args.output_root).resolve()
        intake_id = args.project_id or "sparse-intake"
        project_dir = output_root / intake_id
        guide_dir = project_dir / "intake"
        guide_dir.mkdir(parents=True, exist_ok=True)
        sparse_artifacts = run_sparse_request_pipeline(
            args.prompt,
            project_dir,
            mode=args.mode,
            explicit_sources=args.source or [],
            search_topics=args.search_topic or [],
            project_name=args.project_name,
            explicit_strategy=args.strategy,
        )
        packet = compose_guide_packet_from_intent(
            sparse_artifacts["intent_profile"],
            sparse_artifacts["source_summary"],
            sparse_artifacts["routing_report"],
            request_intake=sparse_artifacts["request_intake"],
            project_name=args.project_name,
        )
        guide_path = guide_dir / "guide-data.public.json"
        json_dump(guide_path, packet)

    if args.mode == "auto":
        strategy_a = "investor_open"
        strategy_b = "operator_dense"
        if sparse_artifacts:
            selected = sparse_artifacts["routing_report"]["selected"]
            strategy_a = selected["variant_a"]["strategy_id"]
            strategy_b = selected["variant_b"]["strategy_id"]
        elif args.routing_report:
            routed_a, routed_b, _ = load_routed_strategy_pair(guide_path, output_root=args.output_root, project_id=args.project_id, routing_report_path=args.routing_report)
            strategy_a = routed_a or strategy_a
            strategy_b = routed_b or strategy_b
        result = build_auto_variants(
            guide_path,
            output_root=args.output_root,
            project_id=args.project_id,
            html_guide_requested=args.html_guide,
            variant_strategy_a=strategy_a,
            variant_strategy_b=strategy_b,
            routing_report_path=args.routing_report,
            approved_package_path=args.approved_package,
        )
    else:
        strategy = "investor_open"
        if sparse_artifacts:
            strategy = sparse_artifacts["routing_report"]["selected"]["variant_a"]["strategy_id"]
        if args.build_approved:
            result = build_from_guide_packet(
                guide_path,
                mode="assistant",
                output_root=args.output_root,
                project_id=args.project_id,
                html_guide_requested=args.html_guide or args.review_guide,
                variant_strategy=strategy,
                approved_package_path=args.approved_package,
            )
        else:
            result = plan_from_guide_packet(
                guide_path,
                mode="assistant",
                output_root=args.output_root,
                project_id=args.project_id,
                html_guide_requested=True,
                variant_strategy=strategy,
                approved_package_path=args.approved_package,
            )
    print_json(result)
    return 0 if result["status"] in {"built", "pass", "waiting_for_approval"} else 1


def command_validate_guide(args: argparse.Namespace) -> int:
    packet, path, _ = load_guide_packet(args.guide)
    print_json(
        {
            "status": "pass",
            "guide_path": safe_rel(path),
            "guide_id": packet.guide_identity.guide_id,
            "slide_count": packet.guide_identity.slide_count,
            "layout_archetypes": sorted({item.id for item in packet.layout_archetypes}),
        }
    )
    return 0


def command_compose_guide(args: argparse.Namespace) -> int:
    output = Path(args.output).resolve()
    if args.intent:
        artifact_dir = output.parent if output.suffix.lower() == ".json" else output
        artifacts = run_sparse_request_pipeline(
            args.prompt,
            artifact_dir,
            mode="assistant",
            explicit_sources=args.source or [],
            search_topics=args.search_topic or [],
            project_name=args.project_name,
            explicit_strategy=args.strategy,
        )
        packet = compose_guide_packet_from_intent(
            artifacts["intent_profile"],
            artifacts["source_summary"],
            artifacts["routing_report"],
            request_intake=artifacts["request_intake"],
            project_name=args.project_name,
        )
    else:
        packet = compose_default_packet_from_prompt(args.prompt, slide_count=args.slide_count, project_name=args.project_name)
    if output.is_dir() or output.suffix.lower() != ".json":
        output = output / "guide-data.public.json"
    json_dump(output, packet)
    print_json({"status": "written", "guide_path": safe_rel(output)})
    return 0


def command_export_schema(args: argparse.Namespace) -> int:
    output = Path(args.output).resolve() if args.output else None
    path = export_guide_packet_schema(output) if output else export_guide_packet_schema()
    print_json({"status": "written", "schema_path": safe_rel(path)})
    return 0


def command_install_host(args: argparse.Namespace) -> int:
    host = args.host
    workspace = Path(args.workspace).resolve()
    install_dir = workspace / ".ppt-agent" / "hosts" / host
    install_dir.mkdir(parents=True, exist_ok=True)
    command = f"python scripts\\ppt_agent.py make --mode assistant --guide-bundle <path-to-guide-bundle>"
    if host == "mcp":
        command = "python scripts\\mcp_adapter.py --serve"
    payload = {
        "host": host,
        "workspace": safe_rel(workspace) if workspace == BASE_DIR else "[selected-workspace]",
        "commands": {
            "assistant_mode": "python scripts\\ppt_agent.py make --mode assistant --guide-bundle <bundle>",
            "assistant_final_build": "python scripts\\ppt_agent.py make --mode assistant --guide-bundle <bundle> --build-approved",
            "auto_mode": "python scripts\\ppt_agent.py make --mode auto --guide-bundle <bundle>",
            "assistant_with_approved_package": "python scripts\\ppt_agent.py make --mode assistant --guide-packet <guide-data.public.json> --approved-package <approved-package-response.json> --build-approved",
            "sparse_assistant": "python scripts\\ppt_agent.py make --mode assistant --prompt \"파일인데 참고해서 만들어줘\" --source <local-source>",
            "sparse_auto": "python scripts\\ppt_agent.py make --mode auto --prompt \"ㅇㅇ 내용 찾아서 만들어줘\" --search-topic <topic>",
            "mcp": "python scripts\\mcp_adapter.py --serve",
        },
        "machine_artifacts": [
            "request-intake.json",
            "source-summary.json",
            "intent-profile.json",
            "routing-report.json",
            "guide-data.public.json",
            "deck-plan.json",
            "renderer-contract.json",
        ],
        "public_safe": True,
        "private_material_excluded": [
            "tokens",
            "private prompts",
            "raw payloads",
            "Drive IDs",
            "raw source attachment paths",
        ],
    }
    json_dump(install_dir / "connection.json", payload)
    (install_dir / "README.md").write_text(
        f"# PPT Agent Host Setup: {host}\n\n"
        f"Default command:\n\n```powershell\n{command}\n```\n\n"
        "Use `--mode assistant` for planning first, add `--build-approved` after review, or use `--mode auto` for two variants.\n"
        "Sparse prompts create request-intake, source-summary, intent-profile, and routing-report artifacts before guide packet composition.\n",
        encoding="utf-8",
    )
    print_json({"status": "installed", "host": host, "path": safe_rel(install_dir)})
    return 0


def command_doctor(_: argparse.Namespace) -> int:
    status = {
        "status": "ready",
        "workspace": safe_rel(BASE_DIR),
        "guide_schema_exists": (BASE_DIR / "config" / "ppt-maker-design-guide-packet.schema.json").exists(),
        "default_projects_dir": safe_rel(DEFAULT_PROJECTS_DIR),
    }
    print_json(status)
    return 0 if status["guide_schema_exists"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Public-safe PPT guide packet agent.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    make = subparsers.add_parser("make", help="Build from a guide packet or sparse prompt.")
    make.add_argument("--guide-bundle")
    make.add_argument("--guide-packet")
    make.add_argument("--prompt")
    make.add_argument("--project-name")
    make.add_argument("--source", action="append", help="Optional local source path or source reference for sparse prompt intake.")
    make.add_argument("--search-topic", action="append", help="Optional search topic to record without fetching by default.")
    make.add_argument("--strategy", help="Optional approved strategy id or alias to prefer during routing.")
    make.add_argument("--routing-report", help="Optional routing-report.json to consume when building Auto variants from an existing guide packet.")
    make.add_argument("--approved-package", help="Optional approved package response JSON. Assets are checksum/size validated before insertion.")
    make.add_argument("--mode", choices=["assistant", "auto"], default="assistant")
    make.add_argument("--output-root", default=str(DEFAULT_PROJECTS_DIR))
    make.add_argument("--project-id")
    make.add_argument("--html-guide", action="store_true")
    make.add_argument("--review-guide", action="store_true")
    make.add_argument(
        "--build-approved",
        "--continue-build",
        action="store_true",
        help="Render final Assistant PPTX after the planning checkpoint has been reviewed.",
    )
    make.set_defaults(func=command_make)

    validate = subparsers.add_parser("validate-guide")
    validate.add_argument("guide")
    validate.set_defaults(func=command_validate_guide)

    compose = subparsers.add_parser("compose-guide")
    compose.add_argument("--prompt", required=True)
    compose.add_argument("--project-name")
    compose.add_argument("--slide-count", type=int, default=5)
    compose.add_argument("--output", required=True)
    compose.add_argument("--intent", action="store_true", help="Compose through request intake, intent profile, and strategy routing.")
    compose.add_argument("--source", action="append")
    compose.add_argument("--search-topic", action="append")
    compose.add_argument("--strategy")
    compose.set_defaults(func=command_compose_guide)

    schema = subparsers.add_parser("export-guide-schema")
    schema.add_argument("--output")
    schema.set_defaults(func=command_export_schema)

    install = subparsers.add_parser("install-host")
    install.add_argument("host", choices=["codex", "antigravity", "claude-code", "mcp"])
    install.add_argument("--workspace", default=str(BASE_DIR))
    install.set_defaults(func=command_install_host)

    doctor = subparsers.add_parser("doctor")
    doctor.set_defaults(func=command_doctor)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
