from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
CONTRACT_PATH = BASE_DIR / "config" / "delivery_summary_contract.json"


def relative_ref(path: Path) -> str:
    try:
        return path.resolve().relative_to(BASE_DIR.resolve()).as_posix()
    except ValueError:
        return path.name


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"Request `{summary['request_id']}` delivery status: `{summary['delivery_status']}`",
        "",
        f"Link status: `{summary['link_status']['status']}`",
        "",
        "Artifacts:",
    ]
    for key, value in summary.get("artifact_refs", {}).items():
        if value:
            lines.append(f"- {key}: `{value}`")
    lines.extend(["", "Build rationale:"])
    rationale = summary.get("build_rationale", {})
    for key, value in rationale.items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "Quality findings:"])
    lines.extend([f"- {item}" for item in summary.get("quality_findings", [])] or ["- No blocking findings recorded."])
    lines.extend(["", "Remaining manual review:"])
    lines.extend([f"- {item}" for item in summary.get("remaining_manual_review_points", [])] or ["- None recorded."])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def maybe_report(path: Path) -> dict[str, Any]:
    return load_json(path) if path.exists() else {}


def build_summary(runtime_report: dict[str, Any], *, output_json: Path, output_md: Path) -> dict[str, Any]:
    request_id = str(runtime_report.get("request_id") or "unknown_request")
    runtime_status = str(runtime_report.get("status") or "blocked")
    delivered = runtime_status == "built"
    delivery_status = "delivered" if delivered else ("needs_review" if runtime_status == "needs_review" else "blocked")

    first_slide = maybe_report(BASE_DIR / "outputs" / "reports" / "first_slide_quality_validation.json")
    production_bundle = maybe_report(BASE_DIR / "outputs" / "reports" / "production_build_bundle_validation.json")
    brand = maybe_report(BASE_DIR / "outputs" / "reports" / "brand_style_contract_validation.json")
    quality_findings: list[str] = []
    for label, report in (("first_slide_quality", first_slide), ("production_build_bundle", production_bundle), ("brand_style_contract", brand)):
        errors = report.get("errors", []) if isinstance(report.get("errors"), list) else []
        if errors:
            quality_findings.extend(f"{label}: {error}" for error in errors)
    quality_findings.extend(str(item) for item in runtime_report.get("findings", []))

    artifact_refs = dict(runtime_report.get("artifact_paths", {})) if isinstance(runtime_report.get("artifact_paths"), dict) else {}
    private_build = runtime_report.get("private_build", {}) if isinstance(runtime_report.get("private_build"), dict) else {}
    private_artifacts = private_build.get("artifact_paths", {}) if isinstance(private_build.get("artifact_paths"), dict) else {}
    for key in ("pptx", "html", "html_manifest"):
        if private_artifacts.get(key):
            artifact_refs[key] = private_artifacts[key]

    summary = {
        "schema_version": "1.0",
        "request_id": request_id,
        "delivery_status": delivery_status,
        "link_status": {
            "status": "private_links_ready" if delivered else "blocked_no_success_link",
            "drive_permission": "private_sync_default",
            "public_editor_link": None,
            "public_editor_link_enabled": False,
        },
        "artifact_refs": artifact_refs,
        "build_rationale": {
            "selected_template_family": "production_template_manifest",
            "selected_brand_profile_id": "brand:sample-neutral-modern:v1",
            "selected_operating_mode": runtime_report.get("operating_mode"),
            "rejected_candidate_rationale": "See config/production_template_manifest.json fallback rejected_candidate_rationale fields.",
        },
        "quality_findings": quality_findings,
        "remaining_manual_review_points": [] if delivered and not quality_findings else ["Resolve blocking findings before Drive/Slack success delivery."],
        "reply_summary": relative_ref(output_md),
        "policy_summary": {
            "blocked_delivery_claims_success": False,
            "drive_public_permission_changed": False,
            "slack_success_reply_allowed": delivered and not quality_findings,
        },
    }
    write_json(output_json, summary)
    write_markdown(output_md, summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Build delivery summary JSON/Markdown from a maker runtime report.")
    parser.add_argument("--runtime-report", required=True)
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-md", required=True)
    args = parser.parse_args()
    runtime_report = Path(args.runtime_report)
    if not runtime_report.is_absolute():
        runtime_report = (BASE_DIR / runtime_report).resolve()
    output_json = Path(args.output_json)
    if not output_json.is_absolute():
        output_json = (BASE_DIR / output_json).resolve()
    output_md = Path(args.output_md)
    if not output_md.is_absolute():
        output_md = (BASE_DIR / output_md).resolve()
    summary = build_summary(load_json(runtime_report), output_json=output_json, output_md=output_md)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
