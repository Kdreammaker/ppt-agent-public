from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from scripts.build_deck import load_spec, resolve_path

DEFAULT_SPEC_PATH = BASE_DIR / "data" / "specs" / "template_slide_sample_spec.json"
REPORTS_DIR = BASE_DIR / "outputs" / "reports"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(BASE_DIR).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def output_path_for_spec(spec_path: Path) -> Path:
    spec, spec_dir = load_spec(spec_path)
    output_path = resolve_path(spec_dir, spec.get("output_path"))
    if output_path is None:
        raise ValueError(f"Spec has no output_path: {spec_path}")
    return output_path


def manifest_command(args: list[str]) -> list[str]:
    normalized: list[str] = []
    for arg in args:
        if arg == sys.executable:
            normalized.append("python")
        else:
            try:
                path = Path(arg)
                if path.is_absolute() and path.resolve().is_relative_to(BASE_DIR):
                    normalized.append(relative(path))
                    continue
            except OSError:
                pass
            normalized.append(arg)
    return normalized


def run_build_attempt(spec_path: Path, attempt_no: int) -> dict[str, Any]:
    command = [
        sys.executable,
        "scripts/ppt_system.py",
        "build",
        relative(spec_path),
        "--validate",
        "--auto-project",
        "--auto-run-id",
        "--no-delivery",
        "--no-reference-capture",
    ]
    process = subprocess.run(command, cwd=BASE_DIR, capture_output=True, text=True)
    return {
        "attempt": attempt_no,
        "state": "draft_build_and_validation",
        "command": manifest_command(command),
        "returncode": process.returncode,
        "status": "passed" if process.returncode == 0 else "failed",
        "stdout_tail": process.stdout.splitlines()[-12:],
        "stderr_tail": process.stderr.splitlines()[-12:],
    }


def report_paths_for_output(output_path: Path) -> dict[str, Path]:
    stem = output_path.stem
    return {
        "visual_smoke": REPORTS_DIR / f"{stem}_visual_smoke.json",
        "design_quality": REPORTS_DIR / f"{stem}_quality.json",
        "deck_design_review": REPORTS_DIR / f"{stem}_design_review.json",
        "text_overflow": REPORTS_DIR / f"{stem}_text_overflow.json",
        "slide_selection_rationale": REPORTS_DIR / f"{stem}_slide_selection_rationale.json",
        "deck_slot_map": REPORTS_DIR / f"{stem}_deck_slot_map.json",
    }


def summarize_reports(output_path: Path) -> dict[str, Any]:
    summaries: dict[str, Any] = {}
    for name, path in report_paths_for_output(output_path).items():
        payload = load_json(path)
        summaries[name] = {
            "path": relative(path),
            "exists": path.exists(),
            "summary": payload.get("summary", payload if payload else {}),
        }
    return summaries


def issue_codes(review_payload: dict[str, Any]) -> list[str]:
    return sorted({str(issue.get("code") or issue.get("type")) for issue in review_payload.get("issues", [])})


def propose_revisions(output_path: Path) -> list[dict[str, Any]]:
    reports = report_paths_for_output(output_path)
    design_review = load_json(reports["deck_design_review"])
    overflow = load_json(reports["text_overflow"])
    rationale = load_json(reports["slide_selection_rationale"])
    proposals: list[dict[str, Any]] = []

    codes = issue_codes(design_review)
    if "deterministic_cutoff" in codes or int(overflow.get("summary", {}).get("cutoff_events", 0)) > 0:
        proposals.append(
            {
                "proposal_type": "text_budget_review",
                "safe_to_apply_automatically": False,
                "reason": "Text cutoff exists, but automatic rewriting requires content intent preservation.",
                "future_action": "B24+ may shorten text only when slot source and semantic priority are explicit.",
            }
        )
    if "layout_monotony" in codes:
        proposals.append(
            {
                "proposal_type": "template_substitution",
                "safe_to_apply_automatically": False,
                "reason": "Layout monotony is detected, but safe substitution needs slide intent and candidate fit checks.",
                "future_action": "Try alternate production_ready template from rationale rejected_candidates.",
            }
        )
    if any(code in codes for code in ("template_needs_operator_review", "scope_mismatch")):
        proposals.append(
            {
                "proposal_type": "selector_constraint_review",
                "safe_to_apply_automatically": False,
                "reason": "Selected template policy/scope needs operator review before unattended substitution.",
                "future_action": "Prefer production_ready scope or adjacent-scope candidates with explicit caveat.",
            }
        )
    if not proposals:
        proposals.append(
            {
                "proposal_type": "no_op",
                "safe_to_apply_automatically": True,
                "reason": "Current focused validation passed and no conservative correction trigger was found.",
                "future_action": "Accept draft and record the validation report paths.",
            }
        )

    proposals.append(
        {
            "proposal_type": "rationale_context",
            "safe_to_apply_automatically": False,
            "reason": "Rationale is recorded for future correction strategies.",
            "selected_templates": [
                slide.get("selected_template_key")
                for slide in rationale.get("slides", [])
                if slide.get("selected_template_key")
            ],
        }
    )
    return proposals


