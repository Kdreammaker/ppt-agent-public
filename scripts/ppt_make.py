from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "1.0"


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def slugify(value: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9가-힣]+", value.casefold())
    slug = "_".join(tokens[:8])
    return slug[:64] or "natural_language_deck"


def resolve_workspace(value: str | None) -> Path:
    if value:
        path = Path(value)
        return path.resolve() if path.is_absolute() else (Path.cwd() / path).resolve()
    default = BASE_DIR.parent / "workspace"
    if default.exists():
        return default.resolve()
    return (BASE_DIR / "outputs" / "ppt_make_workspace").resolve()


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def run_step(label: str, command: list[str], *, env: dict[str, str] | None = None, timeout: int = 360) -> dict[str, Any]:
    merged_env = None
    if env:
        import os

        merged_env = os.environ.copy()
        merged_env.update(env)
    result = subprocess.run(command, cwd=BASE_DIR, env=merged_env, capture_output=True, text=True, check=False, timeout=timeout)
    payload = {
        "label": label,
        "command": ["python" if item == sys.executable else item for item in command],
        "returncode": result.returncode,
        "status": "passed" if result.returncode == 0 else "failed",
        "stdout_tail": result.stdout[-4000:],
        "stderr_tail": result.stderr[-4000:],
    }
    parsed = maybe_json(result.stdout)
    if parsed:
        payload["stdout_json"] = parsed
    return payload


