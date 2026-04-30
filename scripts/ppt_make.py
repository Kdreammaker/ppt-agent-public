from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import urllib.request
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


def display_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (Path.cwd() / path).resolve()


def existing_path(path: Path | None) -> str | None:
    return path.resolve().as_posix() if path and path.exists() else None


def read_text_limited(path: Path, limit: int = 8000) -> str:
    data = path.read_text(encoding="utf-8-sig", errors="replace")
    return " ".join(data[:limit].split())


def fetch_url_summary(url: str, limit: int = 8000) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "ppt-agent-public/1.0"})
    with urllib.request.urlopen(req, timeout=15) as response:
        content_type = response.headers.get("content-type", "")
        raw = response.read(limit)
    text = raw.decode("utf-8", errors="replace")
    return {
        "source_type": "url",
        "url": url,
        "content_type": content_type,
        "excerpt": " ".join(text.split())[:3000],
        "stored_full_content": False,
    }


def collect_external_context(args: argparse.Namespace, project_root: Path) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for value in args.source_file:
        path = Path(value)
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        if path.exists() and path.is_file():
            items.append(
                {
                    "source_type": "file",
                    "path_ref": path.name,
                    "excerpt": read_text_limited(path),
                    "stored_full_content": False,
                }
            )
    for url in args.source_url:
        try:
            items.append(fetch_url_summary(url))
        except Exception as exc:  # noqa: BLE001 - source availability is nonblocking context.
            items.append({"source_type": "url", "url": url, "error": str(exc), "stored_full_content": False})
    payload = {
        "schema_version": SCHEMA_VERSION,
        "items": items,
        "policy_summary": {
            "full_source_content_stored": False,
            "tokens_printed": False,
            "used_for_local_plan_only": True,
        },
    }
    if items:
        write_json(project_root / "context" / "source_context.json", payload)
    return payload


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


def extract_korean_topic_list(request: str) -> list[str]:
    topics: list[str] = []
    for match in re.finditer(r"(?:다음|아래|목록|항목)[^:：\n]{0,80}[:：]\s*([^。.\n]+)", request):
        raw = match.group(1)
        for item in re.split(r"\s*(?:,|，|、|ㆍ|·|/| 및 | 그리고 )\s*", raw):
            cleaned = re.sub(r"\s+", " ", item).strip(" \t\r\n-•,.;:：")
            cleaned = re.sub(r"^(?:각\s*)?슬라이드(?:에|마다)?\s*", "", cleaned)
            if cleaned and len(cleaned) <= 32 and re.search(r"[가-힣A-Za-z0-9]", cleaned):
                topics.append(cleaned)
    unique: list[str] = []
    for topic in topics:
        if topic not in unique:
            unique.append(topic)
    return unique[:20]


def extract_common_item_detail(request: str) -> str | None:
    match = re.search(r"각\s*(?:음식|항목|주제)의?\s*([^。.\n]{2,90}?)(?:을|를)?\s*(?:간단히\s*)?포함", request)
    if not match:
        return None
    detail = re.sub(r"\s+", " ", match.group(1)).strip(" ,.;:：")
    return detail or None


def strip_korean_slide_meta(value: str) -> str:
    text = re.sub(r"\s+", " ", value).strip(" \t\r\n-•,.;:：")
    text = re.sub(r"^\d{1,2}\s*번\s*슬라이드(?:는|은)?\s*", "", text)
    text = re.sub(r"^\d{1,2}\s*번\s*부터\s*\d{1,2}\s*번\s*까지(?:는|은)?\s*", "", text)
    text = re.sub(r"^(?:각\s*)?슬라이드(?:에|마다)?\s*", "", text)
    text = re.sub(
        r"\s*(?:으로|로)?\s*슬라이드\s*총?\s*\d{1,2}\s*(?:장|쪽|페이지|슬라이드)?\s*(?:구성|작성|제작)?\s*$",
        "",
        text,
    )
    text = re.sub(r"\s+(?:으로|로)$", "", text)
    return text.strip(" \t\r\n-•,.;:：")