def final_decision(attempt: dict[str, Any], proposals: list[dict[str, Any]]) -> dict[str, Any]:
    if attempt["status"] != "passed":
        return {
            "status": "failed",
            "delivery_allowed": False,
            "reason": "Focused build/validation command failed.",
        }
    blocking = [proposal for proposal in proposals if proposal["proposal_type"] != "rationale_context" and not proposal["safe_to_apply_automatically"]]
    if blocking:
        return {
            "status": "accepted_with_recorded_caveats",
            "delivery_allowed": True,
            "reason": "Validation passed; non-automatic improvement proposals were recorded for operator/Phase 5 follow-up.",
        }
    return {
        "status": "accepted",
        "delivery_allowed": True,
        "reason": "Validation passed and no correction was required.",
    }


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Auto Self-Correction Report",
        "",
        f"- Spec: `{report['spec_path']}`",
        f"- Output: `{report['output_path']}`",
        f"- Max attempts: `{report['max_attempts']}`",
        f"- Final status: `{report['final_decision']['status']}`",
        f"- Delivery allowed: `{report['final_decision']['delivery_allowed']}`",
        f"- Reason: {report['final_decision']['reason']}",
        "",
        "## Attempts",
        "",
    ]
    for attempt in report["attempts"]:
        lines.extend(
            [
                f"### Attempt {attempt['attempt']}",
                "",
                f"- State: `{attempt['state']}`",
                f"- Status: `{attempt['status']}`",
                f"- Command: `{' '.join(attempt['command'])}`",
                "",
            ]
        )
    lines.extend(["## Revision Proposals", ""])
    for proposal in report["revision_proposals"]:
        lines.extend(
            [
                f"- `{proposal['proposal_type']}`: {proposal['reason']}",
                f"  - Safe automatic apply: `{proposal['safe_to_apply_automatically']}`",
            ]
        )
    lines.extend(["", "## Report Inputs", ""])
    for name, summary in report["diagnostics"].items():
        lines.append(f"- `{name}`: `{summary['path']}` exists=`{summary['exists']}`")
    return "\n".join(lines) + "\n"


def build_self_correction_report(spec_path: Path, max_attempts: int, check: bool) -> dict[str, Any]:
    if max_attempts < 1:
        raise ValueError("--max-attempts must be at least 1")
    output_path = output_path_for_spec(spec_path)
    attempts: list[dict[str, Any]] = []
    attempt = run_build_attempt(spec_path, 1)
    attempts.append(attempt)
    proposals = propose_revisions(output_path)
    decision = final_decision(attempt, proposals)
    report = {
        "schema_version": "1.0",
        "mode": "auto",
        "state_machine": [
            "draft_build",
            "validation",
            "diagnosis",
            "revision_proposal",
            "final_accept_or_fail",
        ],
        "spec_path": relative(spec_path),
        "output_path": relative(output_path),
        "max_attempts": max_attempts,
        "attempts": attempts,
        "diagnostics": summarize_reports(output_path),
        "revision_proposals": proposals,
        "final_decision": decision,
    }
    if check:
        errors = validate_report(report)
        if errors:
            raise AssertionError("; ".join(errors))
    report_json = REPORTS_DIR / f"{output_path.stem}_auto_self_correction.json"
    report_md = REPORTS_DIR / f"{output_path.stem}_auto_self_correction.md"
    report_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_md.write_text(markdown_report(report), encoding="utf-8")
    print(report_json)
    print(report_md)
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if report.get("mode") != "auto":
        errors.append("mode must be auto")
    if not report.get("state_machine"):
        errors.append("state_machine is required")
    attempts = report.get("attempts", [])
    if not attempts:
        errors.append("at least one attempt is required")
    if len(attempts) > int(report.get("max_attempts", 0)):
        errors.append("attempt count exceeds max_attempts")
    final_decision = report.get("final_decision", {})
    if final_decision.get("status") == "failed" and final_decision.get("delivery_allowed") is not False:
        errors.append("failed final decision must not allow delivery")
    if not report.get("revision_proposals"):
        errors.append("revision_proposals are required")
    diagnostics = report.get("diagnostics", {})
    required = {"visual_smoke", "design_quality", "deck_design_review", "text_overflow", "slide_selection_rationale"}
    missing = sorted(required - set(diagnostics))
    if missing:
        errors.append(f"missing diagnostics: {missing}")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a bounded Auto Mode self-correction loop.")
    parser.add_argument("--spec", default=relative(DEFAULT_SPEC_PATH))
    parser.add_argument("--max-attempts", type=int, default=2)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_self_correction_report((BASE_DIR / args.spec).resolve(), args.max_attempts, args.check)
    print(f"auto_self_correction_status={report['final_decision']['status']}")
    print(f"auto_self_correction_attempts={len(report['attempts'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