def maybe_json(text: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def detect_slide_count(request: str) -> int:
    match = re.search(r"(\d{1,2})\s*(?:slides?|장|페이지|page)", request, re.IGNORECASE)
    if match:
        return max(1, min(20, int(match.group(1))))
    return 6


def detect_deck_type(request: str) -> str:
    lowered = request.casefold()
    candidates = [
        ("sales", ["sales", "영업", "세일즈"]),
        ("proposal", ["proposal", "제안", "제안서"]),
        ("strategy", ["strategy", "전략"]),
        ("training", ["training", "교육", "훈련"]),
        ("status_update", ["status", "weekly", "진행", "현황"]),
        ("portfolio", ["portfolio", "포트폴리오"]),
        ("analysis", ["analysis", "분석"]),
        ("report", ["report", "briefing", "review", "보고", "리뷰"]),
    ]
    for deck_type, needles in candidates:
        if any(needle in lowered for needle in needles):
            return deck_type
    return "report"


def detect_industry(request: str) -> str:
    lowered = request.casefold()
    candidates = [
        ("technology", ["tech", "software", "ai", "기술", "소프트웨어"]),
        ("finance", ["finance", "financial", "투자", "금융"]),
        ("healthcare", ["health", "medical", "의료", "헬스"]),
        ("travel", ["travel", "tour", "여행"]),
        ("food_and_beverage", ["food", "restaurant", "식품", "음식"]),
        ("entertainment", ["game", "media", "entertainment", "게임", "콘텐츠"]),
        ("exhibition", ["exhibition", "expo", "전시"]),
    ]
    for industry, needles in candidates:
        if any(needle in lowered for needle in needles):
            return industry
    return "business"


def detect_tone(request: str, mode: str) -> list[str]:
    lowered = request.casefold()
    tone = ["executive", "analytical"]
    if any(token in lowered for token in ["sales", "영업", "세일즈"]):
        tone = ["sales", "visual"]
    if any(token in lowered for token in ["technical", "기술"]):
        tone.append("technical")
    if any(token in lowered for token in ["friendly", "친근"]):
        tone.append("friendly")
    if mode == "assistant" and "conservative" not in tone:
        tone.append("conservative")
    return list(dict.fromkeys(tone))[:4]


def split_request_points(request: str) -> list[str]:
    parts = [part.strip(" -•\t\r\n") for part in re.split(r"[;\n。.!?]", request) if part.strip()]
    points = [part for part in parts if len(part) > 6][:5]
    if points:
        return points
    return [request.strip()[:220]]


def build_intake(request: str, *, project_id: str, mode: str) -> dict[str, Any]:
    slide_count = detect_slide_count(request)
    title = request.strip().splitlines()[0].strip()
    title = title[:80] or "Natural Language Deck"
    approval_mode = "assistant" if mode == "assistant" else "operator_review"
    return {
        "$schema": "../../config/deck_intake.schema.json",
        "intake_version": "1.0",
        "name": title,
        "audience": {
            "primary": "Business decision makers",
            "secondary": ["Operators", "Reviewers"],
            "knowledge_level": "informed",
            "decision_role": "decision_maker",
        },
        "presentation_context": {
            "setting": "Natural language PPT request",
            "delivery_mode": "live",
            "duration_minutes": max(8, slide_count * 3),
            "presenter_role": "Presenter",
            "locale": "ko-KR" if re.search(r"[가-힣]", request) else "en-US",
        },
        "primary_goal": request.strip(),
        "deck_type": detect_deck_type(request),
        "industry": detect_industry(request),
        "tone": detect_tone(request, mode),
        "slide_count_range": {"min": slide_count, "max": slide_count},
        "brand_or_template_scope": {
            "preferred_scope": None,
            "preferred_template_keys": [],
            "required_template_library": None,
            "theme_path": (BASE_DIR / "config" / "pptx_theme.neutral_modern.json").as_posix(),
            "notes": "Generated by the public natural-language make wrapper.",
        },
        "content_density": "medium",
        "variation_level": "single_path",
        "review_requirements": {
            "needs_variant_review": False,
            "requires_rationale_report": True,
            "requires_slot_map": True,
            "reviewers": ["operator"],
            "approval_mode": approval_mode,
        },
        "must_include": split_request_points(request),
        "must_avoid": ["Unreviewed private payloads", "Raw private asset paths", "Generic filler"],
        "source_materials": [],
        "output_preferences": {
            "output_spec_path": f"outputs/projects/{project_id}/specs/deck_spec.json",
            "output_deck_path": f"outputs/decks/{project_id}.pptx",
            "required_reports": [
                f"outputs/reports/{project_id}_slide_selection_rationale.json",
                f"outputs/reports/{project_id}_deck_slot_map.json",
            ],
        },
        "notes": "Natural-language request normalized locally; no model call or telemetry was used.",
    }


def connector_status(workspace: Path) -> dict[str, Any]:
    step = run_step(
        "connector_status",
        [sys.executable, "scripts/ppt_private_connector.py", "status", "--workspace", workspace.as_posix()],
        timeout=120,
    )
    return step.get("stdout_json", {}) if step["returncode"] == 0 else {}


def private_ready(status: dict[str, Any], *, execute: bool) -> bool:
    capability = status.get("capability_summary", {}).get("private_template_library_build", {})
    if execute:
        return bool(capability.get("ready_for_execution", False))
    return bool(capability.get("ready_for_request", False))


def command_make(args: argparse.Namespace) -> int:
    request = args.request or " ".join(args.request_parts).strip()
    if not request:
        raise SystemExit("Provide a natural-language request as text or --request-file.")
    if args.request_file:
        request = Path(args.request_file).read_text(encoding="utf-8-sig").strip()
    workspace = resolve_workspace(args.workspace)
    mode = args.mode
    project_id = args.project_id or slugify(request)
    project_root = BASE_DIR / "outputs" / "projects" / project_id
    intake_path = project_root / "intake" / "request.json"
    plan_path = project_root / "plans" / "deck_plan.json"
    spec_path = project_root / "specs" / "deck_spec.json"
    report_path = project_root / "reports" / "ppt_make_report.json"

    intake = build_intake(request, project_id=project_id, mode=mode)
    write_json(intake_path, intake)

    steps: list[dict[str, Any]] = []
    errors: list[str] = []
    steps.append(
        run_step(
            "compose_spec",
            [
                sys.executable,
                "scripts/ppt_system.py",
                "compose-spec",
                intake_path.as_posix(),
                "--operating-mode",
                mode,
                "--plan-output",
                plan_path.as_posix(),
                "--output",
                spec_path.as_posix(),
            ],
        )
    )
    if steps[-1]["returncode"] != 0:
        errors.append("plan-first compose failed")

    status_payload = connector_status(workspace)
    requested_private = args.production == "private"
    use_private = args.production == "private" or (
        args.production == "auto" and private_ready(status_payload, execute=args.execute_private)
    )
    private_step: dict[str, Any] | None = None
    if not errors and use_private:
        private_command = [
            sys.executable,
            "scripts/ppt_private_connector.py",
            "build",
            "--workspace",
            workspace.as_posix(),
            "--spec",
            spec_path.as_posix(),
            "--operating-mode",
            mode,
        ]
        if args.execute_private:
            private_command.append("--execute")
        private_step = run_step("private_production_build", private_command, timeout=args.timeout_seconds)
        steps.append(private_step)
        if private_step["returncode"] != 0:
            errors.append("private production build failed or is not ready")

    if not errors and (args.production == "public" or not use_private):
        if requested_private:
            errors.append("private production was requested but connector is not ready")
        else:
            steps.append(
                run_step(
                    "public_dual_output_build",
                    [
                        sys.executable,
                        "scripts/ppt_system.py",
                        "build-outputs",
                        spec_path.as_posix(),
                        "--validate",
                    ],
                    env={"PPT_AGENT_WORKSPACE": workspace.as_posix()},
                    timeout=args.timeout_seconds,
                )
            )
            if steps[-1]["returncode"] != 0:
                errors.append("public PPTX/HTML build failed")

    spec = read_json(spec_path) if spec_path.exists() else {}
    deck_path = (spec_path.parent / str(spec.get("output_path", ""))).resolve() if spec.get("output_path") else None
    if deck_path and not deck_path.exists():
        deck_path = None
    report = {
        "schema_version": SCHEMA_VERSION,
        "command": "ppt_make",
        "generated_at": utc_now(),
        "status": "built" if not errors else "failed",
        "project_id": project_id,
        "operating_mode": mode,
        "production_mode": args.production,
        "private_attempted": bool(private_step),
        "private_executed": bool(private_step and "--execute" in private_step.get("command", [])),
        "workspace_root": workspace.as_posix(),
        "request_summary": {
            "source": "natural_language",
            "characters": len(request),
            "telemetry_performed": False,
        },
        "artifact_paths": {
            "intake": intake_path.relative_to(BASE_DIR).as_posix(),
            "deck_plan": plan_path.relative_to(BASE_DIR).as_posix(),
            "spec": spec_path.relative_to(BASE_DIR).as_posix(),
            "pptx": deck_path.relative_to(BASE_DIR).as_posix() if deck_path else None,
            "html": f"outputs/html/{project_id}/index.html",
            "report": report_path.relative_to(BASE_DIR).as_posix(),
        },
        "connector_status": {
            "status": status_payload.get("status"),
            "private_request_ready": private_ready(status_payload, execute=False),
            "private_execution_ready": private_ready(status_payload, execute=True),
        },
        "errors": errors,
        "steps": steps,
        "policy_summary": {
            "raw_private_payload_stored": False,
            "tokens_printed": False,
            "natural_language_request_stays_local": True,
            "public_fallback_used": args.production != "private" and not bool(private_step),
        },
    }
    write_json(report_path, report)
    print(json.dumps({k: report[k] for k in ("status", "project_id", "operating_mode", "production_mode", "artifact_paths", "connector_status", "errors")}, indent=2, ensure_ascii=False))
    return 0 if not errors else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Make a PPTX/HTML deck from a natural-language request.")
    parser.add_argument("request_parts", nargs="*", help="Natural-language deck request.")
    parser.add_argument("--request", default=None, help="Natural-language deck request.")
    parser.add_argument("--request-file", default=None, help="Read the natural-language request from a text file.")
    parser.add_argument("--workspace", default=None)
    parser.add_argument("--mode", choices=["auto", "assistant"], default="assistant")
    parser.add_argument("--project-id", default=None)
    parser.add_argument("--production", choices=["auto", "public", "private"], default="auto")
    parser.add_argument("--execute-private", action="store_true", help="Execute the configured private runtime command when production=private/auto is ready.")
    parser.add_argument("--timeout-seconds", type=int, default=600)
    return parser


def main(argv: list[str] | None = None) -> int:
    return command_make(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