def is_structural_slide_instruction(value: str) -> bool:
    text = re.sub(r"\s+", " ", value).strip()
    return bool(
        re.fullmatch(r"\d{1,2}\s*번\s*슬라이드(?:는|은)?\s*(?:표지|커버|목차|구성)\s*\.?", text)
        or re.fullmatch(r"슬라이드\s*총?\s*\d{1,2}\s*(?:장|쪽|페이지|슬라이드)?\s*(?:구성|작성|제작)?\s*\.?", text)
    )


def derive_request_title(request: str) -> str:
    first_sentence = re.split(r"[。.!?\n]", request.strip(), maxsplit=1)[0]
    title = strip_korean_slide_meta(first_sentence)
    if re.search(r"[가-힣]", request) and title:
        return title[:80]
    title = re.sub(r"\b(?:create|make|generate|build)\b", " ", first_sentence, flags=re.IGNORECASE)
    title = re.sub(r"\b\d{1,2}\s*(?:slides?|pages?)\b", " ", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+", " ", title).strip(" \t\r\n-•,.;:")
    return (title or "Natural Language Deck")[:80]


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
    topics = extract_korean_topic_list(request)
    if topics:
        detail = extract_common_item_detail(request)
        return [f"{topic}: {detail}" if detail else topic for topic in topics][:18]
    parts = [part.strip(" -•\t\r\n") for part in re.split(r"[;\n。.!?]", request) if part.strip()]
    points = []
    for part in parts:
        if is_structural_slide_instruction(part):
            continue
        cleaned = strip_korean_slide_meta(part)
        if cleaned and len(cleaned) > 6:
            points.append(cleaned)
    points = points[:5]
    if points:
        return points
    return [request.strip()[:220]]


def context_points(context: dict[str, Any]) -> list[str]:
    points: list[str] = []
    for item in context.get("items", []):
        if not isinstance(item, dict):
            continue
        excerpt = str(item.get("excerpt") or "").strip()
        if excerpt:
            points.append(excerpt[:220])
    return points[:4]


def build_intake(request: str, *, project_id: str, mode: str, context: dict[str, Any]) -> dict[str, Any]:
    slide_count = detect_slide_count(request)
    title = derive_request_title(request)
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
        "must_include": split_request_points(request) + context_points(context),
        "must_avoid": ["Unreviewed private payloads", "Raw private asset paths", "Generic filler"],
        "source_materials": [],
        "output_preferences": {},
        "notes": "Natural-language request normalized locally; external source excerpts are stored as bounded context only; no telemetry was used.",
    }


