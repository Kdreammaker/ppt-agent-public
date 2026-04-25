from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
REPORTS_DIR = BASE_DIR / "outputs" / "reports"
DEFAULT_DECKS = [
    "outputs/decks/jb_meeting_component_preset_system.pptx",
    "outputs/decks/jb_meeting_design_elevated_system.pptx",
    "outputs/decks/jb_meeting_component_modular_system.pptx",
    "outputs/decks/jb_meeting_internal_share_deck_system.pptx",
    "outputs/decks/jb_meeting_blueprint_system.pptx",
    "outputs/decks/portfolio_auto_selection_sample.pptx",
    "outputs/decks/report_auto_selection_sample.pptx",
    "outputs/decks/sales_auto_selection_sample.pptx",
    "outputs/decks/template_slide_sample_system.pptx",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def report_path(deck_path: Path, suffix: str) -> Path:
    return REPORTS_DIR / f"{deck_path.stem}_{suffix}.json"


def selected_candidate(slide: dict[str, Any]) -> dict[str, Any]:
    selected_key = slide.get("selected_template_key")
    for candidate in slide.get("candidate_templates", []):
        if candidate.get("template_key") == selected_key:
            return candidate
    return slide.get("candidate_templates", [{}])[0] if slide.get("candidate_templates") else {}


def add_issue(
    issues: list[dict[str, Any]],
    *,
    deck: Path,
    slide_number: int | None,
    template_key: str | None,
    severity: str,
    issue_type: str,
    message: str,
    code: str | None = None,
    slides: list[int] | None = None,
) -> None:
    issues.append(
        {
            "deck": deck.as_posix(),
            "slide_number": slide_number,
            "template_key": template_key,
            "severity": severity,
            "type": issue_type,
            "code": code or issue_type,
            "message": message,
            **({"slides": slides} if slides else {}),
        }
    )


def slide_structure_key(slide: dict[str, Any]) -> str | None:
    candidate = selected_candidate(slide)
    return (
        candidate.get("structure")
        or candidate.get("variant")
        or slide.get("selected_variant")
        or slide.get("template_key")
        or slide.get("layout")
    )


def inspect_repetition(deck: Path, rationale: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    run_structure = None
    run_start = 1
    run_length = 0
    previous_template = None
    for slide in rationale.get("slides", []):
        structure = slide_structure_key(slide)
        slide_number = int(slide.get("slide_number", 0))
        if structure == run_structure:
            run_length += 1
        else:
            if run_length >= 3:
                slides = list(range(run_start, run_start + run_length))
                add_issue(
                    issues,
                    deck=deck,
                    slide_number=run_start,
                    template_key=previous_template,
                    severity="warning",
                    issue_type="layout_monotony",
                    code="layout_monotony",
                    message=(
                        f"Slides {run_start}-{run_start + run_length - 1} use the same "
                        f"'{run_structure}' layout structure consecutively; consider inserting "
                        "a breather or alternate layout."
                    ),
                    slides=slides,
                )
            run_structure = structure
            run_start = slide_number
            run_length = 1
        previous_template = slide.get("selected_template_key")
    if run_length >= 3:
        slides = list(range(run_start, run_start + run_length))
        add_issue(
            issues,
            deck=deck,
            slide_number=run_start,
            template_key=previous_template,
            severity="warning",
            issue_type="layout_monotony",
            code="layout_monotony",
            message=(
                f"Slides {run_start}-{run_start + run_length - 1} use the same "
                f"'{run_structure}' layout structure consecutively; consider inserting "
                "a breather or alternate layout."
            ),
            slides=slides,
        )


def inspect_selection_fit(deck: Path, rationale: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    for slide in rationale.get("slides", []):
        matches = slide.get("selection_factors", {}).get("selected_matches", {})
        scope_match = matches.get("scope_match")
        if scope_match == "other_scope":
            add_issue(
                issues,
                deck=deck,
                slide_number=slide.get("slide_number"),
                template_key=slide.get("selected_template_key"),
                severity="warning",
                issue_type="scope_mismatch",
                message="Selected template scope does not match the requested scope or generic fallback.",
            )
        candidate = selected_candidate(slide)
        if candidate.get("usage_policy") != "production_ready":
            add_issue(
                issues,
                deck=deck,
                slide_number=slide.get("slide_number"),
                template_key=slide.get("selected_template_key"),
                severity="info",
                issue_type="template_needs_operator_review",
                message=f"Usage policy is '{candidate.get('usage_policy')}', so the slide should receive operator review.",
            )


def inspect_slots(deck: Path, slot_map: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    title_values = {}
    footer_seen = set()
    for slot in slot_map.get("slots", []):
        slide_number = slot.get("slide_number")
        slot_name = slot.get("slot_name")
        value = slot.get("current_value")
        if slot_name == "title":
            title_values[slide_number] = value
            if not value:
                add_issue(
                    issues,
                    deck=deck,
                    slide_number=slide_number,
                    template_key=slot.get("template_key"),
                    severity="warning",
                    issue_type="missing_title",
                    message="Editable title slot is empty.",
                )
            elif str(value).strip().lower() in {"title", "closing", "agenda"}:
                add_issue(
                    issues,
                    deck=deck,
                    slide_number=slide_number,
                    template_key=slot.get("template_key"),
                    severity="info",
                    issue_type="generic_title",
                    message=f"Title is generic: {value!r}.",
                )
        if slot_name == "footer_note":
            footer_seen.add(slide_number)
        budget = slot.get("budget")
        if slot.get("slot_kind") == "text" and budget and value:
            ratio = len(str(value)) / max(int(budget), 1)
            if ratio >= 0.9:
                add_issue(
                    issues,
                    deck=deck,
                    slide_number=slide_number,
                    template_key=slot.get("template_key"),
                    severity="info",
                    issue_type="text_near_budget",
                    message=f"Slot '{slot_name}' uses {ratio:.0%} of its text budget.",
                )

    slide_numbers = {slot.get("slide_number") for slot in slot_map.get("slots", [])}
    for slide_number in sorted(slide_numbers - footer_seen):
        add_issue(
            issues,
            deck=deck,
            slide_number=slide_number,
            template_key=None,
            severity="info",
            issue_type="footer_slot_absent",
            message="No editable footer_note slot is exposed for this slide.",
        )


def inspect_overflow(deck: Path, overflow: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    events = overflow.get("events", [])
    if len(events) >= 3:
        add_issue(
            issues,
            deck=deck,
            slide_number=None,
            template_key=None,
            severity="warning",
            issue_type="excessive_text_cutoff",
            message=f"{len(events)} text overflow events were recorded for this deck.",
        )
    for event in events:
        if event.get("resolution") == "deterministic_cutoff":
            add_issue(
                issues,
                deck=deck,
                slide_number=None,
                template_key=event.get("template_key"),
                severity="info",
                issue_type="deterministic_cutoff",
                message=f"Slot '{event.get('slot')}' was cut to fit budget {event.get('budget')}.",
            )


def inspect_deck(deck: Path) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    rationale = load_json(report_path(deck, "slide_selection_rationale"))
    slot_map = load_json(report_path(deck, "deck_slot_map"))
    overflow = load_json(report_path(deck, "text_overflow"))
    inspect_repetition(deck, rationale, issues)
    inspect_selection_fit(deck, rationale, issues)
    inspect_slots(deck, slot_map, issues)
    inspect_overflow(deck, overflow, issues)
    return issues


def markdown_for_payload(payload: dict[str, Any]) -> str:
    lines = [
        "# Deck Design Review",
        "",
        f"- Decks reviewed: {payload['summary']['decks']}",
        f"- Issues: {payload['summary']['issues']}",
        f"- Warnings: {payload['summary']['warnings']}",
        f"- Info: {payload['summary']['info']}",
        "",
    ]
    if payload["issues"]:
        lines.extend(
            [
                "| Severity | Deck | Slide | Type | Template | Message |",
                "| --- | --- | ---: | --- | --- | --- |",
            ]
        )
        for issue in payload["issues"]:
            deck_name = Path(issue["deck"]).name
            slide = "" if issue.get("slide_number") is None else str(issue["slide_number"])
            message = str(issue["message"]).replace("|", "\\|")
            lines.append(
                f"| {issue['severity']} | {deck_name} | {slide} | {issue['type']} | "
                f"{issue.get('template_key') or ''} | {message} |"
            )
    else:
        lines.append("_No design review issues recorded._")
    return "\n".join(lines) + "\n"


def write_one_report(payload: dict[str, Any], json_path: Path, md_path: Path) -> None:
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(markdown_for_payload(payload), encoding="utf-8")


def payload_for_issues(deck_paths: list[Path], issues: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "summary": {
            "decks": len(deck_paths),
            "issues": len(issues),
            "warnings": sum(1 for issue in issues if issue["severity"] == "warning"),
            "info": sum(1 for issue in issues if issue["severity"] == "info"),
        },
        "issues": issues,
    }


def load_gate_config(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    if not path.is_absolute():
        path = BASE_DIR / path
    return load_json(path)


def gate_errors(summary: dict[str, Any], config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if config.get("schema_version") != "1.0":
        errors.append("deck design review gate schema_version must be '1.0'")
    if config.get("mode") != "enforce_thresholds":
        errors.append("deck design review gate mode must be enforce_thresholds")
    thresholds = config.get("thresholds")
    if not isinstance(thresholds, dict):
        errors.append("deck design review gate thresholds must be an object")
        return errors
    checks = {
        "max_issues": "issues",
        "max_warnings": "warnings",
        "max_info": "info",
    }
    for max_key, summary_key in checks.items():
        limit = thresholds.get(max_key)
        if not isinstance(limit, int) or limit < 0:
            errors.append(f"deck design review gate {max_key} must be a non-negative integer")
            continue
        actual = int(summary.get(summary_key, 0))
        if actual > limit:
            errors.append(f"deck design review {summary_key}={actual} exceeds {max_key}={limit}")
    return errors


def attach_gate_result(payload: dict[str, Any], config_path: Path, config: dict[str, Any]) -> list[str]:
    errors = gate_errors(payload["summary"], config)
    payload["gate"] = {
        "config_path": config_path.relative_to(BASE_DIR).as_posix() if config_path.is_absolute() else config_path.as_posix(),
        "mode": config.get("mode"),
        "thresholds": config.get("thresholds", {}),
        "status": "failed" if errors else "passed",
        "errors": errors,
    }
    return errors


def write_reports(payload: dict[str, Any], deck_paths: list[Path]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    write_one_report(payload, REPORTS_DIR / "deck_design_review.json", REPORTS_DIR / "deck_design_review.md")

    for deck in deck_paths:
        deck_key = deck.as_posix()
        deck_issues = [issue for issue in payload["issues"] if issue.get("deck") == deck_key]
        deck_payload = payload_for_issues([deck], deck_issues)
        write_one_report(
            deck_payload,
            REPORTS_DIR / f"{deck.stem}_design_review.json",
            REPORTS_DIR / f"{deck.stem}_design_review.md",
        )


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("deck_paths", nargs="*")
    parser.add_argument("--fail-on-warning", action="store_true")
    parser.add_argument("--fail-on-info", action="store_true")
    parser.add_argument("--fail-on-any", action="store_true")
    parser.add_argument("--gate-config", default=None)
    parser.add_argument("--enforce-gate-config", action="store_true")
    args = parser.parse_args(argv)

    deck_paths = [Path(arg).resolve() for arg in args.deck_paths] if args.deck_paths else [BASE_DIR / path for path in DEFAULT_DECKS]
    all_issues: list[dict[str, Any]] = []
    for deck in deck_paths:
        all_issues.extend(inspect_deck(deck))
    payload = payload_for_issues(deck_paths, all_issues)
    gate_config_errors: list[str] = []
    gate_config_path = Path(args.gate_config) if args.gate_config else None
    if gate_config_path:
        resolved_gate_config_path = gate_config_path if gate_config_path.is_absolute() else BASE_DIR / gate_config_path
        gate_config = load_gate_config(gate_config_path)
        if gate_config is not None:
            gate_config_errors = attach_gate_result(payload, resolved_gate_config_path, gate_config)
    write_reports(payload, deck_paths)
    print(REPORTS_DIR / "deck_design_review.json")
    print(REPORTS_DIR / "deck_design_review.md")
    if args.enforce_gate_config and gate_config_errors:
        for error in gate_config_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if args.fail_on_any and payload["summary"]["issues"] > 0:
        return 1
    if args.fail_on_warning and payload["summary"]["warnings"] > 0:
        return 1
    if args.fail_on_info and payload["summary"]["info"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