def write_design_brief(path: Path, request: str, plan: dict[str, Any], spec: dict[str, Any], context: dict[str, Any], version_report: dict[str, Any] | None) -> None:
    style = plan.get("brand_style_intent", {}) if isinstance(plan.get("brand_style_intent"), dict) else {}
    lines = [
        f"# Draft Design Brief: {plan.get('request_id', spec.get('project_id', 'deck'))}",
        "",
        "## Request",
        request.strip(),
        "",
        "## Version And Channel",
    ]
    if version_report:
        summary = version_report.get("summary", {})
        lines.append(f"- update available: `{summary.get('update_available', [])}`")
        lines.append(f"- remote unreachable: `{summary.get('remote_unreachable', [])}`")
        lines.append(f"- dirty repos: `{summary.get('dirty', [])}`")
    else:
        lines.append("- version check: not run")
    lines.extend(
        [
            "",
            "## External Context",
            f"- bounded sources: `{len(context.get('items', []))}`",
            "- full source content stored: `false`",
            "",
            "## Table Of Contents",
        ]
    )
    for index, title in enumerate(plan.get("toc", []), start=1):
        lines.append(f"{index}. {title}")
    lines.extend(["", "## Slide Layout And Content Plan"])
    for slide in plan.get("slide_plans", []):
        lines.extend(
            [
                f"### Slide {slide.get('slide_number')}: {slide.get('working_title')}",
                f"- layout: `{slide.get('layout_intent')}`",
                f"- message: {slide.get('message')}",
                f"- visual: {slide.get('visual_intent')}",
                f"- max title chars: `{slide.get('content_budget', {}).get('max_title_chars')}`",
                f"- max body points: `{slide.get('content_budget', {}).get('max_body_points')}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Style Decisions",
            f"- tone: `{style.get('tone', spec.get('mode_policy'))}`",
            f"- theme: `{spec.get('theme_path')}`",
            f"- template recipe: `{spec.get('recipe')}`",
            "- font policy: editable Office text; private runtime may apply installed brand fonts when available",
            "- color policy: theme-driven palette, no raw private style payload in public report",
            "",
            "## Reverse-Engineering Boundary",
            "- public brief contains only plan IDs, layout intent, safe style refs, and bounded source excerpts",
            "- private prompt text, ranking details, raw template binaries, raw asset payloads, and work logs are not written here",
            "- connector reports omit private stdout/stderr and raw private payloads",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


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
    project_base = resolve_path(args.output_root) if args.output_root else workspace / "outputs" / "projects"
    project_root = project_base / project_id
    intake_path = project_root / "intake" / "request.json"
    plan_path = project_root / "plans" / "deck_plan.json"
    spec_path = project_root / "specs" / "deck_spec.json"
    report_path = project_root / "reports" / "ppt_make_report.json"
    design_brief_path = project_root / "plans" / "draft_design_brief.md"
    version_report_path = project_root / "reports" / "version_check.json"
    deck_output_path = workspace / "outputs" / "decks" / f"{project_id}.pptx"
    html_output_path = workspace / "outputs" / "html" / project_id / "index.html"
    build_report_dir = workspace / "outputs" / "reports"

    context = collect_external_context(args, project_root)
    intake = build_intake(request, project_id=project_id, mode=mode, context=context)
    intake["output_preferences"] = {
        "output_spec_path": spec_path.as_posix(),
        "output_deck_path": deck_output_path.as_posix(),
        "required_reports": [
            (build_report_dir / f"{project_id}_slide_selection_rationale.json").as_posix(),
            (build_report_dir / f"{project_id}_deck_slot_map.json").as_posix(),
        ],
    }
    write_json(intake_path, intake)

    steps: list[dict[str, Any]] = []
    errors: list[str] = []
    version_report: dict[str, Any] | None = None
    if not args.skip_version_check:
        version_command = [
            sys.executable,
            "scripts/ppt_version_check.py",
            "--workspace",
            workspace.as_posix(),
            "--report",
            version_report_path.as_posix(),
        ]
        if args.skip_remote_version_check:
            version_command.append("--skip-remote")
        if args.require_latest:
            version_command.append("--require-latest")
        version_step = run_step("version_check", version_command, timeout=90)
        steps.append(version_step)
        if version_report_path.exists():
            version_report = read_json(version_report_path)
        if version_step["returncode"] != 0:
            errors.append("version check blocked execution")
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
                "--report-dir",
                build_report_dir.as_posix(),
            ],
        )
    )
    if steps[-1]["returncode"] != 0:
        errors.append("plan-first compose failed")

    spec = read_json(spec_path) if spec_path.exists() else {}
    plan = read_json(plan_path) if plan_path.exists() else {}
    if plan and spec:
        write_design_brief(design_brief_path, request, plan, spec, context, version_report)

    assistant_waiting = mode == "assistant" and not args.build_approved and not errors
    status_payload = connector_status(workspace)
    requested_private = args.production == "private"
    use_private = (not assistant_waiting) and (
        args.production == "private" or (args.production == "auto" and private_ready(status_payload, execute=args.execute_private))
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

    if not errors and not assistant_waiting and (args.production == "public" or not use_private):
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
                        "--report-dir",
                        build_report_dir.as_posix(),
                        "--html-output",
                        html_output_path.as_posix(),
                    ],
                    env={"PPT_AGENT_WORKSPACE": workspace.as_posix()},
                    timeout=args.timeout_seconds,
                )
            )
            if steps[-1]["returncode"] != 0:
                errors.append("public PPTX/HTML build failed")
    deck_path = (spec_path.parent / str(spec.get("output_path", ""))).resolve() if spec.get("output_path") else None
    if deck_path and not deck_path.exists():
        deck_path = None
    status = "waiting_for_approval" if assistant_waiting else ("built" if not errors else "failed")
    report = {
        "schema_version": SCHEMA_VERSION,
        "command": "ppt_make",
        "generated_at": utc_now(),
        "status": status,
        "project_id": project_id,
        "operating_mode": mode,
        "production_mode": args.production,
        "approval_required": assistant_waiting,
        "build_approved": bool(args.build_approved),
        "next_action": "review_planning_artifacts_then_rerun_with_build_approved" if assistant_waiting else None,
        "private_attempted": bool(private_step),
        "private_executed": bool(private_step and "--execute" in private_step.get("command", [])),
        "workspace_root": workspace.as_posix(),
        "request_summary": {
            "source": "natural_language",
            "characters": len(request),
            "telemetry_performed": False,
        },
        "artifact_paths": {
            "intake": display_path(intake_path, workspace),
            "deck_plan": display_path(plan_path, workspace),
            "draft_design_brief": display_path(design_brief_path, workspace) if design_brief_path.exists() else None,
            "source_context": display_path(project_root / "context" / "source_context.json", workspace) if context.get("items") else None,
            "version_check": display_path(version_report_path, workspace) if version_report_path.exists() else None,
            "renderer_contract": None,
            "spec": display_path(spec_path, workspace),
            "pptx": display_path(deck_path, workspace) if deck_path else None,
            "html": display_path(html_output_path, workspace) if html_output_path.exists() else None,
            "report": display_path(report_path, workspace),
        },
        "artifacts": {
            "intake": existing_path(intake_path),
            "deck_plan": existing_path(plan_path),
            "draft_design_brief": existing_path(design_brief_path),
            "source_context": existing_path(project_root / "context" / "source_context.json") if context.get("items") else None,
            "version_check": existing_path(version_report_path),
            "renderer_contract": None,
            "spec": existing_path(spec_path),
            "pptx": existing_path(deck_path),
            "html": existing_path(html_output_path),
            "report": report_path.resolve().as_posix(),
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
    print(json.dumps({k: report[k] for k in ("status", "project_id", "operating_mode", "production_mode", "approval_required", "next_action", "artifact_paths", "artifacts", "connector_status", "errors")}, indent=2, ensure_ascii=False))
    return 0 if not errors else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Make a PPTX/HTML deck from a natural-language request.")
    parser.add_argument("request_parts", nargs="*", help="Natural-language deck request.")
    parser.add_argument("--request", default=None, help="Natural-language deck request.")
    parser.add_argument("--request-file", default=None, help="Read the natural-language request from a text file.")
    parser.add_argument("--workspace", default=None)
    parser.add_argument("--output-root", default=None, help="Optional project output root; defaults to <workspace>/outputs/projects.")
    parser.add_argument("--mode", choices=["auto", "assistant"], default="assistant")
    parser.add_argument("--project-id", default=None)
    parser.add_argument("--production", choices=["auto", "public", "private"], default="auto")
    parser.add_argument("--source-file", action="append", default=[], help="Use a local text/markdown/json source as bounded context for the draft plan.")
    parser.add_argument("--source-url", action="append", default=[], help="Fetch a URL excerpt as bounded context for the draft plan.")
    parser.add_argument("--skip-version-check", action="store_true")
    parser.add_argument("--skip-remote-version-check", action="store_true")
    parser.add_argument("--require-latest", action="store_true")
    parser.add_argument(
        "--build-approved",
        "--continue-build",
        action="store_true",
        help="Render final Assistant PPTX/HTML after reviewing the planning checkpoint.",
    )
    parser.add_argument("--execute-private", action="store_true", help="Execute the configured private runtime command when production=private/auto is ready.")
    parser.add_argument("--timeout-seconds", type=int, default=600)
    return parser


def main(argv: list[str] | None = None) -> int:
    return command_make(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
